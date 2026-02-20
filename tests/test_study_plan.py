from datetime import date, timedelta

from backend.study_plan import PlanInput, build_study_plan


def test_study_plan_generation():
    exam = date.today() + timedelta(days=30)
    plan = build_study_plan(
        PlanInput(
            baseline_score=600,
            target_score=700,
            exam_date=str(exam),
            weekly_hours=10,
            days_off=["Sunday"],
            weakness_profile=[{"tag": "probability", "accuracy": 50, "avg_time": 140}],
        )
    )
    assert plan["summary"]["score_gap"] == 100
    assert plan["daily_plan"]
