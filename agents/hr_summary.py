"""
Agent 4 - HR Summary Agent
Combines all earlier outputs into the final ranked shortlist, a
Hire / Maybe / Reject recommendation and tailored interview questions.
"""
from crewai import Agent

from config import HIRE_THRESHOLD, MAYBE_THRESHOLD

NAME = "HR Summary Agent"
ROLE = "HR Summary Agent"
GOAL = (
    "Produce a clear, ranked shortlist using the bias-corrected scores, give "
    "each candidate a Hire / Maybe / Reject recommendation, and write 3-5 "
    "tailored interview questions for every shortlisted candidate."
)
BACKSTORY = (
    "You are an HR business partner who prepares hiring managers for "
    "interviews. Your summaries are short, evidence-based and fair, and your "
    "interview questions probe the specific strengths and gaps of each person."
)


def build_agent(llm, verbose: bool = False) -> Agent:
    return Agent(role=ROLE, goal=GOAL, backstory=BACKSTORY, llm=llm,
                 verbose=verbose, allow_delegation=False)


ACTION_VERBS = {"built", "wrote", "developed", "designed", "created", "added", "automated",
                "packaged", "containerised", "containerized", "cleaned", "used", "led",
                "implemented", "deployed", "optimised", "optimized", "managed", "integrated"}


def recommendation(score: int) -> str:
    if score >= HIRE_THRESHOLD:
        return "Hire"
    if score >= MAYBE_THRESHOLD:
        return "Maybe"
    return "Reject"


def _questions(breakdown: list[dict]) -> list[str]:
    """3-5 questions built from this candidate's own resume evidence and gaps."""
    qs, used = [], set()
    matched = [b for b in breakdown if b["matched"]]
    # Prefer concrete achievements ("Built ...", "Wrote ...") over skill lists or titles
    def concrete(b):
        first = b["evidence"].split()[0].lower() if b["evidence"].split() else ""
        return first in ACTION_VERBS
    matched.sort(key=lambda b: (not concrete(b), b["type"] != "must-have"))
    for b in matched:
        evidence = b["evidence"].rstrip(".")
        if evidence in used or len(qs) == 2:
            continue
        used.add(evidence)
        qs.append(f'Your resume says "{evidence}". Walk us through it: what was the '
                  f'problem, how did you use {b["skill"]}, and what was your own part?')
    for b in [b for b in breakdown if b["type"] == "must-have" and not b["matched"]][:2]:
        qs.append(f"This role needs {b['skill']}. Have you used anything similar, and how "
                  f"would you get productive with it in your first month?")
    if len(qs) < 4:
        qs.append("Describe a bug that was hard to track down. How did you find and fix it?")
    if len(qs) < 5:
        qs.append("How do you make sure the code you write is tested and easy for others to maintain?")
    return qs[:5]


# ---------------------------------------------------------------------------
# Offline engine (demo mode)
# ---------------------------------------------------------------------------
def demo_respond(payload: dict) -> dict:
    rows = sorted(payload["candidates"], key=lambda c: c["adjusted_score"], reverse=True)
    ranking = []
    for rank, cand in enumerate(rows, start=1):
        breakdown = cand["skill_breakdown"]
        matched_must = [b["skill"] for b in breakdown if b["type"] == "must-have" and b["matched"]]
        missing_must = [b["skill"] for b in breakdown if b["type"] == "must-have" and not b["matched"]]
        matched_nice = [b["skill"] for b in breakdown if b["type"] == "nice-to-have" and b["matched"]]
        rec = recommendation(cand["adjusted_score"])
        ranking.append({
            "rank": rank,
            "candidate": cand["candidate"],
            "final_score": cand["adjusted_score"],
            "recommendation": rec,
            "strengths": matched_must + matched_nice,
            "gaps": missing_must,
            "bias_corrected": cand["bias_found"],
            "interview_questions": _questions(breakdown) if rec != "Reject" else [],
        })

    shortlist = [r["candidate"] for r in ranking if r["recommendation"] != "Reject"]
    hires = [r["candidate"] for r in ranking if r["recommendation"] == "Hire"]
    corrected = sum(1 for r in ranking if r["bias_corrected"])
    return {
        "ranking": ranking,
        "shortlist": shortlist,
        "summary": (f"{len(ranking)} candidates screened. {len(hires)} recommended to hire "
                    f"({', '.join(hires) or 'none'}), {len(shortlist) - len(hires)} maybe, "
                    f"{len(ranking) - len(shortlist)} rejected. Bias corrections were applied "
                    f"to {corrected} candidate(s) before ranking."),
    }
