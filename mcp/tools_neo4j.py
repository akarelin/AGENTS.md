"""MCP tools for Neo4j graph database exploration via Cypher.

Auto-discovers available Neo4j servers from Key Vault by matching
secrets named neo4j-*-uri / neo4j-*-password. If multiple servers
are found, the user must select one before querying.
"""

from gppu import Vault

TOOLS = [
    {"name": "neo4j_list_servers", "description": "List available Neo4j servers (auto-discovered from Key Vault). Call this first to see what's available, then use neo4j_use_server to select one.", "inputSchema": {
        "type": "object",
        "properties": {}
    }},
    {"name": "neo4j_use_server", "description": "Select which Neo4j server to use for subsequent queries", "inputSchema": {
        "type": "object",
        "properties": {
            "server": {"type": "string", "description": "Server name from neo4j_list_servers (e.g. 'default', 'xsolla-aura')"}
        },
        "required": ["server"]
    }},
    {"name": "read_neo4j_cypher", "description": "Execute a read-only Cypher query against the selected Neo4j server", "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Cypher query (read-only)"},
            "params": {"type": "object", "description": "Query parameters", "default": {}}
        },
        "required": ["query"]
    }},
    {"name": "write_neo4j_cypher", "description": "Execute a write Cypher query against the selected Neo4j server", "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Cypher query (write)"},
            "params": {"type": "object", "description": "Query parameters", "default": {}}
        },
        "required": ["query"]
    }},
    {"name": "get_neo4j_schema", "description": "Get the graph schema (node labels, relationship types, properties) from the selected Neo4j server", "inputSchema": {
        "type": "object",
        "properties": {}
    }},
]

_RO = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}
_RW = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}
for t in TOOLS:
    t["annotations"] = _RO
TOOLS[3]["annotations"] = _RW

# ── Server discovery and selection ──

_active_server: str | None = None


def _discover_servers():
    """Find neo4j-*-uri secrets in Key Vault and return server names."""
    import os
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    vault_name = os.environ.get("AZURE_KEYVAULT_NAME", "")
    client = SecretClient(vault_url=f"https://{vault_name}.vault.azure.net",
                          credential=DefaultAzureCredential())
    servers = {}
    for s in client.list_properties_of_secrets():
        if s.name.startswith("neo4j-") and s.name.endswith("-uri"):
            name = s.name.removeprefix("neo4j-").removesuffix("-uri")
            servers[name] = s.name
    return servers


def _list_servers(args):
    servers = _discover_servers()
    result = []
    for name in sorted(servers):
        uri = Vault.get(f"neo4j-{name}-uri")
        result.append({"name": name, "uri": uri, "active": name == _active_server})
    return {"servers": result, "active": _active_server,
            "hint": "Call neo4j_use_server to select a server before querying." if not _active_server else None}


def _use_server(args):
    global _active_server
    server = args["server"]
    servers = _discover_servers()
    if server not in servers:
        return {"error": f"Unknown server '{server}'. Available: {sorted(servers)}"}
    # Validate credentials exist
    Vault.get(f"neo4j-{server}-uri")
    Vault.get(f"neo4j-{server}-password")
    _active_server = server
    return {"active": server, "uri": Vault.get(f"neo4j-{server}-uri")}


# ── Driver ──

def _get_driver():
    from neo4j import GraphDatabase
    if not _active_server:
        # Auto-select if only one server available
        servers = _discover_servers()
        if len(servers) == 1:
            _use_server({"server": next(iter(servers))})
        else:
            raise ValueError(f"Multiple Neo4j servers available ({', '.join(sorted(servers))}). "
                             "Call neo4j_use_server first to select one.")
    uri = Vault.get(f"neo4j-{_active_server}-uri")
    password = Vault.get(f"neo4j-{_active_server}-password")
    return GraphDatabase.driver(uri, auth=("neo4j", password))


# ── Query tools ──

def _read_cypher(args):
    query = args["query"]
    params = args.get("params", {})
    driver = _get_driver()
    try:
        with driver.session(database="neo4j") as session:
            result = session.run(query, params)
            records = [dict(r) for r in result]
            return {"records": records, "count": len(records)}
    finally:
        driver.close()


def _write_cypher(args):
    query = args["query"]
    params = args.get("params", {})
    driver = _get_driver()
    try:
        with driver.session(database="neo4j") as session:
            result = session.run(query, params)
            summary = result.consume()
            counters = summary.counters
            return {
                "nodes_created": counters.nodes_created,
                "nodes_deleted": counters.nodes_deleted,
                "relationships_created": counters.relationships_created,
                "relationships_deleted": counters.relationships_deleted,
                "properties_set": counters.properties_set,
            }
    finally:
        driver.close()


def _get_schema(args):
    driver = _get_driver()
    try:
        with driver.session(database="neo4j") as session:
            labels = [r["label"] for r in session.run("CALL db.labels()")]
            rel_types = [r["relationshipType"] for r in session.run("CALL db.relationshipTypes()")]
            props = [dict(r) for r in session.run("CALL db.propertyKeys()")]
            return {"labels": labels, "relationship_types": rel_types,
                    "property_keys": [p["propertyKey"] for p in props]}
    finally:
        driver.close()


HANDLERS = {
    "neo4j_list_servers": _list_servers,
    "neo4j_use_server": _use_server,
    "read_neo4j_cypher": _read_cypher,
    "write_neo4j_cypher": _write_cypher,
    "get_neo4j_schema": _get_schema,
}


def dispatch_tool(name, arguments):
    handler = HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")
    return handler(arguments)
