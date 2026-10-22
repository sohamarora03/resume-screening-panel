"""
Agent 1 - JD Analyst Agent
Reads the job description and turns it into structured hiring criteria
(JSON) that every later agent works from.
"""
import re

from crewai import Agent

NAME = "JD Analyst Agent"
ROLE = "JD Analyst Agent"
GOAL = (
    "Convert a free-text job description into precise, structured hiring "
    "criteria: must-have skills, nice-to-have skills, experience level and "
    "qualifications."
)
BACKSTORY = (
    "You are a senior technical recruiter who has written hundreds of job "
    "descriptions. You separate genuine requirements from wish-list items and "
    "never invent requirements that are not in the text."
)


def build_agent(llm, verbose: bool = False) -> Agent:
    """Create the CrewAI agent object."""
    return Agent(role=ROLE, goal=GOAL, backstory=BACKSTORY, llm=llm,
                 verbose=verbose, allow_delegation=False)


# ---------------------------------------------------------------------------
# Offline engine (demo mode): rule-based extraction with the same JSON schema
# ---------------------------------------------------------------------------
_MUST = re.compile(r"(must|required|requirement|mandatory|essential)", re.I)
_NICE = re.compile(r"(nice|preferred|bonus|plus|good to have|desirable)", re.I)
_QUAL = re.compile(r"(qualification|education|eligibility)", re.I)
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.*)")


def demo_respond(payload: dict) -> dict:
    jd = payload["job_description"]
    lines = jd.splitlines()
    title = next((l.split(":", 1)[1].strip() for l in lines
                  if l.lower().startswith(("job title", "position", "role:"))),
                 lines[0].strip() if lines else "Unknown role")

    must, nice, quals, section = [], [], [], None
    for line in lines:
        bullet = _BULLET.match(line)
        if not bullet:
            if _MUST.search(line):
                section = "must"
            elif _NICE.search(line):
                section = "nice"
            elif _QUAL.search(line):
                section = "qual"
            elif line.strip().endswith(":"):
                section = None
            continue
        item = bullet.group(1).strip()
        {"must": must, "nice": nice, "qual": quals}.get(section, []).append(item)

    years = re.search(r"(\d+)\s*(?:-|–|to)\s*(\d+)\s*years", jd, re.I)
    if years:
        lo, hi = int(years.group(1)), int(years.group(2))
    else:
        lo, hi = 0, 2
    level = "Entry / Junior" if hi <= 2 else ("Mid" if hi <= 5 else "Senior")

    return {
        "job_title": title,
        "must_have_skills": must,
        "nice_to_have_skills": nice,
        "experience": {"min_years": lo, "max_years": hi, "level": level},
        "qualifications": quals,
        "summary": f"{title}: {len(must)} must-have and {len(nice)} nice-to-have "
                   f"skills, {lo}-{hi} years experience ({level}).",
    }
