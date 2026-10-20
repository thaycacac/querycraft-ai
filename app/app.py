"""Demo Streamlit:  streamlit run app/app.py"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from querycraft.cli import build_agent  # noqa: E402

st.set_page_config(page_title="QueryCraft AI", page_icon="🔎", layout="wide")
st.title("QueryCraft AI: hỏi dữ liệu event bằng ngôn ngữ tự nhiên")

with st.sidebar:
    llm = st.text_input("LLM", "ollama:qwen3:8b", help="ollama:<model>, anthropic:<model>, openai:<model>")
    mode = st.radio("Chế độ", ["Agentic + Semantic layer", "Baseline (prompt đơn)"])
    st.caption("Ví dụ: 'DAU ngày 2026-01-15?', 'ARPPU của tháng 2/2026?', 'Doanh thu tháng 1?' (sẽ hỏi lại)")


@st.cache_resource
def get_agent(llm_spec: str, full: bool):
    return build_agent(llm_spec, full=full)


agent = get_agent(llm, mode.startswith("Agentic"))
q = st.text_input("Câu hỏi", "Doanh thu bán hàng tháng 1/2026 là bao nhiêu?")
if st.button("Hỏi") and q:
    with st.spinner("Đang xử lý..."):
        res = agent.run(q)
    if res.clarification:
        st.warning(res.clarification)
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("SQL")
            st.code(res.sql, language="sql")
            st.caption(f"Metric đã resolve: {res.resolved_metrics or '—'} · Số lần thử: {res.attempts} · {res.seconds:.1f}s")
            if res.error:
                st.error(res.error)
        with c2:
            st.subheader("Kết quả")
            try:
                cols, rows = agent.db.execute(res.sql, limit=100)
                st.dataframe([dict(zip(cols, r)) for r in rows])
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
