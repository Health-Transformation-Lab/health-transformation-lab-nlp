"""A PHI tagger for MACCROBAT's Age, Sex and Date labels: BIO data, scoring, regex dates (spec 010).

De-identification as sequence classification (named entity recognition): every word gets a tag,
B-<type> (begins an entity), I-<type> (inside one) or O (outside). The data comes from the original
brat records (maccrobat.load_brat); the model is fine-tuned by scripts/33_maccrobat_phi_tagger.py.
MACCROBAT's Date includes relative dates ("3 days later"), and Sex and most ages aren't HIPAA
identifiers: the label set follows the exercise, not Safe Harbor.
"""

from __future__ import annotations

import random
import re
from collections import Counter

import pandas as pd

TYPES = ("Age", "Date", "Sex")
LABELS = ["O"] + [f"{p}-{t}" for t in TYPES for p in ("B", "I")]
_WORD = re.compile(r"\w+|[^\w\s]")


# ------------------------------------------------------------------ data
def words(text: str) -> list[tuple[str, int, int]]:
    """Words with character offsets: runs of letters/digits, or one punctuation mark."""
    return [(m.group(), m.start(), m.end()) for m in _WORD.finditer(text)]


def bio_docs(records: list[dict], types=TYPES) -> list[dict]:
    """Records with text and entities (maccrobat.load_brat) -> words, BIO tags and sentence ranges.
    An entity's first word is B-, the rest I-; a word already tagged keeps its first tag."""
    out = []
    for r in records:
        ws = words(r["text"])
        tags = ["O"] * len(ws)
        for e in sorted((e for e in r["entities"] if e["type"] in types), key=lambda e: e["start"]):
            idx = [i for i, (_, a, b) in enumerate(ws) if a < e["end"] and e["start"] < b and tags[i] == "O"]
            for k, i in enumerate(idx):
                tags[i] = ("B-" if k == 0 else "I-") + e["type"]
        sents, start = [], 0
        for i, (w, a, _) in enumerate(ws):
            if i > start and "\n" in r["text"][ws[i - 1][2]:a]:
                sents.append((start, i))
                start = i
            if w in (".", "?", "!") and (i + 1 == len(ws) or not ws[i + 1][0][0].islower()):
                sents.append((start, i + 1))
                start = i + 1
        if start < len(ws):
            sents.append((start, len(ws)))
        out.append({"note_id": r["note_id"], "text": r["text"], "spans": ws,
                    "words": [w for w, _, _ in ws], "tags": tags, "sents": sents})
    return out


def split_docs(ids: list[str], test_share: float = 0.2, seed: int = 42) -> tuple[list[str], list[str]]:
    ids = sorted(ids)
    random.Random(seed).shuffle(ids)
    n_test = round(len(ids) * test_share)
    return sorted(ids[n_test:]), sorted(ids[:n_test])


def write_conll(docs: list[dict], path) -> None:
    """One "word tag" per line, a blank line between sentences, -DOCSTART- before each note."""
    lines = []
    for d in docs:
        lines.append("-DOCSTART- O")
        lines.append("")
        for a, b in d["sents"]:
            lines += [f"{w} {t}" for w, t in zip(d["words"][a:b], d["tags"][a:b])]
            lines.append("")
    from pathlib import Path
    Path(path).write_text("\n".join(lines) + "\n")


def chunks(doc: dict, max_words: int) -> list[tuple[int, int]]:
    """Consecutive whole sentences packed up to max_words words; a longer sentence is cut."""
    out, cur = [], None
    for a, b in doc["sents"]:
        for s in range(a, b, max_words):
            e = min(s + max_words, b)
            if cur and e - cur[0] <= max_words:
                cur = (cur[0], e)
            else:
                if cur:
                    out.append(cur)
                cur = (s, e)
    if cur:
        out.append(cur)
    return out


def align(word_ids: list, tags: list[str], label2id: dict) -> list[int]:
    """Sub-token labels: the word's tag on its first sub-token, -100 (ignored) elsewhere."""
    out, prev = [], None
    for w in word_ids:
        out.append(-100 if w is None or w == prev else label2id[tags[w]])
        prev = w
    return out


