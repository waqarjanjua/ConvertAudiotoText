from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import ingest
from .clean import clean
from .enrich import enrich
from .export import export
from .models import Result
from .transcribe import Transcriber

log = logging.getLogger("pipeline")


@dataclass
class RunReport:
    succeeded: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)


def process_file(path: Path, transcriber: Transcriber, out_dir: Path) -> Result:
    timings: dict[str, float] = {}

    def timed(name, fn, *args):
        t0 = time.perf_counter()
        value = fn(*args)
        timings[name] = round(time.perf_counter() - t0, 3)
        return value

    valid = timed("ingest", ingest.validate, path)
    raw = timed("transcribe", transcriber.transcribe, valid)
    cleaned = timed("clean", clean, raw)
    enriched = timed("enrich", enrich, cleaned)
    result = Result(cleaned, enriched, timings)
    timed("export", export, result, out_dir)
    return result


def run(target: str | Path, transcriber: Transcriber, out_dir: Path) -> RunReport:
    """Process a file or directory. A failure on one file never aborts the others."""
    report = RunReport()
    for path in ingest.discover(target):
        try:
            result = process_file(path, transcriber, out_dir)
            flagged = sum(s.flagged for s in result.transcript.segments)
            log.info("ok %s (%d segments, %d flagged, %s)", path.name, len(result.transcript.segments), flagged, result.timings)
            report.succeeded.append(str(path))
        except Exception as exc:  # isolate per-file failures (bad audio, decode errors, ...)
            log.error("failed %s: %s", path.name, exc)
            report.failed[str(path)] = str(exc)
    return report
