---
description: Process medical scans into bilingual Obsidian vault
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, WebFetch
model: opus
argument-hint: <source_directory>
---

Process medical scan images from `$ARGUMENTS` into a structured bilingual Obsidian vault.

1. Read the skill at `${CLAUDE_PLUGIN_ROOT}/skills/medical-scan-obsidian/SKILL.md`.
2. Read the detailed workflow at `${CLAUDE_PLUGIN_ROOT}/skills/medical-scan-obsidian/references/workflow-phases.md`.
3. Execute all phases (1-6) in order against the source directory `$ARGUMENTS`.
4. If `$ARGUMENTS` is empty, ask the user for the source directory path.
