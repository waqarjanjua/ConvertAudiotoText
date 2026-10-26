from __future__ import annotations

from pathlib import Path

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
MAX_BYTES = 500 * 1024 * 1024


class IngestError(Exception):
    pass


def validate(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_file():
        raise IngestError(f"not a file: {p}")
    if p.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise IngestError(f"unsupported extension '{p.suffix}' (allowed: {sorted(ALLOWED_EXTENSIONS)})")
    size = p.stat().st_size
    if size == 0:
        raise IngestError(f"empty file: {p}")
    if size > MAX_BYTES:
        raise IngestError(f"file too large ({size} bytes, limit {MAX_BYTES}): {p}")
    return p


def discover(path: str | Path) -> list[Path]:
    """A file yields itself; a directory yields its supported audio files (sorted)."""
    p = Path(path)
    if p.is_dir():
        return sorted(f for f in p.iterdir() if f.suffix.lower() in ALLOWED_EXTENSIONS)
    return [p]
