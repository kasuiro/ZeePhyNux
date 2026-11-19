"""Questline stamp catalog and pure eligibility checks.

24 achievements in three families of eight. A stamp is earned when its
criterion becomes true in the event log; `ql.py` records that as a `stamp`
event. Nothing here writes, renders or notifies.

All code and labels are American English. See docs/subsystem/GIFTS.md.
"""
import json
from datetime import datetime, timezone


def when(ts: str) -> datetime:
    """An event timestamp as a local datetime."""
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc).astimezone()


def number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def experiments(events: list[dict]) -> list[dict]:
    """Merge kaizen start/end events by experiment id."""
    runs: dict[str, dict] = {}
    for ev in events:
        if ev["type"] != "kaizen":
            continue
        try:
            data = json.loads(ev["value"])
        except ValueError:
            continue
        row = runs.setdefault(ev["key"], {"id": ev["key"]})
        row.update({k: v for k, v in data.items() if k != "phase"})
        row[data.get("phase", "start")] = ev["ts"]
    return list(runs.values())


def task_days(events: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ev in events:
        if ev["type"] == "task.done":
            counts[ev["day"]] = counts.get(ev["day"], 0) + 1
    return counts


def iso_weeks(rows: list[dict]) -> set[str]:
    weeks = set()
    for row in rows:
        if row.get("start"):
            year, week, _ = when(row["start"]).isocalendar()
            weeks.add(f"{year}-W{week:02d}")
    return weeks


def context(events: list[dict], state: dict, rules: dict) -> dict:
    return {
        "events": events,
        "state": state,
        "rules": rules,
        "milestones": set(state.get("milestones", [])),
        "starts": [ev for ev in events if ev["type"] == "mode.start"],
        "tasks": task_days(events),
        "kaizen": experiments(events),
    }


def any_milestone(c: dict, prefix: str) -> bool:
    return any(key.startswith(prefix) for key in c["milestones"])


def improvement(row: dict) -> float | None:
    before, after = number(row.get("baseline")), number(row.get("value"))
    return None if before is None or after is None else before - after


# id, name, family, glyph, criterion, predicate
STAMPS = [
    # milestone family
    ("chain-five", "Chain of Five", "milestone", "zoso",
     "Five tasks of one project in a single mode session",
     lambda c: any_milestone(c, "chain:")),
    ("clean-sweep", "Clean Sweep", "milestone", "icarus",
     "A project completed with at least ten tasks",
     lambda c: any_milestone(c, "project:")),
    ("streak-seven", "Seven Days", "milestone", "presence",
     "A seven-day streak",
     lambda c: c["state"].get("streak_days", 0) >= 7),
    ("streak-fourteen", "Fortnight", "milestone", "presence",
     "A fourteen-day streak",
     lambda c: c["state"].get("streak_days", 0) >= 14),
    ("streak-thirty", "Thirty Days", "milestone", "presence",
     "A thirty-day streak",
     lambda c: c["state"].get("streak_days", 0) >= 30),
    ("perfect-week", "Perfect Week", "milestone", "hermit",
     "Seven consecutive qualified days",
     lambda c: any_milestone(c, "week:")),
    ("centurion", "Centurion", "milestone", "coda",
     "One hundred tasks closed",
     lambda c: c["state"].get("tasks_done", 0) >= 100),
    ("fragment-thousand", "Thousand Fragments", "milestone", "airship",
     "One thousand fragments earned",
     lambda c: c["state"].get("fragments", 0) >= 1000),

    # streak family
    ("first-light", "First Light", "streak", "presence",
     "The first qualified day",
     lambda c: c["state"].get("streak_days", 0) >= 1),
    ("warm-up", "Warm Up", "streak", "icarus",
     "Sixty minutes in a mode in one day",
     lambda c: any(day.get("minutes", 0) >=
                   c["rules"].get("points", {}).get("streak_min_minutes", 60)
                   for day in c["state"].get("days", {}).values())),
    ("early-bird", "Early Bird", "streak", "hermit",
     "A mode session started before nine in the morning",
     lambda c: any(when(ev["ts"]).hour < 9 for ev in c["starts"])),
    ("night-owl", "Night Owl", "streak", "hermit",
     "A mode session started after nine at night",
     lambda c: any(when(ev["ts"]).hour >= 21 for ev in c["starts"])),
    ("five-modes", "Five Modes", "streak", "zoso",
     "Five different modes used",
     lambda c: len({ev["key"] for ev in c["starts"]}) >= 5),
    ("all-modes", "All Modes", "streak", "zoso",
     "All seven modes used",
     lambda c: len({ev["key"] for ev in c["starts"]}) >= 7),
    ("weekend-warrior", "Weekend Warrior", "streak", "airship",
     "A mode session on a Saturday or Sunday",
     lambda c: any(when(ev["ts"]).weekday() >= 5 for ev in c["starts"])),
    ("daily-ten", "Ten in a Day", "streak", "coda",
     "Ten tasks closed on one day",
     lambda c: any(count >= 10 for count in c["tasks"].values())),

    # kaizen family
    ("hypothesis", "Hypothesis", "kaizen", "hermit",
     "The first Kaizen experiment started",
     lambda c: any(row.get("start") for row in c["kaizen"])),
    ("measured", "Measured", "kaizen", "presence",
     "A Kaizen experiment measured at the end",
     lambda c: any(row.get("end") for row in c["kaizen"])),
    ("drop-three", "Drop Three", "kaizen", "zoso",
     "An experiment improved its metric by at least three",
     lambda c: any((improvement(row) or 0) >= 3 for row in c["kaizen"])),
    ("zero-open", "Zero Open", "kaizen", "coda",
     "An open-task experiment ended at zero",
     lambda c: any(row.get("metric", "").lower() == "open"
                   and number(row.get("value")) == 0 for row in c["kaizen"])),
    ("time-saved", "Time Saved", "kaizen", "icarus",
     "An experiment saved at least twenty-five minutes",
     lambda c: any("minute" in row.get("metric", "").lower()
                   and (improvement(row) or 0) >= 25 for row in c["kaizen"])),
    ("repeat-offender", "Repeat Offender", "kaizen", "zoso",
     "Three Kaizen experiments started",
     lambda c: sum(1 for row in c["kaizen"] if row.get("start")) >= 3),
    ("chain-of-custody", "Chain of Custody", "kaizen", "presence",
     "Five Kaizen experiments measured",
     lambda c: sum(1 for row in c["kaizen"] if row.get("end")) >= 5),
    ("weekly-cadence", "Weekly Cadence", "kaizen", "airship",
     "Experiments started in three different ISO weeks",
     lambda c: len(iso_weeks(c["kaizen"])) >= 3),
]

BY_ID = {item[0]: item for item in STAMPS}
FAMILIES = sorted({item[2] for item in STAMPS})


def candidates(events: list[dict], state: dict, rules: dict) -> list[dict]:
    """Stamps whose criterion is true and that are not in the log yet."""
    seen = {ev["key"] for ev in events if ev["type"] == "stamp"}
    c = context(events, state, rules)
    out = []
    for sid, name, family, glyph, criterion, test in STAMPS:
        if sid in seen:
            continue
        try:
            earned = bool(test(c))
        except (KeyError, TypeError, ValueError):
            earned = False
        if earned:
            out.append({"id": sid, "name": name, "family": family,
                        "glyph": glyph, "criterion": criterion, "gift": sid})
    return out
