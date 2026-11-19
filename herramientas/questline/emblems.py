#!/usr/bin/env python3
"""Emblem pipeline — prompt, validate and install a project medal.

The image itself is generated elsewhere (remote, free): this tool never draws a
candidate, it only writes the prompt, checks the file and copies it into the
vault. Documentation: docs/subsystem/EMBLEMS.md.

    ./emblems.py prompt gallery
    ./emblems.py pick gallery 2
    ./emblems.py status
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import tomllib
from datetime import datetime
from pathlib import Path

import cairo

from glyphs import GLYPHS, draw as draw_glyph

VAULT = Path(os.environ.get("QL_VAULT", "~/Documentos/Vault")).expanduser()
HOME = Path(os.environ.get("QL_HOME", "~/.local/state/questline")).expanduser()
RULES = Path(os.environ.get("QL_RULES", Path(__file__).resolve().with_name("rules.toml")))
CANDIDATES = Path(os.environ.get("QL_EMBLEM_OUT", "/tmp/questline-emblems")).expanduser()
RECORD = HOME / "emblems.json"
EMBLEMS = VAULT / "Questline" / "emblems"

GLYPHS_ORDER = sorted(GLYPHS)
GRID = 128            # pixel-art canvas before the nearest-neighbour upscale
SCALE = 4             # 128 -> 512, hard 4x4 pixels

PROMPT = """Pixel-art arcade medallion, {size}x{size}, transparent background, exactly TWO
colours: near-black {ink} and warm gold {accent}. A centred round coin with a
thick rim and one inner ring drawn in gold. Inside the coin: {glyph}. Bold 8-bit
pixel clusters, hard crisp edges, no anti-aliasing, no gradients, no shadows, no
extra colours, no background. No text, no letters, no numbers, no watermark.
Flat, iconic, readable at 96 pixels. Subject: {project}."""


def settings() -> dict:
    with RULES.open("rb") as fh:
        return tomllib.load(fh).get("emblems", {})


def slug(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in text.lower()).strip("-")


def glyph_for(project: str) -> str:
    """Stable: the same project always asks for the same symbol."""
    digest = hashlib.sha1(project.encode()).hexdigest()
    return GLYPHS_ORDER[int(digest[:8], 16) % len(GLYPHS_ORDER)]


def colour(value: str) -> tuple:
    raw = value.lstrip("#")
    return tuple(int(raw[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def octagon(cr: cairo.Context, cx: float, cy: float, radius: float) -> None:
    for point in range(8):
        angle = math.pi / 8 + point * math.pi / 4
        x, y = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
        if point:
            cr.line_to(x, y)
        else:
            cr.move_to(x, y)
    cr.close_path()


def render(project: str, variant: int) -> cairo.ImageSurface:
    """One free, deterministic candidate: pixel art drawn at 128 px, upscaled 4x."""
    cfg = settings()
    ink = colour(cfg.get("ink", "#12100E"))
    gold = colour(cfg.get("accent", "#E0B45C"))
    glyph = load_record().get(project, {}).get("glyph") or glyph_for(project)

    small = cairo.ImageSurface(cairo.FORMAT_ARGB32, GRID, GRID)
    cr = cairo.Context(small)
    cr.set_antialias(cairo.ANTIALIAS_NONE)
    cr.set_source_rgba(0, 0, 0, 0)
    cr.paint()

    cx, cy = GRID / 2, GRID / 2
    r = GRID * 0.44
    face, mark = (ink, gold) if variant != 2 else (gold, ink)

    if variant == 3:                          # octagonal medal
        cr.set_source_rgb(*face)
        octagon(cr, cx, cy, r)
        cr.fill()
    else:
        cr.set_source_rgb(*face)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.fill()

    cr.set_source_rgb(*mark)
    cr.set_line_width(GRID * 0.045)
    if variant == 3:
        octagon(cr, cx, cy, r - GRID * 0.03)
        cr.stroke()
    else:
        cr.arc(cx, cy, r - GRID * 0.03, 0, 2 * math.pi)
        cr.stroke()
    cr.set_line_width(GRID * 0.012)
    cr.arc(cx, cy, r - GRID * 0.12, 0, 2 * math.pi)
    cr.stroke()

    draw_glyph(cr, glyph, cx, cy, r - GRID * 0.17, mark)

    out = cairo.ImageSurface(cairo.FORMAT_ARGB32, GRID * SCALE, GRID * SCALE)
    scaled = cairo.Context(out)
    scaled.scale(SCALE, SCALE)
    scaled.set_source_surface(small, 0, 0)
    scaled.get_source().set_filter(cairo.FILTER_NEAREST)
    scaled.paint()
    return out


def draw_candidates(project: str, force: bool) -> int:
    """Three free candidates, no model involved: prompt, pick, or draw."""
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    written = []
    for variant in (1, 2, 3):
        target = CANDIDATES / f"{slug(project)}-{variant}.png"
        if target.exists() and not force:
            print(f"exists: {target} (--force to redraw)", file=sys.stderr)
            return 1
        render(project, variant).write_to_png(str(target))
        written.append(target)
    for target in written:
        print(target)
    print(f"\ninstall: ./emblems.py pick {project} <1|2|3>")
    return 0


def load_record() -> dict:
    if RECORD.is_file():
        try:
            return json.loads(RECORD.read_text())
        except (OSError, ValueError):
            pass
    return {}


def save_record(data: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = RECORD.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, RECORD)


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def inspect(path: Path) -> tuple[int, int, list, float]:
    """(width, height, opaque colours, opaque fraction) straight from the PNG."""
    surface = cairo.ImageSurface.create_from_png(str(path))
    width, height = surface.get_width(), surface.get_height()
    stride = surface.get_stride()
    data = bytes(surface.get_data())
    colours = set()
    opaque = 0
    for y in range(height):
        row = data[y * stride:(y + 1) * stride]
        for x in range(width):
            b, g, r, a = row[4 * x:4 * x + 4]
            if a < 8:
                continue
            opaque += 1
            colours.add((r, g, b))
    return width, height, sorted(colours), opaque / float(width * height)


def prompt(project: str, glyph: str | None, force: bool) -> int:
    cfg = settings()
    record = load_record()
    entry = record.setdefault(project, {})
    if entry.get("prompted") == today() and not force:
        print(f"{project}: already generated today ({entry['prompted']}); "
              f"one run per project per day (--force to override)")
        return 1
    choice = glyph or entry.get("glyph") or glyph_for(project)
    if choice not in GLYPHS:
        print(f"unknown glyph {choice} (one of: {', '.join(sorted(GLYPHS))})", file=sys.stderr)
        return 2
    entry.update({"glyph": choice, "prompted": today()})
    save_record(record)
    print(PROMPT.format(size=cfg.get("size", 512), ink=cfg.get("ink", "#12100E"),
                        accent=cfg.get("accent", "#E0B45C"),
                        glyph=GLYPHS[choice], project=project))
    print(f"\ncandidates: {CANDIDATES}/{slug(project)}-1.png .. -3.png")
    print(f"install:    ./emblems.py pick {project} <n>")
    return 0


def pick(project: str, number: int, force: bool) -> int:
    cfg = settings()
    source = CANDIDATES / f"{slug(project)}-{number}.png"
    if not source.is_file():
        print(f"missing candidate: {source}", file=sys.stderr)
        return 2
    try:
        width, height, colours, opaque = inspect(source)
    except (OSError, cairo.Error) as exc:
        print(f"cannot read {source}: {exc}", file=sys.stderr)
        return 2
    problems = []
    if width != height:
        problems.append(f"not square ({width}x{height})")
    low, high = cfg.get("min_size", 128), cfg.get("max_size", 1024)
    if not low <= width <= high:
        problems.append(f"size {width} outside {low}..{high}")
    if len(colours) > 2:
        problems.append(f"{len(colours)} opaque colours (pixel art needs 2: no anti-aliasing)")
    if opaque < 0.05 or opaque > 0.98:
        problems.append(f"opaque area {opaque:.0%} (a coin on transparent background)")
    if problems and not force:
        for line in problems:
            print(f"rejected: {line}", file=sys.stderr)
        print("fix the prompt or pass --force to install anyway", file=sys.stderr)
        return 1
    EMBLEMS.mkdir(parents=True, exist_ok=True)
    target = EMBLEMS / f"{slug(project)}.png"
    shutil.copyfile(source, target)
    record = load_record()
    record.setdefault(project, {}).update(
        {"picked": today(), "file": str(target.relative_to(VAULT)), "candidate": number,
         "size": width, "colours": [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in colours]})
    save_record(record)
    print(f"installed {target} ({width}x{height}, {len(colours)} colours)")
    return 0


def status() -> int:
    record = load_record()
    projects = sorted(set(record) | {p.stem for p in EMBLEMS.glob("*.png")} if EMBLEMS.is_dir()
                      else set(record))
    if not projects:
        print("no emblems yet")
        return 0
    print(f"{'project':<20} {'glyph':<10} {'emblem':<8} {'prompted':<12} file")
    for name in projects:
        entry = record.get(name, {})
        target = EMBLEMS / f"{slug(name)}.png"
        print(f"{name:<20} {entry.get('glyph', '-'):<10} "
              f"{'yes' if target.is_file() else '-':<8} {entry.get('prompted', '-'):<12} "
              f"{target.relative_to(VAULT) if target.is_file() else ''}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="emblems", description="Questline emblem pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prompt", help="print the generation prompt for a project")
    p.add_argument("project")
    p.add_argument("--glyph")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("pick", help="validate and install a candidate")
    p.add_argument("project")
    p.add_argument("number", type=int)
    p.add_argument("--force", action="store_true")

    sub.add_parser("status", help="emblems installed and quota")
    p = sub.add_parser("draw", help="render three free candidates without a model")
    p.add_argument("project")
    p.add_argument("--force", action="store_true")

    a = ap.parse_args()
    if a.cmd == "prompt":
        return prompt(a.project, a.glyph, a.force)
    if a.cmd == "pick":
        return pick(a.project, a.number, a.force)
    if a.cmd == "draw":
        return draw_candidates(a.project, a.force)
    return status()


if __name__ == "__main__":
    sys.exit(main())
