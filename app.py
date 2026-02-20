"""GMAT AI Coach Streamlit app."""
from __future__ import annotations

import asyncio
import csv
import io
import json
from datetime import date

import pandas as pd
import streamlit as st

from backend.explain_engine import ExplainEngine
from backend.monetization import FeatureGate, create_stripe_checkout_session_stub
from backend.pdf_ingest import ingest_pdfs
from backend.study_plan import PlanInput, build_study_plan
from backend.tracker import Tracker
from backend.utils import bootstrap_env, classify_question, extract_tags, now_iso
from backend.vectorstore import VectorStore

bootstrap_env()
st.set_page_config(page_title="GMAT AI Coach", page_icon="🎯", layout="wide")

if "theme" not in st.session_state:
    st.session_state.theme = True
if "last_explanation" not in st.session_state:
    st.session_state.last_explanation = None
if "leaderboard" not in st.session_state:
    st.session_state.leaderboard = [{"name": "You", "score": 0}]

tracker = Tracker()
tracker.initialize()
user_id = tracker.get_or_create_default_user()
vector_store = VectorStore()
engine = ExplainEngine(vector_store=vector_store)
gate = FeatureGate(free_daily_limit=5)

st.title("🎯 GMAT AI Coach")
st.caption("This app is a study aid and not an official GMAT product.")

with st.sidebar:
    st.subheader("Profile")
    game = tracker.gamification()
    trends = tracker.score_trends()
    estimate = trends.get("estimated_score", [550])[-1] if trends.get("estimated_score") else 550
    st.metric("🔥 Streak", game["streak"])
    st.metric("⭐ XP", game["xp"])
    st.metric("🏁 Level", game["level"])
    st.metric("📈 Est. Score", estimate)
    st.toggle("Dark mode", key="theme", value=True)
    st.write("---")
    st.subheader("Monetization")
    st.code(json.dumps(create_stripe_checkout_session_stub("price_pro", "https://success", "https://cancel"), indent=2))

left, center, right = st.columns([1, 2, 1])

with left:
    st.subheader("Daily Challenge")
    st.info("Question: If 3x = 24, x = ? (30 seconds)")
    if st.button("Submit Daily Challenge (+10 XP)"):
        st.session_state.leaderboard[0]["score"] += 10
    st.dataframe(pd.DataFrame(st.session_state.leaderboard), use_container_width=True)

with center:
    st.subheader("Ask a GMAT Question")
    question = st.text_area("", placeholder="Paste GMAT question here (or type)", height=170)
    c1, c2, c3 = st.columns(3)
    with c1:
        explain_using_notes = st.toggle("Explain using my notes")
    with c2:
        eli5_mode = st.toggle("Explain like I am 5")
    with c3:
        st.toggle("Reveal answer (Space)")

    st.markdown("Keyboard shortcuts: **Ctrl+Enter** submit, **Space** reveal answer")

    if st.button("Explain & Coach", type="primary", use_container_width=True):
        attempts_today = len([r for r in tracker.recent_activity(200) if str(date.today()) in r["created_at"]])
        allowed, msg = gate.can_explain(attempts_today)
        if not allowed:
            st.warning(msg)
        elif not question.strip():
            st.warning("Please provide a GMAT question.")
        else:
            with st.spinner("Thinking like an elite tutor..."):
                resp = engine.explain(question, explain_using_notes=explain_using_notes, eli5_mode=eli5_mode)
                st.session_state.last_explanation = resp
                qid = tracker.log_question(user_id, question, classify_question(question), extract_tags(question))
                st.session_state.last_question_id = qid

    if st.session_state.last_explanation:
        resp = st.session_state.last_explanation
        for key, value in resp.items():
            with st.expander(key, expanded=key in ["ANSWER", "STEP-BY-STEP SOLUTION"]):
                st.write(value)

        if st.button("Practice Similar"):
            for i, q in enumerate(engine.generate_similar(question), start=1):
                st.write(f"{i}. {q}")

        with st.form("attempt_form"):
            user_answer = st.text_input("Your answer")
            correct_answer = st.text_input("Correct answer (for logging)")
            time_taken = st.number_input("Time taken (seconds)", min_value=5, max_value=600, value=120)
            if st.form_submit_button("Log Attempt"):
                correct = user_answer.strip().lower() == correct_answer.strip().lower()
                tracker.log_attempt(st.session_state.last_question_id, user_answer, correct, int(time_taken))
                st.success("Attempt logged.")

with right:
    st.subheader("Weakness Heatmap")
    weakness = tracker.weakness_metrics()
    if weakness:
        st.dataframe(pd.DataFrame(weakness), use_container_width=True)
    else:
        st.caption("No attempts yet.")

    st.subheader("Study Plan")
    with st.form("study_plan"):
        baseline = st.number_input("Baseline", 200, 800, 600)
        target = st.number_input("Target", 200, 800, 700)
        exam_date = st.date_input("Exam date")
        weekly_hours = st.slider("Weekly hours", 2, 30, 12)
        days_off = st.multiselect("Days off", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], ["Sunday"])
        if st.form_submit_button("Create Study Plan"):
            plan = build_study_plan(PlanInput(baseline, target, str(exam_date), int(weekly_hours), days_off, weakness))
            tracker.conn.execute("INSERT INTO study_plans(user_id, plan_json, created_at) VALUES (?, ?, ?)", (user_id, json.dumps(plan), now_iso()))
            tracker.conn.commit()
            st.session_state.plan = plan

    if st.session_state.get("plan"):
        st.json(st.session_state.plan["summary"])

st.write("---")
st.subheader("Upload Reference PDFs (optional)")
uploaded = st.file_uploader("Upload one or more PDFs", type=["pdf"], accept_multiple_files=True)
if uploaded and st.button("Ingest PDFs"):
    paths = []
    for f in uploaded:
        path = f"example_data/uploads/{f.name}"
        with open(path, "wb") as out:
            out.write(f.getvalue())
        paths.append(path)
    with st.spinner("Extracting + indexing PDFs locally..."):
        ingested = asyncio.run(ingest_pdfs(paths, vector_store, tracker))
    st.success(f"Indexed {ingested} chunks from {len(paths)} PDF(s).")
    st.caption("Privacy: uploads stay local unless you configure cloud sync.")

activity = tracker.recent_activity(50)
if activity:
    st.subheader("Exports")
    csv_buf = io.StringIO()
    writer = csv.DictWriter(csv_buf, fieldnames=list(activity[0].keys()))
    writer.writeheader()
    writer.writerows(activity)
    st.download_button("Export Data CSV", csv_buf.getvalue(), "gmat_activity.csv", "text/csv")

    txt = "\n".join(["GMAT AI Coach Report"] + [f"{r['created_at']} | {r['type']} | correct={r['correct']}" for r in activity[:10]])
    st.download_button("Export PDF Report (paywall hook)", txt.encode("utf-8"), "gmat_report.pdf", "application/pdf")
