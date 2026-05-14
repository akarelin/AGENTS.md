---
name: administer
description: >
  Cloud and tenant administration router. Use when the user needs to
  administer M365 tenant (users, groups, licenses), manage GCP resources,
  redeploy Portainer Docker stacks, or perform other cloud admin tasks.
---

# Administer

Cloud and tenant administration.

## Sub-skills

| Skill | Platform | Description |
|-------|----------|-------------|
| admin-m365 | Microsoft 365 | Tenant admin: users, groups, teams, licenses, audit, security |
| admin-gcp | Google Cloud | Project and resource management, IAM, compute, storage |
| admin-portainer | Portainer | Docker Compose stack deploys on the karel.in fleet |

## Routing

- **"M365", "users", "groups", "licenses", "teams admin", "tenant"** → admin-m365
- **"GCP", "Google Cloud", "VM", "bucket", "IAM", "service account"** → admin-gcp
- **"Portainer", "redeploy stack", "compose deploy", "roll image", host names (seven/kolme/five/trix/kiiro)** → admin-portainer
