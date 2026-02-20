"""Streamlit UI for PE Lens – Mid-Market Deal Intelligence Platform."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from analysis_engine import AnalysisEngine
from config import settings
from data_collection import DealResearchEngine
from report_generator import deals_csv_bytes, render_markdown_report, report_to_docx_bytes, report_to_pdf_bytes

st.set_page_config(page_title="PE Lens", page_icon="🔎", layout="wide")

st.markdown(
    """
    <style>
      .stApp { background: linear-gradient(180deg,#0b0f1a 0%, #10182c 100%); color: #dbe6ff; }
      h1,h2,h3,h4,p,label { color: #dbe6ff !important; }
      [data-testid="stSidebar"] { background: #0d1525; }
      .panel { background:#111d32; border:1px solid #223353; border-radius:12px; padding:1rem; }
      .small-note { color:#9ab0d6; font-size:0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🔎 PE Lens – Mid-Market Deal Intelligence Platform")
st.caption("Live web deal research, valuation extraction, trend analytics, and institutional-grade memo generation.")

query = st.text_input(
    "Sector, geography, or theme",
    placeholder="US Mid-Market Healthcare IT Deals 2026",
)

if st.button("Generate Intelligence Report", type="primary", use_container_width=True):
    if not query.strip():
        st.warning("Please enter a query.")
        st.stop()
    if not settings.openai_api_key:
        st.error("OPENAI_API_KEY is required.")
        st.stop()

    with st.spinner("Collecting market data and generating report..."):
        research_engine = DealResearchEngine()
        deals, sources = research_engine.build_deal_universe(query.strip())

        if not deals:
            st.error("No qualifying deals extracted. Try broadening query terms.")
            st.stop()

        analysis_engine = AnalysisEngine()
        analysis = analysis_engine.generate_structured_analysis(query.strip(), deals)
        report_md = render_markdown_report(query.strip(), analysis, deals)

    st.success(f"Report generated with {len(deals)} deals from {len(sources)} researched sources.")

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(report_md)
    st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("Recent Deal Snapshot")
    table = pd.DataFrame(
        [
            {
                "Date": d.date,
                "Target": d.target,
                "Acquirer": d.acquirer,
                "Deal Size": d.deal_size,
                "Valuation Multiple": d.valuation_multiple,
                "Strategic Rationale": d.strategic_rationale,
            }
            for d in deals
        ]
    )
    st.dataframe(table, use_container_width=True)

    with st.expander("Source evidence"):
        for s in sources:
            st.markdown(f"- [{s.title}]({s.url}) • {s.outlet} • {s.published or 'Date unavailable'}")

    title = analysis.get("title", f"PE Lens Report - {query.strip()}")
    pdf_file = report_to_pdf_bytes(report_md, title)
    docx_file = report_to_docx_bytes(report_md, title)
    csv_file = deals_csv_bytes(deals)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("Export PDF", pdf_file, "pe_lens_report.pdf", "application/pdf", use_container_width=True)
    with c2:
        st.download_button(
            "Export Word",
            docx_file,
            "pe_lens_report.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    with c3:
        st.download_button("Download Deal CSV", csv_file, "pe_lens_deals.csv", "text/csv", use_container_width=True)

    memo_json = json.dumps(report_md)
    components.html(
        f"""
        <button id="copy-btn" style="padding:9px 14px;border-radius:8px;border:none;background:#2f7df6;color:white;font-weight:700;">Copy to Clipboard</button>
        <span id="status" style="margin-left:10px;color:#9ab0d6;"></span>
        <script>
          const memo = {memo_json};
          document.getElementById('copy-btn').onclick = async () => {{
            try {{
              await navigator.clipboard.writeText(memo);
              document.getElementById('status').textContent = 'Copied';
            }} catch (err) {{
              document.getElementById('status').textContent = 'Clipboard access unavailable';
            }}
          }};
        </script>
        """,
        height=55,
    )

st.markdown("<p class='small-note'>Built for PE funds, IB boutiques, independent sponsors, and corp dev teams.</p>", unsafe_allow_html=True)
