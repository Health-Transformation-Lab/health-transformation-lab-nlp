"""Rules that read status from a chart note's text (source 1).

Reads the clinician's stated diagnosis first, in any of the schemes clinicians
use (2017 stage/grade, abbreviations, pre-2017 severity, AAP case types).
If none is stated, falls back to the findings (numbers or descriptors).
Ignores copied-forward text from previous visits.

This is the notes column of the method-comparison step and the rules rung of
the model ladder. The BERT models are scored against the same reviewers.
"""

from __future__ import annotations

import re

from .labels import PerioChart, Status, label_chart

_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "1": 1, "2": 2, "3": 3, "4": 4}
_STAGE = re.compile(r"\b(?:stage|st\.?|perio)\s*(IV|III|II|I|[1-4])(?=[\s/.,ABCabc]|$)", re.IGNORECASE)
_OLD = re.compile(r"\b(slight|mild|moderate|severe|advanced)\s+chronic periodontitis", re.IGNORECASE)
_CASE_TYPE = re.compile(r"case type\s*(IV|III|II|I)\b", re.IGNORECASE)
_OLD_MAP = {"slight": 1, "mild": 1, "moderate": 2, "severe": 3, "advanced": 3}
_CASE_MAP = {"I": "gingivitis", "II": 1, "III": 2, "IV": 3}
_GRADE = re.compile(r"\b(?:grade|gr\.?)\s*(iii|ii|i|[abc])\b", re.IGNORECASE)
_GRADE_MAP = {"a": "A", "b": "B", "c": "C", "i": "A", "ii": "B", "iii": "C"}
# Extent words, including the typo variants seen in real notes (arXiv 2311.10809).
_EXTENT = re.compile(r"\b(gen[a-z]*[sz][a-z]*d|loc[a-z]*[sz][a-z]*d)\b", re.IGNORECASE)
# An extent word followed by one of these describes a different finding (arXiv 2407.21050).
_NOT_PERIO_EXTENT = re.compile(r"^\s+(recession|gingival|inflammation|plaque|calculus|bop|bleeding|bone)",
                               re.IGNORECASE)


def current_text(text: str) -> str:
    """Drop copied-forward sections."""
    return re.split(r"--\s*copied from visit", text, flags=re.IGNORECASE)[0]


def _teeth_lost(t: str) -> int:
    m = re.search(r"(\d+) teeth lost|extraction of (\d+) teeth", t, re.IGNORECASE)
    if m:
        return int(m.group(1) or m.group(2))
    m = re.search(r"missing ((?:#\d+,?\s*)+)\(hx perio", t, re.IGNORECASE)
    return len(re.findall(r"#\d+", m.group(1))) if m else 0


def _stage_status(stage: int, t: str) -> str:
    if stage == 3 and _teeth_lost(t) >= 5:
        stage = 4
    return f"periodontitis_stage_{stage}"


def read_stated_dx(text: str) -> str | None:
    t = current_text(text)
    if re.search(r"gingival health|periodontal health|perio(?:dontium)? WNL|perio health", t, re.IGNORECASE):
        return Status.HEALTHY.value
    if re.search(r"\bgingivitis\b", t, re.IGNORECASE) and not re.search(r"periodontitis|\bperio\s+(?:st|[1-4IV])", t, re.IGNORECASE):
        return Status.GINGIVITIS.value
    m = _STAGE.search(t)
    # Published notes sometimes give "Generalized Stage 3 Grade B" with no disease word.
    # An explicit stage is taken as written; only the pre-2017 terms below, which
    # can't separate stage III from IV, are upgraded on documented tooth loss.
    if m and (re.search(r"perio|periodontitis", t, re.IGNORECASE) or _GRADE.search(t)):
        return f"periodontitis_stage_{_ROMAN[m.group(1).upper()]}"
    m = _OLD.search(t)
    if m:
        return _stage_status(_OLD_MAP[m.group(1).lower()], t)
    m = _CASE_TYPE.search(t)
    if m:
        v = _CASE_MAP[m.group(1).upper()]
        return v if isinstance(v, str) else _stage_status(v, t)
    return None


def _num(pattern: str, t: str) -> float | None:
    m = re.search(pattern, t, re.IGNORECASE)
    if not m:
        return None
    return float(next(g for g in m.groups() if g is not None))


def read_findings(text: str) -> str:
    t = current_text(text)
    # Probing depth is not read here: in notes it is usually a site list, not the max.
    bop = _num(r"BOP (\d+)%|bleeding on probing (\d+)%", t)
    if bop is None:
        bop = 45 if re.search(r"heavy BOP", t, re.IGNORECASE) else 25 if re.search(r"BOP generalized", t, re.IGNORECASE) \
            else 12 if re.search(r"localized BOP", t, re.IGNORECASE) else 0
    cal = _num(r"CAL up to (\d+)|max CAL (\d+)|attachment loss \d+-(\d+)", t)
    if cal is None:
        cal = 6 if re.search(r"severe attachment loss", t, re.IGNORECASE) else 3.5 if re.search(r"moderate attachment loss", t, re.IGNORECASE) \
            else 1.5 if re.search(r"slight attachment loss", t, re.IGNORECASE) else None
    rbl = _num(r"bone loss[^~\n]*~(\d+)%", t)
    if rbl is None:
        rbl = 45 if re.search(r"severe horizontal bone loss|apical third", t, re.IGNORECASE) else \
            25 if re.search(r"moderate horizontal bone loss|middle third", t, re.IGNORECASE) else \
            8 if re.search(r"mild horizontal bone loss|coronal third", t, re.IGNORECASE) else None
    if cal is None and rbl is None:
        rbl = 0.0   # nothing charted: no evidence of loss
    # AAP: stage from CAL; RBL only when CAL isn't in the note (labels.py)
    return label_chart(PerioChart(0, min(bop, 100), cal, None if rbl is None else min(rbl, 100),
                                  _teeth_lost(t))).value


def read_note(text: str) -> str:
    return read_stated_dx(text) or read_findings(text)


def _dx_region(t: str) -> str:
    """The diagnosis line if one is marked, else the whole current text."""
    m = re.search(r"(?im)^\s*(?:d|dx|diagnosis|impression|a)\s*[:\-].*$", t)
    return m.group(0) if m else t


def read_grade(text: str) -> str:
    """A/B/C for periodontitis, 'NA' otherwise, 'unknown' if not written."""
    t = current_text(text)
    status = read_stated_dx(text)
    if not status or not status.startswith("periodontitis"):
        return "NA"
    m = _GRADE.search(_dx_region(t)) or _GRADE.search(t)
    return _GRADE_MAP[m.group(1).lower()] if m else "unknown"


def read_extent(text: str) -> str:
    """localized/generalized for periodontitis, 'NA' otherwise, 'unknown' if not written.
    Skips extent words that describe another finding ('generalized recession')."""
    t = current_text(text)
    status = read_stated_dx(text)
    if not status or not status.startswith("periodontitis"):
        return "NA"
    for region in (_dx_region(t), t):
        for m in _EXTENT.finditer(region):
            if _NOT_PERIO_EXTENT.match(region[m.end():]):
                continue
            return "generalized" if m.group(1).lower().startswith("gen") else "localized"
    return "unknown"
