#!/usr/bin/env python3
"""Questline — the event-log core of the desktop-work subsystem.

Design rules (see docs/subsystem/RULES.md):
  * The append-only event log is the only source of truth.
  * state.json is a pure projection; `ql rebuild` reproduces it exactly.
  * Nothing outside Questline/ is ever rewritten.
  * No network, no daemon, no dependencies beyond the stdlib.

Layout:
  $QL_VAULT/Questline/events/<device>.tsv   one log per device, merged on read
  $QL_VAULT/Questline/id-backups/           last copy of each note before ids
  $QL_HOME/state.json                       projection cache
  $QL_HOME/vault-cache.json                 note mtimes and parsed tasks
  $QL_HOME/device-id                         local identity, never synced

Event columns (tab separated, no header):
  event_id  ts(UTC)  day(local)  device  seq  type  key  value
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import tomllib
import uuid
from collections import Counter

import stamps as stamp_catalog
from datetime import datetime, timedelta, timezone
from pathlib import Path

VAULT = Path(os.environ.get("QL_VAULT", "~/Documentos/Vault")).expanduser()
HOME = Path(os.environ.get("QL_HOME", "~/.local/state/questline")).expanduser()
EVENTS = VAULT / "Questline" / "events"
STATE = HOME / "state.json"
# Texto ya masticado para waybar: el indicador lo lee con `read`, sin lanzar
# ningún proceso. Se reescribe en cada rebuild (transición de modo o tarea).
LINE = HOME / "line"
TIP = HOME / "tip"
HUD = HOME / "hud.json"
NOTIFY_STATE = HOME / "notify.json"
SPLASH = HOME / "splash.json"
SPRINT = VAULT / "Questline" / "sprint.json"
GALLERY = VAULT / "Questline" / "gallery"
DEVICE_FILE = HOME / "device-id"
CACHE_FILE = HOME / "vault-cache.json"
IDBACKUPS = VAULT / "Questline" / "id-backups"
RULES_FILE = Path(os.environ.get("QL_RULES", Path(__file__).resolve().with_name("rules.toml")))

TYPES = ("mode.start", "mode.stop", "task.done", "task.reopen", "role",
         "stamp", "gift.claim", "kaizen", "milestone", "nudge")


# --------------------------------------------------------------------------- #
# identity and clock
# --------------------------------------------------------------------------- #
def slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")[:16]


def device() -> str:
    """Stable local identity: <host>-<6 hex>. Never leaves this machine."""
    HOME.mkdir(parents=True, exist_ok=True)
    if DEVICE_FILE.is_file():
        value = DEVICE_FILE.read_text().strip()
        if value:
            return value
    value = f"{slug(socket.gethostname()) or 'host'}-{uuid.uuid4().hex[:6]}"
    DEVICE_FILE.write_text(value + "\n")
    os.chmod(DEVICE_FILE, 0o600)
    return value


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def local_day(dt: datetime) -> str:
    return dt.astimezone().strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- #
# log
# --------------------------------------------------------------------------- #
def log_path(dev: str) -> Path:
    return EVENTS / f"{dev}.tsv"


def append(kind: str, key: str, value: str = "", when: datetime | None = None,
           origin: str | None = None) -> dict:
    """Append one event under an exclusive lock and return it as a dict."""
    if kind not in TYPES:
        sys.exit(f"unknown event type: {kind} (allowed: {', '.join(TYPES)})")
    EVENTS.mkdir(parents=True, exist_ok=True)
    dev = origin or device()
    when = when or now_utc()
    path = log_path(dev)
    with path.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        seq = 0
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 5 and parts[3] == dev:
                try:
                    seq = max(seq, int(parts[4]))
                except ValueError:
                    pass
        event = {
            "event_id": uuid.uuid4().hex,
            "ts": iso(when),
            "day": local_day(when),
            "device": dev,
            "seq": seq + 1,
            "type": kind,
            "key": key,
            "value": str(value),
        }
        fh.write("\t".join(str(event[k]) for k in
                           ("event_id", "ts", "day", "device", "seq", "type", "key", "value")) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
        fcntl.flock(fh, fcntl.LOCK_UN)
    # La proyección se recalcula aquí para que el indicador de waybar tenga el
    # texto fresco en la siguiente vuelta (2 s) sin lanzar Python por tick.
    rebuild(quiet=True)
    return event


def read_events() -> list[dict]:
    """Merge every device log: dedupe by event_id, order by (ts, device, seq)."""
    if not EVENTS.is_dir():
        return []
    seen: set[str] = set()
    out: list[dict] = []
    for path in sorted(EVENTS.glob("*.tsv")):
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            eid, ts, day, dev, seq, kind, key = parts[:7]
            value = parts[7] if len(parts) > 7 else ""
            if eid in seen:
                continue
            seen.add(eid)
            try:
                seq_i = int(seq)
            except ValueError:
                continue
            out.append({"event_id": eid, "ts": ts, "day": day, "device": dev,
                        "seq": seq_i, "type": kind, "key": key, "value": value})
    out.sort(key=lambda e: (e["ts"], e["device"], e["seq"]))
    return out


# --------------------------------------------------------------------------- #
# vault scan (F9.2)
# --------------------------------------------------------------------------- #
# The vault is the task manager; Questline only reads it. The single exception
# is a block id appended once to a task line, so a task keeps its identity when
# the line moves between notes. Everything else is left byte for byte.
CHECKBOX = re.compile(r"^(\s*[-*]\s+\[)([ xX])(\]\s+)(.*)$")
BLOCKID = re.compile(r"\s\^ql-([0-9a-f]{6,12})\s*$")
PROJECT = re.compile(r"#project/([A-Za-z0-9_-]+)")
LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
SKIP_DIRS = {".obsidian", ".trash", ".git", ".stversions", ".sync",
             "node_modules", "Questline"}
MAX_NOTE_BYTES = 256 * 1024


def plain(text: str) -> str:
    """Task text without machine tags: project tag and Obsidian wikilinks."""
    cleaned = PROJECT.sub("", text)
    cleaned = LINK.sub("", cleaned)
    return " ".join(cleaned.split())


def load_cache() -> dict:
    if CACHE_FILE.is_file():
        try:
            data = json.loads(CACHE_FILE.read_text())
            if data.get("version") == 1 and isinstance(data.get("files"), dict):
                return data
        except (OSError, ValueError):
            pass
    return {"version": 1, "files": {}}


def save_cache(files: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"version": 1, "files": files}, indent=1,
                              sort_keys=True) + "\n")
    os.replace(tmp, CACHE_FILE)


def task_id(rel: str, text: str, taken: dict) -> str:
    """Deterministic id: the same line in the same note always gets the same id."""
    seed = f"{rel}\0{text}"
    digest = hashlib.sha1(seed.encode()).hexdigest()
    for size in (6, 8, 12):
        tid = "ql-" + digest[:size]
        owner = taken.get(tid)
        if owner is None or owner == seed:
            return tid
    return "ql-" + uuid.uuid4().hex[:12]


def split_task(line: str):
    """(prefix, mark, text, block_id) for a checkbox line, else None."""
    m = CHECKBOX.match(line)
    if not m:
        return None
    body = m.group(4)
    bid = BLOCKID.search(body)
    if bid:
        body = body[:bid.start()].rstrip()
    return m.group(1), m.group(2), body.strip(), (f"ql-{bid.group(1)}" if bid else "")


def parse_note(path: Path, rel: str, taken: dict) -> list:
    tasks = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for number, line in enumerate(text.splitlines(), 1):
        parsed = split_task(line)
        if parsed is None:
            continue
        _, mark, body, bid = parsed
        if not body:
            continue
        proj = PROJECT.search(body)
        tid = bid or task_id(rel, body, taken)
        taken[tid] = f"{rel}\0{body}"
        tasks.append({"id": tid, "done": mark in "xX", "text": body,
                      "project": proj.group(1) if proj else "",
                      "links": [m.group(1).strip() for m in LINK.finditer(body)],
                      "line": number, "has_id": bool(bid)})
    return tasks


def assign_ids(path: Path, rel: str, tasks: list) -> int:
    """Append ` ^ql-xxxxxx` to task lines without one. Backs the note up first."""
    todo = [t for t in tasks if not t.get("has_id")]
    if not todo:
        return 0
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    for t in todo:
        idx = t["line"] - 1
        if idx >= len(lines):
            continue
        keep = "\n" if lines[idx].endswith("\n") else ""
        body = lines[idx][:-1] if keep else lines[idx]
        lines[idx] = f"{body.rstrip()} ^{t['id']}{keep}"
        t["has_id"] = True
    IDBACKUPS.mkdir(parents=True, exist_ok=True)
    (IDBACKUPS / rel.replace("/", "__")).write_text(raw, encoding="utf-8")
    mode = path.stat().st_mode
    tmp = path.with_name(path.name + ".qltmp")
    tmp.write_text("".join(lines), encoding="utf-8")
    os.chmod(tmp, mode & 0o7777)
    os.replace(tmp, path)
    return len(todo)


def scan_vault(write_ids: bool = False) -> tuple:
    """Walk the vault. Returns ({relpath: {mtime, size, tasks}}, stats)."""
    cache = load_cache()
    taken = {t["id"]: f"{rel}\0{t['text']}"
             for rel, info in cache["files"].items() for t in info.get("tasks", [])}
    files: dict = {}
    stats: Counter = Counter()
    if not VAULT.is_dir():
        return files, stats
    for path in sorted(VAULT.rglob("*.md")):
        rel = path.relative_to(VAULT).as_posix()
        if set(Path(rel).parts) & SKIP_DIRS:
            stats["excluded"] += 1
            continue
        if path.is_symlink():
            stats["symlink"] += 1
            continue
        try:
            st = path.stat()
        except OSError:
            continue
        if st.st_size > MAX_NOTE_BYTES:
            stats["large"] += 1
            continue
        prev = cache["files"].get(rel)
        pending = bool(prev) and any(not t.get("has_id") for t in prev.get("tasks", []))
        fresh = prev and prev.get("mtime") == st.st_mtime and prev.get("size") == st.st_size
        if fresh and not (write_ids and pending):
            files[rel] = prev
            stats["cached"] += 1
            continue
        tasks = parse_note(path, rel, taken)
        stats["read"] += 1
        stats["tasks"] += len(tasks)
        if write_ids and any(not t["has_id"] for t in tasks):
            stats["ids"] += assign_ids(path, rel, tasks)
            st = path.stat()
        files[rel] = {"mtime": st.st_mtime, "size": st.st_size, "tasks": tasks}
    return files, stats


def all_tasks(files: dict) -> list:
    out = []
    for rel, info in files.items():
        for t in info.get("tasks", []):
            out.append({**t, "file": rel})
    return sorted(out, key=lambda t: (t["file"], t["line"]))


def sync_vault() -> tuple:
    """Emit task.done / task.reopen only on a change since the last sync."""
    old = {t["id"]: t for info in load_cache()["files"].values()
           for t in info.get("tasks", [])}
    files, stats = scan_vault()
    new = {t["id"]: t for t in all_tasks(files)}
    emitted = 0
    for tid, t in sorted(new.items()):
        prev = old.get(tid)
        if prev is None or bool(prev.get("done")) == t["done"]:
            continue
        append("task.done" if t["done"] else "task.reopen", tid, t["project"])
        emitted += 1
    save_cache(files)
    return emitted, stats


def set_done(task_id: str, done: bool, project: str = "",
             when: datetime | None = None) -> dict:
    """Tick or untick a task: vault line + event, so both agree.

    The vault is the source of truth for existence; the event log is the source
    of truth for points. Doing both keeps `ql sync` from re-emitting anything.
    An unknown id still records the event (a task may live outside this vault).
    """
    files, _ = scan_vault(write_ids=False)
    target = next((t for t in all_tasks(files) if t["id"] == task_id), None)
    if target is not None:
        if bool(target["done"]) == done:
            return {"changed": False, "file": target["file"], "project": target["project"]}
        flip_checkbox(VAULT / target["file"], target["file"], task_id, done)
        files.pop(target["file"], None)   # force a rescan of that note
        save_cache(files)
        project = project or target["project"]
    append("task.done" if done else "task.reopen", task_id, project, when)
    return {"changed": True,
            "file": target["file"] if target else "",
            "text": plain(target["text"]) if target else "",
            "project": project}


def flip_checkbox(path: Path, rel: str, task_id: str, done: bool) -> bool:
    """Flip one task's checkbox in place. Backs the note up first."""
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines(keepends=True)
    hit = False
    for i, line in enumerate(lines):
        m = CHECKBOX.match(line.rstrip("\n"))
        if not m:
            continue
        bid = BLOCKID.search(m.group(4))
        if not bid or f"ql-{bid.group(1)}" != task_id:
            continue
        nueva = "x" if done else " "
        lines[i] = f"{m.group(1)}{nueva}{m.group(3)}{m.group(4)}" + \
                   ("\n" if line.endswith("\n") else "")
        hit = True
        break
    if not hit:
        return False
    IDBACKUPS.mkdir(parents=True, exist_ok=True)
    (IDBACKUPS / rel.replace("/", "__")).write_text(raw, encoding="utf-8")
    mode = path.stat().st_mode
    tmp = path.with_name(path.name + ".qltmp")
    tmp.write_text("".join(lines), encoding="utf-8")
    os.chmod(tmp, mode & 0o7777)
    os.replace(tmp, path)
    return True


