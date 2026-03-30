#!/usr/bin/env python3
"""
M365-Admin CLI — Tenant admin operations via Graph beta API.
Application permissions (client credentials) — no user login required.
Users, Groups, Teams, Licenses, Directory, Devices, Reports, Security.
"""

import argparse
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from graph_admin_client import graph_get, graph_post, graph_patch, graph_delete, pp

TENANT = "karelin"

def set_context(args):
    global TENANT
    TENANT = getattr(args, "tenant", "karelin") or "karelin"

def kw():
    return {"tenant": TENANT}

# --- Users ---

def cmd_users_list(args):
    set_context(args)
    pp(graph_get(f"/users?$top={args.top or 25}&$select=id,displayName,mail,userPrincipalName,accountEnabled,userType,createdDateTime", **kw()))

def cmd_users_get(args):
    set_context(args)
    pp(graph_get(f"/users/{args.id}?$select=id,displayName,mail,userPrincipalName,accountEnabled,userType,jobTitle,department,officeLocation,mobilePhone,assignedLicenses", **kw()))

def cmd_users_create(args):
    set_context(args)
    body = {
        "accountEnabled": True,
        "displayName": args.name,
        "mailNickname": args.nickname or args.name.split()[0].lower(),
        "userPrincipalName": args.upn,
        "passwordProfile": {"forceChangePasswordNextSignIn": True, "password": args.password},
    }
    if args.first: body["givenName"] = args.first
    if args.last: body["surname"] = args.last
    if args.job: body["jobTitle"] = args.job
    if args.department: body["department"] = args.department
    pp(graph_post("/users", json_body=body, **kw()))

def cmd_users_update(args):
    set_context(args)
    body = json.loads(args.json)
    pp(graph_patch(f"/users/{args.id}", json_body=body, **kw()))

def cmd_users_disable(args):
    set_context(args)
    pp(graph_patch(f"/users/{args.id}", json_body={"accountEnabled": False}, **kw()))

def cmd_users_enable(args):
    set_context(args)
    pp(graph_patch(f"/users/{args.id}", json_body={"accountEnabled": True}, **kw()))

def cmd_users_delete(args):
    set_context(args)
    pp(graph_delete(f"/users/{args.id}", **kw()))

def cmd_users_reset_pw(args):
    set_context(args)
    pp(graph_patch(f"/users/{args.id}", json_body={"passwordProfile": {"forceChangePasswordNextSignIn": True, "password": args.password}}, **kw()))

# --- Invite guest ---

def cmd_users_invite(args):
    set_context(args)
    body = {
        "invitedUserEmailAddress": args.email,
        "inviteRedirectUrl": "https://teams.microsoft.com",
        "sendInvitationMessage": not args.no_email,
    }
    if args.name: body["invitedUserDisplayName"] = args.name
    pp(graph_post("/invitations", json_body=body, **kw()))

# --- Groups ---

def cmd_groups_list(args):
    set_context(args)
    pp(graph_get(f"/groups?$top={args.top or 25}&$select=id,displayName,mail,groupTypes,membershipRule,createdDateTime", **kw()))

def cmd_groups_get(args):
    set_context(args)
    pp(graph_get(f"/groups/{args.id}?$select=id,displayName,mail,description,groupTypes,membershipRule,visibility", **kw()))

def cmd_groups_members(args):
    set_context(args)
    pp(graph_get(f"/groups/{args.id}/members?$select=id,displayName,mail,userPrincipalName", **kw()))

def cmd_groups_add_member(args):
    set_context(args)
    pp(graph_post(f"/groups/{args.id}/members/$ref", json_body={"@odata.id": f"https://graph.microsoft.com/beta/users/{args.user_id}"}, **kw()))

def cmd_groups_remove_member(args):
    set_context(args)
    pp(graph_delete(f"/groups/{args.id}/members/{args.user_id}/$ref", **kw()))

def cmd_groups_create(args):
    set_context(args)
    body = {
        "displayName": args.name,
        "mailEnabled": args.mail_enabled,
        "mailNickname": args.nickname or args.name.lower().replace(" ", "-"),
        "securityEnabled": True,
    }
    if args.description: body["description"] = args.description
    pp(graph_post("/groups", json_body=body, **kw()))

# --- Teams ---

def cmd_teams_list(args):
    set_context(args)
    pp(graph_get(f"/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')&$top={args.top or 25}&$select=id,displayName,mail,description", **kw()))

def cmd_teams_get(args):
    set_context(args)
    pp(graph_get(f"/teams/{args.id}", **kw()))

