#!/usr/bin/env python3
"""Questline HUD — the pinned card on the desktop.

Reads `~/.local/state/questline/hud.json` (written by `ql`), never runs `ql`
itself. It is a Wayland *layer surface* (GTK3 + libgtk-layer-shell): anchored to
a corner, above normal windows, and it never takes keyboard focus, so it cannot
steal a click from the app you are working in.

Cost: one Gio file monitor on hud.json plus a 15 s timer for the session clock.
No processes per tick, no polling of the system.

    ./hud.py        # or the symlink: ql-hud
"""
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, Gio, GLib, Gtk, GtkLayerShell  # noqa: E402

STATE_DIR = Path(os.environ.get("QL_HOME", "~/.local/state/questline")).expanduser()
HUD_FILE = STATE_DIR / "hud.json"
RUNTIME = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
PID_FILE = Path(RUNTIME) / "questline-hud.pid"
WIDTH = 300
MARGIN_TOP = 44      # clear of waybar
MARGIN_SIDE = 18
REFRESH_SECONDS = 15
POLL_SECONDS = 12

CSS = b"""
window { background-color: transparent; }
.hud {
  background-color: rgba(18, 18, 20, 0.90);
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  padding: 12px 14px;
  color: #e6e6e6;
  font-family: "JetBrainsMono Nerd Font", monospace;
  font-size: 11pt;
}
.headline { font-size: 11pt; font-weight: bold; }
.dim { opacity: 0.55; font-size: 8pt; }
.session { font-size: 9pt; color: #8fd3a6; }
.task { font-size: 9pt; opacity: 0.90; }
.time { font-size: 8pt; color: #8a8f98; }
progressbar trough {
  min-height: 6px; border-radius: 3px;
  background-color: rgba(255, 255, 255, 0.10);
}
progressbar progress {
  min-height: 6px; border-radius: 3px; background-color: #7fb2ff;
}
progressbar.project progress { background-color: #a8d08d; }
progressbar.streak progress  { background-color: #f0a35e; }
"""


def load_hud() -> dict:
    try:
        return json.loads(HUD_FILE.read_text())
    except (OSError, ValueError):
        return {}


