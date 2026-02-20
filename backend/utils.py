"""Utility helpers for GMAT AI Coach."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

QUESTION_TYPES = {
    "quant_problem_solving": ["solve", "equation", "value of", "integer", "ratio", "probability"],
    "quant_data_sufficiency": ["statement (1)", "statement (2)", "data sufficiency"],
    "verbal_cr": ["argument", "assumption", "strengthen", "weaken", "conclusion"],
    "verbal_rc": ["passage", "author", "inference", "according to"],
    "verbal_sc": ["sentence correction", "grammar", "underlined"],
}


def bootstrap_env() -> None:
    """Load env vars from .env if present."""
    load_dotenv(override=False)


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def classify_question(question_text: str) -> str:
    """Best-effort classifier for GMAT question type."""
    q = question_text.lower()
    for label, hints in QUESTION_TYPES.items():
        if any(h in q for h in hints):
            return label
    if any(ch in question_text for ch in ["A)", "B)", "C)", "D)"]) or "=" in question_text:
        return "quant_problem_solving"
    return "verbal_cr"


def extract_tags(question_text: str) -> list[str]:
    """Infer topic tags from keywords."""
    tag_map = {
        "algebra": ["equation", "variable", "linear", "quadratic"],
        "geometry": ["triangle", "circle", "angle", "radius", "area"],
        "number_properties": ["integer", "divisible", "prime", "factor"],
        "probability": ["probability", "likely", "random"],
        "critical_reasoning": ["assumption", "strengthen", "weaken"],
        "reading_comprehension": ["passage", "author", "inference"],
        "sentence_correction": ["grammar", "sentence", "underlined"],
    }
    q = question_text.lower()
    tags = [name for name, keys in tag_map.items() if any(key in q for key in keys)]
    return tags or ["general"]


def sanitize_pdf_text(text: str) -> str:
    """Remove control chars from extracted PDF text."""
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def json_loads(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def get_feature_mode() -> str:
    return os.getenv("FEATURE_TIER", "free").lower()


def can_use_pro_feature() -> bool:
    return get_feature_mode() == "pro"


def ensure_path(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
