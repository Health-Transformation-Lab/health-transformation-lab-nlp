# Feature Specification: Judge-backed model scorecard on Databricks

**Feature Branch**: `012-judge-scorecard`

**Created**: 2026-10-27

**Status**: Draft

**Input**: "How can I use the Databricks LLM judge to evaluate and report on the models? Can it
evaluate BERT models? Can I get all the metrics in my README from the LLM judge? Does the LLM
judge or other Databricks reporting do this better than me coding it? Two tabs, one for
phenotyping and one for de-identification. Why does dev not deploy to dev?"

> Personal learning project; synthetic data only. The judge is a real LLM call on synthetic,
> de-identified notes; its output is labelled *LLM judgment*. Simulated judge runs stay
> `simulated_*` / `sim:`.

## Context

Every phenotyping metric in the README is computed against the generator's truth, which exists
only because the data is synthetic. On real notes there is no answer key. An LLM judge can stand in
for one, but only as far as it agrees with the truth where the truth is known. The repo already has
a judge prompt (`judge.py`, AAP worksheet rules, verbatim-quote gate), a batch SQL judge notebook
(`02_llm_judge.sql`), an MLflow GenAI judge (`mlflow_judge.py`) and judge-error correction
(Rogan-Gladen in `cost_effectiveness.py`), but nothing feeds the judge per-chart answers, it returns
only a verdict, and no endpoint is set.

The judge evaluates a system's **answers**, not the system: it works the same for fine-tuned BERT
models, keyword rules and LLM readers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dev stays current without a manual deploy (Priority: P1)

As the project owner, when a change merges to `main`, the dev environment is redeployed so what I
see in Databricks matches the repo.

**Why this priority**: Every later story is inspected in dev; today merges deploy only to uat, which
isn't set up, so dev drifts.

**Independent Test**: Merge a non-doc change; the deploy workflow runs for dev and the dev jobs
show the merged commit. uat and prod behave as before.

**Acceptance Scenarios**:

1. **Given** dev has the service principal's credentials, **When** a non-doc change merges to
   `main`, **Then** the bundle deploys to dev.
2. **Given** uat has no credentials, **When** the same merge happens, **Then** uat skips as today.
3. **Given** a doc-only change, **When** it merges, **Then** nothing deploys.

---

### User Story 2 - Every README metric, from the judge as well as the truth (Priority: P1)

As the owner, for each phenotyping system I see every README metric twice, once against the
truth and once against the judge's answer, with the gap between them, so I know how far the judge
can be trusted on real notes.

**Why this priority**: This is the question asked: can the judge report on the models?

**Independent Test**: Run the judge over the 240 review charts; the per-system table has both
columns for every metric and a judge-corrected accuracy with a 95% range.

**Acceptance Scenarios**:

1. **Given** each system's per-chart answers, **When** the judge runs, **Then** for every chart it
   records a verdict on the answer (correct / incorrect / not determinable), its own status (one of
   six) and a verbatim quote from the note; an answer whose quote isn't in the note is not counted.
2. **Given** judge results, **When** metrics are computed, **Then** each README phenotyping metric
   (exact status right, periodontitis sensitivity, specificity, PPV, NPV, stage IV caught, unsafe
   errors, by note difficulty, rank) appears against the truth and against the judge's status.
3. **Given** verdicts and the judge's agreement with the truth, **When** corrected accuracy is
   computed, **Then** it comes with a 95% range.
4. **Given** the same inputs, **When** the metrics are computed in Python and R, **Then** they agree
   to 1e-9.

---

### User Story 3 - Two-tab dashboard with drill-down (Priority: P2)

As the owner, I open one dashboard with a Phenotyping page and a De-identification page, see the
scorecard, and click through to a system's per-chart answers with the judge's quote.

**Why this priority**: The README stays short; detail belongs where it can be filtered.

**Independent Test**: After a dev deploy and a benchmark run, the dashboard opens with both pages
populated from the metric tables.

**Acceptance Scenarios**:

1. **Given** a deploy, **When** I open the dashboard, **Then** it has a Phenotyping page and a
   De-identification page.
2. **Given** a system on the Phenotyping page, **When** I filter to it, **Then** I see its charts:
   truth, its answer, the judge's status, verdict and quote.
3. **Given** a judge run, **When** I open the MLflow experiment, **Then** each chart is a trace with
   the judge's assessment.

