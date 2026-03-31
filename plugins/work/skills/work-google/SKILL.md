---
name: work-google
description: "Personal Google account operations. Use when the user mentions: gmail, google drive, google email, my personal email, google docs, google sheets, search my drive, send personal email, check gmail, download from drive."
user-invocable: true
argument-hint: "<command> [subcommand] [options]"
allowed-tools:
  - Bash
  - Read
---

# Google Gmail & Drive — Personal Account

Access personal Gmail and Google Drive via OAuth2 user credentials.

Arguments passed: $ARGUMENTS

## Setup

All secrets stored in Azure Key Vault (via gppu):
- `google-oauth-client-id` — OAuth2 client ID
- `google-oauth-client-secret` — OAuth2 client secret
- `google-oauth-token` — OAuth2 token JSON (auto-managed)

First-time auth:
1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" login` (opens browser for consent)
2. Token is saved to Key Vault automatically (persists across machines, auto-refreshes)

To import an existing token from another machine:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" add-token '{"token": "...", "refresh_token": "...", ...}'
```

Requires: `pip install google-api-python-client google-auth-oauthlib gppu`

## CLI Reference

The script is at `${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py`. Run via:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" <command> [subcommand] [options]
```

If $ARGUMENTS is provided, parse and execute the matching command below.
If no arguments, show available commands.

### Auth
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" login
```

### Gmail
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" gmail list [--top N] [--label LABEL]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" gmail read MESSAGE_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" gmail thread THREAD_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" gmail search "query" [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" gmail send --to "a@b.com" --subject "Subj" --body "Body" [--cc "c@d.com"] [--html]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" gmail draft --to "a@b.com" --subject "Subj" --body "Body"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" gmail reply MESSAGE_ID --body "Reply text"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" gmail labels
```

### Drive
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" drive list [--top N] [--folder FOLDER_ID]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" drive search "query" [--top N]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" drive get FILE_ID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" drive download FILE_ID [--out PATH]
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gwork.py" drive mkdir "Folder Name" [--parent PARENT_ID]
```

## Implementation Notes

- OAuth2 user credentials; client ID/secret from Azure Key Vault via gppu
- Token stored in Azure Key Vault, auto-refreshes
- Output is JSON
- Gmail scopes: gmail.modify, gmail.compose, gmail.readonly
- Drive scopes: drive, drive.file
