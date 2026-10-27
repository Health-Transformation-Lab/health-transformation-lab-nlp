# Research: Judge-backed model scorecard (spec 012)

## R1. Where do per-chart answers come from?

- **Decision**: `data/datasets/ladder/ladder_preds.csv` (240 review charts × 30 note-reading systems,
  committed) plus the phenotype columns in `data/datasets/answer_key/review_key.csv`
  (`algorithm_v0`, `algorithm_design`, single-evidence readings). The scorecard job loads these into
  a `chart_answers` table; the Databricks benchmark job appends the baselines it trains itself.
- **Rationale**: the encoders and MedGemma were run on CPU outside Databricks; their answers are
  already committed and are what the README scores. Re-running them in Databricks isn't needed to
  judge them.
- **Alternatives**: have the benchmark job train every system (GPU, hours; out of scope).

## R2. The judge's own status: reuse the verdict call or a separate call?

- **Decision**: a separate *status* call per chart (no predicted status shown), plus the existing
  *verdict* call per unique (chart, answer).
- **Rationale**: the verdict prompt shows the predicted status, so its `supported_status` can lean
  towards it (anchoring). FR-006 needs one judge status per chart independent of any system. The
  status prompt reuses `judge.CRITERIA` and the same JSON shape (`supported_status`, `quote`).
- **Alternatives**: take `supported_status` from the verdict calls and vote across systems
  (anchored, and several answers per chart).

## R3. How many calls, and cost (SC-005)?

- **Decision**: judge each unique (chart, answer) once. On `ladder_preds.csv` there are far fewer
  unique pairs than 240 × 30 because systems mostly agree; the plan computes the exact count in
  the queue step and prints the estimated token cost before calling.
- **Estimate**: ~1,100 input and ~100 output tokens per call; 240 status calls + at most 1,440
  verdict calls (240 charts × 6 statuses) is ≤ 1.9 M input tokens. At pay-per-token list prices for
  a 70B model this is a few US dollars at most; the task checks the current price list first.
- **Alternatives**: judge per (chart, system): ~9,000 calls for the same information.

## R4. How does the judge run on Databricks?

- **Decision**: the existing `OpenAIJudge` client against the workspace's OpenAI-compatible
  serving endpoint (`<host>/serving-endpoints`), run by a Python notebook task, with MLflow tracing
  on. The batch SQL notebook (`02_llm_judge.sql`) stays for corpus scale.
- **Rationale**: one Python path gives the quote gate, retries, resumability (skip rows already
  judged) and MLflow traces (FR-011); the same code runs locally for tests with a simulated judge.
- **Alternatives**: `ai_query` in SQL (gate in SQL, no traces, harder to resume per row).

## R5. Metrics against the judge: new scoring code?

- **Decision**: no new scorer. Every README metric is computed by the existing functions
  (`ladder_eval`, `eval/score.py`, `harm.unsafe_rates`) with the judge's status as the reference
  instead of the truth. Judge-corrected accuracy uses `cost_effectiveness.corrected_accuracy`
  with the verdicts and a calibration set built from the review charts.
- **Rationale**: Python/R parity already covers those functions. The only new computation is
  the per-metric difference and the judge's agreement with the truth (kappa, per-status), both
  added to the R twin and the parity test.

## R6. Dashboard

- **Decision**: an AI/BI (Lakeview) dashboard as a bundle resource
  (`resources.dashboards`, a `.lvdash.json` file, the bundle's warehouse), two pages:
  Phenotyping and De-identification. Datasets are SQL over the gold schema tables.
- **Rationale**: deployed with the bundle (identical name in every target), no custom web code;
  workspace probe on 2026-10-27 confirmed the dashboards API is enabled.
- **Alternatives**: a hand-built HTML page (more code, can drift from tables).

## R7. Deploy dev on merge

- **Decision**: on `push` to `main`, run the deploy job for `[dev, uat]` (matrix); `workflow_dispatch`
  keeps its single chosen target. Each target still skips when its environment has no secret.
- **Rationale**: FR-001 with uat unchanged.

## R8. Calibration source

- **Decision**: calibrate against the generator's truth on the review charts and say so; the
  reviewers here are simulated, so a "human review" calibration would be simulated too.
