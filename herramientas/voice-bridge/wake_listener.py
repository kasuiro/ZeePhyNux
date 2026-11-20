#!/usr/bin/env python3
"""Session-scoped wake-phrase listener for voice-bridge.

Runs inside the Whisper venv, reads raw PCM from ``pw-record`` on stdout and
loads the STT model only once. There is no socket, no port, no network and no
systemd unit: ``voicectl wake-start`` owns the process and ``wake-stop`` ends
it. All I/O stays under the configured state directory.
"""
import argparse
import array
import io
import json
import math
import os
import pathlib
import signal
import subprocess
import sys
import time
import wave

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import wake  # noqa: E402
import whisper_transcribe  # noqa: E402

RATE = 16000
SAMPLE_BYTES = 2
CHUNK_SECONDS = 0.1
CHUNK_BYTES = int(RATE * CHUNK_SECONDS * SAMPLE_BYTES)


def wake_env(rules):
    """Environment for the validated wake parameters, from rules.toml only."""
    provider = rules.get("stt", {}).get("providers", {}).get("whisper", {})
    config = rules.get("wake", {})
    download_root = ""
    if provider.get("hf_home"):
        download_root = str(pathlib.Path(str(provider["hf_home"])).expanduser())
    env = {
        "WHISPER_MODEL": str(provider.get("model", "base")),
        "WHISPER_COMPUTE_TYPE": str(provider.get("compute_type", "int8")),
        "WHISPER_CPU_THREADS": str(provider.get("cpu_threads", 4)),
        "WHISPER_LANGUAGE": str(config.get("language", "es")),
        "WHISPER_BEAM_SIZE": str(config.get("beam_size", 1)),
        "WHISPER_BEST_OF": str(config.get("best_of", 1)),
        "WHISPER_MAX_NEW_TOKENS": str(config.get("max_new_tokens", 40)),
        "WHISPER_VAD": "0" if config.get("vad_filter", True) is False else "1",
        "WHISPER_CONDITION_ON_PREVIOUS_TEXT":
            "1" if config.get("condition_on_previous_text", False) else "0",
        "WHISPER_INITIAL_PROMPT": str(config.get("initial_prompt", "")),
        "WHISPER_HOTWORDS": str(config.get("hotwords", "")),
        "WHISPER_DOWNLOAD_ROOT": download_root,
    }
    if download_root:
        env["HF_HOME"] = download_root
    return env


def pad_pcm(pcm, seconds, rate=RATE):
    """Add leading and trailing digital silence so the phrase has margins."""
    silence = b"\x00\x00" * int(rate * max(0.0, seconds))
    return silence + pcm + silence


