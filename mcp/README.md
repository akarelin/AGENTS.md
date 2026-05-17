# MCP Server

A multi-endpoint [Model Context Protocol](https://modelcontextprotocol.io/) server packaged as an Azure Function (Python). One container exposes several tool sets — Microsoft 365 Graph (via on-behalf-of), Azure Key Vault secrets, an Obsidian vault, Neo4j, TickTick, and a local `qmd` search index — behind a single Entra ID OAuth app. All endpoints speak Streamable HTTP (MCP protocol `2025-03-26`).

## Architecture

```
Claude.ai / Claude Code / any MCP client
        │  Authorization: Bearer <Entra JWT>
        ▼
<MCP_HOST>                            (your reverse proxy / Application Proxy)
        │  pass-through; no auth stripping
        ▼
Azure Functions container (this repo)
        │
        ├── /.well-known/*, /register, /authorize,
        │   /oauth/callback, /token                  ← OAuth shim (anonymous)
        ├── /m365, /m365-admin                       ← open tier (allowlist)
        ├── /keys, /obsidian, /neo4j, /ticktick,
        │   /qmd, /mcp, /                            ← privileged tier (allowlist + role)
        └── /docs, /icons/*                          ← anonymous
```

The function validates inbound JWTs itself against the Entra JWKS, so it works behind any pass-through proxy and does not depend on platform-managed auth.

## Authentication

A single multi-tenant Entra app registration handles everything. It publishes one delegated scope, `<SCOPE_NAME>` (default `MCP.Access`), and exposes one app role, `<ROLE_NAME>` (default `MCP.Privileged`).

The flow is standard OAuth 2.0 authorization code with PKCE, brokered by this server so MCP clients see a normal `.well-known/oauth-authorization-server` discovery document:

1. Client hits any MCP endpoint without a Bearer → server returns `401` with `WWW-Authenticate: Bearer resource_metadata=…`.
2. Client fetches `.well-known/oauth-protected-resource` and `.well-known/oauth-authorization-server` and discovers `/authorize`, `/token`, `/register`.
3. Client `POST /register` (RFC 7591 DCR stub) — server returns its fixed Entra `client_id` so the caller can proceed without per-client registration in Entra.
4. Client `GET /authorize` with its own PKCE pair. The server stashes the caller's PKCE challenge, mints a fresh state nonce, and `302`s to Entra's `/authorize` with its own PKCE pair and the requested scope `<SCOPE_NAME>`.
5. User signs in at Microsoft. Entra `302`s back to `/oauth/callback?code=…`.
6. Server exchanges the code for tokens via MSAL using the confidential-client secret, mints an opaque code keyed to the real Entra token, and `302`s back to the client's `redirect_uri`.
7. Client `POST /token` with the opaque code + its PKCE verifier → server verifies PKCE and returns the Entra-issued JWT. `refresh_token` grants are proxied to Entra.

Every subsequent tool call must carry `Authorization: Bearer <jwt>`. The server validates:

- RS256 signature against the issuing tenant's `discovery/v2.0/keys` (cached 1 h)
- `aud` equals the configured `<CLIENT_ID>`
- `iss` equals `https://login.microsoftonline.com/<tid>/v2.0`
- `oid` claim is present and appears in the allowlist loaded from vault

## Authorization

Two tiers, both enforced in the same auth path:

| Tier | Endpoints | Requirement |
|---|---|---|
| Open | `/m365`, `/m365-admin` | `oid` in the allowlist. Per-user permission boundaries are enforced downstream by Microsoft Graph. |
| Privileged | `/keys`, `/obsidian`, `/neo4j`, `/ticktick`, `/qmd`, `/mcp`, `/` (alias) | Allowlist plus the `<ROLE_NAME>` app role in the JWT `roles` claim. Assign per-user in Entra. |

The role is assigned in Entra against the application's service principal; users must sign in again for a newly-assigned role to appear in their token.

## Microsoft Graph via on-behalf-of

The backend never calls Graph with its own identity. For every Graph request:

1. The validated user JWT is stashed in a `ContextVar` per request.
2. `graph_client.get_token()` reads it and calls `msal.acquire_token_on_behalf_of(user_assertion=<jwt>, scopes=["https://graph.microsoft.com/.default"])` using the app's confidential-client credentials.
3. Graph returns a token bound to the caller's identity (cached for ~1 h, keyed by SHA-256 of the assertion).
4. The Graph request runs with that token, so `/me/...` resolves natively and Graph itself enforces what each user can read or write.

Consequence: there is no `user=<someone-else>` override. A user cannot read another user's mailbox by passing a parameter — Graph will reject the call because the OBO token is bound to the original caller.

## Endpoints

| Path | Tier | Description |
|---|---|---|
| `/m365` | open | M365 user tools via Graph OBO: mail (list/read/search/send/draft/reply/folders), calendar (list/today/search/create/delete), Teams chats and channels (list/messages/send/search), OneDrive files (list/search), To Do tasks, contacts, OneNote notebooks, presence, unified `/search/query`. |
| `/m365-admin` | open | Read-only tenant inventory via Graph: users, groups (and members), domains, subscribed SKUs and per-user licences, devices, directory roles (and members), organisation info. Each user only sees what their own roles permit. |
| `/keys` | privileged | `secret_get`, `secret_list`, `secret_create`, `secret_update` against the configured Azure Key Vault. |
| `/obsidian` | privileged | Read/write to a local Obsidian vault via the [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin: list, read, write, append, patch (by heading / block-reference / frontmatter-key), delete, open, run command, simple search, Dataview DQL search, tags, active note, daily note get/append. Tries each configured host in order and caches the one that responds. |
| `/neo4j` | privileged | Auto-discovers Neo4j servers from vault secrets of the form `neo4j-<server>-uri` / `neo4j-<server>-password`. Tools: `neo4j_list_servers`, `neo4j_use_server`, `read_neo4j_cypher`, `write_neo4j_cypher`, `get_neo4j_schema`. |
| `/ticktick` | privileged | TickTick projects and tasks (`tt_lists`, `tt_tasks`, `tt_create`, `tt_update`, `tt_complete`, `tt_abandon`). Accepts natural-language due dates (`today`, `tomorrow`, `in N days`, `next monday`, ISO 8601). |
| `/qmd` | privileged | Wraps a local `qmd` CLI (hybrid BM25 + vector index): `qmd_search`, `qmd_vsearch`, `qmd_get`, `qmd_status`. |
| `/mcp`, `/` | privileged | Aggregate endpoint exposing every tool from every module above. |

Each endpoint also responds to `GET` with a JSON manifest (transport, protocol version, tool name list) for clients that want to introspect before authenticating.

## Environment variables

| Variable | Purpose |
|---|---|
| `MCP_BASE_URL` | Public base URL the OAuth shim advertises in discovery documents and uses as its own redirect URI. Required. |
| `MCP_AUTH_MODE` | `entra` (validate JWT — production), `disabled` (no auth — dev only). Defaults to `psk`, which is now a stub that rejects all requests; set explicitly. |
| `AZURE_KEYVAULT_NAME` | Name of the Azure Key Vault the container reads all secrets from. The container's identity must have `get` (and `list`/`set` for `/keys` write tools) on the vault. |
| `MCP_TOOL_TEXT_LIMIT` | Max characters per tool response before truncation. Default `12000`. |
| `MCP_DEFAULT_USER` | Legacy default for the (now-ignored) `user` parameter on M365 tools. |
| `OBSIDIAN_HOSTS` | Comma-separated host list for the Obsidian Local REST API. Tried in order. |
| `OBSIDIAN_PORT` | Port for the Obsidian REST API. Default `27123`. |
| `OBSIDIAN_SCHEME` | `http` or `https`. Default `http`. (Self-signed certs are accepted.) |
| `OBSIDIAN_API_KEY` | Bearer token printed by the Obsidian Local REST API plugin. |
| `TICKTICK_CLIENT_ID` / `TICKTICK_CLIENT_SECRET` | OAuth credentials for TickTick. |
| `TICKTICK_ACCESS_TOKEN` / `TICKTICK_REFRESH_TOKEN` | TickTick tokens. The current build expects a pre-obtained access token. |
| `QMD_BIN` | Path to the `qmd` binary. |
| `QMD_XDG_CONFIG` / `QMD_XDG_CACHE` | XDG dirs passed to the `qmd` subprocess. |
| `QMD_TIMEOUT` | Subprocess timeout in seconds. Default `30`. |

## Vault secrets

The container resolves all sensitive configuration from Key Vault at runtime. Names below; values stay in vault.

| Secret name | Purpose |
|---|---|
| `mcp-entra-tenant-id` | Entra tenant id for the OAuth shim and OBO exchange. |
| `mcp-entra-client-id` | Application (client) id of the Entra app registration. |
| `mcp-entra-client-secret` | Confidential-client secret used for the `/oauth/callback` token exchange and for OBO. |
| `mcp-entra-resource-audience` | Identifier URI of the same app (e.g. `api://<MCP_HOST>`), used to construct the requested scope. |
| `mcp-allowed-oids` | Comma-separated list of Entra `oid` values permitted to call the server. |
| `neo4j-<server>-uri`, `neo4j-<server>-password` | One pair per Neo4j server. The `/neo4j` endpoint auto-discovers them. |

## Quick start

### Local dev (no auth)

```bash
pip install -r requirements.txt
export MCP_AUTH_MODE=disabled
export MCP_BASE_URL=http://localhost:7071
# Optional, only if you want to exercise tools that read vault:
export AZURE_KEYVAULT_NAME=<VAULT_NAME>
az login    # so DefaultAzureCredential can resolve

func start
```

Point an MCP client at `http://localhost:7071/mcp` (or any per-module path).

### Container

```bash
docker build -t mcp-server .
docker run --rm -p 7071:80 \
  -e MCP_AUTH_MODE=entra \
  -e MCP_BASE_URL=https://<MCP_HOST> \
  -e AZURE_KEYVAULT_NAME=<VAULT_NAME> \
  mcp-server
```

The image is a standard `mcr.microsoft.com/azure-functions/python` base; deploy it wherever you run containers (Azure Container Apps, Container Instances, plain Docker, etc.). Front it with TLS termination at `<MCP_HOST>`; the function should receive `Authorization` headers untouched.

### Client config

Point an MCP-aware client at any endpoint URL. Clients that support OAuth discovery (Claude.ai, Claude Code) will walk the flow automatically:

```bash
claude mcp add my-keys https://<MCP_HOST>/keys
```

Or wire individual endpoints into a static config:

```json
{
  "mcpServers": {
    "M365":      {"type": "http", "url": "https://<MCP_HOST>/m365"},
    "Keys":      {"type": "http", "url": "https://<MCP_HOST>/keys"},
    "Obsidian":  {"type": "http", "url": "https://<MCP_HOST>/obsidian"},
    "Neo4j":     {"type": "http", "url": "https://<MCP_HOST>/neo4j"},
    "TickTick":  {"type": "http", "url": "https://<MCP_HOST>/ticktick"},
    "QMD":       {"type": "http", "url": "https://<MCP_HOST>/qmd"}
  }
}
```

## Entra setup (one-time)

In your tenant, create an app registration with:

- **Supported account types:** Accounts in any organisational directory (multi-tenant).
- **Identifier URI:** `api://<MCP_HOST>`.
- **Redirect URI** (Web): `https://<MCP_HOST>/oauth/callback`.
- **Public client / native** flow: enabled (so device-code clients can use the same app).
- **Exposed API scope:** `<SCOPE_NAME>` (default `MCP.Access`).
- **App role:** `<ROLE_NAME>` (default `MCP.Privileged`), assignable to users.
- **Client secret:** create one and store its value as `mcp-entra-client-secret` in your vault.
- **API permissions (delegated Microsoft Graph):** whatever scopes you want the `/m365` tools to be able to exercise (Mail, Calendars, Files, Sites, etc.). Admin-consent them tenant-wide.

Populate the vault secrets listed above (`mcp-entra-tenant-id`, `mcp-entra-client-id`, `mcp-entra-client-secret`, `mcp-entra-resource-audience`, `mcp-allowed-oids`). Grant the container's identity `get` on the vault (and `list`/`set` if you use the `/keys` write tools).

## License

See `LICENSE`.
