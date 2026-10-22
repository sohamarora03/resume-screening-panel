"""End-to-end: all four agents run through CrewAI on the sample data."""
import pytest

from main import load_inputs
from orchestrator import PIPELINE, ResumePanel
from utils.logger import PanelLogger

EXPECTED_FLAGS = {
    "Priya Raghavan": "Employment gap",
    "Oluwaseun Adeyemi": "Location / national origin",
    "Rakesh Kumar Verma": "Age",
    "Sneha Patil": "College prestige",
    "Arjun Mehta": "College prestige",
}


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    log_file = tmp_path_factory.mktemp("logs") / "run_log.txt"
    jd, resumes = load_inputs(None, None)
    statuses = []
    panel = ResumePanel(on_status=lambda a, s, d: statuses.append((a, s)),
                        logger=PanelLogger(log_file, echo=False))
    return panel.run(jd, resumes), statuses, log_file.read_text()


def test_all_candidates_ranked(run):
    result, _, _ = run
    ranking = result["summary"]["ranking"]
    assert len(ranking) == 6
    scores = [r["final_score"] for r in ranking]
    assert scores == sorted(scores, reverse=True)


def test_bias_traps_are_caught(run):
    result, _, _ = run
    reviews = {r["candidate"]: r for r in result["bias_reviews"]}
    for name, category in EXPECTED_FLAGS.items():
        cats = [f["category"] for f in reviews[name]["bias_flags"]]
        assert category in cats, f"{name}: expected {category}, got {cats}"
    assert reviews["Kevin D'Souza"]["bias_found"] is False


def test_every_agent_ran_in_order(run):
    _, statuses, log = run
    done = [a for a, s in statuses if s == "done"]
    assert done == PIPELINE
    for a, b in zip(PIPELINE, PIPELINE[1:]):
        assert f"[{a}] handed off to [{b}]" in log
