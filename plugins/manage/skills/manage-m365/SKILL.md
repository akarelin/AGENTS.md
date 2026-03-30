---
name: manage-m365
description: "Microsoft 365 tenant administration via Graph beta API. Use when the user mentions: create user, delete user, reset password, add to group, remove from group, invite guest, manage team, assign license, audit log, sign-in logs, directory roles, security alerts, secure score, list users, list groups, manage devices, tenant admin."
user-invocable: true
argument-hint: "<command> [subcommand] [options]"
allowed-tools:
  - Bash
  - Read
  - Skill(get-secret)
version: 0.1.0
---

# /m365-admin — Tenant Administration

Microsoft 365 tenant administration via Graph beta API with application permissions.
No user login required — uses client credentials. Full admin: Users, Groups, Teams, Licenses, Directory, Audit, Devices, Security.

Arguments passed: $ARGUMENTS

**Restriction**: Only Alex should use this skill (admin operations).

## Authentication

Application permissions via client credentials flow — no interactive login needed.

**Credentials**: Use `/get-secret` to retrieve from Azure Key Vault:
- `alex-graph-app-id` → set as `GRAPH_ADMIN_CLIENT_ID`
- `alex-graph-client-secret` → set as `GRAPH_ADMIN_CLIENT_SECRET`
- Tenant ID: `052461ba-115a-49f9-8564-1857461f2161` → set as `GRAPH_ADMIN_TENANT_ID`

Or configure `tenants.json` alongside the script.

**App Registration**: Alex Graph API (App ID: 9fa6f2a3-c2f8-4bd2-9dfb-d84f54169e7c, 41 application permissions)

## CLI Reference

The script is at `${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py`. Run via:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" [--tenant TENANT] <command> [subcommand] [options]
```

If $ARGUMENTS is provided, parse and execute the matching command below.
If no arguments, show available commands.

### Users
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" users list [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" users search "query" [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" users get USER_ID_OR_UPN
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" users create --name "Jane Doe" --upn "jane@karelin.com" --password "TempPass123!" [--first Jane] [--last Doe] [--job "Engineer"] [--department "IT"]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" users update USER_ID --json '{"jobTitle":"Sr Engineer"}'
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" users disable USER_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" users enable USER_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" users delete USER_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" users reset-pw USER_ID --password "NewPass456!"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" users invite --email "guest@external.com" [--name "Guest Name"] [--no-email]
```

### Groups
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" groups list [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" groups search "query" [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" groups get GROUP_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" groups members GROUP_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" groups add-member GROUP_ID USER_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" groups remove-member GROUP_ID USER_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" groups create --name "New Group" [--nickname "newgroup"] [--description "..."] [--mail-enabled]
```

### Teams
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" teams list [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" teams get TEAM_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" teams channels TEAM_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" teams members TEAM_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" teams add-member TEAM_ID USER_ID [--owner]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" teams create-channel TEAM_ID --name "Channel" [--type standard|private|shared] [--description "..."]
```

### Licenses
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" licenses list
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" licenses user USER_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" licenses assign USER_ID SKU_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" licenses remove USER_ID SKU_ID
```

### Directory Roles
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" roles list
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" roles members ROLE_ID
```

### Audit Logs
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" audit signins [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" audit directory [--top N]
```

### Devices
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" devices list [--top N]
```

### Domains / Org
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" domains
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" org
```

### Security
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" security alerts [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" security score
```

### Raw Graph API
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" raw GET "/users?$top=5"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/m365_admin.py" raw POST "/invitations" --body '{"invitedUserEmailAddress":"a@b.com","inviteRedirectUrl":"https://teams.microsoft.com","sendInvitationMessage":true}'
```

## Implementation Notes

- All API calls use Graph beta endpoint
- Application permissions (no user context) — operates as the app identity
- Output is JSON (pretty-printed)
- Requires `msal` and `requests` Python packages
- Destructive operations (delete, disable) should be confirmed with the user before execution
