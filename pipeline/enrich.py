from __future__ import annotations

import re
from collections import Counter

from .models import Enriched, Transcript

STOPWORDS = set(
    """a an the and or but if then so of to in on at by for with from as is are was were be been it its this that
    these those we you i he she they them our your their will would should could can may might do does did have has
    had not no yes just very also about over into out up down than more most some any all each new need""".split()
)
ACTION_PATTERNS = [
    re.compile(r"\b\w+ will (?!be\b)\w+", re.I),
    re.compile(r"\b(?:we|i) (?:need|have|must|should|'ll|will) to? ?\w+", re.I),
    re.compile(r"\bplease \w+", re.I),
    re.compile(r"\baction item\b", re.I),
]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z']+", text.lower()) if w not in STOPWORDS and len(w) > 2]


def enrich(transcript: Transcript, n_keywords: int = 5, n_summary: int = 2) -> Enriched:
    # Flagged segments are excluded: don't build downstream output on text we don't trust.
    trusted = " ".join(s.text for s in transcript.segments if not s.flagged)
    sentences = _sentences(trusted)
    counts = Counter(_tokens(trusted))

    keywords = [w for w, _ in counts.most_common(n_keywords)]
    actions = [s for s in sentences if any(p.search(s) for p in ACTION_PATTERNS)]

    def score(s: str) -> float:
        toks = _tokens(s)
        return sum(counts[t] for t in toks) / (len(toks) or 1)

    top = sorted(sentences, key=score, reverse=True)[:n_summary]
    summary = " ".join(s for s in sentences if s in top)  # restore original order
    return Enriched(keywords=keywords, action_items=actions, summary=summary)
