"""Label Studio review flows for de-identification (spec 008).

Two projects, each with tasks out, an export back in, and scores:

  gold  Annotators mark every identifier in the ORIGINAL note (labelstudio/deid_gold.xml),
        categories from spec 007 (phi_challenge.CATEGORIES). Tasks carry one engine's spans as
        Label Studio predictions to accept or fix; a seeded share has none, to measure anchoring.
        Scores: agreement between annotators (entity F1, exact span, with/without category), a
        consensus gold (characters at least half the note's annotators marked) that every engine
        is scored against with deid_eval.score_records, and on synthetic notes each annotator's
        recall against the generator's spans, aided vs unaided.
  qa    Reviewers read DE-IDENTIFIED notes (labelstudio/deid_qa.xml): does any identifier remain,
        and was clinical meaning lost to over-redaction. Sample: notes the residual scan flags
        first, then seeded random ones, up to n. Scores: leak-note rate with a Wilson 95% CI
        (a note leaks if any reviewer says so), per reviewer and pooled; against the answer key
        (synthetic only, never in the tasks) reviewer sensitivity and specificity.

Task files contain note text with (fake) PHI, a QA leak included: write them to RAW_DIR only.
`simulate_*_export` fake the annotators for dry runs; their output is named simulated_*.
R twin of `agreement` and `wilson`: r/R/08_deid.R.
"""

from __future__ import annotations

import math
import random
from collections import Counter

import pandas as pd

from .deid import residual_scan
from .phi_challenge import CATEGORIES

UNSPECIFIED = "PHI_UNSPECIFIED"
GOLD_LABELS = [*CATEGORIES, UNSPECIFIED]
# engine types that name a category; NAME (patient? doctor? relative?) and LOCATION don't
ENGINE_TYPE_MAP = {"DATE": "DATE", "PHONE": "PHONE", "EMAIL": "EMAIL", "URL": "URL", "AGE": "AGE",
                   "SSN": "SSN", "ID": "ID_OTHER"}


def _label(engine_type: str) -> str:
    return engine_type if engine_type in CATEGORIES else ENGINE_TYPE_MAP.get(engine_type, UNSPECIFIED)


def _result(text: str, s: dict, label: str, from_name: str, i: int) -> dict:
    return {"id": f"p{i}", "from_name": from_name, "to_name": "text", "type": "labels",
            "value": {"start": s["start"], "end": s["end"], "text": text[s["start"]:s["end"]], "labels": [label]}}


def _who(ann: dict) -> str:
    w = ann.get("completed_by")
    return str(w.get("email", w.get("id")) if isinstance(w, dict) else w)


def _chars(spans) -> set[int]:
    return {i for s in spans for i in range(int(s["start"]), int(s["end"]))}


def _runs(chars: set[int]) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for i in sorted(chars):
        if out and i == out[-1][1]:
            out[-1][1] = i + 1
        else:
            out.append([i, i + 1])
    return [(a, b) for a, b in out]


# ------------------------------------------------------------------ gold flow
def gold_tasks(records: list[dict], detect, engine: str, unaided_share: float = 0.2, seed: int = 0) -> list[dict]:
    """One task per note; engine spans as predictions except on a seeded unaided share."""
    rng = random.Random(seed)
    unaided = set(rng.sample(range(len(records)), round(len(records) * unaided_share)))
    tasks = []
    for i, r in enumerate(records):
        t = {"data": {"note_id": r["note_id"], "tier": r.get("tier", ""), "text": r["text"], "aided": i not in unaided}}
        if i not in unaided:
            t["predictions"] = [{"model_version": engine, "result": [
                _result(r["text"], s, _label(s["type"]), "phi", j) for j, s in enumerate(detect(r["text"]))]}]
        tasks.append(t)
    return tasks


def parse_gold_export(export: list[dict]) -> pd.DataFrame:
    """One row per marked span (note_id, annotator, aided, start, end, type, text). An annotation
    with no spans (the annotator found no PHI) is kept as one row with start = end = -1."""
    rows = []
    for task in export:
        d = task["data"]
        for ann in task.get("annotations", []):
            if ann.get("was_cancelled"):
                continue
            base = {"note_id": d["note_id"], "annotator": _who(ann), "aided": bool(d.get("aided", True))}
            spans = [r["value"] for r in ann.get("result", []) if r.get("type") == "labels" and r.get("from_name") == "phi"]
            rows += [{**base, "start": v["start"], "end": v["end"], "type": v["labels"][0], "text": v.get("text", "")}
                     for v in spans] or [{**base, "start": -1, "end": -1, "type": "", "text": ""}]
    return pd.DataFrame(rows, columns=["note_id", "annotator", "aided", "start", "end", "type", "text"])


