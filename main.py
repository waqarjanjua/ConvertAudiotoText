import argparse
import logging
import sys
from pathlib import Path

from pipeline.run import run
from pipeline.transcribe import FasterWhisperTranscriber, MockTranscriber


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Audio -> transcript -> cleaned/enriched outputs")
    ap.add_argument("target", help="audio file or directory of audio files")
    ap.add_argument("--out", default="out", help="output directory (default: out)")
    ap.add_argument("--model", default="base.en", help="faster-whisper model size (default: base.en)")
    ap.add_argument("--mock", action="store_true", help="use canned transcript, no model download")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    transcriber = MockTranscriber() if args.mock else FasterWhisperTranscriber(args.model)
    report = run(args.target, transcriber, Path(args.out))

    print(f"\n{len(report.succeeded)} succeeded, {len(report.failed)} failed")
    for path, err in report.failed.items():
        print(f"  FAILED {path}: {err}")
    return 1 if report.failed or not report.succeeded else 0


if __name__ == "__main__":
    sys.exit(main())
