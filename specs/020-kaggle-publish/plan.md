# Plan: spec 020

## This pull request: US1, US2, US4

- `kaggle/publish.py`: `DATASETS` names each dataset's files (listed, or globbed inside named folders with
  `simulated_*` dropped); `build()` copies them and writes `dataset-metadata.json` (CC-BY-4.0, title, subtitle,
  keywords) with the card from `kaggle/cards/<name>.md` plus a generated contents table and the commit.
- `.github/workflows/kaggle-publish.yml`: manual; environment `dev`; `kaggle datasets status` decides between
  `create --public` (first time) and `version -m "<note> (<sha>)"`; `--dir-mode zip` for the subfolders.
- `kaggle/README.md`: one page for everything on Kaggle, the collection steps included.
- Tests: `python/tests/test_kaggle_publish.py`.

## Next pull request: US3 (the model)

`HFEncoder.save(dir)` and `11_ai_predict.py --save-model DIR`; the encoder notebook gains `CLASS_WEIGHT` and
`SAVE_MODEL`; a `model` job in `kaggle-publish.yml` trains ModernBERT-base (class-weighted) on Kaggle, downloads
the weights and the run's predictions, scores them against `review_key.csv`, and runs `kaggle models create` /
`kaggle models instances create` (framework transformers, Apache 2.0) with a card giving those scores.
