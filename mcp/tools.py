"""MCP tool definitions and handlers for M365 Graph API."""

from datetime import datetime, timezone
from graph_client import graph_get, graph_post, graph_patch, graph_delete


# ── Tool Definitions ────────────────────────────────────────────────

_U = {"type": "string", "description": "User hint: alex or irina (default: alex)"}
_TOP = {"type": "integer", "description": "Max results to return"}

TOOLS = [
    # --  Mail  --
    {"name": "mail_list", "description": "List emails", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "top": _TOP, "folder": {"type": "string", "description": "Mail folder ID"}}
    }},
    {"name": "mail_read", "description": "Read email", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "message_id": {"type": "string", "description": "Message ID"}},
        "required": ["message_id"]
    }},
    {"name": "mail_search", "description": "Search emails", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "query": {"type": "string", "description": "Search query"}, "top": _TOP},
        "required": ["query"]
    }},
    {"name": "mail_send", "description": "Send email", "inputSchema": {
        "type": "object",
        "properties": {
            "user": _U,
            "to": {"type": "string", "description": "Comma-separated recipient email addresses"},
            "subject": {"type": "string", "description": "Email subject"},
            "body": {"type": "string", "description": "Email body text"},
            "cc": {"type": "string", "description": "Comma-separated CC email addresses"},
            "html": {"type": "boolean", "description": "Send body as HTML (default false)"}
        },
        "required": ["to", "subject", "body"]
    }},
    {"name": "mail_draft", "description": "Create draft email", "inputSchema": {
        "type": "object",
        "properties": {
            "user": _U,
            "to": {"type": "string", "description": "Comma-separated recipient email addresses"},
            "subject": {"type": "string", "description": "Email subject"},
            "body": {"type": "string", "description": "Email body text"}
        },
        "required": ["to", "subject", "body"]
    }},
    {"name": "mail_reply", "description": "Reply to email", "inputSchema": {
        "type": "object",
        "properties": {
            "user": _U,
            "message_id": {"type": "string", "description": "Message ID to reply to"},
            "body": {"type": "string", "description": "Reply body text"}
        },
        "required": ["message_id", "body"]
    }},
    {"name": "mail_folders", "description": "List mail folders", "inputSchema": {
        "type": "object",
        "properties": {"user": _U}
    }},

    # --  Calendar  --
    {"name": "cal_list", "description": "List calendar events", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "top": _TOP}
    }},
    {"name": "cal_today", "description": "Get today's events", "inputSchema": {
        "type": "object",
        "properties": {"user": _U}
    }},
    {"name": "cal_search", "description": "Search calendar events", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "query": {"type": "string", "description": "Search query"}, "top": _TOP},
        "required": ["query"]
    }},
    {"name": "cal_create", "description": "Create calendar event", "inputSchema": {
        "type": "object",
        "properties": {
            "user": _U,
            "subject": {"type": "string", "description": "Event subject/title"},
            "start": {"type": "string", "description": "Start datetime (ISO 8601, e.g. 2025-03-15T09:00:00)"},
            "end": {"type": "string", "description": "End datetime (ISO 8601, e.g. 2025-03-15T10:00:00)"},
            "attendees": {"type": "string", "description": "Comma-separated attendee email addresses"},
            "online": {"type": "boolean", "description": "Create as Teams online meeting"},
            "tz": {"type": "string", "description": "Timezone (default: America/Los_Angeles)"}
        },
        "required": ["subject", "start", "end"]
    }},
    {"name": "cal_delete", "description": "Delete calendar event", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "event_id": {"type": "string", "description": "Event ID"}},
        "required": ["event_id"]
    }},

    # --  Chat (Teams)  --
    {"name": "chat_list", "description": "List Teams chats", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "top": _TOP}
    }},
    {"name": "chat_messages", "description": "Get chat messages", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "chat_id": {"type": "string", "description": "Chat ID"}, "top": _TOP},
        "required": ["chat_id"]
    }},
    {"name": "chat_send", "description": "Send chat message", "inputSchema": {
        "type": "object",
        "properties": {
            "user": _U,
            "chat_id": {"type": "string", "description": "Chat ID"},
            "message": {"type": "string", "description": "Message text"}
        },
        "required": ["chat_id", "message"]
    }},
    {"name": "chat_search", "description": "Search chat messages", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "query": {"type": "string", "description": "Search query"}, "top": _TOP},
        "required": ["query"]
    }},

    # --  Channel (Teams)  --
    {"name": "channel_list", "description": "List channels", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "team_id": {"type": "string", "description": "Team ID"}},
        "required": ["team_id"]
    }},
    {"name": "channel_messages", "description": "Get channel messages", "inputSchema": {
        "type": "object",
        "properties": {
            "user": _U,
            "team_id": {"type": "string", "description": "Team ID"},
            "channel_id": {"type": "string", "description": "Channel ID"},
            "top": _TOP
        },
        "required": ["team_id", "channel_id"]
    }},
    {"name": "channel_send", "description": "Send channel message", "inputSchema": {
        "type": "object",
        "properties": {
            "user": _U,
            "team_id": {"type": "string", "description": "Team ID"},
            "channel_id": {"type": "string", "description": "Channel ID"},
            "message": {"type": "string", "description": "Message text"}
        },
        "required": ["team_id", "channel_id", "message"]
    }},

    # --  Files (OneDrive)  --
    {"name": "files_list", "description": "List files", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "path": {"type": "string", "description": "Folder path (default: root)"}}
    }},
    {"name": "files_search", "description": "Search files", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "query": {"type": "string", "description": "Search query"}},
        "required": ["query"]
    }},

    # --  Tasks (To Do)  --
    {"name": "tasks_lists", "description": "List task lists", "inputSchema": {
        "type": "object",
        "properties": {"user": _U}
    }},
    {"name": "tasks_list", "description": "List tasks", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "list_id": {"type": "string", "description": "Task list ID"}},
        "required": ["list_id"]
    }},
    {"name": "tasks_create", "description": "Create task", "inputSchema": {
        "type": "object",
        "properties": {
            "user": _U,
            "list_id": {"type": "string", "description": "Task list ID"},
            "title": {"type": "string", "description": "Task title"},
            "due": {"type": "string", "description": "Due date (YYYY-MM-DD)"},
            "body": {"type": "string", "description": "Task body/notes"}
        },
        "required": ["list_id", "title"]
    }},
    {"name": "tasks_complete", "description": "Complete task", "inputSchema": {
        "type": "object",
        "properties": {
            "user": _U,
            "list_id": {"type": "string", "description": "Task list ID"},
            "task_id": {"type": "string", "description": "Task ID"}
        },
        "required": ["list_id", "task_id"]
    }},

    # --  Contacts  --
    {"name": "contacts_list", "description": "List contacts", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "top": _TOP}
    }},
    {"name": "contacts_search", "description": "Search contacts", "inputSchema": {
        "type": "object",
        "properties": {"user": _U, "query": {"type": "string", "description": "Search query"}},
        "required": ["query"]
    }},

    # --  Notes (OneNote)  --
    {"name": "notes_notebooks", "description": "List notebooks", "inputSchema": {
        "type": "object",
        "properties": {"user": _U}
    }},

    # --  Presence  --
    {"name": "presence_get", "description": "Get presence", "inputSchema": {
        "type": "object",
        "properties": {"user": _U}
    }},
    {"name": "presence_set", "description": "Set presence", "inputSchema": {
        "type": "object",
        "properties": {
            "user": _U,
            "availability": {"type": "string", "description": "Available, Busy, DoNotDisturb, Away, or Offline"},
            "activity": {"type": "string", "description": "Activity label (defaults to availability value)"}
        },
        "required": ["availability"]
    }},

    # --  Search  --
    {"name": "search", "description": "Search across M365", "inputSchema": {
        "type": "object",
        "properties": {
            "user": _U,
            "query": {"type": "string", "description": "Search query"},
            "types": {"type": "string", "description": "Comma-separated entity types: message,driveItem,event,chatMessage,site,list,listItem"},
            "top": _TOP
        },
        "required": ["query"]
    }},
]

