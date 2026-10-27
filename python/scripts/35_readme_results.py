"""Regenerate the results leaderboards in README.md from committed results (no re-runs).

    python scripts/35_readme_results.py           # rewrite the block between the results markers
    python scripts/35_readme_results.py --check   # exit 1 if the README is stale

Note readers (data/datasets/ladder/), the rule phenotypes (answer key) and de-identification
(data/deid/). Method and ranking: dental_omop_nlp/readme_results.py.
"""

import argparse
import sys

from dental_omop_nlp import readme_results as rr
from dental_omop_nlp.paths import REPO_ROOT

ap = argparse.ArgumentParser()
ap.add_argument("--check", action="store_true")
a = ap.parse_args()

readme = REPO_ROOT / "README.md"
text = readme.read_text()
new = rr.update_readme(text, rr.results_markdown(rr.load_inputs()))
if a.check:
    sys.exit(0 if new == text else "README results are stale: run python scripts/35_readme_results.py")
readme.write_text(new)
print("README results block", "unchanged" if new == text else "updated")
