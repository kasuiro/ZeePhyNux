# Questline — MCP server (F9.8)

A small Model Context Protocol server over **stdio**: the agent starts
`ql-mcp`, writes one JSON-RPC request per line to stdin, and reads one response
per line from stdout. No socket, no port, no daemon, no network, no new Python
packages.

```
agent ──stdin──▶ mcp.py ──stdout──▶ agent
                    │
                    └─▶ ql.py ─▶ vault + event log
```

stdout carries **only** protocol JSON; diagnostics go to stderr. The process
lives exactly as long as the client keeps it open.

## Tools

| Tool | Effect | Writes? |
|---|---|---|
| `board` | open and done cards, sprint window, fragments, streak, gifts | no |
| `status` | projected state plus earned/claimed stamp counts | no |
| `done` | close a task by block id, idempotent | yes: `task.done` and vault line |
| `add_task` | append a task to a vault note with a stable block id | yes: vault note only |

`python3 mcp.py` also answers `initialize` and `tools/list`, so a standard MCP
client can discover the tools without extra configuration.

## Obsidian links

Task identity is the block id (`^ql-…`), never a wikilink: notes can be renamed
and links can rot without changing the log.

`ql add "text" --project x --link "[[projects/x]]" --link "Weekly/2026-W47"`
writes a checkbox like:

```markdown
- [ ] text #project/x [[projects/x]] [[Weekly/2026-W47]] ^ql-a1b2c3d4
```

`ql scan` parses `[[target]]` (and `[[target|alias]]`) into a `links` array in
the vault cache. `board` and `status` return those links with each card, so an
agent can show or follow the source note. Display text drops both the project
tag and the wikilinks; the raw line in the vault is untouched.

Backlinks are **calculated by Obsidian from the markdown**, not stored by
Questline. Questline never reads Obsidian's graph database and never requires
Obsidian to be running.

## Defaults and safety

| Item | Value |
|---|---|
| Default note | `Inbox.md` at the vault root |
| Backup | `Vault/Questline/id-backups/<note>.md` before a write |
| Write | temporary file + `os.replace`, preserving mode |
| Rejected notes | paths outside the vault, symlinks, and folders skipped by `ql scan` |
| Points | `add_task` writes no event: creating a task earns nothing |

## Acceptance

- `tools/list` returns exactly `board`, `status`, `done`, `add_task`.
- An agent calls `board`, then `done <id>`; a second `done` reports
  `already_done: true`.
- `add_task` produces a scannable block id and the wikilinks appear in `board`.
- Unknown tools and malformed lines return JSON-RPC errors; the server never
  crashes and never prints non-JSON to stdout.

## Launcher (QL-802)

`~/.local/share/applications/questline.desktop` starts `ql-board` from rofi or
fuzzel. It is a static `.desktop` entry: no daemon and no shell wrapper.
