# How periodontitis is staged and graded here

**Rule source:** AAP, *Staging and Grading Periodontitis* worksheet (2017
AAP/EFP classification) —
[perio.org PDF](https://www.perio.org/wp-content/uploads/2019/08/Staging-and-Grading-Periodontitis.pdf).
Background: Tonetti, Greenwell & Kornman, *J Periodontol* 2018;89(Suppl 1):S159–S172.

Every part of the repo follows this worksheet: the synthetic ground truth,
the rule readers, the reviewer protocol, and the LLM judge and reader prompts.
Change one and you must change them all (table at the end).

## In plain words

| Label | What it means | How it's decided here |
|---|---|---|
| **Healthy** | Gums don't bleed much; no damage to the tooth's support | No attachment loss, no bone loss, bleeding at < 10% of sites |
| **Gingivitis** | Inflamed, bleeding gums. Reversible: cleaning and home care fix it | Bleeding at ≥ 10% of sites, but no attachment or bone loss |
| **Periodontitis** | The gum has detached from the tooth and bone has been lost. Permanent: treatment stops it getting worse, but lost support doesn't grow back | Any interdental attachment loss (CAL ≥ 1 mm), bone loss, or tooth lost to gum disease |

Periodontitis then gets three more labels:

- **Stage (I, II, III, IV): how severe and how hard to treat.** Mostly from the worst
  attachment loss: I is 1–2 mm (early), II is 3–4 mm (moderate), III and IV are 5 mm or more.
  Teeth lost to gum disease and complicating factors (deep pockets, bone defects, loose teeth,
  few teeth left) push it up. Stage IV means the bite itself needs rebuilding.
- **Grade (A, B, C): how fast it's progressing, and how likely to keep going.** A is slow, B
  moderate (the default), C rapid. Judged from bone loss over 5 years when available,
  otherwise from bone loss relative to age (a lot of loss in a young patient means fast).
  Smoking and poorly controlled diabetes raise it.
- **Extent: how much of the mouth is involved.** Localized (fewer than 30% of teeth),
  generalized (30% or more), or a molar/incisor pattern (typical of disease that starts young).

A full label reads like "generalized periodontitis, stage III, grade B".

## Stage

**Not periodontitis:** no interdental attachment loss (CAL < 1 mm; or, if CAL
isn't charted, no radiographic bone loss) and no tooth lost to periodontitis.
BOP ≥ 10% of sites is gingivitis; otherwise healthy.

**Step 1: initial stage from severity.** Interdental CAL at the site of greatest loss.

| | Stage I | Stage II | Stage III | Stage IV |
|---|---|---|---|---|
| Interdental CAL | 1–2 mm | 3–4 mm | ≥ 5 mm | ≥ 5 mm |
| RBL (only if CAL isn't available) | coronal third, < 15% | coronal third, 15–33% | middle third or beyond | middle third or beyond |

**Step 2: tooth loss due to periodontitis.** None for stages I–II; 1–4 teeth means at least
stage III; ≥ 5 teeth means stage IV.

**Step 3: complexity raises the stage** (never lowers it).

| Factor | Effect |
|---|---|
| Max probing depth > 4 mm (stage I allows ≤ 4) | at least stage II |
| Probing depth ≥ 6 mm; vertical bone loss ≥ 3 mm; class II/III furcation; moderate ridge defect | at least stage III |
| At stage III, a need for complex rehabilitation: masticatory dysfunction; secondary occlusal trauma (mobility ≥ degree 2); severe ridge defect; bite collapse, drifting, flaring; < 20 remaining teeth (10 opposing pairs) | stage IV |

## Grade (periodontitis only)

Start at **grade B**, then look for evidence to move it to A or C.

| | Grade A (slow) | Grade B (moderate) | Grade C (rapid) |
|---|---|---|---|
| Direct evidence: RBL or CAL loss over 5 years (use when available) | none | < 2 mm | ≥ 2 mm |
| Indirect evidence: % bone loss ÷ age | < 0.25 | 0.25–1.0 | > 1.0 |
| Case phenotype | heavy biofilm, low destruction | destruction in line with biofilm | destruction beyond what biofilm explains |
| Modifier: smoking | non-smoker | < 10 cigarettes/day | ≥ 10 cigarettes/day |
| Modifier: diabetes | normoglycemic / no diabetes | HbA1c < 7.0% with diabetes | HbA1c ≥ 7.0% with diabetes |

Modifiers only raise the grade.

## Extent

Localized (< 30% of teeth involved), generalized (≥ 30%), or molar/incisor pattern.

## What the code models, and what it doesn't

| Worksheet item | In `labels.py` / `labels.R` | In the synthetic data |
|---|---|---|
| CAL first, RBL only if CAL missing | yes (`max_cal_mm=None` / `NA`) | CAL always charted in the truth; notes and sources can lack it |
| Tooth loss due to perio | yes | yes |
| PD complexity (> 4, ≥ 6 mm) | yes | yes |
| Vertical defect, furcation, mobility, remaining teeth, complex rehabilitation | yes, optional fields | not generated yet (radiograph AI simulates vertical defects and furcation as its own source) |
| Moderate / severe ridge defect, masticatory dysfunction, bite collapse | via `complex_rehab` (stage IV) only | no |
| Grade: start at B | yes (no RBL → B) | RBL always present |
| Grade: direct 5-year evidence | yes (`loss_5yr_mm`) | not generated (visits are drawn independently) |
| Grade: case phenotype | no (judgment call) | no |
| Grade: smoking, diabetes modifiers | yes | yes |
| Extent incl. molar/incisor | yes (`molar_incisor=True`) | localized/generalized only |

## Where the rules live

| Place | What to keep in step |
|---|---|
| `python/dental_omop_nlp/labels.py`, `r/R/labels.R` | ground truth; parity-tested, including 3,456 edge cases (`aap_rule_cases.csv`) |
| `python/tests/test_aap_rules.py` | one test per worksheet rule |
| `docs/labeling_protocol.md`, `labelstudio/chart_review.xml` | what reviewers apply |
| `judge.CRITERIA` (shared by the judge and the MedGemma reader), `databricks/notebooks/02_llm_judge.sql` | what LLMs apply (prompt versions `judge-v2`, `reader-v2`) |

## Change log

- **2026-10-25:** aligned to the AAP worksheet. Before: stage = worse of CAL and
  RBL, no complexity factors, grade had no B default or direct evidence, and
  extent had no molar/incisor pattern. Stage I charts in the generator now keep
  max PD ≤ 4 mm. Datasets rebuilt; the simulated dry-run numbers changed accordingly.
