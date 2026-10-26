"""MACCROBAT case reports (original brat files or BIO labels) as a de-identification test set (spec 009).

MACCROBAT (Caufield 2019, https://doi.org/10.6084/m9.figshare.9764942.v2, CC BY 4.0) is 200 clinical
case reports from PubMed Central with hand-annotated entities. A Hugging Face mirror publishes the
same annotations as BIO token labels: B- begins an entity, I- continues it, O is outside.

It was not built for PHI and holds no names or contact details, so it tests two things:
  phi       identifiers derived by rule (HIPAA Safe Harbor): dates with a month or day, ages >= 90
  clinical  entities that must survive (symptoms, drugs, procedures, ...): the scorer's "decoys"
Everything else (relative dates, a year alone, ages under 90, sex, places, ethnicity) is "other".

Real (published, de-identified) text: download to data/raw/, never commit it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# The original release (brat standoff, exact text) on figshare: MACCROBAT2020.zip, file 21489405.
FIGSHARE_URL = "https://ndownloader.figshare.com/files/21489405"
# Hugging Face mirror (BIO tokens; drops overlapping entities and the original spacing), pinned.
HF_REPO = "ktgiahieu/maccrobat2018_2020"
HF_REVISION = "9a14415289dea0e603687b14d4581a81ecdfe9c9"
HF_URL = f"https://huggingface.co/datasets/{HF_REPO}/resolve/{HF_REVISION}/data.jsonl"

CLINICAL_TYPES = {"Sign_symptom", "Disease_disorder", "Diagnostic_procedure", "Therapeutic_procedure",
                  "Medication", "Dosage", "Administration", "Lab_value", "Biological_structure",
                  "Detailed_description", "Clinical_event", "History", "Family_history", "Severity", "Outcome"}

_MONTH = re.compile(r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|june?|july?|aug(?:ust)?"
                    r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b|\bmay\b(?! (?:have|be)\b)", re.IGNORECASE)
_NUMERIC_DATE = re.compile(r"\b\d{1,4}\s*[/.-]\s*\d{1,2}\s*[/.-]\s*\d{1,4}\b")
_AGE = re.compile(r"\d+")

_NO_SPACE_BEFORE = {",", ".", ";", ":", ")", "]", "%", "!", "?", "-", "/"}
_NO_SPACE_AFTER = {"(", "[", "-", "/"}


def bio_spans(tokens: list[str], tags: list[str]) -> tuple[str, list[dict]]:
    """BIO tokens -> (text, [{start, end, type, text}]). An I- tag that doesn't continue an entity of
    its type starts a new one. Spacing is approximate: BIO files drop the original whitespace."""
    parts, spans, pos, cur, prev = [], [], 0, None, None
    for tok, tag in zip(tokens, tags):
        if tok == "\n":
            sep, tok = "", "\n"
        elif prev is None or prev == "\n" or tok in _NO_SPACE_BEFORE or prev in _NO_SPACE_AFTER:
            sep = ""
        else:
            sep = " "
        parts.append(sep + tok)
        start, pos = pos + len(sep), pos + len(sep) + len(tok)
        kind = tag[2:] if tag[:2] in ("B-", "I-") else None
        if kind and tag.startswith("I-") and cur and cur["type"] == kind:
            cur["end"] = pos
        elif kind:
            cur = {"start": start, "end": pos, "type": kind}
            spans.append(cur)
        else:
            cur = None
        prev = tok
    text = "".join(parts)
    return text, [s | {"text": text[s["start"]:s["end"]]} for s in spans]


def role(kind: str, text: str) -> str:
    """phi, clinical or other (see the module docstring)."""
    if kind == "Date" and (_MONTH.search(text) or _NUMERIC_DATE.search(text)):
        return "phi"
    if kind == "Age" and any(int(n) >= 90 for n in _AGE.findall(text)) and "month" not in text.lower():
        return "phi"
    return "clinical" if kind in CLINICAL_TYPES else "other"


def _core(span: dict) -> dict:
    """A PHI date trimmed to its first and last month or number ("in October 2014" -> "October 2014"),
    so lead-in words an engine rightly keeps don't count as a leak."""
    hits = [(m.start(), m.end()) for rx in (_MONTH, _NUMERIC_DATE, _AGE) for m in rx.finditer(span["text"])]
    a, b = min(h[0] for h in hits), max(h[1] for h in hits)
    return span | {"start": span["start"] + a, "end": span["start"] + b, "text": span["text"][a:b]}


def _record(note_id, tier: str, text: str, spans: list[dict]) -> dict:
    ents = [s | {"role": role(s["type"], s["text"])} for s in sorted(spans, key=lambda s: s["start"])]
    return {"note_id": note_id, "tier": tier, "text": text, "entities": ents,
            "phi": [_core(s) for s in ents if s["role"] == "phi"],
            "decoys": [s for s in ents if s["role"] == "clinical"]}


def load_bio(path, tier: str = "maccrobat") -> list[dict]:
    """JSONL rows {"tokens", "tags"} -> challenge records (spec 007 format) plus `entities` with a role.
    Rows with the same tokens are copies (the mirror holds the 2018 and 2020 releases): the last one wins."""
    docs = {}
    for line in Path(path).read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            docs[tuple(r["tokens"])] = r["tags"]
    return [_record(f"{tier}_{i:03d}", tier, *bio_spans(list(tokens), tags))
            for i, (tokens, tags) in enumerate(docs.items())]


def _brat_spans(text: str, ann: str) -> list[dict]:
    """brat standoff "T" lines (type, start end[;start end], text); each fragment of a split entity
    becomes its own span. Events and relations are skipped."""
    spans = []
    for line in ann.splitlines():
        if not line.startswith("T"):
            continue
        kind, _, offsets = line.split("\t")[1].partition(" ")
        for frag in offsets.split(";"):
            a, b = (int(x) for x in frag.split())
            spans.append({"start": a, "end": b, "type": kind, "text": text[a:b]})
    return spans


def load_brat(path, tier: str = "maccrobat") -> list[dict]:
    """The original release (figshare zip, or the folder it unpacks to): NNN.txt with NNN.ann.
    Exact text and offsets, unlike the BIO mirror."""
    import zipfile
    path = Path(path)
    if path.is_dir():
        files = {p.name: p.read_text(encoding="utf-8") for p in path.rglob("*") if p.suffix in (".txt", ".ann")}
    else:
        with zipfile.ZipFile(path) as z:
            files = {Path(n).name: z.read(n).decode("utf-8") for n in z.namelist() if n.endswith((".txt", ".ann"))}
    out = []
    for name in sorted(files):
        if name.endswith(".txt") and name[:-4] + ".ann" in files:
            text = files[name]
            out.append(_record(name[:-4], tier, text, _brat_spans(text, files[name[:-4] + ".ann"])))
    return out
