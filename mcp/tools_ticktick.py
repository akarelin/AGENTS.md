"""MCP tool definitions and handlers for TickTick API."""

import base64
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

# ── Config ────────────────────────────────────────────────────────────────────

OAUTH_BASE = "https://ticktick.com/oauth"
API_BASE = "https://api.ticktick.com/open/v1"

PRIORITY_MAP = {"none": 0, "low": 1, "medium": 3, "high": 5}
PRIORITY_REVERSE = {0: "none", 1: "low", 3: "medium", 5: "high"}

# Focus type codes per OpenAPI (/open/v1/focus): 0=Pomodoro, 1=Timing.
FOCUS_TYPE_MAP = {"pomo": 0, "pomodoro": 0, "timing": 1}
FOCUS_TYPE_REVERSE = {0: "pomo", 1: "timing"}
FOCUS_RANGE_MAX_DAYS = 30  # server clamps anything larger, document it explicitly

RETRY_DELAYS = [5, 15, 30, 60]
MAX_RETRIES = 4

# Credentials from env or fallback
_CLIENT_ID = os.environ.get("TICKTICK_CLIENT_ID", "")
_CLIENT_SECRET = os.environ.get("TICKTICK_CLIENT_SECRET", "")
_ACCESS_TOKEN = os.environ.get("TICKTICK_ACCESS_TOKEN", "")
_REFRESH_TOKEN = os.environ.get("TICKTICK_REFRESH_TOKEN", "")


def _get_token() -> str:
    if _ACCESS_TOKEN:
        return _ACCESS_TOKEN
    raise RuntimeError("TICKTICK_ACCESS_TOKEN not set. Configure TickTick credentials.")


def _api(method: str, endpoint: str, retry: int = 0, **kwargs):
    token = _get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", **kwargs.pop("headers", {})}
    resp = requests.request(method, f"{API_BASE}{endpoint}", headers=headers, **kwargs)
    if not resp.ok:
        txt = resp.text
        is_rate = resp.status_code == 429 or (resp.status_code == 500 and "exceed_query_limit" in txt)
        if is_rate and retry < MAX_RETRIES:
            time.sleep(RETRY_DELAYS[retry])
            return _api(method, endpoint, retry + 1, **kwargs)
        raise RuntimeError(f"TickTick API error {resp.status_code}: {txt or resp.reason}")
    return resp.json() if resp.text else {}


# ── Date helpers ──────────────────────────────────────────────────────────────

def _parse_due(s: str) -> str:
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
        raise ValueError(f"Invalid date: {s!r}")


def _parse_range_point(s: str, *, end: bool) -> datetime:
    """Resolve a natural-language date string to a datetime.

    `end=True` resolves bare days to end-of-day, `end=False` resolves to start-of-day.
    Accepted forms: today, yesterday, now, this week, last week, N days ago, ISO 8601.
    """
    lower = s.lower().strip()
    now = datetime.now()
    sod = lambda d: d.replace(hour=0, minute=0, second=0, microsecond=0)
    eod = lambda d: d.replace(hour=23, minute=59, second=59, microsecond=0)
    boundary = eod if end else sod
    if lower == "now":
        return now.replace(microsecond=0)
    if lower == "today":
        return boundary(now)
    if lower == "yesterday":
        return boundary(now - timedelta(days=1))
    if lower in ("this week", "week"):
        return boundary(now - timedelta(days=now.weekday()))
    if lower == "last week":
        return boundary(now - timedelta(days=now.weekday() + 7))
    m = re.match(r"^(\d+) days? ago$", lower)
    if m:
        return boundary(now - timedelta(days=int(m.group(1))))
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        raise ValueError(f"Invalid date: {s!r}")


def _focus_fmt(dt: datetime) -> str:
    # /open/v1/focus expects yyyy-MM-dd'T'HH:mm:ssZ with a numeric timezone offset.
    tz = dt.strftime("%z") or "+0000"
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + tz


def _focus_type_code(s: str) -> int:
    code = FOCUS_TYPE_MAP.get(s.lower().strip())
    if code is None:
        raise ValueError(f"Invalid focus type {s!r}. Use 'pomo' or 'timing'.")
    return code


# ── Tool Definitions ──────────────────────────────────────────────────────────

