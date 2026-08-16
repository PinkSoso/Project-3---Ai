# AB Testing AI Agent — Setup Guide

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed locally

---

## 1. Install Ollama

**Mac**
```bash
brew install ollama
```

**Windows / Linux**
Download from https://ollama.com/download

---

## 2. Pull a model

The app defaults to `llama3.1:8b`. Pull it once:

```bash
ollama pull llama3.1:8b
```

Other options (change `OLLAMA_MODEL` in `.env` accordingly):

| Model | Size | Notes |
|---|---|---|
| `llama3.1:8b` | 4.7 GB | **Recommended** — good instruction following |
| `mistral:7b` | 4.1 GB | Fast, solid JSON output |
| `llama3.2:3b` | 2.0 GB | Lighter, less quality |
| `llama3.1:70b` | 40 GB | Best quality, needs 32 GB+ RAM |

---

## 3. Clone the repo and install dependencies

```bash
cd ab-testing-agent
pip install -r requirements.txt
```

---

## 4. Configure environment

```bash
cp .env.example .env
```

Then open `.env` and choose your database option:

### Option A — SQLite (local, zero setup)

Keep the default — nothing else needed:
```
DATABASE_URL=sqlite:///./local.db
```

The DB file (`local.db`) is created automatically on first run. Each team member gets their own local DB.

### Option B — Supabase (shared team DB)

Everyone shares the same data — useful when testing together.

1. Go to [supabase.com](https://supabase.com) → New project
2. Settings → Database → Connection string → **URI** tab
3. Copy the URI and paste into `.env`:

```
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
```

> The DB schema and seed data are created automatically on first backend startup — one person runs it, everyone else gets the data.

---

## 5. Choose your Ollama model

The app defaults to `mistral:latest`. Pull it if you haven't:

```bash
ollama pull mistral:latest
```

Models available on the team machine:

| Model | Size | Notes |
|---|---|---|
| `mistral:latest` | 4.1 GB | **Default** — fast, reliable JSON output |
| `llama3:latest` | 4.7 GB | Good alternative |
| `llama3.2:latest` | 2.0 GB | Lighter, less quality |
| `qwen:7b` | 4.5 GB | Alternative option |

Change model in `.env`:
```
OLLAMA_MODEL=mistral:latest
```

---

## 6. Run

Open **two terminals** from the `ab-testing-agent/` directory.

**Terminal 1 — Backend**
```bash
ollama serve          # skip if Ollama is already running
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend**
```bash
streamlit run frontend/app.py
```

The DB is seeded automatically on first startup (400 subscribers + 40 products).

Open http://localhost:8501 in your browser.

---

## Project structure

```
ab-testing-agent/
├── backend/
│   ├── main.py                  # FastAPI — 5 endpoints
│   ├── agents/
│   │   ├── content_agent.py     # Ollama → 2 email variants
│   │   └── winner_agent.py      # Stats + Ollama narrative
│   ├── simulation/
│   │   └── experiment.py        # 50/50 split + synthetic events
│   ├── models/
│   │   ├── pydantic_models.py   # CampaignBrief, EmailVariant, Decision
│   │   └── db_models.py         # SQLAlchemy tables
│   └── db/
│       ├── setup_db.py          # Init schema + seed data
│       └── session.py           # DB connection
├── frontend/
│   └── app.py                   # Streamlit — 4 screens
├── data/
│   └── products_dataset.csv     # 40 Lumino products
├── .env.example
├── requirements.txt
└── SETUP.md                     # This file
```

---

## API endpoints (FastAPI)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/generate` | Takes CampaignBrief → returns 2 email variants |
| `POST` | `/run-test/{id}` | Runs simulation + evaluates winner |
| `GET` | `/results/{id}` | Returns full results for a campaign |
| `GET` | `/history` | All completed tests |
| `GET` | `/products/{name}` | Product details by name |

Interactive docs at http://localhost:8000/docs

---

## Resetting the database

**SQLite:**
```bash
rm local.db
# restart backend — DB re-seeds automatically
```

**Supabase:**
```bash
# Drop and recreate all tables via Supabase dashboard → SQL editor:
DROP TABLE IF EXISTS decisions, experiment_results, variants, campaigns, subscribers, products;
# Then restart backend — it will re-seed automatically
```
