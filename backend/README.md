# FormPilot – Backend

FastAPI server: upload passport and G-28, extract data with BAML (Gemini 2.0 Flash), fill form with Playwright.

## Setup

```bash
cd backend
poetry install
# Set GOOGLE_API_KEY in .env (see project root .env.example)
poetry run baml-cli generate   # if you change baml_src
poetry run playwright install chromium
```

## Run

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /health` – health check
- `POST /extract` – upload `passport` and/or `g28` (files), returns extracted JSON
- `POST /fill-form` – same uploads, then opens form in browser and fills (does not submit)
- `GET /demo/sample-extraction?variant=good|messy` – local sample payload + readiness + preview (no API keys)
- `POST /demo/sample-session?variant=good|messy` – create a stored demo session (no API keys)
- `GET /extraction-sessions/{id}/readiness.md` – export readiness scorecard as Markdown
- `POST /intake/jobs` – multipart `passport` / `g28`; creates job, stores files, runs pipeline in background
- `GET /intake/jobs/{id}` – job status, audit tail, artifact list, signed `page_image_links` for review UI
- `GET /intake/jobs/{id}/fields` – field assertions (values + `baml` vs `human_override`)
- `PATCH /intake/jobs/{id}/fields` – body `{ "patches": [{ "field_path", "value", "reviewer_note?" }] }`
- `GET /intake/jobs/{id}/artifacts/{artifact_id}/file?exp=&sig=` – signed download for rendered pages / originals
- `POST /intake/jobs/{id}/promote-to-session` – create `extraction_sessions` row from current assertions + readiness
