# ADR 0001: Synthetic data, public repo, R and Python against one contract

Date: 2026-10-25 · Status: accepted

## Context

We want to compare BERT-family models for reading periodontal status out of
dental notes. The work is not yet approved for internal data or compute.
The data science side works in R; data engineering works in Python.
Databricks is the eventual platform; Free Edition is available now.

## Decision

1. **Synthetic only.** Synthea plus custom dental generation. No PHI, no
   internal data, in any branch.
2. **Public GitHub** until internal use is approved, then the code moves to
   the internal workspace and this repo stays the public reference.
3. **One contract, two languages.** OMOP tables, `labeled_notes.csv`,
   `split.csv` and the results schema in `eval/README.md` are the interface.
   Labels and the scorer exist in both languages and are parity-tested.
   Fine-tuning lives in Python; R reaches it through reticulate rather than
   re-implementing it.
4. **OMOP 5.4 + OHDSI Dentistry WG `SITE`/`SITE_EVENT`** for tooth-level
   data, rather than inventing our own extension.
5. **Model output goes to `NOTE_NLP` as a flag**, never `CONDITION_OCCURRENCE`.
6. **Free Edition first** for the Python path at small sample sizes; R runs
   locally because serverless is Python/SQL only.

## Consequences

- Results on synthetic notes say nothing about real-note accuracy; they
  rank models and prove the pipeline. Real-note evaluation needs de-id and
  clinician labels first.
- Two implementations of labels/scorer is extra code; the parity test is
  what keeps it honest.
- The synthetic note generator becomes a product in itself: if it's too
  easy, every model ties (see `docs/plan.md`).
