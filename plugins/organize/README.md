# organize

File organizer with sub-skills. Scans folders, identifies files by type, renames/tags/moves them using specialized sub-skills.

## Installation

```
/plugin install organize@akarelin-skills
```

## Sub-skills

### organize (meta)
Discovers all sub-skills, runs each one's scan on the target folder, presents a combined plan, and executes on approval.

### organize-arxiv
Identifies arxiv PDFs by filename or page-1 watermark, fetches metadata from the arxiv API, renames to `{id} {#tags} {Title} {version}.pdf`, and moves to a structured library. Requires `pip install PyMuPDF`.

### medical-scan-obsidian
Converts medical scan images (discharge instructions, diagnostic studies, lab reports) into a structured Obsidian vault with bilingual EN/RU notes, per-study summaries, and a Map of Content.

## Usage

Ask Claude to "organize my downloads", "file my arxiv papers", or "process medical scans".

## Scripts

- `arxiv_organizer.py` — `--scan` (dry run) and `--execute` modes
- `organize-downloads.bat` — Windows batch shortcut
