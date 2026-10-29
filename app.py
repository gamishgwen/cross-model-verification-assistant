import streamlit as st
from datetime import datetime
import html
import os
import json

from dotenv import load_dotenv
from answer_engine import generate_answer

load_dotenv()

st.set_page_config(page_title="CrossVerify AI", page_icon="✦", layout="wide", initial_sidebar_state="expanded")

st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], [data-testid="stApp"] {font-family:'DM Sans',sans-serif!important;}
[data-testid="stAppViewContainer"] {background:#f6f9fd;}
[data-testid="stHeader"] {background:transparent;}
.block-container {max-width:1280px;padding:2rem 2.5rem 5rem;}
[data-testid="stSidebar"] {background:#fff;border-right:1px solid #e5ebf2;}
[data-testid="stSidebar"] .block-container {padding-top:2rem;}
[data-testid="stSidebar"] button {text-align:left;}
h1,h2,h3 {color:#182944!important;letter-spacing:-.035em!important;}
h1 {font-size:2rem!important;font-weight:800!important;}
h3 {font-size:1.15rem!important;}
p,li {color:#43546b;}
[data-testid="stTextArea"] textarea {background:#fff;border:1px solid #dbe4ef;border-radius:12px;padding:14px;color:#1f3046;}
[data-testid="stTextArea"] textarea:focus {border-color:#6c8cd9;box-shadow:0 0 0 2px #dbe7fd;}
[data-testid="stButton"] button[kind="primary"] {background:#3157b8;border:1px solid #3157b8;border-radius:10px;font-weight:700;padding:.65rem 1.2rem;}
[data-testid="stButton"] button[kind="primary"]:hover {background:#24469e;border-color:#24469e;}
[data-testid="stButton"] button[kind="primary"] p {color:#fff!important;font-weight:700!important;}
[data-testid="stButton"] button[kind="secondary"] {border-radius:10px;border-color:#d7e1ee;color:#30435c;background:#fff;}
[data-testid="stButton"] button {min-height:42px;}
[data-testid="stMetric"] {background:#fff;border:1px solid #e3eaf3;border-radius:13px;padding:12px 16px;}
[data-testid="stExpander"] {background:#fff;border:1px solid #e3eaf3!important;border-radius:12px!important;}
[data-testid="stAlert"] {border-radius:12px;}
[data-testid="stSelectbox"]>div>div {border-radius:10px;}
.cv-brand {display:flex;align-items:center;gap:11px;margin:4px 0 18px;}
.cv-mark {width:37px;height:37px;background:#e9f1ff;color:#3157b8;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:23px;font-weight:800;}
.cv-name {font-size:19px;font-weight:800;color:#172b48;letter-spacing:-.03em;}
.cv-slogan {color:#7c8a9d;font-size:11px;}
.cv-label {font-size:11px;letter-spacing:.13em;text-transform:uppercase;font-weight:800;color:#8c9bab;margin:16px 0 9px;}
.cv-nav {padding:11px 13px;border-radius:9px;font-size:14px;font-weight:600;color:#65758b;margin-bottom:5px;}
.cv-nav.on {background:#ecf3ff;color:#3157b8;}
.cv-sidefoot {font-size:12px;color:#8795a8;padding-top:18px;}
.cv-top {display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 22px;}
.cv-crumb {font-size:13px;color:#8090a6;}
.cv-crumb strong {color:#3c506e;}
.cv-dot {display:inline-block;width:8px;height:8px;background:#35b88a;border-radius:50%;margin-right:7px;}
.cv-status {font-size:12px;font-weight:700;color:#547164;background:#e8f7f0;padding:7px 11px;border-radius:30px;}
.cv-hero {padding:24px 28px;border-radius:16px;border:1px solid #dce7f2;background:linear-gradient(120deg,#fff 25%,#eff6ff);margin-bottom:19px;}
.cv-hero h1 {margin:0 0 6px;font-size:30px!important;}
.cv-hero p {margin:0;color:#64748b;font-size:14px;}
.cv-card {border:1px solid #e0e8f2;background:#fff;border-radius:14px;padding:19px 21px;margin:13px 0;box-shadow:0 3px 14px rgba(38,67,110,.025);}
.cv-card-title {font-weight:800;color:#203650;font-size:15px;margin-bottom:6px;}
.cv-muted {color:#77879a;font-size:13px;}
.cv-pill {display:inline-block;background:#ebf5ee;color:#258351;border-radius:20px;padding:5px 10px;font-size:12px;font-weight:700;}
.cv-pill.demo {background:#edf3ff;color:#3662b0;}
.cv-answer {white-space:pre-wrap;font-size:15px;line-height:1.75;color:#34445b;}
.cv-step {background:#f7faff;border:1px solid #e6edf7;border-radius:10px;padding:12px;font-size:13px;color:#586a80;}
.cv-divider {height:1px;background:#e9eef5;margin:16px 0;}
</style>
''', unsafe_allow_html=True)

DEMO_QUESTIONS = {
    "SaaS onboarding": {
        "question": "How can a SaaS company reduce onboarding time without compromising integration quality?",
        "initial": "Automate onboarding and improve documentation.",
        "feedback": "The initial answer is too general. It lacks technical implementation steps, QA controls, and measurable outcomes.",
        "refined": "A SaaS team can reduce onboarding time by standardizing the integration discovery checklist, providing reusable API templates and sandbox credentials, and automating preflight checks for authentication, webhooks, and payload formats.\n\nKeep quality gates for test transactions, error handling, security, and a documented handoff before production access.\n\nTrack time to first successful API call, integration defects, and onboarding completion time. Pilot the workflow with a small cohort and compare results before broader rollout.",
    },
    "API troubleshooting": {
        "question": "How should I troubleshoot intermittent 401 errors in a REST API integration?",
        "initial": "Check the API key and retry the request.",
        "feedback": "Needs a structured diagnosis of tokens, timing, headers, permissions, and safer logging.",
        "refined": "Start by correlating failed requests using timestamps and request IDs. Check whether failures coincide with token expiry or refresh, clock skew, missing Authorization headers, or requests routed through different environments.\n\nInspect token scopes and permissions, verify refresh handling under concurrent load, and compare a successful and failed request with sensitive values redacted.\n\nAdd safe observability around authentication failures and test a fix in staging before production deployment.",
    },
    "Knowledge assistant": {
        "question": "What would make an internal AI knowledge assistant more reliable?",
        "initial": "Use RAG and a good language model.",
        "feedback": "Needs source quality controls, citations, retrieval evaluation, access permissions, and abstention behavior.",
        "refined": "Use retrieval-augmented generation with a curated, permission-aware document index. Preserve document freshness and ownership, show citations to source passages, and teach the system to say when evidence is missing.\n\nEvaluate retrieval relevance separately from answer quality on a representative question set. Add red-team tests for prompt injection and confidential data leakage.\n\nMonitor user feedback, unsupported claims, and answer latency; route high-impact or low-evidence questions to a human expert.",
    },
}

def clear_question():
    st.session_state["question"] = ""
    st.session_state["result"] = None


if "demo" not in st.session_state:
    st.session_state.demo = "SaaS onboarding"
if "question" not in st.session_state:
    st.session_state.question = DEMO_QUESTIONS[st.session_state.demo]["question"]
if "result" not in st.session_state:
    st.session_state.result = None
if "history" not in st.session_state:
    st.session_state.history = []
if "mode" not in st.session_state:
    st.session_state.mode = "Live AI"

with st.sidebar:
    st.markdown('<div class="cv-brand"><div class="cv-mark">✦</div><div><div class="cv-name">CrossVerify AI</div><div class="cv-slogan">ANSWER INTELLIGENCE</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="cv-label">WORKSPACE</div>', unsafe_allow_html=True)
    st.markdown('<div class="cv-nav on">⌕ &nbsp; Answer workspace</div>', unsafe_allow_html=True)
    st.markdown('<div class="cv-nav">◷ &nbsp; Recent sessions</div>', unsafe_allow_html=True)
    st.markdown('<div class="cv-nav">▤ &nbsp; Verification details</div>', unsafe_allow_html=True)
    st.markdown('<div class="cv-label">ANSWER MODE</div>', unsafe_allow_html=True)
    st.radio("Answer mode", ["Live AI", "Offline demo"], key="mode", label_visibility="collapsed")
    st.markdown('<div class="cv-label">QUICK EXAMPLES</div>', unsafe_allow_html=True)
    for key in DEMO_QUESTIONS:
        if st.button(key, key=f"example-{key}", use_container_width=True):
            st.session_state.demo = key
            st.session_state.question = DEMO_QUESTIONS[key]["question"]
            st.session_state.result = None
            st.rerun()
    st.markdown('<div class="cv-sidefoot">Live AI uses paid API calls.<br>Demo mode is offline and limited to example questions.</div>', unsafe_allow_html=True)

st.markdown('<div class="cv-top"><div class="cv-crumb">Workspace / <strong>Answer assistant</strong></div><div class="cv-status"><span class="cv-dot"></span>'+("Live AI" if st.session_state.mode == "Live AI" else "Demo environment")+'</div></div>', unsafe_allow_html=True)
st.markdown('<div class="cv-hero"><h1>Find a better answer.</h1><p>Explore how independent AI review can strengthen clarity, completeness, and answer quality.</p></div>', unsafe_allow_html=True)

left, right = st.columns([3.2, 1.1], gap="large")
with left:
    st.markdown('<div class="cv-card-title">Your question</div><div class="cv-muted">Describe a problem or select an example from the sidebar.</div>', unsafe_allow_html=True)
    question = st.text_area("Question", key="question", label_visibility="collapsed", height=120)
    a, b = st.columns([2, 1])
    with a:
        clicked = st.button("✦  Get refined answer", type="primary", use_container_width=True)
    with b:
        st.button("Clear", use_container_width=True, on_click=clear_question)
with right:
    st.markdown('<div class="cv-card"><div class="cv-card-title">Verification approach</div><div class="cv-muted">Initial response → Independent review → Answer refinement</div><div class="cv-divider"></div><div class="cv-step">① Generate an initial answer</div><br><div class="cv-step">② Identify missing details</div><br><div class="cv-step">③ Improve the final response</div></div>', unsafe_allow_html=True)

if clicked:
    q = question.strip()
    if not q:
        st.warning("Enter a question or choose an example.")
    elif st.session_state.mode == "Offline demo":
        matched = next((k for k, d in DEMO_QUESTIONS.items() if d["question"].strip().lower() == q.lower()), None)
        if matched:
            st.session_state.result = {**DEMO_QUESTIONS[matched], "live": False}
            st.session_state.history.insert(0, {"question": q, "status": "Demo"})
        else:
            st.session_state.result = None
            st.info("Offline demo has only three preset examples. Select Live AI for other questions.")
    else:
        try:
            with st.status("Generating and refining your answer…", expanded=True) as status:
                st.write("OpenAI is drafting; Claude is reviewing; OpenAI is refining. This involves paid API calls.")
                output = generate_answer(q)
                status.update(label="Refined answer ready", state="complete", expanded=False)
            st.session_state.result = {
                "question": q,
                "initial": output.initial,
                "feedback": output.feedback,
                "refined": output.refined,
                "uncertainties": output.uncertainties,
                "live": True,
            }
            st.session_state.history.insert(0, {"question": q, "status": "Refined"})
        except Exception as exc:
            st.session_state.result = None
            st.error(f"Could not generate an answer: {type(exc).__name__}: {exc}")
            st.caption("Check your .env keys, model access, account credits, and terminal output. Do not share API keys.")

if st.session_state.result:
    result = st.session_state.result
    tag = "Live model refinement · Not independently fact-checked" if result.get("live") else "Illustrative example · Not live AI output"
    st.markdown('<div class="cv-card"><div class="cv-pill demo">'+tag+'</div><h3 style="margin:14px 0 8px">Refined answer</h3></div>', unsafe_allow_html=True)
    st.markdown(result['refined'])
    if result.get('live'):
        st.caption(result.get('uncertainties', 'Model review does not guarantee factual accuracy.'))
    with st.expander("View answer refinement details", expanded=False):
        st.caption("Raw review text — no Markdown interpretation. Copy or download the evaluation record below.")
        st.markdown("**Initial answer**")
        st.code(str(result.get("initial", "")), language=None, wrap_lines=True)
        st.markdown("**Claude reviewer observations**" if result.get("live") else "**Example reviewer observations**")
        st.code(str(result.get("feedback", "")), language=None, wrap_lines=True)
        st.markdown("**Refined response**")
        st.code(str(result.get("refined", "")), language=None, wrap_lines=True)
        if not result.get("live"):
            st.caption("All examples are prewritten and not checked by live models.")
        record = {
            "question": result.get("question", ""),
            "initial_answer": str(result.get("initial", "")),
            "reviewer_feedback": str(result.get("feedback", "")),
            "refined_answer": str(result.get("refined", "")),
            "uncertainties": str(result.get("uncertainties", "")),
            "mode": "live" if result.get("live") else "demo",
        }
        st.download_button(
            "Download evaluation record (JSON)",
            data=json.dumps(record, indent=2, ensure_ascii=False),
            file_name="crossverify-evaluation.json",
            mime="application/json",
            key="download_evaluation_record",
        )
    st.download_button("Download answer", data=result['refined'], file_name="crossverify-answer.txt", mime="text/plain")
else:
    st.markdown('<div class="cv-card"><div class="cv-card-title">Answer workspace</div><div class="cv-muted">Ask a question and click “Get refined answer” to generate and review a response.</div></div>', unsafe_allow_html=True)

st.caption("CrossVerify AI · Model-based refinement is not a guarantee of factual correctness")