# ── Annotations ─────────────────────────────────────────────────────

_RO  = {"readOnlyHint": True,  "destructiveHint": False, "openWorldHint": False}
_WR  = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}
_DEL = {"readOnlyHint": False, "destructiveHint": True,  "openWorldHint": True}

_READ_TOOLS = {
    "mail_list", "mail_read", "mail_search", "mail_folders",
    "cal_list", "cal_today", "cal_search",
    "chat_list", "chat_messages", "chat_search",
    "channel_list", "channel_messages",
    "files_list", "files_search",
    "tasks_lists", "tasks_list",
    "contacts_list", "contacts_search",
    "notes_notebooks",
    "presence_get",
    "search",
}
_DESTRUCTIVE_TOOLS = {"cal_delete"}

for _t in TOOLS:
    if _t["name"] in _READ_TOOLS:
        _t["annotations"] = _RO
    elif _t["name"] in _DESTRUCTIVE_TOOLS:
        _t["annotations"] = _DEL
    else:
        _t["annotations"] = _WR


# ── Handlers ────────────────────────────────────────────────────────

def _u(a):
    """Extract user hint, defaulting to alex."""
    return a.get("user", "alex")


# --  Mail  --

def _mail_list(a):
    u, top, folder = _u(a), a.get("top", 10), a.get("folder")
    base = f"/me/mailFolders/{folder}/messages" if folder else "/me/messages"
    return graph_get(f"{base}?$top={top}&$orderby=receivedDateTime desc"
                     "&$select=id,subject,from,receivedDateTime,isRead,hasAttachments", user_hint=u)

