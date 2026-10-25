# Python side

```bash
pip install -e .            # core: build, labels, baselines
pip install -e ".[models]"  # + transformers/torch for encoder rungs
pytest -q tests

python scripts/01_build_dataset.py --n-people 300   # add --no-leak for the harder variant
python scripts/02_split.py
python scripts/03_run_ladder.py --rungs rules_baseline,structured_baseline,tfidf_logreg
python scripts/03_run_ladder.py --rungs distilbert-base --epochs 2 --max-len 192
```

Tested here: build, split, rules/structured/TF-IDF rungs, scorer, unit tests.
Written but not yet run: the Hugging Face fine-tune rung (`HFEncoder`), which
needs model downloads.
