#!/usr/bin/env python3
"""voice-bridge MCP server over stdio, zero dependencies.

Same protocol shape as the Questline server: one JSON-RPC request per line,
stdout reserved for the protocol, diagnostics to stderr. The agent can ask the
user to speak and receive the transcript as a tool result.

Tools: listen, transcribe, last, languages.
"""
import json
import sys

import voicectl

PROTOCOL = "2024-11-05"
LANGUAGES = {
    "es": "Spanish", "en": "English", "pt": "Portuguese", "fr": "French",
    "de": "German", "it": "Italian",
}
TOOLS = [
    {
        "name": "listen",
        "description": "Ask the user to speak, then transcribe with the configured Whisper provider. Returns text, language and duration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "seconds": {"type": "integer", "minimum": 1, "maximum": 60,
                            "description": "recording window in seconds (default 8)"},
                "language": {"type": "string",
                             "description": "ISO-639-1 hint, e.g. es or en (default: configured)"},
            },
        },
    },
    {
        "name": "transcribe",
        "description": "Transcribe an existing WAV file; optional language and vocabulary hint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "language": {"type": "string"},
                "hint": {"type": "string", "description": "up to 224 tokens of vocabulary"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "last",
        "description": "Read the most recent transcript without recording anything.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "languages",
        "description": "List the language codes available for transcription.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "speak",
        "description": "Speak an answer aloud with the configured local Piper voice (Cloudflare is a fallback). Use when the user asks for an audio reply.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "text to synthesize (max 2000 chars)"},
                "language": {"type": "string", "description": "es or en (default: configured)"},
                "play": {"type": "boolean", "description": "play the audio now (default true)"},
            },
            "required": ["text"],
        },
    },
]


def tool_listen(args):
    seconds = int(args.get("seconds") or 8)
    language = str(args.get("language") or "")
    rules = voicectl.load_rules()
    if language:
        rules["stt"]["language"] = language
    result = voicectl.listen(seconds, rules)
    if not result.get("text"):
        raise ValueError("empty transcription: check the microphone and STT credentials")
    return result


def tool_transcribe(args):
    path = str(args.get("path", "")).strip()
    if not path:
        raise ValueError("path is required")
    hint = args.get("hint")
    return voicectl.transcribe_file(path, voicectl.load_rules(),
                                    language=args.get("language"),
                                    hint=str(hint) if hint is not None else None)


def tool_last(_):
    return {"text": voicectl.last()}


def tool_languages(_):
    return {"languages": LANGUAGES, "default": voicectl.load_rules()["stt"].get("language", "es")}


def tool_speak(args):
    text = str(args.get("text", "")).strip()
    if not text:
        raise ValueError("text is required")
    return voicectl.speak(text, voicectl.load_rules(),
                          language=args.get("language"),
                          play=bool(args.get("play", True)))


TOOL_FUNCS = {"listen": tool_listen, "transcribe": tool_transcribe,
              "last": tool_last, "languages": tool_languages, "speak": tool_speak}


def respond(request):
    rid = request.get("id")
    method = request.get("method", "")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "voice-bridge", "version": "0.1.0"}}}
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
                "content": [{"type": "text", "text": json.dumps(
                    result, indent=2, sort_keys=True, ensure_ascii=False)}]}}
        except Exception as exc:  # the protocol must never crash
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": str(exc)}], "isError": True}}
    return {"jsonrpc": "2.0", "id": rid,
            "error": {"code": -32601, "message": f"method not found: {method}"}}


def main():
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
