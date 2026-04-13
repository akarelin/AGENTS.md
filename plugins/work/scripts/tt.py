#!/usr/bin/env python3
"""
TickTick CLI — task and project management via TickTick Open API v1.

All secrets from Azure Key Vault via gppu:
  - ticktick-client-id       OAuth2 client ID
  - ticktick-client-secret   OAuth2 client secret
  - ticktick-token           OAuth2 token JSON (access_token, refresh_token, etc.)
"""

import argparse
import base64
import json
import os
import re
import secrets
import sys
import threading
import time
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from gppu import resolve_secret

OAUTH_BASE = "https://ticktick.com/oauth"
API_BASE = "https://api.ticktick.com/open/v1"

PRIORITY_MAP = {"none": 0, "low": 1, "medium": 3, "high": 5}
PRIORITY_REVERSE = {0: "none", 1: "low", 3: "medium", 5: "high"}

RETRY_DELAYS = [5, 15, 30, 60]
MAX_RETRIES = 4

# Key Vault secret names
KV_CLIENT_ID = "ticktick-client-id"
KV_CLIENT_SECRET = "ticktick-client-secret"
KV_TOKEN = "ticktick-token"


# ── Auth ──────────────────────────────────────────────────────────────────────

def _load_token():
    """Load token JSON from Key Vault."""
    try:
        raw = resolve_secret(KV_TOKEN)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def _save_token(token_data: dict):
    """Save token JSON to Key Vault."""
    from gppu import set_secret
    set_secret(KV_TOKEN, json.dumps(token_data))


def get_token() -> str:
    """Get a valid access token, refreshing if needed."""
    token_data = _load_token()
    if not token_data or not token_data.get("access_token"):
        print("Error: No TickTick token. Run: tt.py auth", file=sys.stderr)
        sys.exit(1)

    expiry = token_data.get("token_expiry")
    if expiry and time.time() > expiry - 300:
        if token_data.get("refresh_token"):
            return _refresh(token_data)
        print("Error: Token expired. Run: tt.py auth", file=sys.stderr)
        sys.exit(1)

    return token_data["access_token"]


