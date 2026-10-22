"""Export the panel's results as a table (DataFrame/CSV) and as a PDF report."""
import io

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (ListFlowable, ListItem, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)


def results_table(result: dict) -> pd.DataFrame:
    reviews = {r["candidate"]: r for r in result["bias_reviews"]}
    rows = []
    for r in result["summary"]["ranking"]:
        review = reviews.get(r["candidate"], {})
        flags = review.get("bias_flags", [])
        rows.append({
            "Rank": r["rank"],
            "Candidate": r["candidate"],
            "Screener Score": review.get("original_score"),
            "Final Score": r["final_score"],
            "Recommendation": r["recommendation"],
            "Bias Flags": ", ".join(f["category"] for f in flags) or "None",
            "Missing Must-haves": ", ".join(r.get("gaps", [])) or "None",
        })
    return pd.DataFrame(rows)


def to_csv(result: dict) -> bytes:
    return results_table(result).to_csv(index=False).encode("utf-8")


def to_pdf(result: dict) -> bytes:
    styles = getSampleStyleSheet()
    small = styles["BodyText"].clone("small", fontSize=8, leading=10)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
                            title="Resume Screening Panel - Results")
    story = [Paragraph("Resume Screening Panel - Results", styles["Title"]),
             Paragraph(f"Role: {result['criteria'].get('job_title', '')}", styles["Heading3"]),
             Paragraph(result["summary"].get("summary", ""), styles["BodyText"]),
             Spacer(1, 10)]

    df = results_table(result)
    data = [[Paragraph(f"<b>{c}</b>", small) for c in df.columns]]
    data += [[Paragraph(str(v), small) for v in row] for row in df.values.tolist()]
    table = Table(data, repeatRows=1, colWidths=[1.1*cm, 3.4*cm, 1.8*cm, 1.6*cm, 2.2*cm, 3.6*cm, 4.3*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story += [table, Spacer(1, 14), Paragraph("Interview questions", styles["Heading2"])]

    for r in result["summary"]["ranking"]:
        if not r["interview_questions"]:
            continue
        story.append(Paragraph(f"{r['candidate']} ({r['recommendation']}, {r['final_score']}/100)",
                               styles["Heading4"]))
        story.append(ListFlowable([ListItem(Paragraph(q, styles["BodyText"]))
                                   for q in r["interview_questions"]], bulletType="1"))
    doc.build(story)
    return buf.getvalue()
