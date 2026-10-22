"""Check every agent returns JSON with the agreed schema (offline engine)."""
from agents import bias_checker, hr_summary, jd_analyst, screener
from utils.parser import read_path

JD = read_path("sample_data/job_description.txt")
PRIYA = read_path("sample_data/resume_01_priya_raghavan.txt")


def test_jd_analyst_schema():
    out = jd_analyst.demo_respond({"job_description": JD})
    assert set(out) >= {"job_title", "must_have_skills", "nice_to_have_skills",
                        "experience", "qualifications", "summary"}
    assert out["job_title"] == "Junior Python Developer"
    assert "Python" in out["must_have_skills"] and "Docker" in out["nice_to_have_skills"]
    assert out["experience"]["max_years"] == 2


def _screen(text, name="Priya Raghavan"):
    criteria = jd_analyst.demo_respond({"job_description": JD})
    return criteria, screener.demo_respond({"criteria": criteria, "candidate": name, "resume": text})


def test_screener_schema_and_range():
    _, out = _screen(PRIYA)
    assert set(out) >= {"candidate", "score", "skill_score", "adjustments",
                        "skill_breakdown", "justification"}
    assert 0 <= out["score"] <= 100
    assert all({"skill", "type", "matched", "evidence"} <= set(b) for b in out["skill_breakdown"])


def test_bias_checker_reverses_maternity_gap():
    _, screening = _screen(PRIYA)
    out = bias_checker.demo_respond({"candidate": "Priya Raghavan", "resume": PRIYA,
                                     "screening": screening})
    assert out["bias_found"] is True
    assert out["bias_flags"][0]["category"] == "Employment gap"
    assert out["adjusted_score"] > out["original_score"]


def test_bias_checker_leaves_clean_screening_alone():
    screening = {"candidate": "X", "score": 60, "skill_score": 60, "adjustments": []}
    out = bias_checker.demo_respond({"candidate": "X", "resume": "", "screening": screening})
    assert out["bias_found"] is False and out["adjusted_score"] == 60


def test_hr_summary_schema_and_thresholds():
    criteria, s = _screen(PRIYA)
    cand = {"candidate": "Priya", "adjusted_score": 90, "bias_found": True,
            "skill_breakdown": s["skill_breakdown"]}
    weak = {**cand, "candidate": "Weak", "adjusted_score": 30, "bias_found": False}
    out = hr_summary.demo_respond({"criteria": criteria, "candidates": [weak, cand]})
    assert [r["candidate"] for r in out["ranking"]] == ["Priya", "Weak"]
    assert out["ranking"][0]["recommendation"] == "Hire"
    assert 3 <= len(out["ranking"][0]["interview_questions"]) <= 5
    assert out["ranking"][1]["recommendation"] == "Reject"
    assert out["shortlist"] == ["Priya"]
