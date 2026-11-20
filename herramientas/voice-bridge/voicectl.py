#!/usr/bin/env python3
"""voice-bridge control CLI: capture, transcribe and deliver spoken input.

Zero third-party dependencies on the host. The default STT provider is local
faster-whisper running in a dedicated venv under ~/.local/state/voice-bridge/;
Vosk in Docker remains available as an alternative. Credentials are only needed
for the optional cloud providers and come from env vars or 0600 files in
~/.config/voice-bridge/: key (Groq), cf_token and cf_account (Cloudflare).
No secret is ever written by this module.

Set [stt].provider in rules.toml to "whisper", "vosk", "cloudflare" or "groq".

    voicectl.py start          # push-to-talk key down
    voicectl.py stop           # key up: transcribe + deliver
    voicectl.py listen --seconds 5
    voicectl.py transcribe FILE
    voicectl.py last
    voicectl.py wake-start|wake-stop   # session-scoped hands-free trigger
    voicectl.py wake-dictate           # said phrase: end-on-silence dictation
"""
import argparse
import json
import os
import pathlib
import re
import select
import shutil
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
DEFAULT_CF_TOKEN_FILE = pathlib.Path.home() / ".config/voice-bridge/cf_token"
DEFAULT_CF_ACCOUNT_FILE = pathlib.Path.home() / ".config/voice-bridge/cf_account"


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


RETRYABLE_HTTP = frozenset({429, 500, 502, 503, 504})


def retry_settings(rules=None):
    """Bounded backoff for transient provider errors (429 and 5xx)."""
    api = (rules or {}).get("api", {})
    return (
        max(0, int(api.get("retry_attempts", 3))),
        max(0.1, float(api.get("retry_base_seconds", 2))),
        max(1.0, float(api.get("retry_max_seconds", 8))),
    )


def _retry_delay(exc, attempt, base, cap):
    header = exc.headers.get("Retry-After", "") if exc.headers else ""
    try:
        seconds = float(header)
    except (TypeError, ValueError):
        seconds = base * (2 ** attempt)
    return max(0.0, min(seconds, cap))


