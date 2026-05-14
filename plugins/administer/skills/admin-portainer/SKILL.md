---
name: admin-portainer
description: >
  Portainer-based Docker stack deployments. Use when the user mentions
  Portainer, redeploying a stack, updating a compose file in
  production, rolling a container image, or any Docker Compose deploy
  managed through Portainer.
allowed-tools: [Bash, Read, Skill(get-secret)]
---

# Portainer Administration

Docker Compose stack management via portainer API at <https://portainer.{localdomain}>.

## Repo rule

**All Docker Compose deployment goes through Portainer.** Do not
`docker compose up` directly on hosts. Update the compose file in the
service's source repo, then call the Portainer API to redeploy.

## Auth

API key from Azure Key Vault — fetch with `/get-secret`:

- Secret name: `portainer-api-key` (format: `ptr_...`)
- Send as `X-API-Key: $PORTAINER_API_KEY` header
- All requests use `-k` (self-signed cert chain via `/etc/ssl`)

In GitHub Actions the key is `secrets.PORTAINER_API_KEY`.

Resolve to numeric IDs at runtime — don't hardcode.

## Core API pattern

Every redeploy is the same four steps:

```bash
# 1. Resolve endpoint name → ID
ENDPOINT_ID=$(curl -fsSk -H "X-API-Key: $PORTAINER_API_KEY" \
  "$PORTAINER_URL/api/endpoints" \
  | jq -r --arg n "$ENDPOINT_NAME" '.[] | select(.Name==$n) | .Id')

# 2. Resolve stack name → ID (scoped to the endpoint)
STACK_ID=$(curl -fsSk -H "X-API-Key: $PORTAINER_API_KEY" \
  "$PORTAINER_URL/api/stacks" \
  | jq -r --arg n "$STACK_NAME" --argjson e "$ENDPOINT_ID" \
      '.[] | select(.Name==$n and .EndpointId==$e) | .Id')

# 3. Fetch current stack JSON (for the existing Env array)
STACK_JSON=$(curl -fsSk -H "X-API-Key: $PORTAINER_API_KEY" \
  "$PORTAINER_URL/api/stacks/$STACK_ID")

# 4. PUT updated compose + preserved env
jq -n \
  --rawfile compose "$COMPOSE_PATH" \
  --argjson env "$(echo "$STACK_JSON" | jq '.Env')" \
  '{StackFileContent: $compose, Env: $env, Prune: false, PullImage: true}' \
  > body.json
curl -fsSk -X PUT \
  -H "X-API-Key: $PORTAINER_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @body.json \
  "$PORTAINER_URL/api/stacks/$STACK_ID?endpointId=$ENDPOINT_ID" \
  | jq '{Id, Name, Status, DeploymentStartStatus}'
```

`PullImage: true` makes Portainer re-pull `:latest` (or whatever tag is
in the compose); `Prune: false` keeps orphan containers from previous
versions around for inspection.

## Two redeploy strategies
### Replace from repo (default)

Use this when the repo is the source of truth for the compose file.

```bash
COMPOSE_PATH=path/to/docker-compose.yml
# Then run the core pattern above with --rawfile compose "$COMPOSE_PATH"
```

### Deep-merge with Portainer's copy

Use this when ad-hoc env or service tweaks may have been added in the
Portainer UI that you want to preserve.

```bash
# Pull Portainer's current compose
curl -fsSk -H "X-API-Key: $PORTAINER_API_KEY" \
  "$PORTAINER_URL/api/stacks/$STACK_ID/file" \
  | jq -r '.StackFileContent' > portainer-compose.yml

# Deep-merge: repo wins on overlap, Portainer-only keys preserved
yq eval-all '. as $item ireduce ({}; . * $item)' \
  portainer-compose.yml repo-compose.yml > merged-compose.yml

# Then PUT merged-compose.yml as StackFileContent
```

## Common operations

### Redeploy an existing stack (image rolled to `:latest`)

Run the core pattern above. Portainer pulls the new image and recreates
containers.

### Deploy a brand-new stack

1. Place the compose file in the service's source repo.
2. Always include: `restart: unless-stopped`, `pull_policy: always`,
   and a `healthcheck` (Portainer + Uptime Kuma both consume it).
3. Create the stack in the Portainer UI (Stacks → Add stack → Web editor
   or Repository). For subsequent updates, use the API pattern above.
4. No `.env` files — bake env into the compose or pull from the vault.

### Inspect a stack

```bash
curl -fsSk -H "X-API-Key: $PORTAINER_API_KEY" \
  "$PORTAINER_URL/api/stacks/$STACK_ID" | jq .
curl -fsSk -H "X-API-Key: $PORTAINER_API_KEY" \
  "$PORTAINER_URL/api/stacks/$STACK_ID/file" | jq -r '.StackFileContent'
```

### List endpoints / stacks

```bash
curl -fsSk -H "X-API-Key: $PORTAINER_API_KEY" \
  "$PORTAINER_URL/api/endpoints" | jq '.[] | {Id, Name}'
curl -fsSk -H "X-API-Key: $PORTAINER_API_KEY" \
  "$PORTAINER_URL/api/stacks" | jq '.[] | {Id, Name, EndpointId}'
```

### Container logs / state

Prefer the Portainer UI for tailing logs. For scripted use, the Docker
API is proxied at `$PORTAINER_URL/api/endpoints/$ENDPOINT_ID/docker/...`
(same shape as the Docker Engine API).

## Guardrails

- **Do not** `ssh <host> docker compose up` as a normal workflow. The
  one allowed escape hatch is when Portainer itself is down — and then
  ask the user to re-deploy via Portainer afterward so the stack state
  matches.
- **Do not** restart Docker or the Portainer container.
- **Do not** edit nginx configs on hosts — that goes through the
  project's nginx deploy script, not Portainer.
- Confirm with the user before destructive ops (stack delete, `Prune:
  true`, force-recreate of volumes).
- Upgrading Portainer itself uses its own upgrade procedure, not the
  stack API.
