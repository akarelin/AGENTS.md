"""
Session importers for external LLM exports.

Converts ChatGPT and Claude.ai export archives into the SessionManager format
(JSONL files compatible with the folder store and Langfuse deposit).

Supported:
  - OpenAI ChatGPT export (conversations.json from ZIP)
  - Anthropic Claude.ai export (JSON from ZIP)
"""

import json
import os
import zipfile
from datetime import datetime
from pathlib import Path


def import_chatgpt(source: str | Path, output_dir: str | Path) -> list[dict]:
    """Import ChatGPT data export.

    Args:
        source: Path to ZIP archive or extracted conversations.json
        output_dir: Directory to write converted JSONL files

    Returns:
        List of dicts with session metadata for each imported conversation
    """
    source = Path(source)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load conversations
    if source.suffix == ".zip":
        with zipfile.ZipFile(source) as zf:
            with zf.open("conversations.json") as f:
                conversations = json.load(f)
    elif source.suffix == ".json":
        conversations = json.loads(source.read_text())
    else:
        raise ValueError(f"Unsupported file type: {source.suffix} (expected .zip or .json)")

    results = []
    for conv in conversations:
        result = _convert_chatgpt_conversation(conv, output_dir)
        if result:
            results.append(result)

    return results


def _convert_chatgpt_conversation(conv: dict, output_dir: Path) -> dict | None:
    """Convert a single ChatGPT conversation to JSONL."""
    conv_id = conv.get("id", conv.get("conversation_id", ""))
    title = conv.get("title", "Untitled")
    create_time = conv.get("create_time")
    update_time = conv.get("update_time")
    model = conv.get("default_model_slug", "")

    # ChatGPT stores messages as a DAG (mapping node), not a flat list
    mapping = conv.get("mapping", {})
    if not mapping:
        return None

    # Walk the active path through the DAG
    messages = _flatten_chatgpt_dag(mapping)
    if not messages:
        return None

    # Write JSONL
    output_file = output_dir / f"{conv_id}.jsonl"
    input_tokens = 0
    output_tokens = 0

    with open(output_file, "w") as f:
        # Session header
        f.write(json.dumps({
            "type": "session",
            "id": conv_id,
            "source": "chatgpt-export",
            "timestamp": _ts_to_iso(create_time),
            "title": title,
            "model": model,
        }) + "\n")

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            ts = msg.get("timestamp")

            if role in ("user", "assistant", "system", "tool"):
                entry = {
                    "type": "message",
                    "timestamp": _ts_to_iso(ts),
                    "message": {
                        "role": role,
                        "content": [{"type": "text", "text": content}] if content else [],
                    },
                }

                # Token tracking from metadata
                meta = msg.get("metadata", {})
                if meta.get("model_slug"):
                    entry["message"]["model"] = meta["model_slug"]
                if meta.get("finish_details"):
                    entry["message"]["stop_reason"] = meta["finish_details"].get("type")

                # Aggregate token counts
                if role == "assistant":
                    # Estimate tokens from content length
                    output_tokens += len(content) // 4 if content else 0
                elif role == "user":
                    input_tokens += len(content) // 4 if content else 0

                f.write(json.dumps(entry) + "\n")

    return {
        "id": conv_id,
        "title": title,
        "source": "chatgpt-export",
        "model": model,
        "messages": len(messages),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "started": _ts_to_iso(create_time),
        "ended": _ts_to_iso(update_time),
        "file": str(output_file),
    }


def _flatten_chatgpt_dag(mapping: dict) -> list[dict]:
    """Walk the active path through ChatGPT's DAG-structured messages."""
    # Find root node (no parent)
    root_id = None
    for node_id, node in mapping.items():
        if node.get("parent") is None:
            root_id = node_id
            break
    if not root_id:
        # Try first node
        root_id = next(iter(mapping))

    messages = []
    current = root_id
    visited = set()

    while current and current not in visited:
        visited.add(current)
        node = mapping.get(current)
        if not node:
            break

        msg = node.get("message")
        if msg:
            role = msg.get("author", {}).get("role", "")
            content_parts = msg.get("content", {}).get("parts", [])

            # Extract text content
            text = ""
            for part in content_parts:
                if isinstance(part, str):
                    text += part
                elif isinstance(part, dict) and part.get("content_type") == "text":
                    text += part.get("text", "")

            if role in ("user", "assistant", "system", "tool") and (text or role == "system"):
                messages.append({
                    "role": role,
                    "content": text,
                    "timestamp": msg.get("create_time"),
                    "metadata": msg.get("metadata", {}),
                })

        # Follow active child (last child = active branch)
        children = node.get("children", [])
        current = children[-1] if children else None

    return messages


