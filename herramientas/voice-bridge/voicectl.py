#!/usr/bin/env python3
"""voice-bridge control CLI: capture, transcribe and deliver spoken input.

Zero third-party dependencies. The API key is read from GROQ_API_KEY, from the
file named by VOICE_KEY_FILE, or from ~/.config/voice-bridge/key (0600); this
module never writes the key to disk.

    voicectl.py start          # push-to-talk key down
    voicectl.py stop           # key up: transcribe + deliver
    voicectl.py listen --seconds 5
    voicectl.py transcribe FILE
    voicectl.py last
"""
import argparse
import json
import os
import pathlib
import select
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave

ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_RULES = ROOT / "rules.toml"
DEFAULT_KEY_FILE = pathlib.Path.home() / ".config/voice-bridge/key"


def load_rules(path=DEFAULT_RULES):
    import tomllib
    with open(path, "rb") as handle:
        return tomllib.load(handle)


def state_dir(rules):
    value = rules.get("paths", {}).get("state", "")
    path = pathlib.Path(value).expanduser() if value else \
        pathlib.Path.home() / ".local/state/voice-bridge"
    path.mkdir(parents=True, exist_ok=True)
    return path


def api_key():
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if key:
        return key
    key_file = os.environ.get("VOICE_KEY_FILE", "").strip()
    if key_file:
        path = pathlib.Path(key_file).expanduser()
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    path = pathlib.Path(DEFAULT_KEY_FILE).expanduser()
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""


def key_ready():
    return bool(api_key())


def wav_seconds(path):
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate() or 16000
            return round(frames / rate, 2)
    except Exception:
        return 0.0


def _multipart(path, fields):
    boundary = "----voicebridge-boundary"
    chunks = []
    for name, value in fields.items():
        chunks.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
            f"{value}\r\n".encode("utf-8")
        )
    chunks.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"capture.wav\"\r\nContent-Type: audio/wav\r\n\r\n".encode("utf-8")
    )
    chunks.append(pathlib.Path(path).read_bytes())
    chunks.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def transcribe_file(path, rules=None, language=None, hint=None, mock=False):
    """Return {text, language, model, seconds} using the Groq STT endpoint."""
    rules = rules or load_rules()
    stt = rules["stt"]
    lang = language or stt.get("language", "es")
    if mock:
        return {"text": "mock transcription", "language": lang,
                "model": "mock", "seconds": wav_seconds(path)}
    key = api_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set (or VOICE_KEY_FILE is missing)")
    payload = pathlib.Path(path).read_bytes()
    if len(payload) > 25 * 1024 * 1024:
        raise RuntimeError("audio exceeds the 25 MB free-tier upload limit")
    body, content_type = _multipart(path, {
        "model": stt.get("model", "whisper-large-v3-turbo"),
        "language": lang,
        "prompt": hint if hint is not None else stt.get("hint", ""),
    })
    request = urllib.request.Request(
        stt.get("endpoint", "https://api.groq.com/openai/v1/audio/transcriptions"),
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": content_type},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=int(stt.get("timeout", 30))) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        retry = exc.headers.get("retry-after", "?") if exc.headers else "?"
        raise RuntimeError(f"Groq HTTP {exc.code} (retry-after: {retry}s)") from exc
    return {"text": (result.get("text") or "").strip(), "language": lang,
            "model": stt.get("model", ""), "seconds": wav_seconds(path)}


def _comm(pid):
    try:
        return pathlib.Path(f"/proc/{pid}/comm").read_text().strip()
    except OSError:
        return ""


def _kitty_master():
    """Path to the PTY master of the active (or any) kitty window."""
    candidates = []
    try:
        info = json.loads(subprocess.run(
            ["hyprctl", "activewindow", "-j"], capture_output=True,
            text=True, timeout=3).stdout or "{}")
        if info.get("pid"):
            candidates.append(int(info["pid"]))
    except Exception:
        pass
    for proc in pathlib.Path("/proc").iterdir():
        if proc.name.isdigit() and _comm(proc.name) == "kitty":
            candidates.append(int(proc.name))
    for pid in candidates:
        fd_dir = pathlib.Path(f"/proc/{pid}/fd")
        try:
            for fd in fd_dir.iterdir():
                try:
                    if os.readlink(fd) == "/dev/ptmx":
                        return str(fd)
                except OSError:
                    continue
        except OSError:
            continue
    return None


def _write_pty(text, rules):
    target = _kitty_master()
    if not target:
        return False
    fd = os.open(target, os.O_WRONLY | os.O_NONBLOCK)
    data = (text + rules.get("deliver", {}).get("suffix", "\r")).encode("utf-8")
    try:
        while data:
            _, writable, _ = select.select([], [fd], [], 2)
            if not writable:
                raise RuntimeError("PTY write timed out")
            written = os.write(fd, data)
            data = data[written:]
    finally:
        os.close(fd)
    return True


def deliver(text, rules):
    """Return the backend actually used."""
    backend = rules.get("deliver", {}).get("backend", "none")
    if not text or backend == "none":
        return backend
    if backend == "tty":
        try:
            if _write_pty(text, rules):
                return "tty"
        except Exception:
            pass
        backend = "clipboard"
    if backend == "clipboard":
        subprocess.run(["wl-copy"], input=text.encode("utf-8"), check=False)
        return "clipboard"
    return "none"


def notify(message):
    try:
        subprocess.run(["notify-send", "-a", "voice-bridge", message],
                       check=False, timeout=3)
    except Exception:
        pass


def start(rules=None):
    rules = rules or load_rules()
    state = state_dir(rules)
    pid_file = state / "recording.pid"
    if pid_file.exists():
        old_pid = int(pid_file.read_text())
        try:
            os.kill(old_pid, 0)
            return {"recording": True, "already": True, "pid": old_pid}
        except ProcessLookupError:
            pid_file.unlink(missing_ok=True)
    rec = rules["record"]
    wav = state / "capture.wav"
    cmd = ["pw-record", "--rate", str(rec.get("rate", 16000)),
           "--channels", str(rec.get("channels", 1)),
           "--format", str(rec.get("format", "s16")), str(wav)]
    with open(state / "recorder.log", "ab") as log:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=log,
                                start_new_session=True)
    pid_file.write_text(str(proc.pid))
    notify("Recording… release SUPER+ALT+SHIFT+V to send")
    return {"recording": True, "already": False, "pid": proc.pid}


