import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import plant as P  # noqa: E402
from src import scoring as S  # noqa: E402
from src import searoutes as SR  # noqa: E402


@pytest.fixture(scope="module")
def res():
    return P.run(n_mc=60, n_dir=300)


def test_weights_and_structure():
    m = S.Model.from_config(P.load_config())
    assert m.scenarios["Base Case"] == {"production_economics": 0.30, "market_access": 0.20, "corbion_readiness": 0.15,
                                       "regulation_incentives": 0.15, "strategic_risk": 0.20}
    assert sum(m.nominal_weight(k) for k in m.metrics) == pytest.approx(1.0)


def test_goalposts_fixed_and_capped():
    m = S.Metric("x", "s", 1.0, "linear", "x", worst=100, best=0)
    s = S.normalise(pd.Series([150, 100, 50, 0, -10]), m)
    assert list(s) == [0, 0, 5, 10, 10]
    lg = S.Metric("y", "s", 1.0, "log", "y", worst=1, best=100)
    assert S.normalise(pd.Series([10.0]), lg).iloc[0] == pytest.approx(5)


def test_missing_is_not_zero(res):
    t = res["table"]
    for c in t.index:
        assert t.score_if_missing_0[c] <= t.score[c] + 1e-9 <= t.score_if_missing_10[c] + 2e-9


def test_score_equals_weighted_criteria(res):
    t, model = res["table"], res["model"]
    w = model.scenarios[model.base]
    for c in t.index:
        crit = t.loc[c, list(w)].astype(float)
        if crit.notna().all():
            assert t.score[c] == pytest.approx(sum(crit[k] * w[k] for k in w), abs=0.01)


def test_adding_a_country_does_not_change_others():
    cfg = P.load_config()
    m = S.Model.from_config(cfg)
    data, _ = P.derive(P.load_inputs(), cfg)
    v = S.wide_values(m, data).reindex(P.COUNTRIES).apply(pd.to_numeric, errors="coerce")
    s1, _, _ = S.aggregate(m, S.metric_scores(m, v))
    v2 = pd.concat([v, v.loc[["Brazil"]].rename(index={"Brazil": "Clone"}) * 1.3])
    s2, _, _ = S.aggregate(m, S.metric_scores(m, v2))
    assert np.allclose(s1.values, s2.loc[s1.index].values)


def test_every_scored_value_has_source(res):
    d = pd.read_csv(P.PROC / "plant_inputs_long.csv")
    scored = d[d.metric_id.isin(res["model"].metrics)]
    assert scored.source_name.notna().all()
    assert scored.value_type.isin(["reported", "estimate", "proxy"]).all()


def test_sea_routes_sane():
    ports = {"santos": ((-46.33, -23.96), ["w_atl_s"]), "rotterdam": ((4.0, 51.95), ["w_channel", "w_north_sea"]),
             "laem": ((100.88, 13.08), ["w_gulf_thai"])}
    g = SR.build_graph(ports)
    d1 = SR.shortest_nm(g, "santos", "rotterdam")
    assert 5000 < d1 < 6200  # published ~5,450 nm
    d2 = SR.shortest_nm(g, "laem", "rotterdam")
    assert 8500 < d2 < 10000  # via Suez ~9,300 nm
    assert SR.shortest_nm(g, "santos", "laem") > SR.gc_nm((-46.33, -23.96), (100.88, 13.08))


def test_transit_weighted_uses_market_weights(res):
    w = res["weights"]
    assert w.sum() == pytest.approx(1.0)
    tm = res["tm"]
    for c in ["Brazil", "Thailand"]:
        t = tm[tm.origin == c].set_index("market").door_to_door_days
        val = res["data"]
        v = float(val[(val.country == c) & (val.metric_id == "ma_transit_days_weighted")].raw_value.iloc[0])
        assert v == pytest.approx(float((t.reindex(w.index) * w).sum()), abs=0.01)


def test_effective_tax_floor():
    d = pd.DataFrame([dict(country="Thailand", metric_id=k, raw_value=v, unit="", reference_year="", source_name="t",
                           source_url="", date_accessed="", value_type="reported", confidence="High", notes="")
                      for k, v in [("ri_corporate_tax_rate", 20), ("ri_tax_holiday_years", 8), ("ri_incentive_rate", 0)]])
    out, _ = P.derive(d, P.load_config())
    eff = float(out[(out.country == "Thailand") & (out.metric_id == "ri_effective_tax_10y")].raw_value.iloc[0])
    assert eff == pytest.approx((8 * 15 + 2 * 20) / 10)


def test_v2_baseline_still_reproduced():
    v2 = pd.read_csv(P.PARENT / "v3" / "data" / "raw" / "frozen_v2" / "v2_country_scores.csv")
    assert v2.sort_values("score", ascending=False).country.iloc[0] == "Brazil"
