# Policy

## Fidelity

- Reproduce source wording. Do not summarise, expand, translate or correct
  spelling unless the user explicitly asks for that change in the source.
- If a datum is unverified, keep the source's own wording or mark it as
  pending validation. Never fill gaps from model memory.
- Metadata is data the user supplied. If the user did not supply a value,
  leave it empty rather than guessing.

## Source immutability

The renderer computes SHA-256 before and after the job and fails if it changed.
The source path is only ever opened for reading.

## Output paths

The renderer derives the delivery directory from the source path, not from the
current working directory:

1. nearest ancestor with `.git` → `<project>/entregables/`
2. otherwise, first level under `~/Documentos` → `~/Documentos/<project>/entregables/`
3. otherwise → `~/Documentos/entregables/<source-parent>/`

An explicit `--output` must resolve inside that directory. This prevents
deliverables from leaking outside the project.

## Overwrites

Default behaviour is fail-closed: if the target exists, the renderer exits 3
and prints the exact path. `--force` is the only override and requires prior
user confirmation.

## Tool boundaries

| Stage | Allowed |
|---|---|
| Generate/convert | Pandoc, ReportLab, openpyxl, `csv` |
| Review | ONLYOFFICE Desktop Editors (read/open only) |
| Forbidden | LibreOffice, LaTeX, WeasyPrint, python-docx, system installs |

Pandoc PDF via LaTeX is not used. The PDF path is Pandoc → HTML5 → ReportLab,
which needs no system libraries.

## Provenance

Every deliverable gets `<name>.provenance.json` with source path, source hash,
tool, pinned version, UTC timestamp and output name. This file is metadata,
not a substitute for the source.
