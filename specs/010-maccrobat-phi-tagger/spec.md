# Feature Specification: a fine-tuned PHI tagger (Age, Sex, Date) on MACCROBAT, with regex date post-processing

**Feature Branch**: `010-maccrobat-phi-tagger`

**Created**: 2026-10-26

**Status**: implemented; four Longformer runs on CPU, final system test weighted F1 0.77 (model alone 0.80)

**Input**: a course exercise on de-identification as sequence classification (named entity recognition)
over MACCROBAT: filter the annotations to AGE, SEX and DATE, split notes 80:20, write BIO files,
fine-tune Longformer, then (A) tune the training settings, (B) add regex post-processing of dates,
(C) report the final system's weighted F1 and analyse the errors left. The course's own files and
notebook aren't used here; the steps are rebuilt from that description.

> Personal learning project; public data only. MACCROBAT (Caufield 2019, CC BY 4.0) and the BIO
> files and error listings derived from it are committed under `data/external/maccrobat/`
> (constitution v1.2.0); fine-tuned models stay in `python/runs/` (git-ignored, too large).
> Test fixtures are invented sentences.

## Context

Spec 009 scored off-the-shelf de-identification engines on MACCROBAT. This spec trains one: a token
classifier for MACCROBAT's own `Age`, `Sex` and `Date` labels. Note that MACCROBAT's `Date` covers
relative dates ("3 days later") as well as calendar dates, and `Sex` and most ages aren't HIPAA
identifiers; the label set follows the exercise, not Safe Harbor.

## User stories

### US1 - BIO data (P1)
`phi_tagger.bio_docs(records)`: the original brat records (spec 009 `load_brat`) to word tokens
(`\w+` or one punctuation mark, so "8-year-old" is 8 / - / year / - / old) with BIO tags for the
three types; other entity types are O. `split_docs` makes a seeded 80:20 document split.
`write_conll` writes `train.txt` / `test.txt` in the exercise's format.

### US2 - Fine-tuning (P1)
`scripts/33_maccrobat_phi_tagger.py` fine-tunes a Hugging Face encoder (default
`allenai/longformer-base-4096`) for token classification: sentences packed into chunks of up to
`--max-words` words, labels on each word's first sub-token. Settings on the command line (learning
rate, epochs, batch size, weight decay, warmup, chunk size, seed); one row per run appended to
`data/deid/maccrobat_tagger_runs.csv`.

### US3 - Scores (P1)
Entity-level precision, recall and F1 per type (exact span and type, the usual seqeval rule), and
their support-weighted average ("weighted F1"). Error counts by kind (missed, spurious, wrong
boundary, wrong type) per type.

### US4 - Regex date post-processing (P1)
`phi_tagger.regex_dates(text, words, tags, patterns)`: words the model left O that fall inside a date
regex match are tagged Date. Named pattern sets are scored one by one and together, before and
after, so each pattern's gain and cost is visible.

## Limits
- One 40-note test set: differences of a point or two are within noise; report the split and seed.
- CPU only here; few settings can be tried. Name what wasn't tried.
- Python only (not part of the R parity contract).
