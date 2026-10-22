"""
Task definitions for the four agents.

Each task embeds its input data between <<<INPUT_JSON and INPUT_JSON>>>
markers and asks the agent to answer with JSON only. The markers make the
input easy for both the LLM and the offline demo engine to locate.
"""
import json

from crewai import Task

START, END = "<<<INPUT_JSON", "INPUT_JSON>>>"


def _wrap(payload: dict) -> str:
    return f"{START}\n{json.dumps(payload, indent=2)}\n{END}"


def jd_task(agent, job_description: str) -> Task:
    return Task(
        agent=agent,
        description=(
            "Analyse the job description below and extract the hiring criteria.\n"
            "Only use requirements that are actually written in the text.\n\n"
            + _wrap({"job_description": job_description})
        ),
        expected_output=(
            "ONLY a JSON object with keys: job_title (string), must_have_skills (list of "
            "strings), nice_to_have_skills (list of strings), experience ({min_years, "
            "max_years, level}), qualifications (list of strings), summary (string)."
        ),
    )


def screen_task(agent, criteria: dict, candidate: str, resume: str) -> Task:
    return Task(
        agent=agent,
        description=(
            "Screen this candidate against the hiring criteria.\n"
            "1. For every must-have and nice-to-have skill, say whether the resume shows it "
            "and quote the evidence line.\n"
            "2. skill_score = 70 x (must-have matched / total) + 20 x (nice-to-have matched / "
            "total) + 10 for relevant experience (6 if none).\n"
            "3. List any OTHER factors that changed your overall impression as "
            "'adjustments' with a points value (+ or -). Use an empty list if none.\n"
            "4. score = skill_score + sum of adjustment points, kept between 0 and 100.\n\n"
            + _wrap({"criteria": criteria, "candidate": candidate, "resume": resume})
        ),
        expected_output=(
            "ONLY a JSON object with keys: candidate, skill_score (int), adjustments (list of "
            "{reason, points}), score (int 0-100), experience_years (number), skill_breakdown "
            "(list of {skill, type: 'must-have'|'nice-to-have', matched: bool, evidence}), "
            "justification (string, max 3 sentences)."
        ),
    )


def bias_task(agent, candidate: str, resume: str, screening: dict) -> Task:
    return Task(
        agent=agent,
        description=(
            "Audit the Screener Agent's decision below for bias.\n"
            "Flag any adjustment or reasoning based on: name, gender, age, religion, college "
            "prestige (positive OR negative), location / national origin, marital status, or "
            "employment gaps (including maternity/parental leave).\n"
            "For each flag, reverse its points. adjusted_score = skill_score + the points of the "
            "adjustments that are NOT biased (0-100). Skill-based reasoning must stay unchanged.\n\n"
            + _wrap({"candidate": candidate, "resume": resume, "screening": screening})
        ),
        expected_output=(
            "ONLY a JSON object with keys: candidate, original_score (int), adjusted_score (int), "
            "bias_found (bool), bias_flags (list of {category, evidence, points_reversed, "
            "explanation}), verdict (string)."
        ),
    )


def summary_task(agent, criteria: dict, candidates: list[dict]) -> Task:
    return Task(
        agent=agent,
        description=(
            "Create the final hiring summary from the bias-corrected results below.\n"
            "Rank candidates by adjusted_score (highest first). Recommendation: Hire if >= 75, "
            "Maybe if 55-74, Reject if < 55. For every Hire or Maybe candidate write 3-5 "
            "interview questions that probe their specific strengths and missing skills. "
            "Never ask about age, family, gaps, origin or other personal matters.\n\n"
            + _wrap({"criteria": criteria, "candidates": candidates})
        ),
        expected_output=(
            "ONLY a JSON object with keys: ranking (list of {rank, candidate, final_score, "
            "recommendation, strengths (list), gaps (list), bias_corrected (bool), "
            "interview_questions (list)}), shortlist (list of names), summary (string)."
        ),
    )
