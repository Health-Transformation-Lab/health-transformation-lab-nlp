"""Spec 029 US2: one app, every bench, in bench order; each reads its own gold schema."""

from bench_report import benches


def test_benches_are_in_bench_order():
    assert [b.key for b in benches.BENCHES] == ["perio_bench", "oral_health_bench", "access_bench"]
    assert [b.name for b in benches.BENCHES] == ["PerioBench", "OralHealthBench", "AccessBench"]


def test_each_bench_reads_its_own_gold_schema():
    assert [b.gold_schema for b in benches.BENCHES] == ["gold_perio_bench", "gold_oral_health_bench",
                                                        "gold_access_bench"]


def test_statuses_follow_agents_md_and_only_perio_bench_has_a_report_yet():
    assert [b.status for b in benches.BENCHES] == ["live", "planned", "exploratory"]
    assert all(b.status in benches.STATUSES for b in benches.BENCHES)
    assert [r.key for r in benches.get("perio_bench").reports] == ["dq"]
    assert benches.get("oral_health_bench").reports == [] and benches.get("access_bench").reports == []


def test_report_keys_are_unique_within_a_bench():
    for b in benches.BENCHES:
        keys = [r.key for r in b.reports]
        assert len(keys) == len(set(keys))