def pcm_to_wav(pcm, rate=RATE):
    """In-memory 16 kHz mono s16 WAV; faster-whisper accepts a binary file."""
    out = io.BytesIO()
    with wave.open(out, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(SAMPLE_BYTES)
        handle.setframerate(rate)
        handle.writeframes(pcm)
    out.seek(0)
    return out


class UtteranceSplitter:
    """Energy-based grouping of raw PCM chunks. Pure in-memory logic."""

    def __init__(self, rate=RATE, *, threshold=300, min_seconds=1.0,
                 max_seconds=6.0, silence_timeout=0.8, pad_seconds=0.5):
        self.rate = rate
        self.threshold = threshold
        self.min_samples = int(min_seconds * rate)
        self.max_samples = int(max_seconds * rate)
        self.silence_samples = int(silence_timeout * rate)
        self.pad_samples = int(pad_seconds * rate)
        self.samples = array.array("h")
        self.silent = 0
        self.active = False

    @staticmethod
    def rms(chunk):
        if not chunk:
            return 0.0
        values = array.array("h")
        values.frombytes(chunk[:len(chunk) // 2 * 2])
        if not values:
            return 0.0
        return math.sqrt(sum(value * value for value in values) / len(values))

    def feed(self, chunk):
        """Return PCM bytes for each completed utterance (possibly none)."""
        done = []
        if not chunk:
            return done
        if self.rms(chunk) >= self.threshold:
            self.active = True
            self.silent = 0
        elif self.active:
            self.silent += len(chunk) // SAMPLE_BYTES
        self.samples.frombytes(chunk[:len(chunk) // 2 * 2])
        if not self.active and len(self.samples) > self.pad_samples:
            del self.samples[:len(self.samples) - self.pad_samples]
        if self.active and (len(self.samples) >= self.max_samples or
                            self.silent >= self.silence_samples):
            done.append(self._take())
        return [item for item in done if item]

    def _take(self):
        data = self.samples[:self.max_samples]
        self.samples = array.array("h")
        self.silent = 0
        self.active = False
        return data.tobytes() if len(data) >= self.min_samples else b""

    def flush(self):
        if not self.active:
            return b""
        data = self._take()
        return data


class NoiseAwareSplitter(UtteranceSplitter):
    """Raises the threshold above the measured noise floor of the room."""

    def __init__(self, *args, factor=2.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.factor = factor
        self.base_threshold = self.threshold
        # Seed with the configured floor so speech at the very first chunk is
        # not mistaken for the room's noise level. Window is ~1 s at 16 kHz.
        self.levels = [self.base_threshold] * 10

    def feed(self, chunk):
        self.levels.append(self.rms(chunk))
        floor = min(self.levels[-10:])
        self.threshold = max(self.base_threshold, floor * self.factor)
        return super().feed(chunk)


def detect(model, pcm, env, phrases, rate=RATE, pad_seconds=0.5):
    """Transcribe one utterance and report whether it is an approved phrase."""
    audio = pcm_to_wav(pad_pcm(pcm, pad_seconds, rate), rate)
    result = whisper_transcribe.transcribe(model, audio, env)
    return result, wake.matched(result["text"], phrases)


def default_recorder(rules):
    rec = rules.get("record", {})
    cmd = ["pw-record",
           "--rate", str(rec.get("rate", RATE)),
           "--channels", str(rec.get("channels", 1)),
           "--format", str(rec.get("format", "s16")),
           "-", "-a"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)


def default_trigger(rules):
    """Start the normal dictation flow through the existing CLI."""
    config = rules.get("wake", {})
    cap = float(config.get("dictate_max_seconds", 30))
    stt_timeout = int(rules.get("stt", {}).get("timeout", 120))
    cmd = [sys.executable, str(ROOT / "voicectl.py"), "wake-dictate"]
    subprocess.run(cmd, check=False, timeout=cap + stt_timeout + 30)


class Listener:
    """Owns one recorder child, one model instance and one state file."""

    def __init__(self, rules, *, env=None, state=None, recorder=None,
                 trigger=None, model=None, splitter=None):
        self.rules = rules
        self.config = rules.get("wake", {})
        self.env = env
        self.state = pathlib.Path(state) if state else pathlib.Path(
            str(rules.get("paths", {}).get("state", "")) or
            pathlib.Path.home() / ".local/state/voice-bridge")
        self.recorder = recorder or (lambda: default_recorder(rules))
        self.trigger = trigger or (lambda: default_trigger(rules))
        self.model = model
        self.splitter = splitter
        self.proc = None
        self.stopped = False
        self.suppressed_until = 0.0
        self.next_allowed = 0.0
        self._previous_handlers = {}

    def _signal(self, signum, _frame):
        self.stopped = True
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except OSError:
                pass

    def _install_signals(self):
        for name in ("SIGINT", "SIGTERM"):
            sig = getattr(signal, name, None)
            if sig is None:
                continue
            self._previous_handlers[sig] = signal.signal(sig, self._signal)

    def _restore_signals(self):
        for sig, handler in self._previous_handlers.items():
            signal.signal(sig, handler)
        self._previous_handlers.clear()

    def _new_splitter(self):
        cfg = self.config
        return NoiseAwareSplitter(
            rate=int(self.rules.get("record", {}).get("rate", RATE)),
            threshold=float(cfg.get("energy_threshold", 300)),
            min_seconds=float(cfg.get("min_utterance_seconds", 1.0)),
            max_seconds=float(cfg.get("max_utterance_seconds", 6.0)),
            silence_timeout=float(cfg.get("silence_timeout", 0.8)),
            pad_seconds=float(cfg.get("pad_seconds", 0.5)),
            factor=float(cfg.get("noise_factor", 2.0)),
        )

    def _record(self, result, matched):
        payload = {"text": result.get("text", ""), "matched": matched,
                   "model": result.get("model", ""),
                   "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / "wake.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False), flush=True)

    def run(self):
        if not self.config.get("enabled", True):
            return 0
        self.env = self.env if self.env is not None else wake_env(self.rules)
        self.splitter = self.splitter or self._new_splitter()
        self.model = self.model or whisper_transcribe.load_model(self.env)
        phrases = tuple(self.config.get("phrases") or wake.DEFAULT_PHRASES)
        rate = int(self.rules.get("record", {}).get("rate", RATE))
        pad_seconds = float(self.config.get("pad_seconds", 0.5))
        cooldown = float(self.config.get("cooldown_seconds", 3))
        self.proc = self.recorder()
        self._install_signals()
        try:
            while not self.stopped:
                chunk = self.proc.stdout.read(CHUNK_BYTES)
                if not chunk:
                    break
                if time.monotonic() < self.suppressed_until:
                    continue  # drain stale audio while dictation owns the mic
                for pcm in self.splitter.feed(chunk):
                    result, matched = detect(
                        self.model, pcm, self.env, phrases, rate, pad_seconds)
                    self._record(result, matched)
                    if matched and time.monotonic() >= self.next_allowed:
                        self.trigger()
                        self.splitter = self._new_splitter()
                        self.suppressed_until = time.monotonic() + cooldown
                        self.next_allowed = self.suppressed_until
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            print(f"wake_listener: {exc}", file=sys.stderr, flush=True)
            return 1
        finally:
            self._restore_signals()
            if self.proc is not None:
                if self.proc.poll() is None:
                    self.proc.terminate()
                    try:
                        self.proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.proc.kill()
                        self.proc.wait(timeout=2)
                if self.proc.stdout is not None:
                    self.proc.stdout.close()
                self.proc = None
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(
        pathlib.Path.home() / ".config/voice-bridge/rules.toml"))
    args = parser.parse_args(argv)
    config = pathlib.Path(args.config).expanduser()
    if config.is_file():
        import tomllib
        with open(config, "rb") as handle:
            rules = tomllib.load(handle)
    else:
        import voicectl
        rules = voicectl.load_rules()
    return Listener(rules).run()


if __name__ == "__main__":
    sys.exit(main())
