# Arxiv Paper Organizer

Scan a folder for arxiv PDFs, rename them, set metadata, set file dates, and move them to the correct Library subfolder. Non-arxiv PDFs are skipped.

## Trigger
User asks to organize, rename, or file arxiv papers in any folder.

## Steps

1. **Ask** which folder to scan (default: `D:\Downloads`). Ask if recursive.
2. **Run** `arxiv_organizer.py --scan FOLDER [--recurse]` via Desktop Commander or bash.
3. **Present** the plan summary to the user: how many papers, how many moves vs renames, any collisions.
4. **Wait for approval** before executing.
5. **Run** `arxiv_organizer.py --execute FOLDER [--recurse] --library "C:\Users\Alex\OneDrive - Karelin\Library"`.
6. **Report** results.

## Script location
`C:\Users\Alex\OneDrive - Karelin\.claude\skills\organize-arxiv\arxiv_organizer.py`

Requires: `pip install PyMuPDF`
## Naming convention
```
{arxivID} {#tags} {Title} {version}.pdf
```
Example: `2310.08560 #ai MemGPT Towards LLMs as Operating Systems v2.pdf`

## Identification
A PDF is arxiv if:
- Filename matches `\d{4}\.\d{4,5}v?\d*` with valid YYMM prefix (MM ≤ 12), OR
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