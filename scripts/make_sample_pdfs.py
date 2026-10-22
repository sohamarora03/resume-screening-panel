"""Convert some sample resumes to PDF so the app is demonstrated with both formats.

Usage:  python scripts/make_sample_pdfs.py
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data"
TO_PDF = ["resume_02_oluwaseun_adeyemi", "resume_04_sneha_patil", "resume_06_kevin_dsouza"]


def text_to_pdf(src: Path, dst: Path) -> None:
    styles = getSampleStyleSheet()
    story = []
    for i, line in enumerate(src.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            story.append(Spacer(1, 6))
            continue
        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(safe, styles["Title"] if i == 0 else styles["Normal"]))
    SimpleDocTemplate(str(dst), pagesize=A4, title=src.stem).build(story)


if __name__ == "__main__":
    for stem in TO_PDF:
        src = SAMPLE / f"{stem}.txt"
        if src.exists():
            text_to_pdf(src, SAMPLE / f"{stem}.pdf")
            src.unlink()          # keep only the PDF version
            print("created", stem + ".pdf")
