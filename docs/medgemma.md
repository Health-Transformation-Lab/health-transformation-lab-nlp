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

## Licence requirement

Every MedGemma model is **gated** on Hugging Face under the
[HAI-DEF terms of use](https://developers.google.com/health-ai-developer-foundations/terms).
Before any run: accept the terms on the model's Hugging Face page with your own account, then make a
read token from that account available as `HF_TOKEN` (cloud environment secret, or the Databricks
secret scope `dental` / `hf_token` for notebook 03). Without both, the download fails with 401/403.
The terms also govern sharing outputs and fine-tuned weights: check them before publishing a LoRA
adapter. `models.yaml` marks these entries `gated: true` with the licence link.

## Implemented (spec 004)

Uses 1 (reader), 2 (LoRA fine-tune) and 3 (judge family rule) are in the code.
The zero-shot reader has been run once on real `medgemma-1.5-4b-it` weights (CPU,
reader-v2, 240 review charts); the LoRA fine-tune has not (needs a GPU).

**First real run (synthetic notes, generator truth; not clinical performance).**
Accuracy 0.758 (95% CI 0.700-0.808) against note_rules' 0.788, paired difference
-0.029 (-0.058 to 0.000); with the note rules deciding stage IV, 0.771. By difficulty:
L1 100% (141), L2 97% (31), L3 16% (68). Gate pass 97.9%, fallback 2.1%, ~850 tokens
in and ~75 out per note, ~27 s per note on 4 CPU cores. So it reads a written
diagnosis well and does not yet stage from the chart findings when none is
written; L3 is where few-shot, prompt variants or the LoRA fine-tune would have to
help. Against the best encoder alone (`modernbert-base+cw`, 0.838) the difference is
-0.079 (-0.154 to -0.013); on L3 the encoder gets 81%. Full tables:
`data/datasets/ladder/ladder_vs_truth.csv` and `medgemma_vs_bert*.csv`.

MedGemma 1.5 opens with a `<unused94>thought ... <unused95>` block; the hf backend
suppresses it (it otherwise used up the 300 new tokens before the JSON) and
`parse_answer` strips one if present.

| Piece | Where |
|---|---|
| Note reader rung: prompt shares the judge's AAP/EFP criteria; JSON status/grade/extent + verbatim quote; falls back to `note_rules` and flags the row on any failure; never sends a note the residual PHI scan flags | `python/dental_omop_nlp/llm_reader.py` |
| Backends: `hf` (local transformers, optional LoRA adapter), `openai` (Databricks serving, vLLM, Ollama), `simulated` (dry run) | same |
| Run it | `python scripts/11_ai_predict.py --rung medgemma-1.5-4b-it --backend hf [--shots 1] [--limit 40]` |
| Fine-tune | `python scripts/17_medgemma_lora.py` then `--adapter runs/medgemma-lora` |
| Judge rule | `15_judge.py` excludes judges of any evaluated LLM's family (`family: gemma` in `models.yaml`) |
| Databricks | `databricks/notebooks/03_medgemma_reader.py` (Free Edition serverless GPU) |
| Costs | `costs.yaml`: assumed GPU throughput, ILLUSTRATIVE; measure and replace |
| Compare with BERT | `python scripts/29_medgemma_vs_bert.py [--bert modernbert-base]`: each MedGemma run minus the encoder, paired bootstrap CI, stage IV recall, by difficulty, fallback rate; R twin in `10_ladder.R`. Notebook 03 runs it after the reader (set `limit` 0, `lora_train` > 0 for the fine-tuned version) |

Per-note details (gate pass, fallback, tokens, latency) go to
`data/datasets/llm_details_<rung><tag>.csv`; the tag (`+lora`, `+k<shots>`, `+terse`) keeps
zero-shot, few-shot and fine-tuned runs apart. The simulated dry run's numbers come from
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
- **Kaggle (free GPU), when Databricks has none:** GPU access on Free Edition needs LinkedIn
  verification and free capacity, and some accounts get none, so the `medgemma_reader` job can wait and
  retry for hours without starting. [`kaggle/medgemma_reader.ipynb`](../kaggle/medgemma_reader.ipynb) runs
  the same `11_ai_predict.py` on Kaggle's free "GPU T4 x2" (about 30 GPU-hours a week): clone, install,
  token from Kaggle Secrets, a 10-note test, then all 240 notes with *Save & Run All*. The reader picks
  the weights dtype for the GPU (`llm_reader.pick_dtype`: bfloat16 on A10/A100/H100, float32 on T4 x2,
  `DENTAL_LLM_DTYPE` to force one). Download the prediction CSVs from the Output tab into
  `data/datasets/`, then run `28_ladder_vs_truth.py` and `35_readme_results.py`.
  **From GitHub:** Actions → *kaggle-medgemma* → Run workflow pushes the notebook to Kaggle
  (`kaggle kernels push --accelerator NvidiaTeslaT4`, private), waits, and keeps the predictions and
  the Kaggle log as a workflow artifact. Needs `KAGGLE_USERNAME` and `KAGGLE_API_TOKEN` (or
  `KAGGLE_KEY`) in the GitHub environment `dev` (Kaggle → Settings → API → Generate New Token; delete it
  there when done). The Hugging Face token stays a Kaggle secret: after the first push, open the
  notebook on kaggle.com, Add-ons → Secrets → attach `HF_TOKEN`, and run the workflow again. `limit` 10
  is a test; `limit` 0 reads all 240 notes (hours: turn `wait` off, then rerun with `collect_only`).
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
