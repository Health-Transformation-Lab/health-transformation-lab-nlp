"""Cost-effectiveness of each method at full-corpus scale.

    1. Calibrate the judge on the human-reviewed charts: for each method's
       prediction on a reviewed chart we know whether it was truly correct
       (matches reviewer consensus). The judge's verdicts on the same pairs
       give its sensitivity (says correct | is correct) and specificity
       (says incorrect | is incorrect).
    2. Judge a sample of each method's predictions on the corpus. The raw
       share judged correct is biased by the judge's errors; correct it with
       the Rogan-Gladen estimator:
           accuracy = (p_judged + specificity - 1) / (sensitivity + specificity - 1)
       Bootstrap the calibration set and the sample together for a 95% CI, so
       the judge's own uncertainty is in the interval.
    3. Cost of running each method over the whole corpus (costs.yaml), plus
       cost per 1,000 correctly classified notes.
    4. Incremental cost-effectiveness: sort by cost, drop dominated methods
       (one that costs more and isn't more accurate), and for each remaining
       step report dollars per additional correctly classified note (ICER).

r/R/05_cost_effectiveness.R computes the same table; the parity test checks.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .telemetry import traced

CORRECT, INCORRECT, ND = "correct", "incorrect", "not_determinable"


# ------------------------------------------------------------------ costs
@traced
def method_cost(cfg: dict, n_notes: int, avg_note_tokens: float, compute: dict,
                measured_tput: float | None = None) -> dict:
    """Cost to run one method over n_notes. Returns cost and the inputs used."""
    if cfg["kind"] == "llm":
        tok_in = n_notes * (avg_note_tokens + cfg["prompt_overhead_tokens"])
        tok_out = n_notes * cfg["output_tokens"]
        usd = tok_in / 1e6 * cfg["usd_per_1m_input_tokens"] + tok_out / 1e6 * cfg["usd_per_1m_output_tokens"]
        return {"cost_usd": usd, "node_hours": None, "notes_per_sec": None, "throughput_source": "tokens"}
    tput = measured_tput if cfg.get("throughput_source") == "measured" else cfg.get("notes_per_sec")
    if not tput:
        raise ValueError("no throughput: run scripts/14_benchmark_cost.py or set notes_per_sec")
    rate = compute["gpu_node_usd_per_hour" if cfg["hardware"] == "gpu" else "cpu_node_usd_per_hour"]
    hours = n_notes / tput / 3600 + cfg.get("train_hours", 0.0)
    return {"cost_usd": hours * rate, "node_hours": hours, "notes_per_sec": tput,
            "throughput_source": cfg.get("throughput_source", "assumed")}


@traced
def judge_cost(n_judged: int, avg_note_tokens: float, judge_cfg: dict) -> float:
    tok_in = n_judged * (avg_note_tokens + judge_cfg["prompt_overhead_tokens"])
    tok_out = n_judged * judge_cfg["output_tokens"]
    return tok_in / 1e6 * judge_cfg["usd_per_1m_input_tokens"] + tok_out / 1e6 * judge_cfg["usd_per_1m_output_tokens"]


# ------------------------------------------------------------------ judge calibration
@traced
def calibrate_judge(gold: pd.DataFrame) -> dict:
    """gold: rows with columns truly_correct (bool) and verdict. Not-determinable excluded."""
    g = gold[gold["verdict"].isin([CORRECT, INCORRECT]) & gold["gate_ok"]]
    pos, neg = g[g["truly_correct"]], g[~g["truly_correct"]]
    sens = float((pos["verdict"] == CORRECT).mean()) if len(pos) else float("nan")
    spec = float((neg["verdict"] == INCORRECT).mean()) if len(neg) else float("nan")
    return {"sensitivity": sens, "specificity": spec, "n_pos": len(pos), "n_neg": len(neg),
            "nd_rate": float((gold["verdict"] == ND).mean()),
            "gate_fail_rate": float((~gold["gate_ok"]).mean())}


@traced
def calibrate_components(gold: pd.DataFrame) -> pd.DataFrame:
    """gold: component, verdict, truly_correct, gate_ok (one row per chart and component).
    One calibration row per component (spec 002 T011); not_applicable rows are dropped."""
    rows = []
    for comp, g in gold[gold["verdict"] != "not_applicable"].groupby("component", sort=False):
        rows.append({"component": comp, **calibrate_judge(g)})
    return pd.DataFrame(rows)


@traced
def judge_kappa(gold: pd.DataFrame) -> float:
    """Cohen's kappa between the judge's verdict and the truth (reviewer consensus)."""
    from .phenotype import cohen_kappa
    g = gold[gold["verdict"].isin([CORRECT, INCORRECT]) & gold["gate_ok"]]
    return cohen_kappa((g["verdict"] == CORRECT), g["truly_correct"].astype(bool))


@traced
def bakeoff(gold: pd.DataFrame, classifier_families: set[str] | None = None,
            judge_families: dict[str, str] | None = None, n_boot: int = 500, seed: int = 0) -> pd.DataFrame:
    """Compare candidate judges on the calibration set (spec 002; after GlobalDentBench's
    five-judge comparison, but scored by kappa with a bootstrap CI rather than raw
    acceptance). gold needs a judge_model column. The highest-kappa judge that is NOT
    the same family as an evaluated LLM is selected."""
    rng = np.random.default_rng(seed)
    rows = []
    for j, g in gold.groupby("judge_model"):
        cal = calibrate_judge(g)
        k = judge_kappa(g)
        boots = [judge_kappa(g.iloc[rng.integers(0, len(g), len(g))]) for _ in range(n_boot)]
        lo, hi = np.nanpercentile(boots, [2.5, 97.5])
        fam = (judge_families or {}).get(j, "")
        rows.append({"judge_model": j, "family": fam, "sensitivity": cal["sensitivity"],
                     "specificity": cal["specificity"], "kappa": k, "kappa_ci_low": float(lo),
                     "kappa_ci_high": float(hi), "n": int(cal["n_pos"] + cal["n_neg"]),
                     "nd_rate": cal["nd_rate"], "gate_fail_rate": cal["gate_fail_rate"],
                     "same_family_as_classifier": bool(fam) and fam in (classifier_families or set())})
    t = pd.DataFrame(rows).sort_values("kappa", ascending=False).reset_index(drop=True)
    eligible = t[~t["same_family_as_classifier"]]
    t["selected"] = t["judge_model"] == (eligible.iloc[0]["judge_model"] if len(eligible) else None)
    return t


@traced
def rogan_gladen(p: float, sens: float, spec: float) -> float:
    denom = sens + spec - 1
    if not np.isfinite(denom) or denom <= 0:
        return float("nan")   # judge no better than chance: estimate undefined
    return float(min(max((p + spec - 1) / denom, 0.0), 1.0))


def _p_judged_correct(s: pd.DataFrame) -> float:
    d = s[s["verdict"].isin([CORRECT, INCORRECT]) & s["gate_ok"]]
    return float((d["verdict"] == CORRECT).mean()) if len(d) else float("nan")


@traced
def corrected_accuracy(sample: pd.DataFrame, gold: pd.DataFrame, n_boot: int = 1000,
                       seed: int = 0) -> dict:
    """sample: judged corpus predictions for ONE method. gold: judged calibration rows (all methods)."""
    cal = calibrate_judge(gold)
    p = _p_judged_correct(sample)
    est = rogan_gladen(p, cal["sensitivity"], cal["specificity"])
    # Resample yes/no arrays, not DataFrames (8 methods x 1,000 draws): same draws, same means.
    s_judged = (sample["verdict"].isin([CORRECT, INCORRECT]) & sample["gate_ok"]).to_numpy(bool)
    s_correct = (sample["verdict"] == CORRECT).to_numpy(bool)
    g_ok = (gold["verdict"].isin([CORRECT, INCORRECT]) & gold["gate_ok"]).to_numpy(bool)
    g_true = gold["truly_correct"].to_numpy(bool)
    g_correct = (gold["verdict"] == CORRECT).to_numpy(bool)
    g_incorrect = (gold["verdict"] == INCORRECT).to_numpy(bool)

    def share(x: np.ndarray, keep: np.ndarray) -> float:
        return float(x[keep].mean()) if keep.any() else float("nan")

    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        i = rng.integers(0, len(sample), len(sample))
        j = rng.integers(0, len(gold), len(gold))
        ok, tc = g_ok[j], g_true[j]
        sens, spec = share(g_correct[j], ok & tc), share(g_incorrect[j], ok & ~tc)
        boots.append(rogan_gladen(share(s_correct[i], s_judged[i]), sens, spec))
    lo, hi = np.nanpercentile(boots, [2.5, 97.5]) if np.isfinite(boots).any() else (np.nan, np.nan)
    return {"p_judged_correct": p, "accuracy_est": est, "ci_low": float(lo), "ci_high": float(hi),
            "n_judged": int(sample["verdict"].isin([CORRECT, INCORRECT]).sum()),
            "nd_rate": float((sample["verdict"] == ND).mean())}


# ------------------------------------------------------------------ frontier
@traced
def frontier(table: pd.DataFrame, n_notes: int) -> pd.DataFrame:
    """Adds dominated flag and ICER (USD per additional correct note) along the frontier."""
    t = table.sort_values(["cost_usd", "accuracy_est"], ascending=[True, False]).reset_index(drop=True)
    t["dominated"] = False
    best = -1.0
    for i, r in t.iterrows():
        if r["accuracy_est"] <= best:
            t.loc[i, "dominated"] = True
        else:
            best = r["accuracy_est"]
    t["icer_usd_per_extra_correct_note"] = np.nan
    t["compared_to"] = ""
    prev = None
    for i, r in t[~t["dominated"]].iterrows():
        if prev is not None:
            d_correct = (r["accuracy_est"] - prev["accuracy_est"]) * n_notes
            t.loc[i, "icer_usd_per_extra_correct_note"] = (r["cost_usd"] - prev["cost_usd"]) / d_correct
            t.loc[i, "compared_to"] = prev["method"]
        prev = r
    t["expected_correct_notes"] = t["accuracy_est"] * n_notes
    t["usd_per_1k_correct"] = t["cost_usd"] / (t["expected_correct_notes"] / 1000)
    return t
