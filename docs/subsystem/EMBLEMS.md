# Questline — emblems

One medal per project. Pixel art, two colours, no text. The splash draws it on
top of the coin when the project has one; otherwise it falls back to the
procedural glyph it already ships with. Nothing breaks while a project has no
emblem.

## Rules

| Rule | Value |
|---|---|
| Canvas | square, `512 × 512` default, accepted from 128 to 1024 |
| Colours | exactly **two** opaque colours: ink `#12100E` and accent `#E0B45C` |
| Edges | hard pixels, no anti-aliasing, no gradients, no shadows |
| Background | transparent (the coin is the medal) |
| Text | none: no letters, numbers or watermark |
| Readability | must read at 96 px, the size the splash uses |
| Generation | remote and free, never on this machine; **one run per project per day**, three candidates per run |
| Choice | the user picks; the agent never accepts an emblem |

## Glyph library (Led Zeppelin)

| id | Reference | Milestone it serves |
|---|---|---|
| `zoso` | the four symbols of *Led Zeppelin IV* | chains (5 tasks in a row) |
| `icarus` | the Swan Song angel | project at 100 % |
| `presence` | the obelisk of *Presence* | streaks |
| `hermit` | the hermit of *Led Zeppelin IV* | perfect week |
| `airship` | the Hindenburg of *Led Zeppelin I* | inbox and projects without an emblem |
| `coda` | the arcs of *Coda* | spare |

The prompt picks a glyph by hashing the project name, so the same project always
asks for the same symbol. Override it by passing `--glyph` once, at prompt time.

## Flow

```bash
emblem.py prompt gallery          # prints the prompt, records today's run
# generate 3 candidates -> /tmp/questline-emblems/gallery-1..3.png
emblem.py pick gallery 2          # validates, installs, records
emblem.py status                  # what exists and when it was generated
```

There is also a **free path with no model**: `emblem.py draw gallery` renders the
same three candidates with Cairo at 128 px and upscales them 4× with
nearest-neighbour, so every pixel is a hard 4×4 block and the file keeps exactly
two colours. Use it when the model is unavailable or costs credits; the prompt
path stays for richer art.

1. `prompt` refuses a second run for the same project on the same day unless
   `--force` is passed. The quota lives in
   `~/.local/state/questline/emblems.json`.
2. Candidates land in `/tmp/questline-emblems/<project>-1.png`, `-2`, `-3`.
3. `pick` checks the file: PNG, square, size range, opaque fraction, and the
   number of distinct colours (anti-aliasing shows up as hundreds and is
   rejected). Then it copies the file to
   `~/Documentos/Vault/Questline/emblems/<project>.png`.
4. The splash reads the vault directly on its next run; no restart needed.
5. Rollback: delete the PNG and the procedural glyph comes back.

## Prompt template

```
Pixel-art arcade medallion, 512x512, transparent background, exactly TWO
colours: near-black #12100E and warm gold #E0B45C. A centred round coin with a
thick rim and one inner ring drawn in gold. Inside the coin: <glyph>. Bold 8-bit
pixel clusters, hard crisp edges, no anti-aliasing, no gradients, no shadows, no
extra colours, no background. No text, no letters, no numbers, no watermark.
Flat, iconic, readable at 96 pixels. Subject: <project>.
```

## Acceptance

- The file loads in `ql-splash` and the glyph is legible inside the coin.
- Vault path, colours and quota are checked by `tests/smoke.py`.
- The final look is the user's call; a rejected candidate is regenerated the
  next day, never the same day.
