"""Streamlit interface for AI Research & Deal Memo Generator."""
from __future__ import annotations

import asyncio
import json

import streamlit as st
import streamlit.components.v1 as components

from config import settings
from services.analysis_engine import AnalysisEngine
from services.exporter import memo_to_docx_bytes, memo_to_pdf_bytes
from services.research_engine import ResearchEngine

st.set_page_config(page_title="AI Research & Deal Memo Generator", page_icon="📈", layout="wide")

st.markdown(
    """
    <style>
        .stApp { background: linear-gradient(180deg, #0a0f1c 0%, #10182b 100%); color: #e5ecff; }
        h1, h2, h3 { color: #e5ecff !important; }
        .block-container { padding-top: 2rem; }
        .memo-card { background: #111d33; border-radius: 12px; padding: 1rem 1.25rem; border: 1px solid #223150; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📈 AI Research & Deal Memo Generator")
st.caption("Type a topic. The app researches the web and drafts an investment-grade memo.")

query = st.text_input(
    "Research topic / question",
    placeholder="e.g., SaaS valuation multiples 2025–2026",
)

col_a, col_b = st.columns([1, 3])
with col_a:
    generate_clicked = st.button("Generate Memo", type="primary", use_container_width=True)
with col_b:
    st.write("Preferred sources are credible financial/business outlets from the last 12 months.")

if generate_clicked:
    if not query.strip():
        st.warning("Please enter a research topic first.")
        st.stop()

    if not settings.openai_api_key:
        st.error("OPENAI_API_KEY is missing. Add it in your environment or .env file.")
        st.stop()

    with st.spinner("Running web research and analysis..."):
        engine = ResearchEngine(max_sources=settings.max_sources, timeout_seconds=settings.request_timeout_seconds)
        sources = asyncio.run(engine.research(query.strip()))

        if not sources:
            st.error("Could not extract enough credible source content. Try a broader query.")
            st.stop()

        analysis = AnalysisEngine()
        memo = analysis.generate_memo(query=query.strip(), sources=sources)

    st.success(f"Generated memo using {len(sources)} sources.")

    st.subheader("Memo")
    st.markdown('<div class="memo-card">', unsafe_allow_html=True)
    st.markdown(memo.replace("\n", "  \n"))
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Research sources"):
        for source in sources:
            st.markdown(f"- [{source.title}]({source.url}) ({source.source})")

    pdf_bytes = memo_to_pdf_bytes(memo)
    docx_bytes = memo_to_docx_bytes(memo)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Export PDF",
            data=pdf_bytes,
            file_name="deal_memo.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "Export Word (.docx)",
            data=docx_bytes,
            file_name="deal_memo.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

    escaped_memo = json.dumps(memo)
    components.html(
        f"""
        <button id="copy-btn" style="padding:10px 14px;border-radius:8px;border:none;background:#2f7df6;color:white;font-weight:600;cursor:pointer;">Copy Memo to Clipboard</button>
        <span id="copy-status" style="margin-left:10px;color:#9fd3ff;"></span>
        <script>
            const memo = {escaped_memo};
            const btn = document.getElementById('copy-btn');
            const status = document.getElementById('copy-status');
            btn.onclick = async () => {{
                try {{
                    await navigator.clipboard.writeText(memo);
                    status.textContent = 'Copied!';
                }} catch (e) {{
                    status.textContent = 'Clipboard unavailable in this browser session.';
                }}
            }};
        </script>
        """,
        height=60,
    )
