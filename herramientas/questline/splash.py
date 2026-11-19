#!/usr/bin/env python3
"""Questline splash — the milestone medal that pops for six seconds.

Started by `ql` on the transition that earns a milestone, never resident. It is
a Wayland layer surface on the overlay layer, keyboard interactivity disabled, so
it cannot take the focus from the app that is running. A click dismisses it early.

    ./splash.py ~/.local/state/questline/splash.json
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell  # noqa: E402

from glyphs import draw as draw_glyph  # noqa: E402

STATE_DIR = Path(os.environ.get("QL_HOME", "~/.local/state/questline")).expanduser()
VAULT = Path(os.environ.get("QL_VAULT", "~/Documentos/Vault")).expanduser()
EMBLEMS = VAULT / "Questline" / "emblems"
WIDTH, HEIGHT = 440, 380
LIFETIME = 6.0            # seconds on screen, dismiss included
POP_IN = 0.30             # seconds of popup before it holds
FADE_OUT = 0.35
INK = (0.055, 0.055, 0.070)
ACCENT = (0.878, 0.706, 0.361)
FONT = "JetBrainsMono Nerd Font"


def ease_out_back(p: float) -> float:
    """Overshoot at the end: the coin lands with a small bounce."""
    c1, c3 = 1.70158, 2.70158
    p -= 1
    return 1 + c3 * p ** 3 + c1 * p ** 2


def emblem_surface(project: str):
    """The project's installed pixel-art medal, or None for the procedural one."""
    if not project:
        return None
    name = "".join(c if c.isalnum() or c in "-_" else "-" for c in project.lower()).strip("-")
    target = EMBLEMS / f"{name}.png"
    if not target.is_file():
        return None
    try:
        return cairo.ImageSurface.create_from_png(str(target))
    except (OSError, cairo.Error):
        return None


def draw(cr: cairo.Context, width: float, height: float, payload: dict) -> None:
    """One frame: card, coin, rim, glyph, title and subtitle."""
    pad, radius = 16.0, 22.0
    x0, y0, w, h = pad, pad, width - 2 * pad, height - 2 * pad
    cr.new_sub_path()
    cr.arc(x0 + w - radius, y0 + radius, radius, -math.pi / 2, 0)
    cr.arc(x0 + w - radius, y0 + h - radius, radius, 0, math.pi / 2)
    cr.arc(x0 + radius, y0 + h - radius, radius, math.pi / 2, math.pi)
    cr.arc(x0 + radius, y0 + radius, radius, math.pi, 3 * math.pi / 2)
    cr.close_path()
    cr.set_source_rgba(*INK, 0.94)
    cr.fill_preserve()
    cr.set_source_rgba(*ACCENT, 0.55)
    cr.set_line_width(1.4)
    cr.stroke()

    cx, cy, r = width / 2, 158.0, 96.0
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.set_source_rgba(*INK, 0.96)
    cr.fill_preserve()
    cr.set_source_rgb(*ACCENT)
    cr.set_line_width(6)
    cr.stroke()
    cr.arc(cx, cy, r - 16, 0, 2 * math.pi)
    cr.set_line_width(1.6)
    cr.set_source_rgba(*ACCENT, 0.60)
    cr.stroke()

    emblem = emblem_surface(payload.get("project", ""))
    if emblem is not None:
        side = (r - 18) * 2
        cr.save()
        cr.translate(cx - side / 2, cy - side / 2)
        cr.scale(side / emblem.get_width(), side / emblem.get_height())
        cr.set_source_surface(emblem, 0, 0)
        cr.get_source().set_filter(cairo.FILTER_NEAREST)
        cr.paint()
        cr.restore()
    else:
        draw_glyph(cr, payload.get("glyph", "zoso"), cx, cy, r - 30, ACCENT)
    title = payload.get("title", "Milestone")
    subtitle = payload.get("subtitle", "")
    cr.set_source_rgb(*ACCENT)
    cr.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(26)
    ext = cr.text_extents(title)
    cr.move_to(width / 2 - ext.width / 2 - ext.x_bearing, 312)
    cr.show_text(title)

    if subtitle:
        cr.set_source_rgba(*ACCENT, 0.72)
        cr.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(13)
        ext = cr.text_extents(subtitle)
        cr.move_to(width / 2 - ext.width / 2 - ext.x_bearing, 342)
        cr.show_text(subtitle)


