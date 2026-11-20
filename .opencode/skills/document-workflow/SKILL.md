---
name: document-workflow
description: Use when converting Markdown or tables into DOCX, PDF, CSV or XLSX deliverables in this project. Enforces local tools, no LibreOffice, no invented content, no overwriting, and deliverables inside the source project.
---

# Document workflow

Markdown in Obsidian is the source of truth. This skill only renders copies;
it never edits the source document.

## Use when

- The user asks for a `.docx`, `.pdf`, `.csv` or `.xlsx` deliverable.
- A Markdown note or flat table must be exported for review in ONLYOFFICE.
- A reusable template or output contract must be chosen.

## Hard rules

1. Do not invent, infer or add facts. Render only what is in the source or what
   the user explicitly supplied as metadata.
2. Markdown source is immutable. Verify its SHA-256 before and after rendering.
3. Deliverables stay inside the source project:
   - project with `.git` → `<project>/entregables/`
   - under `~/Documentos` without `.git` → `~/Documentos/<project>/entregables/`
   - outside `~/Documentos` → `~/Documentos/entregables/<project>/`
4. Never overwrite an existing deliverable without explicit confirmation.
5. No LibreOffice, no LaTeX, no system packages, no resident services.
6. Use only the approved local tools: Pandoc 3.14, ReportLab 5.1.0,
   openpyxl 3.1.5 and the Python `csv` standard library.

## Routing

| Request | Tool |
|---|---|
| Markdown → DOCX | Pandoc |
| Markdown → PDF | Pandoc HTML intermediate + ReportLab |
| Flat table → CSV | Python `csv` |
| Styled/formula/multi-sheet table → XLSX | openpyxl |

WeasyPrint and python-docx are not used in this phase.

## Metadata contract

`title`, `author`, `date`, `lang`, `template`, `output`. See
`schemas/doc.yaml` and `references/policy.md`.

## Render

```sh
python3 .opencode/skills/document-workflow/scripts/render.py \
  --source path/to/note.md \
  --format docx \
  --title "Título real" \
  --author "Autor real" \
  --lang es \
  --template informe-tecnico
```

Formats: `docx`, `pdf`, `csv`, `xlsx`. Add `--force` only after the user
explicitly confirms replacing an existing deliverable.

Each render writes a `.provenance.json` beside the output and prints one JSON
object on stdout with `output`, `format`, `tool`, `bytes` and `source_sha256`.

## Verification

After rendering, confirm the file exists, has non-zero size, has the expected
signature, and open DOCX/XLSX in ONLYOFFICE when the user asks for review.
