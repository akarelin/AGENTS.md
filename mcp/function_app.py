"""Azure Function — Multi-endpoint MCP server (Streamable HTTP) with Entra OAuth shim.

Auth model:
  - The function validates inbound Bearer JWTs itself against Entra JWKS
    (no Easy Auth dependency — works in containerised / App-Proxy fronted deploys).
  - The "OAuth shim" endpoints (/.well-known/*, /register, /authorize,
    /oauth/callback, /token) delegate user authentication to Entra ID via the
    MCP United app registration, then issue real Entra JWTs back to the caller.
  - Allowlist enforcement: oid claim must be in `mcp-allowed-oids` (KV secret).
  - PSK fallback (`MCP_API_KEY`) is supported via `MCP_AUTH_MODE` env:
      psk      → PSK required (legacy, default)
      entra    → Entra JWT required
      both     → PSK accepted, otherwise Entra JWT
      disabled → no auth (dev only)
"""

import base64
import hashlib
import json
import logging
import os
import secrets
import time
from urllib.parse import parse_qs, urlencode

import azure.functions as func
import jwt as pyjwt
import msal
import requests
from gppu import Vault

import tools as m365_tools
import tools_admin as admin_tools
import tools_keys as keys_tools
import tools_obsidian as obsidian_tools
import tools_neo4j as neo4j_tools
import tools_ticktick as ticktick_tools
import tools_qmd as qmd_tools

app = func.FunctionApp()

PROTOCOL_VERSION = "2025-03-26"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOL_TEXT_LIMIT = int(os.environ.get("MCP_TOOL_TEXT_LIMIT", "12000"))
AUTH_MODE = os.environ.get("MCP_AUTH_MODE", "psk").lower()
BASE_URL = os.environ["MCP_BASE_URL"].rstrip("/")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,x-api-key,Accept,Mcp-Session-Id",
}

_ICON_FILES = {
    "keys": "Keys.png",
    "m365": "M365.png",
    "m365-admin": "M365-admin.png",
}
_SERVER_ICONS = {}


# ── Entra config + JWKS cache ──────────────────────────────────────

_ENTRA_PREFIX = "mcp-entra"
_entra_config = {}
_jwks_cache = {}      # tid → {keys, ts}
_pending = {}         # nonce → {state, code_challenge, redirect_uri, our_verifier, ts}
_token_store = {}     # our_code → {access_token, refresh_token, expires_in, code_challenge, ts}
_STATE_TTL = 600      # 10 min


def _now():
    return int(time.time())


def _entra():
    if not _entra_config:
        _entra_config["tenant_id"] = Vault.get(f"{_ENTRA_PREFIX}-tenant-id")
        _entra_config["client_id"] = Vault.get(f"{_ENTRA_PREFIX}-client-id")
        _entra_config["client_secret"] = Vault.get(f"{_ENTRA_PREFIX}-client-secret")
        _entra_config["audience"] = Vault.get(f"{_ENTRA_PREFIX}-resource-audience")
        oids = Vault.get("mcp-allowed-oids") or ""
        _entra_config["allowed_oids"] = {o.strip() for o in oids.split(",") if o.strip()}
    return _entra_config


def _gc_state():
    cutoff = _now() - _STATE_TTL
    for d in (_pending, _token_store):
        for k in [k for k, v in d.items() if v.get("ts", 0) < cutoff]:
            d.pop(k, None)


def _pkce_pair():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _get_jwks(tid):
    cached = _jwks_cache.get(tid)
    if cached and _now() - cached["ts"] < 3600:
        return cached["keys"]
    url = f"https://login.microsoftonline.com/{tid}/discovery/v2.0/keys"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    keys = resp.json().get("keys", [])
    _jwks_cache[tid] = {"keys": keys, "ts": _now()}
    return keys


def _validate_jwt(token):
    cfg = _entra()
    header = pyjwt.get_unverified_header(token)
    kid = header.get("kid")
    unverified = pyjwt.decode(token, options={"verify_signature": False})
    tid = unverified.get("tid")
    if not tid:
        raise ValueError("missing tid claim")
    keys = _get_jwks(tid)
    jwk = next((k for k in keys if k.get("kid") == kid), None)
    if not jwk:
        raise ValueError(f"no JWKS key for kid={kid}")
    public_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
    issuer = f"https://login.microsoftonline.com/{tid}/v2.0"
    return pyjwt.decode(
        token,
        key=public_key,
        algorithms=["RS256"],
        audience=cfg["client_id"],
        issuer=issuer,
    )


