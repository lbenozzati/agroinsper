import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import market as M  # noqa: E402


@pytest.fixture(scope="module")
def res():
    cfg = M.load_config()
    data = M.load_inputs()
    return cfg, {n: M.run_niche(cfg, data, n, 40, 300) for n in cfg["niches"]}


def test_models_valid_and_weights_sum():
    cfg = M.load_config()
    for n in cfg["niches"]:
        m = M.niche_model(cfg, n)
        assert sum(m.nominal_weight(k) for k in m.metrics) == pytest.approx(1.0)


def test_every_country_ranked_once(res):
    cfg, r = res
    for n, x in r.items():
        t = x["table"]
        assert sorted(t.index) == sorted(cfg["niches"][n]["countries"])
        assert t["rank"].min() == 1


def test_low_coverage_metrics_dropped(res):
    cfg, r = res
    for n, x in r.items():
        cov = pd.read_csv(M.OUT / f"market_metric_coverage_{n}.csv")
        assert (cov[~cov.used].coverage < cfg["min_metric_coverage"]).all()
        assert (cov[cov.used].coverage >= cfg["min_metric_coverage"]).all()


def test_dha_need_formula(res):
    cfg, r = res
    d = r["salmon"]["data"]
    feed = float(d[(d.country == "Norway") & (d.metric_id == "sal_feed_t")].raw_value.iloc[0])
    need = float(d[(d.country == "Norway") & (d.metric_id == "dha_need_t")].raw_value.iloc[0])
    assert need == pytest.approx(feed * cfg["dha_g_per_kg_feed"]["salmon"] / 1000, rel=1e-3)


def test_overall_is_dha_weighted_average(res):
    _, r = res
    ov, pairs = M.overall(r)
    for c in ["United States", "China", "Norway"]:
        g = pairs[pairs.country == c]
        w = g.dha_need_t / g.dha_need_t.sum()
        assert ov.overall_score[c] == pytest.approx(float((g.score * w).sum()))
    assert ov.overall_score.between(0, 10).all()


def test_country_names_normalised():
    d = M.load_inputs()
    assert not d.country.str.contains(r"\(").any()


def test_insufficient_data_ranked_last(res):
    _, r = res
    for x in r.values():
        t = x["table"]
        if (t.data_status != "ok").any():
            assert t[t.data_status != "ok"]["rank"].min() > t[t.data_status == "ok"]["rank"].max()