def import_claude(source: str | Path, output_dir: str | Path) -> list[dict]:
    """Import Claude.ai data export.

    Args:
        source: Path to ZIP archive or extracted JSON file
        output_dir: Directory to write converted JSONL files

    Returns:
        List of dicts with session metadata for each imported conversation
    """
    source = Path(source)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load conversations
    if source.suffix == ".zip":
        with zipfile.ZipFile(source) as zf:
            # Claude export structure varies — look for conversation files
            conversations = []
            for name in zf.namelist():
                if name.endswith(".json") and "conversation" in name.lower():
                    with zf.open(name) as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            conversations.extend(data)
                        else:
                            conversations.append(data)
            # If no conversation-specific file, try all JSON files
            if not conversations:
                for name in zf.namelist():
                    if name.endswith(".json"):
                        with zf.open(name) as f:
                            try:
                                data = json.load(f)
                                if isinstance(data, list):
                                    conversations.extend(data)
                                elif isinstance(data, dict) and "chat_messages" in data:
                                    conversations.append(data)
                            except json.JSONDecodeError:
                                continue
    elif source.suffix == ".json":
        data = json.loads(source.read_text())
        conversations = data if isinstance(data, list) else [data]
    else:
        raise ValueError(f"Unsupported file type: {source.suffix}")

    results = []
    for conv in conversations:
        result = _convert_claude_conversation(conv, output_dir)
        if result:
            results.append(result)

    return results


def _convert_claude_conversation(conv: dict, output_dir: Path) -> dict | None:
    """Convert a single Claude.ai conversation to JSONL."""
    conv_id = conv.get("uuid", conv.get("id", ""))
    title = conv.get("name", conv.get("title", "Untitled"))
    created = conv.get("created_at", conv.get("create_time"))
    updated = conv.get("updated_at", conv.get("update_time"))

    # Claude export has chat_messages array
    chat_messages = conv.get("chat_messages", [])
    if not chat_messages:
        # Try alternate structures
        chat_messages = conv.get("messages", [])

    if not chat_messages:
        return None

    output_file = output_dir / f"{conv_id}.jsonl"
    input_tokens = 0
    output_tokens = 0
    msg_count = 0

    with open(output_file, "w") as f:
        # Session header
        f.write(json.dumps({
            "type": "session",
            "id": conv_id,
            "source": "claude-export",
            "timestamp": created,
            "title": title,
        }) + "\n")

        for msg in chat_messages:
            role = msg.get("sender", msg.get("role", ""))
            # Claude uses "human" / "assistant"
            if role == "human":
                role = "user"

            # Content extraction
            content = ""
            if isinstance(msg.get("content"), str):
                content = msg["content"]
            elif isinstance(msg.get("content"), list):
                for part in msg["content"]:
                    if isinstance(part, str):
                        content += part
                    elif isinstance(part, dict):
                        content += part.get("text", "")
            elif isinstance(msg.get("text"), str):
                content = msg["text"]

            if role in ("user", "assistant") and content:
                msg_count += 1
                ts = msg.get("created_at", msg.get("timestamp", created))

                entry = {
                    "type": "message",
                    "timestamp": ts,
                    "message": {
                        "role": role,
                        "content": [{"type": "text", "text": content}],
                    },
                }

                # Token tracking
                if role == "assistant":
                    output_tokens += len(content) // 4
                else:
                    input_tokens += len(content) // 4

                f.write(json.dumps(entry) + "\n")

    if msg_count == 0:
        output_file.unlink()
        return None

    return {
        "id": conv_id,
        "title": title,
        "source": "claude-export",
        "messages": msg_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "started": created,
        "ended": updated,
        "file": str(output_file),
    }


def _ts_to_iso(ts) -> str | None:
    """Convert various timestamp formats to ISO string."""
    if ts is None:
        return None
    if isinstance(ts, str):
        return ts
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts).isoformat()
    return str(ts)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import sys

    if len(sys.argv) < 3:
        print("""Usage:
  sm-import chatgpt <export.zip|conversations.json> [--output dir]
  sm-import claude  <export.zip|conversations.json> [--output dir]
""")
        return

    source_type = sys.argv[1]
    source_file = sys.argv[2]
    output_dir = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--output" else f"./imported-{source_type}"

    if source_type == "chatgpt":
        results = import_chatgpt(source_file, output_dir)
    elif source_type == "claude":
        results = import_claude(source_file, output_dir)
    else:
        print(f"Unknown source type: {source_type}")
        return

    print(f"\n  Imported {len(results)} conversations → {output_dir}\n")
    for r in results[:10]:
        print(f"  {r.get('title', 'Untitled'):<40} {r.get('messages',0):>4} msgs  {r.get('source','')}")
    if len(results) > 10:
        print(f"  ... and {len(results) - 10} more")

    print(f"\n  To deposit into Langfuse:")
    print(f"    for f in {output_dir}/*.jsonl; do sm deposit \"$f\"; done")
    print(f"\n  To import into folder store:")
    print(f"    for f in {output_dir}/*.jsonl; do sm-local deposit \"$f\"; done")


if __name__ == "__main__":
    main()
