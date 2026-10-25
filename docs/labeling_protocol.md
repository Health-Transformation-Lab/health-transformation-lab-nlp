# Chart review protocol (draft v0.1)

For reviewers staging charts in Label Studio. **Draft**: the qualitative review
finalizes it. Every change gets a new version number, and the version is
recorded with the labels.

## What you're doing

Each task is one visit. You see the de-identified chart note and every other
source for that visit. Assign the periodontal status the **whole chart**
supports, following the **AAP staging and grading worksheet**
([PDF](https://www.perio.org/wp-content/uploads/2019/08/Staging-and-Grading-Periodontitis.pdf);
how it's applied here: [staging_grading.md](staging_grading.md)). Work alone: don't discuss
charts with other reviewers until the reliability round is closed.

## Status (required)

| Choose | When |
|--------|------|
| `healthy` | No interdental attachment loss, BOP < 10% of sites |
| `gingivitis` | No interdental attachment loss, BOP ≥ 10% |
| `periodontitis_stage_1` | Interdental CAL 1–2 mm (RBL < 15% if no CAL), no tooth loss due to perio, max PD ≤ 4 mm |
| `periodontitis_stage_2` | CAL 3–4 mm (RBL 15–33% if no CAL), no tooth loss due to perio, max PD ≤ 5 mm |
| `periodontitis_stage_3` | CAL ≥ 5 mm (RBL beyond the coronal third if no CAL), or 1–4 teeth lost to perio, or a stage III complexity factor |
| `periodontitis_stage_4` | Stage III severity plus ≥ 5 teeth lost to perio or a need for complex rehabilitation |
| `cannot_determine` | The chart doesn't support a call. Say why in the comment |

**Staging steps (AAP worksheet):**

1. **Initial stage from interdental CAL** at the site of greatest loss. Use
   radiographic bone loss only if CAL isn't charted.
2. **Tooth loss** due to periodontitis: 1–4 teeth → at least stage III; ≥ 5 → stage IV.
3. **Complexity** can raise the stage, never lower it: PD ≥ 6 mm, vertical bone
   loss ≥ 3 mm, or class II/III furcation → at least III. At stage III, a need
   for complex rehabilitation (mobility ≥ degree 2, < 20 remaining teeth,
   masticatory dysfunction, bite collapse, drifting/flaring, severe ridge
   defect) → IV.

**When sources disagree:**

1. Measured findings (probing chart, radiographic bone loss) outrank a written
   diagnosis. If the note says "Stage II" and the chart shows CAL 6 mm with 40%
   bone loss, stage it III and tick *conflict = yes*.
2. The worst-affected site decides the stage (CAL first, then RBL; see the staging steps).
3. Ignore copied-forward text (marked `-- copied from visit --`). Stage today's visit.
4. Pre-2017 terms: slight ≈ stage I, moderate ≈ stage II, severe/advanced ≈
   stage III (IV if ≥ 5 teeth are documented as lost to perio). AAP Case Type
   I = gingivitis, II = stage I, III = stage II, IV = stage III/IV.
5. Procedure codes support a call but can't stage on their own. SRP (D4341)
   means periodontitis, not a stage.
6. Planned procedures that weren't completed are still evidence of the
   clinician's assessment.

## Grade and extent (periodontitis only, otherwise `NA`)

- **Grade**: start at **B**, then look for evidence to move to A or C.
  1. Direct evidence (RBL or CAL change over 5 years), if the chart has it:
     none → A, < 2 mm → B, ≥ 2 mm → C.
  2. Otherwise % bone loss ÷ age: < 0.25 → A; 0.25–1.0 → B; > 1.0 → C.
  3. Modifiers raise the grade: smoking < 10 cigarettes a day or diabetes with
     HbA1c < 7.0% → at least B; ≥ 10 a day or HbA1c ≥ 7.0% with diabetes → C.
- **Extent**: < 30% of teeth involved → localized; ≥ 30% → generalized; or
  molar/incisor pattern.

## Also record

- **Which sources decided it**: tick every source you relied on.
- **Conflict**: yes if any two sources point to different statuses.
- **Confidence**: 1–5.
- **Evidence spans** (optional, helps train the NER model): highlight the
  diagnosis statement and the findings you used, using the labels on the left.

## Pace

Most charts take 1–3 minutes. If one takes over 5, choose `cannot_determine`,
comment, and move on.