class Hud:
    def __init__(self):
        self.data: dict = {}
        self.session_label = None
        self.bars: dict[str, Gtk.ProgressBar] = {}
        self.hidden = False        # what the compositor sees right now
        self.fullscreen = False    # an app is fullscreen on the focused monitor
        self.user_hidden = False   # toggled with SIGUSR1 / SUPER ALT SHIFT H
        self.current_output = ""

        win = Gtk.Window()
        self.win = win
        win.set_decorated(False)
        win.set_resizable(False)
        win.set_skip_taskbar_hint(True)
        win.set_skip_pager_hint(True)
        win.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        win.set_size_request(WIDTH, -1)

        GtkLayerShell.init_for_window(win)
        GtkLayerShell.set_layer(win, GtkLayerShell.Layer.TOP)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(win, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.TOP, MARGIN_TOP)
        GtkLayerShell.set_margin(win, GtkLayerShell.Edge.RIGHT, MARGIN_SIDE)
        GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_exclusive_zone(win, 0)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.get_style_context().add_class("hud")

        self.headline = Gtk.Label(xalign=0)
        self.headline.get_style_context().add_class("headline")
        self.session_label = Gtk.Label(xalign=0)
        self.session_label.get_style_context().add_class("session")
        box.pack_start(self.headline, False, False, 0)
        box.pack_start(self.session_label, False, False, 0)

        for key, caption in (("day", "today"), ("project", "project"), ("streak", "streak")):
            row = Gtk.Box(spacing=8)
            name = Gtk.Label(xalign=0)
            name.set_text(caption)
            name.set_size_request(56, -1)
            name.get_style_context().add_class("dim")
            bar = Gtk.ProgressBar()
            bar.set_hexpand(True)
            bar.set_valign(Gtk.Align.CENTER)
            bar.get_style_context().add_class(key)
            self.bars[key] = bar
            row.pack_start(name, False, False, 0)
            row.pack_start(bar, True, True, 0)
            box.pack_start(row, False, False, 0)

        self.tasks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self.tasks_box.set_margin_top(3)
        box.pack_start(self.tasks_box, False, False, 0)

        self.time_label = Gtk.Label(xalign=0)
        self.time_label.get_style_context().add_class("time")
        box.pack_start(self.time_label, False, False, 0)

        win.add(box)
        win.show_all()
        self.reload()

        self.follow_monitor()
        self.poll_hyprland()
        monitor = Gio.File.new_for_path(str(HUD_FILE)).monitor_file(
            Gio.FileMonitorFlags.NONE, None)
        monitor.connect("changed", lambda *_: self.reload())
        self.monitor = monitor
        GLib.timeout_add_seconds(REFRESH_SECONDS, self.tick)
        GLib.timeout_add_seconds(POLL_SECONDS, self.poll_hyprland)

    # --------------------------------------------------------------- wayland
    # GDK reports the EDID model ("0x323C", "S22A33x"), not the connector name
    # ("eDP-1", "HDMI-A-1"), so monitors are matched by their position instead.
    def gdk_monitor_for(self, hypr_mon: dict):
        display = Gdk.Display.get_default()
        scale = hypr_mon.get("scale") or 1
        want_x, want_y = hypr_mon["x"] / scale, hypr_mon["y"] / scale
        for i in range(display.get_n_monitors()):
            mon = display.get_monitor(i)
            g = mon.get_geometry()
            if abs(g.x - want_x) <= 2 and abs(g.y - want_y) <= 2:
                return mon
        return None

    def hypr_monitors(self) -> list:
        try:
            import subprocess
            out = subprocess.run(["hyprctl", "-j", "monitors"], capture_output=True,
                                 text=True, timeout=5).stdout
            return json.loads(out)
        except Exception:
            return []

    def follow_monitor(self, name: str = ""):
        """Anchor to the monitor that has the focus right now."""
        monitors = self.hypr_monitors()
        focused = next((m for m in monitors
                        if (name and m.get("name") == name) or (not name and m.get("focused"))),
                       None)
        if not focused:
            return False
        mon = self.gdk_monitor_for(focused)
        if mon is None:
            return False
        self.current_output = focused["name"]
        # gtk-layer-shell fixes the output when the surface is realised, so the
        # window is re-mapped to move it to another screen.
        self.win.hide()
        GtkLayerShell.set_monitor(self.win, mon)
        self.apply_visibility(force=True)   # the surface was just destroyed
        return False

    # ------------------------------------------------------------------ hypr
    # This build streams nothing on Hyprland's event socket (verified with
    # socat: zero bytes even for workspace switches), so the two facts the card
    # needs are polled instead. Two `hyprctl` calls every 12 s is ~0.1% of a
    # core, and only while the HUD is running.
    def poll_hyprland(self):
        import subprocess
        try:
            active = json.loads(subprocess.run(
                ["hyprctl", "-j", "activewindow"], capture_output=True,
                text=True, timeout=5).stdout)
        except Exception:
            active = {}
        self.fullscreen = bool(active.get("fullscreen", 0))
        self.apply_visibility()
        monitors = self.hypr_monitors()
        focused = next((m.get("name") for m in monitors if m.get("focused")), "")
        if focused and focused != self.current_output:
            self.follow_monitor(focused)
        return True

    def apply_visibility(self, force: bool = False):
        """Hidden while an app is fullscreen, or when the user asked for it."""
        hidden = self.fullscreen or self.user_hidden
        if hidden == self.hidden and not force:
            return
        self.hidden = hidden
        if hidden:
            self.win.hide()
        else:
            self.win.show_all()

    def toggle(self):
        """SUPER+ALT+SHIFT+H. Overrides the fullscreen rule while it is off."""
        self.user_hidden = not self.user_hidden
        self.apply_visibility()
        return True

    # ---------------------------------------------------------------- render
    def reload(self):
        self.data = load_hud()
        d = self.data
        if not d:
            self.headline.set_text("Questline")
            self.session_label.set_text("no data · run ql rebuild")
            return
        role = d.get("role") or "no role"
        gifts = d.get("gifts", [])
        badge = f" · ✦{len(gifts)}" if gifts else ""
        self.headline.set_text(
            f"{role} · {d.get('fragments', 0)} FRG · {d.get('streak', 0)}d{badge}")
        self.headline.set_tooltip_text(
            "gifts: " + ", ".join(gifts) if gifts else "no gifts claimed")
        self.session_label.set_text(self.session_text())

        self.bars["day"].set_fraction(
            min(1.0, d.get("fragments_today", 0) / max(1, d.get("day_goal", 60))))
        self.bars["streak"].set_fraction(
            min(1.0, d.get("streak", 0) / max(1, d.get("streak_goal", 7))))

        projects = [p for p in d.get("projects", [])
                    if p.get("name") != "inbox" or p.get("done")]
        if projects:
            p = max(projects, key=lambda x: (x["done"], x["total"]))
            self.bars["project"].set_fraction(p["done"] / max(1, p["total"]))
            self.bars["project"].set_tooltip_text(
                f"{p['name']} {p['done']}/{p['total']} tasks")
        else:
            self.bars["project"].set_fraction(0)
            self.bars["project"].set_tooltip_text("no project")

        for child in self.tasks_box.get_children():
            self.tasks_box.remove(child)
        for t in d.get("tasks_open", []):
            label = Gtk.Label(xalign=0)
            label.set_ellipsize(3)  # Pango.EllipsizeMode.END
            label.set_text(f"· {t['text']}")
            label.set_tooltip_text(f"{t['text']}  ({t.get('project', '')})")
            label.get_style_context().add_class("task")
            self.tasks_box.pack_start(label, False, False, 0)
        rest = d.get("open_count", 0) - len(d.get("tasks_open", []))
        if rest > 0:
            more = Gtk.Label(xalign=0)
            more.set_text(f"+{rest} more")
            more.get_style_context().add_class("dim")
            self.tasks_box.pack_start(more, False, False, 0)
        self.time_label.set_text(self.clock_text())
        self.tasks_box.show_all()

    def session_text(self) -> str:
        s = self.data.get("session")
        if not s:
            return "○ no session"
        return f"● {s.get('mode')} · {self.session_minutes(s)} min"

    def session_minutes(self, session: dict) -> int:
        started = session.get("started") or ""
        try:
            t0 = datetime.strptime(started, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            return int((datetime.now(timezone.utc) - t0).total_seconds() // 60)
        except ValueError:
            return 0

    def clock_text(self) -> str:
        d = self.data
        return (f"{d.get('fragments_today', 0)}/{d.get('day_goal', 60)} today"
                f" · {d.get('open_count', 0)} open")

    def quit(self):
        Gtk.main_quit()
        return False

    def tick(self):
        if self.data.get("session"):
            self.session_label.set_text(self.session_text())
        self.time_label.set_text(self.clock_text())
        return True


def main() -> int:
    if not HUD_FILE.exists():
        print(f"missing {HUD_FILE}; run `ql rebuild` first", file=sys.stderr)
    app = Hud()
    try:
        PID_FILE.write_text(str(os.getpid()))
    except OSError:
        pass
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, app.toggle)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, app.quit)
    Gtk.main()
    try:
        PID_FILE.unlink()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
