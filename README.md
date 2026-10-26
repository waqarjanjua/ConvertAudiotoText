# Audio-to-Text Transcription Pipeline

A command-line pipeline that converts audio recordings into timestamped text and derives structured output for downstream use. It uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper), an open-source speech-recognition library, and runs locally on CPU with no external service.

## Overview

```
audio ─► ingest ─► transcribe ─► clean ─► enrich ─► export
         validate   faster-whisper  remove fillers,  keywords,     JSON / SRT / TXT
                    (or mock)       flag low         action items,
                                    confidence       summary
```

| Stage | Responsibility |
|---|---|
| **Ingest** | Validates the input: file exists, is non-empty, is under 500 MB, and is WAV, MP3, M4A, FLAC or OGG. |
| **Transcribe** | Produces timestamped segments with a confidence score and the detected language. |
| **Clean** | Removes filler words, normalizes casing and punctuation, merges very short fragments, and flags low-confidence segments. |
| **Enrich** | Extracts keywords, action items and an extractive summary from trusted (unflagged) text. |
| **Export** | Writes `.json` (full structured result), `.srt` (subtitles) and `.txt` (plain transcript) for each input file. |

## Getting started

```
pip install -r requirements.txt
pytest -q

python main.py samples --mock --out out        # offline demo, no model download
python main.py recording.mp3 --model base.en   # real transcription
```

| Option | Description | Default |
|---|---|---|
| `target` | Audio file or directory of audio files | required |
| `--out` | Output directory | `out` |
| `--model` | faster-whisper model size (`tiny.en`, `base.en`, `small.en`, ...) | `base.en` |
| `--mock` | Use a canned transcript instead of the model | off |

The first real run downloads the model (about 150 MB for `base.en`). The process exits with a non-zero status if any file fails.

## Design decisions

- **faster-whisper:** open source, efficient on CPU (int8), bundles its own audio decoder so ffmpeg is not required, and returns timestamps and confidence scores.
- **Pluggable transcriber:** engines implement a small `Transcriber` interface. A `MockTranscriber` enables offline tests, and a cloud engine can be added as one class.
- **Flag, don't drop:** low-confidence segments stay in the output and are marked (`flagged`, and `[?]` in SRT) for human review. They are excluded from enrichment, so derived results rely only on trusted text.
- **Per-file failure isolation:** in batch mode, a failing file is reported with its reason and the remaining files continue.
- **JSON as the downstream contract:** it contains the segments, confidence, enrichment results and per-stage timings.
- **Rule-based enrichment:** deterministic and offline. An LLM could replace `enrich.py` behind the same `Enriched` structure.

## Service architecture (proposed)

The current implementation is a CLI. To run it as a service, it would be exposed as an asynchronous HTTP API (for example with FastAPI), because transcription takes too long to run inside a single request. The existing `process_file` function would serve unchanged as the background worker task.

| Endpoint | Purpose |
|---|---|
| `POST /v1/transcriptions` | Upload audio. Returns `202 Accepted` with a job ID. Accepts an optional `callback_url` and `model`. |
| `GET /v1/transcriptions/{id}` | Job status (`queued`, `running`, `completed`, `failed`), progress and any error. |
| `GET /v1/transcriptions/{id}/result?format=json\|srt\|txt` | Completed transcript in the requested format. |
| `POST /v1/transcriptions/{id}/retry` | Re-queue a failed job. |
| `DELETE /v1/transcriptions/{id}` | Delete the audio and transcript. |
| `GET /health` | Liveness check for monitoring. |

**Typical flow:** the client uploads a file and receives `{"job_id": "abc123", "status": "queued"}`. It then polls the status endpoint, or receives a callback, and fetches the result when the job is complete.

**Key points**
- **Concurrency:** uploads are queued (Redis or SQS) and processed by a pool of workers, each holding one model instance. Throughput scales by adding workers.
- **Storage:** audio in object storage with a retention policy, job metadata and transcripts in PostgreSQL.
- **Reliability:** transient failures are retried with exponential backoff, permanent failures (such as corrupt audio) fail immediately, and exhausted jobs go to a dead-letter queue.
- **Errors and security:** standard HTTP status codes (400, 404, 413, 415, 429, 503) with consistent JSON bodies, token-based authentication, per-client rate limits, HTTPS only, and an optional `Idempotency-Key` header.
