# Questline core

`ql` is the measurement layer of the desktop-work subsystem. It records mode
sessions and closed tasks as an append-only event log, and derives fragments,
streaks and role bonuses from it. Standard library only: no packages, no
service, no network.

Spec: `docs/subsystem/SPEC.md` · Invariants: `docs/subsystem/RULES.md`
Backlog: `docs/subsystem/BACKLOG.md`

## Install

```bash
chmod +x herramientas/questline/ql.py
ln -sfn "$PWD/herramientas/questline/ql.py" ~/.local/bin/ql
ql device          # first run creates the local device id
```

The Hyprland hook (`~/.config/hypr/UserScripts/gamemode/gamemode_common.sh`)
uses `~/.local/bin/ql` and does nothing if it is missing.

## Use

```bash
ql status                      # fragments, streak, role, today's modes
ql status --json               # same, machine readable
ql mode start readmode         # what the keybind does
ql tasks                       # vault tasks with their block id
ql tasks --project gallery     # filter by #project/<name>
ql scan --write-ids            # append the block id to new task lines
ql sync                        # record done/reopen since the last scan
ql done ql-a1b2c3 --project gallery
ql done ql-a1b2c3 --notify   # same, plus a desktop notification
ql reopen ql-a1b2c3
ql add "Write notes" --project x --link "[[projects/x]]"
ql role artisan
ql rebuild                     # recompute state.json from the log
ql events                      # merged log, oldest first
ql milestones                  # milestones already earned
ql stamps [--json]              # 24 stamps: earned / unclaimed / claimed
ql claim <stamp-id>             # render and record the gift, once
ql sprint start --projects all # open a 7-day sprint (--weeks 2/3, --start YYYY-MM-DD)
ql sprint status [--json]      # dates, day N/M, commit / done / open / carried
ql sprint close                # carry the open ones into the next start
ql review [--days 7] [--json]  # minutes per mode, tasks, FRG, one experiment
ql kaizen start "hypothesis" --metric open --baseline 12
ql kaizen end <id> --value 9
ql kaizen list [--json]
```

## Vault rules

Questline reads every `*.md` under the vault except `.obsidian/`, `.trash/`,
`.git/`, `.stversions/` and `Questline/`, and ignores notes over 256 KB and
symlinks. A task is any checkbox line; `#project/<name>` groups it.

The only write into your notes is one block id, appended once:

```markdown
- [ ] Ship the board #project/questline ^ql-a1b2c3
```

That id is what keeps a task's history when the line moves to another note. The
note is copied to `Questline/id-backups/` before the first write. Plain
`ql scan` and `ql tasks` never write.

`ql sync` emits `task.done` / `task.reopen` **only on a change since the last
run**; the first sync is a baseline and awards nothing, so a vault full of ticked
boxes does not become a fortune.

## Files

| Path | Role |
|---|---|
| `~/Documentos/Vault/Questline/events/<device>.tsv` | source of truth, one per device |
| `~/Documentos/Vault/Questline/sprint.json` | sprint window, commitment and carry-over |
| `~/Documentos/Vault/Questline/gallery/` | gift cards, written only by `ql claim` |
| `~/Documentos/Vault/Questline/id-backups/` | note copy before block ids are added |
| `~/.local/state/questline/state.json` | cache, safe to delete |
| `~/.local/state/questline/hud.json` | what the desktop card shows |
| `~/.local/state/questline/notify.json` | last notification group (5 s window) |
| `~/.local/state/questline/splash.json` | last milestone shown by the splash |
| `~/.local/state/questline/line` | one line for waybar (`42 FRG · 3d`) |
| `~/.local/state/questline/tip` | one line for the module tooltip |
| `~/.local/state/questline/vault-cache.json` | note mtimes and parsed tasks |
| `~/.local/state/questline/device-id` | local identity, never synced |
| `rules.toml` | points, caps, roles — edit by hand |

## Board

`ql-board` (or `./board.py`) opens a GTK4 window with two columns, **Open** and
**Done**, a project filter, and the fragment counter in the header. It reads with
`ql tasks --json` and writes with `ql done|reopen <id>`, which flips the checkbox
in the note as well — so Obsidian and the board never disagree.

- Keybind: `SUPER+ALT+SHIFT+B` (in `~/.config/hypr/UserConfigs/user_keybinds.lua`).
- Reloads on focus, on `r`, or with the refresh button; `Escape` closes it.
- No socket, no daemon: the window shells out to `ql` while it is open. A listener
  would break invariant 8, so it is deferred until a client that cannot shell out
  exists (phone or agent).

## HUD

`ql-hud` (or `./hud.py`) is the card that stays on the desktop: role, fragments,
streak, the open mode with its clock, and three progress bars (today's goal, the
project with the most closed tasks, the 7-day streak). It is a **Wayland layer
surface** (GTK3 + libgtk-layer-shell), anchored top-right, with keyboard
interactivity disabled, so it never steals a click from the app you are using.

- It only reads `~/.local/state/questline/hud.json`, which `ql` writes on every
  rebuild. The card never runs `ql` and never writes the log.
- Refreshes through a file monitor; the session minutes are local arithmetic on
  a 15 s timer. Measured: **0.07 % of a core**, ~58 MB RSS (24 MB PSS).
- Follows the monitor that has the focus, hides itself while a window is
  fullscreen, and `ql-hud-toggle` (keybind `SUPER+ALT+SHIFT+H`) shows or hides it.