def _marked(spans: pd.DataFrame) -> pd.DataFrame:
    return spans[spans["start"] >= 0]


def agreement(spans: pd.DataFrame) -> pd.DataFrame:
    """Pairwise entity F1 on the notes both annotated: exact (start, end), then also same category."""
    rows = []
    who = sorted(spans["annotator"].unique())
    for i, a in enumerate(who):
        for b in who[i + 1:]:
            notes = set(spans.loc[spans.annotator == a, "note_id"]) & set(spans.loc[spans.annotator == b, "note_id"])
            m = _marked(spans[spans["note_id"].isin(notes)])
            sa, sb = (m[m.annotator == x] for x in (a, b))
            key = lambda d, typed: set(zip(d.note_id, d.start, d.end, d.type if typed else [""] * len(d)))
            n = len(sa) + len(sb)
            rows.append({"annotator_a": a, "annotator_b": b, "n_notes": len(notes), "n_spans_a": len(sa),
                         "n_spans_b": len(sb),
                         "f1_span": 2 * len(key(sa, False) & key(sb, False)) / n if n else float("nan"),
                         "f1_typed": 2 * len(key(sa, True) & key(sb, True)) / n if n else float("nan")})
    return pd.DataFrame(rows)


def consensus(spans: pd.DataFrame) -> dict:
    """{note_id: [span]}: characters marked by at least half the note's annotators; each run takes
    the most common category among the spans covering it (ties: alphabetical)."""
    out = {}
    for nid, g in spans.groupby("note_id", sort=False):
        k = g["annotator"].nunique()
        m = _marked(g)
        votes = Counter(i for _, s in m.iterrows() for i in range(int(s.start), int(s.end)))
        keep = {i for i, v in votes.items() if v >= k / 2}
        gold = []
        for a, b in _runs(keep):
            cats = Counter(s.type for _, s in m.iterrows() if s.start < b and s.end > a)
            gold.append({"start": a, "end": b, "type": min(cats.items(), key=lambda kv: (-kv[1], kv[0]))[0]})
        out[nid] = gold
    return out


def gold_records(spans: pd.DataFrame, records: list[dict]) -> list[dict]:
    """The annotated notes with the consensus as their PHI, ready for deid_eval.score_records."""
    gold = consensus(spans)
    return [{**r, "phi": [{**s, "text": r["text"][s["start"]:s["end"]]} for s in gold[r["note_id"]]]}
            for r in records if r["note_id"] in gold]


def annotator_recall(spans: pd.DataFrame, records: list[dict]) -> pd.DataFrame:
    """Synthetic only: share of the generator's identifiers each annotator fully marked, aided vs unaided."""
    truth = {r["note_id"]: r["phi"] for r in records}
    rows = []
    for (who, aided), g in spans.groupby(["annotator", "aided"]):
        found = total = 0
        for nid, gn in g.groupby("note_id"):
            marked = _chars(_marked(gn).to_dict("records"))
            phi = truth.get(nid, [])
            total += len(phi)
            found += sum(set(range(p["start"], p["end"])) <= marked for p in phi)
        rows.append({"annotator": who, "aided": bool(aided), "n_notes": g["note_id"].nunique(), "n_phi": total,
                     "entity_recall": found / total if total else float("nan")})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ QA flow
def redact_map(text: str, spans: list[dict]) -> tuple[str, list[int]]:
    """deid.redact plus where each original character landed (-1 = redacted)."""
    out, pos, last, n = [], [-1] * len(text), 0, 0
    for s in sorted(spans, key=lambda s: s["start"]):
        if s["start"] < last:                       # overlapping spans: already redacted
            last = max(last, s["end"])
            continue
        for i in range(last, s["start"]):
            pos[i] = n + i - last
        n += s["start"] - last
        out += [text[last:s["start"]], f"[{s['type']}]"]
        n += len(s["type"]) + 2
        last = s["end"]
    for i in range(last, len(text)):
        pos[i] = n + i - last
    out.append(text[last:])
    return "".join(out), pos


