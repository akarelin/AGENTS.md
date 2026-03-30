---
name: manage-skills
description: >
  Manage and improve Cowork plugin skills end-to-end.
  Use when the user asks to "fix a skill", "patch a plugin", "update a skill",
  "deploy a plugin", "rebuild plugin", "improve skill", "skill has a bug",
  or references feedback about a skill that needs to be acted on.
version: 0.2.0
---

# Skill Manager

End-to-end workflow for improving Cowork plugin skills: gather feedback, patch code, test, rebuild, and deploy.

## Canonical Skill Location

The user's custom skills live in the **AGENTS.md** git repo:

```
mnt/Alex/AGENTS.md/skills/
```

Each skill is a subdirectory (e.g. `organize-arxiv/`) containing at minimum a `SKILL.md` and any scripts it references. When deploying patched scripts, **always copy them to this location** in addition to packaging the `.plugin` file. This is the source of truth — not OneDrive, not Downloads.

## Locating Plugins

Installed plugins live under `mnt/.remote-plugins/` (read-only in sandbox) and `mnt/.local-plugins/`.
Plugin source may also exist at the canonical skill path above or a path recorded in auto-memory.

To find a plugin by name:
```bash
find mnt/.remote-plugins mnt/.local-plugins -name "plugin.json" -exec grep -l '"name"' {} \; 2>/dev/null
```

Read `plugin.json` to confirm identity, then map the full file tree:
```bash
find /path/to/plugin -type f
```

## Workflow

### 1. Gather Feedback

Collect issues from any combination of:

- **User input** in the current conversation ("the script misidentifies X", "it crashes on Y")
- **Auto-memory** — read `mnt/.auto-memory/MEMORY.md` and any project/feedback files for the plugin
- **Execution logs** — if the user ran the skill recently, check the conversation or ask for error output

Produce a numbered list of issues to fix. Confirm with user before proceeding.

### 2. Prepare Writable Copy

Plugin dirs under `mnt/.remote-plugins/` are read-only. Always:

1. Copy the entire plugin tree to the working directory:
   ```bash
   cp -r /path/to/plugin /sessions/SESSIONID/plugin-name
   ```
2. All edits happen on this copy.

### 3. Patch

For each issue:

1. Read the relevant source file(s).
2. Apply the minimal fix. Preserve existing style and formatting.
3. If the fix involves a Python script, prefer defensive changes (try/except, input validation, stricter regex) over restructuring.

### 4. Test

Run the patched code against real data when possible:

- **Scripts**: Execute with `--scan` (dry-run) first if the script supports it. Compare output against known-good results.
- **Skill/command markdown**: Verify no broken references to `${CLAUDE_PLUGIN_ROOT}`, no missing files.
- **Structural**: Confirm all files referenced in skill SKILL.md or commands exist in the tree.

Validation checklist:
```bash
# All plugin files present
find /path/to/copy -type f
# JSON valid
python -m json.tool /path/to/copy/.claude-plugin/plugin.json
# No broken internal refs
grep -r 'CLAUDE_PLUGIN_ROOT' /path/to/copy --include='*.md'
```

If the script has a `--scan` mode, run it against the user's target folder and show the plan without executing.

### 5. Deploy

1. Build the `.plugin` zip (always via /tmp to avoid permission issues):
   ```bash
   cd /path/to/copy && zip -r /tmp/plugin-name.plugin . -x "*.DS_Store" && cp /tmp/plugin-name.plugin /path/to/outputs/plugin-name.plugin
   ```
2. Present the `.plugin` file link to the user. It renders as a rich preview in Cowork.
3. Copy patched script(s) to the canonical skill location:
   ```bash
   cp patched-script.py mnt/Alex/AGENTS.md/skills/<skill-name>/
   ```
4. Also save a copy to Downloads as a convenience backup.

### 6. Update Memory

After successful deployment:

- Update the plugin's auto-memory file with patches applied, date, and any remaining issues.
- Remove resolved pending items.

## Constraints

- Never modify files in `mnt/.remote-plugins/` directly — always copy first.
- Never reformat code that isn't part of the fix.
- Never add linting or style changes.
- If a test fails, stop and report to the user before deploying.
- The `.plugin` filename must match the `name` field in `plugin.json`.

## Additional Resources

- **`references/plugin-structure.md`** — quick reference for plugin directory layout and packaging
