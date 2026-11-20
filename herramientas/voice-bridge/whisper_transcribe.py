#!/usr/bin/env python3
"""Local Whisper STT worker: WAV path in, one JSON object on stdout.

Runs inside the dedicated venv configured in rules.toml (not on the host).
All tuning comes from environment variables so voicectl.py stays dependency-free.
"""
import json
import os
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: whisper_transcribe.py WAV", file=sys.stderr)
        return 2
    from faster_whisper import WhisperModel

    model_name = os.environ.get("WHISPER_MODEL", "base")
    language = os.environ.get("WHISPER_LANGUAGE", "auto")
    model = WhisperModel(
        model_name,
        device=os.environ.get("WHISPER_DEVICE", "cpu"),
        compute_type=os.environ.get("WHISPER_COMPUTE_TYPE", "int8"),
        cpu_threads=int(os.environ.get("WHISPER_CPU_THREADS", "4")),
        download_root=os.environ.get("WHISPER_DOWNLOAD_ROOT") or None,
    )
    segments, info = model.transcribe(
        sys.argv[1],
        language=None if language == "auto" else language,
        beam_size=int(os.environ.get("WHISPER_BEAM_SIZE", "5")),
        vad_filter=os.environ.get("WHISPER_VAD", "1") != "0",
    )
    text = "".join(segment.text for segment in segments).strip()
    print(json.dumps({
        "text": text,
        "language": info.language,
        "language_probability": round(float(info.language_probability), 4),
        "model": model_name,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
