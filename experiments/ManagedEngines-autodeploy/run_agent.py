"""PER-INVOCATION — start a session, stream events, download outputs.

Usage: python run_agent.py "your research question"
"""

import json
import sys
import time
from pathlib import Path
from anthropic import Anthropic

HERE = Path(__file__).parent
cfg = json.loads((HERE / "agent_config.json").read_text())
client = Anthropic()

session = client.beta.sessions.create(
    agent=cfg["agent_id"],
    environment_id=cfg["environment_id"],
    vault_ids=[cfg["vault_id"]],
    title=f"research: {sys.argv[1][:60] if len(sys.argv) > 1 else 'adhoc'}",
)
print(f"session: {session.id}")

kickoff = sys.argv[1] if len(sys.argv) > 1 else (
    "Research: recent progress on Claude Managed Agents. Pull related notes "
    "from my Obsidian, check Neo4j for connected topics, supplement with web "
    "search, and write the HTML dashboard to /mnt/session/outputs/report.html."
)

# Stream-first: open the stream before sending the kickoff event.
with client.beta.sessions.events.stream(session.id) as stream:
    client.beta.sessions.events.send(
        session.id,
        events=[{"type": "user.message",
                 "content": [{"type": "text", "text": kickoff}]}],
    )

    for event in stream:
        t = event.type
        if t == "agent.message":
            for block in event.content:
                if block.type == "text":
                    print(block.text, end="", flush=True)
        elif t == "agent.tool_use":
            print(f"\n[tool: {event.name}]", flush=True)
        elif t == "agent.mcp_tool_use":
            print(f"\n[mcp: {event.server_name}.{event.name}]", flush=True)
        elif t == "session.error":
            print(f"\n[error: {event}]", flush=True)
        elif t == "session.status_terminated":
            print("\n[terminated]")
            break
        elif t == "session.status_idle":
            # Terminal idle = not waiting on us. 'requires_action' would need a reply.
            if event.stop_reason.type != "requires_action":
                print(f"\n[idle: {event.stop_reason.type}]")
                break

# Download anything the agent wrote to /mnt/session/outputs/
time.sleep(2)  # brief indexing lag after idle
out_dir = HERE / "outputs"
out_dir.mkdir(exist_ok=True)
for f in client.beta.files.list(
    scope_id=session.id,
    betas=["managed-agents-2026-04-01"],
):
    resp = client.beta.files.download(f.id)
    (out_dir / f.filename).write_bytes(resp.read())
    print(f"saved: outputs/{f.filename} ({f.size_bytes} bytes)")
