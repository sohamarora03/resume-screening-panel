"""
Generate the report diagrams with Graphviz (`dot` must be installed).

    python scripts/make_diagrams.py

Outputs PNGs in docs/diagrams/:
  system_architecture.png, agent_workflow.png, deployment_architecture.png
"""
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "diagrams"

FONT = 'fontname="Helvetica"'
NODE = f'node [shape=box, style="rounded,filled", {FONT}, fontsize=12, penwidth=1.4, margin="0.18,0.10"];'
EDGE = f'edge [{FONT}, fontsize=10, color="#475569", penwidth=1.3];'

AGENT_COLOURS = {"jd": "#cffafe", "sc": "#fef3c7", "bc": "#fae8ff", "hr": "#dcfce7"}

SYSTEM = f"""
digraph G {{
  rankdir=LR; bgcolor=white; pad=0.3; nodesep=0.45; ranksep=0.6; {FONT};
  {NODE} {EDGE}
  label="System Architecture - Resume Screening Panel"; labelloc=t; fontsize=18;

  user [label="HR User", shape=oval, fillcolor="#e0e7ff"];
  subgraph cluster_ui {{ label="Presentation layer"; style="rounded,dashed"; color="#94a3b8";
    ui [label="Streamlit Web UI\\n(app.py)\\nupload · live status · results", fillcolor="#f1f5f9"];
    cli [label="CLI runner\\n(main.py)", fillcolor="#f1f5f9"];
  }}
  subgraph cluster_core {{ label="Orchestration layer (CrewAI)"; style="rounded,dashed"; color="#94a3b8";
    parser [label="Document parser\\n(PDF / TXT)", fillcolor="#f8fafc"];
    orch [label="Orchestrator\\n(orchestrator.py)", fillcolor="#e2e8f0", penwidth=2];
    jd [label="1. JD Analyst Agent", fillcolor="{AGENT_COLOURS['jd']}"];
    sc [label="2. Screener Agent", fillcolor="{AGENT_COLOURS['sc']}"];
    bc [label="3. Bias Checker Agent", fillcolor="{AGENT_COLOURS['bc']}"];
    hr [label="4. HR Summary Agent", fillcolor="{AGENT_COLOURS['hr']}"];
  }}
  subgraph cluster_ai {{ label="Model layer"; style="rounded,dashed"; color="#94a3b8";
    llm [label="LLM factory\\n(utils/llm.py)", fillcolor="#f8fafc"];
    groq [label="Groq API\\nLlama 3.3 70B\\n(live mode)", fillcolor="#fee2e2"];
    demo [label="Offline engine\\n(demo mode)", fillcolor="#f1f5f9"];
  }}
  subgraph cluster_out {{ label="Outputs"; style="rounded,dashed"; color="#94a3b8";
    logs [label="logs/run_log.txt\\n(hand-off log)", shape=note, fillcolor="#fffbeb"];
    res [label="Ranked shortlist\\nCSV · PDF · JSON", shape=note, fillcolor="#fffbeb"];
  }}

  user -> ui [label="JD + resumes"]; user -> cli;
  ui -> parser; cli -> parser; parser -> orch [label="text"];
  orch -> jd; orch -> sc; orch -> bc; orch -> hr;
  jd -> llm [style=dotted]; sc -> llm [style=dotted]; bc -> llm [style=dotted]; hr -> llm [style=dotted];
  llm -> groq; llm -> demo;
  orch -> logs; orch -> res; res -> ui [label="display / download", constraint=false];
}}
"""

