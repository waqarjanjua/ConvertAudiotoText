from __future__ import annotations

import re

from .models import Segment, Transcript

FILLERS = re.compile(r"\b(?:um+|uh+|erm|you know|i mean)\b[,]?\s*", re.IGNORECASE)
MIN_CONFIDENCE = 0.5
MAX_NO_SPEECH = 0.6
MIN_MERGE_SECONDS = 1.0


def clean_text(text: str) -> str:
    text = FILLERS.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text:
        text = text[0].upper() + text[1:]
        if text[-1] not in ".!?":
            text += "."
    return text


def is_low_confidence(seg: Segment) -> bool:
    return seg.confidence < MIN_CONFIDENCE or seg.no_speech_prob > MAX_NO_SPEECH


def clean(transcript: Transcript) -> Transcript:
    """Normalize text, flag (never drop) low-confidence segments, merge tiny fragments."""
    out: list[Segment] = []
    for seg in transcript.segments:
        text = clean_text(seg.text)
        if not text:  # was only fillers
            continue
        new = Segment(seg.start, seg.end, text, seg.confidence, seg.no_speech_prob)
        new.flagged = is_low_confidence(new)
        prev = out[-1] if out else None
        if prev and (new.end - new.start) < MIN_MERGE_SECONDS and prev.flagged == new.flagged:
            prev.text = f"{prev.text} {new.text}"
            prev.end = new.end
            prev.confidence = min(prev.confidence, new.confidence)
            continue
        out.append(new)
    return Transcript(transcript.source, transcript.language, transcript.duration, out)
