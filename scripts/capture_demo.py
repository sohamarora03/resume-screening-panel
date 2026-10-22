"""
Automated screenshots and demo video of the Streamlit app (Playwright).

    streamlit run app.py               # in one terminal
    python scripts/capture_demo.py screenshots
    python scripts/capture_demo.py video

Screenshots -> docs/screenshots/*.png
Video       -> docs/demo/demo.webm (+ demo.mp4 via ffmpeg)
"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
DEMO = ROOT / "docs" / "demo"
URL = os.getenv("APP_URL", "http://localhost:8501")
CHROME = os.getenv("CHROME_PATH")          # optional custom Chromium binary
SAMPLE = ROOT / "sample_data"
RESUMES = sorted(str(p) for p in SAMPLE.glob("resume_*") if p.suffix in (".txt", ".pdf"))

BANNER_JS = """
(text) => {
  let b = document.getElementById('demo-caption');
  if (!b) {
    b = document.createElement('div');
    b.id = 'demo-caption';
    Object.assign(b.style, {position:'fixed', left:'50%', top:'14px', transform:'translateX(-50%)',
      zIndex: 999999, background:'rgba(15,23,42,.92)', color:'#fff', padding:'14px 26px',
      borderRadius:'12px', font:'600 20px system-ui, sans-serif', maxWidth:'80%',
      textAlign:'center', boxShadow:'0 8px 24px rgba(0,0,0,.35)'});
    document.body.appendChild(b);
  }
  b.textContent = text;
  b.style.display = text ? 'block' : 'none';
}
"""


class Demo:
    def __init__(self, page: Page, record: bool):
        self.page, self.record = page, record

    def caption(self, text: str, hold: float = 0):
        if self.record:
            self.page.evaluate(BANNER_JS, text)
            time.sleep(hold)

    def pause(self, secs: float):
        if self.record:
            time.sleep(secs)

    def shot(self, name: str, locator=None, full=False):
        if self.record:
            return
        self.page.evaluate(BANNER_JS, "")
        target = SHOTS / f"{name}.png"
        if locator is not None or full:
            # Streamlit scrolls inside its own container, so grow the viewport
            # to the page height first; otherwise tall sections get clipped
            height = self.page.evaluate(
                "() => document.querySelector('[data-testid=\"stMain\"]').scrollHeight")
            self.page.set_viewport_size({"width": 1280, "height": max(720, int(height) + 40)})
            self.page.wait_for_timeout(800)
            if locator is not None:
                locator.screenshot(path=str(target))
            else:
                self.page.screenshot(path=str(target))
            self.page.set_viewport_size({"width": 1280, "height": 720})
            self.page.wait_for_timeout(400)
        else:
            self.page.screenshot(path=str(target))
        print("saved", target.name)

    def slow_scroll(self, pixels: int, steps: int = 12, delay: float = 0.12):
        for _ in range(steps):
            self.page.mouse.wheel(0, pixels / steps)
            time.sleep(delay if self.record else 0.02)


def expander(page: Page, text: str):
    return page.locator('[data-testid="stExpander"]').filter(has_text=text).first


def run_flow(page: Page, record: bool) -> None:
    d = Demo(page, record)
    page.goto(URL)
    page.get_by_text("Resume Screening Panel").first.wait_for(timeout=60000)
    page.wait_for_timeout(1500)

    d.caption("Resume Screening Panel - a multi-agent HR system built with CrewAI", 5)
    d.caption("Four agents: JD Analyst, Screener, Bias Checker and HR Summary", 5)
    d.shot("01_upload_screen", full=True)

    d.caption("Step 1: upload the job description (Junior Python Developer)", 3)
    page.locator('input[type="file"]').nth(0).set_input_files(str(SAMPLE / "job_description.txt"))
    page.wait_for_timeout(1500)
    d.caption("Step 2: upload 6 resumes - a mix of PDF and TXT files", 3)
    page.locator('input[type="file"]').nth(1).set_input_files(RESUMES)
    page.wait_for_timeout(3000)               # let Streamlit receive all six files
    d.pause(3)
    d.shot("02_files_uploaded", full=True)

    d.caption("Step 3: click Run Panel - the agents start working in sequence", 3)
    pipeline = page.get_by_text("Agent pipeline").first
    page.get_by_role("button", name="Run Panel").click()
    pipeline.scroll_into_view_if_needed()
    page.wait_for_timeout(2500)
    d.caption("Live status: each card shows which agent is working and on what")
    d.shot("03_agents_running")
    page.wait_for_timeout(3500)
    d.shot("03b_agents_running_bias")

    page.get_by_text("Final ranked shortlist").wait_for(timeout=180000)
    page.wait_for_timeout(1500)
    d.caption("All four agents finished and handed off their results", 4)
    d.shot("04_pipeline_complete")

    sections = [
        ("Agent 1", "05_agent1_jd_analyst",
         "Agent 1 - JD Analyst: turns the job description into structured criteria (JSON)"),
        ("Agent 2", "06_agent2_screener",
         "Agent 2 - Screener: scores each resume with a per-skill evidence table"),
        ("Agent 3", "07_agent3_bias_checker",
         "Agent 3 - Bias Checker: catches gap, age, college, marital and origin bias"),
        ("Agent 4", "08_agent4_hr_summary",
         "Agent 4 - HR Summary: Hire / Maybe / Reject + tailored interview questions"),
    ]
    for label, shot_name, text in sections:
        exp = expander(page, label)
        exp.scroll_into_view_if_needed()
        d.caption(text)
        exp.locator("summary").click()
        page.wait_for_timeout(1200)
        d.pause(2)
        d.shot(shot_name, locator=exp)
        if record:
            d.slow_scroll(900 if label != "Agent 2" else 2600, steps=20, delay=0.25)
            d.pause(3)
        exp.scroll_into_view_if_needed()
        exp.locator("summary").click()       # collapse again
        page.wait_for_timeout(600)

    final = page.get_by_text("Final ranked shortlist").first
    final.scroll_into_view_if_needed()
    d.caption("Final ranked shortlist with bias-corrected scores, plus CSV / PDF downloads", 6)
    d.shot("09_final_ranking", locator=page.locator('[data-testid="stDataFrame"]').last)

    log_exp = expander(page, "hand-off log")
    log_exp.scroll_into_view_if_needed()
    log_exp.locator("summary").click()
    page.wait_for_timeout(1000)
    d.caption("Hand-off log: timestamped proof of the four separate agents", 6)
    d.shot("10_handoff_log", locator=log_exp)
    d.shot("11_full_results_page", full=True)
    d.caption("Thanks for watching - Resume Screening Panel", 4)


class ScreencastRecorder:
    """Records the page with Chrome's DevTools screencast and encodes it with ffmpeg.

    Works with any Chromium build (Playwright's own recorder needs a matching
    ffmpeg download). Frames arrive only when the page changes, so each frame's
    timestamp decides how long it stays on screen.
    """

    def __init__(self, page: Page, workdir: Path):
        self.page, self.dir = page, workdir
        self.frames: list[tuple[float, Path]] = []
        shutil.rmtree(workdir, ignore_errors=True)
        workdir.mkdir(parents=True)
        self.cdp = page.context.new_cdp_session(page)
        self.cdp.on("Page.screencastFrame", self._on_frame)

    def _on_frame(self, event):
        import base64
        path = self.dir / f"f{len(self.frames):06d}.jpg"
        path.write_bytes(base64.b64decode(event["data"]))
        self.frames.append((event["metadata"]["timestamp"], path))
        self.cdp.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})

    def start(self):
        self.cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 90,
                                               "maxWidth": 1280, "maxHeight": 720})

    def stop_and_encode(self, mp4: Path, webm: Path):
        self.page.wait_for_timeout(500)
        self.cdp.send("Page.stopScreencast")
        lines = []
        for (t, path), nxt in zip(self.frames, self.frames[1:] + [(None, None)]):
            duration = (nxt[0] - t) if nxt[0] else 2.0
            lines += [f"file '{path.name}'", f"duration {max(duration, 0.04):.3f}"]
        lines.append(f"file '{self.frames[-1][1].name}'")
        concat = self.dir / "frames.txt"
        concat.write_text("\n".join(lines))
        scale = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:white"
        base = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
                "-vf", f"{scale},fps=25"]
        subprocess.run(base + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                               str(mp4)], check=True)
        subprocess.run(base + ["-c:v", "libvpx-vp9", "-b:v", "1M", str(webm)], check=True)
        shutil.rmtree(self.dir, ignore_errors=True)


def main(mode: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    DEMO.mkdir(parents=True, exist_ok=True)
    record = mode == "video"
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME) if CHROME else p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 720},
                                  device_scale_factor=1 if record else 2)
        page = ctx.new_page()
        recorder = None
        if record:
            recorder = ScreencastRecorder(page, DEMO / "frames")
            recorder.start()
        run_flow(page, record)
        if recorder:
            recorder.stop_and_encode(DEMO / "demo.mp4", DEMO / "demo.webm")
            print("saved docs/demo/demo.mp4 and demo.webm")
        ctx.close()
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "screenshots")
