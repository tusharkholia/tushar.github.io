# PE Lens – Mid-Market Deal Intelligence Platform

PE Lens is a production-oriented Streamlit SaaS starter for generating institutional-grade deal intelligence memos from a single text query.

## What it does

A user enters a theme such as:
- `US Healthcare IT deals 2026`
- `UK mid-market SaaS acquisitions`
- `Climate tech growth equity Europe`

The platform then:
1. Runs automated web research across credible financial sources.
2. Extracts deal-level fields (target, acquirer, size, multiples, rationale, etc.).
3. Synthesizes trends with OpenAI.
4. Produces a structured memo in investment-committee style.
5. Exports report to PDF/Word and deal table to CSV.

## Architecture

```text
app.py                # Streamlit UI
config.py             # Environment + runtime settings
data_collection.py    # Async web research + extraction
analysis_engine.py    # Institutional trend synthesis
report_generator.py   # Structured memo rendering + export helpers
requirements.txt
.env.example
```

## Functional coverage

- **Input UX**: one text box + "Generate Intelligence Report" button.
- **Automated research**:
  - Tavily News API (optional) + DuckDuckGo discovery.
  - RSS ingestion (Reuters/FT/CNBC/BusinessWire).
  - Domain credibility filtering.
  - Async content fetching + article text extraction.
- **Data extraction**:
  - LLM-based structured parsing from article text into deal records.
  - Captures target/acquirer/deal size/multiple/rationale/sector/geography/date.
  - Fallback to "Not disclosed" where data is unavailable.
- **Analysis output**:
  - Executive summary, market context, valuation insights, buyer landscape,
    key themes, risks/headwinds, forward outlook, analyst take.
- **Export**:
  - PDF download.
  - Word (.docx) download.
  - Deal snapshot CSV download.
  - Copy full memo to clipboard.

## Setup (Local)

1. Clone repo and enter directory
   ```bash
   git clone <repo-url>
   cd tushar.github.io
   ```
2. Create virtual environment
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment
   ```bash
   cp .env.example .env
   ```
5. Add required keys in `.env`
   ```env
   OPENAI_API_KEY=...
   OPENAI_MODEL=gpt-4o-mini
   TAVILY_API_KEY=...  # optional but recommended for stronger news coverage
   ```

## Run

```bash
streamlit run app.py
```

## Example run

- Query: `US Mid-Market Healthcare IT Deals 2026`
- Expected behavior:
  - Spinner appears while data collection + synthesis executes.
  - Report renders with all required sections.
  - Deal table displays extracted transactions.
  - Export buttons provide PDF, DOCX, and CSV files.

## Deployment guide

### Streamlit Community Cloud
1. Push this repo to GitHub.
2. In Streamlit Cloud, create new app and point to `app.py`.
3. Add secrets (OPENAI_API_KEY and optional TAVILY_API_KEY).
4. Deploy.

### Docker / VM / PaaS
1. Provision Python 3.11+ runtime.
2. Install dependencies from `requirements.txt`.
3. Inject environment variables via secrets manager.
4. Run:
   ```bash
   streamlit run app.py --server.port 8501 --server.address 0.0.0.0
   ```
5. Front with reverse proxy (Nginx/Caddy) and TLS for production.

## SaaS scalability extensions

Designed to extend with:
- Auth and accounts
- Saved searches
- Scheduled weekly reports
- Payment/paywall via Stripe
- Persistent deal database
- Sector dashboards and valuation trend charts
