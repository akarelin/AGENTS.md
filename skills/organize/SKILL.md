# Organize Files

Scan a folder, identify files by type, rename/tag/move them using registered organizer sub-skills.

## Trigger
User asks to organize, triage, or clean up a folder.

## Steps

1. **Ask** which folder to scan (default: `D:\Downloads`). Ask if recursive.
2. **Discover** all `organize-*` skill folders under `.claude/skills/`. Read each sub-skill's SKILL.md.
3. **Run each organizer's scan** (dry run) on the target folder.
4. **Present a combined plan** to the user: group by organizer, show counts, moves, renames.
5. **Wait for approval** before executing anything.
6. **Execute** each approved organizer.
7. **Report** what was done, what was skipped, any errors.

## Sub-skill contract

Each `organize-*` folder contains:
- `SKILL.md` — describes what file types it handles, identification rules, naming convention
- `*_organizer.py` — CLI script with standard interface:
  ```
  python *_organizer.py --scan   FOLDER [--recurse]
  python *_organizer.py --execute FOLDER [--recurse] --library "C:\Users\Alex\OneDrive - Karelin\Library"
  ```
  `--scan` prints a dry-run plan to stdout. `--execute` does the work.

## Registered organizers

| Skill | Handles | Location |
|-------|---------|----------|
| organize-arxiv | Arxiv PDFs | `.claude/skills/organize-arxiv/` |

## Constants
- Library root: `C:\Users\Alex\OneDrive - Karelin\Library`
- Default scan folder: `D:\Downloads`
- PyMuPDF required: `pip install PyMuPDF`