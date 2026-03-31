"""MCP tools for Obsidian vault access via the Local REST API plugin.

Tries multiple hosts in order until one responds. Each host runs the
Obsidian Local REST API plugin on port 27124 (HTTPS, self-signed cert).
"""

import json
import logging
import os
import requests
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

HOSTS = os.environ.get("OBSIDIAN_HOSTS", "alex-mac,alex-pc,alex-laptop").split(",")
PORT = int(os.environ.get("OBSIDIAN_PORT", "27123"))
SCHEME = os.environ.get("OBSIDIAN_SCHEME", "http")
API_KEY = os.environ.get("OBSIDIAN_API_KEY", "")

_active_host = None


def _try_request(method, path, params=None, json_body=None, data=None,
                 extra_headers=None, timeout=10):
    """Try each host until one responds."""
    global _active_host
    headers = {"Authorization": f"Bearer {API_KEY}"}
    if extra_headers:
        headers.update(extra_headers)

    # Try cached host first, then the rest
    hosts = [_active_host] + HOSTS if _active_host else list(HOSTS)
    seen = set()
    ordered = []
    for h in hosts:
        if h and h not in seen:
            seen.add(h)
            ordered.append(h)

    last_err = None
    for host in ordered:
        url = f"{SCHEME}://{host.strip()}:{PORT}{path}"
        try:
            resp = requests.request(method, url, headers=headers, params=params,
                                    json=json_body, data=data, verify=False,
                                    timeout=timeout)
            _active_host = host.strip()
            if resp.status_code == 204:
                return {"status": "ok"}
            try:
                return resp.json()
            except Exception:
                ct = resp.headers.get("Content-Type", "")
                if "text/" in ct:
                    return {"content": resp.text}
                return {"status": resp.status_code, "body": resp.text[:500]}
        except requests.exceptions.ConnectionError:
            last_err = f"Connection refused: {host.strip()}:{PORT}"
        except requests.exceptions.Timeout:
            last_err = f"Timeout: {host.strip()}:{PORT}"
        except Exception as e:
            last_err = f"{host.strip()}: {e}"

    _active_host = None
    return {"error": f"All hosts unreachable. Last: {last_err}",
            "hosts_tried": [h.strip() for h in ordered]}


# ── Tool Definitions ────────────────────────────────────────────────

_PATH = {"type": "string", "description": "Path relative to vault root (e.g. 'Notes/daily.md')"}
_QUERY = {"type": "string", "description": "Search query"}

TOOLS = [
    # --  Read  --
    {"name": "note_list", "description": "List files and folders at a path", "inputSchema": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Directory path (default: root)"}}
    }},
    {"name": "note_read", "description": "Read one note by path", "inputSchema": {
        "type": "object",
        "properties": {"path": _PATH},
        "required": ["path"]
    }},
    {"name": "note_search", "description": "Search notes by text query", "inputSchema": {
        "type": "object",
        "properties": {"query": _QUERY},
        "required": ["query"]
    }},
    {"name": "note_search_dql", "description": "Search notes with Dataview DQL", "inputSchema": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Dataview DQL query string"}},
        "required": ["query"]
    }},
    {"name": "note_tags", "description": "List tags in the vault", "inputSchema": {
        "type": "object",
        "properties": {}
    }},
    {"name": "note_active", "description": "Get the currently active note", "inputSchema": {
        "type": "object",
        "properties": {}
    }},
    {"name": "note_commands", "description": "List Obsidian commands", "inputSchema": {
        "type": "object",
        "properties": {}
    }},
    {"name": "note_status", "description": "Check Obsidian connection status", "inputSchema": {
        "type": "object",
        "properties": {}
    }},

    # --  Write  --
    {"name": "note_write", "description": "Create or overwrite a note", "inputSchema": {
        "type": "object",
        "properties": {
            "path": _PATH,
            "content": {"type": "string", "description": "File content (markdown)"}
        },
        "required": ["path", "content"]
    }},
    {"name": "note_append", "description": "Append text to a note", "inputSchema": {
        "type": "object",
        "properties": {
            "path": _PATH,
            "content": {"type": "string", "description": "Content to append"}
        },
        "required": ["path", "content"]
    }},
    {"name": "note_patch", "description": "Insert or replace content in a note section", "inputSchema": {
        "type": "object",
        "properties": {
            "path": _PATH,
            "content": {"type": "string", "description": "Content to insert"},
            "operation": {"type": "string", "description": "insert, append, prepend, or replace (default: append)"},
            "target_type": {"type": "string", "description": "heading, block-reference, or frontmatter-key"},
            "target": {"type": "string", "description": "The heading text, block ID, or frontmatter key to target"}
        },
        "required": ["path", "content", "target_type", "target"]
    }},
    {"name": "note_delete", "description": "Delete a note or folder", "inputSchema": {
        "type": "object",
        "properties": {"path": _PATH},
        "required": ["path"]
    }},
    {"name": "note_open", "description": "Open a note in Obsidian UI", "inputSchema": {
        "type": "object",
        "properties": {"path": _PATH},
        "required": ["path"]
    }},
    {"name": "note_command", "description": "Run an Obsidian command by ID", "inputSchema": {
        "type": "object",
        "properties": {"command_id": {"type": "string", "description": "Command ID to execute"}},
        "required": ["command_id"]
    }},

    # --  Periodic notes  --
    {"name": "note_daily", "description": "Get today's daily note", "inputSchema": {
        "type": "object",
        "properties": {}
    }},
    {"name": "note_daily_append", "description": "Append text to today's daily note", "inputSchema": {
        "type": "object",
        "properties": {"content": {"type": "string", "description": "Content to append"}},
        "required": ["content"]
    }},
]

