# Questline — backlog

One sprint = one week. Status: `[ ]` pending · `[x]` done · `[~]` in progress.
Every item names its acceptance test; "done" means the test passes, not that
the code exists.

## F9.1 — core (done)

- [x] `QL-101` event log with `event_id`, `device`, `seq`, `day`
      → *accept*: duplicate line in the file changes nothing
- [x] `QL-102` `ql rebuild` is a pure fold of the merged log
      → *accept*: two rebuilds are byte-identical
- [x] `QL-103` scoring: 1 FRG/10 min, 40/day/mode, 4 h/session, 10/task
      → *accept*: 10 h session = 24 FRG; two of them = 40 (cap)
- [x] `QL-104` role affinity ×1.25 on its modes only
      → *accept*: artisan boosts devmode, not readmode
- [x] `QL-105` streak from `day` fields, `+5/day`, `+25` at 7
      → *accept*: 2 consecutive days = 10
- [x] `QL-106` multi-device merge, dedupe by `event_id`
      → *accept*: two logs of the same session = 6 FRG, not 12
- [x] `QL-107` gamemode hook (`gm_quest`) non-blocking and optional
      → *accept*: toggle a mode with `ql` removed from PATH → no error, mode works
- [x] `QL-108` smoke suite, no dependencies
      → *accept*: `python3 tests/smoke.py` → 0 failures

## F9.2 — vault scan (done)

- [x] `QL-201` parse `- [ ]` / `- [x]` from `~/Documentos/Vault/**/*.md`
      → *accept*: 300 notes scanned in < 1 s on this HDD — **0.52 s cold / 0.40 s warm, 6 000 tasks**
- [x] `QL-202` stable task identity via Obsidian block id `^ql-xxxxxx`
      → *accept*: moving a line inside a file keeps its history
- [x] `QL-203` one-time block-ID append, announced and backed up
      → *accept*: a second run writes nothing
- [x] `QL-204` mtime cache so unchanged files are not re-read
      → *accept*: second run touches 0 notes — **300 cached, 0 read**
- [x] `QL-205` project grouping from `#project/<name>` tags
      → *accept*: `ql tasks --project gallery` filters correctly
- [x] `QL-206` never follows symlinks out of the vault; skips `.obsidian/` and `Questline/`
      → *accept*: no read outside the vault

## F9.3 — waybar (done)

- [x] `QL-301` `FRG · streak · role` in the existing `custom/gamemode`
      → *accept*: ≤ 0.2% CPU added — **+0.01%**, and the module got 12× cheaper on the way (below)
- [x] `QL-302` click → open board (F9.4), no long-poll in the module
      → *accept*: no subprocess per tick (0 forks; two `read` builtins per tick)

## F9.4 — board (partial: UI done, socket deferred)

- [x] `QL-401` GTK4 window: `Open · Done`, project filter, reload on focus
      → *accept*: starts in ~0.4 s, ~55 MB while open, exits with Escape
- [x] `QL-402` keybind `SUPER+ALT+SHIFT+B` → `ql-board`
      → *accept*: Lua validates; **takes effect on the next Hyprland reload**
- [~] `QL-403` Unix socket API — **deferred on purpose.** It needs a resident
      listener, which invariant 8 forbids. Do it only when a client that cannot
      shell out appears (phone or agent), and then via a systemd user socket
      unit so it starts on the first connection and exits when idle.
- [x] `QL-404` ticking a card writes `task.done` **and** the checkbox
      → *accept*: Obsidian shows it ticked; `reopen` undoes both; `sync` after
      `done` emits nothing (4 checks in the suite)

## F9.5a — desktop HUD (done)

- [x] `QL-451` `hud.json` pre-rendered by `ql rebuild`: role, fragments, day goal,
      streak, open session with its start time, next 3 tasks, per-project counts
      → *accept*: the card never runs `ql`; 6 checks in the suite