def http_post(request_factory, timeout, rules=None, label="API"):
    """POST with backoff on rate limits, transient 5xx and network errors."""
    attempts, base, cap = retry_settings(rules)
    for attempt in range(attempts + 1):
        try:
            with urllib.request.urlopen(request_factory(), timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_HTTP or attempt >= attempts:
                retry = exc.headers.get("Retry-After", "?") if exc.headers else "?"
                raise RuntimeError(
                    f"{label} HTTP {exc.code}: {exc.reason} (retry-after: {retry}s)"
                ) from exc
            delay = _retry_delay(exc, attempt, base, cap)
        except urllib.error.URLError as exc:
            if attempt >= attempts:
                raise RuntimeError(f"{label} network error: {exc.reason}") from exc
            delay = min(base * (2 ** attempt), cap)
        time.sleep(delay)
    raise RuntimeError(f"{label} request failed after {attempts + 1} attempts")


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


def _credential(env_name, default_file):
    value = os.environ.get(env_name, "").strip()
    if value:
        return value
    path = pathlib.Path(default_file).expanduser()
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""


def cloudflare_credentials():
    return (_credential("CLOUDFLARE_API_TOKEN", DEFAULT_CF_TOKEN_FILE),
            _credential("CF_ACCOUNT_ID", DEFAULT_CF_ACCOUNT_FILE))


def credential_ready(rules=None):
    rules = rules or load_rules()
    name = provider_config(rules["stt"])["name"]
    if name in ("whisper", "vosk"):
        # Local STT needs no credentials; runtime availability is reported by
        # status() instead of being treated as a secret.
        return True
    if name == "cloudflare":
        return all(cloudflare_credentials())
    return key_ready()


def provider_config(stt):
    name = stt.get("provider", "groq")
    config = dict(stt.get("providers", {}).get(name, {}))
    config.setdefault("model", stt.get("model", ""))
    config.setdefault("endpoint", stt.get("endpoint", ""))
    config["name"] = name
    config["language"] = stt.get("language", "es")
    config["timeout"] = int(stt.get("timeout", 30))
    config["hint"] = stt.get("hint", "")
    return config


def wav_seconds(path):
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate() or 16000
            if frames:
                return round(frames / rate, 2)
    except Exception:
        pass
    # pw-record may not have finalised the header when we read it. Fall back to
    # the byte count for our fixed 16 kHz / mono / s16 capture format.
    try:
        size = pathlib.Path(path).stat().st_size
        return round(max(0, size - 44) / (16000 * 2), 2)
    except OSError:
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


SPANISH_MARKERS = re.compile(
    r"[¿¡ñáéíóúü]|\b(?:el|la|los|las|de|del|que|y|en|un|una|es|no|con|para|"
    r"por|pero|muy|también|hola|gracias|necesito|quiero|puede|puedes|estamos|"
    r"mensaje|listo|sonríe)\b",
    re.IGNORECASE,
)
ENGLISH_MARKERS = re.compile(
    r"\b(?:the|and|is|are|you|for|with|this|that|have|need|want|hello|thanks|"
    r"thank|please|message|yes|ready|smile|okay|ok|we|it|to|of|in)\b",
    re.IGNORECASE,
)


def detect_language(text, default="es"):
    """Best-effort es/en detection for reporting and voice selection."""
    sample = str(text or "")[:2000]
    spanish = len(SPANISH_MARKERS.findall(sample))
    english = len(ENGLISH_MARKERS.findall(sample))
    if spanish > english:
        return "es"
    if english > spanish:
        return "en"
    return default


def transcribe_file(path, rules=None, language=None, hint=None, mock=False):
    """Return {text, language, model, seconds} using the configured provider."""
    rules = rules or load_rules()
    provider = provider_config(rules["stt"])
    lang = language or provider["language"]
    if mock:
        return {"text": "mock transcription",
                "language": "es" if lang == "auto" else lang,
                "model": "mock", "seconds": wav_seconds(path)}
    if provider["name"] == "whisper":
        return _transcribe_whisper(path, provider, lang)
    if provider["name"] == "vosk":
        return _transcribe_vosk(path, provider, lang)
    if provider["name"] == "cloudflare":
        return _transcribe_cloudflare(path, provider, hint, lang, rules)
    return _transcribe_groq(path, provider, "es" if lang == "auto" else lang,
                            hint, rules)


def _read_audio(path):
    payload = pathlib.Path(path).read_bytes()
    if len(payload) > 25 * 1024 * 1024:
        raise RuntimeError("audio exceeds the 25 MB upload limit")
    return payload


def _transcribe_groq(path, provider, lang, hint, rules=None):
    key = api_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set (or VOICE_KEY_FILE is missing)")
    body, content_type = _multipart(path, {
        "model": provider["model"],
        "language": lang,
        "prompt": hint if hint is not None else provider["hint"],
    })
    request = urllib.request.Request(
        provider["endpoint"], data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": content_type},
        method="POST",
    )
    raw = http_post(lambda: request, provider["timeout"], rules, "Groq STT")
    result = json.loads(raw)
    return {"text": (result.get("text") or "").strip(), "language": lang,
            "model": provider["model"], "seconds": wav_seconds(path)}


def _transcribe_whisper(path, provider, lang="es"):
    """One-shot local STT: run faster-whisper in its venv, read JSON."""
    python = pathlib.Path(str(provider.get("python", ""))).expanduser()
    if not python.is_file():
        raise RuntimeError(
            "Whisper venv is missing: run the install script or set "
            "[stt.providers.whisper].python in rules.toml")
    script = pathlib.Path(str(provider.get("script") or
                              (ROOT / "whisper_transcribe.py"))).expanduser()
    if not script.is_file():
        raise RuntimeError("whisper_transcribe.py is missing from the module")
    download_root = str(pathlib.Path(str(provider.get("hf_home", ""))).expanduser()) \
        if provider.get("hf_home") else ""
    env = os.environ.copy()
    env.update({
        "WHISPER_MODEL": str(provider.get("model", "base")),
        "WHISPER_COMPUTE_TYPE": str(provider.get("compute_type", "int8")),
        "WHISPER_CPU_THREADS": str(provider.get("cpu_threads", 4)),
        "WHISPER_BEAM_SIZE": str(provider.get("beam_size", 5)),
        "WHISPER_LANGUAGE": lang,
        "WHISPER_VAD": "0" if provider.get("vad_filter", True) is False else "1",
        "WHISPER_DOWNLOAD_ROOT": download_root,
        "HF_HOME": download_root or env.get("HF_HOME", ""),
    })
    cmd = [str(python), str(script), str(pathlib.Path(path).resolve())]
    timeout = int(provider.get("timeout", 120))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              env=env)
    except FileNotFoundError as exc:
        raise RuntimeError("Whisper Python interpreter is not executable") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Whisper STT timed out after {timeout}s") from exc
    if proc.returncode != 0:
        detail = [line for line in (proc.stderr or "").splitlines() if line.strip()]
        raise RuntimeError("Whisper STT failed: " +
                           (detail[-1] if detail else f"exit {proc.returncode}"))
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Whisper STT returned invalid JSON") from exc
    text = str(result.get("text", "")).strip()
    reported = str(result.get("language") or "").lower()[:2]
    if reported not in ("es", "en"):
        reported = detect_language(text, "es") if lang == "auto" else lang[:2]
    return {"text": text, "language": reported,
            "model": result.get("model") or provider.get("model", "base"),
            "seconds": wav_seconds(path)}


