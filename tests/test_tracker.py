from backend.tracker import Tracker


def test_tracker_flow(tmp_path):
    db = tmp_path / "test.db"
    tracker = Tracker(str(db))
    tracker.initialize("db/schema.sql")
    uid = tracker.create_user("A")
    qid = tracker.log_question(uid, "If x+1=2", "quant_problem_solving", ["algebra"])
    tracker.log_attempt(qid, "1", True, 60)
    weakness = tracker.weakness_metrics()
    assert weakness[0]["accuracy"] == 100.0
