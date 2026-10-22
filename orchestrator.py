"""
Orchestrator - coordinates the four agents of the Resume Screening Panel.

Pipeline (sequential hand-offs):

  JD Analyst Agent --criteria--> Screener Agent --scores--> Bias Checker Agent
        --corrected scores--> HR Summary Agent --> ranked shortlist

Each stage runs as its own CrewAI Crew (one agent + one task), which lets
the orchestrator log every hand-off and report live status to the UI.
"""
import time
from typing import Callable

from crewai import Crew, Process

import config
from agents import bias_checker, hr_summary, jd_analyst, screener
from tasks import prompts
from utils.llm import get_llm
from utils.logger import PanelLogger
from utils.parser import extract_json

StatusFn = Callable[[str, str, str], None]  # (agent, state, detail)

PIPELINE = [jd_analyst.NAME, screener.NAME, bias_checker.NAME, hr_summary.NAME]


class ResumePanel:
    def __init__(self, on_status: StatusFn | None = None, logger: PanelLogger | None = None):
        self.llm = get_llm()
        self.logger = logger or PanelLogger(config.LOG_FILE)
        self.on_status = on_status or (lambda *a: None)
        v = config.CREW_VERBOSE
        self.agents = {
            jd_analyst.NAME: jd_analyst.build_agent(self.llm, v),
            screener.NAME: screener.build_agent(self.llm, v),
            bias_checker.NAME: bias_checker.build_agent(self.llm, v),
            hr_summary.NAME: hr_summary.build_agent(self.llm, v),
        }

    # ------------------------------------------------------------------ helpers
    def _kickoff(self, agent_name: str, task) -> dict | list:
        """Run one agent on one task and return its parsed JSON answer."""
        crew = Crew(agents=[self.agents[agent_name]], tasks=[task],
                    process=Process.sequential, verbose=config.CREW_VERBOSE)
        last_error = None
        for attempt in range(2):                     # one retry if JSON is malformed
            try:
                return extract_json(crew.kickoff().raw)
            except ValueError as err:
                last_error = err
                self.logger.warn(agent_name, f"invalid JSON (attempt {attempt + 1}), retrying")
        raise RuntimeError(f"{agent_name} did not return valid JSON: {last_error}")

    def _stage(self, name: str, detail: str = ""):
        self.on_status(name, "running", detail)
        self.logger.started(name, detail)
        return time.perf_counter()

    def _finish(self, name: str, t0: float, detail: str, next_agent: str | None):
        secs = time.perf_counter() - t0
        self.logger.completed(name, secs, detail)
        self.on_status(name, "done", detail)
        if next_agent:
            self.logger.handoff(name, next_agent)
        return secs

    # --------------------------------------------------------------------- run
    def run(self, job_description: str, resumes: list[tuple[str, str]]) -> dict:
        """resumes = list of (candidate_name, resume_text)."""
        if not job_description.strip():
            raise ValueError("Job description is empty")
        if not resumes:
            raise ValueError("Upload at least one resume")

        log = self.logger
        log.banner(f"Resume Screening Panel run - {config.mode_label()}")
        log.info("Orchestrator", f"received 1 job description and {len(resumes)} resume(s)")
        log.info("Orchestrator", f"pipeline: {' -> '.join(PIPELINE)}")
        timings = {}

        # 1. JD Analyst Agent --------------------------------------------------
        t0 = self._stage(jd_analyst.NAME, "extracting hiring criteria")
        criteria = self._kickoff(jd_analyst.NAME,
                                 prompts.jd_task(self.agents[jd_analyst.NAME], job_description))
        timings[jd_analyst.NAME] = self._finish(
            jd_analyst.NAME, t0,
            f"{len(criteria.get('must_have_skills', []))} must-have, "
            f"{len(criteria.get('nice_to_have_skills', []))} nice-to-have skills",
            screener.NAME)

        # 2. Screener Agent ----------------------------------------------------
        t0 = self._stage(screener.NAME, f"scoring {len(resumes)} resumes")
        screenings = []
        for i, (name, text) in enumerate(resumes, start=1):
            self.on_status(screener.NAME, "running", f"scoring {name} ({i}/{len(resumes)})")
            result = self._kickoff(screener.NAME, prompts.screen_task(
                self.agents[screener.NAME], criteria, name, text))
            result["candidate"] = name
            screenings.append(result)
            log.info(screener.NAME, f"scored {name}: {result.get('score')}/100")
        timings[screener.NAME] = self._finish(
            screener.NAME, t0, f"{len(screenings)} resumes scored", bias_checker.NAME)

        # 3. Bias Checker Agent ------------------------------------------------
        t0 = self._stage(bias_checker.NAME, "auditing screening decisions")
        reviews = []
        for (name, text), screening in zip(resumes, screenings):
            self.on_status(bias_checker.NAME, "running", f"auditing {name}")
            review = self._kickoff(bias_checker.NAME, prompts.bias_task(
                self.agents[bias_checker.NAME], name, text, screening))
            review["candidate"] = name
            reviews.append(review)
            if review.get("bias_found"):
                cats = ", ".join(f["category"] for f in review.get("bias_flags", []))
                log.info(bias_checker.NAME, f"FLAGGED {name}: {cats} -> score "
                         f"{review.get('original_score')} -> {review.get('adjusted_score')}")
            else:
                log.info(bias_checker.NAME, f"{name}: no bias found")
        flagged = sum(1 for r in reviews if r.get("bias_found"))
        timings[bias_checker.NAME] = self._finish(
            bias_checker.NAME, t0, f"{flagged} candidate(s) corrected for bias", hr_summary.NAME)

        # 4. HR Summary Agent --------------------------------------------------
        t0 = self._stage(hr_summary.NAME, "ranking and writing interview questions")
        merged = [{
            "candidate": s["candidate"],
            "original_score": r.get("original_score", s.get("score")),
            "adjusted_score": r.get("adjusted_score", s.get("score")),
            "bias_found": r.get("bias_found", False),
            "bias_flags": r.get("bias_flags", []),
            "experience_years": s.get("experience_years"),
            "skill_breakdown": s.get("skill_breakdown", []),
        } for s, r in zip(screenings, reviews)]
        summary = self._kickoff(hr_summary.NAME, prompts.summary_task(
            self.agents[hr_summary.NAME], criteria, merged))
        summary = self._normalise_summary(summary)
        timings[hr_summary.NAME] = self._finish(
            hr_summary.NAME, t0, f"{len(summary['shortlist'])} candidate(s) shortlisted", None)

        log.info("Orchestrator", f"pipeline finished in {sum(timings.values()):.1f}s - "
                                 f"4 agents, {2 + 2 * len(resumes)} agent tasks executed")
        return {
            "mode": config.mode_label(),
            "criteria": criteria,
            "screenings": screenings,
            "bias_reviews": reviews,
            "summary": summary,
            "timings": timings,
            "log": list(log.lines),
        }

    @staticmethod
    def _normalise_summary(summary: dict) -> dict:
        """Keep ranks and recommendations consistent even if an LLM slips."""
        ranking = sorted(summary.get("ranking", []),
                         key=lambda r: r.get("final_score", 0), reverse=True)
        for i, row in enumerate(ranking, start=1):
            row["rank"] = i
            row["recommendation"] = hr_summary.recommendation(int(row.get("final_score", 0)))
            row.setdefault("interview_questions", [])
            row.setdefault("strengths", [])
            row.setdefault("gaps", [])
        summary["ranking"] = ranking
        summary["shortlist"] = [r["candidate"] for r in ranking if r["recommendation"] != "Reject"]
        summary.setdefault("summary", "")
        return summary
