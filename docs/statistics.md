# Statistics used here: kappa and confidence intervals

Plain-language notes on the two numbers that appear in most results tables.

## Kappa: agreement beyond chance

Kappa measures how well two raters (or a rater and a model, or two data
sources) agree, after removing the agreement you'd expect by luck.

Percent agreement alone misleads when one answer is common. If 90% of charts
are periodontitis and two reviewers both say "periodontitis" most of the time,
they'll agree roughly 80% of the time without really reading the charts.

```
kappa = (observed agreement − chance agreement) / (1 − chance agreement)
```

| Kappa | Meaning |
|-------|---------|
| 1 | Perfect agreement |
| 0 | No better than chance |
| < 0 | Worse than chance |

Common rule of thumb (Landis & Koch, 1977): 0.41–0.60 moderate, 0.61–0.80
substantial, above 0.80 almost perfect. A convention, not a law.

### The three kinds used here

| Kind | When | Where in the code |
|------|------|-------------------|
| **Cohen's kappa** | Two raters: a reviewer vs the AI model, one source vs another (e.g. notes vs probing chart), the judge vs human verdicts | `phenotype.cohen_kappa` |
| **Fleiss' kappa** | Many reviewers staging the same charts (quantitative validation) | `reliability.fleiss_kappa` |
| **Weighted kappa** | Ordered categories (healthy → gingivitis → stage I–IV): calling stage III "stage II" is a small miss, calling it "healthy" a big one. Quadratic weights penalize by the square of the distance | `reliability.weighted_kappa` |

All three have R twins in `r/R/04_reliability.R`, parity-tested against Python.

## Confidence intervals: how sure is the number?

A result from a sample is an estimate. If the model agrees with the reviewer
consensus on 86% of 237 reviewed charts, the "true" agreement on all charts
could be a bit higher or lower.

A **95% confidence interval** of, say, 81–90% means: if the study were repeated
many times, intervals built this way would contain the true value 95% of the
time. More charts give a narrower interval; fewer give a wider one.

### Bootstrap

Kappa and the judge-corrected accuracy have no simple interval formula, so the
repo uses the **bootstrap**: resample the charts with replacement (same size,
some charts drawn twice, some not at all), recompute the metric, repeat 500–1,000
times, and take the middle 95% of the results (2.5th to 97.5th percentile).

Where it's used now:

- `cost_effectiveness.bakeoff`: CI on each candidate judge's kappa against human
  verdicts.
- `cost_effectiveness.corrected_accuracy`: CI on each method's judge-estimated
  accuracy over the corpus sample. Both the sample and the calibration set are
  resampled, so uncertainty about the judge itself is included.

Not yet: the reliability tables (`13_reliability.py`) report kappa without CIs.
Adding bootstrap CIs there (in Python and R) is an open item.

## Reading them together

A kappa of 0.72 for the model vs 0.68 for a second reviewer looks like a win.
If the intervals are about 0.62–0.80 and 0.57–0.77, they overlap heavily and the
honest claim is "comparable", not "better". Report kappa with its interval, and
the number of charts behind it.

## Related corrections

- **Rogan-Gladen:** the LLM judge makes mistakes too. Given its sensitivity and
  specificity (measured against human reviewers), this formula corrects the raw
  "share judged correct" into an estimate of true accuracy. See
  [cost_effectiveness.md](cost_effectiveness.md).
- **Unsafe rate:** share of predictions whose error is clinically serious (S2),
  from the GlobalDentBench-style severity grading. See
  [dentbench_methods.md](dentbench_methods.md).

## Sources

- Cohen J. A coefficient of agreement for nominal scales. *Educ Psychol Meas*, 1960.
- Fleiss JL. Measuring nominal scale agreement among many raters. *Psychol Bull*, 1971.
- Landis JR, Koch GG. The measurement of observer agreement for categorical data. *Biometrics*, 1977.
- Efron B, Tibshirani R. *An Introduction to the Bootstrap.* Chapman & Hall, 1993.
- Rogan WJ, Gladen B. Estimating prevalence from the results of a screening test. *Am J Epidemiol*, 1978.
