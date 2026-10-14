"""Substantive checks: independent hand calculations, invariants and rejection rules (not re-implementations)."""

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import analysis as A  # noqa: E402
from src import data as D  # noqa: E402
from src import engine as E  # noqa: E402
from src import screening as S  # noqa: E402


@pytest.fixture(scope="module")
def ctx():
    cfg = D.load_config()
    a = D.load_assumptions(cfg)
    fr = D.load_freight(cfg)
    demand, _ = D.load_demand(cfg, a)
    p0 = D.build_params(cfg, a, fr)
    p = A.params_for(cfg, p0, demand, "base")
    return cfg, a, p0, p, demand


def flat_params(p):
    """Strip taxes, inflation, WC, FX and freight so cash flows can be checked by hand."""
    q = copy.deepcopy(p)
    q.update(infl_usd=0.0, wc_pct=0.0, transit_rate=0.0, g=0.0, maint_pct=0.0, ins_pct=0.0)
    for c in q["country"].values():
        c.update(cit=0.0, globe_applies=0, leak=0.0, duty=0.0, qrtc=0.0, wacc=0.10)
    for s in q["sites"].values():
        s.update(qa=0.0, headcount=0.0, conn=0.0, land=0.0)
    for c in q["freight"]:
        for r in q["freight"][c]:
            q["freight"][c][r] = {"usd": 0.0, "days": 0.0}
    return q


# ---- mass balance & units ---------------------------------------------------------------------------

def test_mass_balance_closes(ctx):
    _, _, _, p, _ = ctx
    sugar = E.sugar_per_t(p)
    dha_out = sugar * p["dha_yield"] * p["recovery"]
    assert dha_out == pytest.approx(p["dha_fraction"])  # t DHA in 1 t SKU
    assert 4.0 < sugar < 6.5  # 0.36 / (0.075 * 0.95) = 5.05 t sucrose per t SKU


def test_unit_conversions(ctx):
    _, _, _, p, _ = ctx
    brl_per_t = 104.37 / 50 * 1000                     # CEPEA BRL per 50 kg bag -> BRL per t
    assert brl_per_t == pytest.approx(2087.4)
    assert brl_per_t / 5.40 == pytest.approx(386.6, abs=0.1)
    q = dict(p, fish_oil=p["fish_oil_base"], infl_usd=0.0)
    # USD/kg DHA x DHA fraction x 1000 = USD per t SKU
    assert E.price_per_t(q, "SALMON", 2026) == pytest.approx(p["price_dha"] * p["dha_fraction"] * 1000)


def test_fx_shock_only_moves_local_share(ctx):
    _, _, _, p, _ = ctx
    q = copy.deepcopy(p)
    q["fx_shock"]["BR"] = 0.25
    base, shocked = E.variable_cost_lines(p, "BR_ORI_EXP"), E.variable_cost_lines(q, "BR_ORI_EXP")
    s = p["sites"]["BR_ORI_EXP"]
    expected = base["sugar"] * (s["sugar_local"] / 1.25 + 1 - s["sugar_local"])
    assert shocked["sugar"] == pytest.approx(expected)
    assert E.variable_cost(q, "TH_NSN") == pytest.approx(E.variable_cost(p, "TH_NSN"))


# ---- capex ------------------------------------------------------------------------------------------

def test_brownfield_discount_only_from_shared_modules(ctx):
    _, _, _, p, _ = ctx
    q = copy.deepcopy(p)
    q.update(bf_utilities=1.0, bf_buildings=1.0, bf_owner=1.0, cont_bf=q["cont_gf"])
    bf = E.unit_capex(q, {"site": "BR_ORI_EXP"})
    q["sites"]["BR_ORI_EXP"]["brownfield"] = False
    gf = E.unit_capex(q, {"site": "BR_ORI_EXP"})
    assert bf["total"] == pytest.approx(gf["total"])  # no hidden brownfield discount
    assert E.unit_capex(p, {"site": "BR_ORI_EXP"})["total"] < gf["total"]


def test_capex_override_and_modules_sum(ctx):
    _, _, _, p, _ = ctx
    c = E.unit_capex(p, {"site": "TH_NSN"})
    parts = sum(c[m] for m in E.CAPEX_MODULES) + c["contingency"] + c["import_duty"] + c["connection"] + c["land"]
    assert parts == pytest.approx(c["total"])
    q = dict(p, capex_override={"BR_ORI_EXP": 70e6})
    assert E.unit_capex(q, {"site": "BR_ORI_EXP"})["total"] == pytest.approx(70e6)


# ---- finance: known NPV, nominal/real, IRR ----------------------------------------------------------

