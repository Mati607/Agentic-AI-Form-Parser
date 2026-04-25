# FormPilot – AI Document-to-Form

Upload passport and G-28 (PDF or image), extract data with **BAML + Gemini**, and fill a test form via **Playwright**. The app does not submit or sign the form.

---

## Setup

### 1. API key (Google AI Studio)

1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in and open **Get API key** (or **API keys** in the left menu).
3. Create an API key and copy it.
4. In the project root, create a `.env` file and add:

```bash
GOOGLE_API_KEY=your_api_key_here
```

Optional: `FORM_URL`, `HEADLESS`, and Chrome CDP options can be set in `.env` (see [Environment](#environment)).

### 2. Backend

```bash
cd backend
poetry install
poetry run baml-cli generate
poetry run playwright install chromium
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Upload passport and/or G-28, then use **Extract only** or **Extract & fill form**.

---

## Tests

Backend unit tests use **pytest** with mocked extraction and form-filling so no API key or browser is required. They cover the FastAPI routes: health, extract (validation, content-type, missing key), fill (with stubbed Playwright), preview/readiness, and extraction sessions.

From the backend directory:

```bash
cd backend
poetry run pytest
```

Use `-v` for verbose output or `-k "test_name"` to run a subset of tests.

---

## Main functionality

- **Document validation** — Before extraction, each file is checked (passport vs G-28/A-28) via LLM. Invalid document types are rejected with a short reason.
- **Data extraction** — BAML + Gemini read passport and G-28 images (PDFs are converted to images). All fields are optional so missing or unclear data does not break the pipeline.
- **Form filling** — Playwright opens the target form and fills fields by matching labels (with fallbacks for placeholder and name). Only non-empty extracted values are written; the form is not submitted.
- **Fill preview** — `POST /preview-fill` returns which mapped fields have values (same mapping Playwright uses). No browser or Gemini call.
- **Extraction readiness** — `POST /extraction-readiness` runs rule-based checks (missing core fields, passport expiry, attorney contact hints, etc.) and returns a score, letter grade, and findings. No LLM call. Saving a session stores this snapshot in SQLite (`quality_json`) and returns it from `POST /extraction-sessions`; the UI shows the report after extract/load.
- **Saved extraction sessions** — Merged extraction JSON can be stored in SQLite (`POST /extraction-sessions`), listed, exported, deleted, and used to run `POST /extraction-sessions/{id}/fill-form` without re-uploading files. The React app includes a sidebar for these sessions.
- **Demo mode (no API keys)** — `GET /demo/sample-extraction` and `POST /demo/sample-session` generate realistic sample data locally (no LLM calls) so you can show the full UX without credentials.
- **Shareable readiness report** — `GET /extraction-sessions/{id}/readiness.md` exports a one-page Markdown scorecard for demos and reviews.

---

## Environment

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | **Required.** Google AI API key (from Google AI Studio). |
| `FORM_URL` | Form URL to fill. Default: `https://mendrika-alma.github.io/form-submission/` |
| `HEADLESS` | Set to `false` to show the browser when filling the form. |
| `EXTRACTION_DB_PATH` | Optional. Path to the SQLite file for saved sessions. Default: `backend/data/extraction_sessions.db` (created on startup). |

---

## Tech

- **Backend:** FastAPI, BAML (Gemini), Playwright (Chromium). Poetry.
- **Frontend:** React (Vite) upload UI.