def _refresh(token_data: dict) -> str:
    client_id = resolve_secret(KV_CLIENT_ID)
    client_secret = resolve_secret(KV_CLIENT_SECRET)
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(f"{OAUTH_BASE}/token", headers={
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/x-www-form-urlencoded",
    }, data={"grant_type": "refresh_token", "refresh_token": token_data["refresh_token"]})
    if not resp.ok:
        print(f"Error: Token refresh failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    token_data["access_token"] = data["access_token"]
    if "refresh_token" in data:
        token_data["refresh_token"] = data["refresh_token"]
    token_data["token_expiry"] = time.time() + data["expires_in"]
    _save_token(token_data)
    return token_data["access_token"]


# ── API client ────────────────────────────────────────────────────────────────

def tt_request(method, endpoint, retry=0, **kwargs):
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", **kwargs.pop("headers", {})}
    resp = requests.request(method, f"{API_BASE}{endpoint}", headers=headers, **kwargs)
    if not resp.ok:
        txt = resp.text
        is_rate = resp.status_code == 429 or (resp.status_code == 500 and "exceed_query_limit" in txt)
        if is_rate and retry < MAX_RETRIES:
            wait = RETRY_DELAYS[retry]
            print(f"Rate limited, waiting {wait}s (retry {retry+1}/{MAX_RETRIES})...", file=sys.stderr)
            time.sleep(wait)
            return tt_request(method, endpoint, retry + 1, **kwargs)
        if resp.status_code == 401:
            print("Error: Auth expired. Run: tt.py auth", file=sys.stderr)
            sys.exit(1)
        return {"error": f"API error {resp.status_code}", "body": txt or resp.reason}
    return resp.json() if resp.text else {"status": "ok"}


def tt_get(path):
    return tt_request("GET", path)


def tt_post(path, json_body=None):
    return tt_request("POST", path, json=json_body)


def pp(data):
    print(json.dumps(data, indent=2, default=str))


# ── Helpers ───────────────────────────────────────────────────────────────────

def find_project(name):
    projects = tt_get("/project")
    if isinstance(projects, dict) and "error" in projects:
        return None
    lower = name.lower()
    return next((p for p in projects if p["name"].lower() == lower or p["id"] == name), None)


def find_task(title, project_name=None):
    projects = tt_get("/project")
    if isinstance(projects, dict) and "error" in projects:
        return None
    if project_name:
        projects = [p for p in projects if p["name"].lower() == project_name.lower() or p["id"] == project_name]
    is_id = bool(re.fullmatch(r"[a-f0-9]{24}", title, re.IGNORECASE))
    matches = []
    for p in projects:
        data = tt_get(f"/project/{p['id']}/data")
        if isinstance(data, dict) and "error" in data:
            continue
        for t in data.get("tasks") or []:
            if t["title"].lower() == title.lower() or t["id"] == title:
                matches.append({"task": t, "projectId": p["id"], "projectName": p["name"]})
    if not matches:
        return None
    if is_id or len(matches) == 1:
        return matches[0]
    lines = "\n".join(f"  [{m['task']['id'][:8]}] \"{m['task']['title']}\" in \"{m['projectName']}\"" for m in matches)
    print(f"Multiple matches:\n{lines}\nUse task ID instead.", file=sys.stderr)
    sys.exit(1)


def parse_due(s):
    lower = s.lower().strip()
    now = datetime.now()
    def eod(d):
        return d.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%dT%H:%M:%S.000+0000")
    if lower == "today":
        return eod(now)
    if lower == "tomorrow":
        return eod(now + timedelta(days=1))
    m = re.match(r"^in (\d+) days?$", lower)
    if m:
        return eod(now + timedelta(days=int(m.group(1))))
    days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    m = re.match(r"^next (" + "|".join(days) + ")$", lower)
    if m:
        target = (days.index(m.group(1)) - 1) % 7
        delta = (target - now.weekday()) % 7 or 7
        return eod(now + timedelta(days=delta))
    try:
        return datetime.fromisoformat(s).strftime("%Y-%m-%dT%H:%M:%S.000+0000")
    except ValueError:
        print(f"Error: Invalid date: {s!r}. Try 'today', 'tomorrow', 'in 3 days', 'next monday', or ISO.", file=sys.stderr)
        sys.exit(1)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_auth(args):
    if args.status:
        token_data = _load_token()
        if token_data and token_data.get("access_token"):
            print("Authenticated with TickTick")
        else:
            print("Not authenticated")
        return

    if args.logout:
        _save_token({})
        print("Logged out.")
        return

    client_id = resolve_secret(KV_CLIENT_ID)
    client_secret = resolve_secret(KV_CLIENT_SECRET)
    if not client_id or not client_secret:
        print("Error: ticktick-client-id and ticktick-client-secret must be in Key Vault.", file=sys.stderr)
        sys.exit(1)

    redirect_uri = "http://localhost:8080"
    state = f"tt-{secrets.token_hex(16)}"
    auth_url = f"{OAUTH_BASE}/authorize?" + urlencode({
        "scope": "tasks:read tasks:write",
        "client_id": client_id,
        "state": state,
        "redirect_uri": redirect_uri,
        "response_type": "code",
    })

    if args.manual:
        print(f"\nOpen this URL:\n{auth_url}\n")
        print("After authorizing, paste the full redirect URL:")
        redirect_url = input("> ").strip()
        params = parse_qs(urlparse(redirect_url).query)
        if params.get("state", [None])[0] != state:
            print("State mismatch.", file=sys.stderr)
            sys.exit(1)
        code = params.get("code", [None])[0]
        if not code:
            print("No code in URL.", file=sys.stderr)
            sys.exit(1)
    else:
        result = {"code": None, "error": None}
        event = threading.Event()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                params = parse_qs(urlparse(self.path).query)
                if params.get("state", [None])[0] != state:
                    self._reply(400, "Invalid state")
                    result["error"] = "Invalid state"
                elif params.get("error"):
                    self._reply(400, f"Error: {params['error'][0]}")
                    result["error"] = params["error"][0]
                elif params.get("code"):
                    self._reply(200, "Authenticated! Close this window.")
                    result["code"] = params["code"][0]
                event.set()

            def _reply(self, status, msg):
                self.send_response(status)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(f"<html><body><h1>{msg}</h1></body></html>".encode())

            def log_message(self, *a):
                pass

        server = HTTPServer(("127.0.0.1", 8080), Handler)
        print(f"\nOpening browser...\nIf it doesn't open, visit:\n{auth_url}\n")
        webbrowser.open(auth_url)
        t = threading.Thread(target=server.handle_request, daemon=True)
        t.start()
        if not event.wait(timeout=300):
            print("Timeout.", file=sys.stderr)
            sys.exit(1)
        server.server_close()
        if result["error"]:
            print(f"Auth failed: {result['error']}", file=sys.stderr)
            sys.exit(1)
        code = result["code"]

    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(f"{OAUTH_BASE}/token", headers={
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/x-www-form-urlencoded",
    }, data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri})
    if not resp.ok:
        print(f"Token exchange failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    _save_token({
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "token_expiry": time.time() + data["expires_in"],
    })
    print("Authentication successful! Token saved to Key Vault.")


def cmd_lists(args):
    pp(tt_get("/project"))


def cmd_list_create(args):
    body = {"name": args.name}
    if args.color:
        body["color"] = args.color
    pp(tt_post("/project", body))


