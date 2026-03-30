#!/usr/bin/env python3
"""
M365 CLI — User-level Microsoft 365 operations via Graph beta API.
Delegated permissions: Mail, Calendar, Chat, Files, Tasks, Contacts, Notes, Meetings, Presence.
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from graph_client import graph_get, graph_post, graph_patch, graph_delete, get_token, pp

TENANT = "karelin"
USER = "default"


def set_context(args):
    global TENANT, USER
    TENANT = getattr(args, "tenant", "karelin") or "karelin"
    USER = getattr(args, "user", "default") or "default"


def kw():
    return {"tenant": TENANT, "user_hint": USER}

# --- Auth ---

def cmd_login(args):
    set_context(args)
    token = get_token(TENANT)
    if token:
        print("Authenticated via client credentials (no user login needed).")
        cmd_whoami(args)

def cmd_whoami(args):
    set_context(args)
    pp(graph_get("/me", **kw()))

def cmd_status(args):
    set_context(args)
    token = get_token(TENANT)
    if token:
        me = graph_get("/me?$select=displayName,mail,userPrincipalName", **kw())
        print(f"Acting as: {me.get('displayName', '?')} ({me.get('mail', me.get('userPrincipalName', '?'))}) [user={USER}]")
    else:
        print("Auth failed.")

# --- Mail ---

def cmd_mail_list(args):
    set_context(args)
    top = args.top or 10
    path = f"/me/messages?$top={top}&$orderby=receivedDateTime desc&$select=id,subject,from,receivedDateTime,isRead,hasAttachments"
    if args.folder:
        path = f"/me/mailFolders/{args.folder}/messages?$top={top}&$orderby=receivedDateTime desc&$select=id,subject,from,receivedDateTime,isRead,hasAttachments"
    pp(graph_get(path, **kw()))

def cmd_mail_read(args):
    set_context(args)
    pp(graph_get(f"/me/messages/{args.id}", **kw()))

def cmd_mail_search(args):
    set_context(args)
    pp(graph_get(f"/me/messages?$search=\"{args.query}\"&$top={args.top or 10}&$select=id,subject,from,receivedDateTime,bodyPreview", **kw()))

def cmd_mail_send(args):
    set_context(args)
    to_list = [{"emailAddress": {"address": a.strip()}} for a in args.to.split(",")]
    body = {"message": {"subject": args.subject, "body": {"contentType": "HTML" if args.html else "Text", "content": args.body}, "toRecipients": to_list}}
    if args.cc:
        body["message"]["ccRecipients"] = [{"emailAddress": {"address": a.strip()}} for a in args.cc.split(",")]
    pp(graph_post("/me/sendMail", json_body=body, **kw()))

def cmd_mail_draft(args):
    set_context(args)
    body = {"subject": args.subject, "body": {"contentType": "Text", "content": args.body}, "toRecipients": [{"emailAddress": {"address": a.strip()}} for a in args.to.split(",")]}
    pp(graph_post("/me/messages", json_body=body, **kw()))

def cmd_mail_reply(args):
    set_context(args)
    pp(graph_post(f"/me/messages/{args.id}/reply", json_body={"comment": args.body}, **kw()))

def cmd_mail_folders(args):
    set_context(args)
    pp(graph_get("/me/mailFolders?$top=50", **kw()))

# --- Calendar ---

def cmd_cal_list(args):
    set_context(args)
    pp(graph_get(f"/me/events?$top={args.top or 10}&$orderby=start/dateTime&$select=id,subject,start,end,location,organizer,isOnlineMeeting", **kw()))

def cmd_cal_today(args):
    set_context(args)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    pp(graph_get(f"/me/calendarView?startDateTime={now:%Y-%m-%dT00:00:00Z}&endDateTime={now:%Y-%m-%dT23:59:59Z}&$orderby=start/dateTime&$select=id,subject,start,end,location,organizer", **kw()))

def cmd_cal_search(args):
    set_context(args)
    pp(graph_get(f"/me/events?$search=\"{args.query}\"&$top={args.top or 10}&$select=id,subject,start,end,location,organizer,isOnlineMeeting", **kw()))

def cmd_cal_create(args):
    set_context(args)
    body = {"subject": args.subject, "start": {"dateTime": args.start, "timeZone": args.timezone}, "end": {"dateTime": args.end, "timeZone": args.timezone}}
    if args.body: body["body"] = {"contentType": "Text", "content": args.body}
    if args.attendees: body["attendees"] = [{"emailAddress": {"address": a.strip()}, "type": "required"} for a in args.attendees.split(",")]
    if args.online: body["isOnlineMeeting"] = True; body["onlineMeetingProvider"] = "teamsForBusiness"
    pp(graph_post("/me/events", json_body=body, **kw()))

def cmd_cal_delete(args):
    set_context(args)
    pp(graph_delete(f"/me/events/{args.id}", **kw()))

# --- Chat (Teams) ---

def cmd_chat_list(args):
    set_context(args)
    pp(graph_get(f"/me/chats?$top={args.top or 20}&$expand=lastMessagePreview&$orderby=lastMessagePreview/createdDateTime desc", **kw()))

def cmd_chat_messages(args):
    set_context(args)
    pp(graph_get(f"/me/chats/{args.chat_id}/messages?$top={args.top or 20}", **kw()))

def cmd_chat_send(args):
    set_context(args)
    pp(graph_post(f"/me/chats/{args.chat_id}/messages", json_body={"body": {"contentType": "text", "content": args.message}}, **kw()))

def cmd_chat_search(args):
    set_context(args)
    body = {
        "requests": [{
            "entityTypes": ["chatMessage"],
            "query": {"queryString": args.query},
            "from": 0,
            "size": args.top or 25,
        }]
    }
    pp(graph_post("/search/query", json_body=body, **kw()))

# --- Channel (Teams) ---

def cmd_channel_list(args):
    set_context(args)
    pp(graph_get(f"/teams/{args.team_id}/channels", **kw()))

def cmd_channel_messages(args):
    set_context(args)
    pp(graph_get(f"/teams/{args.team_id}/channels/{args.channel_id}/messages?$top={args.top or 20}", **kw()))

def cmd_channel_send(args):
    set_context(args)
    pp(graph_post(f"/teams/{args.team_id}/channels/{args.channel_id}/messages", json_body={"body": {"contentType": "text", "content": args.message}}, **kw()))

# --- Files ---

def cmd_files_list(args):
    set_context(args)
    path = f"/me/drive/root:/{args.path}:/children" if args.path else "/me/drive/root/children"
    pp(graph_get(f"{path}?$top=50&$select=id,name,size,lastModifiedDateTime,folder,file,webUrl", **kw()))

def cmd_files_search(args):
    set_context(args)
    pp(graph_get(f"/me/drive/root/search(q='{args.query}')?$top=20&$select=id,name,size,webUrl,parentReference", **kw()))

def cmd_sites_search(args):
    set_context(args)
    pp(graph_get(f"/sites?search={args.query}&$top=10", **kw()))

# --- Tasks ---

def cmd_tasks_lists(args):
    set_context(args)
    pp(graph_get("/me/todo/lists", **kw()))

def cmd_tasks_list(args):
    set_context(args)
    pp(graph_get(f"/me/todo/lists/{args.list_id}/tasks?$top=50", **kw()))

def cmd_tasks_create(args):
    set_context(args)
    body = {"title": args.title}
    if args.due: body["dueDateTime"] = {"dateTime": f"{args.due}T00:00:00", "timeZone": "UTC"}
    if args.body: body["body"] = {"contentType": "text", "content": args.body}
    pp(graph_post(f"/me/todo/lists/{args.list_id}/tasks", json_body=body, **kw()))

def cmd_tasks_complete(args):
    set_context(args)
    pp(graph_patch(f"/me/todo/lists/{args.list_id}/tasks/{args.task_id}", json_body={"status": "completed"}, **kw()))

# --- Contacts ---

def cmd_contacts_list(args):
    set_context(args)
    pp(graph_get(f"/me/contacts?$top={args.top or 20}&$select=id,displayName,emailAddresses,mobilePhone,companyName,jobTitle", **kw()))

def cmd_contacts_search(args):
    set_context(args)
    pp(graph_get(f"/me/people?$search=\"{args.query}\"&$top=10", **kw()))

# --- Notes ---

def cmd_notes_notebooks(args):
    set_context(args)
    pp(graph_get("/me/onenote/notebooks?$select=id,displayName,lastModifiedDateTime", **kw()))

def cmd_notes_sections(args):
    set_context(args)
    pp(graph_get(f"/me/onenote/notebooks/{args.notebook_id}/sections", **kw()))

def cmd_notes_pages(args):
    set_context(args)
    pp(graph_get(f"/me/onenote/sections/{args.section_id}/pages?$top=20&$select=id,title,createdDateTime", **kw()))

def cmd_notes_search(args):
    set_context(args)
    pp(graph_get(f"/me/onenote/pages?search={args.query}&$top={args.top or 20}&$select=id,title,createdDateTime,parentSection", **kw()))

# --- Meetings ---

def cmd_meetings_create(args):
    set_context(args)
    pp(graph_post("/me/onlineMeetings", json_body={"subject": args.subject, "startDateTime": args.start, "endDateTime": args.end}, **kw()))

# --- Presence ---

def cmd_presence(args):
    set_context(args)
    pp(graph_get("/me/presence", **kw()))

def cmd_presence_set(args):
    set_context(args)
    pp(graph_post("/me/presence/setPresence", json_body={"sessionId": "chmo", "availability": args.availability, "activity": args.activity or args.availability, "expirationDuration": "PT1H"}, **kw()))

# --- Unified Search ---

def cmd_search(args):
    set_context(args)
    entity_types = args.types.split(",") if args.types else ["message", "driveItem", "event"]
    body = {
        "requests": [{
            "entityTypes": entity_types,
            "query": {"queryString": args.query},
            "from": 0,
            "size": args.top or 25,
        }]
    }
    pp(graph_post("/search/query", json_body=body, **kw()))

# --- Parser ---

def main():
    p = argparse.ArgumentParser(description="M365 CLI — Graph beta API (delegated)")
    p.add_argument("--tenant", default="karelin")
    p.add_argument("--user", default="default", help="User hint for token cache (alex, irina)")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("login").set_defaults(func=cmd_login)
    sub.add_parser("whoami").set_defaults(func=cmd_whoami)
    sub.add_parser("status").set_defaults(func=cmd_status)

    # Mail
    ml = sub.add_parser("mail").add_subparsers(dest="sub")
    s = ml.add_parser("list"); s.add_argument("--top", type=int); s.add_argument("--folder"); s.set_defaults(func=cmd_mail_list)
    s = ml.add_parser("read"); s.add_argument("id"); s.set_defaults(func=cmd_mail_read)
    s = ml.add_parser("search"); s.add_argument("query"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_mail_search)
    s = ml.add_parser("send"); s.add_argument("--to", required=True); s.add_argument("--subject", required=True); s.add_argument("--body", required=True); s.add_argument("--cc"); s.add_argument("--html", action="store_true"); s.set_defaults(func=cmd_mail_send)
    s = ml.add_parser("draft"); s.add_argument("--to", required=True); s.add_argument("--subject", required=True); s.add_argument("--body", required=True); s.set_defaults(func=cmd_mail_draft)
    s = ml.add_parser("reply"); s.add_argument("id"); s.add_argument("--body", required=True); s.set_defaults(func=cmd_mail_reply)
    ml.add_parser("folders").set_defaults(func=cmd_mail_folders)

    # Calendar
    cl = sub.add_parser("cal").add_subparsers(dest="sub")
    s = cl.add_parser("list"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_cal_list)
    cl.add_parser("today").set_defaults(func=cmd_cal_today)
    s = cl.add_parser("search"); s.add_argument("query"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_cal_search)
    s = cl.add_parser("create"); s.add_argument("--subject", required=True); s.add_argument("--start", required=True); s.add_argument("--end", required=True); s.add_argument("--body"); s.add_argument("--attendees"); s.add_argument("--timezone", default="America/Los_Angeles"); s.add_argument("--online", action="store_true"); s.set_defaults(func=cmd_cal_create)
    s = cl.add_parser("delete"); s.add_argument("id"); s.set_defaults(func=cmd_cal_delete)

    # Chat
    ch = sub.add_parser("chat").add_subparsers(dest="sub")
    s = ch.add_parser("list"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_chat_list)
    s = ch.add_parser("messages"); s.add_argument("chat_id"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_chat_messages)
    s = ch.add_parser("send"); s.add_argument("chat_id"); s.add_argument("message"); s.set_defaults(func=cmd_chat_send)
    s = ch.add_parser("search"); s.add_argument("query"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_chat_search)

    # Channel
    cn = sub.add_parser("channel").add_subparsers(dest="sub")
    s = cn.add_parser("list"); s.add_argument("team_id"); s.set_defaults(func=cmd_channel_list)
    s = cn.add_parser("messages"); s.add_argument("team_id"); s.add_argument("channel_id"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_channel_messages)
    s = cn.add_parser("send"); s.add_argument("team_id"); s.add_argument("channel_id"); s.add_argument("message"); s.set_defaults(func=cmd_channel_send)

    # Files
    fl = sub.add_parser("files").add_subparsers(dest="sub")
    s = fl.add_parser("list"); s.add_argument("--path"); s.set_defaults(func=cmd_files_list)
    s = fl.add_parser("search"); s.add_argument("query"); s.set_defaults(func=cmd_files_search)
    s = fl.add_parser("sites"); s.add_argument("query"); s.set_defaults(func=cmd_sites_search)

    # Tasks
    tk = sub.add_parser("tasks").add_subparsers(dest="sub")
    tk.add_parser("lists").set_defaults(func=cmd_tasks_lists)
    s = tk.add_parser("list"); s.add_argument("list_id"); s.set_defaults(func=cmd_tasks_list)
    s = tk.add_parser("create"); s.add_argument("list_id"); s.add_argument("--title", required=True); s.add_argument("--due"); s.add_argument("--body"); s.set_defaults(func=cmd_tasks_create)
    s = tk.add_parser("complete"); s.add_argument("list_id"); s.add_argument("task_id"); s.set_defaults(func=cmd_tasks_complete)

    # Contacts
    ct = sub.add_parser("contacts").add_subparsers(dest="sub")
    s = ct.add_parser("list"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_contacts_list)
    s = ct.add_parser("search"); s.add_argument("query"); s.set_defaults(func=cmd_contacts_search)

    # Notes
    nt = sub.add_parser("notes").add_subparsers(dest="sub")
    nt.add_parser("notebooks").set_defaults(func=cmd_notes_notebooks)
    s = nt.add_parser("sections"); s.add_argument("notebook_id"); s.set_defaults(func=cmd_notes_sections)
    s = nt.add_parser("pages"); s.add_argument("section_id"); s.set_defaults(func=cmd_notes_pages)
    s = nt.add_parser("search"); s.add_argument("query"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_notes_search)

    # Meetings
    mt = sub.add_parser("meetings").add_subparsers(dest="sub")
    s = mt.add_parser("create"); s.add_argument("--subject", required=True); s.add_argument("--start", required=True); s.add_argument("--end", required=True); s.set_defaults(func=cmd_meetings_create)

    # Presence
    pr = sub.add_parser("presence").add_subparsers(dest="sub")
    pr.add_parser("get").set_defaults(func=cmd_presence)
    s = pr.add_parser("set"); s.add_argument("availability", choices=["Available","Busy","DoNotDisturb","Away","Offline"]); s.add_argument("--activity"); s.set_defaults(func=cmd_presence_set)

    # Unified search
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--top", type=int); s.add_argument("--types", help="Comma-separated: message,driveItem,event,chatMessage,site,list,listItem"); s.set_defaults(func=cmd_search)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        sys.exit(1)
    if hasattr(args, "func"):
        args.func(args)
    else:
        p.print_help()

if __name__ == "__main__":
    main()