- [x] `QL-452` pinned card: GTK3 + libgtk-layer-shell, top-right, no keyboard
      focus, three progress bars (today · project · streak) and the session clock
      → *accept*: **58 MB RSS / 24 MB PSS**, **0.07% of a core** idle, clicking
      it never takes the focus away from the active app
- [x] `QL-453` follows the focused monitor (matched by geometry, not by name)
      → *accept*: moving the focus from `HDMI-A-1` to `eDP-1` re-maps the card
- [x] `QL-454` hidden while an app is fullscreen, and `SUPER+ALT+SHIFT+H` toggles it
      → *accept*: fullscreen leaves 0 surfaces; the toggle restores it
- [x] `QL-455` waybar adds the open-task count (`▣3`) to the same module, and it
      stays visible when no mode is active
      → *accept*: no extra process per tick, same `line` file
- [x] `QL-456` autostart with the session
      → *accept*: `user_startup.lua` runs `ql-hud` through `exec_once`

## F9.5b — desktop notifications (done)

- [x] `QL-457` `ql done <id> --notify` posts one bubble per closed task: the
      fragments earned in the title, the task and the day goal in the body
      → *accept*: **11 checks** in the suite; silent without the flag, on reopen
      and when the task was already closed
- [x] `QL-458` closes within 5 s share one bubble (`replaces_id` 9170); the group
      survives between processes through `notify.json`, with no listener
      → *accept*: two closes read "2 tasks closed · +20 FRG"; a close 60 s later
      opens a new group of one
- [x] `QL-459` the board passes `--notify` when it closes a task, and a missing
      daemon never breaks the close
      → *accept*: a `gdbus` failure is swallowed; the vault and the log still update

## F9.5c — milestones and splash (done)

- [x] `QL-460` `milestone` events recorded once, keyed by identity (project, run
      start, session start), so a rebuild never re-fires them
      → *accept*: **11 checks**; a sixth close or an extra session adds nothing
- [x] `QL-461` triggers: 5 tasks of one project in one mode session, project at
      100 % with ≥ 10 tasks, streak 7/14/30, perfect week (every 7 days)
      → *accept*: 5-task project does not celebrate; 10-task one does
- [x] `QL-462` `splash.py`: GTK3 layer surface on the overlay layer, keyboard
      disabled, centred on the focused monitor, popup of 300 ms, gone at 6 s or
      on click, never takes focus
      → *accept*: 440×380 at the centre of the pointer's monitor, active window
      unchanged, ~57 MB RSS, no CPU during the hold
- [x] `QL-463` procedural medal in two colours with a Led Zeppelin glyph
      (`zoso`, `icarus`, `presence`, `hermit`), no text inside the image
      → *accept*: the splash reads its glyph from `splash.json`; F9.6 will swap
      the drawing for pixel art without touching the trigger

## F9.5d — pixel-art emblems (pipeline done, candidates pending the pick)

- [x] `QL-464` `emblems.py prompt <project>` prints the two-colour brief, picks a
      glyph by hashing the project and enforces one run per project per day
      → *accept*: a second run that day exits 1 unless `--force`
- [x] `QL-465` `emblems.py pick <project> <n>` validates PNG, square, size,
      opaque area and **exactly two colours** (anti-aliasing is rejected), then
      copies to `Vault/Questline/emblems/<project>.png`
      → *accept*: two colours installs; a third colour is refused; a missing
      candidate reports the path
- [x] `QL-466` the splash draws the installed PNG inside the coin with
      nearest-neighbour scaling, and falls back to the Cairo glyph without one
      → *accept*: `QL_VAULT` with an emblem changes the medal; deleting it
      returns the procedural one
- [x] `QL-468` free local renderer: `emblems.py draw <project>` writes three
      deterministic candidates with the same two colours, no model involved
      → *accept*: three 512 px files, exactly two colours each, 4×4 hard pixels
- [x] `QL-467` the three candidates are generated and the user picks one
      → *accept*: **candidate 3 (octagonal)** installed at
      `Vault/Questline/emblems/hyprland.png`; the splash shows it and deleting
      the file brings back the procedural glyph. A future free image service can
      replace it: regenerate the prompt and pick again another day.