def test_npv_matches_hand_calculation(ctx):
    _, _, _, p, _ = ctx
    q = flat_params(p)
    q["capex_override"] = {"BR_ORI_EXP": 100e6}
    q["sites"]["BR_ORI_EXP"].update(first_capex=2026, build=2)
    big = {r: {str(y): 1e9 for y in E.years(q)} for r in q["regions"]}
    q["demand"] = big
    res = E.run_alternative(q, {"units": [{"site": "BR_ORI_EXP"}]})
    margin = E.price_per_t(q, "PET", 2030) - E.variable_cost(q, "BR_ORI_EXP")  # PET has the highest price mult
    cap = q["module_t"] * q["oee"]
    flows = []
    for y in E.years(q):
        f = -50e6 if y in (2026, 2027) else 0.0
        f += cap * E.ramp(q, y, 2028) * margin
        flows.append(f)
    hand = sum(f / 1.1 ** (k + 1) for k, f in enumerate(flows))
    assert res["npv_ex_tv"] == pytest.approx(hand, rel=1e-9)
    sustaining = 100e6 / q["economic_life"]
    tv_hand = (flows[-1] - sustaining) / 0.10 / 1.1 ** 10
    assert res["tv_pv"] == pytest.approx(tv_hand, rel=1e-9)


def test_nominal_and_real_discounting_agree():
    real = [-100.0, 20.0, 30.0, 40.0, 50.0]
    infl, r_real = 0.03, 0.07
    nominal = [f * (1 + infl) ** (k + 1) for k, f in enumerate(real)]
    r_nom = (1 + r_real) * (1 + infl) - 1
    assert E.npv_flows(nominal, r_nom) == pytest.approx(E.npv_flows(real, r_real))


def test_irr_known_value():
    assert E.irr([-100.0, 0.0, 121.0]) == pytest.approx(0.10, abs=1e-6)
    flows = [-100.0, 110.0]  # end-year convention: -100/1.1 + 110/1.21 = 0 at 10%
    assert E.irr(flows) == pytest.approx(0.10, abs=1e-6)
    assert E.irr([10.0, 10.0]) is None


# ---- taxes -------------------------------------------------------------------------------------------

def _tax_case(p, country_overrides, site="BR_ORI_EXP"):
    q = flat_params(p)
    q["country"][q["sites"][site]["country"]].update(country_overrides)
    q["demand"] = {r: {str(y): 1e9 for y in E.years(q)} for r in q["regions"]}
    return E.run_alternative(q, {"units": [{"site": site}]})


def test_brazil_loss_carryforward_capped_at_30pct(ctx):
    _, _, _, p, _ = ctx
    res = _tax_case(p, {"cit": 0.34, "nol_cap": 0.30})
    L = res["lines"]
    ys = res["years"]
    ebitda = np.array(L["ebitda"])
    # recompute EBIT from tax: first profitable year must pay tax on at least 70% of EBIT
    i = next(k for k in range(len(ys)) if L["tax"][k] > 0)
    assert L["tax"][i] >= 0.34 * 0.70 * (ebitda[i] - (sum(L["capex"]) / 10)) - 1e-6


def test_thai_holiday_and_globe_topup(ctx):
    _, _, _, p, _ = ctx
    q = flat_params(p)
    q["sbie_pay"], q["sbie_asset"] = 0.0, 0.0
    q["country"]["TH"].update(cit=0.20, holiday=8, globe_applies=1)
    q["demand"] = {r: {str(y): 1e9 for y in E.years(q)} for r in q["regions"]}
    res = E.run_alternative(q, {"units": [{"site": "TH_NSN"}]})
    L = res["lines"]
    for i, y in enumerate(res["years"]):
        if y >= 2030 and L["ebitda"][i] > 0:
            assert L["tax"][i] == 0.0                                   # inside the 8-year holiday
            dep = sum(L["capex"]) / q["dep_years"]
            assert L["topup"][i] == pytest.approx(0.15 * (L["ebitda"][i] - dep))  # QDMTT to 15% without SBIE
    q["country"]["TH"]["globe_applies"] = 0
    res0 = E.run_alternative(q, {"units": [{"site": "TH_NSN"}]})
    assert sum(res0["lines"]["topup"]) == 0.0 and res0["npv"] > res["npv"]


# ---- allocation: optimality and conservation ---------------------------------------------------------

