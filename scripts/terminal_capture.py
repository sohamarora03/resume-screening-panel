"""
Record a CLI run of the panel as terminal "screenshots" (proof of multiple agents).

    python scripts/terminal_capture.py

Uses rich's console recording: saves docs/screenshots/terminal_run.svg and a
PNG copy (rendered in Chromium) for the Word report.
"""
import sys
from pathlib import Path

from rich.console import Console
from playwright.sync_api import sync_playwright
from rich.terminal_theme import MONOKAI

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import main  # noqa: E402  (needs the path set first)

OUT = ROOT / "docs" / "screenshots"


def capture() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    console = Console(record=True, width=132, force_terminal=True, highlight=False)
    console.print("[bold]$ python main.py[/bold]  [dim]# run all four agents on sample_data/[/dim]\n")
    main.main([], console=console)
    svg = OUT / "terminal_run.svg"
    console.save_svg(str(svg), title="Resume Screening Panel - terminal run", theme=MONOKAI)
    # Render the SVG in Chromium (it has proper monospace + box-drawing fonts)
    import os
    with sync_playwright() as p:
        chrome = os.getenv("CHROME_PATH")
        browser = p.chromium.launch(executable_path=chrome) if chrome else p.chromium.launch()
        page = browser.new_page(device_scale_factor=2)
        page.goto(svg.as_uri())
        box = page.locator("svg").bounding_box()
        page.set_viewport_size({"width": int(box["width"]) + 2, "height": int(box["height"]) + 2})
        page.locator("svg").screenshot(path=str(OUT / "terminal_run.png"))
        browser.close()
    # trim the white page margin around the terminal window
    from PIL import Image, ImageChops
    png = OUT / "terminal_run.png"
    img = Image.open(png).convert("RGB")
    bbox = ImageChops.difference(img, Image.new("RGB", img.size, "white")).getbbox()
    if bbox:
        img.crop(bbox).save(png)
    print("saved", svg, "and terminal_run.png")


if __name__ == "__main__":
    capture()
