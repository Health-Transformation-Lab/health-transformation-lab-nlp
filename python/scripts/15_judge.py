"""LLM judge: calibrate on the human-reviewed charts, then judge a sample of each
method's predictions on the corpus.

    # real judge (any OpenAI-compatible endpoint, e.g. Databricks Model Serving)
    export JUDGE_BASE_URL=https://<workspace>/serving-endpoints JUDGE_API_KEY=... JUDGE_MODEL=<endpoint>
    python scripts/15_judge.py --backend openai

    # dry run, no LLM (verdicts simulated from the generator truth; output marked simulated)
    python scripts/15_judge.py --backend simulated --simulated-review

Only de-identified notes are sent. Writes data/corpus/judgments_gold.csv and
judgments_corpus.csv (prefixed simulated_ for the simulated backend).
"""

import argparse
import glob
from pathlib import Path

import pandas as pd
import yaml

from dental_omop_nlp.judge import PROMPT_VERSION, OpenAIJudge, SimulatedJudge
from dental_omop_nlp.paths import CORPUS_DIR, COSTS_YAML, DATASETS_DIR, REVIEW_DIR

ap = argparse.ArgumentParser()
ap.add_argument("--backend", choices=["openai", "simulated"], required=True)
ap.add_argument("--simulated-review", action="store_true",
                help="calibrate against simulated reviewer consensus (dry run)")
ap.add_argument("--per-method", type=int, default=None, help="corpus notes judged per method")
ap.add_argument("--seed", type=int, default=5)
a = ap.parse_args()

cfg = yaml.safe_load(COSTS_YAML.read_text())["judge"]
n_per = a.per_method or cfg["sample_per_method"]
sim = a.backend == "simulated"
prefix = "simulated_" if (sim or a.simulated_review) else ""

# ---- calibration set: each method's prediction on each reviewed chart vs reviewer consensus
rel_dir = REVIEW_DIR / ("simulated_reliability" if a.simulated_review else "reliability")
consensus = pd.read_csv(rel_dir / "consensus.csv").set_index("visit_id")["consensus"]
key = pd.read_csv(DATASETS_DIR / "answer_key" / "review_key.csv").set_index("visit_id")
gold_rows = []
for f in sorted(glob.glob(str(DATASETS_DIR / "ai_predictions_*.csv"))):
    m = Path(f).stem.removeprefix("ai_predictions_")
    p = pd.read_csv(f).set_index("visit_id")["pred"]
    for vid, pred in p.items():
        c = consensus.get(vid)
        if c in (None, "no_consensus") or pd.isna(c):
            continue
        gold_rows.append({"method": m, "visit_id": vid, "pred": pred, "truth": c, "note": key.loc[vid, "note_text"]})
# Calibration needs plenty of WRONG predictions to pin down specificity; good models
# rarely give them. The single-source readers (exam form, codes) are wrong often,
# so their readings on the same charts are added as calibration-only pairs.
for m in ["exam_form", "proc_codes_completed", "proc_dx_completed"]:
    for vid, pred in key[m].items():
        c = consensus.get(vid)
        if pred == "unknown" or c in (None, "no_consensus") or pd.isna(c):
            continue
        gold_rows.append({"method": f"calib:{m}", "visit_id": vid, "pred": pred, "truth": c,
                          "note": key.loc[vid, "note_text"]})
gold = pd.DataFrame(gold_rows)

# ---- corpus sample: n per method, stratified by predicted class
corpus = pd.read_parquet(CORPUS_DIR / "corpus_sample.parquet").set_index("visit_id")
corp_rows = []
for f in sorted(glob.glob(str(CORPUS_DIR / "preds_*.parquet"))):
    m = Path(f).stem.removeprefix("preds_").replace("__", ":")
    p = pd.read_parquet(f)
    frac = min(1.0, n_per / len(p))
    s = p.groupby("pred").sample(frac=frac, random_state=a.seed)   # stratified by predicted class
    for r in s.itertuples():
        corp_rows.append({"method": m, "visit_id": r.visit_id, "pred": r.pred,
                          "truth": corpus.loc[r.visit_id, "truth_status"], "note": corpus.loc[r.visit_id, "note_text"]})
corp = pd.DataFrame(corp_rows)


def run(df: pd.DataFrame, judge_truth_col: str) -> pd.DataFrame:
    if sim:
        judge = SimulatedJudge({i: t for i, t in enumerate(df[judge_truth_col])})
        verdicts = [judge(n, p, visit_id=i) for i, (n, p) in enumerate(zip(df["note"], df["pred"]))]
        model_name = "simulated"
    else:
        judge = OpenAIJudge()
        verdicts = [judge(n, p) for n, p in zip(df["note"], df["pred"])]
        model_name = judge.model
    out = df.drop(columns=["note"]).copy()
    out["verdict"] = [v.verdict for v in verdicts]
    out["supported_status"] = [v.supported_status for v in verdicts]
    out["quote"] = [v.quote for v in verdicts]
    out["gate_ok"] = [v.quote_ok for v in verdicts]
    out["error"] = [v.error for v in verdicts]
    out["input_tokens"] = [v.input_tokens for v in verdicts]
    out["output_tokens"] = [v.output_tokens for v in verdicts]
    out["prompt_version"], out["judge_model"] = PROMPT_VERSION, model_name
    return out


CORPUS_DIR.mkdir(parents=True, exist_ok=True)
g = run(gold, "truth")
g["truly_correct"] = g["pred"] == g["truth"]
g.to_csv(CORPUS_DIR / f"{prefix}judgments_gold.csv", index=False)
c = run(corp, "truth").drop(columns=["truth"])   # corpus truth is never stored with judgments
c.to_csv(CORPUS_DIR / f"{prefix}judgments_corpus.csv", index=False)
if prefix:
    print("*** SIMULATED: dry run, not a result ***")
print(f"calibration: {len(g)} judged pairs over {g['method'].nunique()} methods on reviewed charts")
print(f"corpus: {len(c)} judged predictions over {c['method'].nunique()} methods")
print(f"gate failures: gold {(~g['gate_ok']).mean():.1%}, corpus {(~c['gate_ok']).mean():.1%}")