## F9.5 — stamps and gifts (done)

- [x] `QL-501` 24 stamps in 3 families: milestones, streaks, Kaizen challenges
      → *accept*: 8 per family, pure criteria over the log; one `stamp` event
      per id, never re-issued by a rebuild
- [x] `QL-502` claim flow: notification → `ql claim` → cosmetic applied
      → *accept*: one batch notification (id 9171), `ql claim <id>` writes one
      `gift.claim` event and shows `✦N` in waybar and the HUD; a second claim is
      a no-op
- [x] `QL-503` gallery gift card generated on claim (local, no model)
      → *accept*: nothing is rendered before the claim; `ql claim` writes a
      640 × 360 two-colour PNG and a markdown card in
      `Vault/Questline/gallery/`; method in `GIFTS.md`

## F9.6 — the method (done)

- [x] `QL-601` sprint object: start/end dates, committed tasks, carried-over
      → *accept*: ISO-week id, 7/14/21-day window, close carries the open ones
      into the next sprint; `Vault/Questline/sprint.json`
- [x] `QL-602` daily nudge on the first mode of the day (one notification, max)
      → *accept*: no sprint, no nudge; a second `mode.start` the same day adds
      nothing; the nudge is a `nudge` event plus one desktop bubble
- [x] `QL-603` weekly review: minutes per mode, tasks, fragments, one suggested
      experiment → *accept*: `ql review --days 7` prints the table, the totals
      and an experiment; the sprint and carry-over shape the suggestion
- [x] `QL-604` Kaizen experiment record (`kaizen` event) with before/after metric
      → *accept*: `ql kaizen start` + `end` keeps baseline → value, rejects an
      unknown id; no local generation or daemon

## F9.7 — other devices (deferred, optional)

Deferred by the user on 2026-11-18: **not a priority** because of the risk of
exposing the board and of system-level changes (firewall, Syncthing). Keep the
items open, but do not implement them without explicit re-approval.

- [ ] `QL-701` `ql serve` read-only HTML board on the tailnet address
      → *accept*: opens from the phone over Tailscale, never binds `0.0.0.0`
- [ ] `QL-702` writes require the bearer token (`~/.config/questline/token`)
- [ ] `QL-703` vault sync setup: Syncthing on the desktop and on the phone
      → *accept*: a task added on the phone appears on the desktop and vice versa
- [ ] `QL-704` EMUI battery exemption documented for the HUAWEI Y9 2019
      (autostart allowed, battery "manual", otherwise Syncthing dies)

## F9.8 — agents and apps (done)

- [x] `QL-801` MCP stdio server, zero dependencies, tools:
      `board`, `status`, `done`, `add_task`
      → *accept*: one JSON line in/out, four tools discovered via `tools/list`,
      an agent reads the board and closes a card; a second `done` is a no-op
- [x] `QL-802` `ql` usable from rofi/fuzzel as a launcher entry
      → *accept*: `~/.local/share/applications/questline.desktop` starts
      `ql-board`, no daemon
- [x] `QL-803` Obsidian links as navigation, not identity
      → *accept*: `ql add` writes block id + `[[wikilinks]]`, `ql scan` exposes
      `links`, `board` returns them, display text stays clean; block id remains
      the stable key. Method in `MCP.md`

## F9.9 — optional

- [ ] `QL-901` Vikunja + CalDAV if native phone tasks are ever needed
- [ ] `QL-902` import/export CSV for a Trello migration

## Risks

| Risk | Mitigation |
|---|---|
| Gamification turns into noise | caps and a single daily notification; the log stays useful without the game |
| Two-way sync conflicts in the vault | Questline writes only block IDs and checkboxes; prose is never touched |
| Clock skew across devices | `day` stamped locally, ordering by `(ts, device, seq)` |
| Event log grows unbounded | ~200 events/day is ~70k/year; monthly checkpoints still deferred (no need yet) |
| Scope creep into a full task manager | the vault is the task manager; Questline only reads |
