---
name: organize-arxiv
description: >
  This skill should be used when the user asks to "organize arxiv papers",
  "rename PDFs", "file research papers", "sort arxiv downloads", or needs
  to identify, rename, tag, and move arxiv PDFs into a structured library.
version: 0.1.0
---

# Arxiv Paper Organizer

Scan a folder for arxiv PDFs, rename them, set metadata, set file dates, and move them to the correct Library subfolder. Non-arxiv PDFs are skipped.

## Steps

1. **Ask** which folder to scan (default: `D:\Downloads`). Ask if recursive.
2. **Run** `python arxiv_organizer.py --scan FOLDER [--recurse]`
3. **Present** the plan summary: how many papers, how many moves vs renames, any collisions.
4. **Wait for approval** before executing.
5. **Run** `python arxiv_organizer.py --execute FOLDER [--recurse] --library "C:\Users\Alex\OneDrive - Karelin\Library"`
6. **Report** results.

## Script location
`${CLAUDE_PLUGIN_ROOT}/scripts/arxiv_organizer.py`

Requires: `pip install PyMuPDF`

## Naming convention
```
{arxivID} {#tags} {Title} {version}.pdf
```
Example: `2310.08560 #ai MemGPT Towards LLMs as Operating Systems v2.pdf`

## Identification
A PDF is arxiv if:
- Filename matches `\d{4}\.\d{4,5}v?\d*` with valid YYMM prefix (MM <= 12), OR
- Page 1 text contains `arXiv:\d{4}\.\d{4,5}`

## Tag slugs
| Tag | Code | AI-adjacent |
|-----|------|-------------|
| #ai | cs.AI | yes |
| #nlp | cs.CL | yes |
| #vision | cs.CV | yes |
| #ml | cs.LG | yes |
| #software-eng | cs.SE | yes |
| #multi-agent | cs.MA | yes |
| #neuro-evo | cs.NE | yes |
| #multimedia | cs.MM | yes |
| #hci | cs.HC | yes |
| #comp-eng | cs.CE | yes |
| #tech-society | cs.CY | yes |
| #speech | eess.AS | yes |
| #audio | cs.SD | yes |
| #security | cs.CR | no |
| #databases | cs.DB | no |
| #distributed | cs.DC | no |
