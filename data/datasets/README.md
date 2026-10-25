# Study datasets (synthetic)

Built by `python/scripts/10_build_study.py` (seed 42, 1,200 people). Every
value is generated; the notes contained fake PHI that the de-identification
step removed before anything was written here. `build_summary.json` records
the counts and de-id recall for this build.

| File | Use |
|------|-----|
| `train.csv` | Train the AI model. `label` = chart truth, `stated_status` = what the clinician wrote, `grade`, `extent`. |
| `review_tasks.json` | Import into Label Studio (`labelstudio/README.md`). |
| `answer_key/` | **Reviewers must not open this.** Generator truth, each source's reading, the algorithm's call, per chart. Used only by `13_reliability.py`. |
| `method_agreement.csv` | Pairwise agreement between the seven sources (status level and perio yes/no). |
| `method_coverage.csv` | How often each source says anything. |
| `deid_report.csv` | Per note: PHI characters, removed, over-redacted, leaked values. |
| `ai_predictions_*.csv` | One file per AI model, predictions on the review charts. |
