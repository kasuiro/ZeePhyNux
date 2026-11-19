# Questline — specification

Status: **F9.0–F9.6 + F9.8 implemented** (2026-11-18); F9.7 deferred. Owner: dev. Language: American English.

## 1. What it is

A local subsystem that turns desktop work into an auditable event log and a
light game layer on top of it:

- **modes** (the seven existing Hyprland gamemodes) produce sessions;
- **Obsidian vault** produces tasks, projects and documentation;
- the log produces **fragments** (the currency) and **streaks**;
- **stamps** (achievements) and **gifts** (cosmetic unlocks) are claimed from it;
- a **board** in AGS shows the sprint.

It is not a game with a desktop theme. It is the measurement layer for a
method (Scrum + Kaizen) with a reward layer on top. If the reward layer were
removed, the log would still be worth keeping.

**Alias:** this subsystem is also called **linux zeep** (or simply **zeep**).
The name refers to the reward/measurement layer only; the GitHub repository for
the whole desktop project is `ZeePhyNux`. The first external experiment using
this layer is `voice-bridge` (F10), documented in `VOICE.md`.

## 2. Decisions (locked 2026-11-18)

| Topic | Decision |
|---|---|
| Currency | **Fragments** (`FRG`) |
| Achievements | **Stamps** (collectible badges, not a currency) |
| Backlog and docs | **Obsidian vault** at `~/Documentos/Vault` |
| Board UI | **AGS window** (same GTK4 process; no new daemon) |
| Points | **Hybrid**: time in mode + tasks closed |
| Language | **American English** for all new code, UI and docs |
| Sync | append-only per-device logs, merged on read |
| Transport | local files; Unix socket (F9.4); HTTP over Tailscale (F9.7, deferred); MCP (F9.8) |
| Phone | HUAWEI Y9 2019 (JKM-LX3), Android — browser board first, Syncthing for the vault |

## 3. Architecture

```
Obsidian vault ──tasks──┐
                        ├─→ events/<device>.tsv ─→ fold() ─→ state.json ─→ ql / AGS / HTTP / MCP
gamemode hooks ─sessions┘        (source of truth)   (pure)    (cache)
```

Three layers, replaceable independently:

1. **Core** — `ql.py` (stdlib only): append, merge, fold, project.
2. **Projection** — waybar counter, AGS board, notifications, `status`.
3. **Connectors** — Obsidian scan (F9.2), Unix socket (F9.4), HTTP (F9.7, deferred), MCP (F9.8).

## 4. Data model

### 4.1 Event log (source of truth)

`~/Documentos/Vault/Questline/events/<device>.tsv` — one file per device, tab
separated, no header:

| col | field | notes |
|---|---|---|
| 1 | `event_id` | uuid4 hex — dedupe key when logs merge |
| 2 | `ts` | UTC, `YYYY-MM-DDTHH:MM:SSZ` — display ordering |
| 3 | `day` | local date of the emitting device — used for streaks |
| 4 | `device` | `<host>-<6 hex>`, generated once, never synced |
| 5 | `seq` | monotonic per device |
| 6 | `type` | see below |
| 7 | `key` | mode name, task id, role id, stamp id |
| 8 | `value` | free text (project tag, duration, …) |

Event types: `mode.start`, `mode.stop`, `task.done`, `task.reopen`, `role`,
`stamp`, `gift.claim`, `kaizen`, `milestone`, `nudge`.

### 4.2 Projection

`~/.local/state/questline/state.json` — derived, never edited, rebuilt with
`ql rebuild`. Deleting it loses nothing.

```
fragments, breakdown{modes,tasks,streak}, streak_days, role, role_age_days,
tasks_done, today, modes{day:{mode:{minutes,fragments}}}, open_sessions, events
```

### 4.3 Rules

`herramientas/questline/rules.toml` — points, caps, streak thresholds, role
affinities and bonus. Editing it changes future **and past** scoring, because
scoring is derived. That is intentional: Kaizen on the rules themselves.

## 5. Scoring

| Source | Fragments | Cap |
|---|---|---|
| 10 min in a mode | 1 | 40/day/mode |
| Session longer than 4 h | credited as 4 h | — |
| Task closed | 10 | — |
| Current streak | 5/day, +25 at 7 days | — |
| Role affinity | ×1.25 on its modes | — |

No penalties. Streaks reset; they never subtract. Open sessions earn nothing
until closed, so `rebuild` is reproducible.

## 6. CLI

```
ql mode start|stop <mode>      # used by the gamemode hook
ql done|reopen <task-id>       # vault task, by Obsidian block id
ql role <role-id>
ql status [--json]
ql rebuild                     # recompute state.json from the log
ql events [--json]
ql device
ql log <type> <key> [value]    # low level; --ts injects time for tests
```

## 7. Roles

`apprentice` (readmode) · `artisan` (devmode, writemode) · `scout` (planingmode)
· `director` (audiovisualmode) · `illustrator` (3dmode) · `bard` (gamedevmode).

One role at a time, switchable every 7 days, logged. No role is strictly
better; if one is, that is a bug to fix in `rules.toml`.

## 8. Multi-device

Because state is derived, merging is a file operation: union of per-device logs,
dedupe by `event_id`, order by `(ts, device, seq)`. Two devices holding the same
events cannot disagree. Task conflicts resolve last-writer-wins on
`(ts, device, seq)`; `task.done` and `task.reopen` are both logged, so an undo
is never destructive.

The vault syncs with any tool (Syncthing recommended, git acceptable). The
event folder is visible on purpose: hidden folders are the usual blind spot of
sync tools.

## 9. Phases

| Phase | Scope | State |
|---|---|---|
| F9.0 | this spec, `RULES.md`, `BACKLOG.md` | done |
| F9.1 | core: log, fold, CLI, gamemode hook | **done** |
| F9.2 | Obsidian scan, block IDs, mtime cache | next |
| F9.3 | waybar `FRG · streak · role` | done |
| F9.4 | AGS board + Unix socket API | — |
| F9.5 | 24 stamps + gift claim flow | done |
| F9.6 | sprint, daily nudge, weekly review, Kaizen | done |
| F9.7 | HTTP board over Tailscale | deferred (risk) |
| F9.8 | MCP server (stdio, zero deps) + Obsidian links | done |
| F9.9 | optional: Vikunja + CalDAV | — |

## 10. Acceptance for F9.1

- [x] one real session recorded by toggling a Hyprland mode
- [x] `ql rebuild` reproduces `state.json` exactly
- [x] duplicate `event_id` counted once
- [x] `reopen` reverses a task's points
- [x] per-session 4 h cap and per-day 40 cap enforced
- [x] role bonus applies only to affinity modes
- [x] two device logs merge without double counting
- [x] open session earns 0 until closed
- [x] 16/16 smoke checks pass (`tests/smoke.py`)
