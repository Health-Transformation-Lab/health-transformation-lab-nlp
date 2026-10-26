"""Score de-identification engines on the labeled challenge set, and price them (spec 007).

Scores, per tier (easy / hard / all):
  entity_recall       share of PHI identifiers fully removed (one surviving character = a leak)
  char_recall         share of PHI characters removed
  char_precision      share of removed characters that were PHI (low = over-redaction)
  decoy_damage        share of dental decoys (Glickman class II, #19, D4341 ...) with any character removed
  leaked_per_1k_notes leaked identifiers per 1,000 notes

Cost per corpus: the engine (local: node-hours at measured throughput; service: per MB or per
1,000-character record, after a free allowance) plus a human QA review of a fixed sample of
de-identified notes (same share for every engine).
`deid_frontier` sorts by cost: an engine is dominated if a cheaper one leaks no more; along the
frontier, ICER = extra USD per leaked identifier avoided. R twin: r/R/08_deid.R (parity-tested).
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd


def _chars(spans) -> set[int]:
    return {i for s in spans for i in range(s["start"], s["end"])}


def score_records(records: list[dict], detect) -> dict:
    rows, cat_rows = [], []
    for r in records:
        found = detect(r["text"])
        red = _chars(found)
        phi = _chars(r["phi"])
        leaked = [p for p in r["phi"] if not set(range(p["start"], p["end"])) <= red]
        damaged = [d for d in r["decoys"] if set(range(d["start"], d["end"])) & red]
        rows.append({"note_id": r["note_id"], "tier": r["tier"], "n_phi": len(r["phi"]), "n_leaked": len(leaked),
                     "phi_chars": len(phi), "phi_chars_removed": len(phi & red), "removed_chars": len(red),
                     "n_decoys": len(r["decoys"]), "n_decoys_damaged": len(damaged), "chars": len(r["text"])})
        for p in r["phi"]:
            cat_rows.append({"tier": r["tier"], "category": p["type"], "leaked": p in leaked})
    per = pd.DataFrame(rows)

    def summarize(d: pd.DataFrame, tier: str) -> dict:
        return {"tier": tier, "n_notes": len(d), "n_phi": int(d.n_phi.sum()),
                "entity_recall": 1 - d.n_leaked.sum() / max(d.n_phi.sum(), 1),
                "char_recall": d.phi_chars_removed.sum() / max(d.phi_chars.sum(), 1),
                "char_precision": d.phi_chars_removed.sum() / d.removed_chars.sum() if d.removed_chars.sum() else 1.0,
                "decoy_damage": d.n_decoys_damaged.sum() / max(d.n_decoys.sum(), 1),
                "n_hard_negatives": int((d.n_phi == 0).sum()),       # notes with no PHI at all
                "hard_negative_damage": ((d.n_phi == 0) & (d.removed_chars > 0)).sum() / max((d.n_phi == 0).sum(), 1),
                "leaked_per_1k_notes": 1000 * d.n_leaked.sum() / max(len(d), 1),
                "avg_chars": float(d.chars.mean()) if len(d) else 0.0}
    own = per[per.tier != "external"]          # "all" = the challenge set's own tiers; external reported apart
    summary = pd.DataFrame([summarize(per[per.tier == t], t) for t in sorted(per.tier.unique())]
                           + [summarize(own if len(own) else per, "all")])
    cats = pd.DataFrame(cat_rows)
    by_cat = (cats.groupby(["tier", "category"]).agg(n=("leaked", "size"), n_leaked=("leaked", "sum"))
              .reset_index().assign(recall=lambda x: 1 - x.n_leaked / x.n)) if len(cats) else cats
    return {"summary": summary, "by_category": by_cat, "per_note": per}


def measure_throughput(records: list[dict], detect, min_seconds: float = 0.5) -> float:
    """Notes per second on this machine (local engines)."""
    n, t0 = 0, time.perf_counter()
    while time.perf_counter() - t0 < min_seconds:
        for r in records:
            detect(r["text"])
        n += len(records)
    return n / (time.perf_counter() - t0)


def engine_cost(cfg: dict, n_notes: int, avg_chars: float, compute: dict) -> float:
    """USD to run one engine over n_notes."""
    if cfg["kind"] == "local":
        hours = n_notes / cfg["notes_per_sec"] / 3600
        return hours * compute.get(f"{cfg.get('hardware', 'cpu')}_node_usd_per_hour", 0.0)
    if cfg["kind"] == "service":
        if cfg["unit"] == "mb":
            units = n_notes * avg_chars / 1e6                       # ~1 byte per character (ASCII notes)
        elif cfg["unit"] == "record_1k_chars":
            units = n_notes * np.ceil(avg_chars / 1000)
        else:
            raise ValueError(f"unknown unit {cfg['unit']}")
        return max(units - cfg.get("free_units", 0), 0) * cfg["usd_per_unit"]
    if cfg["kind"] == "llm":                                      # ~4 characters per token
        tin = cfg["prompt_overhead_tokens"] + avg_chars / 4
        return n_notes * (tin * cfg["usd_per_1m_input_tokens"] + cfg["output_tokens"] * cfg["usd_per_1m_output_tokens"]) / 1e6
    raise ValueError(f"unknown kind {cfg['kind']}")


def review_cost(n_notes: int, review: dict) -> float:
    """Human QA of a sample of de-identified notes (same for every engine)."""
    return review["qa_sample_share"] * n_notes * review["minutes_per_note"] / 60 * review["usd_per_hour"]


def deid_frontier(t: pd.DataFrame) -> pd.DataFrame:
    """t: method, cost_usd, leaked_per_1m_notes [, decoy_damage]. Adds dominated,
    icer_usd_per_leak_avoided, usd_per_1k_leaks_avoided, compared_to. At equal cost and leaks the
    one that damages fewer dental terms comes first, so the other is dominated."""
    if "decoy_damage" not in t:
        t = t.assign(decoy_damage=0.0)
    t = t.sort_values(["cost_usd", "leaked_per_1m_notes", "decoy_damage", "method"]).reset_index(drop=True)
    t["dominated"] = False
    best = np.inf
    for i, r in t.iterrows():
        if r["leaked_per_1m_notes"] >= best:
            t.loc[i, "dominated"] = True
        else:
            best = r["leaked_per_1m_notes"]
    t["icer_usd_per_leak_avoided"] = np.nan
    t["compared_to"] = ""
    prev = None
    for i, r in t[~t["dominated"]].iterrows():
        if prev is not None:
            t.loc[i, "icer_usd_per_leak_avoided"] = (r["cost_usd"] - prev["cost_usd"]) / (
                prev["leaked_per_1m_notes"] - r["leaked_per_1m_notes"])
            t.loc[i, "compared_to"] = prev["method"]
        prev = r
    t["usd_per_1k_leaks_avoided"] = t["icer_usd_per_leak_avoided"] * 1000
    return t


_LLM_KEYS = ("usd_per_1m_input_tokens", "usd_per_1m_output_tokens", "prompt_overhead_tokens", "output_tokens")


def cost_table(ci: pd.DataFrame) -> pd.DataFrame:
    """cost_inputs.csv rows (one per method x member engine) -> one row per method with the frontier."""
    if "tier" in ci and ci["tier"].nunique() > 1:
        return pd.concat([cost_table(g).assign(tier=tier) for tier, g in ci.groupby("tier", sort=False)],
                         ignore_index=True)
    out = []
    for method, g in ci.groupby("method", sort=False):
        r0 = g.iloc[0]
        compute = {"cpu_node_usd_per_hour": r0.cpu_node_usd_per_hour, "gpu_node_usd_per_hour": r0.gpu_node_usd_per_hour}
        eng = sum(engine_cost({"kind": r.kind, "hardware": r.hardware or "cpu", "notes_per_sec": r.notes_per_sec,
                               "unit": r.unit, "usd_per_unit": r.usd_per_unit, "free_units": r.free_units,
                               **{k: getattr(r, k, 0.0) for k in _LLM_KEYS}},
                              int(r.n_notes), float(r.avg_chars), compute) for r in g.itertuples())
        rev = review_cost(int(r0.n_notes), {"qa_sample_share": r0.qa_sample_share,
                                            "minutes_per_note": r0.minutes_per_note, "usd_per_hour": r0.review_usd_per_hour})
        out.append({"method": method, "engine_usd": eng, "review_usd": rev, "cost_usd": eng + rev,
                    "leaked_per_1m_notes": r0.leaked_per_1m_notes, "decoy_damage": r0.get("decoy_damage", 0.0),
                    "prices": "ILLUSTRATIVE" if (g.kind == "service").any() else "measured throughput"})
    res = deid_frontier(pd.DataFrame(out))
    return res.assign(tier=ci["tier"].iloc[0]) if "tier" in ci else res
