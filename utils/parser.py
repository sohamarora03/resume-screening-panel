"""
File and text helpers: reading PDF/TXT uploads and pulling JSON out of
LLM answers (LLMs sometimes wrap JSON in ```json fences or add chatter).
"""
import io
import json
import re
from pathlib import Path

from pypdf import PdfReader


def read_pdf_bytes(data: bytes) -> str:
    """Extract plain text from a PDF given its raw bytes."""
    reader = PdfReader(io.BytesIO(data))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(pages).strip()


def read_document(name: str, data: bytes) -> str:
    """Read an uploaded document (PDF or TXT) into text."""
    if name.lower().endswith(".pdf"):
        return read_pdf_bytes(data)
    return data.decode("utf-8", errors="ignore").strip()


def read_path(path: str | Path) -> str:
    path = Path(path)
    return read_document(path.name, path.read_bytes())


def candidate_name(text: str, fallback: str) -> str:
    """The first non-empty line of a resume is treated as the candidate's name."""
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line.replace("Name:", "").strip()[:60]
    return fallback


def extract_json(text: str):
    """Return the first JSON object/array found in `text`.

    Handles ```json fenced blocks and stray text around the JSON.
    Raises ValueError if no valid JSON is present.
    """
    if isinstance(text, (dict, list)):
        return text
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to the outermost {...} or [...] span
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start, end = text.find(open_c), text.rfind(close_c)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"No valid JSON found in model output: {text[:200]!r}")