TOOLS = [
    {"name": "tt_lists", "description": "List all TickTick projects/lists", "inputSchema": {
        "type": "object", "properties": {}
    }},
    {"name": "tt_tasks", "description": "List tasks, optionally filtered by project and status", "inputSchema": {
        "type": "object", "properties": {
            "list": {"type": "string", "description": "Project name or ID to filter"},
            "status": {"type": "string", "enum": ["pending", "completed"], "description": "Filter by status"},
        }
    }},
    {"name": "tt_create", "description": "Create a new task in TickTick", "inputSchema": {
        "type": "object", "properties": {
            "title": {"type": "string", "description": "Task title"},
            "list": {"type": "string", "description": "Project name or ID"},
            "content": {"type": "string", "description": "Task description"},
            "priority": {"type": "string", "enum": ["none", "low", "medium", "high"]},
            "due": {"type": "string", "description": "Due date: today, tomorrow, in N days, next monday, or ISO date"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags"},
        },
        "required": ["title", "list"]
    }},
    {"name": "tt_update", "description": "Update an existing TickTick task", "inputSchema": {
        "type": "object", "properties": {
            "task": {"type": "string", "description": "Task title or ID"},
            "list": {"type": "string", "description": "Project name or ID to narrow search"},
            "title": {"type": "string", "description": "New title"},
            "content": {"type": "string", "description": "New description"},
            "priority": {"type": "string", "enum": ["none", "low", "medium", "high"]},
            "due": {"type": "string", "description": "New due date"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["task"]
    }},
    {"name": "tt_complete", "description": "Mark a TickTick task as completed", "inputSchema": {
        "type": "object", "properties": {
            "task": {"type": "string", "description": "Task title or ID"},
            "list": {"type": "string", "description": "Project name or ID to narrow search"},
        },
        "required": ["task"]
    }},
    {"name": "tt_abandon", "description": "Mark a TickTick task as won't do", "inputSchema": {
        "type": "object", "properties": {
            "task": {"type": "string", "description": "Task title or ID"},
            "list": {"type": "string", "description": "Project name or ID to narrow search"},
        },
        "required": ["task"]
    }},
    {"name": "tt_focus_list", "description": "List TickTick focus / time-tracking sessions in a date range (max 30 days; longer ranges are clamped server-side). Type defaults to 'all' which merges Pomodoro and Timing entries.", "inputSchema": {
        "type": "object", "properties": {
            "from": {"type": "string", "description": "Range start: 'today', 'yesterday', 'this week', 'last week', 'N days ago', or ISO 8601. Defaults to 7 days ago."},
            "to": {"type": "string", "description": "Range end: 'today', 'now', or ISO 8601. Defaults to 'now'."},
            "type": {"type": "string", "enum": ["pomo", "timing", "all"], "description": "Session type filter. 'pomo' = Pomodoro, 'timing' = stopwatch, 'all' = both. Default 'all'."},
        }
    }},
    {"name": "tt_focus_get", "description": "Get a single TickTick focus / time-tracking session by ID", "inputSchema": {
        "type": "object", "properties": {
            "id": {"type": "string", "description": "Focus session ID"},
            "type": {"type": "string", "enum": ["pomo", "timing"], "description": "Session type. Required by the TickTick API."},
        },
        "required": ["id", "type"]
    }},
    {"name": "tt_focus_delete", "description": "Delete a TickTick focus / time-tracking session by ID", "inputSchema": {
        "type": "object", "properties": {
            "id": {"type": "string", "description": "Focus session ID"},
            "type": {"type": "string", "enum": ["pomo", "timing"], "description": "Session type. Required by the TickTick API."},
        },
        "required": ["id", "type"]
    }},
]

_RO = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}
_WR = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}
_DEL = {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": True}

_READ_TOOLS = {"tt_lists", "tt_tasks", "tt_focus_list", "tt_focus_get"}
_DESTRUCTIVE_TOOLS = {"tt_focus_delete"}
for _t in TOOLS:
    if _t["name"] in _DESTRUCTIVE_TOOLS:
        _t["annotations"] = _DEL
    elif _t["name"] in _READ_TOOLS:
        _t["annotations"] = _RO
    else:
        _t["annotations"] = _WR


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_project(name):
    lower = name.lower()
    return next((p for p in _api("GET", "/project") if p["name"].lower() == lower or p["id"] == name), None)


def _find_task(title, project_name=None):
    projects = _api("GET", "/project")
    if project_name:
        projects = [p for p in projects if p["name"].lower() == project_name.lower() or p["id"] == project_name]
    is_id = bool(re.fullmatch(r"[a-f0-9]{24}", title, re.IGNORECASE))
    matches = []
    for p in projects:
        try:
            data = _api("GET", f"/project/{p['id']}/data")
            for t in data.get("tasks") or []:
                if t["title"].lower() == title.lower() or t["id"] == title:
                    matches.append({"task": t, "projectId": p["id"], "projectName": p["name"]})
        except RuntimeError:
            continue
    if not matches:
        return None
    if is_id or len(matches) == 1:
        return matches[0]
    raise RuntimeError(f"Multiple tasks match '{title}'. Use task ID.")


# ── Dispatcher ────────────────────────────────────────────────────────────────

def dispatch(name: str, args: dict):
    if name == "tt_lists":
        projects = _api("GET", "/project")
        return [{"id": p["id"], "name": p["name"], "color": p.get("color")} for p in projects]

    if name == "tt_tasks":
        projects = _api("GET", "/project")
        pmap = {p["id"]: p["name"] for p in projects}
        search = projects
        if args.get("list"):
            p = _find_project(args["list"])
            if not p:
                raise RuntimeError(f"Project not found: {args['list']}")
            search = [p]
        tasks = []
        for p in search:
            try:
                data = _api("GET", f"/project/{p['id']}/data")
                for t in data.get("tasks") or []:
                    t["projectName"] = pmap.get(t.get("projectId", ""), "")
                    tasks.append(t)
            except RuntimeError:
                continue
        status = args.get("status")
        if status == "pending":
            tasks = [t for t in tasks if t.get("status") != 2]
        elif status == "completed":
            tasks = [t for t in tasks if t.get("status") == 2]
        return [{"id": t["id"], "title": t.get("title"), "project": t.get("projectName"),
                 "priority": PRIORITY_REVERSE.get(t.get("priority", 0), "none"),
                 "due": t.get("dueDate"), "tags": t.get("tags", []),
                 "status": "completed" if t.get("status") == 2 else "pending"} for t in tasks]

    if name == "tt_create":
        p = _find_project(args["list"])
        if not p:
            raise RuntimeError(f"Project not found: {args['list']}")
        payload = {"title": args["title"], "projectId": p["id"]}
        if args.get("content"):
            payload["content"] = args["content"]
        if args.get("priority"):
            payload["priority"] = PRIORITY_MAP.get(args["priority"], 0)
        if args.get("due"):
            payload["dueDate"] = _parse_due(args["due"])
        if args.get("tags"):
            payload["tags"] = args["tags"]
        result = _api("POST", "/task", json=payload)
        return {"id": result["id"], "title": result["title"], "project": p["name"]}

    if name == "tt_update":
        found = _find_task(args["task"], args.get("list"))
        if not found:
            raise RuntimeError(f"Task not found: {args['task']}")
        payload = {"id": found["task"]["id"], "projectId": found["projectId"]}
        if args.get("title"):
            payload["title"] = args["title"]
        if args.get("content"):
            payload["content"] = args["content"]
        if args.get("priority"):
            payload["priority"] = PRIORITY_MAP.get(args["priority"], 0)
        if args.get("due"):
            payload["dueDate"] = _parse_due(args["due"])
        if args.get("tags"):
            payload["tags"] = args["tags"]
        result = _api("POST", f"/task/{found['task']['id']}", json=payload)
        return {"id": result.get("id"), "title": result.get("title"), "updated": True}

    if name == "tt_complete":
        found = _find_task(args["task"], args.get("list"))
        if not found:
            raise RuntimeError(f"Task not found: {args['task']}")
        _api("POST", f"/project/{found['projectId']}/task/{found['task']['id']}/complete")
        return {"id": found["task"]["id"], "title": found["task"]["title"], "completed": True}

    if name == "tt_abandon":
        found = _find_task(args["task"], args.get("list"))
        if not found:
            raise RuntimeError(f"Task not found: {args['task']}")
        t = found["task"]
        _api("POST", f"/task/{t['id']}", json={"id": t["id"], "projectId": found["projectId"], "status": -1})
        return {"id": t["id"], "title": t["title"], "abandoned": True}

    if name == "tt_focus_list":
        end = _parse_range_point(args.get("to") or "now", end=True)
        start = _parse_range_point(args.get("from") or f"{FOCUS_RANGE_MAX_DAYS - 23} days ago", end=False)
        if (end - start).days > FOCUS_RANGE_MAX_DAYS:
            start = end - timedelta(days=FOCUS_RANGE_MAX_DAYS)
        type_arg = (args.get("type") or "all").lower().strip()
        codes = [0, 1] if type_arg == "all" else [_focus_type_code(type_arg)]
        params_base = {"from": _focus_fmt(start), "to": _focus_fmt(end)}
        sessions = []
        for code in codes:
            entries = _api("GET", "/focus", params={**params_base, "type": code}) or []
            for e in entries:
                e["_type"] = FOCUS_TYPE_REVERSE.get(code, str(code))
                sessions.append(e)
        sessions.sort(key=lambda e: e.get("startTime") or "")
        return [{
            "id": e.get("id"),
            "type": e.get("_type"),
            "taskId": e.get("taskId"),
            "startTime": e.get("startTime"),
            "endTime": e.get("endTime"),
            "duration": e.get("duration"),
            "note": e.get("note"),
        } for e in sessions]

    if name == "tt_focus_get":
        code = _focus_type_code(args["type"])
        e = _api("GET", f"/focus/{args['id']}", params={"type": code})
        return {
            "id": e.get("id"),
            "type": FOCUS_TYPE_REVERSE.get(code, str(code)),
            "taskId": e.get("taskId"),
            "startTime": e.get("startTime"),
            "endTime": e.get("endTime"),
            "duration": e.get("duration"),
            "note": e.get("note"),
        }

    if name == "tt_focus_delete":
        code = _focus_type_code(args["type"])
        _api("DELETE", f"/focus/{args['id']}", params={"type": code})
        return {"id": args["id"], "type": args["type"].lower().strip(), "deleted": True}

    raise RuntimeError(f"Unknown tool: {name}")