def _transcribe_vosk(path, provider, lang="es"):
    """One-shot local STT: mount the WAV into a Vosk container, read JSON."""
    image = provider.get("image_en") if lang == "en" else provider.get("image")
    if not image:
        raise RuntimeError("Vosk image is not configured in rules.toml")
    if not shutil.which("docker"):
        raise RuntimeError("Docker is required for the local Vosk provider")
    wav = str(pathlib.Path(path).resolve())
    cmd = ["docker", "run", "--rm", "--network",
           provider.get("network", "none"), "-v", f"{wav}:/in.wav:ro", image]
    timeout = int(provider.get("timeout", 60))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise RuntimeError("Docker is required for the local Vosk provider") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Vosk STT timed out after {timeout}s") from exc
    if proc.returncode != 0:
        detail = [line for line in (proc.stderr or "").splitlines() if line.strip()]
        raise RuntimeError("Vosk STT failed: " +
                           (detail[-1] if detail else f"exit {proc.returncode}"))
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Vosk STT returned invalid JSON") from exc
    text = str(result.get("text", "")).strip()
    reported = detect_language(text, "es") if lang == "auto" else lang
    model = provider.get("model_en") if reported == "en" else provider.get("model")
    return {"text": text, "language": reported, "model": model,
            "seconds": wav_seconds(path)}


def _transcribe_cloudflare(path, provider, hint, lang="es", rules=None):
    # Cloudflare Whisper takes raw audio and auto-detects the language; the
    # vocabulary hint is a Groq-only feature and is intentionally ignored.
    del hint
    token, account = cloudflare_credentials()
    if not token or not account:
        raise RuntimeError(
            "Cloudflare credentials missing: CLOUDFLARE_API_TOKEN / CF_ACCOUNT_ID "
            "or ~/.config/voice-bridge/{cf_token,cf_account}")
    endpoint = provider["endpoint"].format(account_id=account, model=provider["model"])
    request = urllib.request.Request(
        endpoint, data=_read_audio(path),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "audio/wav"},
        method="POST",
    )
    raw = http_post(lambda: request, provider["timeout"], rules, "Cloudflare STT")
    result = json.loads(raw)
    if result.get("success") is False:
        detail = ", ".join(str(item.get("message", item))
                           for item in result.get("errors", []))
        raise RuntimeError(f"Cloudflare Workers AI error: {detail or 'unknown'}")
    text = (result.get("result", {}).get("text") or "").strip()
    reported = detect_language(text, "es") if lang == "auto" else lang
    return {"text": text, "language": reported, "model": provider["model"],
            "seconds": wav_seconds(path)}


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
    """Return the backend actually used.

    VOICE_DELIVER_BACKEND overrides the configured backend so callers such as
    the TUI plugin can own the delivery path without typing into the PTY.
    """
    backend = os.environ.get("VOICE_DELIVER_BACKEND") or \
        rules.get("deliver", {}).get("backend", "none")
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


