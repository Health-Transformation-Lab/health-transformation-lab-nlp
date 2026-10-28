# Structured radiograph findings (exploratory)

> **Personal learning project; exploratory, for learning and training.** This
> explores what a possible proof of concept *could* look like if structured
> radiograph AI output were added to periodontal phenotyping. It uses simulated
> data and public information only. It is not affiliated with or endorsed by
> Overjet or any other organization,
> does not reflect any organization's business, research or partnership work,
> is not an integration with any vendor, uses no vendor data, files or APIs,
> and implies no agreement to build one. See [DISCLAIMER](../DISCLAIMER.md).

Spec: [specs/003-radiograph-structured-data](../specs/003-radiograph-structured-data/spec.md).

## Why radiographs

Radiographic bone loss (RBL) is one of the three severity criteria for staging
periodontitis (with interdental attachment loss and tooth loss), and % RBL ÷
age sets the grade (2017 AAP/EFP). A note may not state the diagnosis; a
radiograph AI's measurements can still show how much bone has been lost.

## Public context

As described in each organization's own public materials (cited); included only
to explain why radiograph-derived data is a natural thing to explore.

- **Overjet** offers radiograph AI that measures alveolar bone level, the
  CEJ-to-bone-crest distance in millimetres at each site, under FDA 510(k)
  K210187 ([Overjet](https://www.overjet.com/blog/how-to-detect-periodontal-disease-with-ai)).
  It also describes an AI-powered Oral Health Score for tracking outcomes over
  time ([Overjet, June 2025](https://www.overjet.com/blog/the-new-era-of-oral-healthcare-abundance-trust-and-outcomespowered-by-ai)).
- **Research CNNs on bitewings** detect horizontal bone loss well but miss
  vertical defects; calculus and furcation detection reported at sensitivity
  0.82 and precision 0.66 (Yavuz et al., EuroPerio10, 2022;
  [Dental Tribune](https://www.dental-tribune.com/news/artificial-intelligence-shows-promise-for-detecting-periodontal-status-in-bitewing-radiographs/)).

## What the exploration does

| Piece | What it does |
|-------|--------------|
| `radiograph.py` | Simulates generic radiograph AI output per visit (per-tooth CEJ-crest mm, % RBL, vertical defects, furcation, calculus, missing teeth). Error rates are planning assumptions |
| Reader | Bone loss as a **lower bound** on stage: II or III only; never stage IV (cause of tooth loss isn't visible), never health vs gingivitis |
| Eighth evidence type | Compared with the other seven in method agreement and reviewer reliability; shown to reviewers in Label Studio |
| Rule-based algorithm v0.1 | When the probing chart is missing, raises the stage if the radiograph shows more bone loss |
| `fusion_tfidf_rad` | Note text plus radiograph features in one model |

The schema is vendor-neutral. Any tool that reports per-site bone level could
be mapped to it through a small adapter.

## What the dry run shows (synthetic, simulated reviewers; not a result)

| | Text only (TF-IDF) | Text + radiograph |
|---|---:|---:|
| Agreement with reviewer consensus (review charts) | 0.86 | 0.92 |
| Unsafe error rate (S1+S2) | 0.135 | 0.058 |

- The radiograph alone is weak evidence: it gives a status at 36% of visits
  (no image, or no measurable bone loss) and agrees with reviewers 63% of the
  time when it does. It helps as an *input*, not as a standalone answer.
- The rule-based algorithm barely changes (it already trusts the probing
  chart), with slightly fewer unsafe errors.
- **Open question:** the judge-estimated accuracy on the corpus sample ranks
  the fusion model *below* text-only (0.86 vs 0.92), the opposite of the
  review-set result. That has to be explained before anything is concluded.

## If this ever moved past exploration

- Any real use would need the appropriate agreements and approvals, and the
  vendor's actual export format and validation figures.
- Only structured output, never images: DICOM files carry patient identifiers
  in headers and pixels.
- Structured output goes through the same de-identification gate as notes.