def _mail_read(a):
    return graph_get(f"/me/messages/{a['message_id']}", user_hint=_u(a))

def _mail_search(a):
    return graph_get(f"/me/messages?$search=\"{a['query']}\"&$top={a.get('top', 10)}"
                     "&$select=id,subject,from,receivedDateTime,bodyPreview", user_hint=_u(a))

def _mail_send(a):
    to_list = [{"emailAddress": {"address": e.strip()}} for e in a["to"].split(",")]
    msg = {
        "subject": a["subject"],
        "body": {"contentType": "HTML" if a.get("html") else "Text", "content": a["body"]},
        "toRecipients": to_list,
    }
    if a.get("cc"):
        msg["ccRecipients"] = [{"emailAddress": {"address": e.strip()}} for e in a["cc"].split(",")]
    return graph_post("/me/sendMail", json_body={"message": msg}, user_hint=_u(a))

def _mail_draft(a):
    body = {
        "subject": a["subject"],
        "body": {"contentType": "Text", "content": a["body"]},
        "toRecipients": [{"emailAddress": {"address": e.strip()}} for e in a["to"].split(",")],
    }
    return graph_post("/me/messages", json_body=body, user_hint=_u(a))

def _mail_reply(a):
    return graph_post(f"/me/messages/{a['message_id']}/reply",
                      json_body={"comment": a["body"]}, user_hint=_u(a))

def _mail_folders(a):
    return graph_get("/me/mailFolders?$top=50", user_hint=_u(a))


# --  Calendar  --

def _cal_list(a):
    return graph_get(f"/me/events?$top={a.get('top', 10)}&$orderby=start/dateTime"
                     "&$select=id,subject,start,end,location,organizer,isOnlineMeeting", user_hint=_u(a))

def _cal_today(a):
    now = datetime.now(timezone.utc)
    return graph_get(f"/me/calendarView?startDateTime={now:%Y-%m-%dT00:00:00Z}"
                     f"&endDateTime={now:%Y-%m-%dT23:59:59Z}&$orderby=start/dateTime"
                     "&$select=id,subject,start,end,location,organizer", user_hint=_u(a))

def _cal_search(a):
    return graph_get(f"/me/events?$search=\"{a['query']}\"&$top={a.get('top', 10)}"
                     "&$select=id,subject,start,end,location,organizer,isOnlineMeeting", user_hint=_u(a))

def _cal_create(a):
    tz = a.get("tz", "America/Los_Angeles")
    body = {
        "subject": a["subject"],
        "start": {"dateTime": a["start"], "timeZone": tz},
        "end": {"dateTime": a["end"], "timeZone": tz},
    }
    if a.get("attendees"):
        body["attendees"] = [{"emailAddress": {"address": e.strip()}, "type": "required"}
                             for e in a["attendees"].split(",")]
    if a.get("online"):
        body["isOnlineMeeting"] = True
        body["onlineMeetingProvider"] = "teamsForBusiness"
    return graph_post("/me/events", json_body=body, user_hint=_u(a))

def _cal_delete(a):
    return graph_delete(f"/me/events/{a['event_id']}", user_hint=_u(a))


# --  Chat (Teams)  --

def _chat_list(a):
    return graph_get(f"/me/chats?$top={a.get('top', 20)}"
                     "&$expand=lastMessagePreview&$orderby=lastMessagePreview/createdDateTime desc",
                     user_hint=_u(a))

def _chat_messages(a):
    return graph_get(f"/me/chats/{a['chat_id']}/messages?$top={a.get('top', 20)}", user_hint=_u(a))

def _chat_send(a):
    return graph_post(f"/me/chats/{a['chat_id']}/messages",
                      json_body={"body": {"contentType": "text", "content": a["message"]}},
                      user_hint=_u(a))

def _chat_search(a):
    body = {"requests": [{
        "entityTypes": ["chatMessage"],
        "query": {"queryString": a["query"]},
        "from": 0, "size": a.get("top", 25),
    }]}
    return graph_post("/search/query", json_body=body, user_hint=_u(a))


# --  Channel (Teams)  --