---

### User Story 4 - README links to the dashboard (Priority: P3)

The README keeps its short best-per-group summary and adds one line linking to the dashboard (for
readers with workspace access) and noting where judge-based metrics live.

### Edge Cases

- The judge returns malformed output, a status outside the six, or no quote: the chart counts as
  *not determinable* for the verdict and as *no answer* for the judge's status.
- A system gave no answer for a chart: the judge isn't asked; the chart counts as "no" in yes/no
  metrics, as today.
- The judge endpoint is not set (`none`): the judge step skips; truth-based metrics still publish.
- The endpoint fails or rate-limits mid-run: completed charts are kept; rerunning judges only the
  missing ones.
- A note fails the leak gate: it is not sent to the endpoint and is reported as skipped.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** A non-doc merge to `main` deploys the bundle to dev; uat keeps its current trigger and
  skip rule; prod stays manual with approval.
- **FR-002** The benchmark job writes every system's per-chart answer for the 240 review charts
  (chart, system, answer, note difficulty) to a table, and builds the judge's queue from it: one row
  per chart and system with an answer.
- **FR-003** Only notes that pass de-identification and the leak gate go to the endpoint
  (constitution I).
- **FR-004** The judge returns, per queue row: verdict, its own status, and a verbatim quote; the
  existing quote gate applies to both verdict and status. Prompt version is recorded.
- **FR-005** The judge endpoint is a bundle variable per environment; default for dev
  `databricks-meta-llama-3-3-70b-instruct`; `none` skips the judge.
- **FR-006** Each status is judged once per chart (the judge's own status doesn't depend on which
  system's answer it was shown); the verdict is per chart and system.
- **FR-007** For each system, every README phenotyping metric is computed against the truth and
  against the judge's status, with the difference; judge-corrected accuracy (Rogan-Gladen) with a
  95% bootstrap range; and the judge's own agreement with the truth (overall, per status, per note
  difficulty). Computed in code, never by the LLM. Python and R agree to 1e-9.
- **FR-008** The judge is calibrated against the truth on the review charts before its metrics are
  shown (constitution: judges calibrated before use); its sensitivity, specificity and kappa are
  shown next to its metrics.
- **FR-009** Judge results and metrics are written to tables the dashboard reads, and exported to
  committed CSVs so the repo can rebuild the tables without a workspace.
- **FR-010** A dashboard deployed with the bundle has a Phenotyping page (scorecard, truth vs judge,
  drill-down to per-chart rows) and a De-identification page (existing de-id scores).
- **FR-011** Judge calls are logged as MLflow traces in the bundle's experiment.
- **FR-012** The README summary links to the dashboard and says judge metrics are LLM judgments
  checked against the truth.
- **FR-013** Every name follows the repo's Databricks naming rule: identical in every target, no
  per-environment prefix or suffix.

### Key Entities

- **Chart answer**: one system's status for one review chart, with note difficulty.
- **Judge queue item**: a chart answer plus the de-identified note sent to the judge.
- **Judgment**: verdict, the judge's status, quote, whether the quote passed, prompt version,
  endpoint, time.
- **Metric row**: system, metric, value against truth, value against judge, difference, range.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** After a non-doc merge, dev shows the merged commit within 15 minutes with no manual step.
- **SC-002** For every system on the 240 review charts, all README phenotyping metrics appear
  against both truth and judge.
- **SC-003** The judge's own status agreement with the truth is reported with a 95% range, so a
  reader can say whether judge-based metrics are trustworthy.
- **SC-004** From the dashboard, any system's answer on any chart, with the judge's quote, is two
  clicks away.
- **SC-005** A full judge run over the review charts costs under US$5 on pay-per-token pricing
  (estimate from the price list and token counts recorded before running).

## Assumptions

- The review charts' truth is the generator's; reviewers are simulated, so "calibrated against
  human review" is, here, calibrated against the truth, and the docs say so.
- dev's GitHub environment already holds working credentials (verified by the dev deploy).
- Pay-per-token endpoints in the dev workspace are approved for synthetic, de-identified notes.
- De-identification metrics are unchanged; the judge doesn't score de-identification in this spec
  (a leftover-identifier LLM scan is a possible follow-up).
- The README stays about three printed pages; the dashboard holds the detail.