def _live_pid(pid_file):
    """Return the live PID in a pid file, or None after cleaning a stale one."""
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        pid_file.unlink(missing_ok=True)
        return None


def wake_start(rules=None):
    """Start the session-scoped wake listener. No socket, no systemd unit."""
    rules = rules or load_rules()
    config = rules.get("wake", {})
    if not config.get("enabled", True):
        return {"listening": False, "error": "wake is disabled in rules.toml"}
    state = state_dir(rules)
    pid_file = state / "wake.pid"
    existing = _live_pid(pid_file)
    if existing is not None:
        return {"listening": True, "already": True, "pid": existing}
    provider = rules.get("stt", {}).get("providers", {}).get("whisper", {})
    python = pathlib.Path(str(provider.get("python", ""))).expanduser()
    if not python.is_file():
        raise RuntimeError(
            "Whisper venv is missing: run the install script or set "
            "[stt.providers.whisper].python in rules.toml")
    script = ROOT / "wake_listener.py"
    if not script.is_file():
        raise RuntimeError("wake_listener.py is missing from the module")
    cmd = [str(python), str(script), "--config", str(DEFAULT_RULES)]
    with open(state / "wake.log", "ab") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL,
                                start_new_session=True)
    pid_file.write_text(str(proc.pid))
    return {"listening": True, "already": False, "pid": proc.pid,
            "phrases": list(config.get("phrases") or ["oye zeep",
                                                      "oye linux zeep"])}


def wake_stop(rules=None):
    """Stop the session listener and leave no pid file or child behind."""
    rules = rules or load_rules()
    pid_file = state_dir(rules) / "wake.pid"
    pid = _live_pid(pid_file)
    if pid is None:
        return {"listening": False, "already": True}
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    for _ in range(30):
        try:
            os.kill(pid, 0)
            time.sleep(0.1)
        except ProcessLookupError:
            break
    pid_file.unlink(missing_ok=True)
    still_running = False
    try:
        os.kill(pid, 0)
        still_running = True
    except ProcessLookupError:
        pass
    return {"listening": still_running, "already": False, "pid": pid}


