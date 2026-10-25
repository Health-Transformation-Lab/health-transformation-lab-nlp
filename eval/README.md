# Shared evaluation contract

Python and R both obey this file. A result from either language is
comparable only if it follows it.

## Inputs

`data/labels/labeled_notes.parquet` (also written as `.csv` for R users
without arrow):

| column | type | meaning |
|--------|------|---------|
| `note_id` | int | OMOP `note.note_id` |
| `person_id` | int | OMOP `person.person_id` |
| `note_text` | str | the SOAP note |
| `label` | str | one of the six labels below |
| `max_probing_depth_mm`, `bop_pct`, `max_cal_mm`, `rbl_pct`, `teeth_lost_perio` | float | chart numerics (structured baseline only; text models must not see them) |

`data/labels/split.csv`: `person_id,split` with split in `train|test`.
**Split is by person**, made once by `split.py` with seed 42, 80/20,
stratified on each person's worst label. Never re-split per model.

Labels (fixed order): `healthy, gingivitis, periodontitis_stage_1,
periodontitis_stage_2, periodontitis_stage_3, periodontitis_stage_4`.

## Metrics

Computed on the test split only.

| metric | definition |
|--------|------------|
| `macro_f1` | unweighted mean of per-class F1 over the six labels |
| `f1` (per class) | one row per label |
| `sensitivity` | binary: periodontitis (any stage) vs not. TP / (TP + FN). **Primary metric** — for screening, the miss is the costly error. |
| `specificity` | same binary. TN / (TN + FP) |
| `auroc` | same binary, from P(periodontitis) = sum of the four stage probabilities. Blank if the rung gives no probabilities. |

## Output

One CSV per run under `data/results/`, long format:

```
run_id,model_id,language,metric,class,value,n_test,timestamp
```

`class` is the label for per-class F1 and empty otherwise. `language` is
`python` or `r`. The leaderboard is `cat data/results/*.csv`.
