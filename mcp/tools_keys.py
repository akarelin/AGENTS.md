"""MCP tools for secret/key retrieval via gppu."""

from gppu import resolve_secret

TOOLS = [
    {"name": "get_secret", "description": "Get secret", "inputSchema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Secret name (e.g. anthropic-api-key, openai-api-key)"}
        },
        "required": ["name"]
    }},
    {"name": "list_secrets", "description": "List secrets", "inputSchema": {
        "type": "object",
        "properties": {}
    }},
]

# get_secret is sensitive but read-only; list_secrets is read-only
_RO = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}
for _t in TOOLS:
    _t["annotations"] = _RO

HANDLERS = {
    "get_secret": lambda a: {"name": a["name"], "value": resolve_secret(a["name"])},
    "list_secrets": lambda a: _list_secrets(),
}


def _list_secrets():
    import os
    vault_name = os.environ.get("AZURE_KEYVAULT_NAME")
    if not vault_name:
        return {"error": "AZURE_KEYVAULT_NAME not set"}
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    client = SecretClient(vault_url=f"https://{vault_name}.vault.azure.net",
                          credential=DefaultAzureCredential())
    return {"secrets": [s.name for s in client.list_properties_of_secrets()]}


def dispatch_tool(name, arguments):
    handler = HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")
    return handler(arguments)
