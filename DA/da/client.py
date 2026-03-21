"""Anthropic API client wrapper for DeepAgents."""

import os
from typing import Any

import anthropic

from da.config import Config


def get_client(config: Config) -> anthropic.Anthropic:
    """Create Anthropic client from config/env."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Export it or add to .env file."
        )
    return anthropic.Anthropic(api_key=api_key)


def call_agent(
    client: anthropic.Anthropic,
    config: Config,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None,
) -> anthropic.types.Message:
    """Make a single agent call with tools."""
    kwargs: dict[str, Any] = {
        "model": model or config.model,
        "max_tokens": config.max_tokens,
        "system": system,
        "messages": messages,
    }
    if config.temperature is not None:
        kwargs["temperature"] = config.temperature
    if tools:
        kwargs["tools"] = tools

    return client.messages.create(**kwargs)


def run_agent_loop(
    client: anthropic.Anthropic,
    config: Config,
    system: str,
    user_message: str,
    tools: list[dict[str, Any]],
    tool_executor: Any,
    max_iterations: int = 20,
) -> str:
    """Run an agentic loop: call model -> execute tools -> repeat until done."""
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

    for _ in range(max_iterations):
        response = call_agent(client, config, system, messages, tools)

        # Collect assistant content
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

        messages.append({"role": "assistant", "content": assistant_content})

        # If no tool calls, we're done
        if not tool_uses:
            return "\n".join(text_parts)

        # Execute tools and collect results
        tool_results = []
        for tool_use in tool_uses:
            result = tool_executor(tool_use.name, tool_use.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": str(result),
            })

        messages.append({"role": "user", "content": tool_results})

    return "\n".join(text_parts) if text_parts else "(max iterations reached)"
