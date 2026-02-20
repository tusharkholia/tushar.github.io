# AI Research & Deal Memo Generator

Professional Streamlit app that converts a single research query into an investment-grade memo by automatically gathering web sources, synthesizing evidence, and producing exportable output.

## Features

- **Single input workflow**: enter one topic/question, no uploads.
- **Automated research engine**:
  - DuckDuckGo web discovery
  - Finance/business RSS ingestion
  - Credibility filtering by trusted domains
  - Async article fetch + text extraction
- **AI analysis engine** using OpenAI for structured memo generation.
- **Institutional memo structure**:
  - TITLE
  - EXECUTIVE SUMMARY
  - INDUSTRY / TOPIC OVERVIEW
  - KEY TRENDS & DRIVERS
  - DEALS / FUNDING / CORPORATE ACTIVITY
  - VALUATIONS & FINANCIAL INSIGHTS
  - RISKS & HEADWINDS
  - OPPORTUNITIES & FORWARD OUTLOOK
  - ANALYST TAKE
- **Export options**:
  - PDF download
  - Word (.docx) download
  - Copy memo to clipboard
- **Expansion-ready architecture** for recurring memos, sector trackers, and delivery integrations.

## Project structure

```text
app.py
config.py
services/
  analysis_engine.py
  exporter.py
  research_engine.py
requirements.txt
.env.example
```

## Setup

1. **Clone and enter repo**
   ```bash
   git clone <repo-url>
   cd tushar.github.io
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API keys**
   ```bash
   cp .env.example .env
   ```
   Add your OpenAI key in `.env`:
   ```env
   OPENAI_API_KEY=your_real_key
   ```

## Run locally

```bash
streamlit run app.py
```

Open the URL shown by Streamlit (usually `http://localhost:8501`).

## Notes on production hardening

- Add caching for repeated sources/results.
- Add retriever observability + source quality scoring.
- Add background scheduling for weekly auto-memo features.
- Add persistent storage for sector watchlists and historical memos.