- The waybar module keeps the same numbers (`42 FRG · 3d · ▣5`) even with no mode
  active, so the bar and the card never contradict each other.
- Started with the session from `~/.config/hypr/UserConfigs/user_startup.lua`.

## Notifications

`ql done <id> --notify` (what the board does) posts one bubble through the
session notification daemon (swaync here) with the fragments earned, the task
text and `today/day_goal FRG today`. There is no listener: the whole message is
composed and sent in the same process that writes the event.

- Closes that arrive within **5 s** of each other share the bubble: the title
  becomes `2 tasks closed · +20 FRG` and the body lists them. The group lives in
  `~/.local/state/questline/notify.json`, so separate `ql` runs still group.
- The bubble always uses id `9170`, so a new group replaces the previous one
  instead of stacking.
- `notify-send` is not used: one `gdbus` call, and a missing daemon is swallowed
  — closing a task never fails because a notification could not be shown.
- Tests set `QL_NOTIFY_LOG=<file>` to record the payloads instead of posting.

## Milestones

`ql done` (and `ql mode stop`, and `ql sync` when it emits something) checks the
milestones in `rules.toml [milestones]` and records the new ones as `milestone`
events. The key carries the identity, so nothing fires twice after a rebuild:

| Key | When |
|---|---|
| `chain:<project>:<session start>` | 5 tasks of the same project inside one mode session |
| `project:<name>` | project at 100 % with at least 10 tasks |
| `streak:<days>:<run start>` | streak reaches 7, 14 or 30 |
| `week:<day>` | every seventh qualified day of the streak |

Each new milestone writes `splash.json` and starts **one** short-lived
`ql-splash` process: a GTK3 layer surface on the overlay layer, keyboard
interactivity disabled, centred on the monitor under the pointer. It pops in over
300 ms, holds and disappears at 6 s (or on click), so it never takes the focus.
The medal is drawn with Cairo in two colours, one Led Zeppelin glyph per kind
(`zoso`, `icarus`, `presence`, `hermit`); F9.6 replaces the drawing with pixel
art. `QL_NO_SPLASH=1` records the milestone without opening the window (tests).

## Emblems

A project can own a pixel-art medal. `ql-emblem prompt <project>` prints the
generation brief (two colours, no text, transparent) and records the run, one per
project per day; `ql-emblem draw <project>` renders three free candidates with
Cairo and no model; `ql-emblem pick <project> <n>` validates the candidate and
installs it at

```
~/Documentos/Vault/Questline/emblems/<project>.png
```

The splash uses it with nearest-neighbour scaling, so a 128 px file still looks
like pixels at 96 px. `ql-emblem status` lists glyph, file and last run. Without
an emblem the procedural Cairo glyph is used, so nothing is mandatory. Method,
glyph library and prompt: `docs/subsystem/EMBLEMS.md`.

## Stamps and gifts

`ql done`, `ql mode stop`, `ql sync` and `ql kaizen end` evaluate a catalog of
**24 stamps**: 8 milestone, 8 streak and 8 Kaizen challenges. Each criterion is
a pure function of the event log, so a rebuild never re-issues one. New stamps
produce a single notification (id `9171`, separate from the task bubble) and
`ql stamps` shows what is earned and what is still unclaimed.

`ql claim <stamp-id>` is the only operation that renders an asset. It writes one
`gift.claim` event, a 640 × 360 two-colour PNG and a markdown card under
`Vault/Questline/gallery/`, and adds `✦N` to the waybar line and the HUD
headline. A second claim does nothing. Deleting a card does not revoke the gift;
the event is the truth. Full method: `docs/subsystem/GIFTS.md`.

## Agents and links

`ql-mcp` is a stdio MCP server: one JSON-RPC line in, one line out, no socket
and no dependencies. It exposes `board`, `status`, `done` and `add_task`; stdout
is reserved for protocol JSON. `initialize` and `tools/list` let an agent
discover the tools. `~/.local/share/applications/questline.desktop` opens the
GTK board from rofi/fuzzel.

`ql add` appends a checkbox to `Inbox.md` with a stable `^ql-…` block id, a
project tag and optional Obsidian wikilinks. `ql scan` stores the links in the
cache and `board` returns them with each card; display text drops the tags.
Wikilinks are navigation — the block id and the event log are the identity.
Details: `docs/subsystem/MCP.md`.

## Method

A sprint is a dated window in the vault: `ql sprint start --projects all`
commits the open tasks, and `ql sprint close` carries the unfinished ones into
the next sprint. `--weeks 2` or `3` widens the window; `--start` sets the first
day. One `nudge` notification fires on the first mode of each day while a sprint
is active, keyed by `(day, device)`, so syncing never duplicates it.

`ql review --days 7` folds the event log into a table of minutes, closed tasks
and fragments, then proposes **one** experiment (carry-over, biggest open
project, idle mode, or hold the pace). A Kaizen experiment is just two events:
`start` with a hypothesis, metric and baseline, then `end` with the value.
Both live in the log, so a rebuild keeps them and no daemon is involved.

## Test

```bash
python3 tests/smoke.py         # 119 checks, isolated temp vault
```

Every check that involves points is verified there; do not add scoring rules
without a check.

## Rollback

```bash
rm ~/.local/bin/ql                       # the hook then becomes a no-op
mv ~/Documentos/Vault/Questline ~/.local/share/questline-quarantine-$(date +%F)
rm -rf ~/.local/state/questline
```

Nothing else in the system is touched. The gamemode backups are
`~/.config/hypr/UserScripts/gamemode/*.bak.20261118_*`.
