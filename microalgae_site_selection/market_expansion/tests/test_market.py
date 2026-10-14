"""Checks on denominators, units, double counting, rules and the optimiser (run: python -m pytest -q tests)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import data as D  # noqa: E402
from src import decision as X  # noqa: E402
from src import export as XP  # noqa: E402
from src import model as M  # noqa: E402


@pytest.fixture(scope="module")
def ctx():
    cfg = D.load_config()
    d = D.load_all(cfg)
    seg = M.segments_df(cfg, d)
    mkt = M.market_table(cfg, d, seg)
    return cfg, d, seg, mkt


def test_funnel_ordering_and_units(ctx):
    cfg, d, seg, _ = ctx
    assert (seg.sam_dha_t <= seg.tam_dha_t + 1e-9).all()
    assert (seg.algal_dha_t <= seg.sam_dha_t + 1e-9).all()
    assert (seg.som_dha_t <= seg.algal_dha_t + 1e-9).all()
    assert (seg.som_sku_t <= seg.inclusion_cap_sku_t + 1e-9).all()
    row = seg[(seg.country == "Norway") & (seg.stage == "grow_out") & (seg.year == 2025)].iloc[0]
    # 2.47 Mt feed x 0.79 x 10 g/kg x 0.5 DHA share = 9,756.5 t DHA (g/kg x t / 1000 -> t)
    assert row.tam_dha_t == pytest.approx(2_470_000 * 0.79 * 10 / 1000 * 0.5)
    sku_from_dha = row.som_dha_t / (d["A"]["dha_fraction_sku"]["base"] * d["A"]["formulation_efficiency"]["base"])
    assert row.som_sku_t == pytest.approx(sku_from_dha)


def test_feed_from_production_and_fcr(ctx):
    _, _, seg, _ = ctx
    ecu = seg[(seg.country == "Ecuador") & (seg.year == 2025)].groupby("stage").stage_feed_t.sum().sum()
    assert ecu == pytest.approx(1_700_000 * 1.43 * 0.95)  # production x eFCR x commercial share
    assert 2.0e6 < ecu < 2.7e6  # cross-check with Aprobal-derived ~2.5 Mt


def test_no_double_counting_country_vs_totals(ctx):
    cfg, _, seg, mkt = ctx
    for y in (2030, 2035):
        by_country = seg[seg.year == y].groupby("country").som_sku_t.sum().sum()
        assert by_country == pytest.approx(seg[seg.year == y].som_sku_t.sum())
    assert not mkt.duplicated(["country", "application"]).any()
    cust = D.raw(cfg, "customer_evidence.csv")
    acc = X.account_ranking(cust, mkt)
    # accounts reuse segment volume as context only; no account volume is summed into the total
    assert "account_share_of_segment" in acc and (acc["account_share_of_segment"].str.contains("unknown")).all()


def test_dha_is_not_epa_and_content_bounds(ctx):
    _, d, _, _ = ctx
    n = d["nutrition"]
    assert (n.dha_share_of_target < 1).all()
    bad = n.copy()
    bad.loc[0, "dha_share_of_target"] = 1.0
    with pytest.raises(D.InputError):
        D.validate_nutrition(bad)
    assert 0 < d["A"]["dha_fraction_sku"]["base"] <= 1


def test_stage_shares_and_fcr_rules(ctx):
    _, d, _, _ = ctx
    bad = d["nutrition"].copy()
    bad.loc[0, "feed_share"] += 0.1
    with pytest.raises(D.InputError):
        D.validate_nutrition(bad)
    f = d["feed"].copy()
    f.loc[f.country == "Chile", "fcr"] = 4.0
    with pytest.raises(D.InputError):
        D.validate_feed(f)
    dup = pd.concat([d["feed"], d["feed"].head(1)])
    with pytest.raises(D.InputError):
        D.validate_feed(dup)


def test_historical_is_not_current(ctx):
    _, d, _, _ = ctx
    c = d["customers"].copy()
    c.loc[c.entity == "Thai Union / Thai Union Feedmill", "relationship_status"] = "documented_current"
    with pytest.raises(D.InputError):
        D.validate_customers(c)  # 2020 evidence cannot support a 'current' relationship


def test_no_contract_invented_and_export_schema(ctx):
    cfg, d, seg, mkt = ctx
    dem = XP.demand_for_v3(cfg, d, seg, "base")
    assert (dem.contracted_volume_t == 0).all()
    assert set(dem.opportunity_status) <= {"qualified_pipeline", "unqualified_potential"}
    XP.validate_against_v3(cfg, dem)  # raises if the v3 schema/rules are broken
    vol = dem.eligible_final_product_t * dem.inclusion_rate * dem.expected_supplier_share
    for y in (2030, 2035):
        assert vol[dem.year == y].sum() == pytest.approx(mkt[f"incremental_sku_{y}_t"].sum(), rel=1e-6)


def test_b2b_not_retail_and_targets_not_volume(ctx):
    cfg, d, seg, _ = ctx
    assert "retail" not in " ".join(seg.columns)
    rec = XP.reconciliation(cfg, d, seg)
    nutr = rec[rec.check.str.contains("Nutrition sales 2024")].iloc[0]
    assert nutr.status == "INCOMPATIBLE SCOPES"  # revenue target is never converted into feed demand
    gmi = rec[rec.check.str.contains("GMI")].iloc[0]
    assert gmi.status == "REJECTED"


def test_captured_volume_within_capacity_in_portfolio(ctx):
    cfg, d, _, mkt = ctx
    sel, info = X.optimise_portfolio(cfg, d, mkt)
    assert info["success"]
    assert info["incremental_sku_2030_t"] <= d["A"]["capacity_increment_2030_t"]["base"] + 1e-6
    tight, _ = X.optimise_portfolio(cfg, d, mkt, {"capacity_increment_2030_t": 1000})
    assert (tight.incremental_sku_2030_t * tight.selected).sum() <= 1000 + 1e-6


def test_milp_matches_brute_force(ctx):
    cfg, d, _, mkt = ctx
    A = {k: v["base"] for k, v in d["A"].items()}
    for over in ({}, {"fte_budget": 1.5}, {"max_country_share": 0.5}, {"capacity_increment_2030_t": 2000}):
        AA = dict(A, **over)
        _, info = X.optimise_portfolio(cfg, d, mkt, over)
        assert info["objective_npv_musd"] == pytest.approx(X.brute_force(mkt.reset_index(drop=True), AA), abs=1e-6)


def test_sensitivity_directions(ctx):
    cfg, d, _, _ = ctx
    lo = M.market_table(cfg, d, M.segments_df(cfg, d, "base", {"price": 15}))
    hi = M.market_table(cfg, d, M.segments_df(cfg, d, "base", {"price": 40}))
    assert hi.commercial_npv_musd.sum() > lo.commercial_npv_musd.sum()
    a = M.segments_df(cfg, d, "base", {"share_mult": 0.6})
    b = M.segments_df(cfg, d, "base", {"share_mult": 1.4})
    assert b.som_sku_t.sum() > a.som_sku_t.sum()
    m_lo = M.segments_df(cfg, d, "base", {"marine_mult": 1.2})
    m_hi = M.segments_df(cfg, d, "base", {"marine_mult": 0.8})
    assert m_hi.sam_dha_t.sum() > m_lo.sam_dha_t.sum()  # less marine supply -> more algal space


def test_scenarios_ordered(ctx):
    cfg, d, _, _ = ctx
    t = {sc: M.segments_df(cfg, d, sc) for sc in ("low", "base", "high")}
    s = {k: v[v.year == 2030].som_sku_t.sum() for k, v in t.items()}
    assert s["low"] < s["base"] < s["high"]


def test_source_rules(ctx):
    _, d, _, _ = ctx
    bad = d["sources"].copy()
    bad.loc[0, "vintage"] = np.nan
    with pytest.raises(D.InputError):
        D.validate_sources(bad)