# ------------------------------------------------------------------ scores
def entities(tags: list[str]) -> list[tuple[str, int, int]]:
    """(type, start, end) word ranges; an I- that doesn't continue its type starts an entity."""
    out, cur = [], None
    for i, t in enumerate(tags):
        kind = t[2:] if t != "O" else None
        if kind and t.startswith("I-") and cur and cur[0] == kind and cur[2] == i:
            cur[2] = i + 1
        elif kind:
            cur = [kind, i, i + 1]
            out.append(cur)
        else:
            cur = None
    return [tuple(e) for e in out]


def score(gold: list[list[str]], pred: list[list[str]], types=TYPES) -> pd.DataFrame:
    """Exact-span entity precision, recall, F1 per type, and the support-weighted average."""
    rows = []
    for t in types:
        g = {(d, *e[1:]) for d, tags in enumerate(gold) for e in entities(tags) if e[0] == t}
        p = {(d, *e[1:]) for d, tags in enumerate(pred) for e in entities(tags) if e[0] == t}
        tp = len(g & p)
        prec = tp / len(p) if p else 0.0
        rec = tp / len(g) if g else 0.0
        rows.append({"type": t, "precision": prec, "recall": rec,
                     "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0, "support": len(g)})
    d = pd.DataFrame(rows)
    w = d.support / d.support.sum()
    avg = {"type": "weighted", **{k: float((d[k] * w).sum()) for k in ("precision", "recall", "f1")},
           "support": int(d.support.sum())}
    return pd.concat([d, pd.DataFrame([avg])], ignore_index=True)


def error_kinds(gold: list[list[str]], pred: list[list[str]]) -> Counter:
    """(type, kind) counts. A gold entity not found exactly is `boundary` (overlapped by the same type),
    `wrong_type` (by another type) or `missed`; a predicted entity overlapping no gold one is `spurious`."""
    c = Counter()
    for g_tags, p_tags in zip(gold, pred):
        g, p = entities(g_tags), entities(p_tags)
        for e in g:
            if e in p:
                continue
            over = [q for q in p if q[1] < e[2] and e[1] < q[2]]
            c[(e[0], "boundary" if any(q[0] == e[0] for q in over) else "wrong_type" if over else "missed")] += 1
        for q in p:
            if q not in g and not any(e[1] < q[2] and q[1] < e[2] for e in g):
                c[(q[0], "spurious")] += 1
    return c


# ------------------------------------------------------------------ regex dates
_M = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?"
      r"|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?")
_N = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a few|several|a|an)"
DATE_PATTERNS = {
    "numeric": (re.compile(r"\b\d{1,4}([/.-])\d{1,2}\1\d{1,4}\b"), "on 3/4/15"),
    "month_day_year": (re.compile(rf"\b{_M} \d{{1,2}}(?:st|nd|rd|th)?,? \d{{4}}\b"), "on July 29, 2015"),
    "day_month_year": (re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)? {_M},? \d{{4}}\b"), "on 27 October 2011"),
    "month_year": (re.compile(rf"\b{_M},? (?:19|20)\d{{2}}\b"), "in January 2014"),
    "year": (re.compile(r"\b(?:19|20)\d{2}\b"), "in 2012"),
    "relative": (re.compile(rf"\b{_N} (?:hours?|days?|weeks?|months?|years?) (?:later|after|before|ago|earlier|prior)\b",
                            re.IGNORECASE), "3 days later"),
    "hospital_day": (re.compile(r"\b(?:(?:post-?operative|hospital) )?day \d+\b|\bPOD \d+\b", re.IGNORECASE),
                     "on postoperative day 4"),
}


def regex_dates(text: str, spans: list[tuple[str, int, int]], tags: list[str], patterns) -> list[str]:
    """Words the model left O inside a match of the named date patterns are tagged Date."""
    out = list(tags)
    for name in patterns:
        rx = DATE_PATTERNS[name][0]
        for m in rx.finditer(text):
            idx = [i for i, (_, a, b) in enumerate(spans) if a < m.end() and m.start() < b]
            for k, i in enumerate(idx):
                if out[i] == "O":
                    out[i] = "I-Date" if k and out[idx[k - 1]].endswith("-Date") else "B-Date"
    return out
