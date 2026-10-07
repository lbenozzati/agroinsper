"""Checks for the validation rules and scoring maths (run: python -m pytest -q)."""

import numpy as np
import pandas as pd
import pytest

import microalgae_site_selection as m


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    return m.load_country_data(m.DEFAULT_DATA)


def test_weights_sum_to_one():
    m.validate_weights()


def test_bad_scenario_weights_rejected():
    bad = {"X": dict(m.SCENARIOS["Base Case"], strategic_risk=0.25)}
    with pytest.raises(m.DataValidationError):
        m.validate_weights(scenarios=bad)


def test_input_data_valid(raw):
    report = m.validate_input_data(raw)
    assert set(report["severity"]) <= {"warning"}


def test_duplicate_country_rejected(raw):
    dup = pd.concat([raw, raw[raw["country"] == "Brazil"].head(1)])
    with pytest.raises(m.DataValidationError):
        m.validate_input_data(dup)


def test_off_scale_qualitative_rejected(raw):
    bad = raw.copy()
    bad.loc[(bad.country == "Brazil") & (bad.metric_id == "cr_existing_manufacturing"), "raw_value"] = 8.0
    with pytest.raises(m.DataValidationError):
        m.validate_input_data(bad)


def test_missing_value_not_zero(raw):
    data = m.add_derived_metrics(raw)
    scores = m.score_metrics(data)
    chile = scores[(scores.country == "Chile") & (scores.metric_id == "pe_sugar_production")]
    assert chile["normalized_score"].isna().all()
    sub = m.calculate_subcriterion_scores(scores)
    row = sub[(sub.country == "Chile") & (sub.subcriterion == "pe_sugar")].iloc[0]
    # Only the rubric metric remains, so the sub-score equals it rather than being halved.
    assert row["score"] == pytest.approx(2.5)
    assert "pe_sugar_production" in row["missing_metrics"]


def test_normalisation_direction_and_caps():
    spec = m.METRIC_INDEX["pe_electricity_price"]  # lower is better
    s = m.normalize_metric(pd.Series([0.03, 0.06, 0.155, 0.25, 0.40]), spec)
    assert list(s.round(2)) == [10.0, 10.0, 5.0, 0.0, 0.0]
    log_spec = m.METRIC_INDEX["ma_aquafeed_volume"]
    assert m.normalize_metric(pd.Series([100.0]), log_spec).iloc[0] == 10.0


def test_scores_in_range_and_formula(raw):
    results = m.run(output_dir=m.BASE_DIR / "outputs", make_charts=False)
    assert results["score"].between(0, 10).all()
    w = m.SCENARIOS["Base Case"]
    manual = sum(results[c] * w[c] for c in m.CRITERIA)
    assert np.allclose(manual, results["score"])
