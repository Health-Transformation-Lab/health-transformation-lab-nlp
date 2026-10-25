# MedGemma: how it could be used here (exploratory note)

> **Personal learning project.** Ideas for learning and practice, using public
> information only. Not affiliated with Google or any other organization, and
> not an organization's plan. See [DISCLAIMER](../DISCLAIMER.md).

## What MedGemma is (public sources)

- Open models from Google's Health AI Developer Foundations (HAI-DEF). MedGemma 1:
  a **4B multimodal** model (pre-trained and instruction-tuned), a **27B
  text-only** model and a **27B multimodal** model. Text and image in, text out;
  context up to 128K tokens. Images were radiology (chest X-ray, CT),
  dermatology, ophthalmology and histopathology; **dental imaging is not
  mentioned**. The image encoder is also released on its own as **MedSigLIP**,
  recommended for classification and retrieval without text generation
  ([model card](https://developers.google.com/health-ai-developer-foundations/medgemma/model-card-v1)).
- **MedGemma 1.5** (reported January 2026): 4B for offline / low-resource use,
  27B still available; adds 3D CT/MRI and whole-slide pathology, longitudinal
  X-rays, and better extraction from medical documents and EHR question
  answering; alongside a new speech model, MedASR
  ([BioPharmaTrend](https://www.biopharmatrend.com/news/google-updates-open-medical-ai-suite-with-new-imaging-and-speech-models-launches-100k-developer-hackathon-1464/)).
- **Terms and limits:** governed by the HAI-DEF terms of use; a starting point
  for developers, not intended to directly inform diagnosis or treatment;
  must be validated on representative data; prompt-sensitive; watch for data
  contamination (model card).

## Where it fits in this repo

| # | Use | How | Effort | Fits with |
|---|-----|-----|--------|-----------|
| 1 | **Note reader (LLM rung)** | Zero-/few-shot prompt: note in, JSON status / stage / grade / extent out, same schema and quote gate as the judge. 4B and 27B-text as two rungs | Low | Model ladder; difficulty levels; cost frontier |
| 2 | **Fine-tuned note reader ("extend")** | Parameter-efficient fine-tuning (e.g. LoRA) of the 4B model on `train.csv` (synthetic labels), structured JSON output. Compare against the BERT ladder: does a 4B generative model beat a fine-tuned 150M encoder enough to justify its cost? | Medium; needs a GPU | BERT ladder; harm-weighted errors |
| 3 | **Judge candidate** | Add to the judge bake-off. The same-family rule applies: if a MedGemma model is being graded, the judge must be from a different family, and vice versa | Low | `15_judge.py` bake-off |
| 4 | **Note paraphraser for synthetic data** | Rewrite generated notes in varied clinical phrasing while keeping the label (as the UTHealth team did with GPT-4), then check with the reader and judge that the label survived. Reduces the "same author wrote notes and rules" problem | Medium | Spec 001 note realism |
| 5 | **Radiograph extension ("extend", images)** | MedGemma wasn't trained on dental images. Options: (a) MedSigLIP image embeddings + a small classifier for bone loss; (b) fine-tune the 4B multimodal model on a public, licensed dental radiograph dataset. Output feeds the same structured radiograph schema as spec 003 | High; images and licences | Radiograph exploration |
| 6 | **Grade from history** | Use the long context to read several visits at once and estimate progression (grade is about rate of change) | Medium | Grade reader |

## Implemented (spec 004)

Uses 1 (reader), 2 (LoRA fine-tune) and 3 (judge family rule) are in the code;
none has been run on real MedGemma weights yet (needs a GPU and accepted HAI-DEF terms).

| Piece | Where |
|---|---|
| Note reader rung: prompt shares the judge's AAP/EFP criteria; JSON status/grade/extent + verbatim quote; falls back to `note_rules` and flags the row on any failure; never sends a note the residual PHI scan flags | `python/dental_omop_nlp/llm_reader.py` |
| Backends: `hf` (local transformers, optional LoRA adapter), `openai` (Databricks serving, vLLM, Ollama), `simulated` (dry run) | same |
| Run it | `python scripts/11_ai_predict.py --rung medgemma-1.5-4b-it --backend hf [--shots 1] [--limit 40]` |
| Fine-tune | `python scripts/17_medgemma_lora.py` then `--adapter runs/medgemma-lora` |
| Judge rule | `15_judge.py` excludes judges of any evaluated LLM's family (`family: gemma` in `models.yaml`) |
| Databricks | `databricks/notebooks/03_medgemma_reader.py` (Free Edition serverless GPU) |
| Costs | `costs.yaml`: assumed GPU throughput, ILLUSTRATIVE; measure and replace |

Per-note details (gate pass, fallback, tokens, latency) go to
`data/datasets/llm_details_<rung>.csv`. The simulated dry run's numbers come from
placeholder error rates and say nothing about MedGemma.

## Suggested order

1. **Rung 1 first.** Cheap, and it answers the basic question: how does an
   off-the-shelf medical LLM do on these notes, by difficulty level, and at
   what cost per million notes?
2. **Then rung 2** only if rung 1 is promising but not good enough.
3. **Paraphrasing (4)** whenever the synthetic notes need more variety.
4. **Images (5)** last: it needs public dental image data with a licence that
   allows this, and GPU time.

## Running it

- **Laptop / CPU:** the 4B model, quantized, runs locally for small synthetic
  tests (slow). Synthetic data only.
- **Databricks Free Edition:** has limited serverless GPU in notebooks
  (announced June 2026; subject to capacity, fair-use limits, no published
  quota). Enough to try the 4B model on synthetic notes and possibly a small
  LoRA fine-tune of it. It does **not** offer GPU serving endpoints or custom
  models on GPU batch inference, so run MedGemma inside the notebook rather
  than as an endpoint
  ([limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations),
  [announcement](https://www.databricks.com/blog/whats-coming-next-free-edition)).
  The 27B model is unlikely to fit.
- **Paid Databricks:** register through MLflow, serve on GPU Model Serving, and
  batch-score with `ai_query`. Costs go in `costs.yaml` as a self-hosted GPU method.
- **Evaluation:** the same split, scorer, harm grading, difficulty levels and
  cost-effectiveness as every other method. Report prompt-sensitivity by running
  two or three prompt variants.

## Cautions

- Not for clinical decisions (model terms). Every use here is a research exercise.
- No dental training data in MedGemma 1, so expect to need adaptation.
- If MedGemma reads the notes, don't let a Gemma-family model judge them.
- Check the HAI-DEF terms before sharing fine-tuned weights.
- Nothing identifiable goes in, ever. Synthetic notes only in this repo.
