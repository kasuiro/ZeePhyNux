#!/usr/bin/env python3
"""Deterministic gift-card renderer for claimed Questline stamps.

Local Cairo only: no model, no network, no daemon. The card is written by
`ql claim` and nowhere else. See docs/subsystem/GIFTS.md.
"""
import json
import os
import sys
from pathlib import Path

import cairo

from glyphs import draw as draw_glyph

WIDTH, HEIGHT = 640, 360
INK = (0x12 / 255, 0x10 / 255, 0x0E / 255)
GOLD = (0xE0 / 255, 0xB4 / 255, 0x5C / 255)


def wrap(text: str, limit: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if len(trial) > limit and current:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines[:2]


def label(cr: cairo.Context, text: str, x: float, y: float, size: int) -> None:
    cr.set_font_size(size)
    cr.move_to(x, y)
    cr.show_text(text)


def render_card(stamp: dict) -> cairo.ImageSurface:
    """One two-colour card for a claimed stamp."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    cr = cairo.Context(surface)
    cr.set_antialias(cairo.ANTIALIAS_NONE)

    cr.set_source_rgb(*INK)
    cr.paint()
    cr.set_source_rgb(*GOLD)
    cr.set_line_width(8)
    cr.rectangle(4, 4, WIDTH - 8, HEIGHT - 8)
    cr.stroke()

    cx, cy, radius = 132.0, HEIGHT / 2, 102.0
    cr.set_source_rgb(*GOLD)
    cr.arc(cx, cy, radius, 0, 2 * 3.141592653589793)
    cr.fill()
    cr.set_source_rgb(*INK)
    cr.arc(cx, cy, radius - 12, 0, 2 * 3.141592653589793)
    cr.fill()
    draw_glyph(cr, stamp.get("glyph", "zoso"), cx, cy, radius - 34, GOLD)

    cr.set_line_width(3)
    cr.move_to(266, 84)
    cr.line_to(WIDTH - 42, 84)
    cr.stroke()

    cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    label(cr, "QUESTLINE STAMP", 266, 72, 15)
    label(cr, stamp.get("name", stamp.get("id", "stamp")), 266, 138, 27)

    cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    label(cr, stamp.get("family", "").upper(), 266, 170, 14)
    for index, line in enumerate(wrap(stamp.get("criterion", ""), 44)):
        label(cr, line, 266, 206 + index * 20, 13)
    label(cr, f"glyph: {stamp.get('glyph', 'zoso')}", 266, 276, 12)
    label(cr, f"claimed {str(stamp.get('ts', ''))[:10]}", 266, 310, 12)
    return surface


def markdown(stamp: dict) -> str:
    return (f"# {stamp.get('name', stamp.get('id', 'stamp'))}\n\n"
            f"- id: `{stamp.get('id', '')}`\n"
            f"- family: {stamp.get('family', '')}\n"
            f"- glyph: `{stamp.get('glyph', 'zoso')}`\n"
            f"- criterion: {stamp.get('criterion', '')}\n"
            f"- claimed: {stamp.get('ts', '')}\n\n"
            f"![{stamp.get('name', 'stamp')}]({stamp.get('id', 'stamp')}.png)\n")


def write(path: Path, data: bytes | str) -> None:
    """Atomic write: a failed render never leaves a half card behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if isinstance(data, bytes):
        tmp.write_bytes(data)
    else:
        tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)


def install(stamp: dict, vault: Path) -> tuple[Path, Path]:
    """Write the PNG and the markdown card into the vault gallery."""
    gallery = vault / "Questline" / "gallery"
    gallery.mkdir(parents=True, exist_ok=True)
    png = gallery / f"{stamp['id']}.png"
    md = gallery / f"{stamp['id']}.md"
    if not png.is_file():
        surface = render_card(stamp)
        tmp_png = png.with_name(png.name + ".tmp")
        with tmp_png.open("wb") as fh:
            surface.write_to_png(fh)
        os.replace(tmp_png, png)
    if not md.is_file():
        write(md, markdown(stamp))
    return png, md


def main() -> int:
    """Render one card from a JSON payload (used by hand, not by ql)."""
    if len(sys.argv) != 3:
        print("usage: gifts.py <stamp.json> <out.png>", file=sys.stderr)
        return 2
    stamp = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    render_card(stamp).write_to_png(str(out))
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
