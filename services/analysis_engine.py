"""LLM orchestration for generating investment-grade memos."""
from __future__ import annotations

from openai import OpenAI

from config import settings
from services.research_engine import SourceItem


class AnalysisEngine:
    """Transforms research evidence into an analyst memo."""

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")
        self.client = OpenAI(api_key=settings.openai_api_key)

    @staticmethod
    def _build_source_pack(sources: list[SourceItem]) -> str:
        blocks: list[str] = []
        for idx, source in enumerate(sources, start=1):
            blocks.append(
                "\n".join(
                    [
                        f"SOURCE {idx}: {source.title}",
                        f"URL: {source.url}",
                        f"PUBLISHED: {source.published or 'Unknown'}",
                        f"OUTLET: {source.source}",
                        f"SNIPPET: {source.snippet}",
                        f"EXTRACT: {source.extracted_text}",
                    ]
                )
            )
        return "\n\n".join(blocks)

    def generate_memo(self, query: str, sources: list[SourceItem]) -> str:
        evidence = self._build_source_pack(sources)
        prompt = f"""
You are a top-tier investment banking and private equity research analyst.
Generate a professional, institutional-quality memo from the evidence below.

User Topic: {query}

Required structure (use these exact section headings):
TITLE:
EXECUTIVE SUMMARY
INDUSTRY / TOPIC OVERVIEW
KEY TRENDS & DRIVERS
DEALS / FUNDING / CORPORATE ACTIVITY
VALUATIONS & FINANCIAL INSIGHTS
RISKS & HEADWINDS
OPPORTUNITIES & FORWARD OUTLOOK
ANALYST TAKE

Rules:
- Keep tone concise, factual, and investment-professional.
- Use data points and quantify where possible.
- Distinguish confirmed facts vs interpretation.
- Include dates and names of relevant companies/deals.
- If valuation data is sparse, state assumptions and proxy indicators.
- End with 4-6 bullet recommendations in ANALYST TAKE.

Evidence:
{evidence}
"""

        response = self.client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": "You produce investment-grade memos with clear structure."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or "No memo generated."
