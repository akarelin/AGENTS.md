"""MCP tools for M365 admin operations via Graph API."""

from graph_client import graph_get, graph_post, graph_patch, graph_delete


TOOLS = [
    # --  Users  --
    {"name": "users_list", "description": "List users", "inputSchema": {
        "type": "object",
        "properties": {"top": {"type": "integer", "description": "Max results (default 25)"}}
    }},
    {"name": "users_get", "description": "Get user", "inputSchema": {
        "type": "object",
        "properties": {"user_id": {"type": "string", "description": "User ID or userPrincipalName"}},
        "required": ["user_id"]
    }},
    {"name": "users_search", "description": "Search users", "inputSchema": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Search query"}, "top": {"type": "integer"}},
        "required": ["query"]
    }},

    # --  Groups  --
    {"name": "groups_list", "description": "List groups", "inputSchema": {
        "type": "object",
        "properties": {"top": {"type": "integer", "description": "Max results (default 25)"}}
    }},
    {"name": "groups_get", "description": "Get group", "inputSchema": {
        "type": "object",
        "properties": {"group_id": {"type": "string", "description": "Group ID"}},
        "required": ["group_id"]
    }},
    {"name": "groups_members", "description": "Get group members", "inputSchema": {
        "type": "object",
        "properties": {"group_id": {"type": "string", "description": "Group ID"}},
        "required": ["group_id"]
    }},

    # --  Domains  --
    {"name": "domains_list", "description": "List domains", "inputSchema": {
        "type": "object",
        "properties": {}
    }},

    # --  Licenses  --
    {"name": "licenses_list", "description": "List licenses", "inputSchema": {
        "type": "object",
        "properties": {}
    }},
    {"name": "user_licenses", "description": "Get user licenses", "inputSchema": {
        "type": "object",
        "properties": {"user_id": {"type": "string", "description": "User ID or UPN"}},
        "required": ["user_id"]
    }},

    # --  Devices  --
    {"name": "devices_list", "description": "List devices", "inputSchema": {
        "type": "object",
        "properties": {"top": {"type": "integer", "description": "Max results (default 25)"}}
    }},

    # --  Directory roles  --
    {"name": "roles_list", "description": "List roles", "inputSchema": {
        "type": "object",
        "properties": {}
    }},
    {"name": "role_members", "description": "Get role members", "inputSchema": {
        "type": "object",
        "properties": {"role_id": {"type": "string", "description": "Directory role ID"}},
        "required": ["role_id"]
    }},

    # --  Org info  --
    {"name": "org_info", "description": "Get organization info", "inputSchema": {
        "type": "object",
        "properties": {}
    }},
]

# All admin tools are read-only queries
_RO = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}
for _t in TOOLS:
    _t["annotations"] = _RO


# ── Handlers ────────────────────────────────────────────────────────

def _users_list(a):
    return graph_get(f"/users?$top={a.get('top', 25)}&$select=id,displayName,mail,userPrincipalName,accountEnabled,jobTitle,department")

def _users_get(a):
    return graph_get(f"/users/{a['user_id']}?$select=id,displayName,mail,userPrincipalName,accountEnabled,jobTitle,department,mobilePhone,officeLocation,createdDateTime")

def _users_search(a):
    return graph_get(f"/users?$search=\"displayName:{a['query']}\"&$top={a.get('top', 25)}"
                     "&$select=id,displayName,mail,userPrincipalName,accountEnabled",
                     extra_headers={"ConsistencyLevel": "eventual"})

def _groups_list(a):
    return graph_get(f"/groups?$top={a.get('top', 25)}&$select=id,displayName,groupTypes,mailEnabled,securityEnabled,membershipRule")

def _groups_get(a):
    return graph_get(f"/groups/{a['group_id']}?$select=id,displayName,description,groupTypes,mailEnabled,securityEnabled,createdDateTime")

def _groups_members(a):
    return graph_get(f"/groups/{a['group_id']}/members?$select=id,displayName,mail,userPrincipalName")

def _domains_list(a):
    return graph_get("/domains?$select=id,isDefault,isVerified,authenticationType")

def _licenses_list(a):
    return graph_get("/subscribedSkus?$select=skuId,skuPartNumber,consumedUnits,prepaidUnits,appliesTo")

def _user_licenses(a):
    return graph_get(f"/users/{a['user_id']}/licenseDetails")

def _devices_list(a):
    return graph_get(f"/devices?$top={a.get('top', 25)}&$select=id,displayName,operatingSystem,operatingSystemVersion,isManaged,trustType")

def _roles_list(a):
    return graph_get("/directoryRoles?$select=id,displayName,description")

def _role_members(a):
    return graph_get(f"/directoryRoles/{a['role_id']}/members?$select=id,displayName,mail,userPrincipalName")

def _org_info(a):
    return graph_get("/organization?$select=id,displayName,verifiedDomains,assignedPlans,createdDateTime")


HANDLERS = {
    "users_list": _users_list, "users_get": _users_get, "users_search": _users_search,
    "groups_list": _groups_list, "groups_get": _groups_get, "groups_members": _groups_members,
    "domains_list": _domains_list,
    "licenses_list": _licenses_list, "user_licenses": _user_licenses,
    "devices_list": _devices_list,
    "roles_list": _roles_list, "role_members": _role_members,
    "org_info": _org_info,
}


def dispatch_tool(name, arguments):
    handler = HANDLERS.get(name)
    if not handler:
        raise ValueError(f"Unknown tool: {name}")
    return handler(arguments)
