# Quickstart: validate spec 012

## Locally (no workspace)

```bash
cd python && pip install -e ".[dev]"
pytest -q tests/test_judge_scorecard.py tests/test_bundle.py tests/test_setup_script.py
python scripts/36_judge_scorecard.py --simulated     # simulated judge: writes data/datasets/judge/simulated_*
cd .. && python/scripts/make_parity_inputs.sh && Rscript r/tests/test_parity.R
```

Expected: tests pass; `simulated_judge_metrics.csv` has every system × metric with `vs_truth`
equal to the README's numbers; parity passes.

## In dev

1. Merge to `main` (non-doc change): the `deploy` run shows a `dev` job that deploys (FR-001).
2. Run the `judge_scorecard` job (or `deploy` with `run_benchmark`). The job prints the queue
   size and the estimated cost before calling the endpoint.
3. Open the dashboard *dental-omop-nlp scorecard*: Phenotyping page shows truth vs judge per
   system; filter a system to see per-chart answers, judge status, verdict and quote.
   De-identification page shows the existing de-id scores.
4. Open the MLflow experiment: one trace per judge call.
5. `python/scripts/36_judge_scorecard.py --export` pulls the tables into
   `data/datasets/judge/` for the repo.
