---
name: organize-scan-medical
description: >
  Process medical scan images into a structured, bilingual Obsidian vault.
  This skill should be used when the user asks to "organize medical scans",
  "process discharge documents", "create medical notes from scans",
  "build a medical vault", or needs to convert medical imaging files
  (CT, ultrasound, echocardiogram, X-ray, discharge instructions)
  into structured Obsidian notes with EN/RU bilingual support.
---

# Medical Scan -> Obsidian Vault Builder

Convert medical scan images (discharge instructions, diagnostic studies, lab reports) into a structured, bilingual Obsidian vault package.

## Constants

- **Vault dir**: `D:\_\Ongoing` (hardcoded)
- **Project name**: Inferred from patient surname + context (e.g., "GGG-Medical"). If the source directory name already looks like a project name, prefer that.
- **Project folder**: `<vault_dir>/<ProjectName>/`

## Workflow Overview

Read `${CLAUDE_PLUGIN_ROOT}/skills/medical-scan-obsidian/references/workflow-phases.md` for detailed phase instructions before starting.

### Phase 1: Inventory & Read Scans
List and read ALL image files (JPG, PNG, PDF) in the source directory. Classify each by type (`discharge_page`, `diagnostic_study`, `lab_report`, `other`), extract date, study name, language, page number. Report inventory to user and confirm before proceeding.

### Phase 2: Copy & Rename Scans
Copy scans to `<project_dir>/Scans/` with standardized naming:
- `YYMMDD StudyName.ext` for diagnostic studies
- `YYMMDD Discharge Instructions N.ext` for discharge pages

### Phase 3: Generate Discharge Notes
From grouped discharge pages, generate THREE notes in `<project_dir>/Notes/`:
- **US Medical English** (`YYMMDD Discharge Instructions us.md`) — full structured summary with ICD-10-CM codes and reference links
- **RU OCR** (`YYMMDD Discharge Instructions ru.md`) — faithful Russian transcription, accuracy over readability
- **RU + US Terms** (`YYMMDD Discharge Instructions ru-usmed.md`) — Russian text with inline US medical term annotations

### Phase 4: Generate Per-Study Notes
For each diagnostic study, generate `Notes/YYMMDD StudyName.md` with English findings, clinical significance, and original Russian conclusion.

### Phase 5: Generate Diagnostics Summary
Create `Notes/YYMMDD Diagnostics Summary (US-style).md` — table of all studies with Date, Study Type, Key Findings, Clinical Significance. Includes imaging, ECG, labs.

### Phase 6: Generate MOC
Create `<project_dir>/<ProjectName>.md` with patient demographics, timeline table, wikilinks to all notes, and section for remote source links.

### Phase 7 (Optional): SNOMED CT Normalization
Only if explicitly requested. Uses Snowstorm API at `https://browser.ihtsdotools.org/snowstorm/snomed-ct/`.

## Key Rules

1. **English filenames** always. Russian content stays inside notes only.
2. **`type: ProjectFile`** in frontmatter of ALL notes.
3. **No separate Index file** — the MOC file IS the navigation hub.
4. **Embed scans** using Obsidian `![[Scans/filename]]` syntax.
5. **YYMMDD prefix** on all filenames for chronological sorting.
6. **Wikilinks** for all internal cross-references.
7. When source language is not Russian, adapt bilingual pattern accordingly.
8. If scan quality is poor, note `[illegible]` and flag to user.
9. Never fabricate clinical findings. If uncertain, mark with `[?]` and flag.