def cmd_list_update(args):
    p = find_project(args.name)
    if not p:
        print(f"Project not found: {args.name}", file=sys.stderr)
        sys.exit(1)
    body = {}
    if args.new_name:
        body["name"] = args.new_name
    if args.color:
        body["color"] = args.color
    pp(tt_post(f"/project/{p['id']}", body))


def cmd_tasks(args):
    projects = tt_get("/project")
    if isinstance(projects, dict) and "error" in projects:
        pp(projects)
        return
    pmap = {p["id"]: p["name"] for p in projects}
    search = projects
    if args.list:
        p = find_project(args.list)
        if not p:
            print(f"Project not found: {args.list}", file=sys.stderr)
            sys.exit(1)
        search = [p]

    tasks = []
    for p in search:
        data = tt_get(f"/project/{p['id']}/data")
        if isinstance(data, dict) and "error" in data:
            continue
        for t in data.get("tasks") or []:
            t["projectName"] = pmap.get(t.get("projectId", ""), "")
            tasks.append(t)

    if args.status == "pending":
        tasks = [t for t in tasks if t.get("status") != 2]
    elif args.status == "completed":
        tasks = [t for t in tasks if t.get("status") == 2]
    pp(tasks)


def cmd_task_create(args):
    p = find_project(args.list)
    if not p:
        print(f"Project not found: {args.list}", file=sys.stderr)
        sys.exit(1)
    payload = {"title": args.title, "projectId": p["id"]}
    if args.content:
        payload["content"] = args.content
    if args.priority:
        payload["priority"] = PRIORITY_MAP[args.priority]
    if args.due:
        payload["dueDate"] = parse_due(args.due)
    if args.tag:
        payload["tags"] = args.tag
    pp(tt_post("/task", payload))


def cmd_task_update(args):
    found = find_task(args.title, args.list)
    if not found:
        print(f"Task not found: {args.title}", file=sys.stderr)
        sys.exit(1)
    payload = {"id": found["task"]["id"], "projectId": found["projectId"]}
    if args.content:
        payload["content"] = args.content
    if args.priority:
        payload["priority"] = PRIORITY_MAP[args.priority]
    if args.due:
        payload["dueDate"] = parse_due(args.due)
    if args.tag:
        payload["tags"] = args.tag
    pp(tt_post(f"/task/{found['task']['id']}", payload))


def cmd_complete(args):
    found = find_task(args.task, args.list)
    if not found:
        print(f"Task not found: {args.task}", file=sys.stderr)
        sys.exit(1)
    pp(tt_post(f"/project/{found['projectId']}/task/{found['task']['id']}/complete"))


def cmd_abandon(args):
    found = find_task(args.task, args.list)
    if not found:
        print(f"Task not found: {args.task}", file=sys.stderr)
        sys.exit(1)
    t = found["task"]
    pp(tt_post(f"/task/{t['id']}", {"id": t["id"], "projectId": found["projectId"], "status": -1}))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(prog="tt", description="TickTick CLI")
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    a = sub.add_parser("auth", help="Authenticate")
    a.add_argument("--manual", action="store_true")
    a.add_argument("--logout", action="store_true")
    a.add_argument("--status", action="store_true")
    a.set_defaults(func=cmd_auth)

    t = sub.add_parser("tasks", help="List tasks")
    t.add_argument("-l", "--list")
    t.add_argument("-s", "--status", choices=["pending", "completed"])
    t.set_defaults(func=cmd_tasks)

    tk = sub.add_parser("task", help="Create/update task")
    tk.add_argument("title")
    tk.add_argument("-l", "--list")
    tk.add_argument("-c", "--content")
    tk.add_argument("-p", "--priority", choices=["none", "low", "medium", "high"])
    tk.add_argument("-d", "--due")
    tk.add_argument("-t", "--tag", nargs="+")
    tk.add_argument("-u", "--update", action="store_true")
    tk.set_defaults(func=lambda args: cmd_task_update(args) if args.update else cmd_task_create(args))

    c = sub.add_parser("complete", help="Complete task")
    c.add_argument("task")
    c.add_argument("-l", "--list")
    c.set_defaults(func=cmd_complete)

    ab = sub.add_parser("abandon", help="Abandon task")
    ab.add_argument("task")
    ab.add_argument("-l", "--list")
    ab.set_defaults(func=cmd_abandon)

    ls = sub.add_parser("lists", help="List projects")
    ls.set_defaults(func=cmd_lists)

    li = sub.add_parser("list", help="Create/update project")
    li.add_argument("name")
    li.add_argument("-c", "--color")
    li.add_argument("-u", "--update", action="store_true")
    li.add_argument("-n", "--new-name", dest="new_name")
    li.set_defaults(func=lambda args: cmd_list_update(args) if args.update else cmd_list_create(args))

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
