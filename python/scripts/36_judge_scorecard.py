"""Judge-backed scorecard (spec 012): every README phenotyping metric against the truth and the judge.

    python scripts/36_judge_scorecard.py --simulated            # dry run, no endpoint: simulated_*.csv
    python scripts/36_judge_scorecard.py --endpoint databricks-meta-llama-3-3-70b-instruct \\
        --usd-in 0.50 --usd-out 1.50                               # real judge (DATABRICKS_HOST/TOKEN)

Writes data/datasets/judge/{simulated_,}{chart_answers,judgments,judge_metrics,judge_agreement}.csv.
A real run prints the token cost first and stops if it's over --max-usd; it resumes from an
existing judgments.csv, asking only rows not yet judged (and those that failed on the endpoint).
Prices are the endpoint's per-1M-token list prices: check them before running.
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

from dental_omop_nlp import judge as jg
from dental_omop_nlp import judge_scorecard as js
from dental_omop_nlp import readme_results as rr
from dental_omop_nlp.paths import JUDGE_DIR

ap = argparse.ArgumentParser()
mode = ap.add_mutually_exclusive_group(required=True)
mode.add_argument("--simulated", action="store_true", help="simulated judge: a dry run, never a result")
mode.add_argument("--endpoint", help="Databricks serving endpoint name")
ap.add_argument("--usd-in", type=float, help="US$ per 1M input tokens (required with --endpoint)")
ap.add_argument("--usd-out", type=float, help="US$ per 1M output tokens (required with --endpoint)")
ap.add_argument("--max-usd", type=float, default=5.0, help="stop before calling if the estimate is higher")
ap.add_argument("--n-boot", type=int, default=1000)
ap.add_argument("--out", type=Path, default=JUDGE_DIR)
a = ap.parse_args()

inp = rr.load_inputs()
answers = js.chart_answers(inp)
queue = js.judge_queue(answers, inp["key"])
prefix = "simulated_" if a.simulated else ""
a.out.mkdir(parents=True, exist_ok=True)
path = {n: a.out / f"{prefix}{n}.csv" for n in ("chart_answers", "judgments", "judge_metrics", "judge_agreement")}

if a.simulated:
    judge, endpoint, done = jg.SimulatedJudge(inp["key"]["truth_status"].to_dict(), seed=11), "sim:judge", None
    print("*** SIMULATED judge: pipeline dry run, not a result ***")
else:
    if a.usd_in is None or a.usd_out is None:
        sys.exit("--usd-in and --usd-out are required: check the endpoint's current price list")
    done = pd.read_csv(path["judgments"]) if path["judgments"].exists() else None
    judged = set() if done is None else {js._key(d) for d in done[~done["api_error"]].itertuples()}
    todo = queue[[js._key(r) not in judged for r in queue.itertuples()]]
    est = js.estimate_cost(todo, a.usd_in, a.usd_out)
    print(f"{est['calls']} calls to judge, ~{est['input_tokens']:,.0f} input tokens, ~US${est['usd']:.2f}")
    if est["usd"] > a.max_usd:
        sys.exit(f"estimate over --max-usd {a.max_usd}; not calling")
    host = os.environ["DATABRICKS_HOST"].rstrip("/")
    judge = jg.OpenAIJudge(model=a.endpoint, base_url=f"{host}/serving-endpoints",
                           api_key=os.environ["DATABRICKS_TOKEN"])
    endpoint = a.endpoint

judgments = js.run_judge(queue, judge, endpoint=endpoint, done=done)
metrics = js.judge_metrics(inp, answers, judgments, n_boot=a.n_boot)
agreement = js.judge_agreement(inp, judgments, n_boot=a.n_boot)
answers.to_csv(path["chart_answers"], index=False)
judgments.to_csv(path["judgments"], index=False)
metrics.to_csv(path["judge_metrics"], index=False)
agreement.to_csv(path["judge_agreement"], index=False)

label = "SIMULATED judge" if a.simulated else f"LLM judgment ({endpoint})"
print(f"{label}: {len(judgments)} calls, {int(judgments['api_error'].sum())} endpoint errors, "
      f"{int((~judgments['gate_ok']).sum())} failed the quote gate")
print(agreement[agreement.group == "all"].round(3).to_string(index=False))
ex = metrics[metrics.metric == "correct"].sort_values("vs_truth", ascending=False)
print(ex[["system", "vs_truth", "vs_judge", "difference", "corrected_accuracy"]].head(10).round(3).to_string(index=False))
