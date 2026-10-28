"""Databricks' ai_classify as a phenotyping method (spec 017 US2).

ai_classify (Databricks SQL AI Function, GA June 2026) gives each note one of the six statuses. Each label
carries a one-line description from the same AAP/EFP criteria the LLM reader and judge use. It runs through
the SQL Statement Execution API on a serverless SQL warehouse; note text is always a named parameter, never
pasted into the SQL. The model behind ai_classify is Databricks-managed and not named in its documentation.

A note it can't classify (NULL, an error, a label outside the six) is *no answer*, never a guess. A failed
batch is retried once; after that its notes are no answer, with the error kept.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request

import pandas as pd

from .labels import LABELS
from .telemetry import traced

SETTINGS = ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "DATABRICKS_WAREHOUSE_ID")
CHARS_PER_TOKEN = 4

# One line per status, from judge.CRITERIA (2017 AAP/EFP worksheet).
DESCRIPTIONS = {
    "healthy": "No interdental attachment loss and bleeding on probing below 10% of sites.",
    "gingivitis": "No interdental attachment loss, bleeding on probing at 10% of sites or more.",
    "periodontitis_stage_1": "Periodontitis stage I: interdental CAL 1-2 mm (bone loss under 15%), no teeth lost "
                             "to periodontitis, probing depths 4 mm or less.",
    "periodontitis_stage_2": "Periodontitis stage II: CAL 3-4 mm (bone loss 15-33%), no teeth lost to "
                             "periodontitis, probing depths 5 mm or less.",
    "periodontitis_stage_3": "Periodontitis stage III: CAL 5 mm or more (bone loss past the coronal third), or 1-4 "
                             "teeth lost to periodontitis, or probing depth 6 mm or more, vertical defects or "
                             "class II/III furcation.",
    "periodontitis_stage_4": "Periodontitis stage IV: stage III severity plus 5 or more teeth lost to periodontitis "
                             "or a need for complex rehabilitation (bite collapse, drifting, fewer than 20 teeth).",
}


@traced
def classify_labels() -> str:
    """The labels argument: a JSON object of label -> description."""
    return json.dumps({lab: DESCRIPTIONS[lab] for lab in LABELS})


@traced
def classify_statement(notes: pd.DataFrame) -> tuple[str, list[dict]]:
    """One statement for a batch of notes. The labels are this module's own constant (a SQL string literal,
    as ai_classify requires); every note and visit id is a named parameter."""
    labels = classify_labels().replace("'", "''")
    rows, params = [], []
    for k, r in enumerate(notes.itertuples()):
        rows.append(f"(:i{k}, :t{k})")
        params += [{"name": f"i{k}", "value": str(r.visit_id), "type": "STRING"},
                   {"name": f"t{k}", "value": str(r.note_text), "type": "STRING"}]
    sql = (f"SELECT id, CAST(ai_classify(t, '{labels}') AS STRING) AS r "
           f"FROM VALUES {', '.join(rows)} AS v(id, t)")
    return sql, params


@traced
def parse_classify(value) -> tuple[str | None, str]:
    """(status or None, error). Handles the v2 VARIANT (as JSON text or parsed), the v1 STRING and NULL."""
    if value is None:
        return None, "no answer"
    d = value
    if isinstance(value, str) and value.lstrip().startswith("{"):
        try:
            d = json.loads(value)
        except json.JSONDecodeError:
            return None, "unreadable response"
    if isinstance(d, dict):
        resp, err = d.get("response"), d.get("error_message") or ""
        label = resp[0] if isinstance(resp, list) and resp else resp
        if not label:
            return None, err or "no answer"
    else:
        label = str(d).strip()
    return (label, "") if label in LABELS else (None, f"label outside the six: {str(label)[:40]}")


@traced
def check_settings() -> dict:
    missing = [v for v in SETTINGS if not os.environ.get(v, "").strip()]
    if missing:
        raise RuntimeError(f"set {', '.join(missing)} (a serverless SQL warehouse: ai_classify v2 isn't on Pro or "
                           "Classic warehouses)")
    host = os.environ["DATABRICKS_HOST"].strip().rstrip("/")
    return {"host": host if host.startswith("http") else f"https://{host}",
            "token": os.environ["DATABRICKS_TOKEN"].strip(), "warehouse": os.environ["DATABRICKS_WAREHOUSE_ID"].strip()}


@traced
def wait_for(out: dict, get, timeout_s: int = 600, sleep=time.sleep) -> list[list]:
    """Rows of a statement, checking again every 5 s while it's PENDING or RUNNING (a statement can outlast
    the 50 s the first call waits). Raises with Databricks' message if it fails or times out."""
    t0 = time.time()
    while out["status"]["state"] in ("PENDING", "RUNNING") and time.time() - t0 < timeout_s:
        sleep(5)
        out = get(out["statement_id"])
    if out["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(f"statement {out['status']['state']}: {out['status'].get('error', {}).get('message', '')[:300]}")
    return out.get("result", {}).get("data_array") or []


@traced
def sql_execute(sql: str, params: list[dict], timeout_s: int = 600) -> list[list]:  # pragma: no cover - network
    """Run one statement on the warehouse and return its rows."""
    s = check_settings()

    def call(method, path, body=None):
        req = urllib.request.Request(s["host"] + path, method=method,
                                     data=json.dumps(body).encode() if body else None,
                                     headers={"Authorization": f"Bearer {s['token']}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read())

    out = call("POST", "/api/2.0/sql/statements", {"warehouse_id": s["warehouse"], "statement": sql,
                                                   "parameters": params, "wait_timeout": "50s"})
    return wait_for(out, lambda sid: call("GET", f"/api/2.0/sql/statements/{sid}"), timeout_s)


@traced
def run_classify(notes: pd.DataFrame, execute=None, batch_size: int = 10) -> pd.DataFrame:
    """visit_id, pred (None = no answer), error: one row per note, in the notes' order."""
    execute = execute or sql_execute
    got: dict[str, tuple] = {}
    for start in range(0, len(notes), batch_size):
        batch = notes.iloc[start:start + batch_size]
        sql, params = classify_statement(batch)
        err = ""
        for _attempt in range(2):                       # one retry, then no answer for the batch
            try:
                for vid, value in execute(sql, params):
                    got[str(vid)] = parse_classify(value)
                err = ""
                break
            except Exception as e:  # noqa: BLE001 - warehouse, network, quota: recorded per note
                err = f"{type(e).__name__}: {str(e)[:200]}"
        for vid in batch.visit_id.astype(str):
            got.setdefault(vid, (None, err or "no answer"))
    return pd.DataFrame({"visit_id": notes.visit_id.to_numpy(),
                         "pred": [got[str(v)][0] for v in notes.visit_id],
                         "error": [got[str(v)][1] for v in notes.visit_id]})


@traced
def estimate(notes: pd.DataFrame, batch_size: int = 10) -> dict:
    """Calls and input tokens, printed before a run (ai_classify bills through the warehouse; Databricks
    publishes no per-call price, see the Databricks SQL pricing page)."""
    per_note = len(classify_labels()) // CHARS_PER_TOKEN
    return {"notes": len(notes), "statements": -(-len(notes) // batch_size),
            "input_tokens": int(sum(len(t) // CHARS_PER_TOKEN + per_note for t in notes.note_text))}
