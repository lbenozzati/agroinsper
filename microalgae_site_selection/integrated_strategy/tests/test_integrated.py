"""Integration checks: conservation, units, legality, solver, DCF consistency, JS parity, statistics discipline."""

import copy
import itertools
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import integration as I  # noqa: E402
from src import policies as P  # noqa: E402
from src import stats as ST  # noqa: E402


@pytest.fixture(scope="module")
def ctx():
    cfg = I.load_config()
    up = I.Upstream(cfg)
    segs = {sc: up.market_segments(sc) for sc in cfg["market_scenarios"]}
    comp, flows, alloc, store = P.compare(up, cfg, segs)
    return cfg, up, segs, comp, alloc, store


def test_flow_conservation_and_capacity(ctx):
    cfg, up, segs, comp, alloc, store = ctx
    for (sc, key), (p, res, dem) in store.items():
        for i, y in enumerate(res["years"]):
            a = alloc[(alloc.market_scenario == sc) & (alloc.policy == key) & (alloc.year == y)].allocated_t.sum()
            assert a == pytest.approx(res["sold_t"][i], abs=1e-6)
            assert res["sold_t"][i] <= res["capacity_t"][i] + 1e-6
            assert res["sold_t"][i] <= sum(p["demand"][r][str(y)] for r in p["regions"]) + 1e-6
        assert p["dha_fraction"] == cfg["dha_fraction_canonical"]


def test_demand_not_duplicated_and_reconciled(ctx):
    cfg, up, segs, *_ = ctx
    p, dem, seg = I.integrated_params(up, cfg, "base", segs["base"])
    key = ["market", "country", "application", "customer", "product_sku", "year", "opportunity_status"]
    assert not dem.duplicated(key).any()
    assert (dem.contracted_volume_t == 0).all()  # no contract invented
    rec = I.reconciliation(up, cfg, p, dem, seg)
    assert not (rec.status == "MISMATCH").any()


def test_units_and_route_identity(ctx):
    cfg, up, segs, *_ = ctx
    p, _, seg = I.integrated_params(up, cfg, "base", segs["base"])
    routes = I.route_economics(up, cfg, p, seg, pd.read_csv(ROOT / "data/raw/tariff_assumptions.csv"))
    r = routes.iloc[0]
    assert r.contribution_usd_t == pytest.approx(r.net_price_usd_t - r.variable_cost_usd_t - r.freight_usd_t
                                                 - r.transit_inventory_usd_t - r.duty_usd_t)  # each cost deducted once
    assert r.contribution_usd_kg_dha == pytest.approx(r.contribution_usd_t / (p["dha_fraction"] * 1000))
    infl = up.v3e.infl(p, int(r.year))
    assert r.variable_cost_usd_t == pytest.approx(up.v3e.variable_cost(p, r.origin_site) * infl)
    m = seg[(seg.country == r.dest_country) & (seg.year == r.year)].price_usd_kg_dha.iloc[0]
    deduct = up.dm["A"]["commercial_cost_pct"]["base"] + up.dm["A"]["rebate_pct"]["base"]
    assert r.net_price_usd_t == pytest.approx(m * (1 - deduct) * p["dha_fraction"] * 1000 * infl)


def test_no_illegal_china_route(ctx):
    cfg, up, segs, comp, alloc, store = ctx
    p, res, _ = store[("high", "B_ORI_TH_NOW")]
    th = p["sites"]["TH_NSN"]
    online = th["first_capex"] + th["build"]
    series = res["sold_by_site_region"].get("TH_NSN|CHINA", [0.0] * len(res["years"]))
    for i, y in enumerate(res["years"]):
        if y < online + th["gacc_delay"]:
            assert series[i] == 0.0


def test_integrated_engine_reproduces_standalone_dcf(ctx):
    cfg, up, *_ = ctx
    p = copy.deepcopy(up.p0)
    dem, _ = up.v3d.load_demand(up.c3, up.a3)
    p["demand"] = up.v3d.weighted_demand(dem, p["scenario_weights"]["base"], p["regions"], up.v3e.years(p))
    integ = P.evaluate(up, p, cfg["policies"]["A_ORI_1"])["npv"]
    ref = pd.read_csv(up.v3_dir / "outputs" / "npv_by_scenario.csv")
    ref = ref[(ref.scenario == "base") & (ref.alternative == "A1_ORI")].npv_musd.iloc[0]
    assert integ / 1e6 == pytest.approx(ref, rel=1e-9)