# ── Annotations ─────────────────────────────────────────────────────

_RO  = {"readOnlyHint": True,  "destructiveHint": False, "openWorldHint": False}
_WR  = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}
_DEL = {"readOnlyHint": False, "destructiveHint": True,  "openWorldHint": True}

_READ_TOOLS = {
    "note_list", "note_read", "note_search", "note_search_dql",
    "note_tags", "note_active", "note_commands", "note_status",
    "note_daily",
}
_DESTRUCTIVE_TOOLS = {"note_delete"}

for _t in TOOLS:
    if _t["name"] in _READ_TOOLS:
        _t["annotations"] = _RO
    elif _t["name"] in _DESTRUCTIVE_TOOLS:
        _t["annotations"] = _DEL
    else:
        _t["annotations"] = _WR


# ── Handlers ────────────────────────────────────────────────────────

def _note_list(a):
    path = a.get("path", "/")
    if not path.startswith("/"):
        path = "/" + path
    return _try_request("GET", f"/vault{path}",
                        extra_headers={"Accept": "application/json"})

def _note_read(a):
    path = a["path"]
    if not path.startswith("/"):
        path = "/" + path
    return _try_request("GET", f"/vault{path}")

def _note_search(a):
    return _try_request("POST", "/search/simple/", params={"query": a["query"]},
                        extra_headers={"Accept": "application/json"})

def _note_search_dql(a):
    return _try_request("POST", "/search/",
                        json_body={"query": a["query"], "format": "dataview"},
                        extra_headers={"Accept": "application/json"})

def _note_tags(a):
    return _try_request("GET", "/tags/",
                        extra_headers={"Accept": "application/json"})

def _note_active(a):
    return _try_request("GET", "/active/")

def _note_commands(a):
    return _try_request("GET", "/commands/",
                        extra_headers={"Accept": "application/json"})

def _note_status(a):
    result = _try_request("GET", "/")
    if _active_host:
        result["active_host"] = _active_host
    result["configured_hosts"] = [h.strip() for h in HOSTS]
    return result

def _note_write(a):
    path = a["path"]
    if not path.startswith("/"):
        path = "/" + path
    return _try_request("PUT", f"/vault{path}",
                        data=a["content"].encode("utf-8"),
                        extra_headers={"Content-Type": "text/markdown"})

def _note_append(a):
    path = a["path"]
    if not path.startswith("/"):
        path = "/" + path
    return _try_request("POST", f"/vault{path}",
                        data=a["content"].encode("utf-8"),
                        extra_headers={"Content-Type": "text/markdown"})

def _note_patch(a):
    path = a["path"]
    if not path.startswith("/"):
        path = "/" + path
    hdrs = {
        "Content-Type": "text/markdown",
        "Operation": a.get("operation", "append"),
        "Target-Type": a["target_type"],
        "Target": a["target"],
    }
    return _try_request("PATCH", f"/vault{path}",
                        data=a["content"].encode("utf-8"),
                        extra_headers=hdrs)

def _note_delete(a):
    path = a["path"]
    if not path.startswith("/"):
        path = "/" + path
    return _try_request("DELETE", f"/vault{path}")

def _note_open(a):
    path = a["path"]
    if not path.startswith("/"):
        path = "/" + path
    return _try_request("POST", f"/open{path}")

def _note_command(a):
    return _try_request("POST", f"/commands/{a['command_id']}/")

def _note_daily(a):
    return _try_request("GET", "/periodic/daily/")

def _note_daily_append(a):
    return _try_request("POST", "/periodic/daily/",
                        data=a["content"].encode("utf-8"),
                        extra_headers={"Content-Type": "text/markdown"})


HANDLERS = {
    "note_list": _note_list, "note_read": _note_read,
    "note_search": _note_search, "note_search_dql": _note_search_dql,
    "note_tags": _note_tags, "note_active": _note_active,
    "note_commands": _note_commands, "note_status": _note_status,
    "note_write": _note_write, "note_append": _note_append,
    "note_patch": _note_patch, "note_delete": _note_delete,
    "note_open": _note_open, "note_command": _note_command,
    "note_daily": _note_daily, "note_daily_append": _note_daily_append,
}


def dispatch_tool(name, arguments):
    handler = HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")
    return handler(arguments)
