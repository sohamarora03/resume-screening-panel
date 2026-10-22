"""
Agent 3 - Bias Checker Agent
Audits the Screener Agent's reasoning. Any score change based on a
protected or job-irrelevant attribute is flagged, reversed and explained.
"""
import re

from crewai import Agent

NAME = "Bias Checker Agent"
ROLE = "Bias Checker Agent"
GOAL = (
    "Audit every screening decision for bias based on name, gender, age, "
    "religion, college prestige, location / national origin, marital status "
    "or employment gaps, and correct the score so it reflects job fit only."
)
BACKSTORY = (
    "You are a fair-hiring and diversity compliance officer. You know that "
    "career breaks (e.g. maternity), age, marital status, origin and college "
    "brand do not predict job performance. You leave legitimate skill-based "
    "reasoning untouched and only reverse unfair adjustments."
)

# Protected / job-irrelevant categories and the words that reveal them
PROTECTED = {
    "Employment gap": r"career break|employment gap|gap\b|maternity|sabbatical|skill decay",
    "Age": r"\bage\b|years old|\bis \d{2}\b|junior team|too old|young",
    "College prestige": r"college|institute|tier|university brand",
    "Marital status": r"married|marital|spouse|family commitments",
    "Location / national origin": r"overseas|abroad|foreign|nationality|relocation|origin",
    "Gender": r"\bgender\b|\bfemale\b|\bmale\b|\bwoman\b|pregnan",
    "Religion": r"religion|religious|caste",
    "Name": r"\bname\b|sounding",
}


def build_agent(llm, verbose: bool = False) -> Agent:
    return Agent(role=ROLE, goal=GOAL, backstory=BACKSTORY, llm=llm,
                 verbose=verbose, allow_delegation=False)


def classify(reason: str) -> str | None:
    for category, pattern in PROTECTED.items():
        if re.search(pattern, reason, re.I):
            return category
    return None


# ---------------------------------------------------------------------------
# Offline engine (demo mode)
# ---------------------------------------------------------------------------
def demo_respond(payload: dict) -> dict:
    screening, resume = payload["screening"], payload["resume"]
    flags, kept = [], []
    for adj in screening.get("adjustments", []):
        category = classify(adj["reason"])
        if category:
            note = ""
            if category == "Employment gap" and re.search(r"maternity", resume, re.I):
                note = " The break was for maternity leave, which is legally protected."
            flags.append({
                "category": category,
                "evidence": adj["reason"],
                "points_reversed": -adj["points"],
                "explanation": f"'{adj['reason']}' is not related to the job requirements, "
                               f"so its {adj['points']:+d} point effect is removed.{note}",
            })
        else:
            kept.append(adj)

    original = screening["score"]
    adjusted = max(0, min(100, screening["skill_score"] + sum(a["points"] for a in kept)))
    return {
        "candidate": screening["candidate"],
        "original_score": original,
        "adjusted_score": adjusted,
        "bias_found": bool(flags),
        "bias_flags": flags,
        "verdict": (f"Bias detected in {len(flags)} factor(s); score corrected "
                    f"{original} -> {adjusted}." if flags
                    else "No bias detected; screening reasoning is skill-based."),
    }
