# Implementation Plan: Structured radiograph findings

**Branch**: `003-radiograph-structured-data` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

## Summary

Simulate a radiograph AI's structured output per visit, read it into a status,
add it as the eighth source, use it in the rule-based algorithm and as features
in a note + radiograph fusion model; show it to reviewers; map it to OMOP.

## Constitution Check

| Principle | Status |
|-----------|--------|
| I. Synthetic only | Pass: simulated output only; no images; DICOM explicitly out of scope |
| II. Two languages | Pass: radiograph is a compared method; reliability/harm/by-level parity covers it |
| III. Test-first | Pass: T003–T005 |
| IV. Honest outputs | Pass: error model values marked as planning assumptions; device named `sim-rad-ai` |
| V. Published evidence | Pass: RBL in 2017 staging/grade; vendor clearance and CNN accuracy cited |
| VI. Simple, seeded | Pass: sklearn ColumnTransformer only |

## Source changes

```text
python/dental_omop_nlp/radiograph.py     NEW  simulate output, features, reader, summary text
python/dental_omop_nlp/study.py          radiograph per visit; features in train/key; tasks show it
python/dental_omop_nlp/phenotype.py      priority includes radiograph_ai; METHODS += radiograph_ai
python/dental_omop_nlp/rungs.py          fusion_tfidf_rad
python/scripts/13_reliability.py         compare includes radiograph_ai
r/R/04_reliability.R                     compare includes radiograph_ai
labelstudio/chart_review.xml             radiograph field + decided_by choice
omop/vocab/local_concepts.csv            RAD_* concepts
models.yaml                              fusion rung in ladder
```
