"""
Command-line runner.

    python main.py                       # runs on sample_data/
    python main.py --jd my_jd.txt --resumes cv1.pdf cv2.txt

Prints the agent hand-off log and the final ranking, and saves
outputs/results.json, outputs/results.csv and outputs/results.pdf.
"""
import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

import config
from orchestrator import ResumePanel
from utils.exporter import to_csv, to_pdf
from utils.logger import PanelLogger
from utils.parser import candidate_name, read_path


def load_inputs(jd_path: Path | None, resume_paths: list[Path] | None):
    jd_path = jd_path or config.SAMPLE_DIR / "job_description.txt"
    resume_paths = resume_paths or sorted(p for p in config.SAMPLE_DIR.glob("resume_*")
                                          if p.suffix.lower() in (".txt", ".pdf"))
    resumes = []
    for p in resume_paths:
        text = read_path(p)
        resumes.append((candidate_name(text, p.stem), text))
    return read_path(jd_path), resumes


def print_results(console: Console, result: dict) -> None:
    reviews = {r["candidate"]: r for r in result["bias_reviews"]}
    table = Table(title="Final Ranking (HR Summary Agent)", header_style="bold")
    for col in ("Rank", "Candidate", "Screener", "Final", "Decision", "Bias flags"):
        table.add_column(col)
    colours = {"Hire": "green", "Maybe": "yellow", "Reject": "red"}
    for r in result["summary"]["ranking"]:
        rev = reviews[r["candidate"]]
        flags = ", ".join(f["category"] for f in rev.get("bias_flags", [])) or "-"
        c = colours[r["recommendation"]]
        table.add_row(str(r["rank"]), r["candidate"], str(rev["original_score"]),
                      str(r["final_score"]), f"[{c}]{r['recommendation']}[/{c}]", flags)
    console.print(table)
    console.print(f"[bold]Summary:[/bold] {result['summary']['summary']}")


def main(argv=None, console: Console | None = None) -> dict:
    parser = argparse.ArgumentParser(description="Resume Screening Panel (multi-agent)")
    parser.add_argument("--jd", type=Path, help="job description (.txt or .pdf)")
    parser.add_argument("--resumes", type=Path, nargs="*", help="resume files (.txt or .pdf)")
    args = parser.parse_args(argv)

    console = console or Console()
    jd_text, resumes = load_inputs(args.jd, args.resumes)
    panel = ResumePanel(logger=PanelLogger(config.LOG_FILE, console=console))
    result = panel.run(jd_text, resumes)
    print_results(console, result)

    config.OUTPUT_DIR.mkdir(exist_ok=True)
    (config.OUTPUT_DIR / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (config.OUTPUT_DIR / "results.csv").write_bytes(to_csv(result))
    (config.OUTPUT_DIR / "results.pdf").write_bytes(to_pdf(result))
    console.print("[dim]Saved results to outputs/ (json, csv, pdf) and log to logs/run_log.txt[/dim]")
    return result


if __name__ == "__main__":
    main()
