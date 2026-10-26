# Feature Specification: Label Studio review flows for de-identification

**Feature Branch**: `008-deid-review`

**Created**: 2026-10-26

**Status**: v1 implemented on synthetic data; simulated annotators only (no human has annotated)

**Input**: "We are also going to need a Label Studio flow for de-identification." Clarified: both a
gold-annotation flow and a QA flow; tasks pre-annotated with an engine's spans as predictions.

> Personal learning project; synthetic data only. Every identifier in these tasks is invented by
> the generator (`phi_challenge.py`). Nothing here describes any organization's de-identification setup.

## Context

Spec 007 scores de-identification engines against PHI the generator marked. Real notes have no
such key: the gold has to come from people, and the leak rate of the chosen engine has to be
measured by people reading its output (the human review sample `deid_eval.review_cost` already
prices). Both need a Label Studio project, an import path, and scores.

## User stories

### US1 - Gold PHI annotation (P1)
Annotators mark every identifier in the original note, using the spec 007 categories (2014
i2b2/UTHealth guidelines; HIPAA Safe Harbor), in Label Studio (`labelstudio/deid_gold.xml`).
- Tasks are **pre-annotated** with one engine's spans as Label Studio *predictions*; the annotator
  accepts, fixes, deletes or adds spans. Engine types that don't name a category (NAME, LOCATION)
  load as `PHI_UNSPECIFIED`, which the annotator must re-label.
- A seeded share of tasks (default 20%) has **no** pre-annotation, so anchoring on the engine can
  be measured: annotator recall aided vs unaided.
- Import gives per-annotator spans; **agreement** between annotators (entity F1, exact span, with
  and without category); a **consensus gold** (characters marked by at least half the annotators of
  that note); and every engine scored against the consensus with spec 007's `score_records`.
- On synthetic notes the generator's spans are also known: each annotator's recall against them.
- **Given** a seed, **Then** the tasks are identical.

### US2 - QA of de-identified output (P1)
Reviewers read **de-identified** notes (`labelstudio/deid_qa.xml`) and answer: does any
identifier remain (yes/no), marking each leak; was clinical meaning lost to over-redaction (yes/no).
- Sample: every note the residual scan flags, plus a seeded random sample up to N.
- Residual-scan hits are pre-annotated as `LEAK` predictions.
- Import gives the **leak-note rate** with a Wilson 95% CI (a note leaks if any reviewer says so),
  per reviewer and pooled; over-redaction rate likewise. On synthetic notes the true leaks are
  known (answer key, never in the tasks): reviewer sensitivity and specificity.

### US3 - Dry run (P2)
`--simulate N` writes `simulated_*` exports from N simulated annotators/reviewers with set miss
rates (higher on spans the pre-annotation missed: anchoring), so the import and scores can be
tested before anyone annotates. Simulated numbers are never results.

### US4 - Parity (P2)
R twin of the agreement F1 and the Wilson leak-rate CI (`r/R/08_deid.R`), checked by `test_parity.R`.

## Rules
- Task files hold note text with (fake) PHI: written to `data/raw/` (never committed), including the
  QA tasks, since a leak is PHI. Scores (no note text) go to `data/deid/review/`.
- On real data both projects run only inside the approved secure environment. The gold flow shows
  identified notes, an exception to "only de-identified text goes into Label Studio" that applies to
  this project alone; the chart-review project is unchanged.

## Out of scope
Running a real annotation round. Surrogate replacement. Re-identification risk.

## References
- Stubbs A, Uzuner Ö. Annotating longitudinal clinical narratives for de-identification: the 2014
  i2b2/UTHealth corpus. J Biomed Inform 2015;58(Suppl):S20–S29.
- HHS, Guidance regarding methods for de-identification of PHI (Safe Harbor).
- Label Studio docs: import pre-annotated data (predictions); Labels and Choices tags.
- Wilson EB. Probable inference, the law of succession, and statistical inference. JASA 1927;22:209–212.