def _channel_list(a):
    return graph_get(f"/teams/{a['team_id']}/channels", user_hint=_u(a))

def _channel_messages(a):
    return graph_get(f"/teams/{a['team_id']}/channels/{a['channel_id']}/messages"
                     f"?$top={a.get('top', 20)}", user_hint=_u(a))

def _channel_send(a):
    return graph_post(f"/teams/{a['team_id']}/channels/{a['channel_id']}/messages",
                      json_body={"body": {"contentType": "text", "content": a["message"]}},
                      user_hint=_u(a))


# --  Files (OneDrive)  --

def _files_list(a):
    path = f"/me/drive/root:/{a['path']}:/children" if a.get("path") else "/me/drive/root/children"
    return graph_get(f"{path}?$top=50&$select=id,name,size,lastModifiedDateTime,folder,file,webUrl",
                     user_hint=_u(a))

def _files_search(a):
    return graph_get(f"/me/drive/root/search(q='{a['query']}')"
                     "?$top=20&$select=id,name,size,webUrl,parentReference", user_hint=_u(a))


# --  Tasks (To Do)  --

def _tasks_lists(a):
    return graph_get("/me/todo/lists", user_hint=_u(a))

def _tasks_list(a):
    return graph_get(f"/me/todo/lists/{a['list_id']}/tasks?$top=50", user_hint=_u(a))

def _tasks_create(a):
    body = {"title": a["title"]}
    if a.get("due"):
        body["dueDateTime"] = {"dateTime": f"{a['due']}T00:00:00", "timeZone": "UTC"}
    if a.get("body"):
        body["body"] = {"contentType": "text", "content": a["body"]}
    return graph_post(f"/me/todo/lists/{a['list_id']}/tasks", json_body=body, user_hint=_u(a))

def _tasks_complete(a):
    return graph_patch(f"/me/todo/lists/{a['list_id']}/tasks/{a['task_id']}",
                       json_body={"status": "completed"}, user_hint=_u(a))


# --  Contacts  --

def _contacts_list(a):
    return graph_get(f"/me/contacts?$top={a.get('top', 20)}"
                     "&$select=id,displayName,emailAddresses,mobilePhone,companyName,jobTitle",
                     user_hint=_u(a))

def _contacts_search(a):
    return graph_get(f"/me/people?$search=\"{a['query']}\"&$top=10", user_hint=_u(a))


# --  Notes (OneNote)  --

def _notes_notebooks(a):
    return graph_get("/me/onenote/notebooks?$select=id,displayName,lastModifiedDateTime",
                     user_hint=_u(a))


# --  Presence  --

def _presence_get(a):
    return graph_get("/me/presence", user_hint=_u(a))

def _presence_set(a):
    body = {
        "sessionId": "work-m365",
        "availability": a["availability"],
        "activity": a.get("activity", a["availability"]),
        "expirationDuration": "PT1H",
    }
    return graph_post("/me/presence/setPresence", json_body=body, user_hint=_u(a))


# --  Search  --

def _search(a):
    entity_types = a["types"].split(",") if a.get("types") else ["message", "driveItem", "event"]
    body = {"requests": [{
        "entityTypes": entity_types,
        "query": {"queryString": a["query"]},
        "from": 0, "size": a.get("top", 25),
    }]}
    return graph_post("/search/query", json_body=body, user_hint=_u(a))


# ── Dispatch ────────────────────────────────────────────────────────

HANDLERS = {
    "mail_list": _mail_list, "mail_read": _mail_read, "mail_search": _mail_search,
    "mail_send": _mail_send, "mail_draft": _mail_draft, "mail_reply": _mail_reply,
    "mail_folders": _mail_folders,
    "cal_list": _cal_list, "cal_today": _cal_today, "cal_search": _cal_search,
    "cal_create": _cal_create, "cal_delete": _cal_delete,
    "chat_list": _chat_list, "chat_messages": _chat_messages,
    "chat_send": _chat_send, "chat_search": _chat_search,
    "channel_list": _channel_list, "channel_messages": _channel_messages,
    "channel_send": _channel_send,
    "files_list": _files_list, "files_search": _files_search,
    "tasks_lists": _tasks_lists, "tasks_list": _tasks_list,
    "tasks_create": _tasks_create, "tasks_complete": _tasks_complete,
    "contacts_list": _contacts_list, "contacts_search": _contacts_search,
    "notes_notebooks": _notes_notebooks,
    "presence_get": _presence_get, "presence_set": _presence_set,
    "search": _search,
}


def dispatch_tool(name, arguments):
    handler = HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")
    return handler(arguments)
