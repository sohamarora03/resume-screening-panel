import pytest
from reportlab.pdfgen import canvas

from utils.parser import candidate_name, extract_json, read_document, read_path
from utils.skills import aliases_for, find_evidence


def test_reads_txt():
    assert read_document("a.txt", b"Hello\nWorld") == "Hello\nWorld"


def test_reads_pdf(tmp_path):
    pdf = tmp_path / "cv.pdf"
    c = canvas.Canvas(str(pdf))
    c.drawString(72, 750, "Test Candidate")
    c.drawString(72, 730, "Skills: Python, SQL")
    c.save()
    text = read_path(pdf)
    assert "Test Candidate" in text and "Python" in text


def test_sample_pdf_resume_is_readable():
    text = read_path("sample_data/resume_04_sneha_patil.pdf")
    assert candidate_name(text, "x") == "Sneha Patil"


def test_extract_json_from_fenced_block():
    assert extract_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_surrounding_text():
    assert extract_json('Answer: {"b": [1, 2]} done') == {"b": [1, 2]}


def test_extract_json_raises_on_garbage():
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_skill_aliases_and_evidence():
    assert {"django", "flask"} <= set(aliases_for("Django or Flask"))
    assert find_evidence("Used PostgreSQL daily", aliases_for("SQL (MySQL or PostgreSQL)"))
    assert find_evidence("JavaScript and React", aliases_for("Java")) is None
