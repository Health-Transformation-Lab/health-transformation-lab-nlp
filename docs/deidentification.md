# De-identification: methods, a labeled test set, and cost-effectiveness

> Personal learning project. Every note, name, date and number here is **synthetic and invented**.
> Nothing describes any organization's de-identification setup. Spec: [007](../specs/007-deid-methods/spec.md).

## Does the synthetic data contain real PHI?

No. The notes carry **fake PHI**: invented names from common-name lists, random record numbers,
phone numbers and dates, reserved example domains for emails and URLs, and SSNs starting with 9
(never issued). It's there so de-identification has something real-shaped to find.

Because the generator inserts every identifier, it **knows where each one is**: every fake
identifier is marked with its character span and category. That makes recall exact. Real notes
never allow this; there you only have a human review sample.

## The test set: three tiers, each adds a check

The **challenge set** is labeled fake PHI in three tiers. Each tier tests something the one before
it can't:

| Tier | What's in it | What it adds |
|---|---|---|
| **easy** | The study notes' header shapes (`Patient:`, `MRN:`, `Dr.`) | Confirms the pipeline removes the PHI the study notes carry |
| **hard** | Prose shapes: first name alone, lowercase names, relatives, "Mrs" without a period, ages over 89, written-out dates, dotted and +1 phones, email, URL, SSN, health plan member IDs, street / city / ZIP, referral practices | Covers the shapes real notes have, beyond headers |
| **unseen** | Written **after** regex v2 and never used to tune it: ALL-CAPS and possessive names, names that are words (Rose, Will), O'/hyphenated names, nicknames, weekday dates, spaced phones, fax, apartment numbers, driver's licence, plate, device serial, IP address, social handle, employer | A fair, held-out comparison: no method was tuned on it (regex v2 was written alongside the hard tier) |

Every tier also has marked **dental decoys**: text that looks like PHI but must survive (Glickman
and Miller classes, Gracey 11/12, tooth numbers, CDT and ICD codes, probing readings like 6-5-6,
drug names, ages under 90). They measure the other side of de-identification: whether the
clinical text the classifiers read comes through intact.

