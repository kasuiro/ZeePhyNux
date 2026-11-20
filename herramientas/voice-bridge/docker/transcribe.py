#!/usr/bin/env python3
"""One-shot Vosk transcription: WAV in, JSON out. No network at runtime."""
import json
import os
import sys
import wave

from vosk import KaldiRecognizer, Model, SetLogLevel


def main():
    wav_path = sys.argv[1] if len(sys.argv) > 1 else "/in.wav"
    SetLogLevel(-1)
    model = Model(os.environ.get("VOSK_MODEL_PATH", "/opt/model"))
    parts = []
    with wave.open(wav_path, "rb") as handle:
        if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
            raise SystemExit("Vosk expects mono 16-bit PCM WAV")
        recognizer = KaldiRecognizer(model, handle.getframerate())
        recognizer.SetWords(False)
        while True:
            chunk = handle.readframes(4000)
            if not chunk:
                break
            if recognizer.AcceptWaveform(chunk):
                parts.append(json.loads(recognizer.Result()).get("text", ""))
        parts.append(json.loads(recognizer.FinalResult()).get("text", ""))
    text = " ".join(part for part in parts if part).strip()
    print(json.dumps({"text": text, "engine": "vosk"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
