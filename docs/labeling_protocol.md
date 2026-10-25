# Chart review protocol (draft v0)

For reviewers staging charts in Label Studio. **Draft**: the qualitative review
finalizes it. Every change gets a new version number, and the version is
recorded with the labels.

## What you're doing

Each task is one visit. You see the de-identified chart note and every other
source for that visit. Assign the periodontal status the **whole chart**
supports, using the 2017 AAP/EFP classification. Work alone: don't discuss
charts with other reviewers until the reliability round is closed.

## Status (required)

| Choose | When |
|--------|------|
| `healthy` | No attachment loss, BOP < 10% of sites |
| `gingivitis` | No attachment loss, BOP ≥ 10% |
| `periodontitis_stage_1` | Interdental CAL 1–2 mm, RBL < 15%, no tooth loss due to perio |
| `periodontitis_stage_2` | CAL 3–4 mm, RBL 15–33%, no tooth loss due to perio |
| `periodontitis_stage_3` | CAL ≥ 5 mm, RBL > 33%, ≤ 4 teeth lost due to perio |
| `periodontitis_stage_4` | As stage III, with ≥ 5 teeth lost due to perio |
| `cannot_determine` | The chart doesn't support a call. Say why in the comment |

**When sources disagree:**

1. Measured findings (probing chart, radiographic bone loss) outrank a written
   diagnosis. If the note says "Stage II" and the chart shows CAL 6 mm with 40%
   bone loss, stage it III and tick *conflict = yes*.
2. The worst-affected site decides the stage.
3. Ignore copied-forward text (marked `-- copied from visit --`). Stage today's visit.
4. Pre-2017 terms: slight ≈ stage I, moderate ≈ stage II, severe/advanced ≈
   stage III (IV if ≥ 5 teeth are documented as lost to perio). AAP Case Type
   I = gingivitis, II = stage I, III = stage II, IV = stage III/IV.
5. Procedure codes support a call but can't stage on their own. SRP (D4341)
   means periodontitis, not a stage.
6. Planned procedures that weren't completed are still evidence of the
   clinician's assessment.

## Grade and extent (periodontitis only, otherwise `NA`)

- **Grade**: % bone loss ÷ age < 0.25 → A; 0.25–1.0 → B; > 1.0 → C. Smoking ≥ 10
  cigarettes a day or HbA1c ≥ 7.0 → C. Any smoking or diabetes moves A → B.
- **Extent**: < 30% of teeth involved → localized; ≥ 30% → generalized.

## Also record

- **Which sources decided it**: tick every source you relied on.
- **Conflict**: yes if any two sources point to different statuses.
- **Confidence**: 1–5.
- **Evidence spans** (optional, helps train the NER model): highlight the
  diagnosis statement and the findings you used, using the labels on the left.

## Pace

Most charts take 1–3 minutes. If one takes over 5, choose `cannot_determine`,
comment, and move on.
