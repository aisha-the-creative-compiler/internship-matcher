"""CV parsing: PDF/DOCX -> text -> skills found + a suggested experience level.

The CV is processed in memory only. It is never written to disk or stored.
"""
import io
import json
import os
import re

import docx
import pdfplumber

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class CVError(Exception):
    """Raised with a message that is safe to show to the student."""


def _load_skill_patterns():
    with open(os.path.join(BASE_DIR, "data", "skills.json"), encoding="utf-8") as f:
        skills = json.load(f)
    patterns = []
    for skill in skills:
        terms = {skill["name"].lower(), *[alias.lower() for alias in skill.get("aliases", [])]}
        # Longest first so "machine learning" is tried before "ml".
        alt = "|".join(re.escape(term) for term in sorted(terms, key=len, reverse=True))
        # Avoid matching a skill as part of a longer word; supports names such as C++ and Node.js.
        regex = re.compile(
            r"(?<![A-Za-z0-9+#])(?:" + alt + r")(?![A-Za-z0-9+#])",
            re.IGNORECASE,
        )
        patterns.append((skill["name"], regex))
    return patterns


_PATTERNS = _load_skill_patterns()


def get_skill_catalogue():
    with open(os.path.join(BASE_DIR, "data", "skills.json"), encoding="utf-8") as f:
        return json.load(f)


def extract_text(filename, data):
    """Extract text from an uploaded PDF or DOCX file held in memory."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        if not isinstance(data, (bytes, bytearray)) or not data.startswith(b"%PDF"):
            raise CVError("This file is not a valid PDF. Please upload a real PDF file.")
        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                pages = [(page.extract_text() or "") for page in pdf.pages]
        except Exception as exc:
            raise CVError(
                "We could not read this PDF. It may be corrupted or password-protected."
            ) from exc
        text = "\n".join(pages)
    elif name.endswith(".docx"):
        if not isinstance(data, (bytes, bytearray)) or not data.startswith(b"PK"):
            raise CVError("This file is not a valid DOCX. Please upload a real Word (.docx) file.")
        try:
            document = docx.Document(io.BytesIO(data))
            parts = [paragraph.text for paragraph in document.paragraphs]
            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        parts.append(cell.text)
            text = "\n".join(parts)
        except Exception as exc:
            raise CVError("We could not read this DOCX file. It may be corrupted.") from exc
    else:
        raise CVError("Unsupported file type. Please upload a PDF or DOCX file.")

    if not text.strip():
        raise CVError(
            "No text could be found in this file (it may be a scanned image). "
            "Please select your skills manually instead."
        )
    return text


def parse_text(filename, data):
    """Backward-compatible name for extracting text from an uploaded CV.

    Older tests and callers use parse_text(); keep it as an alias so they
    receive the same validation and friendly errors as extract_text().
    """
    return extract_text(filename, data)


def extract_skills(text):
    """Return canonical skill names found in the supplied text."""
    if not isinstance(text, str) or not text:
        return []
    return [name for name, regex in _PATTERNS if regex.search(text)]


def estimate_level(text):
    """Suggest a level based on explicit 'N years' mentions in the CV."""
    if not isinstance(text, str):
        text = ""
    years = [
        int(value)
        for value in re.findall(r"(\d{1,2})\+?\s*(?:years?|yrs?)\b", text, re.IGNORECASE)
    ]
    years = [value for value in years if value <= 15]
    best = max(years) if years else 0
    if best >= 3:
        return "advanced"
    if best >= 1:
        return "intermediate"
    return "beginner"


def parse_cv(filename, data):
    """Parse an uploaded CV and return its detected skills and suggested level."""
    text = extract_text(filename, data)
    return {"skills": extract_skills(text), "suggested_level": estimate_level(text)}
