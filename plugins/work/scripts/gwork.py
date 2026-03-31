#!/usr/bin/env python3
"""Google Gmail & Drive CLI — personal account operations.

Usage:
    python google.py login
    python google.py gmail list [--top N] [--label LABEL]
    python google.py gmail read MESSAGE_ID
    python google.py gmail thread THREAD_ID
    python google.py gmail search "query" [--top N]
    python google.py gmail send --to "a@b.com" --subject "Subj" --body "Body" [--cc "c@d.com"] [--html]
    python google.py gmail draft --to "a@b.com" --subject "Subj" --body "Body"
    python google.py gmail reply MESSAGE_ID --body "Reply text"
    python google.py gmail labels
    python google.py drive list [--top N] [--folder FOLDER_ID]
    python google.py drive search "query" [--top N]
    python google.py drive get FILE_ID
    python google.py drive download FILE_ID [--out PATH]
    python google.py drive mkdir "Folder Name" [--parent PARENT_ID]
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from email.mime.text import MIMEText
from pathlib import Path


def j(obj):
    print(json.dumps(obj, default=str))
    sys.exit(0)


def jerr(msg):
    print(json.dumps({"error": msg}))
    sys.exit(1)


# ── Gmail ────────────────────────────────────────────────────────────────────

def cmd_gmail_list(args):
    from google_client import gmail_service
    svc = gmail_service()
    label = args.label or "INBOX"
    top = args.top or 10
    res = svc.users().messages().list(userId="me", labelIds=[label], maxResults=top).execute()
    msgs = res.get("messages", [])
    out = []
    for m in msgs:
        detail = svc.users().messages().get(userId="me", id=m["id"], format="metadata",
                                             metadataHeaders=["Subject", "From", "Date"]).execute()
        headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
        out.append({
            "id": m["id"],
            "threadId": detail.get("threadId"),
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "snippet": detail.get("snippet", ""),
            "labelIds": detail.get("labelIds", []),
        })
    j(out)


def cmd_gmail_read(args):
    from google_client import gmail_service
    svc = gmail_service()
    msg = svc.users().messages().get(userId="me", id=args.message_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    body = _extract_body(msg.get("payload", {}))
    j({
        "id": msg["id"],
        "threadId": msg.get("threadId"),
        "subject": headers.get("Subject", ""),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "cc": headers.get("Cc", ""),
        "date": headers.get("Date", ""),
        "body": body,
        "labelIds": msg.get("labelIds", []),
    })


def cmd_gmail_thread(args):
    from google_client import gmail_service
    svc = gmail_service()
    thread = svc.users().threads().get(userId="me", id=args.thread_id, format="full").execute()
    msgs = []
    for msg in thread.get("messages", []):
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        body = _extract_body(msg.get("payload", {}))
        msgs.append({
            "id": msg["id"],
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "body": body,
        })
    j({"threadId": args.thread_id, "messages": msgs})


def cmd_gmail_search(args):
    from google_client import gmail_service
    svc = gmail_service()
    top = args.top or 10
    res = svc.users().messages().list(userId="me", q=args.query, maxResults=top).execute()
    msgs = res.get("messages", [])
    out = []
    for m in msgs:
        detail = svc.users().messages().get(userId="me", id=m["id"], format="metadata",
                                             metadataHeaders=["Subject", "From", "Date"]).execute()
        headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
        out.append({
            "id": m["id"],
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "snippet": detail.get("snippet", ""),
        })
    j(out)


def cmd_gmail_send(args):
    from google_client import gmail_service
    svc = gmail_service()
    msg = _create_message(args.to, args.subject, args.body, cc=args.cc, html=args.html)
    result = svc.users().messages().send(userId="me", body=msg).execute()
    j({"status": "sent", "id": result["id"], "threadId": result.get("threadId")})


def cmd_gmail_draft(args):
    from google_client import gmail_service
    svc = gmail_service()
    msg = _create_message(args.to, args.subject, args.body)
    result = svc.users().drafts().create(userId="me", body={"message": msg}).execute()
    j({"status": "drafted", "id": result["id"], "messageId": result["message"]["id"]})


def cmd_gmail_reply(args):
    from google_client import gmail_service
    svc = gmail_service()
    original = svc.users().messages().get(userId="me", id=args.message_id, format="metadata",
                                           metadataHeaders=["Subject", "From", "To", "Message-ID"]).execute()
    headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
    subject = headers.get("Subject", "")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    reply_to = headers.get("From", headers.get("To", ""))
    msg = _create_message(reply_to, subject, args.body)
    msg["threadId"] = original.get("threadId")
    result = svc.users().messages().send(userId="me", body=msg).execute()
    j({"status": "replied", "id": result["id"], "threadId": result.get("threadId")})


def cmd_gmail_labels(args):
    from google_client import gmail_service
    svc = gmail_service()
    results = svc.users().labels().list(userId="me").execute()
    j(results.get("labels", []))


def _create_message(to, subject, body, cc=None, html=False):
    mime = MIMEText(body, "html" if html else "plain")
    mime["to"] = to
    mime["subject"] = subject
    if cc:
        mime["cc"] = cc
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    return {"raw": raw}


def _extract_body(payload):
    """Extract plain text body from Gmail payload."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        result = _extract_body(part)
        if result:
            return result
    return ""


# ── Drive ────────────────────────────────────────────────────────────────────

