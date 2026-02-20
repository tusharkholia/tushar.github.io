"""OpenAI-backed tutoring engine with deterministic fallback."""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from backend.utils import classify_question

OUTPUT_FIELDS = [
    "ANSWER",
    "CONFIDENCE",
    "STEP-BY-STEP SOLUTION",
    "WHY WRONG OPTIONS ARE WRONG",
    "SHORTCUT / TIMING TRICK",
    "GMAT STRATEGY TIP",
    "DIFFICULTY RATING",
    "COMMON TRAP",
    "QUICK PRACTICE DRILL",
]


class ExplainEngine:
    def __init__(self, vector_store=None) -> None:
        self.vector_store = vector_store

    def explain(
        self,
        question_text: str,
        explain_using_notes: bool = False,
        eli5_mode: bool = False,
    ) -> dict[str, Any]:
        qtype = classify_question(question_text)
        context_chunks = []
        if explain_using_notes and self.vector_store:
            emb = self._local_embedding(question_text)
            context_chunks = self.vector_store.query(emb, top_k=3)

        if os.getenv("OPENAI_API_KEY"):
            try:
                return self._openai_explain(question_text, qtype, context_chunks, eli5_mode)
            except Exception:
                pass
        return self._fallback_explain(question_text, qtype, context_chunks, eli5_mode)

    def generate_similar(self, question_text: str) -> list[str]:
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI

                client = OpenAI()
                rsp = client.responses.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                    temperature=0.6,
                    input=[{"role": "user", "content": f"Generate 3 GMAT questions similar to:\n{question_text}"}],
                )
                raw = rsp.output_text.strip()
                return [line.strip("- ") for line in raw.splitlines() if line.strip()][:3]
            except Exception:
                pass
        return [
            "If x + y = 12 and x - y = 4, what is x?",
            "A store marks up price by 20% then discounts 20%. Net change?",
            "Which assumption is required for the argument to hold?",
        ]

    def _openai_explain(self, q: str, qtype: str, chunks: list[dict[str, Any]], eli5_mode: bool) -> dict[str, Any]:
        from openai import OpenAI

        mode_line = "Also include a short ELI5 explanation." if eli5_mode else ""
        rag = "\n".join(
            f"[Source: {c['metadata'].get('file_name')} | page {c['metadata'].get('source_page')}] {c['text'][:250]}"
            for c in chunks
        )
        prompt = f"""
You are an elite GMAT tutor. Question type: {qtype}.
Return ONLY JSON with keys: {', '.join(OUTPUT_FIELDS)} and optional 'ASSUMPTIONS_USED'.
{mode_line}
If sources are present, cite them with [Source: filename.pdf | page N].
Question:
{q}
Retrieved notes:
{rag or 'None'}
"""
        client = OpenAI()
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            temperature=0.2,
            input=[{"role": "user", "content": prompt}],
        )
        text = response.output_text
        return json.loads(text)

    def _fallback_explain(self, q: str, qtype: str, chunks: list[dict[str, Any]], eli5_mode: bool) -> dict[str, Any]:
        source_line = ""
        if chunks:
            src = chunks[0]["metadata"]
            source_line = f" Used your notes: [Source: {src.get('file_name')} | page {src.get('source_page')}]."
        base = {
            "ANSWER": "Best-effort: Cannot verify exact option without full choices.",
            "CONFIDENCE": "low - running deterministic fallback (offline/rate-limited).",
            "STEP-BY-STEP SOLUTION": "1) Parse givens and unknowns. 2) Choose equation/logic pattern. 3) Solve and sanity-check units/signs.",
            "WHY WRONG OPTIONS ARE WRONG": "- Typical traps: sign errors, denominator mistakes, invalid assumption leaps.",
            "SHORTCUT / TIMING TRICK": "Backsolve with answer choices or estimate bounds before full computation.",
            "GMAT STRATEGY TIP": "Prioritize eliminations; avoid algebra unless needed.",
            "DIFFICULTY RATING": "medium - requires multi-step reasoning under time pressure.",
            "COMMON TRAP": "Exam-writer tests overconfidence in first-step setup.",
            "QUICK PRACTICE DRILL": "1) Solve 2x+5=19. 2) Which choice weakens a causal argument?",
            "ASSUMPTIONS_USED": ["Question may be incomplete or missing answer choices."],
        }
        if eli5_mode:
            base["ELI5"] = "Pretend each number is a puzzle piece; fit pieces slowly, then check if picture makes sense."
        if source_line:
            base["STEP-BY-STEP SOLUTION"] += source_line
        return base

    @staticmethod
    def _local_embedding(text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [b / 255.0 for b in digest[:64]]
