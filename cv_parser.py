
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

    for s in skills:
        terms = {s["name"].lower(), *[a.lower() for a in s.get("aliases", [])]}

        # Longest first so "machine learning" is tried before "ml".
        alt = "|".join(
            re.escape(t) for t in sorted(terms, key=len, reverse=True)
        )

        # Not part of a longer word (also protects things like "c++" / "node.js").
        regex = re.compile(
            r"(?<![A-Za-z0-9+#])(?:" + alt + r")(?![A-Za-z0-9+#])",
            re.IGNORECASE
        )

        patterns.append((s["name"], regex))

    return patterns


_PATTERNS = _load_skill_patterns()


def get_skill_catalogue():
    with open(os.path.join(BASE_DIR, "data", "skills.json"), encoding="utf-8") as f:
        return json.load(f)


def extract_text(filename, data):
    name = (filename or "").lower()

    if name.endswith(".pdf"):
        if not data.startswith(b"%PDF"):
            raise CVError("This file is not a valid PDF. Please upload a real PDF file.")

        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                pages = [(page.extract_text() or "") for page in pdf.pages]
        except Exception:
            raise CVError("We could not read this PDF. It may be corrupted or password-protected.")

        text = "\n".join(pages)

    elif name.endswith(".docx"):
        if not data.startswith(b"PK"):
            raise CVError("This file is not a valid DOCX. Please upload a real Word (.docx) file.")

        try:
            document = docx.Document(io.BytesIO(data))
            parts = [p.text for p in document.paragraphs]

            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        parts.append(cell.text)

            text = "\n".join(parts)

        except Exception:
            raise CVError("We could not read this DOCX file. It may be corrupted.")

    else:
        raise CVError("Unsupported file type. Please upload a PDF or DOCX file.")

    if not text.strip():
        raise CVError(
            "No text could be found in this file (it may be a scanned image). "
            "Please select your skills manually instead."
        )

    return text


def extract_skills(text):
    return [name for name, regex in _PATTERNS if regex.search(text)]


def estimate_level(text):
    """Very simple suggestion based on 'N years' mentions. The student can change it."""

    years = [
        int(y)
        for y in re.findall(
            r"(\d{1,2})\+?\s*(?:years?|yrs?)\b",
            text,
            re.IGNORECASE
        )
    ]

    years = [y for y in years if y <= 15]
    best = max(years) if years else 0

    if best >= 3:
        return "advanced"

    if best >= 1:
        return "intermediate"

    return "beginner"


def parse_text(text):
    """Parse plain CV text and return skills and a suggested experience level."""

    if not isinstance(text, str) or not text.strip():
        raise CVError("No text was provided. Please enter some CV text.")

    if len(text) > 20000:
        raise CVError("The CV text is too long. Please use a shorter version.")

    return {
        "skills": extract_skills(text),
        "suggested_level": estimate_level(text)
    }


def parse_cv(filename, data):
    text = extract_text(filename, data)
    return {"skills": extract_skills(text), "suggested_level": estimate_level(text)}
