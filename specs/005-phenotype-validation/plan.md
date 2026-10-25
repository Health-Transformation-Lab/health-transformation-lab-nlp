# Plan: integrated phenotype and validation extensions

## Constitution check
| Principle | How |
|---|---|
| 0 Not affiliated | Generic wording; differences tracked as action items, no internal documents quoted |
| I Synthetic only | All new data generated; injected errors labelled |
| II Two languages | R twins for 5-category collapse, plausibility flags, prevalence/Wilson CI (parity). Order search, DQ and prediction are Python-only for now (action item) |
| III Test-first | tests per module before code |
| IV Honest | simulated reviewers / placeholders labelled; NHANES comparison caveated |
| V Published evidence | AAP rules; NHANES via NIDCR/Eke 2018; OHDSI DQ terms |
| VI Seeded | histories, clinics, errors, splits seeded |

## Design
- `synthetic.draw_history(age, n, risk, rng)`: baseline chart then 6-monthly steps.
- `study.generate_visits`: clinic per person; history per person; injected errors; `treated_before`.
- `phenotype.py`: `RULES_DESIGN`, `collapse5`, `phenotype(row, rules)`.
- `plausibility.py`, `prevalence.py`, `dq.py`, `prediction.py`; scripts 18–21.
- R: `r/R/06_validation.R` twins; parity sections.
