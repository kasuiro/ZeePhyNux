#!/usr/bin/env python3
"""Smoke tests for ql.py. No dependencies: python3 tests/smoke.py

Every test runs against a throwaway vault and state dir (QL_VAULT / QL_HOME),
so the real ~/Documentos/Vault is never touched.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

QL = Path(__file__).resolve().parent.parent / "ql.py"
FAILS = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global FAILS
    print(f"{'ok  ' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        FAILS += 1


def write_png(path: Path, rows: list) -> None:
    """Minimal RGBA PNG writer (stdlib only) for the emblem checks."""
    import struct
    import zlib
    height, width = len(rows), len(rows[0])
    raw = b"".join(b"\x00" + b"".join(bytes(px) for px in row) for row in rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b""))


class Env:
    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.vault = root / "Vault"
        self.home = root / "state"
        self.notify = root / "notify.log"
        (self.vault / "Questline" / "events").mkdir(parents=True)
        self.env = {**os.environ, "QL_VAULT": str(self.vault), "QL_HOME": str(self.home),
                    "QL_NOTIFY_LOG": str(self.notify), "QL_NO_SPLASH": "1",
                    "QL_EMBLEM_OUT": str(root / "emblems-out")}

    def run(self, script: str, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(QL.with_name(script)), *args],
                              env=self.env, capture_output=True, text=True)

    def ql(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(QL), *args], env=self.env,
                              capture_output=True, text=True)

    def ok(self, *args: str) -> subprocess.CompletedProcess:
        """Like ql(), but a non-zero exit counts as a failure."""
        r = self.ql(*args)
        if r.returncode != 0:
            check(f"`ql {' '.join(args[:2])}` exits 0", False, r.stderr.strip()[-300:])
        return r

    def state(self) -> dict:
        self.ql("rebuild")
        return json.loads(self.ql("status", "--json").stdout)

    def local(self, day_offset: int = 0, hour: int = 9, minute: int = 0) -> str:
        """UTC timestamp string for a local wall-clock time, N days ago."""
        base = datetime.now().astimezone().replace(hour=hour, minute=minute, second=0, microsecond=0)
        return (base - timedelta(days=day_offset)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    e = Env()

    # 1. identity
    dev = e.ql("device").stdout.strip()
    check("device id format", len(dev.split("-")[-1]) == 6 and dev == e.ql("device").stdout.strip(), dev)

    # 2. determinism
    t0, t1 = e.local(0, 9), e.local(0, 10)
    e.ql("mode", "start", "devmode", "--ts", t0)
    e.ql("mode", "stop", "devmode", "--ts", t1)
    s1 = e.state()
    s2 = e.state()
    check("rebuild is deterministic", s1 == s2)
    check("60 min devmode = 6 fragments", s1["breakdown"]["modes"] == 6, str(s1["breakdown"]))

    # 3. dedupe by event_id
    log = next((e.vault / "Questline" / "events").glob("*.tsv"))
    line = log.read_text().splitlines()[0]
    log.write_text(log.read_text() + line + "\n")
    modes = [ev for ev in json.loads(e.ql("events", "--json").stdout)
             if ev["type"].startswith("mode.")]
    check("duplicate line is ignored", len(modes) == 2, str(len(modes)))

    # 4. last-writer-wins on tasks
    e.ql("done", "ql-aaaa", "--project", "hyprland", "--ts", e.local(0, 11))
    check("task done = +10", e.state()["breakdown"]["tasks"] == 10)
    e.ql("reopen", "ql-aaaa", "--ts", e.local(0, 12))
    check("reopen undoes the points", e.state()["breakdown"]["tasks"] == 0)
    e.ql("done", "ql-aaaa", "--ts", e.local(0, 13))
    st = e.state()
    check("task done again = +10, counted once", st["tasks_done"] == 1 and st["breakdown"]["tasks"] == 10)

    # 5. caps
    e2 = Env()
    e2.ql("mode", "start", "gamedevmode", "--ts", e2.local(0, 0))
    e2.ql("mode", "stop", "gamedevmode", "--ts", e2.local(0, 10))  # 10 h
    st = e2.state()
    minutes = st["modes"][st["today"]]["gamedevmode"]["minutes"]
    check("single session capped at 240 min", minutes == 240, str(minutes))
    check("4 h session = 24 fragments", st["modes"][st["today"]]["gamedevmode"]["fragments"] == 24,
          str(st["modes"]))
    # second 4 h session the same day: 48 raw -> 40 cap
    e2.ql("mode", "start", "gamedevmode", "--ts", e2.local(0, 11))
    e2.ql("mode", "stop", "gamedevmode", "--ts", e2.local(0, 21))
    st = e2.state()
    check("daily cap per mode = 40", st["modes"][st["today"]]["gamedevmode"]["fragments"] == 40,
          str(st["modes"]))

    # 6. role bonus applies to the affinity mode only
    e3 = Env()
    e3.ql("role", "artisan", "--ts", e3.local(1, 8))
    e3.ql("mode", "start", "devmode", "--ts", e3.local(0, 9))
    e3.ql("mode", "stop", "devmode", "--ts", e3.local(0, 10))
    e3.ql("mode", "start", "readmode", "--ts", e3.local(0, 11))
    e3.ql("mode", "stop", "readmode", "--ts", e3.local(0, 12))
    modes = e3.state()["modes"][e3.state()["today"]]
    check("artisan boosts devmode (6 -> 8)", modes["devmode"]["fragments"] == 8, str(modes))
    check("artisan does not boost readmode", modes["readmode"]["fragments"] == 6, str(modes))

    # 7. streak
    e4 = Env()
    for d in (1, 0):
        e4.ql("mode", "start", "readmode", "--ts", e4.local(d, 9))
        e4.ql("mode", "stop", "readmode", "--ts", e4.local(d, 10, 30))
    st = e4.state()
    check("streak counts 2 consecutive days", st["streak_days"] == 2, str(st["streak_days"]))
    check("streak bonus = 2 * 5", st["breakdown"]["streak"] == 10, str(st["breakdown"]))

    # 8. two devices merge
    e5 = Env()
    other = "phone-abc123"
    e5.ql("mode", "start", "writemode", "--ts", e5.local(0, 9))
    e5.ql("mode", "stop", "writemode", "--ts", e5.local(0, 10))
    line = (e5.vault / "Questline" / "events" / f"{e5.ql('device').stdout.strip()}.tsv").read_text()
    rows = []
    for i, row in enumerate(line.splitlines()):
        cols = row.split("\t")
        cols[0] = f"{i:032x}"
        cols[3] = other
        rows.append("\t".join(cols))
    (e5.vault / "Questline" / "events" / f"{other}.tsv").write_text("\n".join(rows) + "\n")
    check("two devices' logs merge without double counting", e5.state()["breakdown"]["modes"] == 6,
          str(e5.state()["breakdown"]))

    # 9. no open session earns points
    e6 = Env()
    e6.ql("mode", "start", "3dmode", "--ts", e6.local(0, 9))
    st = e6.state()
    check("open session earns nothing yet", st["breakdown"]["modes"] == 0 and st["open_sessions"] == ["3dmode"],
          str(st["open_sessions"]))

    # 10. unknown event type refused
    r = e6.ql("log", "bogus", "x")
    check("unknown event type is rejected", r.returncode != 0)

    # 11. vault scan finds tasks (F9.2)
    e7 = Env()
    proj = e7.vault / "Projects"
    proj.mkdir(parents=True)
    note = proj / "galeria.md"
    note.write_text("# Galeria\n\n"
                    "- [ ] Subir los 3 stickers #project/gallery\n"
                    "* [x] Revisar el tablero #project/questline\n"
                    "- [ ] sin proyecto\n"
                    "texto normal\n")
    before = note.read_text()
    tasks = json.loads(e7.ql("scan", "--json").stdout)
    check("scan finds 3 tasks", len(tasks) == 3, str(len(tasks)))
    check("project tag parsed", {t["project"] for t in tasks} == {"gallery", "questline", ""},
          str([t["project"] for t in tasks]))
    check("checkbox state parsed", sum(t["done"] for t in tasks) == 1, str(tasks))
    check("plain scan writes nothing", note.read_text() == before)

    # 12. block ids are written once
    e7.ql("scan", "--write-ids")
    text1 = note.read_text()
    check("block ids appended", text1.count("^ql-") == 3, text1)
    e7.ql("scan", "--write-ids")
    check("second --write-ids writes nothing", note.read_text() == text1)
    check("note backed up before ids",
          (e7.vault / "Questline" / "id-backups" / "Projects__galeria.md").is_file())

    # 13. sync emits only transitions
    e8 = Env()
    p = e8.vault / "Inbox.md"
    p.write_text("- [ ] tarea uno #project/x\n")
    r = e8.ql("sync")
    check("first sync is only a baseline", "0 new events" in r.stdout, r.stdout)
    p.write_text("- [x] tarea uno #project/x\n")
    r = e8.ql("sync")
    check("ticking a box emits one event", "1 new events" in r.stdout, r.stdout)
    check("closed task = 10 fragments", e8.state()["breakdown"]["tasks"] == 10)
    r = e8.ql("sync")
    check("second sync emits nothing", "0 new events" in r.stdout, r.stdout)

    # 14. unticking reopens
    p.write_text("- [ ] tarea uno #project/x\n")
    r = e8.ql("sync")
    check("unticking emits task.reopen", "1 new events" in r.stdout, r.stdout)
    check("reopen returns the fragments", e8.state()["breakdown"]["tasks"] == 0)

    # 15. a moved line keeps its id
    e9 = Env()
    fa, fb = e9.vault / "a.md", e9.vault / "b.md"
    fa.write_text("- [ ] mover esto #project/m\n")
    e9.ql("scan", "--write-ids")
    tid = json.loads(e9.ql("scan", "--json").stdout)[0]["id"]
    line = fa.read_text().strip() + "\n"
    fa.write_text("")
    fb.write_text(line)
    moved = json.loads(e9.ql("scan", "--json").stdout)
    check("moved task keeps its id", [t["id"] for t in moved] == [tid], str(moved))

    # 16. exclusions
    e10 = Env()
    (e10.vault / ".obsidian").mkdir()
    (e10.vault / ".obsidian" / "x.md").write_text("- [ ] oculta\n")
    (e10.vault / "big.md").write_text("- [ ] grande\n" + "x" * (300 * 1024))
    (e10.vault / "Questline" / "notes.md").write_text("- [ ] dentro de Questline\n")
    outside = e10.tmp.name and Path(e10.tmp.name) / "outside.md"
    outside.write_text("- [ ] fuera del vault\n")
    os.symlink(outside, e10.vault / "link.md")
    skipped = json.loads(e10.ql("scan", "--json").stdout)
    check(".obsidian, big notes, Questline/ and symlinks are skipped", skipped == [], str(skipped))

    # 17. ql done ticks the vault, ql reopen unticks it, and sync stays quiet
    e11 = Env()
    f = e11.vault / "n.md"
    f.write_text("- [ ] tildar desde el tablero #project/b ^ql-abc123\n")
    r = e11.ok("done", "ql-abc123")
    check("done reports the note", "in n.md" in r.stdout, r.stdout)
    check("done ticks the checkbox", "- [x] tildar desde el tablero" in f.read_text(), f.read_text())
    check("done awards 10 fragments", e11.state()["breakdown"]["tasks"] == 10)
    e11.ql("sync")
    check("sync after done does not double count", e11.state()["breakdown"]["tasks"] == 10)
    r = e11.ok("done", "ql-abc123")
    check("done twice changes nothing", "already done" in r.stdout and
          e11.state()["breakdown"]["tasks"] == 10, r.stdout)
    check("note is backed up before ticking",
          (e11.vault / "Questline/id-backups/n.md").is_file())
    e11.ok("reopen", "ql-abc123")
    check("reopen unticks the checkbox", "- [ ] tildar desde el tablero" in f.read_text(), f.read_text())
    check("reopen returns the fragments", e11.state()["breakdown"]["tasks"] == 0)

    # 18. an id that is not in the vault still records the event
    r = e11.ql("done", "ql-ffffff")
    check("unknown id is recorded but says so", "not in this vault" in r.stdout, r.stdout)

    # 19. hud.json is what the pinned card reads
    e12 = Env()
    (e12.vault / "Inbox.md").write_text(
        "- [ ] una #project/alfa ^ql-aaaaaa\n"
        "- [x] dos #project/alfa ^ql-bbbbbb\n"
        "- [ ] sin tag ^ql-cccccc\n")
    e12.ok("scan")
    e12.ok("rebuild")
    hud = json.loads((e12.home / "hud.json").read_text())
    check("hud has a day goal", hud["day_goal"] == 60, str(hud.get("day_goal")))
    check("hud counts open tasks", hud["open_count"] == 2, str(hud["open_count"]))
    check("hud strips the project tag from the text",
          [t["text"] for t in hud["tasks_open"]] == ["una", "sin tag"], str(hud["tasks_open"]))
    check("hud groups projects", {(p["name"], p["done"], p["total"]) for p in hud["projects"]}
          == {("alfa", 1, 2), ("inbox", 0, 1)}, str(hud["projects"]))
    check("hud has no session when none is open", hud["session"] is None, str(hud["session"]))

    # 20. an open mode shows up in the card with its start time
    e12.ok("mode", "start", "readmode", "--ts", e12.local(0, 9))
    hud = json.loads((e12.home / "hud.json").read_text())
    check("hud reports the open session",
          hud["session"]["mode"] == "readmode" and hud["session"]["started"],
          str(hud.get("session")))

    # 21. closing a task notifies once; closes within 5 s share one bubble
    e13 = Env()
    note = e13.vault / "n.md"
    note.write_text("- [ ] alfa #project/alfa ^ql-aaaaaa\n"
                    "- [ ] beta #project/beta ^ql-bbbbbb\n"
                    "- [ ] gamma #project/gamma ^ql-cccccc\n")
    e13.ok("done", "ql-aaaaaa")
    check("done is silent without --notify", not e13.notify.exists())
    e13.ok("done", "ql-aaaaaa", "--notify")
    check("an unchanged task does not notify", not e13.notify.exists())
    e13.ok("reopen", "ql-aaaaaa", "--notify")
    check("reopen never notifies", not e13.notify.exists())

    e13.ok("done", "ql-aaaaaa", "--notify")
    first = json.loads(e13.notify.read_text().splitlines()[0])
    check("notify title carries the reward", "+10 FRG" in first["title"], str(first))
    check("notify body names the task and the day goal",
          "alfa" in first["body"] and "FRG today" in first["body"], str(first))
    e13.ok("done", "ql-bbbbbb", "--notify")
    notes = [json.loads(line) for line in e13.notify.read_text().splitlines()]
    check("a second close within 5 s replaces the bubble", len(notes) == 2, str(notes))
    check("the group bubble counts both tasks",
          notes[1]["title"].startswith("2 tasks closed") and "+20 FRG" in notes[1]["title"],
          notes[1]["title"])
    check("the group body lists both tasks",
          "alfa" in notes[1]["body"] and "beta" in notes[1]["body"], notes[1]["body"])
    group = json.loads((e13.home / "notify.json").read_text())
    check("the group file keeps both tasks", len(group["tasks"]) == 2, str(group))

    old = datetime.now(timezone.utc) - timedelta(seconds=60)
    group["started"] = old.strftime("%Y-%m-%dT%H:%M:%SZ")
    (e13.home / "notify.json").write_text(json.dumps(group))
    e13.ok("done", "ql-cccccc", "--notify")
    late = [json.loads(line) for line in e13.notify.read_text().splitlines()][-1]
    check("a close after the window starts a new group",
          late["title"].startswith("+10 FRG"), late["title"])
    check("the new group holds one task",
          len(json.loads((e13.home / "notify.json").read_text())["tasks"]) == 1)

    # 22. five closes of one project inside a mode session -> chain milestone
    e14 = Env()
    rows = "".join(f"- [ ] t{i} #project/gallery ^ql-{i:06x}\n" for i in range(1, 7))
    (e14.vault / "g.md").write_text(rows)
    e14.ok("mode", "start", "devmode", "--ts", e14.local(0, 9))
    for i in range(1, 6):
        e14.ok("done", f"ql-{i:06x}", "--ts", e14.local(0, 10, i))
    found = json.loads(e14.ql("milestones", "--json").stdout)
    check("five closes in one session raise one chain",
          [m["key"].split(":")[0] for m in found] == ["chain"], str(found))
    check("the chain keys on the project and the session",
          "gallery" in found[0]["key"] and e14.local(0, 9) in found[0]["key"], str(found))
    splash = json.loads((e14.home / "splash.json").read_text())
    check("the splash carries the zoso medal",
          splash["glyph"] == "zoso" and splash["title"].startswith("5 in a row"), str(splash))
    e14.ok("done", "ql-000006", "--ts", e14.local(0, 10, 6))
    check("a sixth close does not repeat the milestone",
          len(json.loads(e14.ql("milestones", "--json").stdout)) == 1)

    # 23. a small project finishing is not a milestone; a ten-task one is
    e15 = Env()
    (e15.vault / "small.md").write_text(
        "".join(f"- [x] s{i} #project/small ^ql-{i:06x}\n" for i in range(1, 5)) +
        "- [ ] s5 #project/small ^ql-000005\n")
    e15.ok("done", "ql-000005")
    check("a five-task project does not celebrate 100%",
          json.loads(e15.ql("milestones", "--json").stdout) == [])
    e16 = Env()
    (e16.vault / "big.md").write_text(
        "".join(f"- [x] b{i} #project/big ^ql-{i:06x}\n" for i in range(1, 10)) +
        "- [ ] b10 #project/big ^ql-000010\n")
    e16.ok("done", "ql-000010")
    done_ms = json.loads(e16.ql("milestones", "--json").stdout)
    check("a ten-task project finishing is a milestone",
          [m["key"] for m in done_ms] == ["project:big"], str(done_ms))
    splash = json.loads((e16.home / "splash.json").read_text())
    check("the project splash is big and uses the icarus medal",
          splash["kind"] == "big" and splash["glyph"] == "icarus", str(splash))

    # 24. seven qualified days: streak and perfect week
    e17 = Env()
    for back in range(6, -1, -1):
        e17.ok("mode", "start", "readmode", "--ts", e17.local(back, 9))
        e17.ok("mode", "stop", "readmode", "--ts", e17.local(back, 10, 20))
    keys = [m["key"].split(":")[0] for m in json.loads(e17.ql("milestones", "--json").stdout)]
    check("seven qualified days raise the streak", "streak" in keys, str(keys))
    check("seven qualified days raise the perfect week", "week" in keys, str(keys))
    splash = json.loads((e17.home / "splash.json").read_text())
    check("the week splash wins over the smaller streak",
          splash["title"] == "Perfect week" and splash["glyph"] == "hermit", str(splash))
    before = len(json.loads(e17.ql("milestones", "--json").stdout))
    e17.ok("mode", "start", "readmode", "--ts", e17.local(0, 11))
    e17.ok("mode", "stop", "readmode", "--ts", e17.local(0, 11, 40))
    check("an extra session on the same day adds no milestone",
          len(json.loads(e17.ql("milestones", "--json").stdout)) == before)

    # 25. emblem pipeline: prompt quota, colour validation, install
    e18 = Env()
    out = Path(e18.env["QL_EMBLEM_OUT"])
    out.mkdir(parents=True)
    first = e18.run("emblems.py", "prompt", "gallery")
    check("prompt prints the two-colour brief",
          first.returncode == 0 and "#E0B45C" in first.stdout, first.stderr)
    check("prompt names the project",
          "Subject: gallery." in first.stdout, first.stdout[:200])
    second = e18.run("emblems.py", "prompt", "gallery")
    check("one generation per project per day",
          second.returncode == 1 and "already generated today" in second.stdout,
          second.stdout)
    forced = e18.run("emblems.py", "prompt", "gallery", "--force")
    check("--force overrides the daily quota", forced.returncode == 0, forced.stderr)

    ink, gold, red = (18, 16, 14, 255), (224, 180, 92, 255), (200, 40, 40, 255)
    clear = (0, 0, 0, 0)
    two = [[clear if min(x, y) < 8 or max(x, y) >= 120 else ink
            for x in range(128)] for y in range(128)]
    two[40][64] = gold
    write_png(out / "gallery-1.png", two)
    r = e18.run("emblems.py", "pick", "gallery", "1")
    installed = e18.vault / "Questline" / "emblems" / "gallery.png"
    check("a two-colour medallion installs", r.returncode == 0 and installed.is_file(), r.stderr)
    listed = e18.run("emblems.py", "status")
    check("status lists the emblem", "yes" in listed.stdout and "gallery" in listed.stdout,
          listed.stdout)

    three = [[clear if min(x, y) < 8 else (red if x == 64 else (gold if x == 32 else ink))
              for x in range(128)] for y in range(128)]
    write_png(out / "gallery-2.png", three)
    r = e18.run("emblems.py", "pick", "gallery", "2")
    check("anti-aliasing or a third colour is rejected",
          r.returncode == 1 and "opaque colours" in r.stderr, r.stderr)
    r = e18.run("emblems.py", "pick", "gallery", "9")
    check("a missing candidate is reported", r.returncode == 2, r.stderr)

    # 26. the free local renderer: three deterministic candidates, no model
    e19 = Env()
    out19 = Path(e19.env["QL_EMBLEM_OUT"])
    out19.mkdir(parents=True)
    drawn = e19.run("emblems.py", "draw", "hyprland")
    files = sorted(out19.glob("hyprland-*.png"))
    check("draw renders three candidates", drawn.returncode == 0 and len(files) == 3,
          drawn.stderr)
    picked = e19.run("emblems.py", "pick", "hyprland", "1")
    check("a drawn candidate passes the validator",
          picked.returncode == 0 and "2 colours" in picked.stdout, picked.stderr)
    again = e19.run("emblems.py", "draw", "hyprland")
    check("redrawing a candidate needs --force", again.returncode == 1, again.stderr)

    # 27. sprint window: commit, close, carry over
    e20 = Env()
    (e20.vault / "s.md").write_text(
        "- [ ] a1 #project/alfa ^ql-0000a1\n"
        "- [ ] a2 #project/alfa ^ql-0000a2\n"
        "- [x] a3 #project/alfa ^ql-0000a3\n"
        "- [ ] b1 #project/beta ^ql-0000b1\n")
    e20.ok("scan")
    e20.ok("sprint", "start", "--projects", "alfa", "--start", "2026-01-05")
    st = json.loads(e20.ql("sprint", "status", "--json").stdout)
    check("sprint commits the open tasks of the chosen project",
          st["sprint"]["committed"] == ["ql-0000a1", "ql-0000a2"], str(st["sprint"]))
    check("sprint id comes from the ISO week", st["sprint"]["id"] == "2026-W02",
          st["sprint"]["id"])
    e20.ok("done", "ql-0000a1")
    e20.ok("sprint", "close")
    closed = json.loads((e20.vault / "Questline" / "sprint.json").read_text())
    check("closing carries the unfinished tasks", closed["carried"] == ["ql-0000a2"],
          str(closed))
    e20.ok("sprint", "start", "--projects", "beta")
    st = json.loads(e20.ql("sprint", "status", "--json").stdout)
    check("a new sprint inherits what was carried",
          st["sprint"]["carried"] == ["ql-0000a2"] and "ql-0000b1" in st["sprint"]["committed"],
          str(st["sprint"]))

    # 28. weekly review
    e21 = Env()
    (e21.vault / "r.md").write_text("- [ ] r1 #project/r ^ql-0000c1\n")
    e21.ok("mode", "start", "readmode", "--ts", e21.local(0, 9))
    e21.ok("mode", "stop", "readmode", "--ts", e21.local(0, 9, 50))
    e21.ok("done", "ql-0000c1")
    table = e21.ok("review").stdout
    check("review prints a table and an experiment", "total" in table and "experiment" in table,
          table)
    rev = json.loads(e21.ql("review", "--json").stdout)
    check("review counts the closed task", sum(r["tasks"] for r in rev["days"]) == 1,
          str(rev["days"]))
    check("review suggests starting a sprint", "start a sprint" in rev["suggestion"],
          rev["suggestion"])

    # 29. kaizen record with a before/after metric
    e22 = Env()
    started = e22.ok("kaizen", "start", "fewer open tasks", "--metric", "open", "--baseline", "12")
    kid = started.stdout.split()[0]
    e22.ok("kaizen", "end", kid, "--value", "9")
    rows = json.loads(e22.ql("kaizen", "list", "--json").stdout)
    check("kaizen keeps the baseline and the result",
          rows[0]["baseline"] == "12" and rows[0]["value"] == "9", str(rows))
    check("kaizen end rejects an unknown id",
          e22.ql("kaizen", "end", "kz-nope", "--value", "1").returncode == 2)

    # 30. the daily nudge: one per day, only with an open sprint
    e23 = Env()
    (e23.vault / "n.md").write_text("- [ ] n1 #project/n ^ql-0000d1\n")
    e23.ok("scan")
    e23.ok("mode", "start", "readmode")
    check("no nudge without a sprint",
          not [e for e in json.loads(e23.ql("events", "--json").stdout) if e["type"] == "nudge"])
    e23.ok("sprint", "start", "--projects", "n")
    e23.ok("mode", "start", "devmode")
    nudges = [e for e in json.loads(e23.ql("events", "--json").stdout) if e["type"] == "nudge"]
    check("the nudge fires once per day", len(nudges) == 1, str(nudges))
    notes = [json.loads(line) for line in e23.notify.read_text().splitlines()]
    check("the nudge is a sprint notification",
          len(notes) == 1 and "Sprint" in notes[0]["title"], str(notes))

    # 31. stamp catalog, one batch notification, and the claim flow
    sys.path.insert(0, str(QL.parent))
    import stamps as catalog
    check("the catalog holds 24 stamps in 3 families",
          len(catalog.STAMPS) == 24 and len(catalog.FAMILIES) == 3
          and all(sum(1 for s in catalog.STAMPS if s[2] == f) == 8
                  for f in catalog.FAMILIES))

    e24 = Env()
    for i in range(100):
        e24.ql("log", "task.done", f"t{i:03d}")
    e24.ok("mode", "start", "devmode", "--ts", e24.local(0, 8))
    e24.ok("mode", "stop", "devmode", "--ts", e24.local(0, 9))
    earned = {row["id"] for row in json.loads(e24.ql("stamps", "--json").stdout)}
    check("a batch of work earns the obvious stamps",
          {"first-light", "warm-up", "early-bird", "daily-ten",
           "centurion", "fragment-thousand"} <= earned, str(sorted(earned)))
    gallery = e24.vault / "Questline" / "gallery"
    check("no card exists before a claim", not gallery.exists() or not list(gallery.iterdir()))
    notes = [json.loads(line) for line in e24.notify.read_text().splitlines()]
    stamp_notes = [n for n in notes if "stamp" in n["title"]]
    check("one notification covers the whole batch",
          len(stamp_notes) == 1 and "stamp" in stamp_notes[0]["title"], str(stamp_notes))

    e24.ok("claim", "centurion")
    png, md = gallery / "centurion.png", gallery / "centurion.md"
    check("a claim writes the PNG and the markdown card", png.is_file() and md.is_file())
    import struct
    width, height = struct.unpack(">II", png.read_bytes()[16:24])
    check("the gift card is a 640x360 PNG", (width, height) == (640, 360),
          f"{width}x{height}")
    check("the markdown card names the stamp", "centurion" in md.read_text())
    state = json.loads(e24.ql("status", "--json").stdout)
    check("the cosmetic is in the projection", "centurion" in state["gifts_claimed"],
          str(state.get("gifts_claimed")))
    check("waybar shows the gift count", "✦1" in (e24.home / "line").read_text(),
          (e24.home / "line").read_text())
    e24.ok("claim", "centurion")
    claims = [ev for ev in json.loads(e24.ql("events", "--json").stdout)
              if ev["type"] == "gift.claim"]
    check("a second claim is a no-op", len(claims) == 1, str(claims))
    e24.ok("rebuild")
    e24.ok("mode", "start", "readmode", "--ts", e24.local(0, 10))
    e24.ok("mode", "stop", "readmode", "--ts", e24.local(0, 11))
    seen = [ev for ev in json.loads(e24.ql("events", "--json").stdout)
            if ev["type"] == "stamp" and ev["key"] == "centurion"]
    check("a rebuild never re-issues a stamp", len(seen) == 1, str(seen))

    # 32. Kaizen stamps and a refused claim for an unearned gift
    e25 = Env()
    refused = e25.ql("claim", "clean-sweep")
    check("an unearned stamp cannot be claimed",
          refused.returncode == 2 and "not earned" in refused.stderr, refused.stderr)
    for index, offset in enumerate((28, 21, 14, 7, 0)):
        metric = "open" if index == 0 else ("minutes" if index == 1 else "value")
        baseline = "12" if index == 0 else ("100" if index == 1 else str(index + 3))
        value = "0" if index == 0 else ("70" if index == 1 else str(index))
        started = e25.ok("kaizen", "start", f"h{index}", "--metric", metric,
                         "--baseline", baseline, "--ts", e25.local(offset, 10))
        kid = started.stdout.split()[0]
        e25.ok("kaizen", "end", kid, "--value", value)
    earned = {row["id"] for row in json.loads(e25.ql("stamps", "--json").stdout)}
    check("all eight Kaizen stamps can be earned",
          {"hypothesis", "measured", "drop-three", "zero-open", "time-saved",
           "repeat-offender", "chain-of-custody", "weekly-cadence"} <= earned,
          str(sorted(earned)))
    check("unclaimed gifts still generate nothing",
          not (e25.vault / "Questline" / "gallery").exists())

    # 33. Obsidian links, ql add, and the MCP stdio server (F9.8)
    e26 = Env()
    (e26.vault / "Inbox.md").write_text("# Inbox\n")
    added = e26.ok("add", "Write notes", "--project", "demo",
                   "--link", "[[projects/demo]]", "--link", "Weekly/2026-W47")
    tid = added.stdout.split()[0]
    scan = json.loads(e26.ql("scan", "--json").stdout)
    row = next(item for item in scan if item["id"] == tid)
    check("add writes a stable block id", row["has_id"] and tid.startswith("ql-"))
    check("project tag and wikilinks are parsed",
          row["project"] == "demo" and row["links"] == ["projects/demo", "Weekly/2026-W47"],
          str(row))
    hud = json.loads((e26.home / "hud.json").read_text())
    check("wikilinks are hidden from the card text",
          any(t["text"] == "Write notes" for t in hud["tasks_open"]), str(hud["tasks_open"]))
    check("the note is backed up before the write",
          (e26.vault / "Questline" / "id-backups" / "Inbox.md").is_file())
    check("a scanner-skipped note is rejected",
          e26.ql("add", "x", "--note", "Questline/x.md").returncode == 2)
    check("a path outside the vault is rejected",
          e26.ql("add", "x", "--note", "../outside.md").returncode == 2)

    calls = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "board", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "add_task", "arguments":
                    {"text": "From the agent", "project": "demo",
                     "links": ["[[projects/demo]]"]}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "done", "arguments": {"id": tid}}},
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
         "params": {"name": "done", "arguments": {"id": tid}}},
        {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
         "params": {"name": "nope", "arguments": {}}},
    ]
    mcp = subprocess.run([sys.executable, str(QL.with_name("mcp.py"))],
                         input="\n".join(json.dumps(c) for c in calls) + "\n",
                         env=e26.env, capture_output=True, text=True)
    replies = [json.loads(line) for line in mcp.stdout.splitlines()]
    check("MCP answers one JSON line per request",
          len(replies) == 7 and all(r.get("jsonrpc") == "2.0" for r in replies),
          str(len(replies)))
    check("MCP exposes four tools",
          [t["name"] for t in replies[1]["result"]["tools"]] ==
          ["board", "status", "done", "add_task"], str(replies[1]))
    board = json.loads(replies[2]["result"]["content"][0]["text"])
    check("MCP board returns links with a card",
          any(c["id"] == tid and c["links"] == ["projects/demo", "Weekly/2026-W47"]
              for c in board["open"]), str(board["open"]))
    from_agent = json.loads(replies[3]["result"]["content"][0]["text"])
    check("MCP add_task writes to the vault",
          from_agent.get("text") == "From the agent" and from_agent.get("project") == "demo",
          str(from_agent))
    closed = json.loads(replies[4]["result"]["content"][0]["text"])
    check("MCP done closes a card", closed.get("already_done") is False, str(closed))
    again = json.loads(replies[5]["result"]["content"][0]["text"])
    check("MCP done is idempotent", again.get("already_done") is True, str(again))
    check("an unknown MCP tool is reported as an error",
          replies[6]["result"].get("isError") is True, str(replies[6]))

    print(f"\n{FAILS} failure(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