def stop(rules=None, mock=False):
    rules = rules or load_rules()
    state = state_dir(rules)
    pid_file = state / "recording.pid"
    if not pid_file.exists():
        return {"error": "not recording"}
    pid = int(pid_file.read_text())
    try:
        os.kill(pid, signal.SIGINT)
    except ProcessLookupError:
        pass
    for _ in range(50):
        try:
            os.kill(pid, 0)
            time.sleep(0.1)
        except ProcessLookupError:
            break
    pid_file.unlink(missing_ok=True)
    wav = state / "capture.wav"
    result = transcribe_file(wav, rules, mock=mock)
    (state / "last.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (state / "last.txt").write_text(result["text"])
    result["delivered_via"] = deliver(result["text"], rules)
    notify(result["text"][:120] or "(empty transcription)")
    return result


def listen(seconds, rules=None, mock=False):
    rules = rules or load_rules()
    start(rules)
    time.sleep(max(1, min(int(seconds), int(rules["record"].get("max_seconds", 60)))))
    return stop(rules, mock=mock)


def last(rules=None):
    rules = rules or load_rules()
    path = state_dir(rules) / "last.txt"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def status(rules=None):
    rules = rules or load_rules()
    state = state_dir(rules)
    return {"state": str(state), "recording": (state / "recording.pid").exists(),
            "key_ready": key_ready(),
            "last": last(rules)[:200],
            "model": rules["stt"].get("model", ""),
            "language": rules["stt"].get("language", "es"),
            "deliver": rules["deliver"].get("backend", "none")}


def main(argv=None):
    parser = argparse.ArgumentParser(description="voice-bridge control CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("start", help="start recording")
    sub.add_parser("stop", help="stop, transcribe and deliver")
    p_listen = sub.add_parser("listen", help="record for N seconds and deliver")
    p_listen.add_argument("--seconds", type=int, default=5)
    p_transcribe = sub.add_parser("transcribe", help="transcribe an existing WAV")
    p_transcribe.add_argument("file")
    p_transcribe.add_argument("--language", default=None)
    sub.add_parser("last", help="print the last transcript")
    sub.add_parser("status", help="show configuration status")
    for name in ("start", "stop", "listen", "transcribe"):
        sub.choices[name].add_argument("--mock", action="store_true",
                                       help="skip the network call (tests)")
    args = parser.parse_args(argv)
    rules = load_rules()
    try:
        if args.cmd == "start":
            result = start(rules)
        elif args.cmd == "stop":
            result = stop(rules, args.mock)
        elif args.cmd == "listen":
            result = listen(args.seconds, rules, args.mock)
        elif args.cmd == "transcribe":
            result = transcribe_file(args.file, rules, args.language, mock=args.mock)
        elif args.cmd == "last":
            print(last(rules))
            return 0
        else:
            result = status(rules)
    except Exception as exc:
        message = f"voice-bridge: {exc}"
        print(message, file=sys.stderr)
        notify(message[:120])
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
