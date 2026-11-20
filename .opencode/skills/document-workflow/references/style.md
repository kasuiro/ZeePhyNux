# Template conventions

Templates are Markdown files under `templates/`. They contain structure only:
headings, empty section prompts and comments describing what belongs in each
section. They never contain invented facts.

## Frontmatter

```yaml
---
title: ""
author: ""
date: ""
lang: es
template: informe-tecnico
---
```

Pandoc ignores metadata keys ending in `_`; do not use them for contract
fields.

## Headings

- One `#` title per document.
- `##` for major sections, `###` for subsections.
- Keep headings short and declarative.

## Tables

Use pipe tables for flat data. A header row and separator row are required.
Choose CSV when there are no styles, formulas or multiple sheets.

## Available templates

| Template | Use |
|---|---|
| `informe-tecnico.md` | Technical report with findings and recommendations |
| `manual-procedimientos.md` | Step-by-step procedure manual |

Both are deliberately generic. The agent fills content from the source, not
from memory.
