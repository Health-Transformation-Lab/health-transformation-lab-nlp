"""De-identification test pass on MACCROBAT, real published case reports with hand-made labels (spec 009).

    python scripts/32_maccrobat_deid.py --download          # fetch the original release (figshare) into data/raw/
    python scripts/32_maccrobat_deid.py --source bio --download   # or the BIO mirror on Hugging Face
    python scripts/32_maccrobat_deid.py --engines regex,regex_v2+guard,hf_stanford+regex_v2+guard

The original brat files are the default: exact text and offsets, and overlapping entities that BIO
labels can't hold (about twice as many clinical entities as the BIO mirror).

Scores, per engine (deid_eval.score_records on the records from maccrobat.load_brat / load_bio):
  entity_recall   share of derived PHI (dates with a month or day, ages >= 90) fully removed
  decoy_damage    share of clinical entities (symptoms, drugs, procedures ...) with any character removed
  char_precision  share of removed characters that were derived PHI

Writes (aggregates only; the text stays in data/raw/, never committed):
  data/deid/maccrobat_scores.csv    one row per engine
  data/deid/maccrobat_by_type.csv   per engine, role and entity type: share touched, share of characters removed
  data/deid/maccrobat_not_run.csv   engines that couldn't run here, and why
"""

import argparse
import functools
import urllib.request
from pathlib import Path

import pandas as pd

from dental_omop_nlp import deid, deid_eval, maccrobat
from dental_omop_nlp.paths import DEID_DIR, RAW_DIR

DEFAULT = ["regex", "regex+guard", "regex_v2", "regex_v2+guard", "presidio", "presidio+guard",
           "presidio+regex_v2+guard", "hf_stanford", "hf_stanford+guard", "hf_stanford+regex_v2+guard",
           "hf_obi", "hf_obi+regex_v2+guard", "hf_stanford+presidio+regex_v2+guard"]
ap = argparse.ArgumentParser()
ap.add_argument("--source", choices=["brat", "bio"], default="brat")
ap.add_argument("--path", default=None, help="the zip or folder (brat), or the JSONL (bio)")
ap.add_argument("--download", action="store_true", help=f"fetch {maccrobat.FIGSHARE_URL} or {maccrobat.HF_URL}")
ap.add_argument("--engines", default=",".join(DEFAULT))
a = ap.parse_args()

default = RAW_DIR / "maccrobat" / ("MACCROBAT2020.zip" if a.source == "brat" else "maccrobat_bio.jsonl")
a.path = a.path or str(default)
if a.download:
    Path(a.path).parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(maccrobat.FIGSHARE_URL if a.source == "brat" else maccrobat.HF_URL, a.path)
recs = (maccrobat.load_brat if a.source == "brat" else maccrobat.load_bio)(a.path)
n_ent = pd.Series([e["role"] for r in recs for e in r["entities"]]).value_counts()
print(f"{len(recs)} documents; entities by role: {n_ent.to_dict()}")

scores, by_type, not_run = [], [], []
for spec in a.engines.split(","):
    try:
        detect = deid.get_engine(spec)
        detect(recs[0]["text"])
    except Exception as e:  # noqa: BLE001 - missing package or model: record and skip
        not_run.append({"method": spec, "reason": f"{type(e).__name__}: {str(e)[:160]}"})
        print(f"{spec}: not run ({type(e).__name__})")
        continue
    detect_once = functools.lru_cache(maxsize=None)(lambda t, d=detect: tuple(d(t)))  # both scorers reuse the spans
    s = deid_eval.score_records(recs, detect_once)["summary"].set_index("tier").loc["maccrobat"]
    scores.append({"method": spec, **s.to_dict()})
    by_type.append(deid_eval.damage_by_type(recs, detect_once).assign(method=spec))
    print(f"{spec}: PHI recall {s.entity_recall:.3f} (n={int(s.n_phi)}), clinical damage {s.decoy_damage:.3f}")

if not scores:
    raise SystemExit("no engine ran: see the reasons above")
DEID_DIR.mkdir(parents=True, exist_ok=True)
cols = ["method", "n_notes", "n_phi", "entity_recall", "char_recall", "char_precision", "decoy_damage",
        "leaked_per_1k_notes", "avg_chars"]
pd.DataFrame(scores)[cols].round(4).to_csv(DEID_DIR / "maccrobat_scores.csv", index=False)
pd.concat(by_type)[["method", "role", "type", "n", "n_touched", "touched", "chars_removed"]].round(4).to_csv(
    DEID_DIR / "maccrobat_by_type.csv", index=False)
pd.DataFrame(not_run, columns=["method", "reason"]).to_csv(DEID_DIR / "maccrobat_not_run.csv", index=False)
print("wrote", DEID_DIR)