class Splash:
    def __init__(self, payload: dict):
        self.payload = payload
        self.started = time.monotonic()
        self.closed = False
        # One expensive render; every animation frame is a cheap blit of it.
        self.card = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
        draw(cairo.Context(self.card), WIDTH, HEIGHT, payload)

        win = Gtk.Window()
        self.win = win
        win.set_decorated(False)
        win.set_resizable(False)
        win.set_skip_taskbar_hint(True)
        win.set_skip_pager_hint(True)
        win.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        win.set_size_request(WIDTH, HEIGHT)
        win.set_app_paintable(True)
        win.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        win.connect("button-press-event", lambda *_: self.close())

        GtkLayerShell.init_for_window(win)
        GtkLayerShell.set_namespace(win, "questline-splash")
        GtkLayerShell.set_layer(win, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_exclusive_zone(win, -1)

        # Centre on the monitor under the pointer, with margins because a layer
        # surface anchored on both sides would swallow clicks on the whole screen.
        monitor, geom = self.focused_monitor()
        GtkLayerShell.set_monitor(win, monitor)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.LEFT,
                                 max(0, (geom.width - WIDTH) // 2))
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.TOP,
                                 max(0, (geom.height - HEIGHT) // 2))

        area = Gtk.DrawingArea()
        area.set_size_request(WIDTH, HEIGHT)
        area.connect("draw", self.on_draw)
        win.add(area)
        self.area = area
        win.show_all()

        self.schedule()

    @staticmethod
    def focused_monitor():
        display = Gdk.Display.get_default()
        monitor = None
        seat = display.get_default_seat()
        pointer = seat.get_pointer() if seat else None
        if pointer is not None:
            _, px, py = pointer.get_position()
            monitor = display.get_monitor_at_point(px, py)
        monitor = monitor or display.get_primary_monitor() or display.get_monitor(0)
        return monitor, monitor.get_geometry()

    def on_draw(self, area, cr):
        elapsed = time.monotonic() - self.started
        if elapsed < POP_IN:
            p = ease_out_back(elapsed / POP_IN)
            scale, alpha = 0.78 + 0.22 * p, min(1.0, elapsed / (POP_IN * 0.8))
        elif elapsed > LIFETIME - FADE_OUT:
            scale, alpha = 1.0, max(0.0, (LIFETIME - elapsed) / FADE_OUT)
        else:
            scale, alpha = 1.0, 1.0
        cr.save()
        cr.translate(WIDTH / 2, HEIGHT / 2)
        cr.scale(scale, scale)
        cr.translate(-WIDTH / 2, -HEIGHT / 2)
        cr.set_source_surface(self.card, 0, 0)
        cr.paint_with_alpha(alpha)
        cr.restore()
        return False

    def frame(self):
        if self.closed:
            return False
        self.area.queue_draw()
        self.schedule()
        return False

    def schedule(self):
        """Redraw only while animating: the 5 s hold costs no CPU at all."""
        elapsed = time.monotonic() - self.started
        if elapsed >= LIFETIME:
            self.close()
            return
        if elapsed < POP_IN or elapsed >= LIFETIME - FADE_OUT:
            GLib.timeout_add(33, self.frame)
        else:
            delay = int((LIFETIME - FADE_OUT - elapsed) * 1000) + 20
            GLib.timeout_add(delay, self.frame)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.win.destroy()
        Gtk.main_quit()


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else STATE_DIR / "splash.json"
    try:
        payload = json.loads(source.read_text())
    except (OSError, ValueError):
        return 1
    Splash(payload)
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