def add_task(text: str, project: str = "", links: list[str] | None = None,
             note: str = "Inbox.md") -> dict | None:
    """Append a checkbox to a vault note, with a stable block id and links.

    The vault stays the source of truth: the line is backed up first, written
    atomically, then the cache and the projection are refreshed. No event is
    appended here; adding a task is not points.
    """
    text = " ".join(text.split()).strip()
    if not text:
        print("empty task", file=sys.stderr)
        return None
    rel = note or "Inbox.md"
    parts = Path(rel).parts
    if not parts or ".." in parts or set(parts) & SKIP_DIRS:
        print(f"note is outside the scan: {rel}", file=sys.stderr)
        return None
    target = VAULT / rel
    if target.is_symlink() or not target.resolve().is_relative_to(VAULT.resolve()):
        print(f"note escapes the vault: {rel}", file=sys.stderr)
        return None

    files, _ = scan_vault(write_ids=False)
    taken = {t["id"] for info in files.values() for t in info.get("tasks", [])}
    while True:
        tid = "ql-" + uuid.uuid4().hex[:8]
        if tid not in taken:
            break

    clean_links: list[str] = []
    for value in links or []:
        value = value.strip()
        match = LINK.fullmatch(value)
        target_link = (match.group(1).strip() if match else value.strip("[]"))
        if target_link and target_link not in clean_links:
            clean_links.append(target_link)
    tag = f" #project/{slug(project)}" if project else ""
    wiki = "".join(f" [[{value}]]" for value in clean_links)
    line = f"- [ ] {text}{tag}{wiki} ^{tid}\n"

    existed = target.is_file()
    raw = target.read_text(encoding="utf-8") if existed else ""
    if raw and not raw.endswith("\n"):
        raw += "\n"
    mode = target.stat().st_mode & 0o7777 if existed else 0o664
    if existed:
        IDBACKUPS.mkdir(parents=True, exist_ok=True)
        (IDBACKUPS / rel.replace("/", "__")).write_text(raw, encoding="utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".qltmp")
    tmp.write_text(raw + line, encoding="utf-8")
    os.chmod(tmp, mode)
    os.replace(tmp, target)

    files, _ = scan_vault(write_ids=False)
    save_cache(files)
    rebuild(quiet=True)
    return {"id": tid, "file": rel, "text": text,
            "project": slug(project) if project else "", "links": clean_links}


def list_tasks(write_ids: bool, project: str, as_json: bool) -> int:
    files, stats = scan_vault(write_ids=write_ids)
    save_cache(files)
    tasks = all_tasks(files)
    if project:
        tasks = [t for t in tasks if t["project"] == project]
    if as_json:
        print(json.dumps(tasks, indent=2, sort_keys=True))
        return 0
    for t in tasks:
        mark = "x" if t["done"] else " "
        print(f"[{mark}] {t['id']}  {t['file']}:{t['line']}  {t['text'][:64]}")
    extra = f" · {stats['ids']} ids written" if write_ids else ""
    print(f"{len(tasks)} tasks · {stats['read']} notes read · "
          f"{stats['cached']} cached · {stats['large']} large · "
          f"{stats['excluded']} excluded{extra}")
    return 0


# --------------------------------------------------------------------------- #
# rules and fold
# --------------------------------------------------------------------------- #
def load_rules() -> dict:
    with RULES_FILE.open("rb") as fh:
        return tomllib.load(fh)


def fold(events: list[dict], rules: dict) -> dict:
    """Pure function: merged events -> state. Deterministic.

    Open sessions earn nothing until closed, so a rebuild is reproducible.
    Points are computed per closed session, then capped per (day, mode).
    """
    pts = rules["points"]
    roles = rules["roles"]
    affinity = {mode: role for role, modes in roles["affinity"].items() for mode in modes}

    open_sessions: dict[str, tuple[datetime, str, str]] = {}  # mode -> (start, day, role)
    raw_points: dict[tuple[str, str], int] = {}
    minutes: dict[tuple[str, str], float] = {}
    tasks: dict[str, dict] = {}
    milestones: list[str] = []
    role = ""
    role_seen = ""

    for ev in events:
        when = parse_ts(ev["ts"])
        kind, key = ev["type"], ev["key"]

        if kind == "mode.start":
            open_sessions[key] = (when, ev["day"], role)
        elif kind == "mode.stop":
            started = open_sessions.pop(key, None)
            if started is None:
                continue
            start, day, role_at_start = started
            span = min((when - start).total_seconds() / 60.0, pts["max_session_minutes"])
            if span <= 0:
                continue
            bucket = (day, key)
            points = int(span // 10) * pts["per_10_minutes"]
            if role_at_start and affinity.get(key) == role_at_start:
                points = int(round(points * (1 + roles["bonus"])))
            raw_points[bucket] = raw_points.get(bucket, 0) + points
            minutes[bucket] = minutes.get(bucket, 0.0) + span
        elif kind in ("task.done", "task.reopen"):
            tasks[key] = {"done": kind == "task.done", "ts": ev["ts"],
                          "device": ev["device"], "seq": ev["seq"],
                          "project": ev["value"] or tasks.get(key, {}).get("project", "")}
        elif kind == "role":
            role, role_seen = key, ev["ts"]
        elif kind == "milestone":
            milestones.append(key)

    per_mode: dict[str, dict] = {}
    total_time = 0
    for bucket, mins in sorted(minutes.items()):
        day, mode = bucket
        capped = min(raw_points.get(bucket, 0), pts["daily_cap_per_mode"])
        per_mode.setdefault(day, {})[mode] = {"minutes": round(mins, 1), "fragments": capped}
        total_time += capped

    done = {k: v for k, v in tasks.items() if v["done"]}
    total_tasks = len(done) * pts["task_done"]
    done_days: dict[str, int] = {}
    for item in done.values():
        day = local_day(parse_ts(item["ts"]))
        done_days[day] = done_days.get(day, 0) + 1

    # streak: consecutive days (ending today or yesterday) with enough minutes
    by_day: dict[str, float] = {}
    for (day, mode), mins in minutes.items():
        if mode == "role":
            continue
        by_day[day] = by_day.get(day, 0.0) + mins
    today = local_day(now_utc())
    qualified = {d for d, m in by_day.items() if m >= pts["streak_min_minutes"]}
    streak = 0
    cursor = today
    if cursor not in qualified:
        cursor = (now_utc() - timedelta(days=1)).strftime("%Y-%m-%d")
    while cursor in qualified:
        streak += 1
        cursor = (datetime.strptime(cursor, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")

    streak_bonus = streak * pts["streak_day_bonus"] if streak else 0
    if streak >= 7:
        streak_bonus += pts["streak_7_bonus"]

    # points earned per day, for the HUD bar and the weekly review
    days: dict[str, dict] = {}
    for day, modes in per_mode.items():
        days.setdefault(day, {"modes": 0, "tasks": 0, "minutes": 0.0})
        days[day]["modes"] = sum(m["fragments"] for m in modes.values())
        days[day]["minutes"] = round(sum(m["minutes"] for m in modes.values()), 1)
    for day, count in done_days.items():
        days.setdefault(day, {"modes": 0, "tasks": 0, "minutes": 0.0})
        days[day]["tasks"] = count * pts["task_done"]
    today_earned = days.get(today, {}).get("modes", 0) + days.get(today, {}).get("tasks", 0)

    role_days = ""
    if role_seen:
        role_days = (datetime.strptime(today, "%Y-%m-%d")
                     - datetime.strptime(local_day(parse_ts(role_seen)), "%Y-%m-%d")).days
    gifts_claimed = sorted({ev["key"] for ev in events if ev["type"] == "gift.claim"})
    return {
        "version": 1,
        "device": device(),
        "fragments": total_time + total_tasks + streak_bonus,
        "breakdown": {"modes": total_time, "tasks": total_tasks, "streak": streak_bonus},
        "streak_days": streak,
        "role": role,
        "role_age_days": role_days,
        "role_cooldown_days": roles["cooldown_days"],
        "tasks_done": len(done),
        "today": today,
        "today_fragments": today_earned,
        "days": {d: days[d] for d in sorted(days)},
        "modes": per_mode,
        "open_sessions": sorted(open_sessions),
        "session_started": {m: iso(s[0]) for m, s in open_sessions.items()},
        "gifts_claimed": gifts_claimed,
        "milestones": milestones,
        "events": len(events),
    }


def hud_payload(state: dict, rules: dict) -> dict:
    """What the pinned card shows. Built from the cached vault and the state."""
    hud_rules = rules.get("hud", {})
    cache = load_cache()
    tasks = [t for note in cache["files"].values() for t in note.get("tasks", [])]
    open_tasks = [t for t in tasks if not t.get("done")]

    projects: dict[str, dict] = {}
    for t in tasks:
        name = t.get("project") or "inbox"
        p = projects.setdefault(name, {"name": name, "done": 0, "total": 0})
        p["total"] += 1
        if t.get("done"):
            p["done"] += 1

    mode = (state.get("open_sessions") or [""])[0]
    return {
        "role": state.get("role") or "",
        "fragments": state.get("fragments", 0),
        "fragments_today": state.get("today_fragments", 0),
        "day_goal": hud_rules.get("day_goal", 60),
        "streak": state.get("streak_days", 0),
        "streak_goal": hud_rules.get("streak_goal", 7),
        "session": {"mode": mode,
                    "started": state.get("session_started", {}).get(mode, "")} if mode else None,
        "tasks_open": [{"id": t["id"], "text": plain(t["text"]),
                        "project": t.get("project") or "inbox"} for t in open_tasks[:hud_rules.get("tasks_on_card", 3)]],
        "open_count": len(open_tasks),
        "gifts": state.get("gifts_claimed", []),
        "projects": sorted(projects.values(), key=lambda p: (-p["done"], p["name"])),
        "today": state.get("today", ""),
    }


def rebuild(quiet: bool = False) -> dict:
    rules = load_rules()
    state = fold(read_events(), rules)
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, STATE)
    payload = hud_payload(state, rules)
    # Texto para waybar: dos ficheros de una línea, sin formato que el shell
    # tenga que interpretar (nada de JSON ni de subprocesos por tick).
    barra = f"{state['fragments']} FRG" if state["fragments"] else ""
    if state["streak_days"]:
        barra = (barra + " · " if barra else "") + f"{state['streak_days']}d"
    if payload["open_count"]:
        barra = (barra + " · " if barra else "") + f"▣{payload['open_count']}"
    if payload["gifts"]:
        barra = (barra + " · " if barra else "") + f"✦{len(payload['gifts'])}"
    pie = []
    if state["role"] and state["role"] != "none":
        pie.append(f"role {state['role']}")
    if state["streak_days"]:
        pie.append(f"streak {state['streak_days']}d")
    if state["tasks_done"]:
        pie.append(f"{state['tasks_done']} done")
    if payload["open_count"]:
        pie.append(f"{payload['open_count']} open")
    if payload["gifts"]:
        pie.append(f"gifts {', '.join(payload['gifts'])}")
    for target, text in ((LINE, barra), (TIP, " · ".join(pie))):
        tmp = target.with_suffix(".tmp")
        tmp.write_text(text)
        os.replace(tmp, target)
    hud = HUD.with_suffix(".tmp")
    hud.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    os.replace(hud, HUD)
    if not quiet:
        print(f"{state['fragments']} fragments · {state['streak_days']}d streak · {state['tasks_done']} tasks")
    return state


# --------------------------------------------------------------------------- #
# notifications (F9.5b)
# --------------------------------------------------------------------------- #
# One bubble, one fixed replaces_id: a burst of closes updates the same bubble
# instead of stacking. Closes that arrive more than NOTIFY_WINDOW seconds after
# the group opened start a new one. State lives in a file so no process has to
# stay alive to group, which keeps the "no daemon" invariant.
NOTIFY_ID = 9170
STAMP_NOTIFY_ID = 9171
NOTIFY_WINDOW = 5
NOTIFY_MAX = 5


def notify_send(title: str, body: str, replaces_id: int = NOTIFY_ID) -> bool:
    """Post one notification. Silent on failure: a task close must never break."""
    log = os.environ.get("QL_NOTIFY_LOG")
    if log:
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"title": title, "body": body}, ensure_ascii=False) + "\n")
        return True
    try:
        done = subprocess.run(
            ["gdbus", "call", "--session",
             "--dest", "org.freedesktop.Notifications",
             "--object-path", "/org/freedesktop/Notifications",
             "--method", "org.freedesktop.Notifications.Notify",
             "Questline", str(replaces_id), "", title, body, "[]", "{}", "8000"],
            capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def notify_payload(tasks: list[dict], state: dict, rules: dict) -> tuple[str, str]:
    """Title and body for one closed task or for the group it joined."""
    each = rules["points"]["task_done"]
    goal = rules.get("hud", {}).get("day_goal", 60)
    earned = state.get("today_fragments", 0)
    total = each * len(tasks)
    if len(tasks) == 1:
        task = tasks[0]
        title = f"+{total} FRG · {task.get('project') or 'inbox'}"
        body = task.get("text") or task.get("id", "")
    else:
        title = f"{len(tasks)} tasks closed · +{total} FRG"
        lines = [f"• {(t.get('text') or t.get('id', ''))[:60]}" for t in tasks[:3]]
        if len(tasks) > 3:
            lines.append(f"+{len(tasks) - 3} more")
        body = "\n".join(lines)
    return title, f"{body}\n{earned}/{goal} FRG today"


def notify_close(entry: dict) -> bool:
    """Notify a closed task, merging it with the ones of the last NOTIFY_WINDOW s."""
    now = now_utc()
    group = {"started": "", "tasks": []}
    if NOTIFY_STATE.is_file():
        try:
            data = json.loads(NOTIFY_STATE.read_text())
            if isinstance(data.get("tasks"), list) and data.get("started"):
                group = data
        except (OSError, ValueError):
            pass
    try:
        age = (now - parse_ts(group["started"])).total_seconds()
    except ValueError:
        age = None
    fresh = age is not None and 0 <= age <= NOTIFY_WINDOW
    tasks = ((group["tasks"] if fresh else []) + [entry])[-NOTIFY_MAX:]
    state = json.loads(STATE.read_text()) if STATE.is_file() else {}
    title, body = notify_payload(tasks, state, load_rules())
    if not notify_send(title, body):
        return False
    group = {"started": group["started"] if fresh else iso(now), "tasks": tasks}
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = NOTIFY_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(group, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, NOTIFY_STATE)
    return True


# --------------------------------------------------------------------------- #
# milestones (F9.5c)
# --------------------------------------------------------------------------- #
# A milestone is recorded once and never recomputed: the key carries its
# identity (project, run start, session start), so a rebuild cannot re-fire it.
def run_start_day(streak: int, today: str) -> str:
    """First day of the current streak. Stable while the streak keeps growing."""
    if streak <= 0 or not today:
        return today
    start = datetime.strptime(today, "%Y-%m-%d") - timedelta(days=streak - 1)
    return start.strftime("%Y-%m-%d")


def milestone_candidates(state: dict, rules: dict, cache: dict,
                         events: list[dict]) -> list[dict]:
    """Every milestone the current data supports, not just the new ones."""
    cfg = rules.get("milestones", {})
    out: list[dict] = []

    projects: dict[str, list[int]] = {}
    for note in cache.get("files", {}).values():
        for task in note.get("tasks", []):
            name = task.get("project") or "inbox"
            row = projects.setdefault(name, [0, 0])
            row[1] += 1
            if task.get("done"):
                row[0] += 1
    floor = cfg.get("project_min_tasks", 10)
    for name, (done, total) in sorted(projects.items()):
        if total >= floor and done == total:
            out.append({"key": f"project:{name}", "kind": "big",
                        "title": "Project complete",
                        "subtitle": f"{name} · {total} tasks",
                        "glyph": "icarus", "project": name})

    chain = cfg.get("chain_tasks", 5)
    final: dict[str, dict] = {}
    for ev in events:
        if ev["type"] in ("task.done", "task.reopen"):
            final[ev["key"]] = {"done": ev["type"] == "task.done", "ts": ev["ts"],
                                "project": ev["value"] or final.get(ev["key"], {}).get("project", "")}
    for mode, started in sorted(state.get("session_started", {}).items()):
        counts = Counter(t["project"] or "inbox" for t in final.values()
                         if t["done"] and t["ts"] >= started)
        for name, count in sorted(counts.items()):
            if count >= chain:
                out.append({"key": f"chain:{name}:{started}", "kind": "small",
                            "title": f"{count} in a row",
                            "subtitle": f"{name} · {mode}",
                            "glyph": "zoso", "project": name})

    streak = state.get("streak_days", 0)
    start = run_start_day(streak, state.get("today", ""))
    for days in cfg.get("streak_days", [7, 14, 30]):
        if streak >= days:
            out.append({"key": f"streak:{days}:{start}",
                        "kind": "big" if days >= 30 else "small",
                        "title": f"{days}-day streak",
                        "subtitle": f"{streak} days in a row",
                        "glyph": "presence"})
    week = cfg.get("perfect_week_days", 7)
    if streak >= week and streak % week == 0:
        out.append({"key": f"week:{state.get('today', '')}", "kind": "big",
                    "title": "Perfect week",
                    "subtitle": f"{week} qualified days",
                    "glyph": "hermit"})
    return out


def new_milestones(events: list[dict], state: dict, rules: dict, cache: dict) -> list[dict]:
    seen = {ev["key"] for ev in events if ev["type"] == "milestone"}
    return [m for m in milestone_candidates(state, rules, cache, events)
            if m["key"] not in seen]


def show_splash(payload: dict) -> None:
    """Write the payload and hand it to a one-shot splash process."""
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = SPLASH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, SPLASH)
    if os.environ.get("QL_NO_SPLASH"):
        return
    script = Path(__file__).resolve().with_name("splash.py")
    if not script.is_file():
        return
    try:
        subprocess.Popen([sys.executable, str(script), str(SPLASH)],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass


def raise_milestones() -> list[dict]:
    """Record the milestones that just became true and show at most one splash."""
    rules = load_rules()
    files, _ = scan_vault(write_ids=False)
    save_cache(files)
    events = read_events()
    state = fold(events, rules)
    new = new_milestones(events, state, rules, load_cache())
    for milestone in new:
        append("milestone", milestone["key"],
               json.dumps({k: milestone[k] for k in ("kind", "title", "subtitle", "glyph")},
                          sort_keys=True))
    if new:
        best = next((m for m in new if m["kind"] == "big"), new[0])
        show_splash({"key": best["key"], "kind": best["kind"],
                     "title": best["title"], "subtitle": best["subtitle"],
                     "glyph": best["glyph"], "project": best.get("project", "")})
    return new


def list_milestones(as_json: bool) -> int:
    rows = []
    for ev in read_events():
        if ev["type"] != "milestone":
            continue
        try:
            data = json.loads(ev["value"])
        except ValueError:
            data = {}
        rows.append({"ts": ev["ts"], "key": ev["key"], **data})
    if as_json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    for row in rows:
        print(f"{row['ts']}  {row.get('title', '?'):<18} {row['key']}")
    print(f"{len(rows)} milestone(s)")
    return 0


# --------------------------------------------------------------------------- #
# stamps and gifts (F9.5)
# --------------------------------------------------------------------------- #
# A stamp is an achievement earned by a criterion over the log. A claim turns
# it into a gift: one event, one local card, one cosmetic badge. Both are
# events, so a rebuild or a second device cannot invent or lose either.
def stamp_rows(events: list[dict]) -> dict[str, dict]:
    claimed = {ev["key"] for ev in events if ev["type"] == "gift.claim"}
    rows: dict[str, dict] = {}
    for ev in events:
        if ev["type"] != "stamp":
            continue
        try:
            data = json.loads(ev["value"])
        except ValueError:
            data = {}
        fallback = stamp_catalog.BY_ID.get(ev["key"], ())
        row = {
            "id": ev["key"],
            "name": data.get("name") or (fallback[1] if len(fallback) > 1 else ev["key"]),
            "family": data.get("family") or (fallback[2] if len(fallback) > 2 else "unknown"),
            "glyph": data.get("glyph") or (fallback[3] if len(fallback) > 3 else "zoso"),
            "criterion": data.get("criterion") or (fallback[4] if len(fallback) > 4 else ""),
            "gift": data.get("gift") or ev["key"],
            "earned": ev["ts"],
        }
        row["claimed"] = ev["key"] in claimed
        rows[ev["key"]] = row
    return rows


def raise_stamps() -> list[dict]:
    """Record newly earned stamps and post one notification for the batch."""
    rules = load_rules()
    events = read_events()
    state = fold(events, rules)
    new = stamp_catalog.candidates(events, state, rules)
    for stamp in new:
        append("stamp", stamp["id"], json.dumps(stamp, sort_keys=True))
    if new:
        count = len(new)
        title = f"{count} stamp{'s' if count != 1 else ''} earned"
        body = ", ".join(stamp["name"] for stamp in new[:5])
        if count > 5:
            body += f" · +{count - 5} more"
        notify_send(title, f"{body}\nql stamps · ql claim <id>", STAMP_NOTIFY_ID)
        rebuild(quiet=True)
    return new


def list_stamps(as_json: bool) -> int:
    rows = sorted(stamp_rows(read_events()).values(),
                  key=lambda r: (r["family"], r["id"]))
    if as_json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0
    if not rows:
        print(f"no stamps yet · {len(stamp_catalog.STAMPS)} in "
              f"{len(stamp_catalog.FAMILIES)} families")
        return 0
    print(f"{'family':<10} {'id':<18} {'name':<20} status")
    for row in rows:
        print(f"{row['family']:<10} {row['id']:<18} {row['name']:<20} "
              f"{'claimed' if row['claimed'] else 'unclaimed'}")
    print(f"{len(rows)}/{len(stamp_catalog.STAMPS)} stamps · "
          f"{sum(r['claimed'] for r in rows)} claimed")
    return 0


def claim_stamp(sid: str) -> int:
    """Generate a gift card once, record the claim, and apply the cosmetic."""
    events = read_events()
    rows = stamp_rows(events)
    stamp = rows.get(sid)
    if stamp is None:
        known = "" if sid in stamp_catalog.BY_ID else " (unknown id)"
        print(f"stamp not earned: {sid}{known}", file=sys.stderr)
        return 2
    if stamp["claimed"]:
        print(f"{sid} already claimed · ql stamps")
        return 0

    # Imported here so the core CLI does not need Cairo for normal commands.
    import gifts
    claimed_at = iso(now_utc())
    payload = {**stamp, "ts": claimed_at}
    png, md = gifts.install(payload, VAULT)
    append("gift.claim", sid,
           json.dumps({"stamp": sid, "gift": stamp["gift"], "ts": claimed_at,
                       "card": str(png.relative_to(VAULT)),
                       "note": str(md.relative_to(VAULT))}, sort_keys=True))
    rebuild(quiet=True)
    notify_send(f"Gift unlocked: {stamp['name']}",
                f"{png.relative_to(VAULT)} · ✦{len(fold(read_events(), load_rules())['gifts_claimed'])}",
                STAMP_NOTIFY_ID)
    print(f"claimed {sid} · {png.relative_to(VAULT)} · {md.relative_to(VAULT)}")
    return 0


# --------------------------------------------------------------------------- #
# sprint, review, kaizen and the daily nudge (F9.6)
# --------------------------------------------------------------------------- #
DAY = "%Y-%m-%d"


def vault_tasks() -> dict[str, dict]:
    files, _ = scan_vault(write_ids=False)
    save_cache(files)
    return {t["id"]: t for note in files.values() for t in note.get("tasks", [])}


def sprint_load() -> dict:
    try:
        data = json.loads(SPRINT.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def sprint_save(sprint: dict) -> None:
    SPRINT.parent.mkdir(parents=True, exist_ok=True)
    tmp = SPRINT.with_suffix(".tmp")
    tmp.write_text(json.dumps(sprint, indent=1, sort_keys=True) + "\n")
    os.replace(tmp, SPRINT)


def sprint_union(sprint: dict) -> set[str]:
    return set(sprint.get("committed", [])) | set(sprint.get("carried", []))


def sprint_counts(sprint: dict, tasks: dict) -> tuple[list[str], list[str]]:
    ids = sprint_union(sprint)
    done = sorted(t for t in ids if tasks.get(t, {}).get("done"))
    pending = sorted(t for t in ids if not tasks.get(t, {}).get("done"))
    return done, pending


def sprint_progress(sprint: dict) -> tuple[int, int]:
    """(day number, total days) of the sprint window."""
    start = datetime.strptime(sprint["start"], DAY).date()
    end = datetime.strptime(sprint["end"], DAY).date()
    total = (end - start).days + 1
    elapsed = (datetime.now().date() - start).days + 1
    return max(1, min(elapsed, total)), total


def sprint_start(projects: list[str], weeks: int, start: str) -> int:
    tasks = vault_tasks()
    previous = sprint_load()
    carried: list[str] = []
    if previous:
        # Whatever is still open is a commitment that moves to the new sprint.
        carried = sorted(t for t in sprint_union(previous)
                         if not tasks.get(t, {}).get("done"))
        if previous.get("status") == "active":
            previous["status"] = "closed"
        previous["carried"] = carried
        sprint_save(previous)
    wanted = sorted(set(projects))
    open_tasks = [tid for tid, t in tasks.items() if not t.get("done")]
    if wanted == ["all"]:
        committed = open_tasks
    else:
        committed = [tid for tid in open_tasks if tasks[tid]["project"] in wanted]
    if not wanted or (not committed and not carried):
        print("nothing committed: pass --projects a,b or --projects all", file=sys.stderr)
        return 2
    first = datetime.strptime(start, DAY).date() if start else datetime.now().date()
    last = first + timedelta(days=weeks * 7 - 1)
    week = first.isocalendar()
    sprint = {"id": f"{week.year}-W{week.week:02d}", "start": first.strftime(DAY),
              "end": last.strftime(DAY), "status": "active",
              "projects": wanted, "committed": sorted(committed),
              "carried": sorted(set(carried)), "created": iso(now_utc())}
    sprint_save(sprint)
    print(f"sprint {sprint['id']} · {sprint['start']} → {sprint['end']} · "
          f"{len(committed)} committed · {len(carried)} carried")
    return 0


def sprint_status(as_json: bool) -> int:
    sprint = sprint_load()
    if not sprint:
        print("no sprint yet · ql sprint start --projects all")
        return 0
    done, pending = sprint_counts(sprint, vault_tasks())
    day, total = sprint_progress(sprint) if sprint.get("status") == "active" else (0, 0)
    if as_json:
        print(json.dumps({"sprint": sprint, "done": done, "pending": pending,
                          "day": day, "days": total}, indent=2, sort_keys=True))
        return 0
    print(f"sprint {sprint['id']} · {sprint['start']} → {sprint['end']} · "
          f"{sprint.get('status')}" + (f" · day {day}/{total}" if total else ""))
    print(f"commit {len(sprint_union(sprint))} · done {len(done)} · "
          f"open {len(pending)} · carried {len(sprint.get('carried', []))}")
    return 0


def sprint_close() -> int:
    sprint = sprint_load()
    if sprint.get("status") != "active":
        print("no active sprint")
        return 1
    done, pending = sprint_counts(sprint, vault_tasks())
    sprint["status"] = "closed"
    sprint["carried"] = pending
    sprint_save(sprint)
    print(f"sprint {sprint['id']} closed · {len(done)} done · {len(pending)} carried")
    return 0


def last_days(days: int) -> list[str]:
    today = datetime.now().date()
    return [(today - timedelta(days=offset)).strftime(DAY) for offset in range(days - 1, -1, -1)]


def review_suggestion(state: dict, sprint: dict, tasks: dict) -> str:
    if not sprint or sprint.get("status") != "active":
        return "start a sprint: ql sprint start --projects all"
    if sprint.get("carried"):
        return (f"{len(sprint['carried'])} tasks carried over: commit that many fewer "
                f"next sprint")
    _, pending = sprint_counts(sprint, tasks)
    if pending:
        by_project: Counter = Counter(tasks.get(t, {}).get("project") or "inbox" for t in pending)
        project, count = by_project.most_common(1)[0]
        return f"{count} open in {project}: slice three of them into 25-minute tasks"
    used = {mode for modes in state.get("modes", {}).values() for mode in modes}
    idle = [m for m in ("readmode", "devmode", "writemode", "planingmode") if m not in used]
    if idle:
        return f"no {idle[0]} session in the window: book one 25-minute block"
    return "hold the pace: one Kaizen experiment (ql kaizen start) and measure it"


def review(days: int, as_json: bool) -> int:
    rules = load_rules()
    each = rules["points"]["task_done"]
    state = fold(read_events(), rules)
    sprint = sprint_load()
    tasks = vault_tasks()
    rows = []
    for day in last_days(days):
        info = state.get("days", {}).get(day, {})
        modes = state.get("modes", {}).get(day, {})
        rows.append({"day": day, "minutes": info.get("minutes", 0.0),
                     "tasks": info.get("tasks", 0) // each,
                     "fragments": info.get("modes", 0) + info.get("tasks", 0),
                     "modes": {m: v["minutes"] for m, v in modes.items()}})
    suggestion = review_suggestion(state, sprint, tasks)
    if as_json:
        print(json.dumps({"days": rows, "suggestion": suggestion, "sprint": sprint},
                         indent=2, sort_keys=True))
        return 0
    print(f"{'day':<11} {'min':>5} {'tasks':>6} {'FRG':>5}  modes")
    for row in rows:
        modes = ", ".join(f"{m} {int(mins)}m" for m, mins in sorted(row["modes"].items()))
        print(f"{row['day']:<11} {row['minutes']:>5.0f} {row['tasks']:>6} "
              f"{row['fragments']:>5}  {modes}")
    print(f"{'total':<11} {sum(r['minutes'] for r in rows):>5.0f} "
          f"{sum(r['tasks'] for r in rows):>6} {sum(r['fragments'] for r in rows):>5}")
    if sprint:
        done, pending = sprint_counts(sprint, tasks)
        print(f"sprint    {sprint['id']} · {len(done)} done · {len(pending)} open")
    print(f"\nexperiment · {suggestion}")
    return 0


def kaizen_list(as_json: bool) -> int:
    runs: dict[str, dict] = {}
    for ev in read_events():
        if ev["type"] != "kaizen":
            continue
        try:
            data = json.loads(ev["value"])
        except ValueError:
            continue
        row = runs.setdefault(ev["key"], {"id": ev["key"]})
        row.update({k: v for k, v in data.items() if k != "phase"})
        row[data.get("phase", "start")] = ev["ts"]
    if as_json:
        print(json.dumps(sorted(runs.values(), key=lambda r: r["id"]), indent=2, sort_keys=True))
        return 0
    if not runs:
        print("no experiments yet · ql kaizen start \"hypothesis\" --metric name --baseline N")
        return 0
    for row in sorted(runs.values(), key=lambda r: r["id"]):
        result = row.get("value", "?")
        print(f"{row['id']}  {row.get('hypothesis', '?')}  "
              f"{row.get('metric', '?')} {row.get('baseline', '?')} → {result}")
    return 0


def kaizen_start(hypothesis: str, metric: str, baseline: str,
                 when: datetime | None = None) -> int:
    kid = "kz-" + uuid.uuid4().hex[:6]
    append("kaizen", kid, json.dumps({"phase": "start", "hypothesis": hypothesis,
                                      "metric": metric, "baseline": baseline}, sort_keys=True),
           when)
    print(f"{kid}  {hypothesis}  ({metric} baseline {baseline})")
    return 0


def kaizen_end(kid: str, value: str, when: datetime | None = None) -> int:
    starts = [json.loads(ev["value"]) for ev in read_events()
              if ev["type"] == "kaizen" and ev["key"] == kid
              and '"start"' in ev["value"]]
    if not starts:
        print(f"unknown experiment: {kid}", file=sys.stderr)
        return 2
    append("kaizen", kid, json.dumps({"phase": "end", "value": value}, sort_keys=True), when)
    print(f"{kid}  {starts[-1].get('metric', '?')} "
          f"{starts[-1].get('baseline', '?')} → {value}")
    return 0


def maybe_nudge() -> bool:
    """One notification per day, only while a sprint is open, at the first mode."""
    sprint = sprint_load()
    if sprint.get("status") != "active":
        return False
    dev = device()
    day = local_day(now_utc())
    events = read_events()
    if any(ev["type"] == "nudge" and ev["day"] == day and ev["device"] == dev
           for ev in events):
        return False
    done, pending = sprint_counts(sprint, vault_tasks())
    number, total = sprint_progress(sprint)
    try:
        state = json.loads(STATE.read_text())
    except (OSError, ValueError):
        state = {}
    title = f"Sprint {sprint['id']} · day {number}/{total}"
    body = (f"{len(pending)} open · {len(done)} done · "
            f"{state.get('today_fragments', 0)} FRG today")
    append("nudge", day, sprint["id"])
    notify_send(title, body)
    return True


# --------------------------------------------------------------------------- #
# status
# --------------------------------------------------------------------------- #
def status(as_json: bool) -> int:
    state = fold(read_events(), load_rules())
    if as_json:
        print(json.dumps(state, indent=2, sort_keys=True))
        return 0
    today = state["today"]
    role = state["role"] or "none"
    if state["role"]:
        left = max(0, state["role_cooldown_days"] - state["role_age_days"])
        role = f"{state['role']} ({left}d to switch)"
    print(f"device    {state['device']}")
    print(f"role      {role}")
    print(f"fragments {state['fragments']}  = modes {state['breakdown']['modes']}"
          f" + tasks {state['breakdown']['tasks']} + streak {state['breakdown']['streak']}")
    print(f"streak    {state['streak_days']}d   tasks {state['tasks_done']}   "
          f"gifts {len(state.get('gifts_claimed', []))}")
    for day, modes in sorted(state["modes"].items(), reverse=True)[:2]:
        label = "today" if day == today else day
        parts = ", ".join(f"{m} {v['minutes']:.0f}m -> {v['fragments']}"
                          for m, v in sorted(modes.items()))
        print(f"{label:<9} {parts}")
    if state["open_sessions"]:
        print(f"open      {', '.join(state['open_sessions'])} (pending until closed)")
    return 0


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(prog="ql", description="Questline core CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("log", help="append a raw event")
    p.add_argument("type", choices=TYPES)
    p.add_argument("key")
    p.add_argument("value", nargs="?", default="")
    p.add_argument("--ts", help="inject a UTC timestamp (tests)")

    p = sub.add_parser("mode", help="start/stop a desktop mode")
    p.add_argument("action", choices=("start", "stop"))
    p.add_argument("mode")
    p.add_argument("--ts")

    for name, kind in (("done", "task.done"), ("reopen", "task.reopen")):
        p = sub.add_parser(name, help=f"mark a task {name} (vault task id)")
        p.add_argument("task_id")
        p.add_argument("--project", default="")
        p.add_argument("--ts")
        p.add_argument("--notify", action="store_true",
                       help="post a desktop notification (silent by default)")

    p = sub.add_parser("role", help="set the role")
    p.add_argument("role_id")
    p.add_argument("--ts")

    p = sub.add_parser("status", help="show the projection")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("rebuild", help="recompute state.json from the log")
    p = sub.add_parser("events", help="dump merged events")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("device", help="print the device id")

    p = sub.add_parser("tasks", help="list vault tasks (read only)")
    p.add_argument("--project")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("scan", help="like tasks, optionally writing block ids")
    p.add_argument("--project")
    p.add_argument("--json", action="store_true")
    p.add_argument("--write-ids", action="store_true",
                   help="append a block id to task lines that have none")

    p = sub.add_parser("add", help="append a task to a vault note")
    p.add_argument("text", nargs="+", help="task text (quote it)")
    p.add_argument("--project", default="", help="project tag, e.g. gallery")
    p.add_argument("--link", action="append", default=[],
                   help="Obsidian wikilink target; repeatable")
    p.add_argument("--note", default="Inbox.md", help="note inside the vault")

    p = sub.add_parser("sync", help="record task transitions from the vault")
    p = sub.add_parser("milestones", help="list the milestones in the log")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("stamps", help="earned stamps and their claim status")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("claim", help="claim the gift of an earned stamp")
    p.add_argument("stamp_id")

    p = sub.add_parser("sprint", help="the window and what you committed to")
    p.add_argument("action", choices=("start", "status", "close"))
    p.add_argument("--projects", default="", help="comma separated, or 'all'")
    p.add_argument("--weeks", type=int, default=1)
    p.add_argument("--start", help="first day (YYYY-MM-DD), default today")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("review", help="last N days in one table")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("kaizen", help="experiment with a before/after metric")
    p.add_argument("action", choices=("start", "end", "list"))
    p.add_argument("target", nargs="?", default="", help="hypothesis or experiment id")
    p.add_argument("--metric", default="value")
    p.add_argument("--baseline", default="0")
    p.add_argument("--value", default="")
    p.add_argument("--ts", help="inject a UTC timestamp (tests)")
    p.add_argument("--json", action="store_true")

    a = ap.parse_args()
    when = parse_ts(a.ts) if getattr(a, "ts", None) else None

    if a.cmd == "log":
        ev = append(a.type, a.key, a.value, when)
    elif a.cmd == "mode":
        ev = append(f"mode.{a.action}", a.mode, "", when)
        if a.action == "stop":
            raise_milestones()
            raise_stamps()
        else:
            maybe_nudge()
    elif a.cmd in ("done", "reopen"):
        res = set_done(a.task_id, a.cmd == "done", a.project, when)
        if res["changed"]:
            print(f"{'checked' if a.cmd == 'done' else 'unchecked'} {a.task_id}"
                  + (f" in {res['file']}" if res["file"] else " (not in this vault)"))
            if a.cmd == "done" and a.notify:
                notify_close({"id": a.task_id,
                              "text": res["text"] or a.task_id,
                              "project": res["project"] or "inbox"})
            if a.cmd == "done":
                raise_milestones()
                raise_stamps()
        else:
            print(f"{a.task_id} was already {'done' if a.cmd == 'done' else 'open'}"
                  + (f" ({res['file']})" if res["file"] else ""))
        return 0
    elif a.cmd == "role":
        ev = append("role", a.role_id, "", when)
    elif a.cmd == "status":
        return status(a.json)
    elif a.cmd == "rebuild":
        rebuild()
        return 0
    elif a.cmd == "events":
        events = read_events()
        if a.json:
            print(json.dumps(events, indent=2))
        else:
            for e in events:
                print(f"{e['ts']}  {e['device']:<20} {e['type']:<11} {e['key']:<14} {e['value']}")
        return 0
    elif a.cmd == "device":
        print(device())
        return 0
    elif a.cmd == "tasks":
        return list_tasks(False, a.project, a.json)
    elif a.cmd == "scan":
        return list_tasks(a.write_ids, a.project, a.json)
    elif a.cmd == "add":
        task = add_task(" ".join(a.text), a.project, a.link, a.note)
        if task is None:
            return 2
        print(f"{task['id']} added to {task['file']}" +
              (f" · [[{', '.join(task['links'])}]]" if task["links"] else ""))
        return 0
    elif a.cmd == "sync":
        emitted, stats = sync_vault()
        rebuild(quiet=True)
        if emitted:
            raise_milestones()
            raise_stamps()
        print(f"{emitted} new events · {stats['read']} notes read · "
              f"{stats['cached']} cached")
        return 0
    elif a.cmd == "milestones":
        return list_milestones(a.json)
    elif a.cmd == "stamps":
        return list_stamps(a.json)
    elif a.cmd == "claim":
        return claim_stamp(a.stamp_id)
    elif a.cmd == "sprint":
        if a.action == "start":
            return sprint_start([p for p in a.projects.split(",") if p], a.weeks, a.start or "")
        if a.action == "close":
            return sprint_close()
        return sprint_status(a.json)
    elif a.cmd == "review":
        return review(a.days, a.json)
    elif a.cmd == "kaizen":
        if a.action == "start":
            return kaizen_start(a.target, a.metric, a.baseline, when)
        if a.action == "end":
            result = kaizen_end(a.target, a.value, when)
            raise_stamps()
            return result
        return kaizen_list(a.json)
    else:  # pragma: no cover
        return 2

    rebuild(quiet=True)
    print(f"{ev['ts']}  {ev['type']}  {ev['key']}  #{ev['seq']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
