"""MCP tools for QMD (hybrid BM25+vector search index) via subprocess."""

import json
import logging
import os
import subprocess

QMD_BIN = os.environ.get("QMD_BIN", "/opt/homebrew/bin/qmd")
QMD_XDG_CONFIG = os.environ.get("QMD_XDG_CONFIG", "/Users/alex/.openclaw/agents/alex/qmd/xdg-config")
QMD_XDG_CACHE = os.environ.get("QMD_XDG_CACHE", "/Users/alex/.openclaw/agents/alex/qmd/xdg-cache")
QMD_TIMEOUT = int(os.environ.get("QMD_TIMEOUT", "30"))


def _run(args: list[str]) -> dict:
    env = {
        **os.environ,
        "XDG_CONFIG_HOME": QMD_XDG_CONFIG,
        "XDG_CACHE_HOME": QMD_XDG_CACHE,
    }
    try:
        result = subprocess.run(
            [QMD_BIN] + args,
            capture_output=True, text=True, timeout=QMD_TIMEOUT, env=env,
        )
    except FileNotFoundError:
        return {"error": f"qmd binary not found at {QMD_BIN}"}
    except subprocess.TimeoutExpired:
        return {"error": f"qmd timed out after {QMD_TIMEOUT}s"}

    if result.returncode != 0:
        return {"error": result.stderr.strip() or f"exit code {result.returncode}"}

    output = result.stdout.strip()
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"text": output}


# -- Tool Definitions --

TOOLS = [
    {"name": "qmd_search", "description": "Hybrid BM25+vector search across the QMD index", "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "collection": {"type": "string", "description": "Collection name to search (omit for all)"},
            "limit": {"type": "integer", "description": "Max results (default 10)"},
        },
        "required": ["query"]
    }},
    {"name": "qmd_vsearch", "description": "Vector-only semantic search across the QMD index", "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Semantic search query"},
            "collection": {"type": "string", "description": "Collection name to search (omit for all)"},
            "limit": {"type": "integer", "description": "Max results (default 10)"},
        },
        "required": ["query"]
    }},
    {"name": "qmd_get", "description": "Get a specific file/document from the QMD index by path", "inputSchema": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "File path within the index"},
        },
        "required": ["file_path"]
    }},
    {"name": "qmd_status", "description": "Get QMD index status and list collections", "inputSchema": {
        "type": "object",
        "properties": {}
    }},
]

_RO = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}
for _t in TOOLS:
    _t["annotations"] = _RO


# -- Handlers --

def _qmd_search(a):
    args = ["search", a["query"]]
    if a.get("collection"):
        args += ["--collection", a["collection"]]
    limit = a.get("limit", 10)
    args += ["--limit", str(limit), "--json"]
    return _run(args)


def _qmd_vsearch(a):
    args = ["vsearch", a["query"]]
    if a.get("collection"):
        args += ["--collection", a["collection"]]
    limit = a.get("limit", 10)
    args += ["--limit", str(limit), "--json"]
    return _run(args)


def _qmd_get(a):
    return _run(["get", a["file_path"], "--json"])


def _qmd_status(a):
    return _run(["status", "--json"])


HANDLERS = {
    "qmd_search": _qmd_search,
    "qmd_vsearch": _qmd_vsearch,
    "qmd_get": _qmd_get,
    "qmd_status": _qmd_status,
}


def dispatch_tool(name, arguments):
    handler = HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")
    return handler(arguments)