def qa_tasks(records: list[dict], detect, engine: str, n: int = 100, seed: int = 0) -> tuple[list[dict], pd.DataFrame]:
    """De-identify each note with the engine; sample residual-scan hits first, then seeded random notes.
    Returns (tasks, key); the key (true leaks, in redacted coordinates) never goes into a task."""
    rows = []
    for r in records:
        found = detect(r["text"])
        red, pos = redact_map(r["text"], found)
        covered = _chars(found)
        leaks = []
        for p in r.get("phi", []):
            left = [pos[i] for i in range(p["start"], p["end"]) if i not in covered and pos[i] >= 0]
            if left:
                leaks.append({"start": min(left), "end": max(left) + 1, "type": p["type"]})
        rows.append({"rec": r, "text": red, "residual": residual_scan(red), "leaks": leaks})
    rng = random.Random(seed)
    flagged = [i for i, x in enumerate(rows) if x["residual"]]
    rest = [i for i, x in enumerate(rows) if not x["residual"]]
    pick = sorted(rng.sample(flagged, n)) if len(flagged) >= n else flagged + sorted(rng.sample(rest, min(n - len(flagged), len(rest))))
    tasks, key = [], []
    for i in pick:
        x, r = rows[i], rows[i]["rec"]
        t = {"data": {"note_id": r["note_id"], "tier": r.get("tier", ""), "engine": engine, "text": x["text"],
                      "residual_flag": bool(x["residual"])}}
        if x["residual"]:
            t["predictions"] = [{"model_version": "residual_scan", "result": [
                _result(x["text"], s, "LEAK", "leaks", j) for j, s in enumerate(x["residual"])]}]
        tasks.append(t)
        key.append({"note_id": r["note_id"], "tier": r.get("tier", ""), "residual_flag": bool(x["residual"]),
                    "n_true_leaks": len(x["leaks"]), "leak_spans": x["leaks"]})
    return tasks, pd.DataFrame(key)


