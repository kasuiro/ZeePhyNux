# Questline — invariants

These do not change without a written reason in `BACKLOG.md`. Every later phase
is checked against them.

## Data

1. **The event log is the only source of truth.** `state.json` is a cache;
   deleting it must be harmless. `ql rebuild` is the proof.
2. **Events are immutable and additive.** Never edit or delete a line. A
   correction is a new event (`task.reopen`, a new role, a new session).
3. **Every event carries `event_id`.** Dedupe happens on merge, so replaying or
   re-syncing a file can never double-count.
4. **One log per device.** Device identity lives in
   `~/.local/state/questline/device-id` and never syncs.
5. **`day` is stamped by the emitting device.** Streaks use that field, never a
   re-interpretation of UTC on another machine.

## Writes outside Questline

6. **Questline never rewrites prose.** The only two writes into the vault are
   (a) appending a block ID to a task line once, and (b) ticking a checkbox when
   a card is closed from the board. Both are logged and reversible.
7. **Generated files live in `Vault/Questline/`** and carry a README that says
   so. A visible folder, never a hidden one: sync tools skip hidden paths.

## Resources

8. **No data daemon, no polling loop, no network in the core.** Writes happen
   only on a transition (mode change, task closed, role set). A resident UI is
   allowed as long as it only *reads* a file that `ql` pre-rendered (`hud.json`);
   it never computes points, never writes the log and never runs `ql` per tick.
   A notification is a single write at the transition; grouping inside the 5 s
   window uses a small state file, never a listener. The milestone splash is a
   one-shot layer surface that lives six seconds and exits; nothing waits. The
   daily sprint nudge follows the same rule: one write at the first mode, keyed
   by `(day, device)`, never a timer. Stamps are evaluated on a transition and
   notified once per batch; a gift card is rendered only inside `ql claim`,
   never by a rebuild or a resident UI. The MCP server follows the same rule:
   a stdio process owned by the client, never a listener or a background loop.
   **Approved exception (2026-11-20, `ql-ffe4bea3`):** voice-bridge may run
   exactly one wake-phrase listener per user session, started by
   `voicectl wake-start` and ended by `wake-stop`. It reads raw PCM from
   `pw-record` on stdout, uses no socket, port, network or systemd unit, loads
   one local Whisper model and writes only its own state file under
   `~/.local/state/voice-bridge/`. It never writes the core log or the vault.
   No other daemon is authorised by this exception.
9. **Zero new packages required.** `ql.py` is stdlib-only; the UI reuses what the
   desktop already has (Python + GTK, already installed for waybar/swaync).

## Scoring

10. **No penalties.** Streaks reset; fragments never go down.
11. **Open sessions earn nothing** until closed — that is what keeps `rebuild`
    reproducible and makes the log the only thing that matters.
12. **Caps exist to prevent farming**, not to punish: 40/day/mode, 4 h/session.
13. **A role must never be strictly better than another.** If it is, fix
    `rules.toml`; the affinity table is the only intended difference.

## Security (applies from F9.4 on)

14. **Local socket only** (`$XDG_RUNTIME_DIR/questline.sock`, mode 0600).
15. **HTTP binds to the tailnet address or loopback, never `0.0.0.0`, never the
    LAN IP.** Reads may be anonymous; writes require the bearer token in
    `~/.config/questline/token` (mode 0600).
16. **No secrets in the vault.** The vault syncs to other devices and possibly
    other people's servers; tokens never go there.
