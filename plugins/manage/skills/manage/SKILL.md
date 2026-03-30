---
name: manage
description: >
  This skill should be used when the user asks to "manage sessions",
  "fix a skill", "patch a plugin", "create a user", "manage M365 tenant",
  "list sessions", "deploy a plugin", "assign license", "audit logs",
  or any administration/management task for sessions, skills, or M365.
---

# Manage

Meta-skill that routes to the appropriate management sub-skill.

## Sub-skills

| Sub-skill | Scope |
|-----------|-------|
| manage-sessions | Claude Code session folders: sync, list, resume, rename, cleanup |
| manage-skills | Plugin skills: review feedback, patch, test, rebuild, deploy |
| manage-m365 | M365 tenant admin: Users, Groups, Teams, Licenses, Audit, Security |

## Routing

- **Sessions** (sync, list, resume, rename, delete empty) → `manage-sessions`
- **Skills/plugins** (fix, patch, update, deploy, rebuild) → `manage-skills`
- **M365 admin** (users, groups, teams, licenses, audit, security) → `manage-m365`