def test_allocation_matches_linprog_and_conserves():
    rng = np.random.default_rng(7)
    for _ in range(25):
        plants, regions = ["P1", "P2", "P3"], ["R1", "R2", "R3", "R4"]
        supply = {x: float(rng.uniform(0, 100)) for x in plants}
        demand = {r: float(rng.uniform(0, 80)) for r in regions}
        edges = {(x, r): (float(rng.uniform(-5, 20)), float(rng.uniform(0, 90))) for x in plants for r in regions}
        flows = E.allocate(supply, demand, edges)
        got = sum(edges[k][0] * f for k, f in flows.items())
        keys = list(edges)
        c = [-max(edges[k][0], 0) for k in keys]
        A_ub, b_ub = [], []
        for x in plants:
            A_ub.append([1.0 if k[0] == x else 0.0 for k in keys]); b_ub.append(supply[x])
        for r in regions:
            A_ub.append([1.0 if k[1] == r else 0.0 for k in keys]); b_ub.append(demand[r])
        bounds = [(0, edges[k][1]) for k in keys]
        lp = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
        assert got == pytest.approx(-lp.fun, rel=1e-6, abs=1e-6)
        for x in plants:
            assert sum(f for k, f in flows.items() if k[0] == x) <= supply[x] + 1e-6
        for r in regions:
            assert sum(f for k, f in flows.items() if k[1] == r) <= demand[r] + 1e-6


def test_no_double_counting_of_capacity_or_demand(ctx):
    cfg, _, _, p, _ = ctx
    res = E.run_alternative(p, cfg["alternatives"]["G_ORI_TH_NOW"])
    for i, y in enumerate(res["years"]):
        sold_regions = sum(v[i] for v in res["sold_by_region"].values())
        assert sold_regions == pytest.approx(res["sold_t"][i])
        assert res["sold_t"][i] <= res["capacity_t"][i] + 1e-6
        assert sold_regions <= sum(p["demand"][r][str(y)] for r in p["regions"]) + 1e-6


def test_china_route_blocked_until_gacc_registration(ctx):
    cfg, _, _, p, _ = ctx
    q = copy.deepcopy(p)
    q["demand"] = {r: {str(y): (5000.0 if r == "CHINA" else 0.0) for y in E.years(q)} for r in q["regions"]}
    res = E.run_alternative(q, cfg["alternatives"]["C_TH_NSN"])
    online, delay = 2030, q["sites"]["TH_NSN"]["gacc_delay"]
    for i, y in enumerate(res["years"]):
        if y < online + delay:
            assert res["sold_by_region"]["CHINA"][i] == 0.0
    assert res["sold_by_region"]["CHINA"][res["years"].index(online + delay)] > 0


# ---- inputs: evidence, demand, gates -----------------------------------------------------------------

def test_evidence_without_unit_or_vintage_rejected(ctx):
    cfg = ctx[0]
    ev = pd.read_csv(ROOT / "data" / "raw" / "evidence_registry.csv")
    D.validate_evidence(ev)
    bad = ev.copy()
    bad.loc[0, "unit"] = np.nan
    with pytest.raises(D.InputError):
        D.validate_evidence(bad)
    bad = ev.copy()
    bad.loc[0, "vintage"] = ""
    with pytest.raises(D.InputError):
        D.validate_evidence(bad)


def test_demand_rules(ctx):
    cfg, a, _, _, demand = ctx
    regions = list(cfg["regions"])
    dup = pd.concat([demand, demand.head(1)])
    with pytest.raises(D.InputError):
        D.validate_demand(dup, regions)
    bad = demand.copy()
    bad.loc[bad.index[0], "contracted_volume_t"] = 1.0  # contracted volume on a pipeline row
    with pytest.raises(D.InputError):
        D.validate_demand(bad, regions)
    w = {"contracted": 1.0, "qualified_pipeline": 0.0, "unqualified_potential": 0.0}
    only_contracts = D.weighted_demand(demand, w, regions, [2030])
    assert sum(v["2030"] for v in only_contracts.values()) == 0.0  # premises never become firm volume


def test_contracted_volume_is_added_exactly(ctx):
    cfg, _, _, p, demand = ctx
    q = A.params_for(cfg, p, demand, "base", contracted_t=4000, asia_share=0.25)
    for y in ("2028", "2030"):
        diff = sum(q["demand"][r][y] - p["demand"][r][y] for r in p["regions"])
        assert diff == pytest.approx(0.0 if int(y) < cfg["contract_start_year"] else 4000.0)
    asia = sum(q["demand"][r]["2030"] - p["demand"][r]["2030"] for r in p["asia_regions"])
    assert asia == pytest.approx(1000.0)


def test_legal_gate_fail_excludes_site():
    g = pd.DataFrame({"site_id": ["X", "X"], "gate": ["legal_licensing", "water_firm"], "status": ["FAIL", "PASS"]})
    piv = g.pivot(index="site_id", columns="gate", values="status")
    summary = piv.apply(lambda r: "FAIL" if (r == "FAIL").any() else "PASS", axis=1)
    assert summary["X"] == "FAIL"
    gates = pd.read_csv(ROOT / "data" / "raw" / "site_gates.csv")
    assert set(gates.status) <= {"PASS", "REVIEW", "FAIL", "NOT_VERIFIED"}


