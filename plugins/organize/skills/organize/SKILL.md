---
name: organize
description: >
  This skill should be used when the user asks to "organize files",
  "triage a folder", "clean up downloads", "sort files", "organize medical scans",
  "process discharge documents", "organize arxiv papers", or wants to
  scan a directory and route files to specialized organizer sub-skills.
version: 0.1.0
---

# Organize Files

Scan a folder, identify files by type, rename/tag/move them using registered organizer sub-skills.

## Trigger
User asks to organize, triage, or clean up a folder — or specifically asks to organize arxiv papers or medical scans.

## Steps

1. **Ask** which folder to scan (default: `D:\Downloads`). Ask if recursive.
2. **Discover** all sub-skills under `${CLAUDE_PLUGIN_ROOT}/skills/`. Read each sub-skill's SKILL.md.
3. **Run each organizer's scan** (dry run) on the target folder.
4. **Present a combined plan** to the user: group by organizer, show counts, moves, renames.
5. **Wait for approval** before executing anything.
6. **Execute** each approved organizer.
7. **Report** what was done, what was skipped, any errors.

## Sub-skills

| Sub-skill | Handles | Details |
|-----------|---------|---------|
| organize-arxiv | Arxiv PDFs | Rename, tag, file into library |
| medical-scan-obsidian | Medical scans (CT, X-ray, labs, discharge) | Build bilingual Obsidian vault |

For sub-skill details, read their individual SKILL.md files.

## Sub-skill contract (for script-based organizers)

Each organizer sub-skill with a script provides:
- `SKILL.md` — describes what file types it handles, identification rules, naming convention
- `*_organizer.py` — CLI script:
  ```
  python *_organizer.py --scan   FOLDER [--recurse]
  python *_organizer.py --execute FOLDER [--recurse] --library "PATH"
  ```

## Constants
- Library root: `C:\Users\Alex\OneDrive - Karelin\Library`
- Default scan folder: `D:\Downloads`
- PyMuPDF required: `pip install PyMuPDF`
