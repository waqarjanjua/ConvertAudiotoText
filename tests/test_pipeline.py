import json
import wave
from pathlib import Path

import pytest

from pipeline.clean import clean, clean_text
from pipeline.enrich import enrich
from pipeline.ingest import IngestError, validate
from pipeline.models import Segment, Transcript
from pipeline.run import run
from pipeline.transcribe import MockTranscriber


def make_wav(path: Path, seconds: float = 0.2) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * seconds))
    return path


def test_clean_text_removes_fillers_and_punctuates():
    assert clean_text("um so we ship uh tomorrow") == "So we ship tomorrow."


def test_clean_flags_low_confidence_and_drops_filler_only():
    t = Transcript("x.wav", "en", 10, [
        Segment(0, 3, "um", 0.9),
        Segment(3, 6, "mumble", 0.2, 0.8),
        Segment(6, 9, "hello there", 0.9),
    ])
    out = clean(t).segments
    assert [s.text for s in out] == ["Mumble.", "Hello there."]
    assert out[0].flagged and not out[1].flagged


def test_clean_merges_tiny_segments():
    t = Transcript("x.wav", "en", 3, [Segment(0, 2, "hello", 0.9), Segment(2, 2.4, "world", 0.9)])
    out = clean(t).segments
    assert len(out) == 1 and out[0].text == "Hello. World." and out[0].end == 2.4


def test_enrich_finds_actions_and_excludes_flagged():
    t = clean(MockTranscriber().transcribe(Path("m.wav")))
    e = enrich(t)
    assert any("John will send" in a for a in e.action_items)
    assert any("fix the checkout bug" in a for a in e.action_items)
    assert "mumble" not in " ".join(e.keywords).lower()
    assert "checkout" in e.keywords


def test_ingest_errors(tmp_path):
    with pytest.raises(IngestError):
        validate(tmp_path / "missing.wav")
    txt = tmp_path / "a.txt"
    txt.write_text("x")
    with pytest.raises(IngestError):
        validate(txt)
    empty = tmp_path / "e.wav"
    empty.write_bytes(b"")
    with pytest.raises(IngestError):
        validate(empty)


def test_end_to_end_mock_and_failure_isolation(tmp_path):
    src = tmp_path / "in"
    src.mkdir()
    make_wav(src / "good.wav")
    (src / "bad.wav").write_bytes(b"")  # empty -> ingest failure
    out = tmp_path / "out"
    report = run(src, MockTranscriber(), out)
    assert len(report.succeeded) == 1 and len(report.failed) == 1
    data = json.loads((out / "good.json").read_text(encoding="utf-8"))
    assert data["transcript"]["language"] == "en"
    assert data["enriched"]["action_items"]
    assert (out / "good.srt").read_text(encoding="utf-8").startswith("1\n00:00:00,000 --> ")
    assert (out / "good.txt").exists()
