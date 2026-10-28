# Implementation Plan: case profiles and record-mismatch flags (spec 026)

**Spec**: [spec.md](spec.md) · **Issues**: #234 (US1), #235 (US2), #236 (US3) · **Source**: KEEPER, Schuemie,
Ostropolets et al., npj Digit Med 2025 (`docs/rag_and_vocabulary.md`, R6); stage rules from the 2017 AAP/EFP
classification (as encoded in `labels.py`).

> Synthetic data only. Words per `AGENTS.md`: profiles, record mismatches, records to recheck. Every score is
> measured against the generator's truth and labelled synthetic.

## Technical context

- **Language**: Python 3 (`health_transformation_lab_nlp`), R (base R twin), Databricks AI/BI dashboard and
  Genie JSON built from code (spec 019).
- **Inputs** (built by `scripts/10_build_study.py`, seeded): `data/datasets/visits_structured.csv` (4,343 visits,
  1,200 people; each source's status and the recorded measurements; `notes` is the note reader's status, not
  text) and `answer_key/visits_truth.csv` (`truth_status`; `record_error`: 45 injected chart errors, 28 decimal
  slips and 17 wrong-patient charts).
- **What the data allows** (checked on the built study): completed codes run healthy to stage III, never IV;
  `radiograph_ai` reads only stage II, stage III or unknown (3,410 unknown); `probing_chart` is unknown exactly when
  no chart was taken (906 visits); 34 of the 45 injected-error visits have a completed code.
- **No new dependency.** pandas and base R only.

## Decisions (research)

| Question | Decision | Why | Alternatives |
|---|---|---|---|
| "The recorded code" | `proc_dx_completed` | The study's coded diagnosis; planned codes aren't yet true of the visit, as in the rule phenotypes | Planned codes: shown in the profile, never trigger a rule |
| "Periodontal care" | `proc_codes_completed` or `proc_codes_planned` reads periodontitis | The procedure-code readings already in the study | Raw CDT codes: not in the synthetic tables |
| Status ladder | `labels.LABELS`: healthy 0, gingivitis 1, stage I–IV 2–5 | The order `plausibility` already uses | Five categories (spec 005): hides healthy vs gingivitis |
| "Code higher than the chart" | stage III code, chart within stage I on every staging criterion: CAL < 3 mm, bone loss < 15%, no tooth lost, PD < 6 mm | A stage III chart can have low CAL with teeth lost or PD ≥ 6 (`labels.py`); checking only CAL and bone loss flagged a real stage III chart | CAL and bone loss only (first draft) |
| "Code lower than the chart" | healthy or gingivitis code with CAL ≥ 3 mm or bone loss ≥ 15% | Gingivitis has no attachment or bone loss; beyond stage I is unambiguous. Deep pockets with bleeding fit gingivitis (pseudopockets; > 30% BOP is generalized gingivitis), so the first draft's PD + BOP rule had no source | PD ≥ 5 and BOP > 30% (first draft) |
| Radiograph rule | one direction only | The synthetic radiograph AI never reads healthy or gingivitis | Both directions: the reverse can't fire |
| Stage-drop rule | `plausibility.check_history` on `proc_dx_completed`; reported on the later visit, earlier peak visit in the evidence; a true flag when either code is wrong | A stage never decreases under the 2017 classification; in a prototype about half the drops had the earlier, higher code wrong | Score the later visit only: precision about 0.52 and sends reviewers to the wrong visit |
| Denominators | Per rule over the visits it can check (has a code and its evidence), with that count; "any rule" over every coded visit; injected errors over those the rule can check (ceiling 34/45) | One definition everywhere; checkable counts make low coverage visible (the radiograph rule checks about 680 coded visits) | All visits: hides coverage; all 45 errors: counts the uncheckable |
| Overlap | Report "only this rule" (flags no other rule makes) | A prototype showed the measurement rules' flags all also fail the chart-reading rule; the score should show that | Drop overlapping rules: they still state a clinical reason a reviewer can read |
| Profile shape | Long: one row per (visit, item), the value as a short label plus a unit | Genie and a dashboard table read it directly; `_num` must be bigint, so decimals can't be a numeric gold column | A numeric column (`item_value_num`): breaks the suffix-type rule |
| Profile storage | Built by `grader_tables.dq_tables` from `visits_structured.csv` at load time | The long form is about 113k rows, 6 MB: a second committed copy of the same evidence | A committed CSV (first draft) |
| OMOP | The study's tables, not CDM tables | Same evidence; an OMOP-native build is out of scope | Build from `CONDITION_OCCURRENCE` now |

## Approach

