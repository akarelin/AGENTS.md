# Workflow Phase Details

## Phase 1: Inventory & Read Scans

1. List all image files in `<source_dir>` (JPG, PNG, PDF).
2. Read EVERY image using the Read tool (vision capabilities).
3. For each image, determine:
   - **Type**: `discharge_page` | `diagnostic_study` | `lab_report` | `other`
   - **Date**: Extract from document text; fall back to filename; fall back to `000000`
   - **Study name** (for diagnostics): e.g., "Head CT", "Carotid Duplex", "Abdominal Ultrasound", "Echocardiogram (TTE)"
   - **Language**: Detect source language (typically Russian)
   - **Page number** (for multi-page discharge documents)
4. Report inventory to the user and confirm before proceeding.

## Phase 2: Copy & Rename Scans

Copy each scan to `<project_dir>/Scans/` with standardized naming:
- `YYMMDD StudyName.ext` for diagnostic studies
- `YYMMDD Discharge Instructions N.ext` for discharge pages (N = page number)

## Phase 3: Generate Discharge Notes

Group all discharge pages together. Read them as a set and generate THREE notes:

### A) `YYMMDD Discharge Instructions us.md` — US Medical English

Full structured discharge summary translated to US medical English. Include:
- Patient demographics (name, DOB, age, facility, admission/discharge dates, service)
- Primary discharge diagnosis with ICD-10-CM codes
- Secondary/comorbid diagnoses (problem list)
- Presentation / reason for admission
- Key objective findings (vitals, anthropometrics, labs, ECG, imaging summaries)
- Inpatient treatments (flag non-US-standard medications)
- Discharge condition
- Discharge medications/instructions (lifestyle, meds)
- Follow-up plan

Use inline links to authoritative references: `[[ICD-10-CM code]](url)`, `[[drug name]](medlineplus url)`, `[[condition]](medlineplus url)`.

### B) `YYMMDD Discharge Instructions ru.md` — RU OCR (max fidelity)

Faithful Russian-language transcription preserving original structure, abbreviations, formatting. This is the evidence layer — accuracy over readability.

### C) `YYMMDD Discharge Instructions ru-usmed.md` — RU + US Medical Terms

Russian text with US medical term annotations inline. Each significant medical term gets a parenthetical English equivalent and optional reference link.

### Frontmatter for all three:

```yaml
---
type: ProjectFile
title: "<appropriate title>"
date_of_service: <YYYY-MM-DD>
---
```

Each note embeds the discharge scan pages and diagnostic scans.

## Phase 4: Generate Per-Study Notes

For each diagnostic study scan, generate `Notes/YYMMDD StudyName.md`:

```yaml
---
type: ProjectFile
title: "<RU study name>"
date_of_service: <YYYY-MM-DD>
study_type: <English study type>
---
```

Note structure (English-first, bilingual):

```markdown
# <English Study Name> — <YYYY-MM-DD>

![[Scans/YYMMDD StudyName.ext]]

## Technique
<imaging technique details if available>

## Findings
- <structured English findings extracted from scan>

## Clinical Significance
<clinical interpretation and implications>

---

## Заключение (RU)
- <original Russian findings, faithful to scan text>
```

## Phase 5: Generate Diagnostics Summary

Create `Notes/YYMMDD Diagnostics Summary (US-style).md`:

```yaml
---
type: ProjectFile
title: Diagnostics Summary (US-style)
date_range: <YYYY-MM-DD>..<YYYY-MM-DD>
patient: "<Patient Name>"
---
```

Table with columns: Date | Study Type | Key Findings | Clinical Significance.
Include ALL identifiable studies: imaging, ECG, labs (CBC, chemistry, urinalysis, eGFR).
Embed scan images inline in the Clinical Significance column: `Scan: ![[Scans/filename]]`.

## Phase 6: Generate MOC (Map of Contents)

Create `<project_dir>/<ProjectName>.md`:

```yaml
---
type: Ongoing
---
```

Structure:

```markdown
# <Project Name>

**Patient:** <name>, DOB <date> (age <N>)
**Facility:** <facility name and location>

## Timeline

| Date | Event |
|---|---|
| <date> | Admitted — <chief complaints> |
| <date> | [[Notes/YYMMDD StudyName]] — <one-line finding> |
| ... | ... |
| <date> | [[Notes/YYMMDD Discharge Instructions us\|Discharged]] — <condition at discharge> |

**Dx:** <primary diagnosis with ICD code>
**Comorbidities:** <comma-separated list>

## Notes
- Per-study notes (YYMMDD): [[Notes/...]], [[Notes/...]]
- US summary: [[Notes/YYMMDD Discharge Instructions us]]
- RU with US medical term mapping: [[Notes/YYMMDD Discharge Instructions ru-usmed]]
- RU OCR (max fidelity): [[Notes/YYMMDD Discharge Instructions ru]]
- Diagnostics overview table: [[Notes/YYMMDD Diagnostics Summary (US-style)]]

## Remote source links (original uploads)
<only if source URLs are provided by user>
```

## Phase 7 (Optional): SNOMED CT Normalization

Only if the user explicitly requests SNOMED normalization.

Use the Snowstorm API:
- Base: `https://browser.ihtsdotools.org/snowstorm/snomed-ct/`
- Search: `/browser/MAIN/descriptions?term=<query>&conceptActive=true&lang=english&limit=5`
- Add SNOMED entities table to per-study notes
