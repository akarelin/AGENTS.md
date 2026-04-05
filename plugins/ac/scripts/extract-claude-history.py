#!/usr/bin/env python3
"""Extract .claude conversation history related to a folder.

Usage: extract-claude-history.py <search-term> <output-dir> [--projects-dir ~/.claude/projects]

Searches all JSONL conversation files for messages mentioning the search term.
Copies matching raw .jsonl files and writes readable markdown summaries alongside them.
"""

import json
import os
import sys
import glob
import shutil
from pathlib import Path


def extract_text_content(content):
    """Extract readable text from message content (skip thinking, tool_use, etc.)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    # Skip large tool results
                    continue
            elif isinstance(block, str):
                texts.append(block)
        return "\n".join(texts)
    return ""


def parse_session(jsonl_path, search_terms):
    """Parse a JSONL session file and return matching messages."""
    messages = []
    session_meta = {"cwd": None, "first_ts": None, "last_ts": None}

    try:
        with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Skip non-message entries
                if entry.get("type") not in ("user", "assistant"):
                    msg = entry.get("message", {})
                    if not msg.get("role"):
                        continue
                    entry_type = msg.get("role")
                else:
                    entry_type = entry.get("type")

                msg = entry.get("message", {})
                role = msg.get("role", entry_type)
                content = msg.get("content", "")
                timestamp = entry.get("timestamp", "")
                cwd = entry.get("cwd", "")

                if cwd and not session_meta["cwd"]:
                    session_meta["cwd"] = cwd
                if timestamp:
                    if not session_meta["first_ts"]:
                        session_meta["first_ts"] = timestamp
                    session_meta["last_ts"] = timestamp

                text = extract_text_content(content)
                if not text:
                    continue

                # Check if any search term appears in the text or cwd
                combined = (text + " " + cwd).lower()
                matched = any(term.lower() in combined for term in search_terms)

                if matched and role in ("user", "assistant"):
                    # Truncate long responses
                    display_text = text[:1000]
                    if len(text) > 1000:
                        display_text += "\n... (truncated)"

                    messages.append({
                        "role": role,
                        "text": display_text,
                        "timestamp": timestamp,
                    })

    except Exception as e:
        print(f"Warning: Error reading {jsonl_path}: {e}", file=sys.stderr)

    return messages, session_meta


def write_session_md(output_dir, session_id, messages, meta):
    """Write a markdown file for a conversation session."""
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"session-{session_id[:12]}.md")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Session {session_id[:12]}\n\n")
        f.write(f"- **Date range**: {meta.get('first_ts', 'unknown')} to {meta.get('last_ts', 'unknown')}\n")
        f.write(f"- **Working directory**: {meta.get('cwd', 'unknown')}\n")
        f.write(f"- **Matching messages**: {len(messages)}\n\n")
        f.write("## Conversation excerpts\n\n")

        for msg in messages:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            ts = msg.get("timestamp", "")
            f.write(f"**{role_label}** ({ts}):\n")
            # Quote the text
            for line in msg["text"].split("\n"):
                f.write(f"> {line}\n")
            f.write("\n---\n\n")

    return out_path


def main():
    if len(sys.argv) < 3:
        print("Usage: extract-claude-history.py <search-term> <output-dir> [--projects-dir DIR]")
        sys.exit(1)

    search_input = sys.argv[1]
    output_dir = sys.argv[2]
    projects_dir = os.path.expanduser("~/.claude/projects")

    for i, arg in enumerate(sys.argv[3:], 3):
        if arg == "--projects-dir" and i + 1 < len(sys.argv):
            projects_dir = sys.argv[i + 1]

    # Build search terms: the folder name, basename, and path components
    search_terms = [t for t in search_input.split(",") if t.strip()]

    if not os.path.isdir(projects_dir):
        print(f"No .claude/projects directory found at {projects_dir}")
        sys.exit(0)

    # Find all JSONL files
    jsonl_files = glob.glob(os.path.join(projects_dir, "**", "*.jsonl"), recursive=True)
    print(f"Scanning {len(jsonl_files)} conversation files...", file=sys.stderr)

    sessions_found = 0
    files_written = []
    raw_dir = os.path.join(output_dir, "raw")

    for jsonl_path in sorted(jsonl_files):
        session_id = Path(jsonl_path).stem

        # Quick pre-filter: grep for any search term in the file
        try:
            with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
                content_sample = f.read()
            if not any(term.lower() in content_sample.lower() for term in search_terms):
                continue
        except Exception:
            continue

        messages, meta = parse_session(jsonl_path, search_terms)
        if messages:
            # Copy raw .jsonl
            os.makedirs(raw_dir, exist_ok=True)
            raw_dest = os.path.join(raw_dir, f"{session_id}.jsonl")
            shutil.copy2(jsonl_path, raw_dest)

            # Write readable summary
            out_path = write_session_md(output_dir, session_id, messages, meta)
            files_written.append(out_path)
            sessions_found += 1
            print(f"  Found {len(messages)} matching messages in session {session_id[:12]}", file=sys.stderr)

    print(f"\nTotal: {sessions_found} sessions with matches", file=sys.stderr)
    # Print written files to stdout for the caller
    for f in files_written:
        print(f)


if __name__ == "__main__":
    main()
