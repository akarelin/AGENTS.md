#!/usr/bin/env python3
"""
Graph API client for admin operations — application permissions (client credentials).
No user login needed. Uses beta endpoint.
"""

import json
import os
import sys
import msal
import requests

GRAPH_BASE = "https://graph.microsoft.com/beta"
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_tenant_config(tenant="karelin"):
    if os.environ.get("GRAPH_ADMIN_CLIENT_ID"):
        return {
            "tenant_id": os.environ["GRAPH_ADMIN_TENANT_ID"],
            "client_id": os.environ["GRAPH_ADMIN_CLIENT_ID"],
            "client_secret": os.environ["GRAPH_ADMIN_CLIENT_SECRET"],
        }
    tenants_file = os.path.join(SKILL_DIR, "tenants.json")
    if os.path.exists(tenants_file):
        with open(tenants_file) as f:
            return json.load(f).get(tenant, {})
    print(f"Error: No config for tenant '{tenant}'", file=sys.stderr)
    sys.exit(1)


_token_cache = {}

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
    else:
        print(f"Auth failed: {result.get('error_description', result)}", file=sys.stderr)
        sys.exit(1)


def graph_request(method, path, tenant="karelin", params=None, json_body=None, extra_headers=None):
    token = get_token(tenant)
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

def pp(data):
    print(json.dumps(data, indent=2, default=str))
