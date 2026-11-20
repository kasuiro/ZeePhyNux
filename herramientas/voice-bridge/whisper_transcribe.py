#!/usr/bin/env python3
"""Local Whisper STT worker: WAV path in, one JSON object on stdout.

Runs inside the dedicated venv configured in rules.toml (not on the host).
All tuning comes from environment variables so voicectl.py stays dependency-free.

The two helpers (`load_model`, `transcribe`) are also used in-process by the
session wake listener, so the trigger and the dictation share one engine without
loading the model twice. New variables are optional: with none set, the CLI
behaviour is exactly the same as before.
"""
import json
import os
import sys


def load_model(env=None):
    """Build a WhisperModel from env vars. Imports faster_whisper lazily."""
    from faster_whisper import WhisperModel

    env = os.environ if env is None else env
    return WhisperModel(
        env.get("WHISPER_MODEL", "base"),
        device=env.get("WHISPER_DEVICE", "cpu"),
        compute_type=env.get("WHISPER_COMPUTE_TYPE", "int8"),
        cpu_threads=int(env.get("WHISPER_CPU_THREADS", "4")),
        download_root=env.get("WHISPER_DOWNLOAD_ROOT") or None,
    )


def transcribe(model, audio, env=None):
    """Transcribe a WAV path or binary file; return the usual JSON-ready dict."""
    env = os.environ if env is None else env
    language = env.get("WHISPER_LANGUAGE", "auto")
    kwargs = {
        "language": None if language == "auto" else language,
        "beam_size": int(env.get("WHISPER_BEAM_SIZE", "5")),
        "vad_filter": env.get("WHISPER_VAD", "1") != "0",
    }
    # Optional knobs used by the wake listener. They are only sent to the API
    # when present, so the one-shot CLI keeps its original defaults.
    best_of = env.get("WHISPER_BEST_OF")
    if best_of:
        kwargs["best_of"] = int(best_of)
    max_new_tokens = env.get("WHISPER_MAX_NEW_TOKENS")
    if max_new_tokens:
        kwargs["max_new_tokens"] = int(max_new_tokens)
    if env.get("WHISPER_CONDITION_ON_PREVIOUS_TEXT", "1") == "0":
        kwargs["condition_on_previous_text"] = False
    initial_prompt = env.get("WHISPER_INITIAL_PROMPT") or None
    if initial_prompt:
        kwargs["initial_prompt"] = initial_prompt
    hotwords = env.get("WHISPER_HOTWORDS") or None
    if hotwords:
        kwargs["hotwords"] = hotwords
    segments, info = model.transcribe(audio, **kwargs)
    text = "".join(segment.text for segment in segments).strip()
    return {
        "text": text,
        "language": info.language,
        "language_probability": round(float(info.language_probability), 4),
        "model": env.get("WHISPER_MODEL", "base"),
    }


def main():
    if len(sys.argv) != 2:
        print("usage: whisper_transcribe.py WAV", file=sys.stderr)
        return 2
    model = load_model()
    print(json.dumps(transcribe(model, sys.argv[1]), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