def cmd_drive_list(args):
    from google_client import drive_service
    svc = drive_service()
    top = args.top or 20
    query = f"'{args.folder}' in parents" if args.folder else None
    params = {"pageSize": top, "fields": "files(id,name,mimeType,size,modifiedTime,parents)", "orderBy": "modifiedTime desc"}
    if query:
        params["q"] = query
    results = svc.files().list(**params).execute()
    j(results.get("files", []))


def cmd_drive_search(args):
    from google_client import drive_service
    svc = drive_service()
    top = args.top or 20
    q = f"fullText contains '{args.query}' and trashed = false"
    results = svc.files().list(q=q, pageSize=top,
                                fields="files(id,name,mimeType,size,modifiedTime,parents)",
                                orderBy="modifiedTime desc").execute()
    j(results.get("files", []))


def cmd_drive_get(args):
    from google_client import drive_service
    svc = drive_service()
    f = svc.files().get(fileId=args.file_id, fields="id,name,mimeType,size,modifiedTime,parents,webViewLink,owners,shared").execute()
    j(f)


def cmd_drive_download(args):
    from google_client import drive_service
    import io
    svc = drive_service()
    meta = svc.files().get(fileId=args.file_id, fields="name,mimeType").execute()
    request = svc.files().get_media(fileId=args.file_id)
    from googleapiclient.http import MediaIoBaseDownload
    out_path = Path(args.out) if args.out else Path(meta["name"])
    fh = io.FileIO(str(out_path), "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    j({"status": "downloaded", "path": str(out_path.resolve()), "name": meta["name"], "size": out_path.stat().st_size})


def cmd_drive_mkdir(args):
    from google_client import drive_service
    svc = drive_service()
    metadata = {"name": args.name, "mimeType": "application/vnd.google-apps.folder"}
    if args.parent:
        metadata["parents"] = [args.parent]
    folder = svc.files().create(body=metadata, fields="id,name,webViewLink").execute()
    j(folder)


# ── Auth ─────────────────────────────────────────────────────────────────────

def cmd_login(args):
    from google_client import get_credentials
    creds = get_credentials()
    from google_client import gmail_service
    svc = gmail_service()
    profile = svc.users().getProfile(userId="me").execute()
    j({"status": "authenticated", "email": profile.get("emailAddress"), "messagesTotal": profile.get("messagesTotal")})


def cmd_add_token(args):
    from google_client import save_token, TOKEN_PATH
    token_json = args.token_json
    if not token_json:
        token_json = sys.stdin.read()
    if not token_json.strip():
        jerr("No token JSON provided. Pass as argument or pipe to stdin.")
    try:
        json.loads(token_json)
    except json.JSONDecodeError as e:
        jerr(f"Invalid JSON: {e}")
    save_token(token_json)
    j({"status": "saved", "path": str(TOKEN_PATH)})


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    sys.path.insert(0, str(Path(__file__).parent))

    parser = argparse.ArgumentParser(description="Google Gmail & Drive CLI")
    sub = parser.add_subparsers(dest="command")

    # login
    sub.add_parser("login")

    # add-token
    p = sub.add_parser("add-token")
    p.add_argument("token_json", nargs="?", default=None, help="Token JSON string (or pipe via stdin)")

    # gmail
    gmail = sub.add_parser("gmail")
    gsub = gmail.add_subparsers(dest="gmail_cmd")

    p = gsub.add_parser("list")
    p.add_argument("--top", type=int)
    p.add_argument("--label")

    p = gsub.add_parser("read")
    p.add_argument("message_id")

    p = gsub.add_parser("thread")
    p.add_argument("thread_id")

    p = gsub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--top", type=int)

    p = gsub.add_parser("send")
    p.add_argument("--to", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--cc")
    p.add_argument("--html", action="store_true")

    p = gsub.add_parser("draft")
    p.add_argument("--to", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)

    p = gsub.add_parser("reply")
    p.add_argument("message_id")
    p.add_argument("--body", required=True)

    gsub.add_parser("labels")

    # drive
    drive = sub.add_parser("drive")
    dsub = drive.add_subparsers(dest="drive_cmd")

    p = dsub.add_parser("list")
    p.add_argument("--top", type=int)
    p.add_argument("--folder")

    p = dsub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--top", type=int)

    p = dsub.add_parser("get")
    p.add_argument("file_id")

    p = dsub.add_parser("download")
    p.add_argument("file_id")
    p.add_argument("--out")

    p = dsub.add_parser("mkdir")
    p.add_argument("name")
    p.add_argument("--parent")

    args = parser.parse_args()

    dispatch = {
        ("login", None): cmd_login,
        ("add-token", None): cmd_add_token,
        ("gmail", "list"): cmd_gmail_list,
        ("gmail", "read"): cmd_gmail_read,
        ("gmail", "thread"): cmd_gmail_thread,
        ("gmail", "search"): cmd_gmail_search,
        ("gmail", "send"): cmd_gmail_send,
        ("gmail", "draft"): cmd_gmail_draft,
        ("gmail", "reply"): cmd_gmail_reply,
        ("gmail", "labels"): cmd_gmail_labels,
        ("drive", "list"): cmd_drive_list,
        ("drive", "search"): cmd_drive_search,
        ("drive", "get"): cmd_drive_get,
        ("drive", "download"): cmd_drive_download,
        ("drive", "mkdir"): cmd_drive_mkdir,
    }

    subcmd = getattr(args, "gmail_cmd", None) or getattr(args, "drive_cmd", None)
    handler = dispatch.get((args.command, subcmd))
    if not handler:
        parser.print_help()
        sys.exit(1)
    handler(args)


if __name__ == "__main__":
    main()
