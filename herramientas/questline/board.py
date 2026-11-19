#!/usr/bin/env python3
"""Questline board — a small GTK4 window over `ql`.

Reads the vault through `ql tasks --json`, writes through `ql done/reopen`.
No database, no service, no polling: the list refreshes when the window gains
focus or when you press the refresh button.

    ./board.py            # or the symlink: ql-board
"""
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

QL = os.environ.get("QL_BIN", str(Path.home() / ".local/bin/ql"))

CSS = """
.column-title { font-weight: 700; font-size: 0.9em; opacity: 0.7; }
.card { padding: 8px 10px; border-radius: 10px; }
.card:hover { background-color: alpha(currentColor, 0.06); }
.task-open { font-size: 1.0em; }
.task-done { font-size: 1.0em; opacity: 0.55; }
.meta { font-size: 0.78em; opacity: 0.55; }
.stat { font-weight: 700; font-size: 0.9em; }
"""


def ql(*args: str):
    try:
        out = subprocess.run([QL, *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def load():
    tasks = json.loads(ql("tasks", "--json") or "[]")
    status = json.loads(ql("status", "--json") or "{}")
    return tasks, status


class Board(Adw.Application):
    def __init__(self):
        super().__init__(application_id="dev.questline.Board")
        self.tasks: list = []
        self.status: dict = {}
        self.project = ""
        self.projects: list = []

    # ---------------------------------------------------------------- ui
    def do_activate(self):
        win = Adw.ApplicationWindow(application=self, title="Questline")
        win.set_default_size(1040, 720)
        win.add_css_class("qtl")
        self.win = win

        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(
            win.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        header = Adw.HeaderBar()
        self.subtitle = Gtk.Label(label="")
        self.subtitle.add_css_class("meta")
        header.set_title_widget(Gtk.Label(label="Questline"))
        header.pack_start(self.subtitle)

        refresh = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh.set_tooltip_text("Releer el vault")
        refresh.connect("clicked", lambda *_: self.reload())
        header.pack_end(refresh)

        self.stats = Gtk.Label(label="")
        self.stats.add_css_class("stat")
        self.stats.set_margin_start(14)
        self.stats.set_margin_end(8)

        self.filter = Gtk.DropDown.new_from_strings(["All projects"])
        self.filter.connect("notify::selected", self.on_filter)

        bar = Gtk.Box(spacing=10)
        bar.set_margin_top(8)
        bar.set_margin_bottom(4)
        bar.set_margin_start(14)
        bar.set_margin_end(14)
        bar.append(self.stats)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        bar.append(spacer)
        bar.append(self.filter)

        self.open_box = self.column("Open")
        self.done_box = self.column("Done")

        cols = Gtk.Box(spacing=12, homogeneous=True)
        cols.set_margin_start(14)
        cols.set_margin_end(14)
        cols.set_margin_bottom(14)
        cols.set_vexpand(True)
        cols.append(self.scroller(self.open_box))
        cols.append(self.scroller(self.done_box))

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        body.append(bar)
        body.append(cols)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(body)
        win.set_content(toolbar)

        esc = Gtk.EventControllerKey()
        esc.connect("key-pressed", self.on_key)
        win.add_controller(esc)

        focus = Gtk.EventControllerFocus()
        focus.connect("enter", lambda *_: self.reload())
        win.add_controller(focus)

        self.reload()
        win.present()

    def column(self, title: str) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        label = Gtk.Label(label=title, xalign=0)
        label.add_css_class("column-title")
        label.set_margin_start(4)
        box.append(label)
        return box

    def scroller(self, child) -> Gtk.ScrolledWindow:
        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sc.set_child(child)
        sc.set_vexpand(True)
        sc.add_css_class("card")
        return sc

    # -------------------------------------------------------------- data
    def reload(self):
        self.tasks, self.status = load()
        self.projects = sorted({t["project"] for t in self.tasks if t["project"]})
        model = self.filter.get_model()
        current = self.filter.get_selected()
        wanted = ["All projects"] + self.projects
        if list(model) != wanted:
            self.filter.set_model(Gtk.StringList.new(wanted))
            self.filter.set_selected(min(current, len(wanted) - 1))
        self.render()

    def render(self):
        for box in (self.open_box, self.done_box):
            child = box.get_first_child()
            while child is not None:
                nxt = child.get_next_sibling()
                if isinstance(child, Gtk.Button):
                    box.remove(child)
                child = nxt

        s = self.status
        frag = s.get("fragments", 0)
        role = s.get("role") or "no role"
        self.stats.set_label(f"{frag} FRG · {s.get('streak_days', 0)}d · {role}")
        self.subtitle.set_label(f"{len(self.tasks)} tasks · {len(self.projects)} projects")

        shown = [t for t in self.tasks if not self.project or t["project"] == self.project]
        opens = [t for t in shown if not t["done"]]
        dones = [t for t in shown if t["done"]]
        for box, items in ((self.open_box, opens), (self.done_box, dones)):
            if not items:
                empty = Gtk.Label(label="nothing here", xalign=0)
                empty.add_css_class("meta")
                empty.set_margin_start(4)
                box.append(empty)
            for t in items:
                box.append(self.card(t))

    def card(self, task: dict) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add_css_class("flat")
        btn.add_css_class("card")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(xalign=0, wrap=True)
        title.set_markup(GLib.markup_escape_text(task["text"]))
        title.add_css_class("task-done" if task["done"] else "task-open")
        meta = Gtk.Label(xalign=0)
        meta.set_text(f"{task['project'] or 'inbox'} · {task['file']}:{task['line']}")
        meta.add_css_class("meta")
        box.append(title)
        box.append(meta)
        btn.set_child(box)
        btn.set_tooltip_text("Cerrar" if not task["done"] else "Reabrir")
        btn.connect("clicked", lambda *_: self.toggle(task))
        return btn

    # ------------------------------------------------------------ actions
    def toggle(self, task: dict):
        verb = "reopen" if task["done"] else "done"

        def work():
            ql(verb, task["id"], *(["--notify"] if verb == "done" else []))
            GLib.idle_add(self.reload)

        threading.Thread(target=work, daemon=True).start()

    def on_filter(self, *_):
        idx = self.filter.get_selected()
        self.project = "" if idx == 0 else self.projects[idx - 1]
        self.render()

    def on_key(self, _c, keyval, _code, _mods):
        if keyval == 65307:  # Escape
            self.win.close()
            return True
        if keyval in (110, 114):  # n, r
            self.reload()
            return True
        return False


def main() -> int:
    if not Path(QL).exists():
        print(f"no encuentro {QL}", file=sys.stderr)
        return 1
    app = Board()
    return app.run([sys.argv[0]])


if __name__ == "__main__":
    sys.exit(main())
