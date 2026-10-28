# Plan: spec 025

## Files

- `huggingface/publish.py`: imports `DATASETS`, `files_of` and `check` from `kaggle/publish.py` (FR-001).
  `build(name, out, commit)` copies the files under `raw/`, writes the split files for the notes
  (`data/train.csv`, `data/test.csv` from `train.csv` and `review_key.csv`, renaming the review key's
  `truth_status`, `truth_grade`, `truth_extent` to `label`, `grade`, `extent`), copies the quickstart notebook,
  and writes `README.md`: a YAML header (licence, language, task, size, tags, `configs`) and the body from
  `huggingface/cards/<name>.md`, the quick start, and a contents table with the commit.
  `upload(folder, repo_id, message, api)` creates the dataset repository public if needed and uploads the
  folder as one commit, deleting files no longer listed. `--org-card` builds and uploads the organisation card
  Space from `huggingface/cards/org.md`.
- `huggingface/cards/notes.md`, `results.md`, `org.md`.
- `notebooks/perio_bench_quickstart.ipynb`: plain pandas and scikit-learn, nothing to install on Kaggle or Colab.
- `kaggle/prepare_kernel.py`: a `quickstart` job (no GPU, no internet, `dataset_sources` the notes).
- `.github/workflows/kaggle-publish.yml`: renamed in the UI to *Publish datasets (Kaggle and Hugging Face)*; a
  `platform` input; a Hugging Face job with the token check of US3; the quickstart kernel pushed with the Kaggle
  datasets.
- `ops/secrets_register.yaml`, AGENTS.md's credential table: `HF_PUBLISH_TOKEN`.
- `huggingface/README.md` and `kaggle/README.md`: one page each for what's published and how.

## Tests (first)

`python/tests/test_hf_publish.py`: the build has spec 020's files under `raw/` and nothing else but the split
files, card and notebook; train and test share columns and the test split is the 240 review notes; the YAML
header parses and every `configs` path exists; the card carries the labels and links; a refused build stays
refused; the workflow's platform input and token check. `python/tests/test_quickstart.py`: runs the notebook's
code cells on the local data.
