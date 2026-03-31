"""Azure Function — Multi-endpoint MCP server (Streamable HTTP transport)."""

import base64
import hashlib
import json
import logging
import os
import secrets
import time
import azure.functions as func
from urllib.parse import parse_qs

import tools as m365_tools
import tools_admin as admin_tools
import tools_keys as keys_tools
import tools_obsidian as obsidian_tools

app = func.FunctionApp()

PROTOCOL_VERSION = "2025-03-26"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOL_TEXT_LIMIT = int(os.environ.get("MCP_TOOL_TEXT_LIMIT", "12000"))

_auth_codes = {}    # code → {challenge, method, redirect_uri, ts}
_access_tokens = set()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,x-api-key,Accept,Mcp-Session-Id",
}

_ICON_FILES = {
    "keys": "Keys.png",
    "m365": "M365.png",
    "m365-admin": "M365-admin.png",
    "obsidian": "Obsidian.png",
}
_SERVER_ICONS = {
    "Karelin Keys": "keys",
    "Karelin M365": "m365",
    "Karelin M365 Admin": "m365-admin",
    "Karelin Obsidian": "obsidian",
}


# ── JSON-RPC helpers ────────────────────────────────────────────────

def _ok(id, result):
    return {"jsonrpc": "2.0", "id": id, "result": result}

def _err(id, code, message):
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


# ── Generic MCP handler ────────────────────────────────────────────

def _base_url(req):
    proto = req.headers.get("X-Forwarded-Proto", "http")
    host = req.headers.get("Host", "localhost")
    return f"{proto}://{host}"


def _handle(body, tools, dispatcher, server_name, req=None):
    msg_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    # Notifications (no id) — acknowledge silently
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
            return _ok(msg_id, {
                "content": [{"type": "text", "text": text}],
            })
        except Exception as e:
            logging.exception("Tool %s failed", name)
            return _ok(msg_id, {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True,
            })

    return _err(msg_id, -32601, f"Method not found: {method}")


def _check_psk(req):
    psk = os.environ.get("MCP_API_KEY")
    if not psk:
        return None
    provided = (
        req.headers.get("x-api-key")
        or (req.headers.get("Authorization", "").removeprefix("Bearer ").strip() or None)
        or req.params.get("token")
    )
    if provided == psk or provided in _access_tokens:
        return None
    return func.HttpResponse("Unauthorized", status_code=401)


def _mcp_response(req, tools, dispatcher, server_name):
    # CORS preflight
    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=204, headers=CORS_HEADERS)

    # GET — server/tool metadata for discovery
    if req.method == "GET":
        payload = json.dumps({
            "name": server_name,
            "protocolVersion": PROTOCOL_VERSION,
            "transport": "streamable-http",
            "tools": [{"name": t["name"], "description": t.get("description", "")} for t in tools],
        })
        return func.HttpResponse(payload, status_code=200, mimetype="application/json",
                                 headers=CORS_HEADERS)

    denied = _check_psk(req)
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

    # Batch JSON-RPC support
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
<html><head><meta charset="utf-8"><title>MCP Server — mcp.karelin.com</title>
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


# ── OAuth 2.0 (PKCE) ───────────────────────────────────────────────

def _protected_resource_response(req):
    base = _base_url(req)
    return func.HttpResponse(json.dumps({
        "resource": base,
        "authorization_servers": [base],
        "scopes_supported": [],
        "bearer_methods_supported": ["header"],
    }), mimetype="application/json")


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
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "client_id_metadata_document_supported": True,
        "logo_uri": f"{base}/icons/m365",
        "service_documentation": f"{base}/docs",
    }), mimetype="application/json")


@app.route(route="authorize", methods=["GET"],
           auth_level=func.AuthLevel.ANONYMOUS)
def authorize(req: func.HttpRequest) -> func.HttpResponse:
    client_id = req.params.get("client_id", "")
    redirect_uri = req.params.get("redirect_uri", "")
    state = req.params.get("state", "")
    code_challenge = req.params.get("code_challenge", "")
    code_challenge_method = req.params.get("code_challenge_method", "")

    psk = os.environ.get("MCP_API_KEY")
    if psk and client_id != psk:
        return func.HttpResponse("Invalid client_id", status_code=403)

    code = secrets.token_urlsafe(32)
    _auth_codes[code] = {
        "challenge": code_challenge,
        "method": code_challenge_method,
        "redirect_uri": redirect_uri,
        "ts": time.time(),
    }

    location = f"{redirect_uri}?code={code}&state={state}"
    return func.HttpResponse(status_code=302, headers={"Location": location})


@app.route(route="token", methods=["POST"],
           auth_level=func.AuthLevel.ANONYMOUS)
def token(req: func.HttpRequest) -> func.HttpResponse:
    body = parse_qs(req.get_body().decode())
    get = lambda k: body.get(k, [""])[0]

    if get("grant_type") != "authorization_code":
        return func.HttpResponse(
            json.dumps({"error": "unsupported_grant_type"}),
            status_code=400, mimetype="application/json")

    code = get("code")
    stored = _auth_codes.pop(code, None)
    if not stored or time.time() - stored["ts"] > 300:
        return func.HttpResponse(
            json.dumps({"error": "invalid_grant"}),
            status_code=400, mimetype="application/json")

    # Verify PKCE
    verifier = get("code_verifier")
    if stored.get("method") == "S256" and verifier:
        digest = hashlib.sha256(verifier.encode()).digest()
        expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        if expected != stored["challenge"]:
            return func.HttpResponse(
                json.dumps({"error": "invalid_grant"}),
                status_code=400, mimetype="application/json")

    access_token = secrets.token_urlsafe(32)
    _access_tokens.add(access_token)

    return func.HttpResponse(json.dumps({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 86400,
    }), mimetype="application/json")


# ── Endpoints ──────────────────────────────────────────────────────

@app.route(route="keys", methods=["GET", "POST", "DELETE", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def keys(req: func.HttpRequest) -> func.HttpResponse:
    return _mcp_response(req, keys_tools.TOOLS, keys_tools.dispatch_tool, "Karelin Keys")


@app.route(route="m365", methods=["GET", "POST", "DELETE", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def m365(req: func.HttpRequest) -> func.HttpResponse:
    return _mcp_response(req, m365_tools.TOOLS, m365_tools.dispatch_tool, "Karelin M365")


@app.route(route="m365-admin", methods=["GET", "POST", "DELETE", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def m365_admin(req: func.HttpRequest) -> func.HttpResponse:
    return _mcp_response(req, admin_tools.TOOLS, admin_tools.dispatch_tool, "Karelin M365 Admin")


@app.route(route="obsidian", methods=["GET", "POST", "DELETE", "OPTIONS"],
           auth_level=func.AuthLevel.ANONYMOUS)
def obsidian(req: func.HttpRequest) -> func.HttpResponse:
    return _mcp_response(req, obsidian_tools.TOOLS, obsidian_tools.dispatch_tool, "Karelin Obsidian")