def test_solver_matches_manual_small_case(ctx):
    _, up, *_ = ctx
    supply = {"BR": 10.0, "TH": 6.0}
    demand = {"R1": 8.0, "R2": 9.0}
    edges = {("BR", "R1"): (10.0, 8.0), ("BR", "R2"): (9.0, 9.0), ("TH", "R1"): (9.0, 8.0), ("TH", "R2"): (1.0, 9.0)}
    flows = up.v3e.allocate(supply, demand, edges)
    got = sum(edges[k][0] * v for k, v in flows.items())
    best = 0.0
    for a, b in itertools.product(np.arange(0, 10.5, 0.5), repeat=2):  # BR->R1 = a, TH->R1 = b (grid search)
        br_r2 = min(supply["BR"] - a, demand["R2"])
        th_r2 = min(supply["TH"] - b, demand["R2"] - br_r2)
        if a + b > demand["R1"] or a > supply["BR"] or b > supply["TH"] or th_r2 < 0:
            continue
        best = max(best, 10 * a + 9 * br_r2 + 9 * b + 1 * th_r2)
    assert got == pytest.approx(best)


def test_correlation_matrix_psd(ctx):
    _, up, *_ = ctx
    d = P.joint_draws(up, 500, 1)
    assert np.min(np.linalg.eigvalsh(d.attrs["corr"])) > -1e-10
    r = np.corrcoef(d.fish_oil, d.m_adopt)[0, 1]
    assert 0.2 < r < 0.6


def test_statistics_refuse_short_series_and_work_on_long():
    x = pd.Series([1.0, 2.0, 3.0])
    assert ST.empirical_correlation(x, x)["status"].startswith("not computed")
    rng = np.random.default_rng(0)
    a = pd.Series(np.cumsum(rng.normal(size=80)))
    b = a + pd.Series(rng.normal(scale=0.5, size=80))
    res = ST.empirical_correlation(a, b)
    assert res["status"].startswith("computed") and res["pearson"] > 0.5
    inv = ST.series_status(pd.read_csv(ROOT / "data/raw/series_inventory.csv"))
    assert not inv.correlation_computed.any()


def test_no_contracts_no_demand_gives_conditional_wait(ctx):
    cfg, up, *_ = ctx
    p, _, _ = I.integrated_params(up, cfg, "base", up.market_segments("base"))
    p["demand"] = {r: {y: 0.0 for y in v} for r, v in p["demand"].items()}
    key, val = P.best_policy(up, cfg, p)
    assert key == "WAIT" and val == 0.0


def test_contract_threshold_bounds(ctx):
    cfg, up, segs, *_ = ctx
    v = P.contracted_needed(up, cfg, segs["base"], "A_ORI_1", None, 0.5)
    assert v is None or 0 <= v <= 40000
    p, _, _ = I.integrated_params(up, cfg, "base", segs["base"], contracted_t=v, asia_share=0.5,
                                  weights={"contracted": 1.0, "qualified_pipeline": 0.0, "unqualified_potential": 0.0})
    assert P.evaluate(up, p, cfg["policies"]["A_ORI_1"])["npv"] >= -1e3


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_cockpit_js_matches_python(ctx, tmp_path):
    cfg, up, segs, comp, alloc, store = ctx
    p, res, _ = store[("high", "B_ORI_TH_NOW")]
    payload = {"p": p, "policies": cfg["policies"]}
    (tmp_path / "in.json").write_text(json.dumps(payload))
    js = ("const E=require(process.argv[1]);const j=require(process.argv[2]);const o={};"
          "for(const k in j.policies){const pol=j.policies[k];if(!pol.units.length){o[k]=0;continue;}"
          "o[k]=E.runAlternative(j.p,{units:pol.units,hub:!!pol.hub}).npv;}console.log(JSON.stringify(o));")
    got = json.loads(subprocess.check_output(["node", "-e", js, str(up.v3_dir / "src" / "cockpit_engine.js"),
                                              str(tmp_path / "in.json")], text=True))
    for k, pol in cfg["policies"].items():
        assert got[k] == pytest.approx(P.evaluate(up, p, pol)["npv"], rel=1e-9, abs=1e-3)


def test_regression_high_scenario_grid_point_terminates(ctx):
    """Regression for the allocation cycle found at (high market, no contract, price x1.2)."""
    cfg, up, segs, *_ = ctx
    p, _, _ = I.integrated_params(up, cfg, "high", segs["high"], contracted_t=0, asia_share=1.0, price_mult=1.2)
    res = P.evaluate(up, p, cfg["policies"]["B_ORI_TH_NOW"])
    assert res["npv"] > 0
