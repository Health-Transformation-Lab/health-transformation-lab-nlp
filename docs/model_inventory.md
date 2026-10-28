# Model inventory: every model and AI service the repo depends on

> Personal learning project; synthetic data only. This page lists every pretrained model, hosted model
> and AI service the code can call, for an AI-use review. Licences were read from each model's
> Hugging Face card on 2026-10-28; re-check the card before approval, because cards change.
> A test (`tests/test_model_inventory.py`) fails if code or `models.yaml` names a model that isn't here.

**What runs where.** Every model in sections 1–3 downloads its weights from Hugging Face and runs
locally or on Databricks/Kaggle compute; no note text leaves that machine. Section 4 lists hosted
services that receive the text; they only ever get synthetic or de-identified notes, and the code
refuses to call one unless its endpoint is configured.

**Status** says whether real (not simulated) results are committed in `data/datasets/`.

## 1. Encoders: read a note and assign its periodontal status

| Model · paper · domain, role | Hugging Face id | Organisation | Licence (card) | Status |
|---|---|---|---|---|
| BERT base · [1810.04805](https://arxiv.org/abs/1810.04805) · general, classifier | `google-bert/bert-base-uncased` | Google | Apache-2.0 | results |
| DistilBERT · [1910.01108](https://arxiv.org/abs/1910.01108) · general, classifier | `distilbert/distilbert-base-uncased` | Hugging Face | Apache-2.0 | results |
| ModernBERT base · [2412.13663](https://arxiv.org/abs/2412.13663) · general, classifier, long context | `answerdotai/ModernBERT-base` | Answer.AI | Apache-2.0 | results |
| ModernBERT large · [2412.13663](https://arxiv.org/abs/2412.13663) · general, classifier, long context | `answerdotai/ModernBERT-large` | Answer.AI | Apache-2.0 | not run |
| Longformer · [2004.05150](https://arxiv.org/abs/2004.05150) · general, long context; also the base of the PHI tagger | `allenai/longformer-base-4096` | Allen Institute for AI | Apache-2.0 | not run as a classifier; used by the PHI tagger (section 3) |
| SciBERT · [1903.10676](https://arxiv.org/abs/1903.10676) · scientific, classifier | `allenai/scibert_scivocab_uncased` | Allen Institute for AI | **none on the card** (the `allenai/scibert` GitHub repository is Apache-2.0): confirm before approval | results |
| Bio_ClinicalBERT · [1904.03323](https://arxiv.org/abs/1904.03323) · clinical, classifier | `emilyalsentzer/Bio_ClinicalBERT` | Alsentzer et al. (MIT) | MIT | results |
| GatorTron base · [Nature Digital Medicine 2022](https://doi.org/10.1038/s41746-022-00742-2) · clinical, classifier | `UFNLP/gatortron-base` | University of Florida / NVIDIA | Apache-2.0 | not run |
| BiomedBERT · [2007.15779](https://arxiv.org/abs/2007.15779) · biomedical, classifier | `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext` | Microsoft | MIT | results |
| BioClinical ModernBERT base · [2506.10896](https://arxiv.org/abs/2506.10896) · clinical, classifier, long context | `thomas-sounack/BioClinical-ModernBERT-base` | Sounack et al. (Dana-Farber) | MIT | results |
| BioClinical ModernBERT large · [2506.10896](https://arxiv.org/abs/2506.10896) · clinical, classifier, long context | `thomas-sounack/BioClinical-ModernBERT-large` | Sounack et al. (Dana-Farber) | MIT | not run |
| Clinical-Longformer · [2201.11838](https://arxiv.org/abs/2201.11838) · clinical, long context | `yikuan8/Clinical-Longformer` | Northwestern University (Luo lab) | **none on the card**: confirm before approval | not run |

Clinical models were pretrained on clinical notes by their authors (for example MIMIC-III for
Bio_ClinicalBERT and Clinical-Longformer); only their published weights are used here.

## 2. Concept mapping and retrieval (not classifiers)

| Model · paper · domain, role | Hugging Face id | Organisation | Licence (card) | Status |
|---|---|---|---|---|
| SapBERT · [2010.11784](https://arxiv.org/abs/2010.11784) · biomedical, concept mapping (note terms to UMLS/SNOMED) | `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` | University of Cambridge | Apache-2.0 | not run |
| GTE-ModernColBERT · [model card](https://huggingface.co/lightonai/GTE-ModernColBERT-v1) · general, retrieval (evidence lookup for RAG) | `lightonai/GTE-ModernColBERT-v1` | LightOn | Apache-2.0 | not run |

## 3. Large language models and de-identification models

| Model · paper · domain, role | Source | Organisation | Licence | Status |
|---|---|---|---|---|
| MedGemma 1.5 4B (instruction-tuned) · [2507.05201](https://arxiv.org/abs/2507.05201) · medical, note reader (LLM) | `google/medgemma-1.5-4b-it` | Google (Health AI Developer Foundations) | [HAI-DEF terms of use](https://developers.google.com/health-ai-developer-foundations/terms) (accept on Hugging Face first) | results (240 notes) |
| MedGemma 4B (instruction-tuned) · [2507.05201](https://arxiv.org/abs/2507.05201) · medical, note reader (LLM) | `google/medgemma-4b-it` | Google (HAI-DEF) | HAI-DEF terms | not run |
| MedGemma 27B text (instruction-tuned) · [2507.05201](https://arxiv.org/abs/2507.05201) · medical, note reader (LLM) | `google/medgemma-27b-text-it` | Google (HAI-DEF) | HAI-DEF terms | not run (needs a large GPU) |
| PHI tagger: Longformer base fine-tuned on MACCROBAT (CC BY 4.0) · spec 010 · de-identification | `allenai/longformer-base-4096` + own fine-tune (not published) | this repo | Apache-2.0 base; MACCROBAT CC BY 4.0 | results (`data/deid/maccrobat_*`) |
| Stanford de-identifier · Chambon et al., JAMIA 2023 · clinical, de-identification | `StanfordAIMI/stanford-deidentifier-base` | Stanford AIMI | MIT | results (de-id benchmark) |
| OBI de-identifier (RoBERTa on i2b2 2014) · clinical, de-identification | `obi/deid_roberta_i2b2` | Oxford Big Data Institute | MIT; **trained on i2b2 2014, a data-use-agreement set**: only the published weights are used, never the data | results (de-id benchmark) |
| spaCy English large (via Microsoft Presidio) · general, named entities for de-identification | `en_core_web_lg` (spaCy) with `presidio-analyzer` | Explosion; Microsoft | MIT; MIT | results (de-id benchmark) |

## 4. Hosted models and services (receive synthetic or de-identified text only)

| Service · role | Where | Licence / terms | Status |
|---|---|---|---|
| Meta Llama 3.3 70B Instruct · LLM judge (spec 012) and LLM de-identification | Databricks Foundation Model API, pay-per-token endpoint `databricks-meta-llama-3-3-70b-instruct` | Llama 3.3 Community License; Databricks terms | judge: run in dev (2 runs, 2026-10-27); de-id: not run |
| `ai_mask` · de-identification | Databricks SQL AI Function (Public Preview), Databricks-hosted model | Databricks terms | not run |
| Azure Health Data Services de-identification · de-identification | Azure (needs `AZURE_DEID_ENDPOINT`) | Microsoft terms | not run |
| Azure AI Language PII detection · de-identification | Azure (needs `AZURE_LANGUAGE_ENDPOINT`) | Microsoft terms | not run |
| Amazon Comprehend Medical · de-identification | AWS (needs `AWS_REGION`) | AWS terms | not run |

## 5. In-house methods (no external model)

TF-IDF + logistic regression (`tfidf_logreg`), note rules (`note_rules`), the TF-IDF + radiograph fusion
(`fusion_tfidf_rad`), the rule phenotypes and the regex de-identifiers are written and trained in this repo
with scikit-learn; they download no pretrained weights.

## For an AI-use review

- **Licence gaps**: SciBERT and Clinical-Longformer state no licence on their cards; MedGemma uses Google's
  HAI-DEF terms (not an open-source licence) and needs the terms accepted per account.
- **Training data**: the OBI de-identifier was trained on i2b2 2014 (data-use agreement); clinical encoders
  were pretrained on MIMIC or institutional notes. Using published weights doesn't bring that data in, but
  reviewers may ask.
- **Data flow**: sections 1–3 run where the data is; section 4 sends text to a hosted service, and only
  synthetic or de-identified text, behind the leak gate.
- **Not run yet** (no real results): ModernBERT large, BioClinical ModernBERT large, GatorTron, Clinical-
  Longformer, Longformer as a classifier, SapBERT, GTE-ModernColBERT, MedGemma 4B and 27B, and every service
  in section 4 except the judge.
