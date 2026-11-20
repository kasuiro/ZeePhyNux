#!/usr/bin/env python3
"""Pure wake-phrase helpers for voice-bridge.

No microphone, subprocess, network or filesystem side effects. These helpers
are shared by the offline tests and the future session listener. Phrases are
space-separated; the Spanish alias may be said with or without "linux".
"""
import difflib
import json
import unicodedata

DEFAULT_PHRASES = ("oye zeep", "oye linux zeep")


def normalize(text):
    """Casefold, drop diacritics and punctuation, collapse whitespace."""
    if not isinstance(text, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(
        ch if ch.isalnum() or ch.isspace() else " "
        for ch in decomposed if not unicodedata.combining(ch)
    )
    return " ".join(plain.split())


def grammar_json(phrases=DEFAULT_PHRASES):
    """Vosk SetGrammar payload for the approved phrases."""
    cleaned = [normalize(phrase) for phrase in phrases if normalize(phrase)]
    return json.dumps(cleaned, ensure_ascii=False)


def matched(text, phrases=DEFAULT_PHRASES):
    """True when an approved phrase appears verbatim in the text."""
    value = normalize(text)
    return any(normalize(phrase) in value for phrase in phrases if normalize(phrase))


def fuzzy_matched(text, phrases=DEFAULT_PHRASES, threshold=0.78):
    """Tolerates short ASR slips without accepting unrelated phrases."""
    value = normalize(text)
    words = value.split()
    for phrase in phrases:
        target = normalize(phrase)
        if not target or target in value:
            continue
        if difflib.SequenceMatcher(None, value, target).ratio() >= threshold:
            return True
        width = len(target.split())
        for index in range(max(0, len(words) - width + 1)):
            window = " ".join(words[index:index + width])
            if difflib.SequenceMatcher(None, window, target).ratio() >= threshold:
                return True
    return False
