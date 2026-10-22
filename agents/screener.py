"""
Agent 2 - Screener Agent
Scores each resume 0-100 against the JD Analyst's criteria, with a
per-skill breakdown and a short justification.
"""
import re

from crewai import Agent

from utils.skills import aliases_for, find_evidence

NAME = "Screener Agent"
ROLE = "Screener Agent"
GOAL = (
    "Score each resume from 0 to 100 against the structured hiring criteria, "
    "showing exactly which skills were found, with evidence from the resume."
)
BACKSTORY = (
    "You are a fast, first-pass resume screener at a busy IT services firm. "
    "You work like a typical human screener: you read the whole resume, score "
    "the skill match, and also note anything else that influenced your "
    "overall impression of the candidate."
)

WEIGHT_MUST, WEIGHT_NICE, WEIGHT_EXP = 70, 20, 10


def build_agent(llm, verbose: bool = False) -> Agent:
    return Agent(role=ROLE, goal=GOAL, backstory=BACKSTORY, llm=llm,
                 verbose=verbose, allow_delegation=False)


# ---------------------------------------------------------------------------
# Offline engine (demo mode)
# ---------------------------------------------------------------------------
# A real first-pass screen often applies "gut feel" shortcuts. Demo mode
# reproduces the common ones on purpose so the Bias Checker Agent has
# realistic reasoning to audit. They are clearly labelled as adjustments.
FIRST_PASS_HEURISTICS = [
    (re.compile(r"career break|employment gap|maternity|sabbatical", re.I), -12,
     "Career break on resume - possible skill decay"),
    (re.compile(r"tier[- ]?3|small private college|lesser[- ]known", re.I), -6,
     "Degree from a lower-tier college"),
    (re.compile(r"tier[- ]?1|premier institute|institute of national importance", re.I), +10,
     "Graduate of a top-tier institute"),
    (re.compile(r"marital status\s*:\s*married", re.I), -4,
     "Married - may have relocation or commitment constraints"),
    (re.compile(r"lagos|nigeria|overseas|abroad", re.I), -5,
     "Overseas background - relocation and fit uncertain"),
]
_AGE = re.compile(r"\bage\s*[:\-]\s*(\d{2})\b|\b(\d{2})\s*years old\b", re.I)
_EXP = re.compile(r"total experience\s*[:\-]\s*([\d.]+)\s*(years?|months?)", re.I)


def experience_years(text: str) -> float:
    m = _EXP.search(text)
    if not m:
        return 0.0
    value = float(m.group(1))
    return round(value / 12, 1) if m.group(2).lower().startswith("month") else value


def demo_respond(payload: dict) -> dict:
    criteria, resume, name = payload["criteria"], payload["resume"], payload["candidate"]
    must = criteria.get("must_have_skills", [])
    nice = criteria.get("nice_to_have_skills", [])

    breakdown, must_hits, nice_hits = [], 0, 0
    for kind, skills in (("must-have", must), ("nice-to-have", nice)):
        for skill in skills:
            evidence = find_evidence(resume, aliases_for(skill))
            breakdown.append({"skill": skill, "type": kind,
                              "matched": bool(evidence), "evidence": evidence or "Not found"})
            if evidence:
                if kind == "must-have":
                    must_hits += 1
                else:
                    nice_hits += 1

    years = experience_years(resume)
    exp_points = 10 if years >= 0.5 else 6
    skill_score = (WEIGHT_MUST * must_hits / max(len(must), 1)
                   + WEIGHT_NICE * nice_hits / max(len(nice), 1))
    base = round(skill_score + exp_points)

    adjustments = []
    for pattern, points, reason in FIRST_PASS_HEURISTICS:
        if pattern.search(resume):
            adjustments.append({"reason": reason, "points": points})
    age = _AGE.search(resume)
    if age:
        value = int(age.group(1) or age.group(2))
        if value >= 35:
            adjustments.append({"reason": f"Candidate is {value} - may not suit a junior team",
                                "points": -8})

    final = max(0, min(100, base + sum(a["points"] for a in adjustments)))
    missing = [b["skill"] for b in breakdown if b["type"] == "must-have" and not b["matched"]]
    justification = (f"Matched {must_hits}/{len(must)} must-have and {nice_hits}/{len(nice)} "
                     f"nice-to-have skills; {years} years experience.")
    if missing:
        justification += " Missing: " + ", ".join(missing) + "."
    if adjustments:
        justification += " Other factors: " + "; ".join(
            f"{a['reason']} ({a['points']:+d})" for a in adjustments) + "."

    return {
        "candidate": name,
        "skill_score": base,
        "adjustments": adjustments,
        "score": final,
        "experience_years": years,
        "skill_breakdown": breakdown,
        "justification": justification,
    }
