"""ONE-TIME SETUP — creates environment, vault, uploads skills, creates agent.

Writes agent_config.json with the IDs the runtime script loads.
"""

import json
import os
from pathlib import Path
from anthropic import Anthropic

client = Anthropic()

# --- 1. Environment ---------------------------------------------------------
env = client.beta.environments.create(
    name="research-dashboard-env",
    config={"type": "cloud", "networking": {"type": "unrestricted"}},
)
print(f"env:   {env.id}")

# --- 2. Vault + MCP credentials --------------------------------------------
vault = client.beta.vaults.create(display_name="research-dashboard-vault")
print(f"vault: {vault.id}")

KARELIN_PSK = os.environ["MCP_KARELIN_PSK"]
FAR_FUTURE = "2099-12-31T00:00:00Z"

# Gateway accepts OAuth Bearer — store PSK as a bearer-style access_token, no refresh.
for name, url in [
    ("Obsidian", "https://mcp.karelin.ai/obsidian"),
    ("Neo4j",    "https://mcp.karelin.ai/neo4j"),
    ("M365",     "https://mcp.karelin.ai/m365"),
]:
    client.beta.vaults.credentials.create(
        vault_id=vault.id,
        display_name=f"{name} PSK",
        auth={
            "type": "mcp_oauth",
            "mcp_server_url": url,
            "access_token": KARELIN_PSK,
            "expires_at": FAR_FUTURE,
        },
    )

# Atlassian is real OAuth — requires the initial token dance beforehand.
if os.environ.get("ATLASSIAN_ACCESS_TOKEN"):
    client.beta.vaults.credentials.create(
        vault_id=vault.id,
        display_name="Atlassian OAuth",
        auth={
            "type": "mcp_oauth",
            "mcp_server_url": "https://mcp.atlassian.com/v1/mcp",
            "access_token": os.environ["ATLASSIAN_ACCESS_TOKEN"],
            "expires_at": os.environ.get("ATLASSIAN_EXPIRES_AT", FAR_FUTURE),
            "refresh": {
                "refresh_token": os.environ["ATLASSIAN_REFRESH_TOKEN"],
                "client_id": os.environ["ATLASSIAN_CLIENT_ID"],
                "token_endpoint": "https://auth.atlassian.com/oauth/token",
                "token_endpoint_auth": {"type": "none"},
            },
        },
    )

# --- 3. Upload every SKILL.md under plugins/ --------------------------------
PLUGINS_DIR = Path(__file__).resolve().parents[2] / "plugins"
skill_md_paths = sorted(PLUGINS_DIR.rglob("SKILL.md"))
print(f"skills: {len(skill_md_paths)} SKILL.md files found")

skill_ids: dict[str, str] = {}
failures: list[tuple[str, str]] = []

for skill_md in skill_md_paths:
    root = skill_md.parent
    # Files that belong to a nested skill are uploaded separately — exclude them here.
    nested_roots = {p.parent for p in root.rglob("SKILL.md") if p != skill_md}

    files_payload = []
    for f in sorted(root.rglob("*")):
        if f.is_dir() or any(nr in f.parents for nr in nested_roots):
            continue
        rel = f.relative_to(root).as_posix()
        files_payload.append((rel, f.read_bytes(), "application/octet-stream"))

    try:
        skill = client.beta.skills.create(files=files_payload)
        skill_ids[root.name] = skill.id
        print(f"  ok   {root.name:30s} -> {skill.id}")
    except Exception as e:
        failures.append((root.name, str(e)[:200]))
        print(f"  FAIL {root.name:30s}  {e!s:.120}")

# --- 4. Agent ---------------------------------------------------------------
SYSTEM = (
    "You are a research agent with access to Alex's personal knowledge sources: "
    "Obsidian vault, Neo4j knowledge graph, M365 (email/OneDrive/Teams/Calendar), "
    "Atlassian (Jira/Confluence), and the open web. For each research task: "
    "(1) decide which sources are relevant, (2) search in parallel, (3) synthesize "
    "findings with citations, (4) write a self-contained HTML dashboard to "
    "/mnt/session/outputs/report.html with inline CSS and a sources section."
)

agent = client.beta.agents.create(
    name="research-dashboard",
    model="claude-opus-4-7",
    system=SYSTEM,
    tools=[
        {"type": "agent_toolset_20260401", "default_config": {"enabled": True}},
        {"type": "mcp_toolset", "mcp_server_name": "Obsidian"},
        {"type": "mcp_toolset", "mcp_server_name": "Neo4j"},
        {"type": "mcp_toolset", "mcp_server_name": "M365"},
        {"type": "mcp_toolset", "mcp_server_name": "atlassian"},
    ],
    mcp_servers=[
        {"type": "url", "name": "Obsidian",  "url": "https://mcp.karelin.ai/obsidian"},
        {"type": "url", "name": "Neo4j",     "url": "https://mcp.karelin.ai/neo4j"},
        {"type": "url", "name": "M365",      "url": "https://mcp.karelin.ai/m365"},
        {"type": "url", "name": "atlassian", "url": "https://mcp.atlassian.com/v1/mcp"},
    ],
    skills=[
        {"type": "custom", "skill_id": sid, "version": "latest"}
        for sid in skill_ids.values()
    ],
)
print(f"agent: {agent.id} (version {agent.version})")

# --- 5. Persist config for runtime -----------------------------------------
config_path = Path(__file__).parent / "agent_config.json"
config_path.write_text(json.dumps({
    "environment_id": env.id,
    "vault_id": vault.id,
    "agent_id": agent.id,
    "agent_version": agent.version,
    "skill_ids": skill_ids,
    "skill_failures": failures,
}, indent=2))
print(f"\nwrote {config_path.name}. {len(skill_ids)} skills uploaded, {len(failures)} failed.")
