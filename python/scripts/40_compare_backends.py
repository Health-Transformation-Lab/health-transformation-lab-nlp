"""Compare two runs of one LLM rung on the notes both read: a KerasHub run against the committed
Hugging Face run, before trusting a full KerasHub run (the backends differ in weights format and dtype).

    python scripts/40_compare_backends.py --rung medgemma-1.5-4b-it                  # +keras vs hf files
    python scripts/40_compare_backends.py --new a.csv --base b.csv [--key review_key.csv]

Prints the summary and the notes where the two predictions differ. Synthetic review notes only.
"""

import argparse

import pandas as pd

from dental_omop_nlp import telemetry
from dental_omop_nlp.llm_reader import compare_backends
from dental_omop_nlp.paths import DATASETS_DIR
from dental_omop_nlp.rungs import output_tag

ap = argparse.ArgumentParser()
ap.add_argument("--rung", help="compare llm_details_<rung>+keras.csv with llm_details_<rung>.csv")
ap.add_argument("--shots", type=int, default=0)
ap.add_argument("--new", help="llm_details file of the run to check (default: the +keras run of --rung)")
ap.add_argument("--base", help="llm_details file to compare with (default: the hf run of --rung)")
ap.add_argument("--key", default=str(DATASETS_DIR / "answer_key" / "review_key.csv"))
a = ap.parse_args()
if not (a.rung or (a.new and a.base)):
    ap.error("give --rung, or --new and --base")
telemetry.setup()
telemetry.start_script("40_compare_backends", data_label="synthetic", rung=a.rung or "")

new = a.new or DATASETS_DIR / f"llm_details_{a.rung}{output_tag(shots=a.shots, backend='keras')}.csv"
base = a.base or DATASETS_DIR / f"llm_details_{a.rung}{output_tag(shots=a.shots)}.csv"
key = pd.read_csv(a.key)
per_note, s = compare_backends(pd.read_csv(new), pd.read_csv(base), dict(zip(key.visit_id, key.truth_status)))

n, b = s["new_backend"], s["base_backend"]
print(f"{n} vs {b} on {s['notes']} notes: same prediction {s['pred_agreement']:.0%}, "
      f"same status where both passed the gate {s['status_agreement']:.0%}")
print(f"  gate pass {n} {s['new_gate_pass']:.0%} / {b} {s['base_gate_pass']:.0%}; "
      f"accuracy {n} {s['new_accuracy']:.0%} / {b} {s['base_accuracy']:.0%}; "
      f"seconds per note {n} {s['new_latency_s']:.1f} / {b} {s['base_latency_s']:.1f}")
diff = per_note[~per_note.same_pred]
if len(diff):
    print("notes where they differ:")
    print(diff[["visit_id", "truth", "pred_new", "pred_base", "gate_ok_new", "gate_ok_base"]]
          .rename(columns=lambda c: c.replace("_new", f"_{n}").replace("_base", f"_{b}")).to_string(index=False))
