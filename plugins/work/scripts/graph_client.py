#!/usr/bin/env python3
"""
Microsoft Graph beta API client — application permissions, no interactive login.
Uses client credentials flow. Routes /me/ to /users/{aad_id}/ per user.
"""

import json
import os
import sys
import msal
import requests

GRAPH_BASE = "https://graph.microsoft.com/beta"
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))

# Map user hints to AAD object IDs
USERS = {
    "alex":    "be083348-9398-4a22-acef-c48ab74806c1",
    "irina":   "6fff1ee8-31ca-4480-b7b2-04dc6d20c81e",
    "default": "be083348-9398-4a22-acef-c48ab74806c1",
}

_token_cache = {}


def _load_tenant_config(tenant="karelin"):
    # Try multiple env var prefixes: MS365_CLIENT_ID, MS365_MCP_CLIENT_ID
    for prefix in ("MS365_", "MS365_MCP_"):
        cid = os.environ.get(f"{prefix}CLIENT_ID")
        tid = os.environ.get(f"{prefix}TENANT_ID")
        sec = os.environ.get(f"{prefix}CLIENT_SECRET")
        if cid and tid and sec:
            return {"tenant_id": tid, "client_id": cid, "client_secret": sec}
    tenants_file = os.path.join(SKILL_DIR, "tenants.json")
    if os.path.exists(tenants_file):
        with open(tenants_file) as f:
            data = json.load(f)
            cfg = data.get(tenant, {})
            if cfg:
                return cfg
    print(f"Error: No config for tenant '{tenant}'. Set MS365_CLIENT_ID/MS365_TENANT_ID/MS365_CLIENT_SECRET env vars, or create {tenants_file}.", file=sys.stderr)
    sys.exit(1)


def get_token(tenant="karelin"):
    if tenant in _token_cache:
        return _token_cache[tenant]

    config = _load_tenant_config(tenant)
    authority = f"https://login.microsoftonline.com/{config['tenant_id']}"
    app = msal.ConfidentialClientApplication(
        config["client_id"],
        authority=authority,
        client_credential=config["client_secret"],
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" in result:
        _token_cache[tenant] = result["access_token"]
        return result["access_token"]
    print(f"Auth failed: {result.get('error_description', result)}", file=sys.stderr)
    sys.exit(1)


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


def graph_request(method, path, tenant="karelin", user_hint="default",
                  params=None, json_body=None, raw=False, extra_headers=None,
                  data=None, content_type=None):
    token = get_token(tenant)
    path = _resolve_path(path, user_hint)
    url = f"{GRAPH_BASE}{path}" if path.startswith("/") else f"{GRAPH_BASE}/{path}"
    headers = {"Authorization": f"Bearer {token}"}
    if content_type:
        headers["Content-Type"] = content_type
    elif json_body is not None:
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    resp = requests.request(method, url, headers=headers, params=params,
                            json=json_body, data=data)

    if raw:
        return resp
    if resp.status_code == 204:
        return {"status": "ok"}
    try:
        rdata = resp.json()
    except Exception:
        return {"error": f"HTTP {resp.status_code}", "body": resp.text}
    if resp.status_code >= 400:
        err = rdata.get("error", {})
        return {"error": err.get("message", f"HTTP {resp.status_code}"), "code": err.get("code")}
    return rdata


def graph_get(path, **kw):
    return graph_request("GET", path, **kw)

def graph_post(path, json_body=None, **kw):
    return graph_request("POST", path, json_body=json_body, **kw)

def graph_patch(path, json_body=None, **kw):
    return graph_request("PATCH", path, json_body=json_body, **kw)

def graph_put(path, **kw):
    return graph_request("PUT", path, **kw)

def graph_delete(path, **kw):
    return graph_request("DELETE", path, **kw)

def pp(data):
    print(json.dumps(data, indent=2, default=str))


# --- Attachment helpers ---

SMALL_FILE_LIMIT = 3 * 1024 * 1024  # 3 MB — Graph inline attachment limit


def attach_files_to_message(message_id, file_paths, tenant="karelin", user_hint="default"):
    """Attach local files to a draft message. Uses upload sessions for files >3MB."""
    import base64
    import mimetypes
    results = []
    for fpath in file_paths:
        fpath = os.path.expanduser(fpath)
        if not os.path.isfile(fpath):
            results.append({"file": fpath, "error": "File not found"})
            continue
        fname = os.path.basename(fpath)
        fsize = os.path.getsize(fpath)
        mime = mimetypes.guess_type(fpath)[0] or "application/octet-stream"
        if fsize <= SMALL_FILE_LIMIT:
            # Small file: inline base64 attachment
            with open(fpath, "rb") as f:
                content_bytes = base64.b64encode(f.read()).decode()
            att_body = {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": fname,
                "contentType": mime,
                "contentBytes": content_bytes,
            }
            r = graph_post(f"/me/messages/{message_id}/attachments",
                           json_body=att_body, tenant=tenant, user_hint=user_hint)
            results.append({"file": fname, "size": fsize, "method": "inline", "result": r})
        else:
            # Large file: upload session
            sess_body = {
                "AttachmentItem": {
                    "attachmentType": "file",
                    "name": fname,
                    "size": fsize,
                    "contentType": mime,
                }
            }
            sess = graph_post(f"/me/messages/{message_id}/attachments/createUploadSession",
                              json_body=sess_body, tenant=tenant, user_hint=user_hint)
            upload_url = sess.get("uploadUrl")
            if not upload_url:
                results.append({"file": fname, "error": "Failed to create upload session", "detail": sess})
                continue
            # Upload in 4MB chunks
            chunk_size = 4 * 1024 * 1024
            with open(fpath, "rb") as f:
                offset = 0
                while offset < fsize:
                    chunk = f.read(chunk_size)
                    end = offset + len(chunk) - 1
                    hdrs = {
                        "Content-Range": f"bytes {offset}-{end}/{fsize}",
                        "Content-Length": str(len(chunk)),
                    }
                    resp = requests.put(upload_url, headers=hdrs, data=chunk)
                    offset += len(chunk)
            results.append({"file": fname, "size": fsize, "method": "upload_session",
                            "status": resp.status_code})
    return results
