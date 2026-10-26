#!/usr/bin/env bash
# Regenerate every Python output r/tests/test_parity.R compares against
# (seeded; simulated reviewers/judge). Run from the repo root.
set -euo pipefail
cd python
python scripts/01_build_dataset.py
python scripts/02_split.py
python scripts/export_rules_predictions.py
python scripts/10_build_study.py
for r in note_rules tfidf_logreg fusion_tfidf_rad; do python scripts/11_ai_predict.py --rung "$r"; done
python scripts/12_import_review.py --simulate 4
python scripts/13_reliability.py --simulated --n-boot 200
python scripts/28_ladder_vs_truth.py --n-boot 200
python scripts/11_ai_predict.py --rung medgemma-1.5-4b-it --backend simulated
python scripts/29_medgemma_vs_bert.py --simulated --n-boot 200   # needs committed encoder predictions
python scripts/19_prevalence.py
python scripts/20_data_quality.py
python scripts/22_build_sites.py
python scripts/14_benchmark_cost.py --simulate-missing
python scripts/15_judge.py --backend simulated --simulated-review
python scripts/27_component_judge.py --simulated
python scripts/16_cost_effectiveness.py --simulated
python scripts/26_deid_benchmark.py      # engines that can run here; Presidio and Azure are skipped if unavailable