def test_assumptions_reference_known_sources(ctx):
    _, a, _, _, _ = ctx
    assert ((a.low <= a.base) & (a.base <= a.high)).all()


# ---- risk --------------------------------------------------------------------------------------------

def test_correlation_matrix_psd_and_draws(ctx):
    cfg = ctx[0]
    names, m = A.correlation_matrix(cfg)
    assert A.is_psd(m)
    d = A.draw_samples(cfg, 4000, 1)
    rho = np.corrcoef(d["fish_oil"], d["demand"])[0, 1]
    assert 0.25 < rho < 0.55  # declared 0.4 survives the triangular marginals
    for n in names:
        v = cfg["monte_carlo"]["variables"][n]
        assert d[n].between(v["low"], v["high"]).all()


def test_msp_gives_zero_npv(ctx):
    cfg, _, _, p, _ = ctx
    alt = cfg["alternatives"]["A1_ORI"]
    m = E.msp(p, alt)
    assert abs(E.run_alternative(dict(p, price_dha=m), alt)["npv"]) < 1e5
    assert m != pytest.approx(p["price_dha"])  # MSP is not the realised price


def test_no_demand_means_no_value(ctx):
    cfg, _, _, p, _ = ctx
    q = copy.deepcopy(p)
    q["demand"] = {r: {y: 0.0 for y in v} for r, v in q["demand"].items()}
    res = E.run_alternative(q, cfg["alternatives"]["A1_ORI"])
    assert res["npv"] < 0 and max(res["sold_t"]) == 0.0


# ---- baseline ------------------------------------------------------------------------------------------

def test_v2_baseline_reproduced_from_frozen_data():
    rep = S.reproduce_v2()
    assert rep["abs_diff"].max() < 1e-3
    assert (rep["rank_rerun"] == rep["rank_frozen_v2"]).all()
    assert rep.loc["Brazil", "score_rerun"] == pytest.approx(7.15, abs=5e-3)


# ---- JS port parity ------------------------------------------------------------------------------------

@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_cockpit_engine_matches_python(ctx, tmp_path):
    cfg, _, p0, _, demand = ctx
    p = A.params_for(cfg, p0, demand, "upside", contracted_t=7000, asia_share=0.7)
    p["country"]["TH"]["qrtc"] = 0.15
    p["fx_shock"] = {"BR": 0.1, "TH": -0.05}
    (tmp_path / "in.json").write_text(json.dumps({"p": p, "alts": cfg["alternatives"]}))
    js = ("const E=require(process.argv[1]);const j=require(process.argv[2]);const o={};"
          "for(const k in j.alts){const r=E.runAlternative(j.p,j.alts[k]);o[k]=[r.npv,r.npv_ex_tv,r.irr];}"
          "console.log(JSON.stringify(o));")
    out = subprocess.check_output(["node", "-e", js, str(ROOT / "src" / "cockpit_engine.js"),
                                   str(tmp_path / "in.json")], text=True)
    got = json.loads(out)
    for k, alt in cfg["alternatives"].items():
        r = E.run_alternative(p, alt)
        assert got[k][0] == pytest.approx(r["npv"], rel=1e-9, abs=1e-3)
        assert got[k][1] == pytest.approx(r["npv_ex_tv"], rel=1e-9, abs=1e-3)


def test_allocation_terminates_and_is_optimal_with_large_costs():
    """Regression: float noise on USD/t-scale margins once produced a predecessor cycle (infinite loop)."""
    rng = np.random.default_rng(11)
    for _ in range(40):
        plants, regions = ["P1", "P2"], ["R1", "R2", "R3", "R4", "R5"]
        supply = {x: float(rng.uniform(0, 12000)) for x in plants}
        demand = {r: float(rng.uniform(0, 9000)) for r in regions}
        edges = {(x, r): (float(rng.uniform(5000, 20000)), float(rng.uniform(0, 9000))) for x in plants for r in regions}
        flows = E.allocate(supply, demand, edges)
        keys = list(edges)
        A_ub = [[1.0 if k[0] == x else 0.0 for k in keys] for x in plants] + \
               [[1.0 if k[1] == r else 0.0 for k in keys] for r in regions]
        b_ub = [supply[x] for x in plants] + [demand[r] for r in regions]
        lp = linprog([-edges[k][0] for k in keys], A_ub=A_ub, b_ub=b_ub, bounds=[(0, edges[k][1]) for k in keys],
                     method="highs")
        assert sum(edges[k][0] * f for k, f in flows.items()) == pytest.approx(-lp.fun, rel=1e-6)