# ── Auth ───────────────────────────────────────────────────────────

def _bearer(req):
    auth = req.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


def _unauth(req, msg="Unauthorized", status=401):
    base = _base_url(req)
    return func.HttpResponse(
        msg,
        status_code=status,
        headers={
            "WWW-Authenticate": (
                f'Bearer realm="mcp.karelin.ai", '
                f'resource_metadata="{base}/.well-known/oauth-protected-resource"'
            ),
            **CORS_HEADERS,
        },
    )


def _check_auth(req):
    if AUTH_MODE == "disabled":
        return None

    psk = os.environ.get("MCP_API_KEY")
    provided = (
        req.headers.get("x-api-key")
        or _bearer(req)
        or req.params.get("token")
    )

    if AUTH_MODE in ("psk", "both") and psk and provided == psk:
        return None

    if AUTH_MODE == "psk":
        return _unauth(req)

    token = _bearer(req)
    if not token:
        return _unauth(req)
    try:
        claims = _validate_jwt(token)
    except Exception as e:
        logging.warning("JWT validation failed: %s", e)
        return _unauth(req, "Invalid token")
    cfg = _entra()
    oid = claims.get("oid")
    if not oid or (cfg["allowed_oids"] and oid not in cfg["allowed_oids"]):
        return _unauth(req, "Forbidden", status=403)
    return None


# ── JSON-RPC helpers ────────────────────────────────────────────────

def _ok(id, result):
    return {"jsonrpc": "2.0", "id": id, "result": result}


def _err(id, code, message):
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def _base_url(req):
    return BASE_URL


def _handle(body, tools, dispatcher, server_name, req=None):
    msg_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    if method == "notifications/initialized":
        return None
    if msg_id is None:
        return None

    if method == "initialize":
        info = {"name": server_name, "version": "1.0.0"}
        slug = _SERVER_ICONS.get(server_name)
        if req and slug:
            info["icon"] = f"{_base_url(req)}/icons/{slug}"
        return _ok(msg_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": info,
        })

    if method == "ping":
        return _ok(msg_id, {})

    if method == "tools/list":
        return _ok(msg_id, {"tools": tools})

    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {})
        try:
            result = dispatcher(name, args)
            text = json.dumps(result, default=str)
            if len(text) > TOOL_TEXT_LIMIT:
                text = (f"{text[:TOOL_TEXT_LIMIT]}\n\n"
                        f"[truncated at {TOOL_TEXT_LIMIT} chars; refine query for narrower results]")
            return _ok(msg_id, {"content": [{"type": "text", "text": text}]})
        except Exception as e:
            logging.exception("Tool %s failed", name)
            return _ok(msg_id, {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True,
            })

    return _err(msg_id, -32601, f"Method not found: {method}")


def _mcp_response(req, tools, dispatcher, server_name):
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=CORS_HEADERS)

    if req.method == "GET":
        payload = json.dumps({
            "name": server_name,
            "protocolVersion": PROTOCOL_VERSION,
            "transport": "streamable-http",
            "tools": [{"name": t["name"], "description": t.get("description", "")} for t in tools],
        })
        return func.HttpResponse(payload, status_code=200, mimetype="application/json",
                                 headers=CORS_HEADERS)

    denied = _check_auth(req)
    if denied:
        return denied

    if req.method == "DELETE":
        return func.HttpResponse(status_code=200)

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps(_err(None, -32700, "Parse error")),
            status_code=400, mimetype="application/json",
        )

    if isinstance(body, list):
        result = [r for r in (_handle(item, tools, dispatcher, server_name, req) for item in body) if r is not None]
    else:
        result = _handle(body, tools, dispatcher, server_name, req)

    if result is None or result == []:
        return func.HttpResponse(status_code=202)

    payload = json.dumps(result, default=str)

    accept = req.headers.get("Accept", "")
    if "text/event-stream" in accept:
        sse = f"event: message\ndata: {payload}\n\n"
        return func.HttpResponse(sse, status_code=200, mimetype="text/event-stream",
                                 headers={"Cache-Control": "no-cache", **CORS_HEADERS})

    return func.HttpResponse(payload, status_code=200, mimetype="application/json",
                             headers=CORS_HEADERS)


