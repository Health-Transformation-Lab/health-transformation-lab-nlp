# Tasks: Judge-backed model scorecard on Databricks

**Input**: `specs/012-judge-scorecard/` (spec, plan, research, data-model, contracts, quickstart)

**Tests**: required (constitution III, test-first): each implementation task follows its failing test.

## Phase 1: Setup

- [ ] T001 Create `data/datasets/judge/` with a README stating source, simulated vs LLM judgment labelling, and that notes come from `review_key.csv` (de-identified, leak-gated)

## Phase 2: Foundational

- [ ] T002 Failing test in `python/tests/test_judge_scorecard.py`: `chart_answers()` returns one row per (visit_id, system) for the 240 review charts from `data/datasets/ladder/ladder_preds.csv` plus the phenotype systems in `answer_key/review_key.csv`, with `difficulty`; `answer` is one of six statuses or null
- [ ] T003 Implement `chart_answers()` in `python/dental_omop_nlp/judge_scorecard.py` (paths via `dental_omop_nlp.paths`)
- [ ] T004 Failing test: `judge_queue()` has one `status` row per chart and one `verdict` row per unique (visit_id, answer) with a non-null answer; unique on (visit_id, kind, answer); `note_text` from `review_key.csv`
- [ ] T005 Implement `judge_queue()` and `estimate_cost(queue, usd_per_1m_in, usd_per_1m_out)` in `python/dental_omop_nlp/judge_scorecard.py`

## Phase 3: User Story 1 - Dev deploys on merge (P1)

**Independent test**: workflow structure test; then a merge shows a dev deploy job.

- [ ] T006 [US1] Failing test in `python/tests/test_setup_script.py`: on `push`, `deploy.yml` runs targets dev and uat (matrix); `workflow_dispatch` still runs only the chosen target; each still gated on `DATABRICKS_CLIENT_SECRET`
- [ ] T007 [US1] Implement the matrix in `.github/workflows/deploy.yml`; update `docs/deployment.md`

## Phase 4: User Story 2 - Every README metric from the judge and the truth (P1)

**Independent test**: `python scripts/36_judge_scorecard.py --simulated` writes `simulated_judge_metrics.csv` whose `vs_truth` equals the README's numbers.

- [ ] T008 [P] [US2] Failing test in `python/tests/test_judge.py` (or existing judge test file): status prompt `judge-v3` (`STATUS_SYSTEM`, `STATUS_USER`, no answer shown) and `gate_status(note, out)`: status ∈ six or null; non-null status needs a verbatim quote
- [ ] T009 [US2] Implement the status prompt, `gate_status` and `OpenAIJudge.status(note)` in `python/dental_omop_nlp/judge.py`; simulated twin on `SimulatedJudge`
- [ ] T010 [US2] Failing test: `run_judge(queue, judge, done=None)` returns `judgments` per data-model (gate_ok false → verdict not_determinable / judge_status null), skips rows already in `done` (resumable), records endpoint, prompt_version, tokens, `simulated`
- [ ] T011 [US2] Implement `run_judge` in `python/dental_omop_nlp/judge_scorecard.py` with optional MLflow tracing (`track` extra, no-op when absent)
- [ ] T012 [US2] Failing test: `judge_metrics(answers, judgments, key)`: for every system and metric (exact_status, sensitivity, specificity, ppv, npv, stage4_caught, unsafe_rate, exact_L1/L2/L3) `vs_truth` equals the scorer used by `readme_results`; `vs_judge` uses the judge's status as reference; `difference = vs_judge - vs_truth`; exact_status rows carry Rogan-Gladen corrected accuracy with a seeded 95% range from verdicts
- [ ] T013 [US2] Implement `judge_metrics` and `judge_agreement` (judge status vs truth: overall, per truth status, per difficulty; n, agreement, kappa, 95% range) in `python/dental_omop_nlp/judge_scorecard.py`, reusing `eval/score.py`, `harm.unsafe_rates`, `cost_effectiveness.corrected_accuracy`, `phenotype.cohen_kappa`
- [ ] T014 [US2] R twin `r/R/11_judge_scorecard.R` for the difference and judge agreement; parity section in `r/tests/test_parity.R` (1e-9 on point values)
- [ ] T015 [US2] Script `python/scripts/36_judge_scorecard.py` (`--simulated`, `--endpoint`, `--export`); writes `data/datasets/judge/{simulated_,}{chart_answers,judgments,judge_metrics,judge_agreement}.csv`; add the simulated run to `python/scripts/make_parity_inputs.sh`
- [ ] T016 [US2] Notebook `databricks/notebooks/07_judge_scorecard.py` and job `judge_scorecard` in `databricks/resources/jobs.yml`: widgets catalog, schema, judge_endpoint, experiment_id; prints queue size and estimated cost; skips when endpoint is `none`; writes the five tables to the gold schema
- [ ] T017 [US2] `judge_endpoint` dev default `databricks-meta-llama-3-3-70b-instruct` in `databricks.yml`; bundle test in `python/tests/test_bundle.py`

## Phase 5: User Story 3 - Two-page dashboard (P2)

**Independent test**: bundle test parses the dashboard and finds pages Phenotyping and De-identification, each dataset reading a gold table.

- [ ] T018 [US3] Failing test in `python/tests/test_bundle.py`: `resources.dashboards.scorecard` exists with the same name in every target, uses `${var.warehouse_id}`, its `.lvdash.json` has pages named Phenotyping and De-identification
- [ ] T019 [US3] `databricks/dashboards/scorecard.lvdash.json` and `databricks/resources/dashboards.yml`: Phenotyping page (scorecard truth vs judge, judge agreement, per-chart table filterable by system with answer, truth, judge status, verdict, quote); De-identification page (`deid` scores table, loaded by the scorecard notebook from `data/deid/scores.csv`)

## Phase 6: User Story 4 - README link (P3)

- [ ] T020 [US4] Failing test in `python/tests/test_readme_results.py`: the README block links to the dashboard and to `docs/results.md#judge`, and says judge metrics are LLM judgments checked against the truth
- [ ] T021 [US4] Implement in `python/dental_omop_nlp/readme_results.py` (+ judge section in `docs/results.md` from `judge_metrics.csv` when present); run `scripts/35_readme_results.py`

## Phase 7: Polish

- [ ] T022 Check the endpoint's current pay-per-token price; record it with source and date in `data/datasets/judge/README.md`; confirm estimate < US$5 before the first real run
- [ ] T023 Run the judge in dev, export, commit `data/datasets/judge/*.csv`, refresh README
- [ ] T024 `pytest -q tests`, `ruff`, parity; `/create-pr`

## Dependencies

T001 → T002–T005 → (US1 independent) and US2 (T008–T017) → US3 (T018–T019 needs US2 tables) → US4 → Polish.
US1 can ship alone. Parallel: T006–T007 with T008–T009; T014 with T015.

## MVP

US1 + US2 run with the simulated judge locally (no endpoint cost), then one real run in dev.
