"""Microsoft Graph beta API client for Azure Functions — client credentials flow."""

import logging
import msal
import requests

from gppu import resolve_secret

GRAPH_BASE = "https://graph.microsoft.com/beta"

# ##  User hints → AAD object IDs  ##
USERS = {
    "alex":    "be083348-9398-4a22-acef-c48ab74806c1",
    "irina":   "6fff1ee8-31ca-4480-b7b2-04dc6d20c81e",
    "default": "be083348-9398-4a22-acef-c48ab74806c1",
}

_token_cache = {}


def get_token():
    if "t" in _token_cache:
        return _token_cache["t"]
    tenant_id = resolve_secret("msgraph-karelin-tenant-id")
    client_id = resolve_secret("msgraph-karelin-client-id")
    client_secret = resolve_secret("msgraph-karelin-client-secret")
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id, authority=authority, client_credential=client_secret
    )
    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" in result:
        _token_cache["t"] = result["access_token"]
        return result["access_token"]
    raise RuntimeError(f"Auth failed: {result.get('error_description', result)}")


def _resolve_path(path, user_hint):
    """Replace /me/ with /users/{aad_id}/ for the target user."""
    aad_id = USERS.get(user_hint, user_hint)  # allow raw AAD ID too
    if path.startswith("/me/"):
        return f"/users/{aad_id}/{path[4:]}"
    if path == "/me":
        return f"/users/{aad_id}"
    if path.startswith("/me?"):
        return f"/users/{aad_id}?{path[4:]}"
    return path


def graph_request(method, path, user_hint="default",
                  params=None, json_body=None, extra_headers=None):
    token = get_token()
    path = _resolve_path(path, user_hint)
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
