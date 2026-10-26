"""Compare de-identification engines on the labeled fake-PHI challenge set, and price them (spec 007).

    python scripts/26_deid_benchmark.py                       # every engine that can run here
    python scripts/26_deid_benchmark.py --engines regex,regex_v2+guard,presidio+regex_v2+guard
    AZURE_DEID_ENDPOINT=... python scripts/26_deid_benchmark.py --engines azure_deid+regex_v2+guard

Writes:
  data/raw/deid_challenge.jsonl       the labeled notes (fake PHI; never committed)
  data/deid/scores.csv                per engine and tier: recall, precision, decoy damage, leaks
  data/deid/by_category.csv           recall per PHI category
  data/deid/not_run.csv               engines that couldn't run here, and why
  data/deid/cost_inputs.csv           what the cost model uses (R recomputes from this: parity)
  data/deid/cost_effectiveness.csv    cost per corpus, leaks per 1M notes, frontier, ICER

  --external path.jsonl adds another labeled set (e.g. ASQ-PHI) as tier "external"; price it with
  --tiers all,unseen,external.

An engine that can't run here (package missing, no Azure endpoint) is listed as not run, with
the reason; nothing is estimated for it. Service prices in costs.yaml are ILLUSTRATIVE until
filled from the vendor's pricing page.
"""

import argparse
import json
import logging

import pandas as pd
import yaml

from dental_omop_nlp import deid, deid_eval
from dental_omop_nlp.paths import COSTS_YAML, DEID_DIR, RAW_DIR
from dental_omop_nlp.phi_challenge import build_challenge

logging.getLogger("tldextract").setLevel(logging.CRITICAL)   # Presidio's URL recognizer tries the network

DEFAULT = ["regex", "regex+guard", "regex_v2", "regex_v2+guard", "presidio", "presidio+guard",
           "presidio+regex_v2+guard", "azure_deid", "azure_deid+regex_v2+guard", "azure_language",
           "azure_language+regex_v2+guard"]
ap = argparse.ArgumentParser()
ap.add_argument("--engines", default=",".join(DEFAULT))
ap.add_argument("--n-notes", type=int, default=400)
ap.add_argument("--seed", type=int, default=7)
ap.add_argument("--external", default=None,
                help="another labeled PHI set (JSONL/JSON, e.g. ASQ-PHI) scored as tier 'external'")
ap.add_argument("--tiers", default="all,unseen",
                help="tiers priced: all (the mix) and unseen (held out from regex_v2's design)")
a = ap.parse_args()

ch = build_challenge(a.n_notes, a.seed)
if a.external:
    from dental_omop_nlp.phi_challenge import load_external
    ch += load_external(a.external)
RAW_DIR.mkdir(parents=True, exist_ok=True)
DEID_DIR.mkdir(parents=True, exist_ok=True)
with open(RAW_DIR / "deid_challenge.jsonl", "w") as f:
    f.writelines(json.dumps(r) + "\n" for r in ch)

cfg = yaml.safe_load(COSTS_YAML.read_text())
dcfg, compute, n_corpus = cfg["deid"], cfg["compute"], cfg["corpus_notes"]

scores, cats, not_run, speed = [], [], [], {}
for spec in a.engines.split(","):
    detect = deid.get_engine(spec)
    try:
        detect(ch[0]["text"])
    except Exception as e:  # noqa: BLE001 - missing package, model or endpoint: record and skip
        not_run.append({"method": spec, "reason": f"{type(e).__name__}: {str(e)[:160]}"})
        print(f"{spec}: not run ({type(e).__name__})")
        continue
    for member in [p for p in spec.split("+") if p != "guard"]:
        if member not in speed and member not in deid.CLOUD_ENGINES:
            speed[member] = deid_eval.measure_throughput(ch[:100], deid.get_engine(member))
    r = deid_eval.score_records(ch, detect)
    scores.append(r["summary"].assign(method=spec))
    cats.append(r["by_category"].assign(method=spec))
    s = r["summary"].set_index("tier").loc["all"]
    print(f"{spec}: entity recall {s.entity_recall:.3f}, decoy damage {s.decoy_damage:.3f}")

scores = pd.concat(scores)[["method", "tier", "n_notes", "n_phi", "entity_recall", "char_recall",
                            "char_precision", "decoy_damage", "leaked_per_1k_notes", "avg_chars"]]
scores.to_csv(DEID_DIR / "scores.csv", index=False)
pd.concat(cats)[["method", "tier", "category", "n", "n_leaked", "recall"]].to_csv(DEID_DIR / "by_category.csv",
                                                                               index=False)
pd.DataFrame(not_run, columns=["method", "reason"]).to_csv(DEID_DIR / "not_run.csv", index=False)

# ---- cost inputs: one row per (method, member engine); R recomputes the frontier from this file
rows = []
for (tier, spec), g in scores[scores.tier.isin(a.tiers.split(","))].groupby(["tier", "method"], sort=False):
    s = g.iloc[0]
    for member in [p for p in spec.split("+") if p != "guard"]:
        e = dict(dcfg["engines"][member])
        if e["kind"] == "local":
            e["notes_per_sec"] = speed[member]
        rows.append({"tier": tier, "method": spec, "engine": member, "kind": e["kind"], "hardware": e.get("hardware", ""),
                     "notes_per_sec": e.get("notes_per_sec", float("nan")), "unit": e.get("unit", ""),
                     "usd_per_unit": e.get("usd_per_unit", float("nan")), "free_units": e.get("free_units", 0),
                     "n_notes": n_corpus, "avg_chars": s.avg_chars,
                     "leaked_per_1m_notes": s.leaked_per_1k_notes * 1000, "decoy_damage": s.decoy_damage,
                     "cpu_node_usd_per_hour": compute["cpu_node_usd_per_hour"],
                     "gpu_node_usd_per_hour": compute["gpu_node_usd_per_hour"],
                     "qa_sample_share": dcfg["review"]["qa_sample_share"],
                     "minutes_per_note": dcfg["review"]["minutes_per_note"],
                     "review_usd_per_hour": dcfg["review"]["usd_per_hour"]})
ci = pd.DataFrame(rows)
ci.to_csv(DEID_DIR / "cost_inputs.csv", index=False)
ce = deid_eval.cost_table(ci)
ce.to_csv(DEID_DIR / "cost_effectiveness.csv", index=False)
print(ce.round(4).to_string(index=False))
print("wrote", DEID_DIR, "(service prices ILLUSTRATIVE; local throughput measured on this machine)")
