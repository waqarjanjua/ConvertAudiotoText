from __future__ import annotations

import math
from pathlib import Path
from typing import Protocol

from .models import Segment, Transcript


class Transcriber(Protocol):
    def transcribe(self, path: Path) -> Transcript: ...


class FasterWhisperTranscriber:
    """Local open-source STT. Model is loaded lazily and reused across files."""

    def __init__(self, model_size: str = "base.en", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # imported lazily: heavy, and unneeded in mock mode

            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        return self._model

    def transcribe(self, path: Path) -> Transcript:
        segments, info = self._load().transcribe(str(path), vad_filter=True, beam_size=5)
        out = [
            Segment(
                start=s.start,
                end=s.end,
                text=s.text.strip(),
                confidence=math.exp(s.avg_logprob),  # logprob -> probability-like 0..1
                no_speech_prob=s.no_speech_prob,
            )
            for s in segments  # generator: decoding happens here
        ]
        return Transcript(source=str(path), language=info.language, duration=info.duration, segments=out)


class MockTranscriber:
    """Returns canned segments so the pipeline runs and tests without a model download."""

    CANNED = [
        (0.0, 4.0, "um so welcome everyone to the weekly product sync", 0.93, 0.01),
        (4.0, 9.5, "uh the new checkout flow reduced drop off by twelve percent", 0.90, 0.02),
        (9.5, 12.0, "mumble mumble", 0.25, 0.70),
        (12.0, 17.0, "John will send the revised pricing deck to the client by Friday.", 0.95, 0.01),
        (17.0, 22.0, "We need to fix the checkout bug on mobile before the release.", 0.92, 0.01),
        (22.0, 26.0, "Overall the checkout flow and the pricing deck are on track.", 0.94, 0.01),
    ]

    def transcribe(self, path: Path) -> Transcript:
        segs = [Segment(a, b, t, c, n) for a, b, t, c, n in self.CANNED]
        return Transcript(source=str(path), language="en", duration=segs[-1].end, segments=segs)
