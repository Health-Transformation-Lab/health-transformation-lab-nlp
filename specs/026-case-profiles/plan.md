# Implementation Plan: case profiles and record-mismatch flags (spec 026)

**Spec**: [spec.md](spec.md) · **Issues**: #234 (US1), #235 (US2), #236 (US3) · **Source**: KEEPER, Schuemie,
Ostropolets et al., npj Digit Med 2025 (`docs/rag_and_vocabulary.md`, R6); stage rules from the 2017 AAP/EFP
classification.

> Synthetic data only. Words per `AGENTS.md`: profiles, record mismatches, records to recheck; never a wrong
> diagnosis. Every score is measured against the generator's truth and labelled synthetic.

## Technical context

- **Language**: Python 3 (`health_transformation_lab_nlp`), R (base R twin), Databricks AI/BI dashboard and
  Genie JSON built from code (spec 019).
- **Inputs** (already built by `scripts/10_build_study.py`, seeded): `data/datasets/visits_structured.csv`
  (4,343 visits, 1,200 people; each source's status and the recorded measurements) and
  `answer_key/visits_truth.csv` (`truth_status`, `record_error`: 45 injected measurement errors).
- **No new dependency.** pandas and base R only.
- **Storage**: CSVs under `data/datasets/case_profiles/`, loaded to `gold_perio_bench` by Load results.
- **Scale**: about 4,300 visits × about 30 items; seconds to build.

## Decisions (research)

| Question | Decision | Why | Alternatives |
|---|---|---|---|
| Which column is "the recorded code"? | `proc_dx_completed` (status from the diagnosis codes on completed procedures) | It is the study's coded diagnosis; planned codes aren't yet true of the visit, matching the rule phenotypes | Also planned codes: shown in the profile, never trigger a rule |
| "Periodontal care" | `proc_codes_completed` or `proc_codes_planned` reads periodontitis (a periodontal procedure was billed) | These are the procedure-code readings already in the study | Parsing raw CDT codes: not in the synthetic tables |
| Status ladder for "steps apart" | healthy 0, gingivitis 1, stage I–IV 2–5 (`plausibility.LABELS`) | Same order the plausibility checks use | Five categories (spec 005): hides healthy vs gingivitis |
| Stage-drop rule | Reuse `plausibility.check_history` on `proc_dx_completed`: `stage_drop` or `perio_resolved` at the later visit | One definition of a drop in the repo; stage never decreases under the 2017 classification, so treatment doesn't excuse it | A new rule with a treatment exemption: contradicts the classification (spec updated) |
| "Truly wrong" | `proc_dx_completed` ≠ `truth_status`, on visits with a code | The question the flags answer: does the recorded code fit the patient? | Agreement with the review panel: only 240 visits |
| Precision and recall | Per rule, over the visits it can check; plus "any rule" over all coded visits | Spec edge cases: not-checkable visits count in neither; counts are shown | Treating not-checkable as pass: inflates precision |
| Injected errors | Share of the 45 `record_error` visits that fail any rule, and per rule | They corrupt the chart, so a mismatch with the code is how they surface | Score only against code errors: misses them |
| Profile shape | Long: one row per (visit, category, item) with a text value and, where numeric, a number | Genie and a dashboard table read it directly; new items need no schema change | Wide table: 30+ columns, changes with every item |
| OMOP | Read the study's tables, not CDM tables | Same evidence; OMOP-native build is out of scope (spec Assumptions) | Build from `CONDITION_OCCURRENCE`/`MEASUREMENT` now |

## Approach

1. **Profiles (US1)**: new `python/health_transformation_lab_nlp/case_profile.py`.
   - `PROFILE_ITEMS`: an ordered table of (category, item name, source column, unit), the nine categories in
     the spec. One place to add an item.
   - `build_profiles(visits, truth) -> DataFrame` (long form): `visit_id`, `category`, `category_order`,
     `item`, `item_order`, `value_text`, `value_num`. Missing values become `"not recorded"` with
     `value_num` null; `"unknown"` statuses read `"not recorded"`. "Other readings" holds the note reader and
     both rule phenotypes. "After the visit" holds the next visit's code and the plausibility flags it fails,
     or `"no later visit"`.
   - Never reads `notes` (a test asserts the column is never touched and no value matches a note).
2. **Rules (US2)**: same module.
   - `RULES`: name, plain label, needs (columns), and named thresholds with sources:
     `HIGH_CODE_MAX_CAL_MM = 3`, `HIGH_CODE_RBL_PCT = 15` (2017: within stage I, CAL 1–2 mm and bone loss < 15%);
     `LOW_CODE_PD_MM = 5` (2017: deeper than stage I's 4 mm), `LOW_CODE_BOP_PCT = 30` (generalized gingivitis,
     > 30%, Patel 2022 Fig. 2);
     `CHART_STEPS = 1`.
   - `check_rules(visits) -> DataFrame`: one row per (visit, rule) with `outcome` in
     `fail | pass | not_checkable | no_code` and the triggering values as text.
   - `score_rules(checks, truth, by=None) -> DataFrame`: per rule (and `any_rule`), overall and per clinic:
     checked, flagged, not checkable, truly wrong, true flags, precision, recall, injected errors caught.
3. **Script**: `python/scripts/45_case_profiles.py` (44 is spec 023's) writes
   `data/datasets/case_profiles/{case_profile_item,record_mismatch,mismatch_rule_score}.csv`, prints the rule
   table labelled SYNTHETIC, and is added to `make_parity_inputs.sh` after `20_data_quality.py`.
4. **R (US2)**: `r/R/15_spec026.R` (13 and 14 are specs 023 and 024) mirrors `check_rules` and `score_rules`;
   `test_parity.R` compares flags exactly and scores to 1e-9. Profiles are formatting, not scoring, so they have
   no R twin.
5. **Gold (FR-007)**: `grader_tables.dq_tables` adds three tables; `gold_names` maps their columns;
   `diagrams/_build/gold_model.py` declares them (grain in the comment, `DQ_PROV` provenance):
   - `fact_case_profile_item`: one row per visit, category and item (`visit_id`, `category_name`,
     `category_order_num`, `item_name`, `item_order_num`, `item_value_text`, `item_value_num`).
   - `fact_record_mismatch`: one row per visit and failed rule (`visit_id`, `rule_name`, `rule_label_name`,
     `mismatch_evidence_text`, `clinic_code`, `is_injected_error`), failed rules only.
   - `mismatch_rule_score`: one row per rule and clinic (`rule_name`, `clinic_code` with `All`,
     `checked_count`, `flagged_count`, `not_checkable_count`, `wrong_code_count`, `true_flag_count`,
     `precision_ratio`, `recall_ratio`, `injected_error_count`, `injected_caught_count`).
   Load results overwrites each from its CSVs, as for the other DQ tables (idempotent; `file_sha256`,
   `loaded_ts`, `git_commit_sha` on every row).
6. **Dashboard and Genie (US3)**: `dashboards.py`.
   - `dq_grader()` gets a second page, **Records to recheck**: a banner (synthetic, "a mismatch is a coding or
     charting gap, not a clinical error"); a rule-score table; a flagged-visit table ordered by rules failed;
     a visit filter driving a profile table grouped by category; clinic and rule filters.
   - `DQ_TABLES` adds the three tables; `DQ_INSTRUCTIONS` adds the Words rule and the synthetic label;
     `DQ_QUESTIONS` adds three sample questions. Rebuilt with `scripts/42_build_dashboards.py`.
7. **Docs**: `docs/graders.md` (the new page), `docs/gold_tables.md` (three tables), R6 in
   `docs/rag_and_vocabulary.md` notes the profile now exists.

## Constitution check

| Principle | Status |
|---|---|
| 0 Not affiliated | Pass: KEEPER cited from its paper; no organization's plan |
| I Synthetic only | Pass: reads the generated study; never note text |
| II Python = R | Pass: flags and scores twinned in `15_spec026.R`, parity-tested; profiles are display only |
| III Test first | Pass: tests below come before code |
| IV Honest outputs | Pass: every output and page says synthetic; thresholds name their source |
| V Published evidence | Pass: thresholds from the 2017 classification; the stage-drop departure from the user's wording is recorded in the spec |
| VI Seeded, no new deps | Pass: deterministic over seeded inputs; no dependency |
| Clinical: model output never a diagnosis | Pass: flags are record mismatches; Words rule and `test_wording.py` |

Re-checked after design: no change.

## Tests first

- `test_case_profile.py` (new):
  - hand-built visits: every category present; missing values "not recorded"; last visit "no later visit";
    `unknown` statuses read "not recorded"; no note text in any value;
  - one visit per rule that fails exactly that rule; a visit with no chart is `not_checkable` for chart rules;
    a visit with no code is `no_code` for all;
  - stage drop matches `plausibility.check_history` on the same history;
  - `score_rules` on a hand-worked table: precision, recall, not-checkable excluded, injected errors caught;
  - on the built study: one profile per visit, every rule scored.
- `test_grader_tables.py`: the three tables appear with provenance; `test_gold_names.py` and
  `test_sql_conventions.py`: every new column has a gold name with a legal suffix.
- `test_dashboards.py`: the page exists, its datasets read only declared gold tables; `--check` clean.
- `test_wording.py`: already guards the new text.
- `r/tests/test_parity.R`: flags identical, scores to 1e-9.

## Validation (quickstart)

```bash
cd python && pytest -q tests/test_case_profile.py
python scripts/10_build_study.py && python scripts/20_data_quality.py && python scripts/45_case_profiles.py
python scripts/42_build_dashboards.py --check
cd .. && python/scripts/make_parity_inputs.sh && Rscript r/tests/test_parity.R
```

Expected: one profile per visit (4,343); a SYNTHETIC rule table with precision, recall and not-checkable per
rule and the injected-error catch rate; parity OK; dashboards up to date.

## Environments

None change their settings. The three gold tables reach dev, uat and prod with their next Load results and
deploy; each implementation PR says so.
