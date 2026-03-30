# m365-admin

Microsoft 365 tenant administration via Graph beta API with application permissions.

## Installation

```
/plugin install m365-admin@akarelin-skills
```

Requires: `pip install msal requests`

## Capabilities

| Module | Operations |
|--------|-----------|
| **Users** | list, search, get, create, update, disable, enable, delete, reset-pw, invite |
| **Groups** | list, search, get, members, add-member, remove-member, create |
| **Teams** | list, get, channels, members, add-member, create-channel |
| **Licenses** | list, user, assign, remove |
| **Directory Roles** | list, members |
| **Audit Logs** | signins, directory |
| **Devices** | list |
| **Domains / Org** | domains, org |
| **Security** | alerts, score |
| **Raw Graph** | arbitrary GET/POST to any Graph endpoint |

## Authentication

Application permissions via client credentials flow — no interactive login. Admin-only.

## Usage

```bash
python3 m365_admin.py users list --top 10
python3 m365_admin.py groups members GROUP_ID
python3 m365_admin.py security score
```
