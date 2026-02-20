"""Adaptive study plan generation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any


@dataclass
class PlanInput:
    baseline_score: int
    target_score: int
    exam_date: str
    weekly_hours: int
    days_off: list[str]
    weakness_profile: list[dict[str, Any]]


def build_study_plan(payload: PlanInput) -> dict[str, Any]:
    exam = date.fromisoformat(payload.exam_date)
    today = date.today()
    weeks = max(1, (exam - today).days // 7)

    weaknesses = sorted(payload.weakness_profile, key=lambda x: (x.get("accuracy", 100), -x.get("avg_time", 0)))
    focus_topics = [w["tag"] for w in weaknesses[:4]] or ["algebra", "critical_reasoning"]

    daily_minutes = max(30, int((payload.weekly_hours * 60) / 5))
    plan_days = []
    d = today
    while d <= exam:
        day_name = d.strftime("%A")
        if day_name in payload.days_off:
            plan_days.append({"date": str(d), "focus": "Recovery / light review", "minutes": 0, "tasks": ["Flashcards + error log"]})
        else:
            topic = focus_topics[(d - today).days % len(focus_topics)]
            plan_days.append(
                {
                    "date": str(d),
                    "focus": topic,
                    "minutes": daily_minutes,
                    "tasks": [
                        f"15 min concept review on {topic}",
                        f"{max(8, daily_minutes // 10)} timed questions",
                        "10 min error log reflection",
                    ],
                }
            )
        d += timedelta(days=1)

    return {
        "summary": {
            "weeks_remaining": weeks,
            "score_gap": payload.target_score - payload.baseline_score,
            "priority_topics": focus_topics,
        },
        "weekly_template": {
            "target_hours": payload.weekly_hours,
            "mock_test_every_n_weeks": 2,
        },
        "daily_plan": plan_days,
    }
