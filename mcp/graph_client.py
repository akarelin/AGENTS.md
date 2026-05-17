"""Microsoft Graph beta API client — on-behalf-of (OBO) flow.

Uses MCP Universal (mcp-entra-*) credentials to exchange the inbound user's
MCP.Access token for a Graph token bound to that user's identity. All Graph
calls execute as the calling user, so per-user permission boundaries are
enforced by Graph itself — no client-side allowlists, no /users/{oid} rewriting.
"""

import hashlib
import time
from contextvars import ContextVar

import msal
import requests

from gppu import Vault

GRAPH_BASE = "https://graph.microsoft.com/beta"
_ENTRA_PREFIX = "mcp-entra"

# Set per-request by function_app._check_auth after a successful JWT validation.
current_user_assertion: ContextVar = ContextVar("current_user_assertion", default=None)

_msal_app = None
_token_cache = {}  # sha256(assertion) → {token, expires_at}


def _msal():
    global _msal_app
    if _msal_app is None:
        tenant_id     = Vault.get(f"{_ENTRA_PREFIX}-tenant-id")
        client_id     = Vault.get(f"{_ENTRA_PREFIX}-client-id")
        client_secret = Vault.get(f"{_ENTRA_PREFIX}-client-secret")
        _msal_app = msal.ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )
    return _msal_app


def get_token():
    """Exchange the current request's user assertion for a Graph token via OBO."""
    assertion = current_user_assertion.get()
    if not assertion:
        raise RuntimeError(
            "No user assertion in context — graph_client called outside an authenticated "
            "Entra request. Graph endpoints are not available under PSK auth mode."
        )
    key = hashlib.sha256(assertion.encode()).hexdigest()
    now = int(time.time())
    cached = _token_cache.get(key)
    if cached and cached["expires_at"] > now + 60:
        return cached["token"]
    result = _msal().acquire_token_on_behalf_of(
        user_assertion=assertion,
        scopes=["https://graph.microsoft.com/.default"],
    )
    if "access_token" not in result:
        raise RuntimeError(
            f"OBO exchange failed: {result.get('error_description', result)}"
        )
    _token_cache[key] = {
        "token": result["access_token"],
        "expires_at": now + result.get("expires_in", 3600),
    }
    return result["access_token"]


def graph_request(method, path, params=None, json_body=None, extra_headers=None, **_legacy):
    """Call Graph as the current user via OBO.

    `**_legacy` swallows the old `user_hint` kwarg from callers in tools.py —
    OBO binds user identity to the token, so /me/ resolves natively and the
    hint is meaningless.
    """
    token = get_token()
    url = f"{GRAPH_BASE}{path}" if path.startswith("/") else f"{GRAPH_BASE}/{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    resp = requests.request(method, url, headers=headers, params=params, json=json_body)
    if resp.status_code == 204:
        return {"status": "ok"}
    try:
        data = resp.json()
    except Exception:
        return {"error": f"HTTP {resp.status_code}", "body": resp.text}
    if resp.status_code >= 400:
        err = data.get("error", {})
        return {"error": err.get("message", f"HTTP {resp.status_code}"), "code": err.get("code")}
    return data


def graph_get(path, **kw):
    return graph_request("GET", path, **kw)

def graph_post(path, json_body=None, **kw):
    return graph_request("POST", path, json_body=json_body, **kw)

def graph_patch(path, json_body=None, **kw):
    return graph_request("PATCH", path, json_body=json_body, **kw)

def graph_delete(path, **kw):
    return graph_request("DELETE", path, **kw)
