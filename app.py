"""
Streamlit UI for the Resume Screening Panel.

    streamlit run app.py
"""
import html
import json

import pandas as pd
import streamlit as st

import config
from orchestrator import PIPELINE, ResumePanel
from utils.exporter import results_table, to_csv, to_pdf
from utils.logger import PanelLogger
from utils.parser import candidate_name, read_document, read_path

st.set_page_config(page_title="Resume Screening Panel", page_icon="🧑‍💼", layout="wide")

AGENT_INFO = {
    "JD Analyst Agent": ("🧠", "Extracts must-have / nice-to-have skills, experience and qualifications"),
    "Screener Agent": ("📊", "Scores every resume 0-100 with a per-skill breakdown"),
    "Bias Checker Agent": ("⚖️", "Flags unfair reasoning and corrects the scores"),
    "HR Summary Agent": ("📝", "Ranks candidates, recommends and drafts interview questions"),
}
STATE_STYLE = {
    "waiting": ("#94a3b8", "#f1f5f9", "Waiting"),
    "running": ("#d97706", "#fef3c7", "Working…"),
    "done": ("#16a34a", "#dcfce7", "Done"),
}

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
.agent-card {border-radius: 10px; padding: 12px 14px; min-height: 150px;
             border: 2px solid var(--b); background: var(--bg); color: #0f172a;}
.agent-card h4 {margin: 0 0 4px 0; font-size: 1rem; color: #0f172a;}
.agent-card .state {font-weight: 700; color: var(--b); font-size: .85rem;}
.agent-card .detail {font-size: .8rem; color: #334155; margin-top: 6px;}
.agent-card .role {font-size: .78rem; color: #475569;}
.mode-badge {display:inline-block; padding:4px 10px; border-radius:999px;
             background:#e0e7ff; color:#3730a3; font-size:.8rem; font-weight:600;}
</style>
""", unsafe_allow_html=True)


def agent_card(name: str, state: str, detail: str = "") -> str:
    border, bg, label = STATE_STYLE[state]
    icon, role = AGENT_INFO[name]
    step = PIPELINE.index(name) + 1
    return (f'<div class="agent-card" style="--b:{border};--bg:{bg}">'
            f'<h4>{icon} Agent {step}: {html.escape(name)}</h4>'
            f'<div class="role">{html.escape(role)}</div>'
            f'<div class="state">● {label}</div>'
            f'<div class="detail">{html.escape(detail)}</div></div>')


def load_sample():
    jd = read_path(config.SAMPLE_DIR / "job_description.txt")
    resumes = []
    for p in sorted(config.SAMPLE_DIR.glob("resume_*")):
        if p.suffix.lower() in (".txt", ".pdf"):
            text = read_path(p)
            resumes.append((candidate_name(text, p.stem), text))
    return jd, resumes


# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Panel settings")
    st.markdown(f'<span class="mode-badge">{html.escape(config.mode_label())}</span>',
                unsafe_allow_html=True)
    if config.DEMO_MODE:
        st.caption("Add GROQ_API_KEY to the .env file to use the live Llama model.")
    use_sample = st.toggle("Use built-in sample data", value=False,
                           help="1 job description + 6 fictional resumes with bias traps")
    st.divider()
    st.subheader("The agents")
    for i, name in enumerate(PIPELINE, start=1):
        icon, role = AGENT_INFO[name]
        st.markdown(f"**{i}. {icon} {name}**  \n<small>{role}</small>", unsafe_allow_html=True)
    st.divider()
    st.caption("Built with CrewAI · Streamlit · Groq")

# ------------------------------------------------------------------ header
st.title("🧑‍💼 Resume Screening Panel")
st.markdown("A **multi-agent HR system**: four AI agents analyse the job description, "
            "screen resumes, audit the decisions for bias and produce a fair, ranked shortlist.")

col_jd, col_cv = st.columns(2)
with col_jd:
    jd_file = st.file_uploader("1️⃣ Job description (PDF or TXT)", type=["pdf", "txt"], key="jd")
with col_cv:
    cv_files = st.file_uploader("2️⃣ Resumes (PDF or TXT, several allowed)", type=["pdf", "txt"],
                                accept_multiple_files=True, key="cvs")

if use_sample:
    st.info("Using built-in sample data: Junior Python Developer JD + 6 fictional resumes.")

run = st.button("▶️ Run Panel", type="primary", use_container_width=True)

st.subheader("Agent pipeline")
card_cols = st.columns(4)
cards = {name: col.empty() for name, col in zip(PIPELINE, card_cols)}
prev = st.session_state.get("result")
for name in PIPELINE:
    cards[name].markdown(agent_card(name, "done" if prev else "waiting",
                                    "Completed" if prev else ""), unsafe_allow_html=True)
log_box = st.empty()

# --------------------------------------------------------------------- run
if run:
    if use_sample:
        jd_text, resumes = load_sample()
    else:
        if not jd_file or not cv_files:
            st.error("Upload a job description and at least one resume, or switch on sample data.")
            st.stop()
        jd_text = read_document(jd_file.name, jd_file.getvalue())
        resumes = []
        for f in cv_files:
            text = read_document(f.name, f.getvalue())
            resumes.append((candidate_name(text, f.name), text))

    for name in PIPELINE:
        cards[name].markdown(agent_card(name, "waiting"), unsafe_allow_html=True)

    logger = PanelLogger(config.LOG_FILE)

    def on_status(agent: str, state: str, detail: str) -> None:
        if agent in cards:
            cards[agent].markdown(agent_card(agent, state, detail), unsafe_allow_html=True)
        log_box.code("\n".join(logger.lines[-8:]) or "Starting…", language="text", wrap_lines=True)

    try:
        with st.spinner("Agents are working…"):
            result = ResumePanel(on_status=on_status, logger=logger).run(jd_text, resumes)
        st.session_state["result"] = result
    except Exception as err:  # show a friendly error instead of a stack trace
        st.error(f"The panel could not finish: {err}")
        st.stop()
    log_box.empty()

# ----------------------------------------------------------------- results
result = st.session_state.get("result")
if result:
    st.success(result["summary"]["summary"])

    st.subheader("Agent outputs")
    crit = result["criteria"]
    with st.expander("🧠 Agent 1 — JD Analyst Agent · structured hiring criteria", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.markdown("**Must-have skills**\n" + "\n".join(f"- {s}" for s in crit["must_have_skills"]))
        c2.markdown("**Nice-to-have skills**\n" + "\n".join(f"- {s}" for s in crit["nice_to_have_skills"]))
        exp = crit.get("experience", {})
        c3.markdown(f"**Experience:** {exp.get('min_years')}–{exp.get('max_years')} years "
                    f"({exp.get('level')})\n\n**Qualifications**\n"
                    + "\n".join(f"- {q}" for q in crit.get("qualifications", [])))
        st.json(crit, expanded=False)

    with st.expander("📊 Agent 2 — Screener Agent · scores and skill breakdown", expanded=False):
        for s in result["screenings"]:
            st.markdown(f"**{s['candidate']}** — score **{s['score']}/100** "
                        f"(skill score {s.get('skill_score')})")
            st.caption(s.get("justification", ""))
            df = pd.DataFrame(s.get("skill_breakdown", []))
            if not df.empty:
                df["matched"] = df["matched"].map({True: "✅", False: "❌"})
                st.dataframe(df, hide_index=True, use_container_width=True)

    with st.expander("⚖️ Agent 3 — Bias Checker Agent · fairness audit", expanded=False):
        for r in result["bias_reviews"]:
            if r.get("bias_found"):
                st.warning(f"**{r['candidate']}**: {r['verdict']}")
                for f in r.get("bias_flags", []):
                    st.markdown(f"- **{f['category']}** — {f['explanation']}")
            else:
                st.success(f"**{r['candidate']}**: {r['verdict']}")

    with st.expander("📝 Agent 4 — HR Summary Agent · shortlist and interview questions", expanded=False):
        for r in result["summary"]["ranking"]:
            st.markdown(f"**#{r['rank']} {r['candidate']}** — {r['recommendation']} "
                        f"({r['final_score']}/100)")
            if r["interview_questions"]:
                st.markdown("\n".join(f"{i}. {q}" for i, q in enumerate(r["interview_questions"], 1)))
            else:
                st.caption("Not shortlisted — no interview questions.")

    st.subheader("🏆 Final ranked shortlist")
    table = results_table(result)

    def colour(v):
        return {"Hire": "background-color:#dcfce7", "Maybe": "background-color:#fef3c7",
                "Reject": "background-color:#fee2e2"}.get(v, "")
    st.dataframe(table.style.map(colour, subset=["Recommendation"]),
                 hide_index=True, use_container_width=True)

    d1, d2, d3 = st.columns(3)
    d1.download_button("⬇️ Download CSV", to_csv(result), "results.csv", "text/csv",
                       use_container_width=True)
    d2.download_button("⬇️ Download PDF report", to_pdf(result), "results.pdf", "application/pdf",
                       use_container_width=True)
    d3.download_button("⬇️ Download full JSON", json.dumps(result, indent=2), "results.json",
                       "application/json", use_container_width=True)

    with st.expander("🔎 Agent hand-off log (proof of multiple agents)"):
        st.code("\n".join(result["log"]), language="text", wrap_lines=True)