WORKFLOW = f"""
digraph G {{
  rankdir=TB; bgcolor=white; pad=0.3; nodesep=0.5; ranksep=0.42; {FONT};
  {NODE} {EDGE}
  label="Agent Workflow and Hand-off Sequence"; labelloc=t; fontsize=18;

  start [label="Start: 1 JD + N resumes", shape=oval, fillcolor="#e0e7ff"];
  jd [label="JD Analyst Agent\\nextract must-have / nice-to-have skills,\\nexperience, qualifications", fillcolor="{AGENT_COLOURS['jd']}"];
  crit [label="criteria.json", shape=note, fillcolor="#fffbeb"];
  sc [label="Screener Agent  (x N resumes)\\nper-skill evidence, skill_score,\\nother adjustments, score 0-100", fillcolor="{AGENT_COLOURS['sc']}"];
  scores [label="screenings[ ]", shape=note, fillcolor="#fffbeb"];
  bc [label="Bias Checker Agent  (x N)\\naudit reasoning for protected factors", fillcolor="{AGENT_COLOURS['bc']}"];
  q [label="Biased factor?", shape=diamond, style=filled, fillcolor="#f1f5f9"];
  fix [label="Reverse points, flag category,\\nexplain correction", fillcolor="#fee2e2"];
  keep [label="Keep score", fillcolor="#f1f5f9"];
  adj [label="adjusted scores + bias flags", shape=note, fillcolor="#fffbeb"];
  hr [label="HR Summary Agent\\nrank · Hire / Maybe / Reject ·\\n3-5 interview questions each", fillcolor="{AGENT_COLOURS['hr']}"];
  end [label="Final shortlist (UI, CSV, PDF)", shape=oval, fillcolor="#dcfce7"];

  start -> jd; jd -> crit [label=" hand-off 1"]; crit -> sc;
  sc -> scores [label=" hand-off 2"]; scores -> bc; bc -> q;
  q -> fix [label="yes"]; q -> keep [label="no"];
  fix -> adj; keep -> adj; adj -> hr [label=" hand-off 3"]; hr -> end;
}}
"""

DEPLOY = f"""
digraph G {{
  rankdir=LR; bgcolor=white; pad=0.3; nodesep=0.35; ranksep=0.55; compound=true; {FONT};
  {NODE} {EDGE}
  label="Deployment Architecture"; labelloc=t; fontsize=18;

  user [label="User\\n(web browser)", shape=oval, fillcolor="#e0e7ff"];
  subgraph cluster_host {{ label="Streamlit Community Cloud / local machine (Python 3.10+)";
    style="rounded,filled"; fillcolor="#f8fafc"; color="#64748b";
    ui [label="Streamlit UI\\n:8501", fillcolor="#f1f5f9"];
    orch [label="Orchestrator\\n(CrewAI Crews)", fillcolor="#e2e8f0", penwidth=2];
    subgraph cluster_agents {{ label="4 independent agents"; style="rounded,dashed"; color="#94a3b8";
      jd [label="JD Analyst\\nAgent", fillcolor="{AGENT_COLOURS['jd']}"];
      sc [label="Screener\\nAgent", fillcolor="{AGENT_COLOURS['sc']}"];
      bc [label="Bias Checker\\nAgent", fillcolor="{AGENT_COLOURS['bc']}"];
      hr [label="HR Summary\\nAgent", fillcolor="{AGENT_COLOURS['hr']}"];
    }}
    secrets [label="Secrets\\n(.env / st.secrets)\\nGROQ_API_KEY", shape=cylinder, fillcolor="#fef9c3"];
    logs [label="logs/run_log.txt", shape=cylinder, fillcolor="#fffbeb"];
  }}
  groq [label="Groq Cloud\\nLLM API\\n(HTTPS)", shape=box3d, fillcolor="#fee2e2"];
  out [label="Output to user\\nranked shortlist\\nCSV / PDF download", shape=note, fillcolor="#dcfce7"];

  user -> ui [label="HTTPS"]; ui -> orch;
  orch -> jd -> sc -> bc -> hr [color="#1F3A5F", penwidth=2];
  hr -> groq [ltail=cluster_agents, style=dashed, dir=both, label="prompts / JSON answers"];
  secrets -> orch [style=dashed]; orch -> logs [style=dashed];
  hr -> out [label="results"];
}}
"""


def render(name: str, source: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dot_file = OUT / f"{name}.dot"
    dot_file.write_text(source, encoding="utf-8")
    subprocess.run(["dot", "-Tpng", "-Gdpi=180", str(dot_file), "-o", str(OUT / f"{name}.png")],
                   check=True)
    print("saved", name + ".png")


if __name__ == "__main__":
    render("system_architecture", SYSTEM)
    render("agent_workflow", WORKFLOW)
    render("deployment_architecture", DEPLOY)
