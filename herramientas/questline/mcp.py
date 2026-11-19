#!/usr/bin/env python3
"""Questline MCP server over stdio, zero dependencies.

One JSON-RPC request per line in, one response per line out. The process lives
only as long as the client keeps it open: no socket, no port, no daemon, no
network. stdout is reserved for the protocol; diagnostics go to stderr.

    python3 mcp.py

Tools: board, status, done, add_task. See docs/subsystem/MCP.md.
"""
import json
import sys

import ql

PROTOCOL = "2024-11-05"
TOOLS = [
    {
        "name": "board",
        "description": "Read the vault board: open and done cards, sprint, gifts.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "status",
        "description": "Read the projected state and the stamp catalog status.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "done",
        "description": "Close a vault task by block id. Idempotent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "task id, e.g. ql-a1b2c3"},
                "project": {"type": "string", "description": "optional project tag"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "add_task",
        "description": "Append a task to a vault note with a stable block id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "project": {"type": "string"},
                "links": {"type": "array", "items": {"type": "string"},
                          "description": "Obsidian wikilink targets"},
                "note": {"type": "string", "description": "note inside the vault"},
            },
            "required": ["text"],
        },
    },
]


def card(task: dict) -> dict:
    return {
        "id": task["id"],
        "text": ql.plain(task["text"]),
        "project": task.get("project", ""),
        "links": task.get("links", []),
        "done": task.get("done", False),
        "file": task.get("file", ""),
        "line": task.get("line", 0),
    }


def tool_board(_: dict) -> dict:
    files, _stats = ql.scan_vault(write_ids=False)
    ql.save_cache(files)
    tasks = ql.all_tasks(files)
    state = ql.fold(ql.read_events(), ql.load_rules())
    sprint = ql.sprint_load()
    open_cards = [card(t) for t in tasks if not t["done"]]
    done_cards = [card(t) for t in tasks if t["done"]]
    window = None
    if sprint:
        by_id = {t["id"]: t for t in tasks}
        done, pending = ql.sprint_counts(sprint, by_id)
        day, days = ql.sprint_progress(sprint)
        window = {"id": sprint.get("id"), "status": sprint.get("status"),
                  "day": day, "days": days, "done": done, "pending": pending}
    return {
        "open": open_cards,
        "done": done_cards,
        "sprint": window,
        "fragments": state.get("fragments", 0),
        "streak": state.get("streak_days", 0),
        "gifts": state.get("gifts_claimed", []),
        "device": state.get("device", ""),
    }


def tool_status(_: dict) -> dict:
    rules = ql.load_rules()
    state = ql.fold(ql.read_events(), rules)
    stamps = sorted(ql.stamp_rows(ql.read_events()).values(),
                    key=lambda r: (r["family"], r["id"]))
    return {
        "device": state.get("device", ""),
        "role": state.get("role", ""),
        "fragments": state.get("fragments", 0),
        "breakdown": state.get("breakdown", {}),
        "streak": state.get("streak_days", 0),
        "tasks_done": state.get("tasks_done", 0),
        "gifts": state.get("gifts_claimed", []),
        "stamps": {"earned": len(stamps),
                   "claimed": sum(1 for row in stamps if row["claimed"]),
                   "total": len(ql.stamp_catalog.STAMPS)},
    }


def tool_done(args: dict) -> dict:
    tid = str(args.get("id", "")).strip()
    if not tid:
        raise ValueError("id is required")
    result = ql.set_done(tid, True, str(args.get("project", "")), None)
    if not result["changed"]:
        return {"id": tid, "already_done": True}
    ql.raise_milestones()
    ql.raise_stamps()
    return {"id": tid, "already_done": False,
            "project": result.get("project", ""), "file": result.get("file", "")}


def tool_add_task(args: dict) -> dict:
    text = str(args.get("text", "")).strip()
    if not text:
        raise ValueError("text is required")
    links = args.get("links") or []
    if isinstance(links, str):
        links = [links]
    task = ql.add_task(text, str(args.get("project", "")),
                       [str(value) for value in links],
                       str(args.get("note") or "Inbox.md"))
    if task is None:
        raise ValueError("the task could not be written to the vault")
    return task


TOOL_FUNCS = {"board": tool_board, "status": tool_status,
              "done": tool_done, "add_task": tool_add_task}


def respond(request: dict) -> dict | None:
    rid = request.get("id")
    method = request.get("method", "")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "questline", "version": "1.0"}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = request.get("params") or {}
        name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            if name not in TOOL_FUNCS:
                raise ValueError(f"unknown tool: {name}")
            result = TOOL_FUNCS[name](args)
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": json.dumps(result, indent=2,
                                                                sort_keys=True)}]}}
        except Exception as exc:  # noqa: BLE001 - protocol must never crash
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": str(exc)}], "isError": True}}
    return {"jsonrpc": "2.0", "id": rid,
            "error": {"code": -32601, "message": f"method not found: {method}"}}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError as exc:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None,
                                         "error": {"code": -32700,
                                                   "message": str(exc)}}) + "\n")
            sys.stdout.flush()
            continue
        response = respond(request)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
