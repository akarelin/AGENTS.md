"""MCP tools for secret/key management via Azure Key Vault (gppu)."""

import os

from gppu import resolve_secret, set_secret

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
    {"name": "secret_set", "description": "Create or version-bump a secret (idempotent — new version is added if name exists, secret is created if not)", "inputSchema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Secret name (kebab-case, matching existing vault conventions)"},
            "value": {"type": "string", "description": "Secret value"}
        },
        "required": ["name", "value"]
    }, "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}},
]


def _kv_client():
    vault_name = os.environ.get("AZURE_KEYVAULT_NAME")
    if not vault_name:
        raise RuntimeError("AZURE_KEYVAULT_NAME not set")
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    return SecretClient(vault_url=f"https://{vault_name}.vault.azure.net",
                        credential=DefaultAzureCredential())


def _secret_list():
    return {"secrets": [s.name for s in _kv_client().list_properties_of_secrets()]}


def _secret_set(args):
    set_secret(args["name"], args["value"])
    return {"name": args["name"], "set": True}


HANDLERS = {
    "secret_get": lambda a: {"name": a["name"], "value": resolve_secret(a["name"])},
    "secret_list": lambda a: _secret_list(),
    "secret_set": _secret_set,
}


def dispatch_tool(name, arguments):
    handler = HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")
    return handler(arguments)
