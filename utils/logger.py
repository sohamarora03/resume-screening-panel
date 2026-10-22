"""
Run logger - the project's "proof of multiple agents".

Every agent start, finish and hand-off is written with a timestamp to
  1. the terminal (coloured, via the `rich` library), and
  2. logs/run_log.txt (plain text, appended per run).

Example lines:
  2026-10-22 22:15:01 | [JD Analyst Agent] started
  2026-10-22 22:15:02 | [JD Analyst Agent] handed off to [Screener Agent]
"""
from datetime import datetime
from pathlib import Path

from rich.console import Console

AGENT_COLOURS = {
    "Orchestrator": "bold white",
    "JD Analyst Agent": "bold cyan",
    "Screener Agent": "bold yellow",
    "Bias Checker Agent": "bold magenta",
    "HR Summary Agent": "bold green",
}


class PanelLogger:
    def __init__(self, log_file: Path, console: Console | None = None, echo: bool = True):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.console = console or Console()
        self.echo = echo
        self.lines: list[str] = []          # kept in memory for the UI

    def _write(self, agent: str, message: str, style_msg: str = "") -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        plain = f"{stamp} | [{agent}] {message}"
        self.lines.append(plain)
        with self.log_file.open("a", encoding="utf-8") as fh:
            fh.write(plain + "\n")
        if self.echo:
            colour = AGENT_COLOURS.get(agent, "bold")
            self.console.print(
                f"[dim]{stamp}[/dim] | [{colour}]\\[{agent}][/{colour}] {style_msg or message}"
            )

    # Convenience helpers -------------------------------------------------
    def banner(self, title: str) -> None:
        self.console.rule(f"[bold]{title}") if self.echo else None
        with self.log_file.open("a", encoding="utf-8") as fh:
            fh.write("\n" + "=" * 70 + f"\n{title}\n" + "=" * 70 + "\n")

    def info(self, agent: str, message: str) -> None:
        self._write(agent, message)

    def started(self, agent: str, detail: str = "") -> None:
        msg = "started" + (f" - {detail}" if detail else "")
        self._write(agent, msg, f"[green]started[/green]" + (f" - {detail}" if detail else ""))

    def completed(self, agent: str, seconds: float, detail: str = "") -> None:
        msg = f"completed in {seconds:.1f}s" + (f" - {detail}" if detail else "")
        self._write(agent, msg)

    def handoff(self, src: str, dst: str) -> None:
        self._write(src, f"handed off to [{dst}]",
                    f"[bold blue]handed off to[/bold blue] \\[{dst}]")

    def warn(self, agent: str, message: str) -> None:
        self._write(agent, f"WARNING: {message}", f"[red]WARNING:[/red] {message}")
