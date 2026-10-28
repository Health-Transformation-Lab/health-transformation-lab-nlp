"""Script numbers give the run order: each number is used once (two parallel PRs both took 42, #144)."""

from collections import Counter

from health_transformation_lab_nlp.paths import REPO_ROOT


def test_every_script_number_is_used_once():
    numbers = Counter(p.name.split("_", 1)[0] for p in (REPO_ROOT / "python" / "scripts").glob("[0-9]*_*.py"))
    assert not [n for n, c in numbers.items() if c > 1], sorted(numbers.items())
