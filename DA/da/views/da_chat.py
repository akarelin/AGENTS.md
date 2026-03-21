"""ДА chat view — interactive agent conversation.

Menu: [Д]А  |  F1  |  /da
"""

import os
import uuid

from prompt_toolkit.formatted_text import HTML

from da.config import Config
from da.client import get_client, call_agent
from da.agents.orchestrator import get_system_prompt
from da.tools import ALL_TOOL_DEFS, execute_tool
from da.session import SessionStore
from da.rich_render import console, render_message, render_tool

MENU_KEY = "Д"
MENU_LABEL = "ДА"


class DAChatView:
    def __init__(self, cfg: Config, store: SessionStore):
        self.cfg = cfg
        self.store = store
        self.client = get_client(cfg)
        self.system_prompt = get_system_prompt(cfg)
        self.api_tools = [
            {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in ALL_TOOL_DEFS
        ]
        self.session_id = ""
        self.api_messages: list[dict] = []
        self.session_messages: dict[str, list[dict]] = {}

    def get_prompt(self) -> HTML:
        return HTML("<ansigreen><b>you</b></ansigreen> <ansigray>\u203a</ansigray> ")

    def new_session(self, name: str = "rich session") -> None:
        self.session_id = str(uuid.uuid4())
        self.store.create_session(self.session_id, name=name, project=os.getcwd())
        self.api_messages = []
        self.session_messages[self.session_id] = []
        console.print(render_tool(f"New session: {self.session_id[:12]}"))

    def load_session(self, sid: str) -> bool:
        stored = self.store.get_messages(sid, limit=100)
        if stored is None:
            console.print(render_tool(f"Session {sid} not found."))
            return False
        self.session_id = sid
        self.session_messages[sid] = stored
        self.api_messages = []
        for m in stored:
            if m["role"] in ("user", "assistant"):
                self.api_messages.append({"role": m["role"], "content": m["content"]})
        console.print(render_tool(f"Loaded session: {sid[:12]} ({len(stored)} messages)"))
        return True

    def handle_input(self, text: str) -> None:
        """Handle user chat input — send to agent."""
        # Name session from first message
        if not any(m.get("role") == "user" for m in self.api_messages):
            self.store.conn.execute(
                "UPDATE sessions SET name = ? WHERE id = ?",
                (text[:60], self.session_id),
            )
            self.store.conn.commit()

        console.print(render_message("user", text))
        self.store.add_message(self.session_id, "user", text)
        self.session_messages.setdefault(self.session_id, []).append(
            {"role": "user", "content": text}
        )
        self.api_messages.append({"role": "user", "content": text})
        self._run_agent()

    def show(self) -> None:
        """Called when switching to this view."""
        pass  # ДА view doesn't need to redraw on switch

    def _run_agent(self) -> None:
        try:
            with console.status("[bold green]Thinking..."):
                result = self._agent_loop()
            self.store.add_message(self.session_id, "assistant", result)
            self.session_messages.setdefault(self.session_id, []).append(
                {"role": "assistant", "content": result}
            )
            console.print(render_message("assistant", result))
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

    def _agent_loop(self) -> str:
        for _ in range(20):
            response = call_agent(
                self.client, self.cfg, self.system_prompt, self.api_messages, self.api_tools
            )

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

            self.api_messages.append({"role": "assistant", "content": assistant_content})

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

            self.api_messages.append({"role": "user", "content": tool_results})

        return "[max tool iterations reached]"
