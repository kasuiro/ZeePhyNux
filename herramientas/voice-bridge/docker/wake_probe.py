#!/usr/bin/env python3
"""T2 probe: token check and constrained-grammar Vosk recognition.

Runs inside the already-built local Vosk image with --network none. Prints one
JSON object and writes no files. It is a feasibility probe, not the listener.
"""
import argparse
import json
import os
import resource
import time
import wave

from vosk import KaldiRecognizer, Model, SetLogLevel

RATE = 16000
CHUNK = 4000


def read_pcm(path):
    with wave.open(path, "rb") as handle:
        if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
            raise SystemExit("Vosk expects mono 16-bit PCM WAV: " + str(path))
        rate = handle.getframerate()
        return rate, handle.readframes(handle.getnframes())


def recognize(recognizer, pcm):
    parts = []
    for offset in range(0, len(pcm), CHUNK):
        if recognizer.AcceptWaveform(pcm[offset:offset + CHUNK]):
            parts.append(json.loads(recognizer.Result()).get("text", ""))
    parts.append(json.loads(recognizer.FinalResult()).get("text", ""))
    return " ".join(part for part in parts if part).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wavs", nargs="*")
    parser.add_argument("--grammar", default='["oye zeep", "oye linux zeep"]')
    parser.add_argument("--words", default="oye,zeep,linux")
    parser.add_argument("--stress-seconds", type=int, default=0)
    args = parser.parse_args()

    started = time.monotonic()
    SetLogLevel(-1)
    model = Model(os.environ.get("VOSK_MODEL_PATH", "/opt/model"))
    tokens = {
        word: bool(model.vosk_model_find_word(word))
        for word in args.words.split(",") if word
    }

    recognizer = KaldiRecognizer(model, RATE, args.grammar)
    recognizer.SetWords(False)
    results = []
    for path in args.wavs:
        rate, pcm = read_pcm(path)
        if rate != RATE:
            raise SystemExit(f"unexpected sample rate {rate} in {path}; expected {RATE}")
        recognizer.Reset()
        results.append({"file": os.path.basename(path),
                        "text": recognize(recognizer, pcm)})

    stress = None
    if args.stress_seconds:
        if args.wavs:
            _, pcm = read_pcm(args.wavs[0])
        else:
            pcm = b"\x00\x00" * RATE
        if not pcm:
            pcm = b"\x00\x00" * RATE
        loops = max(1, int(args.stress_seconds * RATE * 2 / len(pcm)))
        recognizer.Reset()
        for _ in range(loops):
            for offset in range(0, len(pcm), CHUNK):
                recognizer.AcceptWaveform(pcm[offset:offset + CHUNK])
        recognizer.FinalResult()
        usage = resource.getrusage(resource.RUSAGE_SELF)
        stress = {
            "seconds_of_audio": round(loops * len(pcm) / (RATE * 2), 2),
            "wall_s": round(time.monotonic() - started, 2),
            "cpu_s": round(usage.ru_utime + usage.ru_stime, 2),
            "maxrss_mb": round(usage.ru_maxrss / 1024, 1),
        }

    print(json.dumps({
        "tokens": tokens,
        "grammar": json.loads(args.grammar),
        "results": results,
        "stress": stress,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
