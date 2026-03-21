"""DA Rich TUI — Console-based REPL with Rich rendering.

A lighter alternative to the full Textual TUI. Uses Rich Console for
output and prompt_toolkit for input. No Textual dependency.

Launch: da rich
"""

import os
import uuid

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory

from da import __version__
from da.config import load_config, Config
from da.client import get_client, call_agent
from da.agents.orchestrator import get_system_prompt
from da.tools import ALL_TOOL_DEFS, execute_tool
from da.session import SessionStore
from da.rich_render import (
    console,
    render_banner,
    render_message,
    render_tool,
    query_panel,
    result_panel,
    session_info_table,
)

BANNER = r"""
      ░████             ░██        ░██░██       ░███                                        ░██
    ░██  ░██            ░██           ░██      ░██░██                                       ░██
   ░██   ░██  ░███████  ░████████  ░██░██     ░██  ░██   ░████████  ░███████  ░████████  ░████████
  ░██    ░██ ░██    ░██ ░██    ░██ ░██░██    ░█████████ ░██    ░██ ░██    ░██ ░██    ░██    ░██
  ░██    ░██ ░█████████ ░██    ░██ ░██░██    ░██    ░██ ░██    ░██ ░█████████ ░██    ░██    ░██
  ░██    ░██ ░██        ░███   ░██ ░██░██    ░██    ░██ ░██   ░███ ░██        ░██    ░██    ░██
  ░█████████  ░███████  ░██░█████  ░██░██    ░██    ░██  ░█████░██  ░███████  ░██    ░██     ░████
░██        ░██                                                 ░██
Агент который только говорит ДА                          ░███████
"""

MODELS = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}


def _handle_slash(cmd: str, cfg: Config, store: SessionStore, session_id: str) -> bool:
    """Handle slash commands. Returns True if handled."""
    parts = cmd.split(None, 1)
    verb = parts[0].lower()

    if verb in ("/quit", "/exit", "/q"):
        return False  # signal exit

    if verb in ("/help", "/"):
        console.print(render_tool(
            "/model [name] \u2014 switch model\n"
            "  /tools \u2014 list tools\n"
            "  /hosts \u2014 list hosts\n"
            "  /stats \u2014 current session stats\n"
            "  /clear \u2014 clear screen\n"
            "  /quit \u2014 exit"
        ))
    elif verb == "/model":
        if len(parts) > 1 and parts[1].strip().lower() in MODELS:
            cfg.model = MODELS[parts[1].strip().lower()]
            console.print(render_tool(f"Model: {cfg.model}"))
        elif len(parts) > 1:
            cfg.model = parts[1].strip()
            console.print(render_tool(f"Model: {cfg.model}"))
        else:
            lines = [f"Current: {cfg.model}"]
            for alias, model in MODELS.items():
                lines.append(f"  /model {alias} \u2014 {model}")
            console.print(render_tool("\n".join(lines)))
    elif verb == "/tools":
        lines = [f"{t['name']:18s} {t['description'][:50]}" for t in ALL_TOOL_DEFS]
        console.print(render_tool("\n".join(lines)))
    elif verb == "/hosts":
        lines = [f"{n:15s} {h.ssh} [{', '.join(h.roles)}]" for n, h in cfg.hosts.items()]
        console.print(render_tool("\n".join(lines)))
    elif verb == "/stats":
        stats = store.get_session_stats(session_id)
        if stats:
            import datetime
            created = datetime.datetime.fromtimestamp(stats["created_at"]).strftime("%Y-%m-%d %H:%M") if stats["created_at"] else "?"
            rows = [
                ("Session", session_id[:12]),
                ("Name", stats["name"] or "\u2014"),
                ("Created", created),
                ("Messages", str(stats["total_messages"])),
            ]
            console.print(session_info_table(rows, title="DA Session", border_style="green"))
        else:
            console.print(render_tool("No stats yet."))
    elif verb == "/clear":
        console.clear()
    else:
        console.print(render_tool(f"Unknown: {verb}. Type /help"))

    return True


def _run_agent_loop(cfg, client, system_prompt, api_tools, api_messages):
    """Run the agent loop, printing tool calls and returning final text."""
    for _ in range(20):
        response = call_agent(client, cfg, system_prompt, api_messages, api_tools)

        assistant_content = []
        text_parts = []
        tool_uses = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                tool_uses.append(block)
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        api_messages.append({"role": "assistant", "content": assistant_content})

        if not tool_uses:
            return "\n".join(text_parts)

        tool_results = []
        for tu in tool_uses:
            console.print(render_tool(tu.name))
            result = execute_tool(tu.name, tu.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": str(result),
            })

        api_messages.append({"role": "user", "content": tool_results})

    return "[max tool iterations reached]"


def run_rich_tui(config: Config | None = None):
    """Main Rich REPL loop."""
    cfg = config or load_config()
    store = SessionStore(cfg.session.db_path)
    client = get_client(cfg)
    system_prompt = get_system_prompt(cfg)
    api_tools = [
        {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
        for t in ALL_TOOL_DEFS
    ]

    session_id = str(uuid.uuid4())
    store.create_session(session_id, name="rich session", project=os.getcwd())
    api_messages: list[dict] = []

    console.print(render_banner(BANNER, __version__, cfg.model, len(api_tools)))

    prompt_session = PromptSession(history=InMemoryHistory())

    while True:
        try:
            text = prompt_session.prompt(
                HTML("<ansigreen><b>you</b></ansigreen> <ansigray>\u203a</ansigray> "),
            ).strip()
        except (EOFError, KeyboardInterrupt):
            console.print(render_tool("bye"))
            break

        if not text:
            continue

        if text.startswith("/"):
            if not _handle_slash(text, cfg, store, session_id):
                console.print(render_tool("bye"))
                break
            continue

        # Name session from first message
        if not any(m.get("role") == "user" for m in api_messages):
            store.conn.execute(
                "UPDATE sessions SET name = ? WHERE id = ?",
                (text[:60], session_id),
            )
            store.conn.commit()

        console.print(render_message("user", text))
        store.add_message(session_id, "user", text)
        api_messages.append({"role": "user", "content": text})

        try:
            with console.status("[bold green]Thinking..."):
                result = _run_agent_loop(cfg, client, system_prompt, api_tools, api_messages)

            store.add_message(session_id, "assistant", result)
            console.print(render_message("assistant", result))

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
