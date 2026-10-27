# Feature Specification: results a clinician can read (yes/no periodontitis metrics, plain column names)

**Feature Branch**: `011-plain-results-metrics`

**Created**: 2026-10-27

**Status**: implemented

**Input**: "I don't really understand accuracy and recall … does one cover false positives";
"I have no clue what macro F1 is". Report the results the way phenotype validation studies do.

> Personal learning project; synthetic data. No new runs: every number is recomputed from
> committed predictions and scores.

## Context

The results leaderboards (README summary, `docs/results.md`) rank phenotyping systems by six-status
accuracy and show macro-F1, and de-identification engines by recall and precision. Accuracy doesn't
separate missed cases from false alarms, macro-F1 means nothing to a clinical reader, and the
README never says which column measures false positives.

Phenotype validation (OHDSI PheValuator and case-validation work) reports a yes/no question,
here *does this patient have periodontitis (any stage)?*, with four numbers:

| Term | Plain question | Mistake it measures |
|---|---|---|
| Sensitivity | Of patients who have it, how many were caught? | missed cases (false negatives) |
| Specificity | Of patients who don't, how many were correctly cleared? | false alarms (false positives) |
| PPV | When it says "has it", how often is that right? | false alarms, from the user's side |
| NPV | When it says "doesn't", how often is that right? | missed cases, from the user's side |

## Requirements

- **FR-001** The shared scorer (`eval/score.py`, `eval/score.R`) adds `ppv` and `npv` for the
  periodontitis yes/no question, next to the existing `sensitivity` and `specificity`, with the
  same convention: a prediction that isn't a periodontitis stage (including no prediction) is a
  "no". Undefined values (no positive calls, no negative calls) are missing. Python and R agree to
  1e-9 (parity test, scorer section).
- **FR-002** Phenotyping leaderboards show, per system, periodontitis yes/no sensitivity,
  specificity and PPV (NPV in the full table), alongside the share of charts with the exact status
  right, which keeps its 95% CI as the ranking metric. Macro-F1 is not shown.
- **FR-003** Columns use plain names: "Exact status right" (was accuracy), "Stage IV caught" (was
  stage IV recall), "Identifiers caught" (was recall), "Removals that were identifiers" (was
  precision), "Clinical text damaged" / "Dental terms damaged" / "Clean queries changed" (were the
  damage and over-redaction columns). Each table has a one-line key saying which column counts
  missed cases and which counts false alarms.
- **FR-004** Ranking is unchanged (exact status right for phenotyping, identifiers caught for
  de-identification; 95% rank ranges), so this spec changes presentation, not results.

## Success criteria

- Every phenotyping row shows sensitivity, specificity and PPV; numbers equal `eval/score.py`'s on
  the same predictions (test).
- Neither the README nor `docs/results.md` contains "macro-F1", "accuracy" or "recall" as a column name.
- R parity passes with the new metrics.
