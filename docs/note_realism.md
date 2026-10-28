# How the synthetic notes are made realistic

Spec: [specs/001-realistic-dental-notes](../specs/001-realistic-dental-notes/spec.md).

The generator's `ehr` style (63% of notes) writes the diagnosis line from a
catalogue of forms reported for real dental notes. The other three styles
(`soap`, `narrative`, `chart_summary`) stay for variety. Every published
pattern is re-composed from parts; no published sentence is copied into the data.

## Published sources

| Tag | Source | What it tells us |
|-----|--------|------------------|
| UTH-RE | Chuang et al., *Extracting periodontitis diagnosis in clinical notes with RoBERTa and regular expression*, [arXiv 2311.10809](https://arxiv.org/abs/2311.10809). UTHealth Houston, 8,125 notes, 5,495 patients, 2021 | Diagnosis lines start with `d` or `diagnosis` and `:` or `-` with uneven spacing; lowercase; stage as Roman or Arabic; grade sometimes with a trailing period; hedges ("tentative diagnosis is"); extent before or after stage/grade; typos of generalized/localized; 98.7% of records have a diagnosis section |
| UTH-AI | Chuang et al., *Artificial Intelligence in Extracting Diagnostic Data from Dental Records*, [arXiv 2407.21050](https://arxiv.org/abs/2407.21050v3) | Diagnosis can start a sentence with no prefix ("Generalized Stage 3 Grade B"); a second extent word for another finding ("…Stage I Grade A with Generalized Recession") made a model read the wrong extent |
| AAP17 | 2017 AAP/EFP classification | Wording for health and gingivitis ("clinical gingival health on an intact periodontium", "dental biofilm-induced gingivitis") |
| AAP99 | 1999 AAP classification | "slight/moderate/severe chronic periodontitis", still seen in older or copied-forward notes |
| Patel 2020 | Patel J.S., PhD dissertation, IUPUI | Charting-derived and clinician-written diagnoses agreed 47% of the time; charting present for ~80% of patients |
| COMMON | Common dental charting practice (not a published corpus) | Body sections and abbreviations: CC, MHx, BP, perio charting, rads (4BWX, FMX, PA, PAN), tx, OHI, NV |

## Pattern catalogue

From `python/health_transformation_lab_nlp/dx_patterns.py`. Weights are relative within the
patterns that apply to a visit's status.

| Pattern id | Source | Shape (illustrative, generated) | Weight |
|------------|--------|----------------------------------|-------:|
| `d_ext_stage_grade_label` | UTH-RE | `d: localized stage ii grade b periodontitis.` | 3.0 |
| `d_ext_label_stage_grade` | UTH-RE | `d- generalized periodontitis, stage 3 grade c` | 2.5 |
| `d_hedge_stage_grade_ext` | UTH-RE | `d: tentative diagnosis is stage 2 grade b localized` | 1.0 |
| `d_stage_grade_label` | UTH-RE | `d- stage iv grade c periodontitis.` | 1.5 |
| `misspelled_extent` | UTH-RE | `d: generalzied periodontitis stage 3 grade b` | 0.8 |
| `grade_roman` | UTH-RE | `d: stage ii grade ii periodontitis, localized` | 0.6 |
| `title_case_diagnosis` | UTH-AI | `Diagnosis: Generalized Periodontitis Stage III Grade B` | 1.5 |
| `extent_then_trap` | UTH-AI | `Diagnosis: Localized Periodontitis Stage I Grade A with Generalized Recession.` | 0.8 |
| `bare_sentence_start` | UTH-AI | `Localized Stage 2 Grade B` | 0.8 |
| `pre2017_severity` | AAP99 | `d: generalized moderate chronic periodontitis` | 0.6 |
| `dx_abbreviated` | COMMON | `Dx: Gen. perio St III Gr B` | 0.6 |
| `gingivitis_plaque_induced` | UTH-RE | `d : generalized plaque induced gingivitis` | 2.0 |
| `gingivitis_2017` | AAP17 | `Diagnosis: Dental biofilm-induced gingivitis on an intact periodontium` | 1.0 |
| `health_lower` | AAP17 | `d: periodontal health on intact periodontium` | 2.0 |
| `health_title` | AAP17 | `Diagnosis: Clinical Gingival Health on an Intact Periodontium` | 1.0 |
| `none` | UTH-RE | no diagnosis line (1.5% of `ehr` notes, from the 98.7% rate) | — |

About 15% of UTH-RE-style lines are written in capitals, as some sites do.

On top of the diagnosis line, all styles keep the earlier realism: the
clinician's written status is one step off the chart in 25% of visits (Patel
2020 found low agreement), the probing chart is missing at ~20% of visits, and
copied-forward text from a prior visit appears in some notes.

## Example (generated, fake PHI already removed)

```
Pt [NAME] ([ID])
DOS: [DATE]  Provider: Dr. [NAME]

CC: pt here for comp exam
MHx reviewed, no changes. Med hx: HTN controlled; smoker ~1 cig/day. BP 136/91.
perio charting done: severe attachment loss, heavy BOP, missing #2, #14, #15, #30 (hx perio ext), deep pockets posterior sextants.
rads: PAN reviewed; severe horizontal bone loss, vertical defect #14.
Dx: Gen. perio St III Gr B
tx: SRP 4 quads; perio consult for surgical eval. OHI given. pt tolerated tx well.
NV: perio consult
```

## What changed in the numbers (dry run, synthetic)

- The note-rules reader reads the written diagnosis correctly on 100% of
  `ehr` review notes with a diagnosis line (141 notes), across every pattern.
  That's after two fixes the published forms forced: extent words that
  describe another finding are skipped, and an explicit stage is taken as
  written instead of being upgraded on tooth loss.
- TF-IDF accuracy on the corpus sample (judge-estimated, simulated judge) fell
  from about 0.94 to 0.89 with the new notes. They are harder, as intended.

## Limits

- All patterns come from one institution (UTHealth Houston). Other dental
  schools and private practices write differently.
- Weights are a guess. Once a de-identified real sample is approved, profile
  it and retune (spec 001, task T016).
- The note body follows common charting practice, not a published corpus.
  A dental clinician should rate 20 notes for plausibility (task T012).
- The readers were tuned on these same patterns, so they still have an
  advantage on synthetic notes. Real notes and an independently written
  synthetic set ([data_sources.md](data_sources.md)) remain the fair tests.
