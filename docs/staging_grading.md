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
| CAL first, RBL only if CAL missing | yes (`max_cal_mm=None` / `NA`) | CAL always charted in the truth; notes and other evidence can lack it |
| Tooth loss due to perio | yes | yes |
| PD complexity (> 4, ≥ 6 mm) | yes | yes |
| Vertical defect, furcation, mobility, remaining teeth, complex rehabilitation | yes, optional fields | not generated yet (radiograph AI simulates vertical defects and furcation as its own evidence type) |
| Moderate / severe ridge defect, masticatory dysfunction, bite collapse | via `complex_rehab` (stage IV) only | no |
| Grade: start at B | yes (no RBL → B) | RBL always present |
| Grade: direct 5-year evidence | yes (`loss_5yr_mm`) | not generated (visits are drawn independently) |
| Grade: case phenotype | no (judgment call) | no |
| Grade: smoking, diabetes modifiers | yes | yes |
| Extent incl. molar/incisor | yes (`molar_incisor=True`) | localized/generalized only |

## ACES: the same classification for survey and secondary data (spec 013)

The worksheet needs things a survey or an extract often lacks (radiographs, teeth lost to
periodontitis, complexity factors). ACES (Holtfreter et al., J Clin Periodontol 2024;51:512–521,
doi:10.1111/jcpe.13965) turns it into rules that run on site-level charts alone. `aces.py` /
`r/R/12_spec013.R` implement it from the site and tooth tables of spec 006. The primary paper is
not open access, so the rules are as stated by three open papers that apply it: Tay et al. 2025
(NHANES, PMC12176459), Holde et al. 2025 (Norway, PMC12003053), Nafz et al. 2026 (SHIP-TREND,
PMC13263721).

| Step | Rule | Setting where the papers differ |
|---|---|---|
| Teeth | third molars excluded | |
| Case | interproximal CAL ≥ 1 mm at ≥ 2 non-adjacent teeth, or buccal/oral CAL ≥ 3 mm with PD > 3 mm at the same site on ≥ 2 teeth | `buccal_pd_min_mm` (Tay > 3; Holde ≥ 3); `case_cal_min_mm=3` for the stricter "CAL above 2 mm" case (Tokede et al.) |
| Stage | worst interproximal CAL 1–2 mm I, 3–4 mm II, ≥ 5 mm III/IV | |
| Complexity | II → III with PD ≥ 6 mm at ≥ 2 non-adjacent teeth (distal of second molars ignored) | `complexity=False` reports III/IV together |
| III vs IV | < 10 opposing pairs of natural teeth → IV | `stage4_rule`: `opposing_pairs` (Tay, Nafz), `teeth20` (< 20 teeth; Holde), `teeth_lost_perio` (≥ 5 recorded), `all_missing_perio` (every missing tooth counted) |
| Not a case | healthy, or gingivitis with bleeding ≥ 10% of sites | ACES threshold not confirmed from the primary paper |
| Other | edentulous; non-classified when fewer than two non-adjacent teeth can be assessed; extent generalized at ≥ 30% of teeth | |

Furcation, vertical bone loss and mobility are ACES complexity factors too, but their thresholds and
place in the tree are not stated in the open papers, so they are not used yet. `22_build_sites.py`
reports ACES and its variants next to the 2017 worksheet and CDC/AAP 2012 for every synthetic exam
(`data/sites/derived.csv`, `aap_vs_aces.csv`).

## Where the rules live

| Place | What to keep in step |
|---|---|
| `python/dental_omop_nlp/labels.py`, `r/R/labels.R` | ground truth; parity-tested, including 3,456 edge cases (`aap_rule_cases.csv`) |
| `python/tests/test_aap_rules.py` | one test per worksheet rule |
| `python/dental_omop_nlp/aces.py`, `r/R/12_spec013.R`, `python/tests/test_aces.py` | ACES and its variants; parity-tested on 200 exams × 4 variants |
| `docs/labeling_protocol.md`, `labelstudio/chart_review.xml` | what reviewers apply |
| `judge.CRITERIA` (shared by the judge and the MedGemma reader), `databricks/notebooks/02_llm_judge.sql` | what LLMs apply (prompt versions `judge-v2`, `reader-v2`) |

## Change log

- **2026-10-25:** aligned to the AAP worksheet. Before: stage = worse of CAL and
  RBL, no complexity factors, grade had no B default or direct evidence, and
  extent had no molar/incisor pattern. Stage I charts in the generator now keep
  max PD ≤ 4 mm. Datasets rebuilt; the simulated dry-run numbers changed accordingly.