The categories follow HIPAA Safe Harbor and the 2014 i2b2/UTHealth annotation guidelines
([references](references.md#de-identification) 37–38). The names come from lists no engine uses.

**Guidelines and free test material online** ([references](references.md#de-identification) 37–45):

| Resource | What it is | Free? | Fit here |
|---|---|---|---|
| HHS Safe Harbor guidance | The 18 identifiers that must be removed | yes | Category list |
| 2014 i2b2/UTHealth (n2c2) | Standard clinical de-id benchmark and annotation guidelines | guidelines yes; corpus needs a data use agreement | Category scheme used; corpus not used |
| ASQ-PHI (2025) | 1,051 fully synthetic clinical search queries, PHI tagged, with hard negatives | yes, MIT | Second test set: `26_deid_benchmark.py --external asq_phi.jsonl` (download blocked here; attach it) |
| SHIELD (Stanford) | 1,381 real notes with surrogate PHI, adjudicated spans | access by request | Real-note shapes, if access is granted |
| presidio-evaluator | Fake-PII sentence generator from templates, detector evaluation | yes, MIT | Another way to generate labeled fake PHI |
| John Snow Labs | Clinical de-id pipelines in its licensed Healthcare NLP; public speed benchmarks on Databricks | the de-id models are licensed (trial and academic programs exist); no free test set found | Another engine to compare, if licensed |

## Engines and what each adds

| Engine | What it adds | Runs here |
|---|---|---|
| `regex` | Fast, exact and free; removes the header shapes (`Patient:`, `MRN:`, dates, phones) with no dental damage; the dental allowlist keeps BOP, SRP, FMX | yes |
| `regex_v2` | Extends regex to prose shapes: relatives, Mrs/Dr without a period, "Name, DDS", ages > 89, email, URL, SSN, member IDs, more date, phone and address shapes. Catches formatted IDs that NER models miss | yes |
| `presidio` | Microsoft Presidio: spaCy NER finds names and places from context, not from a fixed pattern, so it reaches shapes nobody wrote a rule for | yes (Python 3.12 + spaCy model) |
| `hf_stanford` | Transformer NER trained specifically for clinical de-identification: StanfordAIMI/stanford-deidentifier-base (radiology reports and notes; MIT). Learned clinical context; free; runs on a CPU ([what is BERT?](bert.md)) | yes (CPU here; GPU on Databricks: [`06_deid_benchmark.py`](../databricks/notebooks/06_deid_benchmark.py)) |
| `hf_obi` | A second clinical de-id transformer, obi/deid_roberta_i2b2 (RoBERTa trained on the i2b2 2014 corpus; MIT); a different training set, so a check on the first | yes, same |
| `azure_deid` | Managed Azure Health Data Services de-identification (27 PHI categories): no model to host, vendor-maintained | wired, tested with a fake client; needs `AZURE_DEID_ENDPOINT` |
| `azure_language` | Azure AI Language PII detection, healthcare (PHI) domain: a second managed option | wired, tested with a fake client; needs `AZURE_LANGUAGE_ENDPOINT` and `_KEY` |
| `llm` | An LLM lists every identifier verbatim; reads context like a person and follows written instructions (e.g. "keep Glickman"). Values not found in the note are dropped | wired, tested with a fake reply; needs an endpoint (Databricks serving) |
| `jsl` | John Snow Labs Healthcare NLP `clinical_deidentification` pipeline: a commercial clinical pipeline with Spark scale-out | wired, tested with a fake pipeline; needs a licence (free academic; trial through their Databricks installer) and Spark |
| `A+B` | Ensemble, the union of the engines' spans: each engine covers the other's gaps | |
| `+guard` | Dental guard: keeps dental terms (eponyms, tooth numbers, probing readings, codes) that general PHI models would remove, at no cost to recall | |

`python scripts/26_deid_benchmark.py --engines azure_deid+regex_v2+guard` runs the Microsoft
service plus regex plus guard, once an Azure resource is set up.

**What published comparisons say.** Transformer models trained for de-identification report
F1 around 0.98–0.99 on the i2b2 corpora (Stanford model card, Chambon et al.). A 2025 comparison by
John Snow Labs ranked its own Healthcare NLP first (recall 0.97), then Azure Health Data Services
(0.92), AWS Comprehend Medical (0.85) and GPT-4o zero-shot (0.77); the authors sell one of the
compared products, so it needs independent checking. None of these were tested on dental notes,
where eponyms and probing readings look like PHI. That's what the challenge set's decoys test.

## Standard test datasets

To compare with published numbers, engines should also be scored on the standard corpora. All are
real (de-identified) clinical text with surrogate PHI, so each needs its own access agreement and
must stay **outside the repo**:

| Dataset | What | Access | Loader |
|---|---|---|---|
| **i2b2/UTHealth 2014 (n2c2)** | 1,304 longitudinal notes, ~28,000 PHI spans; the main benchmark (Stanford and OBI models report on it) | n2c2 data use agreement | `--i2b2-2014 <folder>` (XML) |
| i2b2 2006 | Discharge summaries | n2c2 data use agreement | same XML shape; untested |
| PhysioNet *Deidentified Medical Text* | 2,434 nursing notes, the original deid gold standard | PhysioNet credentialed access (training + DUA) | `--external` after conversion |
| SHIELD (Stanford, 2026) | 1,381 diverse notes, 10,229 adjudicated spans | by request | `--external` |
| ASQ-PHI (2025) | 1,051 synthetic clinical queries with hard negatives | open, MIT | `--external` |
| Text Anonymization Benchmark | 1,268 court cases (not clinical) | open source | not clinical; skip |

None is dental. The challenge set's dental decoys stay the only test of over-redacting
dental terms.

## Results on the challenge set (400 notes, seed 7)

Entity recall = share of identifiers fully removed (one surviving character counts as a leak).
Decoy damage = share of dental decoys with any character removed.

| Engine | easy | hard | **unseen** | all | Precision | **Decoy damage** |
|---|---|---|---|---|---|---|
| regex | 1.00 | 0.27 | 0.20 | 0.47 | 0.94 | 0.00 |
| regex_v2 (+guard) | 1.00 | 1.00\* | 0.27 | 0.76 | 0.96 | 0.00 |
| presidio | 0.82 | 0.72 | 0.53 | 0.69 | 0.75 | **0.37** |
| presidio+guard | 0.82 | 0.72 | 0.53 | 0.69 | 0.91 | 0.05 |
| **presidio+regex_v2+guard** | 1.00 | 1.00\* | **0.57** | **0.86** | 0.89 | 0.05 |

\* written alongside this tier; read the unseen column for a fair comparison.

What it shows:

- **No single method is enough.** Regex is exact on shapes it knows and blind to the rest. The NER
  model generalizes better (53% vs 27% on unseen) but misses formatted IDs. The ensemble beats both.
- **The NER model damages dental text.** Presidio alone redacted part of 37% of dental terms; the
  dental guard cuts that to 5% without losing any recall.
- **Even the best engine here leaks.** 43% of the unseen identifiers survive (streets, URLs, IDs,
  doctors' names are the worst: `data/deid/by_category.csv`). A held-out human review sample stays
  necessary, and the Microsoft service should be run on the same set before choosing.

## Cost-effectiveness

`data/deid/cost_effectiveness.csv`, per 1M notes, for the full mix (`all`) and the held-out tier (`unseen`):

- **Engine cost.** Local engines: node-hours at the throughput **measured** here (regex about
  13,000 notes/s, regex v2 about 3,600, Presidio about 75 on one CPU) × the CPU node price.
  Services: price per MB (Azure de-identification, 50 MB/month free) or per 1,000-character record
  (Azure AI Language). Service prices in `costs.yaml` are **ILLUSTRATIVE** until filled from the
  pricing pages.
- **Review cost.** Human QA of 1 in 1,000 de-identified notes, the same for every engine.
- **Outcome.** Leaked identifiers per 1M notes, then decoy damage as a tie-break.
- **Frontier.** An engine is dominated if one that costs no more leaks no more. ICER = extra USD
  per leaked identifier avoided.

With these inputs the engines themselves are nearly free locally (under $5 per 1M notes, even
Presidio); the review sample dominates the cost. So the choice is about leaks, not compute:
on both tiers the frontier ends at presidio+regex_v2+guard. A cloud service at an illustrative
$0.50/MB would add roughly $140 per 1M notes of about 320 characters. It's worth it only if it
leaks measurably less on the unseen tier. That's the comparison to run once an Azure resource exists.

Python and R compute the same frontier from `cost_inputs.csv` (parity test).

## Limits

- The challenge set is still written by one person. The unseen tier is held out from regex v2,
  not from that person's idea of a "hard" note. Real notes will differ again.
- Leaks are counted, not weighted: a leaked SSN and a leaked first name count the same.
- The study pipeline still uses `regex` by default (`study.py`). Switching it is action item H2.
