# Alma Document Automation – Backend

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
