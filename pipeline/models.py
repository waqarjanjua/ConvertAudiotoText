from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Segment:
    start: float
    end: float
    text: str
    confidence: float = 1.0  # 0..1, derived from avg_logprob
    no_speech_prob: float = 0.0
    flagged: bool = False  # low confidence -> needs human review


@dataclass
class Transcript:
    source: str
    language: str
    duration: float
    segments: list[Segment] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.segments if s.text)


@dataclass
class Enriched:
    keywords: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class Result:
    transcript: Transcript
    enriched: Enriched
    timings: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["transcript"]["text"] = self.transcript.text
        return d
