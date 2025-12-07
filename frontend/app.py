# frontend/app.py

import requests
import streamlit as st

# ======================================================================
# CONFIG
# ======================================================================

# If you run locally, change this to "http://127.0.0.1:8000"
API_BASE = "https://productdoc-autosuite.onrender.com"
GENERATE_URL = f"{API_BASE}/generate"
HISTORY_URL = f"{API_BASE}/history"

st.set_page_config(
    page_title="ProductDoc AutoSuite",
    page_icon="📄",
    layout="wide",
)


# ======================================================================
# STYLES
# ======================================================================

CUSTOM_CSS = """
<style>
body {
    background-color: #020617;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}
.big-hero {
    padding: 1.5rem 2rem;
    border-radius: 20px;
    background: radial-gradient(circle at top left, #1e293b, #020617);
    border: 1px solid rgba(148, 163, 184, 0.3);
}
.big-title {
    font-size: 2.8rem;
    font-weight: 800;
    letter-spacing: 0.03em;
    background: linear-gradient(90deg, #22d3ee, #a855f7, #f97316);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.4rem;
}
.big-subtitle {
    font-size: 0.98rem;
    color: #e5e7eb;
}
.section-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #e5e7eb;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 0.6rem;
}
.section-card {
    padding: 1rem 1.1rem;
    border-radius: 16px;
    background: linear-gradient(135deg, #020617, #020617);
    border: 1px solid rgba(148, 163, 184, 0.3);
}
.stTextArea textarea {
    background-color: #020617 !important;
    border-radius: 12px !important;
    border: 1px solid rgba(148, 163, 184, 0.5) !important;
    color: #e5e7eb !important;
}
.stSlider > div[data-baseweb="slider"] > div {
    background: linear-gradient(90deg,#fb7185,#a855f7,#22d3ee);
}
.result-card {
    padding: 0.8rem 1rem;
    border-radius: 14px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: radial-gradient(circle at top left, #020617, #020617);
    color: #e5e7eb;
    min-height: 200px;
    font-size: 0.94rem;
    line-height: 1.5;
}
.badge {
    display: inline-block;
    padding: 0.18rem 0.55rem;
    border-radius: 999px;
    background: rgba(148,163,184,0.15);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: #9ca3af;
    margin-bottom: 0.2rem;
}
.error-banner {
    padding: 0.6rem 0.9rem;
    border-radius: 12px;
    background: #450a0a;
    border: 1px solid #b91c1c;
    color: #fecaca;
    font-size: 0.9rem;
}
.history-item {
    padding: 0.5rem 0.6rem;
    border-radius: 10px;
    border: 1px solid rgba(148,163,184,0.25);
    margin-bottom: 0.35rem;
    cursor: default;
}
.history-brief {
    font-size: 0.85rem;
    color: #e5e7eb;
}
.history-meta {
    font-size: 0.75rem;
    color: #9ca3af;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ======================================================================
# BACKEND HELPERS
# ======================================================================

def call_generate(brief: str, depth: int):
    """Call backend /generate endpoint."""
    try:
        payload = {"brief": brief, "depth": depth}
        resp = requests.post(GENERATE_URL, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"Backend error {resp.status_code}: {resp.text}"
    except Exception as e:
        return None, f"Request failed: {e}"


def load_history():
    """Load last 10 generations from backend."""
    try:
        resp = requests.get(HISTORY_URL, timeout=20)
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"Could not load history from backend (status {resp.status_code})."
    except Exception as e:
        return None, f"Could not load history from backend: {e}"


# ======================================================================
# UI LAYOUT
# ======================================================================

# Hero
with st.container():
    st.markdown(
        """
        <div class="big-hero">
            <div class="big-title">ProductDoc AutoSuite</div>
            <div class="big-subtitle">
                Turn a short product idea into a PRD, landing page, and FAQ – powered by AI.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

left, right = st.columns([1.4, 1.1], gap="large")

# ----------------------------------------------------------------------
# LEFT COLUMN – INPUT + RESULTS
# ----------------------------------------------------------------------
with left:
    st.markdown(
        '<div class="section-title">🧠 Product Brief</div>',
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        brief = st.text_area(
            "",
            placeholder=(
                "Example: AI tool that helps small businesses create marketing "
                "content automatically using templates."
            ),
            height=130,
        )

        depth = st.slider(
            "Depth (detail level)",
            min_value=1,
            max_value=3,
            value=2,
            help="1 = short draft, 3 = deep detailed document",
        )

        generate_clicked = st.button("Generate", type="primary")
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    # Results area
    st.markdown(
        '<div class="section-title">📄 Generated Documents</div>',
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["PRD", "Landing Page", "FAQ"])

    if "last_output" not in st.session_state:
        st.session_state.last_output = {}

    error_msg = None

    if generate_clicked:
        if not brief.strip():
            error_msg = "Please write a short product brief before generating."
        else:
            with st.spinner("Calling backend and generating documents..."):
                output, err = call_generate(brief.strip(), depth)
            if err:
                error_msg = err
            else:
                st.session_state.last_output = output or {}

    if error_msg:
        st.markdown(
            f'<div class="error-banner">{error_msg}</div>',
            unsafe_allow_html=True,
        )

    # Show outputs (or placeholders)
    prd_text = st.session_state.last_output.get("PRD", "No PRD generated yet.")
    lp_text = st.session_state.last_output.get("Landing Page", "No landing page generated yet.")
    faq_text = st.session_state.last_output.get("FAQ", "No FAQ generated yet.")

    with tabs[0]:
        st.markdown('<div class="badge">Product Requirements Document</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="result-card">{prd_text.replace("\\n", "<br>")}</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.markdown('<div class="badge">Landing Page Copy</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="result-card">{lp_text.replace("\\n", "<br>")}</div>', unsafe_allow_html=True)

    with tabs[2]:
        st.markdown('<div class="badge">FAQ</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="result-card">{faq_text.replace("\\n", "<br>")}</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------
# RIGHT COLUMN – HISTORY
# ----------------------------------------------------------------------
with right:
    st.markdown(
        '<div class="section-title">📊 History (last 10)</div>',
        unsafe_allow_html=True,
    )

    hist, hist_error = load_history()

    with st.container():
        st.markdown('<div class="section-card">', unsafe_allow_html=True)

        if hist_error:
            st.markdown(
                f'<div class="error-banner">{hist_error}</div>',
                unsafe_allow_html=True,
            )
        else:
            if not hist:
                st.write("No history yet. Generate something first 🙂")
            else:
                for item in hist:
                    st.markdown(
                        f"""
                        <div class="history-item">
                            <div class="history-brief">{item.get("brief","")[:120]}...</div>
                            <div class="history-meta">
                                depth={item.get("depth", "")} • id={item.get("id","")}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.markdown("</div>", unsafe_allow_html=True)