# ── Icons ──────────────────────────────────────────────────────────

@app.route(route="icons/{name}", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
def icons(req: func.HttpRequest) -> func.HttpResponse:
    name = req.route_params.get("name", "")
    filename = _ICON_FILES.get(name)
    if not filename:
        return func.HttpResponse("Not found", status_code=404)
    path = os.path.join(SCRIPT_DIR, filename)
    if not os.path.exists(path):
        return func.HttpResponse("Not found", status_code=404)
    with open(path, "rb") as f:
        return func.HttpResponse(f.read(), status_code=200, mimetype="image/png")


# ── Docs ───────────────────────────────────────────────────────────

@app.route(route="docs", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
def docs(req: func.HttpRequest) -> func.HttpResponse:
    readme_path = os.path.join(SCRIPT_DIR, "README.md")
    if not os.path.exists(readme_path):
        return func.HttpResponse("Not found", status_code=404)
    with open(readme_path, "r", encoding="utf-8") as f:
        md = f.read()
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>MCP Server</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #24292e; line-height: 1.6; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
th, td {{ border: 1px solid #dfe2e5; padding: 8px 12px; text-align: left; }}
th {{ background: #f6f8fa; }}
code {{ background: #f6f8fa; padding: 2px 6px; border-radius: 3px; font-size: 90%; }}
pre {{ background: #f6f8fa; padding: 16px; border-radius: 6px; overflow-x: auto; }}
h1 {{ border-bottom: 2px solid #eaecef; padding-bottom: 8px; }}
h2 {{ border-bottom: 1px solid #eaecef; padding-bottom: 6px; margin-top: 32px; }}
</style>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head><body><div id="content"></div>
<script>document.getElementById('content').innerHTML = marked.parse({json.dumps(md)});</script>
</body></html>"""
    return func.HttpResponse(html, status_code=200, mimetype="text/html")


# ── OAuth shim ─────────────────────────────────────────────────────

def _protected_resource_response(req):
    base = _base_url(req)
    return func.HttpResponse(json.dumps({
        "resource": base,
        "authorization_servers": [base],
        "scopes_supported": ["MCP.Access"],
        "bearer_methods_supported": ["header"],
    }), mimetype="application/json", headers=CORS_HEADERS)


@app.route(route=".well-known/oauth-protected-resource/{*path}", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
def oauth_protected_resource_path(req: func.HttpRequest) -> func.HttpResponse:
    return _protected_resource_response(req)


@app.route(route=".well-known/oauth-protected-resource", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
def oauth_protected_resource(req: func.HttpRequest) -> func.HttpResponse:
    return _protected_resource_response(req)


@app.route(route=".well-known/oauth-authorization-server", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
def oauth_metadata(req: func.HttpRequest) -> func.HttpResponse:
    base = _base_url(req)
    return func.HttpResponse(json.dumps({
        "issuer": base,
        "authorization_endpoint": f"{base}/authorize",
        "token_endpoint": f"{base}/token",
        "registration_endpoint": f"{base}/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ["MCP.Access"],
        "logo_uri": f"{base}/icons/m365",
        "service_documentation": f"{base}/docs",
    }), mimetype="application/json", headers=CORS_HEADERS)


@app.route(route="register", methods=["POST", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def register(req: func.HttpRequest) -> func.HttpResponse:
    """RFC 7591 Dynamic Client Registration stub — returns our pre-registered Entra client_id.

    Entra ID has no DCR endpoint; we lie about supporting it so callers (claude.ai)
    will use our fixed client_id in subsequent /authorize calls. The real
    confidential-client exchange happens server-side in /oauth/callback.
    """
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=CORS_HEADERS)
    cfg = _entra()
    body = {}
    try:
        body = req.get_json() or {}
    except Exception:
        pass
    return func.HttpResponse(json.dumps({
        "client_id": cfg["client_id"],
        "client_id_issued_at": _now(),
        "client_name": body.get("client_name", "MCP Karelin Client"),
        "redirect_uris": body.get("redirect_uris", []),
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }), mimetype="application/json", headers=CORS_HEADERS)


@app.route(route="authorize", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
def authorize(req: func.HttpRequest) -> func.HttpResponse:
    """Save caller's PKCE state, 302 to Entra's /authorize with our own PKCE pair."""
    _gc_state()
    cfg = _entra()
    callers_state = req.params.get("state", "")
    callers_challenge = req.params.get("code_challenge", "")
    callers_method = req.params.get("code_challenge_method", "")
    callers_redirect = req.params.get("redirect_uri", "")

    if callers_method and callers_method != "S256":
        return func.HttpResponse("Only S256 PKCE supported", status_code=400)
    if not callers_redirect:
        return func.HttpResponse("Missing redirect_uri", status_code=400)

    nonce = secrets.token_urlsafe(32)
    _pending[nonce] = {
        "state": callers_state,
        "code_challenge": callers_challenge,
        "redirect_uri": callers_redirect,
        "ts": _now(),
    }

    base = _base_url(req)
    entra_url = (
        f"https://login.microsoftonline.com/{cfg['tenant_id']}/oauth2/v2.0/authorize?"
        + urlencode({
            "client_id": cfg["client_id"],
            "response_type": "code",
            "redirect_uri": f"{base}/oauth/callback",
            "response_mode": "query",
            "scope": f"{cfg['audience']}/MCP.Access offline_access",
            "state": nonce,
            "prompt": "select_account",
        })
    )
    return func.HttpResponse(status_code=302, headers={"Location": entra_url})


@app.route(route="oauth/callback", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
def oauth_callback(req: func.HttpRequest) -> func.HttpResponse:
    """Exchange Entra's code for tokens, mint our own code, 302 back to caller."""
    _gc_state()
    cfg = _entra()
    err = req.params.get("error")
    if err:
        return func.HttpResponse(
            f"Entra error: {err}: {req.params.get('error_description', '')}",
            status_code=400)

    entra_code = req.params.get("code", "")
    nonce = req.params.get("state", "")
    pending = _pending.pop(nonce, None)
    if not pending:
        return func.HttpResponse("Unknown or expired state", status_code=400)

    base = _base_url(req)
    msal_app = msal.ConfidentialClientApplication(
        cfg["client_id"],
        authority=f"https://login.microsoftonline.com/{cfg['tenant_id']}",
        client_credential=cfg["client_secret"],
    )
    result = msal_app.acquire_token_by_authorization_code(
        code=entra_code,
        scopes=[f"{cfg['audience']}/MCP.Access"],
        redirect_uri=f"{base}/oauth/callback",
    )
    if "access_token" not in result:
        err_desc = result.get("error_description", result.get("error", "unknown"))
        logging.error("Entra token exchange failed: %s", err_desc)
        return func.HttpResponse(f"Token exchange failed: {err_desc}", status_code=400)

    our_code = secrets.token_urlsafe(32)
    _token_store[our_code] = {
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token"),
        "expires_in": result.get("expires_in", 3600),
        "code_challenge": pending["code_challenge"],
        "ts": _now(),
    }

    sep = "&" if "?" in pending["redirect_uri"] else "?"
    redirect_back = (
        f"{pending['redirect_uri']}{sep}code={our_code}&state={pending['state']}"
    )
    return func.HttpResponse(status_code=302, headers={"Location": redirect_back})


@app.route(route="token", methods=["POST", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def token(req: func.HttpRequest) -> func.HttpResponse:
    """Exchange our code for Entra tokens; proxy refresh_token grants to Entra."""
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=CORS_HEADERS)
    _gc_state()
    cfg = _entra()
    body = parse_qs(req.get_body().decode())
    get = lambda k: body.get(k, [""])[0]
    grant = get("grant_type")

    def _json(payload, status=200):
        return func.HttpResponse(
            json.dumps(payload), status_code=status,
            mimetype="application/json", headers=CORS_HEADERS)

    if grant == "authorization_code":
        our_code = get("code")
        verifier = get("code_verifier")
        stored = _token_store.pop(our_code, None)
        if not stored:
            return _json({"error": "invalid_grant"}, 400)
        if stored["code_challenge"]:
            if not verifier:
                return _json({"error": "invalid_grant",
                              "error_description": "Missing code_verifier"}, 400)
            digest = hashlib.sha256(verifier.encode()).digest()
            expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
            if expected != stored["code_challenge"]:
                return _json({"error": "invalid_grant",
                              "error_description": "PKCE verification failed"}, 400)
        return _json({
            "access_token": stored["access_token"],
            "refresh_token": stored.get("refresh_token"),
            "expires_in": stored["expires_in"],
            "token_type": "Bearer",
        })

    if grant == "refresh_token":
        rt = get("refresh_token")
        if not rt:
            return _json({"error": "invalid_request"}, 400)
        msal_app = msal.ConfidentialClientApplication(
            cfg["client_id"],
            authority=f"https://login.microsoftonline.com/{cfg['tenant_id']}",
            client_credential=cfg["client_secret"],
        )
        result = msal_app.acquire_token_by_refresh_token(
            rt, scopes=[f"{cfg['audience']}/MCP.Access"])
        if "access_token" not in result:
            return _json({"error": "invalid_grant",
                          "error_description": result.get("error_description", "refresh failed")}, 400)
        return _json({
            "access_token": result["access_token"],
            "refresh_token": result.get("refresh_token", rt),
            "expires_in": result.get("expires_in", 3600),
            "token_type": "Bearer",
        })

    return _json({"error": "unsupported_grant_type"}, 400)


# ── Endpoints ──────────────────────────────────────────────────────

_ALL_TOOLS = []
_ALL_DISPATCHERS = {}

for _mod, _fn in [
    (keys_tools,     keys_tools.dispatch_tool),
    (m365_tools,     m365_tools.dispatch_tool),
    (admin_tools,    admin_tools.dispatch_tool),
    (obsidian_tools, obsidian_tools.dispatch_tool),
    (neo4j_tools,    neo4j_tools.dispatch_tool),
    (ticktick_tools, ticktick_tools.dispatch),
    (qmd_tools,      qmd_tools.dispatch_tool),
]:
    for _t in _mod.TOOLS:
        if _t["name"] in _ALL_DISPATCHERS:
            raise RuntimeError(f"duplicate tool name across modules: {_t['name']}")
        _ALL_DISPATCHERS[_t["name"]] = _fn
        _ALL_TOOLS.append(_t)


def _dispatch_all(name, args):
    fn = _ALL_DISPATCHERS.get(name)
    if not fn:
        raise ValueError(f"unknown tool: {name}")
    return fn(name, args)


@app.route(route="mcp", methods=["GET", "POST", "DELETE", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def mcp(req: func.HttpRequest) -> func.HttpResponse:
    return _mcp_response(req, _ALL_TOOLS, _dispatch_all, "Karelin")


@app.route(route="keys", methods=["GET", "POST", "DELETE", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def keys(req: func.HttpRequest) -> func.HttpResponse:
    return _mcp_response(req, keys_tools.TOOLS, keys_tools.dispatch_tool, "Keys")


@app.route(route="m365", methods=["GET", "POST", "DELETE", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def m365(req: func.HttpRequest) -> func.HttpResponse:
    return _mcp_response(req, m365_tools.TOOLS, m365_tools.dispatch_tool, "M365")


@app.route(route="m365-admin", methods=["GET", "POST", "DELETE", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def m365_admin(req: func.HttpRequest) -> func.HttpResponse:
    return _mcp_response(req, admin_tools.TOOLS, admin_tools.dispatch_tool, "M365 Admin")


@app.route(route="obsidian", methods=["GET", "POST", "DELETE", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def obsidian(req: func.HttpRequest) -> func.HttpResponse:
    return _mcp_response(req, obsidian_tools.TOOLS, obsidian_tools.dispatch_tool, "Obsidian")


@app.route(route="neo4j", methods=["GET", "POST", "DELETE", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def neo4j(req: func.HttpRequest) -> func.HttpResponse:
    return _mcp_response(req, neo4j_tools.TOOLS, neo4j_tools.dispatch_tool, "Neo4j")


@app.route(route="ticktick", methods=["GET", "POST", "DELETE", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def ticktick(req: func.HttpRequest) -> func.HttpResponse:
    return _mcp_response(req, ticktick_tools.TOOLS, ticktick_tools.dispatch, "TickTick")


@app.route(route="qmd", methods=["GET", "POST", "DELETE", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def qmd(req: func.HttpRequest) -> func.HttpResponse:
    return _mcp_response(req, qmd_tools.TOOLS, qmd_tools.dispatch_tool, "QMD")
