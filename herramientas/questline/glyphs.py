"""Led Zeppelin glyph library, shared by the splash and the emblem renderer.

Cairo only: no GTK, no state. Every glyph is drawn inside a circle of radius r
centred on (cx, cy) in one colour, so the caller decides the palette.
"""
import math

import cairo

GLYPHS = {
    "zoso": "the Led Zeppelin IV 'Zoso' symbol: a stylised Z crossed by a long "
            "diagonal stroke, a dot above it",
    "icarus": "the Swan Song angel: a winged figure with outstretched feathered "
              "wings and a small head",
    "presence": "the Presence obelisk: a tall narrow monolith under a small full moon",
    "hermit": "the Led Zeppelin IV hermit: a hooded figure holding a lantern on a staff",
    "airship": "the Hindenburg airship of the first album: a long zeppelin with "
               "tail fins and a gondola",
    "coda": "the Coda symbol: three concentric arcs opening to the right, like a "
            "rainbow fan",
}


def draw(cr: cairo.Context, name: str, cx: float, cy: float, r: float,
         colour: tuple) -> None:
    cr.set_source_rgb(*colour)
    cr.set_line_width(max(1.0, r * 0.055))
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)

    if name == "icarus":                       # Swan Song angel: two wings + body
        for side in (-1, 1):
            cr.move_to(cx, cy - r * 0.10)
            cr.curve_to(cx + side * r * 0.62, cy - r * 0.72,
                        cx + side * r * 1.00, cy + r * 0.10,
                        cx + side * r * 0.16, cy + r * 0.52)
            cr.close_path()
            cr.stroke()
        cr.arc(cx, cy - r * 0.34, r * 0.09, 0, 2 * math.pi)
        cr.fill()
        cr.move_to(cx, cy - r * 0.22)
        cr.line_to(cx, cy + r * 0.60)
        cr.stroke()

    elif name == "zoso":                       # the IV symbol: Z, dot and slash
        cr.move_to(cx - r * 0.44, cy - r * 0.46)
        cr.curve_to(cx - r * 0.10, cy - r * 0.58, cx + r * 0.16, cy - r * 0.40,
                    cx + r * 0.34, cy - r * 0.52)
        cr.line_to(cx - r * 0.34, cy + r * 0.46)
        cr.line_to(cx + r * 0.36, cy + r * 0.46)
        cr.stroke()
        cr.arc(cx + r * 0.40, cy - r * 0.54, r * 0.07, 0, 2 * math.pi)
        cr.fill()
        cr.move_to(cx - r * 0.52, cy - r * 0.14)
        cr.line_to(cx + r * 0.52, cy + r * 0.10)
        cr.stroke()

    elif name == "presence":                   # Presence: obelisk and moon
        cr.move_to(cx - r * 0.30, cy + r * 0.58)
        cr.line_to(cx - r * 0.17, cy - r * 0.30)
        cr.line_to(cx + r * 0.17, cy - r * 0.30)
        cr.line_to(cx + r * 0.30, cy + r * 0.58)
        cr.close_path()
        cr.fill()
        cr.arc(cx, cy - r * 0.56, r * 0.15, 0, 2 * math.pi)
        cr.stroke()

    elif name == "airship":                    # Led Zeppelin I: the Hindenburg
        cr.save()
        cr.translate(cx, cy)
        cr.rotate(-0.18)
        cr.save()
        cr.scale(1.0, 0.34)
        cr.arc(0, 0, r * 0.60, 0, 2 * math.pi)
        cr.restore()
        cr.stroke()
        for side in (-1, 1):
            cr.move_to(r * 0.44, side * r * 0.02)
            cr.line_to(r * 0.74, side * r * 0.26)
            cr.line_to(r * 0.74, side * r * 0.06)
        cr.stroke()
        cr.rectangle(-r * 0.10, r * 0.22, r * 0.26, r * 0.12)
        cr.stroke()
        cr.restore()

    elif name == "coda":                       # Coda: arcs opening to the right
        for radius in (0.68, 0.46, 0.24):
            cr.arc(cx + r * 0.10, cy, r * radius, math.pi * 0.60, math.pi * 1.40)
            cr.stroke()

    else:                                      # hermit: figure, staff, lantern
        cr.arc(cx - r * 0.02, cy - r * 0.46, r * 0.10, 0, 2 * math.pi)
        cr.stroke()
        cr.move_to(cx - r * 0.02, cy - r * 0.36)
        cr.line_to(cx, cy + r * 0.16)
        cr.line_to(cx - r * 0.18, cy + r * 0.56)
        cr.move_to(cx, cy + r * 0.16)
        cr.line_to(cx + r * 0.20, cy + r * 0.56)
        cr.stroke()
        cr.move_to(cx - r * 0.36, cy - r * 0.62)
        cr.line_to(cx - r * 0.36, cy + r * 0.60)
        cr.stroke()
        cr.rectangle(cx + r * 0.16, cy - r * 0.26, r * 0.20, r * 0.20)
        cr.stroke()
        cr.move_to(cx - r * 0.02, cy - r * 0.28)
        cr.line_to(cx + r * 0.16, cy - r * 0.16)
        cr.stroke()
