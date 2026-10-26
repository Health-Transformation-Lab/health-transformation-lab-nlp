# dental-omop-nlp Constitution

Principles every spec, plan and change in this repo must satisfy. The Spec Kit
`/speckit-plan` step checks each plan against them ("Constitution Check").

## Core Principles

### 0. Personal Learning Project, Not Affiliated (NON-NEGOTIABLE)
This repo is a personal learning project, built while waiting for internal
approvals. It is not affiliated with or endorsed by any employer, institution or
vendor and reflects no organization's business or research. Docs never present
work here as an organization's plan, study, finding or partnership; companies are
mentioned only as their own public sources describe them. See `DISCLAIMER.md`.

### I. Synthetic Only, No PHI (NON-NEGOTIABLE)
Every record in this repo is generated. Real patient data, real notes, and
employer or partner data never enter the repo, a branch, a test fixture, a
prompt example or a log. Synthetic notes carry fake PHI at known positions,
and nothing reaches Label Studio, a model or an LLM endpoint until it passes
de-identification and the leak gate.

**Public datasets (exception, v1.2.0).** A dataset that is already published, already
de-identified by its publisher and licensed for redistribution (e.g. MACCROBAT, CC BY 4.0) may
be committed under `data/external/<name>/`, unchanged or with documented derived files, next to
a README giving source, licence, attribution and changes. It is used as external evaluation
and training data for its own experiments: never mixed into the synthetic sets, never presented
as this project's patient records. Being de-identified by its publisher, it is exempt from the
leak gate above.
Datasets under a data use agreement or a vendor's terms (i2b2/n2c2, the John Snow Labs
benchmark) stay out of the repo.

### II. One Contract, Two Languages
Python (data engineering) and R (data science) read and write the same files
and produce the same numbers. Any computation that feeds a reported result
(labels, scorer, reliability, cost-effectiveness) exists in both languages and
is covered by `r/tests/test_parity.R` to 1e-9. A change to one side lands with
the change to the other.

### III. Test-First
New behavior starts with a failing test (Superpowers `test-driven-development`).
Bugs get a regression test before the fix. `pytest -q` and the R parity test
pass before any commit to `main`.

### IV. Honest Outputs
Simulated anything (reviewers, judge, predictions) is named `simulated_*` or
`sim:` and printed as SIMULATED. Illustrative prices are labelled illustrative.
No invented statistics: every number in docs comes from a run in this repo or a
cited source. Known limits are written down next to the result.

### V. Published Evidence Over Invention
Clinical rules follow the 2017 AAP/EFP classification. Note realism, label
schemas and evaluation design follow published work (cited in
`docs/data_sources.md` and `docs/note_realism.md`). Where we depart from a
source, the spec says why.

### VI. Simple, Reproducible, Seeded
Every generator and sampler takes a seed. Datasets are rebuilt by one script.
No new dependency without a reason in the plan; base R where it's enough.

## Clinical and Data Constraints

- Model output is a flag in `NOTE_NLP`, never a diagnosis in `CONDITION_OCCURRENCE`.
- Reviewers stage charts independently; the answer key is never shown to them.
- The AI model reads notes only; reviewers see every source.
- LLM judges are calibrated against human review before their verdicts are used,
  and must quote the note verbatim.

## Development Workflow

1. **Specify** (`/speckit-specify`) what and why, in `specs/NNN-feature/spec.md`.
   Clarify (`/speckit-clarify`) anything marked NEEDS CLARIFICATION.
2. **Plan** (`/speckit-plan`) and **tasks** (`/speckit-tasks`), with the
   Constitution Check filled in.
3. **Implement** with Superpowers: `brainstorming` for open design questions,
   `writing-plans`/`executing-plans` for the session, `test-driven-development`
   per task, `systematic-debugging` on failures, `verification-before-completion`
   before claiming done, `requesting-code-review` before merge.
4. One feature branch per spec; small commits; PR into `main`.

## Governance

This constitution overrides other practice in the repo. Amend it by PR that
states the change and why, bumps the version, and updates any affected spec.
Reviewers check principle I and II on every PR.

**Version**: 1.2.0 | **Ratified**: 2026-10-25 | **Last Amended**: 2026-10-26