def parse_qa_export(export: list[dict]) -> pd.DataFrame:
    rows = []
    for task in export:
        for ann in task.get("annotations", []):
            if ann.get("was_cancelled"):
                continue
            res = ann.get("result", [])
            choice = lambda name, res=res: next((";".join(r["value"]["choices"]) for r in res
                                                 if r.get("from_name") == name and r.get("type") == "choices"), None)
            rows.append({"note_id": task["data"]["note_id"], "reviewer": _who(ann), "leak": choice("leak"),
                         "over_redaction": choice("over_redaction"),
                         "n_leak_spans": len(marked := [(r["value"]["start"], r["value"]["end"]) for r in res
                                                        if r.get("type") == "labels" and r.get("from_name") == "leaks"]),
                         "leak_spans": marked})
    return pd.DataFrame(rows)


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float, float]:
    """Share k/n with its Wilson score interval."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return p, max(0.0, centre - half), min(1.0, centre + half)


def qa_summary(labels: pd.DataFrame, key: pd.DataFrame | None = None) -> pd.DataFrame:
    """Leak-note rate (Wilson CI) and over-redaction rate, pooled (any reviewer) and per reviewer;
    with the key, sensitivity (true-leak notes flagged), specificity (clean notes passed) and
    leak_span_recall (share of true leaks a reviewer highlighted; pooled = union of reviewers)."""
    lab = labels.assign(flag=labels["leak"].eq("yes"), over=labels["over_redaction"].eq("yes"))
    if "leak_spans" not in lab:
        lab["leak_spans"] = [[] for _ in range(len(lab))]
    pooled = (lab.groupby("note_id").agg(flag=("flag", "any"), over=("over", "any"),
                                         leak_spans=("leak_spans", lambda x: [s for ss in x for s in ss]))
              .reset_index().assign(reviewer="pooled"))
    truth = None if key is None else key.set_index("note_id")["n_true_leaks"].gt(0)
    rows = []
    for scope, g in [("pooled", pooled), *lab.groupby("reviewer")]:
        p, lo, hi = wilson(int(g["flag"].sum()), len(g))
        row = {"scope": scope, "n_notes": len(g), "leak_notes": int(g["flag"].sum()), "leak_rate": p,
               "leak_lo": lo, "leak_hi": hi, "over_redaction_rate": g["over"].mean(),
               "sensitivity": float("nan"), "specificity": float("nan"), "leak_span_recall": float("nan")}
        if truth is not None:
            t = truth.reindex(g["note_id"]).to_numpy()
            f = g["flag"].to_numpy()
            if t.any():
                row["sensitivity"] = f[t].mean()
            if (~t).any():
                row["specificity"] = (~f[~t]).mean()
            spans = key.set_index("note_id")["leak_spans"] if "leak_spans" in key else None
            if spans is not None:
                hit = tot = 0
                for nid, marked in zip(g["note_id"], g["leak_spans"]):
                    for leak in spans.get(nid, []):
                        tot += 1
                        hit += any(a < leak["end"] and b > leak["start"] for a, b in marked)
                row["leak_span_recall"] = hit / tot if tot else float("nan")
        rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ dry run
def simulate_gold_export(tasks: list[dict], records: list[dict], n_annotators: int = 3, seed: int = 11) -> list[dict]:
    """Simulated annotators: start from the truth, miss more where the pre-annotation missed (anchoring),
    sometimes keep an engine false positive, sometimes pick the wrong category. Dry runs only."""
    rng = random.Random(seed)
    truth = {r["note_id"]: r["phi"] for r in records}
    people = [{"email": f"annotator{i + 1}@example.org", "miss": rng.uniform(0.03, 0.08),
               "anchored_miss": rng.uniform(0.15, 0.35), "fp_keep": rng.uniform(0.1, 0.4),
               "wrong_type": rng.uniform(0.03, 0.1)} for i in range(n_annotators)]
    out = []
    for t in tasks:
        d, text = t["data"], t["data"]["text"]
        preds = [r["value"] for r in t.get("predictions", [{}])[0].get("result", [])] if t.get("predictions") else []
        anns = []
        for p in people:
            res = []
            for s in truth[d["note_id"]]:
                hit = any(v["start"] < s["end"] and v["end"] > s["start"] for v in preds)
                miss = p["miss"] if (hit or not d["aided"]) else p["anchored_miss"]
                if d["aided"] is False:
                    miss *= 1.5
                if rng.random() < miss:
                    continue
                lab = rng.choice(CATEGORIES) if rng.random() < p["wrong_type"] else s["type"]
                res.append({"start": s["start"], "end": s["end"], "labels": [lab]})
            for v in preds:
                if not any(v["start"] < s["end"] and v["end"] > s["start"] for s in truth[d["note_id"]]) \
                        and rng.random() < p["fp_keep"]:
                    res.append({"start": v["start"], "end": v["end"], "labels": v["labels"]})
            anns.append({"completed_by": {"email": p["email"]}, "result": [
                {"from_name": "phi", "to_name": "text", "type": "labels",
                 "value": {**v, "text": text[v["start"]:v["end"]]}} for v in res]})
        out.append({"data": d, "annotations": anns})
    return out


def simulate_qa_export(tasks: list[dict], key: pd.DataFrame, n_reviewers: int = 2, seed: int = 13) -> list[dict]:
    """Simulated QA reviewers with their own sensitivity and false-alarm rate. Dry runs only."""
    rng = random.Random(seed)
    k = key.set_index("note_id")
    people = [{"email": f"qa{i + 1}@example.org", "sens": rng.uniform(0.75, 0.95), "fa": rng.uniform(0.01, 0.05),
               "over": rng.uniform(0.02, 0.08)} for i in range(n_reviewers)]
    out = []
    for t in tasks:
        leaks = k.loc[t["data"]["note_id"], "leak_spans"]
        anns = []
        for p in people:
            seen = [s for s in leaks if rng.random() < p["sens"]]
            flag = bool(seen) or (not leaks and rng.random() < p["fa"])
            res = [{"from_name": "leak", "type": "choices", "value": {"choices": ["yes" if flag else "no"]}},
                   {"from_name": "over_redaction", "type": "choices",
                    "value": {"choices": ["yes" if rng.random() < p["over"] else "no"]}}]
            res += [{"from_name": "leaks", "to_name": "text", "type": "labels",
                     "value": {"start": s["start"], "end": s["end"], "text": t["data"]["text"][s["start"]:s["end"]],
                               "labels": ["LEAK"]}} for s in seen]
            anns.append({"completed_by": {"email": p["email"]}, "result": res})
        out.append({"data": t["data"], "annotations": anns})
    return out
