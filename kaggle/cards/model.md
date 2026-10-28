# Dental periodontal note classifier (ModernBERT-base, class-weighted)

ModernBERT-base fine-tuned to read a dental chart note and give the patient's periodontal status at that visit,
under the 2017 AAP/EFP classification: one of six labels, `healthy`, `gingivitis`, or `periodontitis_stage_1`
to `periodontitis_stage_4`. The loss is weighted by the square root of inverse class frequency, so the rare
stages count for more. It is the top fine-tuned encoder on the repo's leaderboard before the stage IV keyword rule is added.

**Trained and scored on synthetic notes only**, by a personal learning project that is **not affiliated** with
any employer, institution or company. The scores below are against the generator's own truth: **not clinical
performance**, not evidence about any population, and **not for clinical use**. Real notes are harder.

## Training

- Base model: [answerdotai/ModernBERT-base](https://huggingface.co/answerdotai/ModernBERT-base) (Apache 2.0).
- Data: the synthetic training notes of the *Synthetic Dental Periodontal Notes and Charts* dataset
  (`train.csv`), labelled with the chart's true status.
- `python/scripts/11_ai_predict.py --rung modernbert-base --class-weight sqrt`, on a Kaggle GPU (T4), by the
  repository's encoder workflow.
