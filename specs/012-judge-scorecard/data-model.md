# Data model: Judge-backed model scorecard (spec 012)

All tables live in the gold schema (`dental_omop.gold_dental_omop_perio`, same name in every
target). Each has a committed CSV twin under `data/datasets/judge/` (`simulated_*` for dry runs).

## chart_answers
One system's answer on one review chart.

| Column | Type | Notes |
|---|---|---|
| visit_id | int | review chart |
| system | str | e.g. `modernbert-base+cw`, `algorithm_v0` |
| answer | str / null | one of six statuses; null = no answer |
| difficulty | str | L1 / L2 / L3 |

## judge_queue
| Column | Type | Notes |
|---|---|---|
| visit_id | int | |
| kind | str | `status` (no answer shown) or `verdict` |
| answer | str / null | the answer judged (`verdict` only) |
| note_text | str | from `review_key.csv` (de-identified, leak-gated) |

Unique on (visit_id, kind, answer).

## judgments
| Column | Type | Notes |
|---|---|---|
| visit_id, kind, answer | | key, as in the queue |
| verdict | str | correct / incorrect / not_determinable (`verdict` rows) |
| judge_status | str / null | the judge's status (`status` rows) |
| quote | str | verbatim from the note |
| gate_ok | bool | quote gate and schema check passed |
| gate_reason | str | why not |
| endpoint, prompt_version | str | |
| prompt_tokens, completion_tokens | int | |
| simulated | bool | true for the simulated judge |
| api_error | bool | the endpoint failed after retries; not a judgment, asked again on the next run |

Validation: `judge_status` ∈ six statuses or null; a row with `gate_ok = false` counts as
not determinable / no answer.

## judge_metrics
One row per system and metric.

| Column | Type | Notes |
|---|---|---|
| system | str | |
| metric | str | exact_status, sensitivity, specificity, ppv, npv, stage4_caught, unsafe_rate, exact_L1/L2/L3 |
| vs_truth | float | as in the README |
| vs_judge | float | same metric, judge's status as reference |
| difference | float | vs_judge − vs_truth |
| corrected_accuracy, ci_low, ci_high | float | Rogan-Gladen from verdicts (exact_status rows only) |

## judge_agreement
The judge's own status against the truth: overall and per truth status and difficulty: n,
agreement, kappa, 95% range.
