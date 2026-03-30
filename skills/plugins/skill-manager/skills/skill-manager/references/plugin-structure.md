# Plugin Structure Quick Reference

## Directory Layout

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json           # Required manifest
├── commands/                 # Slash commands (.md)
├── skills/                   # Skills (subdirs with SKILL.md)
│   └── skill-name/
│       ├── SKILL.md
│       └── references/
├── scripts/                  # Bundled scripts (.py, .sh, etc.)
├── .mcp.json                 # MCP server definitions (optional)
└── README.md
```

## plugin.json Minimal

```json
{
  "name": "plugin-name",
  "version": "0.1.0",
  "description": "What the plugin does",
  "author": { "name": "Author" }
}
```

## Packaging

```bash
cd /path/to/plugin-dir
zip -r /tmp/plugin-name.plugin . -x "*.DS_Store"
cp /tmp/plugin-name.plugin /path/to/outputs/plugin-name.plugin
```

## Key Rules

- `name` in plugin.json → kebab-case, matches `.plugin` filename
- `${CLAUDE_PLUGIN_ROOT}` for all intra-plugin path references
- Version: semver, bump PATCH for bugfixes, MINOR for new features
- Plugin dirs under `mnt/.remote-plugins/` are read-only in sandbox — always copy before editing
