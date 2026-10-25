"""De-identification: find PHI spans in a note and replace them with tags.

Nothing reaches Label Studio (or any model) until it has passed through here
AND the leak gate. Two engines:

  regex     built in. Context patterns (Patient:, Pt, Dr., MRN, DOS ...),
            date / phone / ID / street-address shapes, and a capitalised
            name-pair heuristic, with an allowlist of dental terms so
            abbreviations like BOP, SRP, MB, DL, FMX are never redacted (the
            earlier de-id failed exactly there). Baseline; tuned on the
            synthetic note formats, so it will under-perform on real notes.
  presidio  Microsoft Presidio (spaCy NER + recognisers) with the same dental
            allowlist. pip install presidio-analyzer and a spaCy model;
            needs Python <= 3.12 today.

On synthetic notes every PHI span is known (phi.py), so `score_deid` measures
recall and over-redaction exactly and `leak_check` fails hard if any injected
value survives. On real notes the gate is `residual_scan` (re-run detectors on
the output) plus a human review sample, because nothing is known in advance.
"""

from __future__ import annotations

import re

DENTAL_ALLOWLIST = {
    "BOP", "CAL", "RBL", "PD", "SRP", "FMX", "BWX", "PAN", "PSR", "WNL", "MB", "DB", "ML", "DL", "B", "L",
    "M", "D", "OHI", "RTC", "FM", "UR", "LR", "UL", "LL", "HTN", "NKDA", "T2DM", "A1c", "AAP", "EFP",
    "Dx", "Tx", "Pt", "Hx", "Med", "Exam", "Impression", "Patient", "Provider", "DOS", "MRN", "DOB",
    "Stage", "Grade", "Generalized", "Localized", "Gen", "Loc", "Perio", "Periodontitis", "Gingivitis",
    "Plaque", "Dental", "Clinical", "Case", "Type", "Prophy", "Recall", "Referred", "Referral", "Next",
    "PERIODONTAL", "CHARTING", "COMPLETED", "Findings", "See", "Adult", "Pt's", "Dr", "Mr", "Mrs", "Ms", "I", "II", "III", "IV", "A", "C", "Gr", "St",
}

_NAME_WORD = r"[A-Z][a-z]+(?:-[A-Z][a-z]+)?"
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("NAME", re.compile(rf"(?<=Patient: )({_NAME_WORD}, {_NAME_WORD})")),
    ("NAME", re.compile(rf"(?<=\bPt )({_NAME_WORD} {_NAME_WORD})(?= \()")),
    ("NAME", re.compile(rf"(?<=\bDr\. )({_NAME_WORD}(?: {_NAME_WORD})?)")),
    ("ID", re.compile(r"(?<=MRN: )(\d{6,10})")),
    ("ID", re.compile(r"(?<=\()(\d{7,10})(?=\))")),
    ("ID", re.compile(r"\b(\d{8,10})\b")),
    ("DATE", re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}|"
                        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4})\b")),
    ("PHONE", re.compile(r"(\(\d{3}\) ?\d{3}-\d{4}|\b\d{3}-\d{3}-\d{4}\b)")),
    ("LOCATION", re.compile(r"(\d{1,5} (?:[A-Z0-9][a-z0-9]* )+(?:St|Ave|Street|Dr|Rd|Ln|Blvd|Ct)\b(?:, [A-Z][a-z]+)?)")),
    ("LOCATION", re.compile(rf"({_NAME_WORD} (?:Periodontics|Dental Group|Family Dentistry|Dental|Clinic))")),
]
_CAP_PAIR = re.compile(rf"\b({_NAME_WORD}) ({_NAME_WORD})\b")


def _merge(spans: list[dict]) -> list[dict]:
    spans = sorted(spans, key=lambda s: (s["start"], -s["end"]))
    out: list[dict] = []
    for s in spans:
        if out and s["start"] < out[-1]["end"]:
            out[-1]["end"] = max(out[-1]["end"], s["end"])
        else:
            out.append(dict(s))
    return out


def detect_regex(text: str) -> list[dict]:
    spans = []
    for kind, pat in _PATTERNS:
        for m in pat.finditer(text):
            spans.append({"start": m.start(1), "end": m.end(1), "type": kind})
    for m in _CAP_PAIR.finditer(text):
        if m.group(1) not in DENTAL_ALLOWLIST and m.group(2) not in DENTAL_ALLOWLIST:
            spans.append({"start": m.start(), "end": m.end(), "type": "NAME"})
    return _merge(spans)


def detect_presidio(text: str) -> list[dict]:  # pragma: no cover - optional dependency
    from presidio_analyzer import AnalyzerEngine
    global _PRESIDIO
    try:
        engine = _PRESIDIO
    except NameError:
        engine = _PRESIDIO = AnalyzerEngine()
    res = engine.analyze(text=text, language="en", allow_list=sorted(DENTAL_ALLOWLIST),
                         entities=["PERSON", "DATE_TIME", "PHONE_NUMBER", "LOCATION", "US_SSN",
                                   "EMAIL_ADDRESS", "MEDICAL_LICENSE", "US_DRIVER_LICENSE"])
    kind = {"PERSON": "NAME", "DATE_TIME": "DATE", "PHONE_NUMBER": "PHONE", "LOCATION": "LOCATION"}
    spans = [{"start": r.start, "end": r.end, "type": kind.get(r.entity_type, "ID")} for r in res]
    return _merge(spans + [s for s in detect_regex(text) if s["type"] == "ID"])


ENGINES = {"regex": detect_regex, "presidio": detect_presidio}


def redact(text: str, spans: list[dict]) -> str:
    out, last = [], 0
    for s in sorted(spans, key=lambda s: s["start"]):
        out.append(text[last:s["start"]])
        out.append(f"[{s['type']}]")
        last = s["end"]
    out.append(text[last:])
    return "".join(out)


def deidentify(text: str, engine: str = "regex") -> tuple[str, list[dict]]:
    spans = ENGINES[engine](text)
    return redact(text, spans), spans


# ------------------------------------------------------------ gates & scoring
def leak_check(deid_text: str, known_phi: list[dict]) -> list[str]:
    """Synthetic data only: every injected PHI value that survived (should be [])."""
    return [p["text"] for p in known_phi if p["text"] in deid_text]


def residual_scan(deid_text: str) -> list[dict]:
    """Real data: detectors re-run on the output. Non-empty = hold for human review."""
    return detect_regex(deid_text)


def score_deid(text: str, known_phi: list[dict], found: list[dict]) -> dict:
    """Character-level recall (PHI removed) and over-redaction (non-PHI removed)."""
    phi = set()
    for p in known_phi:
        phi.update(range(p["start"], p["end"]))
    red = set()
    for s in found:
        red.update(range(s["start"], s["end"]))
    return {"phi_chars": len(phi), "phi_chars_removed": len(phi & red),
            "non_phi_chars_removed": len(red - phi)}
