"""Spec 013 G5: reliability of clinical attachment loss (CAL) from repeated charts.

Variance components at patient, tooth and site level plus measurement error, after a fixed time
trend; ICC per level (de Vet et al. 2006: reliability = between-subject variance / total)."""

import pytest

from health_transformation_lab_nlp.reliability_cal import (
    CalParams,
    draw_repeated_charts,
    icc_report,
    nested_components,
)


def test_estimator_recovers_known_components_on_unrounded_data():
    p = CalParams(sd_patient=1.0, sd_tooth=0.6, sd_site=0.5, sd_error=0.8, mm_per_year=0.1, round_mm=False)
    d = draw_repeated_charts(n_patients=300, n_teeth=12, n_visits=4, params=p, seed=1)
    c = nested_components(d)
    assert c["var_patient"] == pytest.approx(1.0, rel=0.2)
    assert c["var_tooth"] == pytest.approx(0.36, rel=0.15)
    assert c["var_site"] == pytest.approx(0.25, rel=0.15)
    assert c["var_error"] == pytest.approx(0.64, rel=0.05)
    assert c["slope_mm_per_year"] == pytest.approx(0.1, abs=0.03)


def test_icc_levels_are_nested_shares_of_total_variance():
    c = {"var_patient": 1.0, "var_tooth": 0.5, "var_site": 0.25, "var_error": 0.25}
    r = icc_report(c)
    assert r["icc_patient"] == pytest.approx(0.5)            # two sites in the same mouth
    assert r["icc_tooth"] == pytest.approx(0.75)             # two sites on the same tooth
    assert r["icc_site"] == pytest.approx(0.875)             # the same site measured again
    assert r["sem_mm"] == pytest.approx(0.5)                 # standard error of measurement


def test_more_probing_error_means_lower_site_reliability():
    lo = CalParams(sd_error=0.4)
    hi = CalParams(sd_error=1.2)
    r_lo = icc_report(nested_components(draw_repeated_charts(100, 10, 3, lo, seed=2)))
    r_hi = icc_report(nested_components(draw_repeated_charts(100, 10, 3, hi, seed=2)))
    assert r_hi["icc_site"] < r_lo["icc_site"]


def test_draw_is_seeded_and_cal_is_whole_mm_and_never_negative():
    a = draw_repeated_charts(20, 6, 3, CalParams(), seed=5)
    b = draw_repeated_charts(20, 6, 3, CalParams(), seed=5)
    assert a.equals(b)
    assert (a["cal_mm"] >= 0).all() and (a["cal_mm"] % 1 == 0).all()
    assert len(a) == 20 * 6 * 6 * 3
    assert set(a.columns) >= {"patient_id", "tooth", "site", "visit", "years", "cal_mm"}


def test_reml_matches_anova_on_balanced_data():
    pytest.importorskip("statsmodels")
    from health_transformation_lab_nlp.reliability_cal import reml_components
    p = CalParams(round_mm=False)
    d = draw_repeated_charts(60, 8, 3, p, seed=3)
    a, r = nested_components(d), reml_components(d)
    for k in ("var_patient", "var_tooth", "var_site", "var_error"):
        assert r[k] == pytest.approx(a[k], rel=0.1, abs=0.02)


def test_stage_band_flips_between_visits_grow_with_probing_error():
    from health_transformation_lab_nlp.reliability_cal import cal_band, stage_band_flips
    assert [cal_band(x) for x in (0, 1, 2, 3, 4, 5, 9)] == ["<1", "1-2", "1-2", "3-4", "3-4", ">=5", ">=5"]
    still = draw_repeated_charts(50, 10, 3, CalParams(sd_error=0.0, mm_per_year=0.0), seed=4)
    assert stage_band_flips(still)["flip_rate"] == 0.0
    noisy = draw_repeated_charts(50, 10, 3, CalParams(sd_error=1.0, mm_per_year=0.0), seed=4)
    f = stage_band_flips(noisy)
    assert f["pairs"] == 50 * 2 and 0 < f["flip_rate"] < 1 and f["down_rate"] > 0
