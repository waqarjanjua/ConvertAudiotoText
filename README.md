# Audio → Text Pipeline

```
audio ─► ingest ─► transcribe ─► clean ─► enrich ─► export (json / srt / txt)
        validate    faster-whisper  fillers,    keywords,
                    (or mock)       flag low    action items,
                                    confidence  summary
```

## Run
```
pip install -r requirements.txt
pytest -q
python main.py samples --mock --out out        # no model download
python main.py meeting.mp3 --model base.en     # real transcription
```
Exit code is non-zero if any file failed.

## Design decisions
- **faster-whisper**: open source, CPU-friendly (int8), bundles its own audio decoder (no ffmpeg install), and returns timestamps and confidence.
- **Pluggable `Transcriber`**: a `MockTranscriber` makes the pipeline testable offline. A cloud API would be one more class.
- **Flag, don't drop**: low-confidence segments are kept and marked (`flagged`, `[?]` in SRT) for human review. They are excluded from enrichment, so downstream output is built only on trusted text.
- **Per-file failure isolation**: in batch mode one bad file is reported and the rest continue.
- **JSON is the downstream contract**: it holds the full transcript with segments and confidence, enrichment results, and per-stage timings.
- **Rule-based enrichment**: keywords, action items and an extractive summary run offline and deterministically. An LLM could replace `enrich.py` behind the same `Enriched` shape.


## Design decisions for Service implementation
This is a design answer. The current program is a command-line script. I would expose it as an asynchronous HTTP API, for example with FastAPI, because transcription takes too long to complete inside a single request.

Endpoints:
Method and path	Purpose
POST /transcriptions	Upload an audio file (multipart form). The API validates it and returns 202 Accepted with a job identifier. An optional callback_url and model can be supplied.
GET /transcriptions/{id}	Return the job status (queued, running, completed, failed), the progress, and the error message if the job failed.
GET /transcriptions/{id}/result?format=json|srt|txt	Return the finished transcript in the requested format. The JSON format includes the timestamped segments, confidence, keywords, action items and summary.
POST /transcriptions/{id}/retry	Re-queue a failed job.
DELETE /transcriptions/{id}	Delete the audio and the transcript.
GET /health	Report whether the service is running, for monitoring.

Example flow:
The client uploads a file and receives {"job_id": "abc123", "status": "queued"}.
The client polls GET /transcriptions/abc123, or receives a callback to its callback_url when the job finishes.
The client fetches the result as JSON, SRT or text.
Design points:

Asynchronous. The upload returns at once and the work runs on background workers, as described in the answer on concurrent uploads. This keeps the API responsive.
Reuse of the existing code. The worker calls the existing process_file function unchanged, so the pipeline logic is not duplicated.
Validation and errors. Standard HTTP codes: 400 for an invalid request, 413 for a file that is too large, 415 for an unsupported format, 404 for an unknown job, 429 when the client is over its rate limit, and 503 when the service is overloaded. Error bodies are consistent JSON.
Security. Token-based authentication (API key or OAuth), a per-client rate limit, and an access check so each client sees only its own jobs. HTTPS only.
Versioning and documentation. The routes live under /v1/, so the interface can change without breaking clients. FastAPI generates interactive OpenAPI documentation automatically.
Idempotency. An optional Idempotency-Key header prevents a duplicate job if a client retries an upload after a network failure.
I can implement a working FastAPI version of this, with a background worker and SQLite storage, if a demon