def cmd_teams_channels(args):
    set_context(args)
    pp(graph_get(f"/teams/{args.id}/channels", **kw()))

def cmd_teams_members(args):
    set_context(args)
    pp(graph_get(f"/teams/{args.id}/members?$select=id,displayName,email,roles", **kw()))

def cmd_teams_add_member(args):
    set_context(args)
    body = {
        "@odata.type": "#microsoft.graph.aadUserConversationMember",
        "roles": ["owner"] if args.owner else [],
        "user@odata.bind": f"https://graph.microsoft.com/beta/users('{args.user_id}')",
    }
    pp(graph_post(f"/teams/{args.id}/members", json_body=body, **kw()))

def cmd_teams_create_channel(args):
    set_context(args)
    body = {"displayName": args.name, "membershipType": args.type}
    if args.description: body["description"] = args.description
    pp(graph_post(f"/teams/{args.id}/channels", json_body=body, **kw()))

# --- Licenses ---

def cmd_licenses_list(args):
    set_context(args)
    pp(graph_get("/subscribedSkus?$select=skuId,skuPartNumber,consumedUnits,prepaidUnits,appliesTo", **kw()))

def cmd_licenses_user(args):
    set_context(args)
    pp(graph_get(f"/users/{args.id}/licenseDetails", **kw()))

def cmd_licenses_assign(args):
    set_context(args)
    pp(graph_post(f"/users/{args.id}/assignLicense", json_body={"addLicenses": [{"skuId": args.sku_id}], "removeLicenses": []}, **kw()))

def cmd_licenses_remove(args):
    set_context(args)
    pp(graph_post(f"/users/{args.id}/assignLicense", json_body={"addLicenses": [], "removeLicenses": [args.sku_id]}, **kw()))

# --- Directory roles ---

def cmd_roles_list(args):
    set_context(args)
    pp(graph_get("/directoryRoles?$select=id,displayName,description", **kw()))

def cmd_roles_members(args):
    set_context(args)
    pp(graph_get(f"/directoryRoles/{args.id}/members?$select=id,displayName,mail", **kw()))

# --- Audit ---

def cmd_audit_signins(args):
    set_context(args)
    pp(graph_get(f"/auditLogs/signIns?$top={args.top or 20}&$orderby=createdDateTime desc", **kw()))

def cmd_audit_directory(args):
    set_context(args)
    pp(graph_get(f"/auditLogs/directoryAudits?$top={args.top or 20}&$orderby=activityDateTime desc", **kw()))

# --- Devices ---

def cmd_devices_list(args):
    set_context(args)
    pp(graph_get(f"/devices?$top={args.top or 25}&$select=id,displayName,operatingSystem,operatingSystemVersion,isManaged,isCompliant,approximateLastSignInDateTime", **kw()))

# --- Domains ---

def cmd_domains_list(args):
    set_context(args)
    pp(graph_get("/domains?$select=id,isDefault,isVerified,authenticationType", **kw()))

# --- Organization ---

def cmd_org_get(args):
    set_context(args)
    pp(graph_get("/organization?$select=id,displayName,verifiedDomains,assignedPlans", **kw()))

# --- Security ---

def cmd_security_alerts(args):
    set_context(args)
    pp(graph_get(f"/security/alerts_v2?$top={args.top or 20}&$orderby=createdDateTime desc", **kw()))

def cmd_security_score(args):
    set_context(args)
    pp(graph_get("/security/secureScores?$top=1", **kw()))

# --- Generic ---

def cmd_raw(args):
    set_context(args)
    method = args.method.upper()
    body = json.loads(args.body) if args.body else None
    if method == "GET":
        pp(graph_get(args.path, **kw()))
    elif method == "POST":
        pp(graph_post(args.path, json_body=body, **kw()))
    elif method == "PATCH":
        pp(graph_patch(args.path, json_body=body, **kw()))
    elif method == "DELETE":
        pp(graph_delete(args.path, **kw()))

# --- Parser ---

