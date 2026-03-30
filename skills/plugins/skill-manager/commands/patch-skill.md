---
description: Patch a plugin skill from feedback, test, and deploy
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
argument-hint: [plugin-name]
---

Patch and redeploy a Cowork plugin. Runs the full skill-manager workflow automatically.

## Steps

1. Locate the plugin named $ARGUMENTS (search `mnt/.remote-plugins/` and `mnt/.local-plugins/`).
2. Read auto-memory (`mnt/.auto-memory/MEMORY.md`) for known issues and feedback about this plugin.
3. List all issues found. If none in memory, ask the user what to fix.
4. Copy the plugin to the working directory.
5. Apply fixes — minimal patches, preserve style.
6. Test: validate JSON, check file references, dry-run scripts if possible.
7. Bump patch version in plugin.json.
8. Package as `.plugin` and save to the user's output folder.
9. Copy patched scripts to `mnt/Alex/AGENTS.md/skills/<skill-name>/` (canonical location).
10. Also save a backup copy to Downloads.
11. Update auto-memory: record patches applied, remove resolved items.
