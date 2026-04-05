---
name: manage
description: >
  This skill should be used when the user asks to "create a user",
  "manage M365 tenant", "assign license", "audit logs",
  or any M365 tenant administration task.
  Note: sessions and skills are now under AC plugin.
---

# Manage

M365 tenant administration.

## Sub-skills

| Sub-skill | Scope |
|-----------|-------|
| manage-m365 | M365 tenant admin: Users, Groups, Teams, Licenses, Audit, Security |

## Routing

- **M365 admin** (users, groups, teams, licenses, audit, security) → `manage-m365`
- **Sessions** → use AC `session` tool
- **Skills/plugins** → use AC `skill` tool
