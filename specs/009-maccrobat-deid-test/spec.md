# Feature Specification: a de-identification test pass on MACCROBAT (real published case reports, BIO labels)

**Feature Branch**: `009-maccrobat-deid-test`

**Created**: 2026-10-26

**Status**: implemented; regex, Presidio and transformer engines run on the 200 MACCROBAT documents (CPU)

**Input**: "We need to get another test pass using this data": MACCROBAT
([figshare](https://doi.org/10.6084/m9.figshare.9764942.v2), CC BY 4.0), whose annotations are
also published as BIO token labels (B = beginning, I = inside, O = outside an entity).

> Personal learning project; public data only. MACCROBAT is 200 clinical case reports from PubMed
> Central, edited by its authors to the case details and annotated by hand (Caufield, 2019). It holds
> no names or contact details. Its text **never enters the repo**: it is downloaded to `data/raw/`
> (git-ignored) and only aggregate scores are committed. Test fixtures are invented sentences.

## Context

Every de-identification score so far (spec 007) is on synthetic notes or synthetic PHI sets
(ASQ-PHI). The engines and the dental guard have never seen clinical prose written by other
people. MACCROBAT gives that, with two things marked that matter for de-identification:

1. **Identifiers** the engines should remove. MACCROBAT was not built for PHI, so the PHI subset is
   derived by rule from its `Date` and `Age` entities, following HIPAA Safe Harbor: a date with a
   month or day ("June 2013", "12/03/2014"; a year alone is allowed) and an age of 90 or over.
2. **Clinical content** that must survive: symptoms, diseases, procedures, drugs, doses, lab values,
   anatomy and the rest. Anything an engine removes from these is over-redaction on real text,
   the damage that matters to the classifiers downstream.

Everything else (relative dates, a year alone, ages under 90, sex, places such as "emergency
department", ethnicity, occupation) is neither: removed or not, it is reported by type and not scored.

## User stories

### US1 - Read BIO labels (P1)
`maccrobat.bio_spans(tokens, tags)` turns BIO tokens into text and character spans. An `I-` tag
that doesn't continue an entity of the same type starts a new one (the usual lenient reading).
Tokens are re-joined with approximate spacing (no space before closing punctuation, none around
`-` and `/`), since BIO files drop the original whitespace.
- **Given** tokens and tags, **Then** every span's text equals its slice of the text.

### US2 - Records for the existing scorer (P1)
`maccrobat.load_bio(path)` reads JSONL rows `{"tokens", "tags"}` into the challenge-record format
of spec 007 (`phi`, `decoys`, plus `entities` with a `role` of `phi`, `clinical` or `other`).
Duplicate documents (the mirror holds the 2018 and 2020 releases of the same 200) keep the last copy.

### US2b - Original release (P1)
`maccrobat.load_brat(path)` reads the figshare zip (or its folder): `NNN.txt` with `NNN.ann` brat
standoff. Exact text and offsets; each fragment of a split entity is its own span. Default source.

### US3 - Scores (P1)
`deid_eval.score_records` scores the records unchanged (recall on the derived PHI; decoy damage =
share of clinical entities with any character removed). `deid_eval.damage_by_type` adds, per
entity type, the share of entities touched. `scripts/32_maccrobat_deid.py` writes
`data/deid/maccrobat_scores.csv` and `data/deid/maccrobat_by_type.csv`.

## Limits (write them next to the result)
- The PHI subset is a rule over MACCROBAT's labels, not an annotator's PHI labels; it is small
  (calendar dates and few ages ≥ 90) and has no names, phones or addresses at all.
- Case reports are not chart notes: journal prose, already de-identified by the publisher.
- With `--source bio`, spacing is reconstructed from tokens and overlapping entities are lost.
- Python only: de-identification scoring is not part of the R parity contract (spec 007 keeps
  only the cost model in R).

## Out of scope
Training or scoring a clinical entity recognizer on MACCROBAT (possible next step). Committing any
MACCROBAT text.
