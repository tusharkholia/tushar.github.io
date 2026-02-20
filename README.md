# GMAT AI Coach

Production-capable local GMAT tutoring assistant built with **Streamlit + Python + SQLite + optional RAG**.

## Features
- Explain & coach any GMAT Quant/Verbal question with structured tutor output.
- Optional PDF ingestion (local) with chunking + embeddings + vector retrieval.
- Performance tracking: attempts, timing, weaknesses, trends, streak/XP/levels.
- Adaptive study plan generator.
- Practice-similar question generation.
- Export CSV + PDF summary report.
- Free/Pro feature flags and Stripe checkout scaffolding.
- Daily challenge leaderboard, ELI5 mode.

## Architecture
- `app.py`: Streamlit UI and orchestration.
- `backend/explain_engine.py`: prompt templates, OpenAI calls, fallback tutor.
- `backend/pdf_ingest.py`: PDF extraction + async embedding ingestion.
- `backend/vectorstore.py`: Chroma primary, memory fallback.
- `backend/tracker.py`: SQLite persistence and analytics.
- `backend/study_plan.py`: adaptive plan logic.
- `backend/monetization.py`: free/pro gate + Stripe hook.
- `db/schema.sql`: database schema.

## Local setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# add OPENAI_API_KEY=... in .env
streamlit run app.py
```

## Environment variables
- `OPENAI_API_KEY` (optional but recommended)
- `OPENAI_MODEL=gpt-4.1-mini`
- `FEATURE_TIER=free|pro`
- `VECTOR_BACKEND=chroma|memory`
- `EMBEDDING_BACKEND=openai|local`
- `STRIPE_SECRET_KEY` (optional scaffold)

## PDF ingestion
Use the **Upload Reference PDFs** section, then click **Ingest PDFs**. Data stays local by default.

## Testing
```bash
pytest -q
```

## Deploy notes (Render/Railway/Heroku)
- Deploy as a web service with `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`
- Persist `db/` volume for history/vector data.
- Set env vars in platform secrets.

## Stripe integration points
`backend/monetization.py#create_stripe_checkout_session_stub` shows checkout payload shape.
Replace with real `stripe.checkout.Session.create(...)` in production.

## Demo script
```bash
python scripts/demo_session.py
```

## Security & ethics
- API keys loaded from `.env`; never commit real keys.
- PDF text sanitized for control characters.
- Citation policy: avoid quoting >25 words from a source chunk.
- Disclaimer included in app: not an official GMAT product.
