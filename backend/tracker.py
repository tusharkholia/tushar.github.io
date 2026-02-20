"""SQLite persistence and analytics for GMAT AI Coach."""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from backend.utils import json_dumps, json_loads, now_iso


class Tracker:
    def __init__(self, db_path: str = "db/gmat_coach.db") -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def initialize(self, schema_path: str = "db/schema.sql") -> None:
        with open(schema_path, "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())
        self.conn.commit()

    def create_user(self, name: str = "Learner") -> int:
        cur = self.conn.execute(
            "INSERT INTO users(name, created_at) VALUES (?, ?)",
            (name, now_iso()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_or_create_default_user(self) -> int:
        row = self.conn.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
        if row:
            return int(row["id"])
        return self.create_user()

    def log_question(self, user_id: int, question_text: str, qtype: str, tags: list[str]) -> int:
        cur = self.conn.execute(
            "INSERT INTO questions(user_id, question_text, type, tags, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, question_text, qtype, json_dumps(tags), now_iso()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def log_attempt(self, question_id: int, user_answer: str, correct: bool, time_taken_seconds: int) -> int:
        cur = self.conn.execute(
            "INSERT INTO attempts(question_id, user_answer, correct, time_taken_seconds, created_at) VALUES (?, ?, ?, ?, ?)",
            (question_id, user_answer, int(correct), time_taken_seconds, now_iso()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def recent_activity(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT q.question_text, q.type, q.tags, a.user_answer, a.correct, a.time_taken_seconds, a.created_at
            FROM attempts a JOIN questions q ON a.question_id=q.id
            ORDER BY a.created_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def weakness_metrics(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT q.tags, AVG(a.correct) as acc, AVG(a.time_taken_seconds) as avg_time, COUNT(*) as n
            FROM attempts a JOIN questions q ON q.id = a.question_id
            GROUP BY q.tags
            """
        ).fetchall()
        metrics = []
        for row in rows:
            tags = json_loads(row["tags"], ["general"])
            for tag in tags:
                metrics.append(
                    {
                        "tag": tag,
                        "accuracy": round(float(row["acc"] or 0) * 100, 1),
                        "avg_time": round(float(row["avg_time"] or 0), 1),
                        "attempts": int(row["n"] or 0),
                    }
                )
        return sorted(metrics, key=lambda x: (x["accuracy"], -x["avg_time"]))

    def score_trends(self) -> dict[str, list[Any]]:
        rows = self.conn.execute(
            "SELECT DATE(created_at) as d, AVG(correct) as acc, AVG(time_taken_seconds) as avg_t FROM attempts GROUP BY DATE(created_at) ORDER BY d"
        ).fetchall()
        out: dict[str, list[Any]] = defaultdict(list)
        for row in rows:
            out["date"].append(row["d"])
            out["accuracy"].append(round(float(row["acc"] or 0) * 100, 1))
            out["avg_time"].append(round(float(row["avg_t"] or 0), 1))
        out["estimated_score"] = [self._estimate_score(a) for a in out.get("accuracy", [])]
        return out

    @staticmethod
    def _estimate_score(acc_pct: float) -> int:
        return int(450 + (acc_pct / 100) * 300)

    def gamification(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT correct, DATE(created_at) d FROM attempts ORDER BY created_at").fetchall()
        xp = sum(20 if r["correct"] else 5 for r in rows)
        level = xp // 100 + 1
        dates = sorted({datetime.fromisoformat(r["d"]).date() for r in rows if r["d"]})
        streak = 0
        today = date.today()
        cursor = today
        while cursor in dates:
            streak += 1
            cursor -= timedelta(days=1)
        return {"xp": xp, "level": level, "streak": streak}
