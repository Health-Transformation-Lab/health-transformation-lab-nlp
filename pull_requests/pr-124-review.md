---
pr: 124
branch: docs/119-gold-diagrams
title: "Gold-layer ERDs and reference architecture, generated from one declaration"
author: jcbowyer
reviewed_at: 2026-10-28
reviewer: independent reviewer subagent (read-only) + coordinator verification
verdict: approve
---

# PR Review: Gold-layer ERDs and reference architecture, generated from one declaration

## Summary
Adds one declaration of the 9 gold tables (`diagrams/_build/gold_model.py`), generators for the entity and full
ERDs, Mermaid sources and `diagrams/gold/data_model.md`, logical and physical architecture diagrams on the
Databricks reference-architecture frame, a PNG renderer and `docs/gold_tables.md`. The review found no Critical
issues. It found two Important errors in what the ERD claims about the results tables, plus eight Minor ones;
all were verified against the code and fixed in the follow-up commit on this branch. Verdict: approve.

## Scope of Change
- Files changed: 30 (diagrams, docs, one test; PNGs and `.drawio` are generated)
- Areas touched: diagrams / docs / python tests
- Commits: 24eed40 Add gold-layer ERDs (draw.io) and a gold table reference; 69cc917 Redo the gold diagrams the
  DE_Assessment way; plus the review-fix commit
- Range reviewed: `0ec3284..69cc917`, then the fix commit

## CI Status
| Check | Status |
|---|---|
| check (PR conventions) | pass |
| python | pass on 69cc917 |
| postgres | pass |
| r-parity | pass on 69cc917 |
| bundle | pass |
| azure-infra | pass |

## Secrets, PHI and Claims Scan
- Secrets: clean (strict credential patterns over the whole diff, including `.drawio`).
- PHI / real data: clean; no file under `data/` changed.
- Organization claims: clean; Databricks is named only for its reference-architecture layout and product icons.

## Strengths
- One declaration drives the ERDs, Mermaid and `data_model.md`; output is deterministic (reproduced byte for byte).
- Drift tests compare the declaration with the real writers (`results_store.run_rows`, `result_files`) and the CSV twins.
- The two-writer conflict on `judgments` is flagged plainly.
- PNGs embed their draw.io XML, so they reopen as editable diagrams.

## Findings
### 🔴 Blocking (Critical)
None.

### 🟡 Should fix (Important, non-blocking): fixed
1. `gold_model.py` drew `result_files ||--o{ ai_predictions / llm_reader_runs`. The reader job's rows
   (`source = databricks`) carry their scratch CSV's `sha256` but have no `result_files` row: `10_load_results.py`
   adds those hashes to `loaded` and skips them. As a result, the "latest version" query in `gold_tables.md` drops
   reader runs. Verified in `10_load_results.py` lines 60-67; two reader runs with the same answers share a
   `sha256`, because `ai_predictions_medgemma*.csv` holds only `visit_id,pred`. **Fixed:** the link is optional
   (`|o--o{`); the keys are described per row kind; the doc says to pick reader rows by `run_id`.
2. "`llm_reader_runs` matches `ai_predictions` one to one" fails once a file changes: old versions' rows stay,
   and the two files have different `sha256` values. **Fixed:** `}o..o{`, and the doc says the match holds within
   one version or one run.

### 🔵 Nits / suggestions (Minor): fixed
3. `run_ts` description: Load results also sets it on `llm_reader_runs` rows (`10_load_results.py`). Fixed.
4. `result_files` write mode is delete-then-append by `sha256`, not plain append (`append()` deletes first). Fixed
   in the model and doc.
5. `test_gold_model.py` checked one `llm_details_*.csv`; now it loops over all of them.
6. `gold_architecture.py`: the dashboard path is `databricks/dashboards/scorecard.lvdash.json`. Fixed.
7. `drawio_render.js`: documents the Node 20.15+ requirement (`zlib.crc32`), caps the scale on the longer side,
   and fails with a clear message when the viewer draws nothing.
8. `gold_tables.md` cautions: added that `encoder_gpu_predictions` is written by plain append with no batch key
   (`08_encoder_gpu.py`; predates this PR).
9. `gold_tables.md` cautions: if `02` wrote `judgments` last, the scorecard's resume fails (it reads `endpoint`).
   Earlier calls are kept only for the same endpoint and prompt version. Both added.
10. Ruff ISC004 and PERF102 in `gold_erd.py`: fixed.

## Repo-Rule Compliance
| Rule | Pass? | Notes |
|---|---|---|
| No secrets | yes | scan clean |
| Synthetic only, no PHI | yes | no data files |
| No organization claims; vendors cited | yes | product names only |
| Test first | partly | the model and its test came in the same commit; order can't be shown |
| Python and R in parity | n/a | no labels, scoring, reliability or cost changes |
| Simulated is labelled simulated | yes | the `judgments.simulated` caution |
| Seeds fixed | yes | layout search seeded (7) |
| Paths | n/a | |
| Spec for big changes | n/a | docs and diagrams only |
| Commits | yes | imperative subjects, why in the body, co-author trailer |
| Docs | yes | README untouched; diagrams README and results_storage link the new page |
| Idempotent writes | n/a | no writes; existing non-idempotent `encoder_gpu_predictions` noted |

## Test Coverage
`test_gold_model.py` checks the declaration against the CSV twins, `results_store.result_files` / `run_rows`, every
`llm_details_*.csv`, and that relationships join declared columns. Run locally: `cd python && pytest -q tests`,
656 passed, 14 skipped. Generators re-run: identical `.drawio` output. Not checked against a live workspace.

## Verdict
approve: the Important and Minor findings are fixed on the branch.
