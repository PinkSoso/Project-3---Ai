# AB Testing AI Agent

An AI-powered A/B testing platform for email marketing campaigns. The agent generates two email variants using a local LLM (Ollama), simulates a 50/50 audience split, and determines the winning variant using both frequentist (chi-square) and Bayesian statistical methods.

## Features

- **AI content generation** — Ollama generates two distinct email variants (subject, body, CTA) from a campaign brief
- **Experiment simulation** — synthetic open/click events for a realistic 50/50 audience split
- **Statistical analysis** — chi-square p-value + Bayesian posterior probabilities to pick the winner
- **Natural language narrative** — Ollama writes a plain-English explanation of the results
- **Campaign history** — browse all past tests and compare outcomes
- **Product catalogue** — 40 pre-seeded Lumino products with copy hooks

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy |
| Frontend | Streamlit |
| LLM | Ollama (local) |
| Database | Supabase |
| Stats | SciPy, NumPy |

## Quick Start

See [SETUP.md](SETUP.md) for full setup instructions.

**Short version:**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and configure environment
cp .env.example .env

# 3. Start Ollama (separate terminal)
ollama serve

# 4. Start backend
uvicorn backend.main:app --reload --port 8000

# 5. Start frontend
streamlit run frontend/app.py
```

Open **http://localhost:8501** in your browser.

## Project Structure

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
├── SETUP.md
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/generate` | Takes a CampaignBrief → returns 2 email variants |
| `POST` | `/run-test/{id}` | Runs simulation + evaluates winner |
| `GET` | `/results/{id}` | Full results for a campaign |
| `GET` | `/history` | All completed tests |
| `GET` | `/products` | List all active products |

## How It Works

1. **Input** — user submits a campaign brief (goal, segment, product, test variable, statistical method)
2. **Generate** — `content_agent` calls Ollama to produce Variant A and Variant B
3. **Simulate** — `experiment.py` generates synthetic audience events (opens, clicks) for each variant
4. **Evaluate** — `winner_agent` runs chi-square test and Bayesian inference, then calls Ollama for a narrative summary
5. **Output** — results displayed in Streamlit with metrics, winner, and recommendation
