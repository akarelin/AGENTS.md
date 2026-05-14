"""MCP tools for secret/key management via gppu.Vault."""

from gppu import Vault

TOOLS = [
    {"name": "secret_get", "description": "Get secret by name", "inputSchema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Secret name (e.g. anthropic-api-key, openai-api-key)"}
        },
        "required": ["name"]
    }, "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}},
    {"name": "secret_list", "description": "List available secret names", "inputSchema": {
        "type": "object",
        "properties": {}
    }, "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}},
    {"name": "secret_create", "description": "Create a new secret. Fails if a secret with this name already exists — use secret_update with create=true to overwrite.", "inputSchema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Secret name (kebab-case, matching existing vault conventions)"},
            "value": {"type": "string", "description": "Secret value"},
            "designation": {"type": "string", "description": "Optional suffix appended as '-<designation>' (kebab-lower) when the base name collides."}
        },
        "required": ["name", "value"]
    }, "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}},
    {"name": "secret_update", "description": "Update an existing secret (creates a new version). Fails if the secret does not exist, unless create=true is passed.", "inputSchema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Secret name"},
            "value": {"type": "string", "description": "New secret value"},
            "create": {"type": "boolean", "description": "If true, create the secret when it does not exist (upsert).", "default": False}
        },
        "required": ["name", "value"]
    }, "annotations": {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": False}},
]


def _secret_create(args):
    Vault.create(args["name"], args["value"], designation=args.get("designation"))
    return {"name": args["name"], "created": True}


def _secret_update(args):
    Vault.update(args["name"], args["value"], create=bool(args.get("create", False)))
    return {"name": args["name"], "updated": True}


HANDLERS = {
    "secret_get": lambda a: {"name": a["name"], "value": Vault.get(a["name"])},
    "secret_list": lambda a: {"secrets": Vault.list()},
    "secret_create": _secret_create,
    "secret_update": _secret_update,
}


def dispatch_tool(name, arguments):
    handler = HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")
    return handler(arguments)
