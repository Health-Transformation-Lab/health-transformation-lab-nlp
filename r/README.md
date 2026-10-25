# R side

Same benchmark, same notes, same patient split, same scorer output as the
Python side. A result from here and a result from `python/` land in the same
`data/results/` folder in the same columns.

## What's here

| File | What it does | Needs |
|------|--------------|-------|
| `R/labels.R` | Chart → status (R twin of `labels.py`) and the rules baseline | base R |
| `../eval/score.R` | Shared scorer (R twin of `score.py`) | base R |
| `tests/test_parity.R` | Proves R and Python agree on labels, rules predictions and metrics | base R |
| `run_ladder.R` | Runs rungs and writes results | base R for rules; tidymodels for the rest |
| `R/01_etl_synthea.R` | Full Synthea → OMOP CDM 5.4 load with OHDSI `ETLSyntheaBuilder`, plus the dental extension | ETL-Synthea, DuckDB, Athena vocab |
| `R/02_baselines.R` | Structured and TF-IDF baselines | tidymodels, textrecipes, glmnet |
| `R/03_encoders.R` | Encoder rungs: frozen embeddings (`text` pkg) or fine-tune via reticulate | `text` + Python env |
| `install.R` | Installs all of the above | — |

## Quick start (from the repo root)

```r
# once
Rscript r/install.R

# data: either let Python build it ...
#   cd python && pip install -e . && python scripts/01_build_dataset.py && python scripts/02_split.py
# ... or load a full CDM from Synthea with OHDSI's ETL:
Rscript r/R/01_etl_synthea.R

# check R and Python agree
python python/scripts/export_rules_predictions.py
Rscript r/tests/test_parity.R

# run rungs
Rscript r/run_ladder.R rules_baseline structured_baseline tfidf_logreg
Rscript r/run_ladder.R distilbert-base+frozen
Rscript r/run_ladder.R distilbert-base+finetune
```

## Two kinds of encoder result

- `<model>+frozen` — embeddings from the pretrained model, glmnet on top.
  Pure R, cheap, tells you what the pretraining already knows. **Not**
  comparable to the Python fine-tuned numbers.
- `<model>+finetune` — calls the Python trainer through reticulate, so the
  number is the same experiment as the Python rung. Use this when the two
  leaderboards must line up.

## Databricks

Databricks Free Edition serverless runs Python and SQL only, so the R side
runs locally or in Posit. The Delta tables the notebook writes
(`workspace.dental.labeled_notes`, `benchmark_results`) can be read from R
with `sparklyr` / Databricks Connect when that's useful. In a paid workspace
with classic compute, these scripts run in an R notebook unchanged.

## Status

Tested here: `labels.R`, `score.R`, `test_parity.R`, `run_ladder.R rules_baseline`
(R and Python agree on all 754 notes and every metric to 1e-16).
Written but not yet run: `01_etl_synthea.R`, `02_baselines.R`, `03_encoders.R`
— they need packages this repo's CI doesn't install yet.