def main():
    p = argparse.ArgumentParser(description="M365-Admin CLI — Graph beta API (application permissions)")
    p.add_argument("--tenant", default="karelin")
    sub = p.add_subparsers(dest="cmd")

    # Users
    u = sub.add_parser("users").add_subparsers(dest="sub")
    s = u.add_parser("list"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_users_list)
    s = u.add_parser("get"); s.add_argument("id"); s.set_defaults(func=cmd_users_get)
    s = u.add_parser("create"); s.add_argument("--name", required=True); s.add_argument("--upn", required=True); s.add_argument("--password", required=True); s.add_argument("--nickname"); s.add_argument("--first"); s.add_argument("--last"); s.add_argument("--job"); s.add_argument("--department"); s.set_defaults(func=cmd_users_create)
    s = u.add_parser("update"); s.add_argument("id"); s.add_argument("--json", required=True); s.set_defaults(func=cmd_users_update)
    s = u.add_parser("disable"); s.add_argument("id"); s.set_defaults(func=cmd_users_disable)
    s = u.add_parser("enable"); s.add_argument("id"); s.set_defaults(func=cmd_users_enable)
    s = u.add_parser("delete"); s.add_argument("id"); s.set_defaults(func=cmd_users_delete)
    s = u.add_parser("reset-pw"); s.add_argument("id"); s.add_argument("--password", required=True); s.set_defaults(func=cmd_users_reset_pw)
    s = u.add_parser("invite"); s.add_argument("--email", required=True); s.add_argument("--name"); s.add_argument("--no-email", action="store_true"); s.set_defaults(func=cmd_users_invite)

    # Groups
    g = sub.add_parser("groups").add_subparsers(dest="sub")
    s = g.add_parser("list"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_groups_list)
    s = g.add_parser("get"); s.add_argument("id"); s.set_defaults(func=cmd_groups_get)
    s = g.add_parser("members"); s.add_argument("id"); s.set_defaults(func=cmd_groups_members)
    s = g.add_parser("add-member"); s.add_argument("id"); s.add_argument("user_id"); s.set_defaults(func=cmd_groups_add_member)
    s = g.add_parser("remove-member"); s.add_argument("id"); s.add_argument("user_id"); s.set_defaults(func=cmd_groups_remove_member)
    s = g.add_parser("create"); s.add_argument("--name", required=True); s.add_argument("--nickname"); s.add_argument("--description"); s.add_argument("--mail-enabled", action="store_true"); s.set_defaults(func=cmd_groups_create)

    # Teams
    t = sub.add_parser("teams").add_subparsers(dest="sub")
    s = t.add_parser("list"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_teams_list)
    s = t.add_parser("get"); s.add_argument("id"); s.set_defaults(func=cmd_teams_get)
    s = t.add_parser("channels"); s.add_argument("id"); s.set_defaults(func=cmd_teams_channels)
    s = t.add_parser("members"); s.add_argument("id"); s.set_defaults(func=cmd_teams_members)
    s = t.add_parser("add-member"); s.add_argument("id"); s.add_argument("user_id"); s.add_argument("--owner", action="store_true"); s.set_defaults(func=cmd_teams_add_member)
    s = t.add_parser("create-channel"); s.add_argument("id"); s.add_argument("--name", required=True); s.add_argument("--description"); s.add_argument("--type", default="standard", choices=["standard","private","shared"]); s.set_defaults(func=cmd_teams_create_channel)

    # Licenses
    l = sub.add_parser("licenses").add_subparsers(dest="sub")
    l.add_parser("list").set_defaults(func=cmd_licenses_list)
    s = l.add_parser("user"); s.add_argument("id"); s.set_defaults(func=cmd_licenses_user)
    s = l.add_parser("assign"); s.add_argument("id"); s.add_argument("sku_id"); s.set_defaults(func=cmd_licenses_assign)
    s = l.add_parser("remove"); s.add_argument("id"); s.add_argument("sku_id"); s.set_defaults(func=cmd_licenses_remove)

    # Roles
    r = sub.add_parser("roles").add_subparsers(dest="sub")
    r.add_parser("list").set_defaults(func=cmd_roles_list)
    s = r.add_parser("members"); s.add_argument("id"); s.set_defaults(func=cmd_roles_members)

    # Audit
    a = sub.add_parser("audit").add_subparsers(dest="sub")
    s = a.add_parser("signins"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_audit_signins)
    s = a.add_parser("directory"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_audit_directory)

    # Devices
    d = sub.add_parser("devices").add_subparsers(dest="sub")
    s = d.add_parser("list"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_devices_list)

    # Domains
    sub.add_parser("domains").set_defaults(func=cmd_domains_list)

    # Organization
    sub.add_parser("org").set_defaults(func=cmd_org_get)

    # Security
    sec = sub.add_parser("security").add_subparsers(dest="sub")
    s = sec.add_parser("alerts"); s.add_argument("--top", type=int); s.set_defaults(func=cmd_security_alerts)
    sec.add_parser("score").set_defaults(func=cmd_security_score)

    # Raw
    s = sub.add_parser("raw"); s.add_argument("method"); s.add_argument("path"); s.add_argument("--body"); s.set_defaults(func=cmd_raw)

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
