---
name: admin-gcp
description: >
  Google Cloud Platform administration. Use when the user mentions GCP,
  Google Cloud, VMs, buckets, IAM, service accounts, Cloud Run, or
  any GCP resource management.
allowed-tools: [Bash, Read, Skill(get-secret)]
---

# GCP Administration

Google Cloud Platform resource and IAM management via `gcloud` CLI.

## Prerequisites

- `gcloud` CLI installed and authenticated (`gcloud auth login`)
- Credentials resolved from Key Vault when needed (`get_secret`)

## Capabilities

| Area | Commands |
|------|----------|
| **Projects** | `gcloud projects list`, `gcloud config set project` |
| **Compute** | `gcloud compute instances list/create/delete/start/stop` |
| **IAM** | `gcloud iam service-accounts list/create`, `gcloud projects add-iam-policy-binding` |
| **Storage** | `gcloud storage ls`, `gcloud storage cp`, `gcloud storage buckets create` |
| **Cloud Run** | `gcloud run services list/deploy/delete` |
| **Secrets** | `gcloud secrets list`, `gcloud secrets versions access` |
| **Logging** | `gcloud logging read` |
| **Billing** | `gcloud billing accounts list`, `gcloud billing projects describe` |

## Known Projects

- `ai-experiments-469513` — AI/ML experiments (Vertex AI, LiteLLM service accounts)

## Workflow

1. Verify active project with `gcloud config get project`
2. If user specifies a different project, switch with `gcloud config set project`
3. Execute requested operations
4. For destructive operations, confirm with user first
