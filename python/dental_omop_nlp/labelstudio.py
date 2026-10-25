"""Label Studio export → tidy tables.

Reads the JSON export (Project → Export → JSON) and writes:
  reviewer_labels.csv  one row per (visit, reviewer): status, grade, extent,
                       decided_by, conflict, confidence, comment, lead_time
  evidence_spans.csv   one row per highlighted span in the note

Also: `simulate_export` writes a fake export from N simulated reviewers so the
import → reliability path can be dry-run before real reviewers start. Simulated
files are named simulated_* and must never be reported as results.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd

from .labels import Status

STATUS_CHOICES = [s.value for s in Status] + ["cannot_determine"]


def _choice(results: list[dict], name: str) -> str | None:
    for r in results:
        if r.get("from_name") == name and r.get("type") == "choices":
            return ";".join(r["value"]["choices"])
    return None


def parse_export(export: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    labels, spans = [], []
    for task in export:
        vid = task["data"]["visit_id"]
        for ann in task.get("annotations", []):
            if ann.get("was_cancelled"):
                continue
            res = ann.get("result", [])
            reviewer = ann.get("completed_by")
            reviewer = reviewer.get("email", reviewer.get("id")) if isinstance(reviewer, dict) else reviewer
            rating = next((r["value"]["rating"] for r in res if r.get("type") == "rating"), None)
            comment = next((" ".join(r["value"]["text"]) for r in res if r.get("type") == "textarea"), "")
            labels.append({"visit_id": vid, "reviewer": str(reviewer),
                           "status": _choice(res, "status"), "grade": _choice(res, "grade"),
                           "extent": _choice(res, "extent"), "decided_by": _choice(res, "decided_by"),
                           "conflict": _choice(res, "conflict"), "confidence": rating, "comment": comment,
                           "lead_time_s": ann.get("lead_time")})
            for r in res:
                if r.get("type") == "labels" and r.get("from_name") == "evidence":
                    v = r["value"]
                    spans.append({"visit_id": vid, "reviewer": str(reviewer), "label": v["labels"][0],
                                  "start": v["start"], "end": v["end"], "text": v.get("text", "")})
    return pd.DataFrame(labels), pd.DataFrame(spans)


def import_export(path: Path, out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    labels, spans = parse_export(json.loads(Path(path).read_text()))
    prefix = "simulated_" if "simulated" in Path(path).name else ""
    out_dir.mkdir(parents=True, exist_ok=True)
    labels.to_csv(out_dir / f"{prefix}reviewer_labels.csv", index=False)
    spans.to_csv(out_dir / f"{prefix}evidence_spans.csv", index=False)
    return labels, spans


# ------------------------------------------------------------------ dry run
def simulate_export(tasks: list[dict], key: pd.DataFrame, n_reviewers: int = 4,
                    seed: int = 7) -> list[dict]:
    """Each simulated reviewer reads the chart truth with their own error rate,
    sometimes defers to the clinician's written dx, sometimes says
    cannot_determine. Purely for testing the pipeline."""
    rng = random.Random(seed)
    truth = key.set_index("visit_id")
    order = [s.value for s in Status]
    reviewers = [{"id": i + 1, "email": f"reviewer{i + 1}@example.org",
                  "err": rng.uniform(0.08, 0.22), "defer": rng.uniform(0.05, 0.25)} for i in range(n_reviewers)]
    out = []
    for t in tasks:
        vid = t["data"]["visit_id"]
        row = truth.loc[vid]
        anns = []
        for rv in reviewers:
            s = row["stated_status"] if rng.random() < rv["defer"] else row["truth_status"]
            if rng.random() < rv["err"]:
                i = order.index(s)
                s = order[min(max(i + rng.choice([-1, 1]), 0), 5)]
            if rng.random() < 0.02:
                s = "cannot_determine"
            res = [{"from_name": "status", "to_name": "note", "type": "choices", "value": {"choices": [s]}},
                   {"from_name": "confidence", "to_name": "note", "type": "rating",
                    "value": {"rating": rng.randint(3, 5)}}]
            if s.startswith("periodontitis"):
                res.append({"from_name": "grade", "to_name": "note", "type": "choices",
                            "value": {"choices": [row["truth_grade"] if isinstance(row["truth_grade"], str) else "B"]}})
            anns.append({"completed_by": {"id": rv["id"], "email": rv["email"]}, "result": res,
                         "was_cancelled": False, "lead_time": round(rng.uniform(40, 240), 1)})
        out.append({"id": vid, "data": t["data"], "annotations": anns})
    return out
