from __future__ import annotations

import json
from pathlib import Path

from .models import Result, Transcript


def _ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def to_srt(t: Transcript) -> str:
    blocks = []
    for i, s in enumerate(t.segments, 1):
        mark = " [?]" if s.flagged else ""
        blocks.append(f"{i}\n{_ts(s.start)} --> {_ts(s.end)}\n{s.text}{mark}\n")
    return "\n".join(blocks)


def export(result: Result, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(result.transcript.source).stem
    files = {
        out_dir / f"{stem}.json": json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
        out_dir / f"{stem}.srt": to_srt(result.transcript),
        out_dir / f"{stem}.txt": result.transcript.text + "\n",
    }
    for path, content in files.items():
        path.write_text(content, encoding="utf-8")
    return list(files)