1. **Profiles (US1, built)**: `python/health_transformation_lab_nlp/case_profile.py`.
   - `PROFILE_ITEMS`: ordered (category, item, source column or none, unit) for the nine categories:
     Demographics, Presentation, Visit context, Measurements, Tests and imaging, Risk factors, Treatment, Other
     readings (the note reader's status and both rule phenotypes), After the visit.
   - `build_profiles(visits)`: long frame `visit_id, category, category_order, item, item_order, value, unit`.
     Missing or unknown values read "not recorded"; an uncharted visit's chart reading "not taken"; "after the
     visit" holds the next visit's code and the plausibility flags that visit fails, or "no later visit".
2. **Rules (US2)**: same module.
   - `RULES` with named thresholds and sources: `HIGH_CODE_MAX_CAL_MM = 3`, `HIGH_CODE_RBL_PCT = 15`,
     `HIGH_CODE_MAX_PD_MM = 6` (stage I limits, `labels.py`), `LOW_CODE_CAL_MM = 3`, `LOW_CODE_RBL_PCT = 15`
     (beyond stage I), `CHART_STEPS = 1`.
   - `check_rules(visits)`: one row per (visit, rule): `outcome` in `fail | pass | not_checkable | no_code`, and
     `evidence` with the triggering values (and, for stage drops, the earlier visit).
   - `score_rules(checks, truth)`: per rule and `any_rule`, overall (`clinic = "All"`) and per clinic: checkable,
     flagged, not checkable, code-truth mismatches, true flags, precision, recall, only-this-rule, injected errors
     checkable and caught.
3. **Script**: `python/scripts/45_case_profiles.py` (44 is spec 023's) writes
   `data/datasets/case_profiles/{record_mismatch,mismatch_rule_score}.csv`, prints the score table headed
   SYNTHETIC beside the temporal checks' catch rate, and runs in `make_parity_inputs.sh` after
   `20_data_quality.py`.
4. **R (US2)**: `r/R/15_spec026.R` (13 and 14 are specs 023 and 024) mirrors `check_rules` and `score_rules`;
   `test_parity.R` compares outcomes exactly and scores to 1e-9. Profiles are display, not scoring: no R twin.
5. **Gold (FR-007)**: `grader_tables.dq_tables`, `gold_names`, `diagrams/_build/gold_model.py`:
   - `fact_case_profile_item` (US1, built): `visit_id`, `category_name`, `category_order_num`, `item_name`,
     `item_order_num`, `item_value_name`, `item_unit_name`.
   - `fact_record_mismatch`: one row per visit and failed rule: `visit_id`, `rule_name`, `rule_label_name`,
     `mismatch_evidence_text`, `clinic_code`, `is_injected_error`.
   - `dq_mismatch_rule`: one row per rule and clinic (`All` too), named like the other DQ summaries:
     `checkable_count`, `flagged_count`, `not_checkable_count`, `code_truth_mismatch_count`, `true_flag_count`,
     `precision_ratio`, `recall_ratio`, `only_rule_count`, `injected_checkable_count`, `injected_caught_count`.
   All join `fact_visit_evidence` on `visit_id`; Load results overwrites them (idempotent, `DQ_PROV` provenance).
6. **Dashboard and Genie (US3)**: `dashboards.py`.
   - `dq_grader()` gets a **Records to recheck** page: banner (synthetic; "a mismatch is a coding or charting
     gap, not a clinical error"); the rule-score table with checkable counts; flagged visits by rules failed; a
     visit filter driving the profile table; clinic and rule filters.
   - `DQ_TABLES` adds the mismatch tables (the profile table is in already, US1); `DQ_INSTRUCTIONS` adds the
     rules, the denominators and the Words rule; `DQ_QUESTIONS` adds mismatch questions.
7. **Docs**: `docs/graders.md` (profiles: done; rules and page), `docs/rag_and_vocabulary.md` R6 (done).

## Constitution check

| Principle | Status |
|---|---|
| 0 Not affiliated | Pass: KEEPER cited from its paper; no organization's plan |
| I Synthetic only | Pass: reads the generated study; never note text |
| II Python = R | Pass: flags and scores twinned in `15_spec026.R`, parity-tested; profiles are display only |
| III Test first | Pass: tests below come before code |
| IV Honest outputs | Pass: every output and page says synthetic; thresholds name their source; the injected-error ceiling and the temporal checks' rate are shown beside the rules' |
| V Published evidence | Pass: thresholds from the 2017 classification as `labels.py` encodes it; departures from the first draft recorded above |
| VI Seeded, no new deps | Pass: deterministic over seeded inputs; no dependency |
| Clinical: model output never a diagnosis | Pass: flags are record mismatches; `test_wording.py` |

Re-checked after design: no change.

## Tests first

- `test_case_profile.py` (US1, in): categories in order, units, "not recorded", "not taken", "no later
  visit", the next visit's flags from `check_history`, only statuses and measures, one profile per study visit.
- `test_case_profile.py` (US2):
  - one visit per rule that fails only that rule. Fixtures set the other evidence so no second rule fires: the
    chart reading within one step of the code, a periodontal procedure on file, the radiograph unknown;
  - no chart: `not_checkable` for the chart rules; no code: `no_code` for all; no earlier periodontitis code:
    stage drop `not_checkable`;
  - stage-drop flags equal `check_history`; a drop whose earlier code is the wrong one counts as a true flag;
  - `score_rules` on a hand-worked table: precision, recall and injected errors over checkable visits; "only this
    rule"; "any rule" over every coded visit;
  - on the built study: every rule scored, checkable counts shown.
- `test_grader_tables.py`, `test_gold_model.py`, `test_sql_conventions.py`: the new tables, their columns and
  suffixes.
- `test_dashboards.py`: the page, its datasets reading declared tables only, the Genie instructions (the
  dashboard's and Genie's wording are checked through their instructions, not Genie's answers).
- `test_wording.py`: guards all new text.
- `r/tests/test_parity.R`: outcomes identical, scores to 1e-9.

## Validation (quickstart)

```bash
cd python && pytest -q tests/test_case_profile.py tests/test_grader_tables.py tests/test_dashboards.py
python scripts/10_build_study.py && python scripts/20_data_quality.py && python scripts/45_case_profiles.py
python scripts/42_build_dashboards.py --check
cd .. && python/scripts/make_parity_inputs.sh && Rscript r/tests/test_parity.R
```

Expected: one profile per visit (4,343); a SYNTHETIC rule table with checkable counts, precision, recall and
"only this rule"; the injected-error catch rate against its 34/45 ceiling and beside the temporal checks'; parity
OK; dashboards up to date.

## Environments

None change their settings. The new gold tables reach dev, uat and prod with their next deploy and Load results;
each implementation PR says so.