def wake_dictate(rules=None, mock=False):
    """Dictation after a wake phrase: end on silence, never exceed a hard cap.

    Uses its own short-lived raw recorder; it does not touch recording.pid and
    always terminates the child, even on timeout or error.
    """
    rules = rules or load_rules()
    config = rules.get("wake", {})
    rec = rules.get("record", {})
    state = state_dir(rules)
    if config.get("confirm", True):
        try:
            speak(str(config.get("confirm_text", "Escuchando")), rules)
        except Exception as exc:  # a missing voice must not block dictation
            notify(f"voice-bridge: confirmación no disponible: {exc}"[:120])
    rate = int(rec.get("rate", 16000))
    chunk_bytes = rate * 2 // 10
    cmd = ["pw-record",
           "--rate", str(rate),
           "--channels", str(rec.get("channels", 1)),
           "--format", str(rec.get("format", "s16")),
           "-", "-a"]
    log = open(state / "wake-dictate.log", "ab")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=log,
                            start_new_session=True)
    pcm = bytearray()
    heard = False
    timed_out = False
    print(json.dumps({"event": "dictate-start",
                      "cap_seconds": float(config.get("dictate_max_seconds", 30))}),
          flush=True)
    try:
        from wake_listener import NoiseAwareSplitter
        splitter = NoiseAwareSplitter(
            rate=rate,
            threshold=float(config.get("energy_threshold", 300)),
            min_seconds=float(config.get("dictate_min_seconds", 0.5)),
            max_seconds=float(config.get("dictate_max_seconds", 30)),
            silence_timeout=float(config.get("dictate_silence_timeout", 1.2)),
            pad_seconds=0.0,
            factor=float(config.get("noise_factor", 2.0)),
        )
        deadline = time.monotonic() + float(config.get("dictate_max_seconds", 30))
        while time.monotonic() < deadline:
            readable, _, _ = select.select([proc.stdout], [], [], 0.2)
            if not readable:
                if proc.poll() is not None:
                    break
                continue
            chunk = proc.stdout.read(chunk_bytes)
            if not chunk:
                break
            done = splitter.feed(chunk)
            if splitter.rms(chunk) >= splitter.threshold:
                heard = True
            pcm.extend(chunk)
            if done:
                break
        else:
            timed_out = True
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        if proc.stdout is not None:
            proc.stdout.close()
        log.close()
    if timed_out:
        if pcm:
            with wave.open(str(state / "wake-timeout.wav"), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(rate)
                handle.writeframes(bytes(pcm))
        message = "Dictado cancelado: tiempo límite alcanzado"
        notify(message)
        return {"error": message, "timed_out": True,
                "captured_seconds": round(len(pcm) / (rate * 2), 2),
                "heard": heard}
    if not heard or not pcm:
        return {"text": "", "delivered_via": "none", "seconds": 0.0}
    wav = state / "capture.wav"
    with wave.open(str(wav), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(pcm))
    result = transcribe_file(wav, rules, mock=mock)
    (state / "last.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2))
    (state / "last.txt").write_text(result["text"])
    result["delivered_via"] = deliver(result["text"], rules)
    notify(result["text"][:120] or "(empty transcription)")
    return result


def speak(text, rules=None, language=None, play=True):
    """Synthesize a spoken reply locally with Piper, or via Cloudflare."""
    rules = rules or load_rules()
    content = str(text).strip()
    if not content:
        raise ValueError("text is required")
    tts = rules.get("tts", {})
    voice = rules.get("voice", {})
    limit = int(tts.get("max_chars", 2000))
    if len(content) > limit:
        raise ValueError(f"text too long ({len(content)} > {limit} characters)")
    configured = str(
        language or voice.get("language") or rules["stt"].get("language", "es")
    ).lower()
    lang = (detect_language(content, "es") if configured.startswith("auto")
            else configured[:2])
    if lang not in ("es", "en"):
        lang = "es"
    provider = str(tts.get("provider", "piper")).lower()
    if provider == "piper":
        return _speak_piper(content, lang, rules, tts, voice, play)
    if provider == "cloudflare":
        return _speak_cloudflare(content, lang, rules, tts, voice, play)
    raise RuntimeError(f"Unknown TTS provider: {provider}")


def _speak_finish(content, lang, path, provider, model, speaker, rules,
                  tts, voice, play):
    """Apply the optional rate change, play the WAV/MP3 and build the result."""
    audio = path.read_bytes()
    rate = float(voice.get("rate", 1.0))
    if not 0.5 <= rate <= 2.0:
        raise ValueError("voice.rate must be between 0.5 and 2.0")
    if rate != 1.0:
        adjusted = path.with_suffix(f".rate{path.suffix}")
        subprocess.run(
            [voice.get("ffmpeg", "ffmpeg"), "-y", "-loglevel", "error",
             "-i", str(path), "-filter:a", f"atempo={rate}", str(adjusted)],
            check=True, capture_output=True, timeout=60,
        )
        adjusted.replace(path)
        audio = path.read_bytes()
    played = False
    if play:
        player = tts.get("player", "pw-play")
        try:
            subprocess.run([player, str(path)], check=True, capture_output=True,
                           timeout=60)
            played = True
        except (OSError, subprocess.SubprocessError) as exc:
            notify(f"voice-bridge: audio saved but playback failed: {exc}")
    return {"text": content[:200], "language": lang, "provider": provider,
            "model": model, "speaker": speaker, "rate": rate,
            "path": str(path), "bytes": len(audio), "played": played}


def _speak_piper(content, lang, rules, tts, voice, play):
    """One-shot local TTS: piper-tts in its venv writes a WAV, then we play it."""
    cfg = tts.get("providers", {}).get("piper", {})
    python = pathlib.Path(str(cfg.get("python", ""))).expanduser()
    if not python.is_file():
        raise RuntimeError(
            "Piper venv is missing: run tools/install-piper.sh or set "
            "[tts.providers.piper].python in rules.toml")
    data_dir = pathlib.Path(str(cfg.get("data_dir", ""))).expanduser()
    if not data_dir.is_dir():
        raise RuntimeError("Piper voice directory is missing: " + str(data_dir))
    voice_name = cfg.get(f"voice_{lang}", cfg.get("voice_es"))
    if not voice_name:
        raise RuntimeError(f"Piper voice for {lang} is not configured")
    model_file = data_dir / f"{voice_name}.onnx"
    config_file = data_dir / f"{voice_name}.onnx.json"
    if not model_file.is_file() or not config_file.is_file():
        raise RuntimeError(f"Piper voice files are missing for {voice_name}")
    path = state_dir(rules) / "reply.wav"
    cmd = [str(python), "-m", "piper", "--data-dir", str(data_dir),
           "-m", str(voice_name), "-f", str(path), "--", content]
    timeout = int(cfg.get("timeout", 60))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise RuntimeError("Piper Python interpreter is not executable") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Piper TTS timed out after {timeout}s") from exc
    if proc.returncode != 0:
        detail = [line for line in (proc.stderr or "").splitlines() if line.strip()]
        raise RuntimeError("Piper TTS failed: " +
                           (detail[-1] if detail else f"exit {proc.returncode}"))
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("Piper TTS returned no audio")
    return _speak_finish(content, lang, path, "piper", "piper-tts",
                         str(voice_name), rules, tts, voice, play)


def _speak_cloudflare(content, lang, rules, tts, voice, play):
    """Cloudflare Aura-2 fallback: MP3 synthesis plus local playback."""
    model = tts.get(f"model_{lang}", "@cf/deepgram/aura-2-es")
    speaker = voice.get(
        f"speaker_{lang}",
        tts.get(f"speaker_{lang}", tts.get("speaker", "aquila")),
    )
    token, account = cloudflare_credentials()
    if not token or not account:
        raise RuntimeError(
            "Cloudflare credentials missing: CLOUDFLARE_API_TOKEN / CF_ACCOUNT_ID "
            "or ~/.config/voice-bridge/{cf_token,cf_account}")
    endpoint = tts.get(
        "endpoint",
        "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    ).format(account_id=account, model=model)
    body = json.dumps({
        "text": content,
        "speaker": speaker,
        "encoding": tts.get("encoding", "mp3"),
    }).encode("utf-8")
    request = urllib.request.Request(
        endpoint, data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    audio = http_post(lambda: request, int(tts.get("timeout", 30)), rules,
                      "Cloudflare TTS")
    if not audio:
        raise RuntimeError("Cloudflare TTS returned no audio")
    path = state_dir(rules) / "reply.mp3"
    path.write_bytes(audio)
    return _speak_finish(content, lang, path, "cloudflare", model, speaker,
                         rules, tts, voice, play)


def status(rules=None):
    rules = rules or load_rules()
    state = state_dir(rules)
    provider = provider_config(rules["stt"])
    tts = rules.get("tts", {})
    tts_provider = str(tts.get("provider", "piper"))
    if tts_provider == "piper":
        tts_model = tts.get("providers", {}).get("piper", {}).get("voice_es", "")
    else:
        tts_model = tts.get("model_es", "")
    return {"state": str(state), "recording": (state / "recording.pid").exists(),
            "wake_listening": (state / "wake.pid").exists(),
            "provider": provider["name"],
            "credential_ready": credential_ready(rules),
            "key_ready": key_ready(),
            "last": last(rules)[:200],
            "model": provider["model"],
            "language": provider["language"],
            "tts_provider": tts_provider,
            "tts_model": tts_model,
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
    sub.add_parser("wake-start", help="start the session wake listener")
    sub.add_parser("wake-stop", help="stop the session wake listener")
    sub.add_parser("wake-dictate", help="dictate until silence after a wake phrase")
    p_speak = sub.add_parser("speak", help="synthesize and play a reply")
    p_speak.add_argument("text")
    p_speak.add_argument("--language", default=None)
    p_speak.add_argument("--no-play", action="store_true",
                         help="save the audio without playing it")
    sub.add_parser("status", help="show configuration status")
    for name in ("start", "stop", "listen", "transcribe", "wake-dictate"):
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
        elif args.cmd == "speak":
            result = speak(args.text, rules, args.language, play=not args.no_play)
        elif args.cmd == "last":
            print(last(rules))
            return 0
        elif args.cmd == "wake-start":
            result = wake_start(rules)
        elif args.cmd == "wake-stop":
            result = wake_stop(rules)
        elif args.cmd == "wake-dictate":
            result = wake_dictate(rules, args.mock)
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
