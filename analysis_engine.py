"""LLM analysis engine for institutional deal-intelligence outputs."""
from __future__ import annotations

import json
from dataclasses import asdict

from openai import OpenAI

from config import settings
from data_collection import DealRecord


class AnalysisEngine:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for analysis.")
        self.client = OpenAI(api_key=settings.openai_api_key)

    def generate_structured_analysis(self, query: str, deals: list[DealRecord]) -> dict:
        deal_json = json.dumps([asdict(d) for d in deals], ensure_ascii=False)
        prompt = f"""
You are a private equity strategy analyst writing institutional mid-market deal intelligence.
Input query: {query}
Structured deals:
{deal_json}

Return STRICT JSON with keys:
- title
- executive_summary (array of 5-7 bullets)
- market_context (array of bullets)
- valuation_insights (array of bullets)
- buyer_landscape (array of bullets)
- key_themes (array of bullets)
- risks_headwinds (array of bullets)
- forward_outlook (array of bullets)
- analyst_take (array of bullets)

Requirements:
- Concise, analytical, no fluff.
- Mention valuation direction and capital flow.
- If valuation data is limited, say so and provide cautious proxy view.
- Keep bullet items under 28 words.
"""
        response = self.client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Produce concise investment memo analysis."},
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        payload = json.loads(raw)
        return payload
