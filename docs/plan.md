# Plan

Goal: phenotype periodontal status from a dental EHR, compare seven sources,
derive a rule-based algorithm, and test whether a BERT-family model reading
the notes performs like clinicians reviewing the full chart. Built in public on
synthetic data until approved for internal use. Databricks is the eventual home.

**Target dates:** notes analysed by **January 7, 2027**; manuscript submitted
in **February 2027**.

## Built

- [x] Seven sources per visit, generated with realistic disagreement:
      notes (four diagnosis schemes, numbers or descriptors, copy-forward),
      exam forms (PSR), CDT codes completed/planned, ICD-10 diagnoses
      completed/planned, probing chart (present at ~80% of visits)
- [x] Fake PHI in every note at known positions; de-identification with a
      dental allowlist; leak gate; recall measured to the character
- [x] Readers for every source; pairwise method agreement and coverage
- [x] Placeholder rule-based algorithm (`RULES_V0`)
- [x] Datasets: train (~2,400 notes), review (240 charts as Label Studio
      tasks), answer key
- [x] Label Studio config, export import, simulated reviewers for dry runs
- [x] Reliability (Fleiss' kappa, pairwise and weighted kappa, consensus,
      each method vs reviewers) in Python and R, parity-tested
- [x] AI models: note rules, TF-IDF (run); 12 BERT-family encoders (registry,
      fine-tune code written, not yet run)
- [x] Design-review page for the Databricks RSA
- [x] Cost-effectiveness at 1M+ notes: LLM judge (quote gate, OpenAI-compatible
      or `ai_query` backend), judge calibration on the reviewed charts,
      Rogan-Gladen corrected accuracy with bootstrap CI, cost per 1M notes,
      dominance and ICER; Python and R parity-tested ([cost_effectiveness.md](cost_effectiveness.md))

## What the dry run shows (synthetic, simulated reviewers; not results)

- Sources disagree as designed. Against the probing chart: notes κ 0.75,
  exam form 0.68, procedure codes ~0.60, diagnosis codes 0.55–0.79.
- With four simulated reviewers, Fleiss' κ 0.69 and consensus on 95% of charts.
- The rule-based placeholder tracks the probing chart because it trusts it
  first; that's a choice for the qualitative review to confirm or change.
- Note rules and TF-IDF are equal at κ ~0.82 against consensus. On synthetic
  notes there's little room for BERT to win; real notes are the test.

## Timeline (working back from January 7)

| Weeks | Dates | Work | Done when |
|------:|-------|------|-----------|
| 1–2 | Oct 26 – Nov 6 | RSA design review; submit data-access / IRB determination; finalize protocol draft with the qualitative reviewers | approval request filed; RSA answers to questions 1–5 |
| 3–4 | Nov 9 – Nov 20 | Real extract into the restricted zone; run de-id on a 100-note sample; human check of the sample; fix allowlist | zero PHI found in the sample review |
| 4–6 | Nov 16 – Dec 4 | Qualitative review: two reviewers go through disagreeing charts (from `method_agreement.csv`); write `RULES_V1` and protocol v1 | rules and protocol versioned |
| 6–8 | Dec 7 – Dec 23 | Reliability round: N reviewers stage the same 240 charts in Label Studio. In parallel: fine-tune the encoder ladder on de-identified training notes; measure throughput on target hardware; set real prices in `costs.yaml` | all reviewers finished; AI predictions written |
| 8–9 | Dec 21 – Jan 1 | Run every method over the 1M+ notes; judge a stratified sample per method (~1,500 each); calibrate the judge on the reviewed charts | judgments and calibration written |
| 9–10 | Dec 28 – Jan 7 | Analysis: reliability, methods vs reviewers, AI vs reviewers, cost-effectiveness frontier, error review; tables and figures in R | **notes analysed** |
| 11–15 | Jan 8 – Feb | Write-up, co-author review, submit | **submitted** |

## Risks to the dates

1. **Data approval** is the critical path. If real notes aren't in the
   restricted zone by about Nov 20, the reliability round slips past the holidays.
2. **Reviewer time in December.** 240 charts at 1–3 minutes each is 4–12 hours
   per reviewer. Book it now.
3. **De-identification on real notes.** The regex engine is tuned to synthetic
   formats. Real notes need Presidio or a de-id model plus a human sample
   check. Budget a fix-and-rerun cycle.
4. **GPU for the encoder ladder.** CPU is fine for the small models. The large
   ones need GPU or get dropped from the paper.
5. **Holiday weeks** (Nov 23–27, Dec 24 – Jan 1) are already left out above.

## Open decisions

- Judge model and endpoint (a different family from any LLM being judged), and whether the judge may see de-identified notes on a pay-per-token endpoint
- Whether cost-effectiveness reports compute only or includes labeling and engineering time (recommend both)
- Number of reviewers for the reliability round (3–5), and who they are
- Whether the AI model trains on chart truth or on the clinician's written diagnosis (both columns are in `train.csv`)
- Label Studio hosting inside the boundary vs a Databricks-native labeling option (RSA question 3)
- R owner (README names them)
- A 13th candidate model was added after the sheet; name to be confirmed
