# Questline — stamps and gifts

Stamps are achievements; gifts are the cosmetic cards they unlock. Both are
derived from the event log, so a rebuild never loses them and two devices cannot
disagree. No image model is used and nothing is generated until the user claims
a gift explicitly.

## Catalog

24 stamps in three families of eight:

| Family | Ids |
|---|---|
| milestone | `chain-five`, `clean-sweep`, `streak-seven`, `streak-fourteen`, `streak-thirty`, `perfect-week`, `centurion`, `fragment-thousand` |
| streak | `first-light`, `warm-up`, `early-bird`, `night-owl`, `five-modes`, `all-modes`, `weekend-warrior`, `daily-ten` |
| kaizen | `hypothesis`, `measured`, `drop-three`, `zero-open`, `time-saved`, `repeat-offender`, `chain-of-custody`, `weekly-cadence` |

Each stamp has a stable id, a family, a one-line criterion, a Led Zeppelin glyph
from `glyphs.py`, and a gift of the same id. Criteria read only `events` and the
projection from `fold()`; they are pure functions, so the same log always earns
the same stamps.

## Flow

```bash
ql stamps                         # earned stamps, claimed ones marked
ql stamps --json
ql claim <stamp-id>               # generate the card and apply the cosmetic
ql claim <stamp-id>               # again: no new event, no new file
```

1. A transition (`ql done`, `ql mode stop`, `ql sync`, `ql kaizen end`) evaluates
   the catalog. A new criterion writes one `stamp` event keyed by the stamp id
   and posts **one** notification for the whole batch:
   `Questline · N stamps earned`. Notification id 9171 is used so it never
   replaces the 5-second task-close bubble (9170).
2. `ql claim <id>` refuses an unearned or unknown id. On success it writes one
   `gift.claim` event, renders the card, and refreshes `state.json`, `hud.json`
   and the waybar files. The cosmetic is the badge count: `✦N` in the waybar
   line and the HUD headline; the full list is in the HUD tooltip.
3. A second claim is a no-op: the existing `gift.claim` event is returned and
   no file is touched. Idempotence is derived from the log, not a lock file.

## Gift card

The card is **generated only by `ql claim`**, never by `rebuild`, `ql status`,
`ql stamps` or a monitor:

| Item | Value |
|---|---|
| Directory | `~/Documentos/Vault/Questline/gallery/` |
| PNG | `<stamp-id>.png`, 640 × 360, two colours (`#12100E` / `#E0B45C`) |
| Markdown | `<stamp-id>.md` with criterion, family, glyph and claim timestamp |
| Renderer | `gifts.py`: local Cairo, deterministic, no model, no network |
| Look | hard-edged medallion with the stamp glyph and English label text |
| Acceptance | the user judges the look; a card can be replaced by hand at any time |

The renderer writes to a temporary file and renames it, so a failed render
never leaves a half card. Deleting a card does not revoke the gift: the
`gift.claim` event remains in the log and `ql claim` simply reports it as
already claimed.

## Multi-device

`stamp` and `gift.claim` are ordinary events: file union, dedupe by `event_id`,
order by `(ts, device, seq)`. A stamp earned on one device appears on the other
after the log is synced; the card is regenerated locally only when that device
claims it. The gallery PNG itself is never merged — the event is the truth.
