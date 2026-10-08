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
    data = raw.copy()
    mask = (data.country == "Chile") & (data.metric_id == "pe_sugar_production")
    data.loc[mask, "raw_value"] = np.nan
    data.loc[mask, "value_type"] = "missing"
    m.validate_input_data(data)  # a flagged gap is a warning, not an error
    scores = m.score_metrics(m.add_derived_metrics(data))
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


def test_scores_in_range_and_formula(raw, tmp_path):
    results = m.run(output_dir=tmp_path, make_charts=False, mc_sims=200)
    assert results["score"].between(0, 10).all()
    w = m.SCENARIOS["Base Case"]
    manual = sum(results[c] * w[c] for c in m.CRITERIA)
    assert np.allclose(manual, results["score"])


# --------------------------------------------------------------------------- #
# v2 additions                                                                #
# --------------------------------------------------------------------------- #

def test_explicit_zero_scores_zero_not_missing():
    spec = m.METRIC_INDEX["pe_sugar_production"]
    s = m.normalize_metric(pd.Series([0.0, np.nan]), spec)
    assert s.iloc[0] == 0.0 and np.isnan(s.iloc[1])


def test_export_only_distance_excludes_home_market(raw):
    exp = m.add_derived_metrics(raw, "export_only")
    inc = m.add_derived_metrics(raw, "include_domestic")
    get = lambda d, c: d[(d.country == c) & (d.metric_id == "ma_distance_priority_markets")]["raw_value"].iloc[0]
    assert get(exp, "China") > get(inc, "China")  # home market no longer counts as 0 km
    assert get(exp, "Brazil") == get(inc, "Brazil")  # non-priority countries unchanged


def test_monte_carlo_without_noise_matches_deterministic(raw, monkeypatch):
    data = m.add_derived_metrics(raw)
    monkeypatch.setattr(m, "MC_QUANT_SIGMA", {"High": 0.0, "Medium": 0.0, "Low": 0.0})
    monkeypatch.setattr(m, "MC_RUBRIC_SHIFT_PROB", {"High": 0.0, "Medium": 0.0, "Low": 0.0})
    mc = m.run_monte_carlo(data, n_sims=3)
    det = m.score_pipeline(data)
    assert np.allclose(mc["score_mean"].sort_index(), det["score"].sort_index())


def test_rubric_raters_median_and_agreement(raw, tmp_path):
    extra = pd.DataFrame([
        dict(country="Brazil", metric_id="cr_existing_manufacturing", rater="corbion", score=7.5),
        dict(country="Brazil", metric_id="cr_existing_manufacturing", rater="agroinsper", score=7.5),
    ])
    path = tmp_path / "ratings.csv"
    extra.to_csv(path, index=False)
    out, agr = m.apply_rubric_ratings(raw, path)
    val = out[(out.country == "Brazil") & (out.metric_id == "cr_existing_manufacturing")]["raw_value"].iloc[0]
    assert val == 7.5  # median of 10, 7.5, 7.5
    row = agr[agr.metric_id == "cr_existing_manufacturing"].iloc[0]
    assert row["n_raters"] == 3 and row["within_one_level_pct"] == 100.0


def test_breakeven_found_between_scenarios(raw):
    crit = m.calculate_criterion_scores(m.calculate_subcriterion_scores(m.score_metrics(m.add_derived_metrics(raw))))
    be = m.find_breakeven(m.thesis_weight_sweep(crit, "market_access"), "Brazil", "Thailand")
    assert be is None or 0.05 <= be <= 0.6


def test_economics_assumptions_and_msp():
    import brazil_thailand_economics as e
    df = e.load_assumptions()
    res = e.base_results(df)
    assert (res["msp_per_t"] > res["cash_cost_per_t"]).all()
    # Pillar Two: removing the 15% floor can only lower Thailand's required price.
    p = e.case_parameters(df, e.TH)
    assert e.evaluate(p, holiday_floor=0.0).msp <= e.evaluate(p).msp + 1e-6
