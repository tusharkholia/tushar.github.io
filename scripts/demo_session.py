"""CLI demo for GMAT AI Coach core flow."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.explain_engine import ExplainEngine
from backend.study_plan import PlanInput, build_study_plan
from backend.tracker import Tracker
from backend.utils import classify_question, extract_tags
from backend.vectorstore import VectorStore


def run_demo() -> None:
    tracker = Tracker("db/demo.db")
    tracker.initialize()
    user_id = tracker.get_or_create_default_user()
    engine = ExplainEngine(VectorStore())

    question = "If x + 2 = 9, what is x? A)5 B)6 C)7 D)8"
    explanation = engine.explain(question)
    qid = tracker.log_question(user_id, question, classify_question(question), extract_tags(question))
    tracker.log_attempt(qid, "C", True, 50)

    print("Explanation keys:", list(explanation.keys()))
    print("Weakness:", tracker.weakness_metrics())

    plan = build_study_plan(
        PlanInput(
            baseline_score=600,
            target_score=700,
            exam_date="2026-05-30",
            weekly_hours=12,
            days_off=["Sunday"],
            weakness_profile=tracker.weakness_metrics(),
        )
    )
    print("Plan summary:", plan["summary"])


if __name__ == "__main__":
    run_demo()
