"""Scenario runs, unit economics, correlated Monte Carlo, tornado, decision frontier and resilience stress."""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd
from scipy import stats

from . import data as D
from . import engine as E

SITE_LABEL = {"BR_ORI_EXP": "Orindiúva (expansão)", "BR_GF_GO": "Greenfield Brasil (GO)",
              "TH_NSN": "Nakhon Sawan", "TH_RYG": "Rayong"}


def params_for(cfg: dict, base_p: dict, demand_rows: pd.DataFrame, scenario: str = "base",
               contracted_t: float = 0.0, asia_share: float = 0.5, filters: dict | None = None) -> dict:
    p = copy.deepcopy(base_p)
    yrs = [str(y) for y in E.years(p)]
    dem = D.weighted_demand(demand_rows, p["scenario_weights"][scenario], p["regions"], [int(y) for y in yrs],
                            filters)
    if contracted_t:
        dem = D.add_contracted(dem, contracted_t, asia_share, D.region_mix(demand_rows, p["regions"]),
                               p["asia_regions"], cfg["contract_start_year"])
    p["demand"] = dem
    return p


def summarize(res: dict, p: dict) -> dict:
    ys = res["years"]
    i30, i35 = ys.index(2030), ys.index(2035)
    return {
        "npv_musd": res["npv"] / 1e6, "npv_ex_tv_musd": res["npv_ex_tv"] / 1e6, "tv_pv_musd": res["tv_pv"] / 1e6,
        "tv_share_of_npv_value": (res["tv_pv"] / (abs(res["npv_ex_tv"]) + abs(res["tv_pv"]))) if res["tv_pv"] else 0.0,
        "irr": res["irr"], "lcod_usd_per_kg_dha": res["lcod"], "disc_payback_year": res["disc_payback"],
        "peak_funding_musd": res["peak_funding"] / 1e6,
        "capacity_2030_t": res["capacity_t"][i30], "sold_2030_t": res["sold_t"][i30],
        "capacity_2035_t": res["capacity_t"][i35], "sold_2035_t": res["sold_t"][i35],
        "utilisation_2030": res["utilisation"][i30], "utilisation_2035": res["utilisation"][i35],
        "unabsorbed_2035_t": res["capacity_t"][i35] - res["sold_t"][i35],
        "capex_real_musd": sum(res.get("capex_real", {}).values()) / 1e6,
        "units": "; ".join(f"{u['id']}@{u['online']}" for u in res["units"]),
        "dscr": "n/a (corporate funding assumed; no project debt modelled)",
    }


def scenario_table(cfg: dict, base_p: dict, demand_rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, flows = [], []
    for sc in cfg["scenarios"]:
        p = params_for(cfg, base_p, demand_rows, sc)
        for key, alt in cfg["alternatives"].items():
            res = E.run_alternative(p, alt)
            rows.append({"scenario": sc, "alternative": key, "label": alt["label"], **summarize(res, p)})
            for i, y in enumerate(res["years"]):
                rec = {"scenario": sc, "alternative": key, "year": y,
                       "capacity_t": res["capacity_t"][i], "sold_t": res["sold_t"][i],
                       "utilisation": res["utilisation"][i]}
                for k, v in res["lines"].items():
                    rec[f"{k}_usd"] = v[i]
                for r, v in res["sold_by_region"].items():
                    rec[f"sold_{r}_t"] = v[i]
                flows.append(rec)
    return pd.DataFrame(rows), pd.DataFrame(flows)


def unit_economics(cfg: dict, p: dict) -> pd.DataFrame:
    """Steady-state cost per t SKU and per kg DHA at full module utilisation (base-year USD)."""
    rows = []
    for s in p["sites"]:
        c = p["sites"][s]["country"]
        cc = p["country"][c]
        lines = E.variable_cost_lines(p, s)
        cap = E.unit_capex(p, {"site": s})
        out_t = p["module_t"] * p["oee"]
        fixed = (p["sites"][s]["headcount"] * cc["labour"] * E.fxadj(p, c, 1.0)
                 + (p["maint_pct"] + p["ins_pct"]) * cap["total"] + p["sites"][s]["qa"]) / out_t
        w = cc["wacc"]
        crf = w / (1 - (1 + w) ** -p["economic_life"])
        capital = cap["total"] * crf / out_t
        mix = {r: 1 / len(p["regions"]) for r in p["regions"]}
        freight = sum(p["freight"][c][r]["usd"] * mix[r] for r in p["regions"])
        row = {"site_id": s, "site": SITE_LABEL[s], "country": c, "module_t": p["module_t"], "output_t": out_t,
               "sugar_t_per_t_sku": E.sugar_per_t(p),
               **{f"{k}_usd_per_t": v for k, v in lines.items()},
               "fixed_usd_per_t": fixed, "capital_charge_usd_per_t": capital,
               "freight_avg_usd_per_t": freight, "capex_musd": cap["total"] / 1e6,
               "capex_usd_per_t_capacity": cap["total"] / p["module_t"],
               **{f"capex_{m}_musd": cap[m] / 1e6 for m in E.CAPEX_MODULES + ("contingency", "import_duty",
                                                                               "connection", "land")},
               "wacc_nominal_usd": w}
        row["cash_cost_usd_per_t"] = sum(lines.values()) + fixed
        row["full_cost_usd_per_t"] = row["cash_cost_usd_per_t"] + capital + freight
        kg = p["dha_fraction"] * 1000
        for k in ("cash_cost", "full_cost"):
            row[f"{k}_usd_per_kg_dha"] = row[f"{k}_usd_per_t"] / kg
        rows.append(row)
    return pd.DataFrame(rows)


def implied_capacity_of_eur50m(p: dict, eurusd: float) -> pd.DataFrame:
    """What EUR 50m WOULD buy at different brownfield intensities: a sensitivity, not a disclosure."""
    rows = []
    usd = 50e6 * eurusd
    base = E.unit_capex(p, {"site": "BR_ORI_EXP"})["total"] / p["module_t"]
    for factor in (0.6, 0.8, 1.0, 1.2, 1.5):
        rows.append({"brownfield_capex_usd_per_t": base * factor, "eur_50m_in_usd_m": usd / 1e6,
                     "implied_capacity_t_if_all_dha": usd / (base * factor),
                     "status": "sensitivity only; Corbion did not disclose the incremental capacity"})
    return pd.DataFrame(rows)


def _tri_ppf(u, low, mode, high):
    if high == low:
        return np.full_like(u, mode)
    c = (mode - low) / (high - low)
    return stats.triang.ppf(u, c, loc=low, scale=high - low)


def correlation_matrix(cfg: dict) -> tuple[list[str], np.ndarray]:
    names = list(cfg["monte_carlo"]["variables"])
    m = np.eye(len(names))
    for a, b, r in cfg["monte_carlo"]["correlations"]:
        i, j = names.index(a), names.index(b)
        m[i, j] = m[j, i] = r
    return names, m


def is_psd(m: np.ndarray) -> bool:
    return bool(np.all(np.linalg.eigvalsh(m) > -1e-10))


def draw_samples(cfg: dict, n: int, seed: int, correlated: bool = True) -> pd.DataFrame:
    names, corr = correlation_matrix(cfg)
    if not correlated:
        corr = np.eye(len(names))
    if not is_psd(corr):
        raise ValueError("correlation matrix is not positive semi-definite")
    rng = np.random.default_rng(seed)
    z = rng.multivariate_normal(np.zeros(len(names)), corr, size=n)
    u = stats.norm.cdf(z)
    out = {}
    for k, name in enumerate(names):
        v = cfg["monte_carlo"]["variables"][name]
        out[name] = _tri_ppf(u[:, k], v["low"], v["mode"], v["high"])
    df = pd.DataFrame(out)
    df["outage_u"] = list(rng.random((n, 4, 10)))
    return df


def apply_draw(p: dict, draw: pd.Series, cfg: dict, base_sugar: dict) -> dict:
    q = copy.deepcopy(p)
    for s, site in q["sites"].items():
        key = "sugar_BR" if site["country"] == "BR" else "sugar_TH"
        ref = cfg["monte_carlo"]["variables"][key]["mode"]
        site["sugar"] = base_sugar[s] * draw[key] / ref
    q["fx_shock"] = {"BR": float(draw["fx_BR"]), "TH": float(draw["fx_TH"])}
    q["fish_oil"] = float(draw["fish_oil"])
    q["capex_mult"] = {"BR": float(draw["capex_BR"]), "TH": float(draw["capex_TH"])}
    thr = cfg["monte_carlo"]["delay_threshold_capex"]
    q["delay"] = {s: (1 if q["capex_mult"][site["country"]] > thr else 0) for s, site in q["sites"].items()}
    q["dha_yield"] = float(draw["dha_yield"])
    q["oee"] = float(draw["oee"])
    for r in q["regions"]:
        m = float(draw["demand"]) * (float(draw["asia_mix"]) if r in q["asia_regions"] else 1.0)
        q["demand"][r] = {y: v * m for y, v in q["demand"][r].items()}
    pr, dur = q["outage_prob"], q["outage_dur"]
    ys = E.years(q)
    q["outage"] = {}
    for k, s in enumerate(q["sites"]):
        q["outage"][s] = {str(y): (dur if draw["outage_u"][k][i] < pr else 0.0) for i, y in enumerate(ys)}
    return q


def run_monte_carlo(cfg: dict, p: dict, n: int, seed: int, correlated: bool = True) -> pd.DataFrame:
    draws = draw_samples(cfg, n, seed, correlated)
    base_sugar = {s: site["sugar"] for s, site in p["sites"].items()}
    rows = []
    for k in range(n):
        q = apply_draw(p, draws.iloc[k], cfg, base_sugar)
        rec = {"sim": k, **{c: draws.iloc[k][c] for c in draws.columns if c != "outage_u"}}
        for key, alt in cfg["alternatives"].items():
            res = E.run_alternative(q, alt)
            rec[key] = res["npv"] / 1e6
            if key in ("F_ORI_THEN_TH", "A2_ORI_STAGED"):
                rec[f"{key}_triggered"] = len(res["units"]) > 1
        rows.append(rec)
    return pd.DataFrame(rows)


def mc_summary(mc: pd.DataFrame, alts: list[str]) -> pd.DataFrame:
    rows = []
    best = mc[alts].idxmax(axis=1)
    for a in alts:
        v = mc[a].to_numpy()
        q10 = np.quantile(v, 0.10)
        rows.append({"alternative": a, "mean_npv_musd": v.mean(), "p10": q10, "p50": np.quantile(v, 0.5),
                     "p90": np.quantile(v, 0.9), "prob_npv_positive": (v > 0).mean(),
                     "expected_shortfall_10pct": v[v <= q10].mean(),
                     "prob_best_conditional": (best == a).mean(),
                     "prob_beats_A1": (v > mc["A1_ORI"].to_numpy()).mean()})
    return pd.DataFrame(rows)


TORNADO_PARAMS = [
    ("price_dha", "Preço líquido (USD/kg DHA)", None),
    ("sugar_BR", "Açúcar Brasil (USD/t)", None),
    ("sugar_TH", "Açúcar Tailândia (USD/t)", None),
    ("dha_yield", "Rendimento DHA/açúcar", None),
    ("capex_intensity", "Capex greenfield (USD/t·ano)", None),
    ("bf_utilities", "Utilidades compartilhadas (brownfield)", None),
    ("asia_capture_br", "Captura da Ásia a partir do Brasil", None),
    ("oee", "OEE", None),
    ("wacc_BR", "WACC Brasil", None),
    ("globe_TH", "Top-up GloBE na Tailândia (0/1)", None),
    ("fx_BR", "Choque real BRL (+ = depreciação)", None),
    ("demand", "Multiplicador de demanda", None),
]


def _set(p: dict, key: str, value: float) -> dict:
    q = copy.deepcopy(p)
    if key == "sugar_BR":
        for s in q["sites"].values():
            if s["country"] == "BR":
                s["sugar"] = s["sugar"] * value / 370
    elif key == "sugar_TH":
        for s in q["sites"].values():
            if s["country"] == "TH":
                s["sugar"] = s["sugar"] * value / 560
    elif key == "wacc_BR":
        q["country"]["BR"]["wacc"] = value
    elif key == "globe_TH":
        q["country"]["TH"]["globe_applies"] = int(value)
    elif key == "fx_BR":
        q["fx_shock"]["BR"] = value
    elif key == "demand":
        q = E.scaled_demand(q, value)
    else:
        q[key] = value
    return q


def tornado(cfg: dict, p: dict, a: pd.DataFrame, metric) -> pd.DataFrame:
    lo_hi = {
        "price_dha": (D.assumption(a, "net_price_usd_per_kg_dha", which="low"),
                      D.assumption(a, "net_price_usd_per_kg_dha", which="high")),
        "sugar_BR": (300, 520), "sugar_TH": (450, 700),
        "dha_yield": (0.055, 0.10), "capex_intensity": (6000, 14000), "bf_utilities": (0.3, 0.9),
        "asia_capture_br": (0.5, 0.9), "oee": (0.75, 0.92),
        "wacc_BR": (p["country"]["BR"]["wacc"] - 0.015, p["country"]["BR"]["wacc"] + 0.02),
        "globe_TH": (0, 1), "fx_BR": (-0.15, 0.25), "demand": (0.5, 1.4),
    }
    base = metric(p)
    rows = []
    for key, label, _ in TORNADO_PARAMS:
        lo, hi = lo_hi[key]
        v_lo, v_hi = metric(_set(p, key, lo)), metric(_set(p, key, hi))
        rows.append({"parameter": key, "label": label, "low_input": lo, "high_input": hi,
                     "metric_at_low": v_lo, "metric_at_high": v_hi, "base": base,
                     "swing": abs(v_hi - v_lo)})
    return pd.DataFrame(rows).sort_values("swing", ascending=False)


def decision_frontier(cfg: dict, base_p: dict, demand_rows: pd.DataFrame) -> pd.DataFrame:
    fr = cfg["frontier"]
    alts = cfg["alternatives"]
    rows = []
    for capex in fr["capex_ori_musd"]:
        for vol in fr["asia_contract_t"]:
            for price in fr["price_usd_kg_dha"]:
                p = params_for(cfg, base_p, demand_rows, "base", contracted_t=vol, asia_share=1.0)
                p["price_dha"] = price
                p["capex_override"] = {"BR_ORI_EXP": capex * 1e6}
                npv = {k: E.run_alternative(p, alts[k])["npv"] / 1e6 for k in
                       ("A1_ORI", "A2_ORI_STAGED", "E_ORI_HUB", "F_ORI_THEN_TH", "G_ORI_TH_NOW", "C_TH_NSN")}
                best = max(npv, key=npv.get)
                rows.append({"capex_ori_musd": capex, "asia_contracted_t": vol, "price_usd_kg_dha": price,
                             **{f"npv_{k}": v for k, v in npv.items()},
                             "delta_G_vs_A1": npv["G_ORI_TH_NOW"] - npv["A1_ORI"],
                             "delta_F_vs_A1": npv["F_ORI_THEN_TH"] - npv["A1_ORI"],
                             "delta_C_vs_A1": npv["C_TH_NSN"] - npv["A1_ORI"],
                             "best_alternative": best if npv[best] > 0 else "NONE (all NPV <= 0: wait)"})
    return pd.DataFrame(rows)


def resilience_stress(cfg: dict, p0: dict, demand_rows: pd.DataFrame) -> pd.DataFrame:
    """Orindiúva outage (6 months, 2031) under base and upside demand; Thai back-fill shown as an upper bound."""
    rows = []
    for sc in ("base", "upside"):
        p = params_for(cfg, p0, demand_rows, sc)
        for key in ("A1_ORI", "G_ORI_TH_NOW"):
            alt = cfg["alternatives"][key]
            base = E.run_alternative(p, alt)
            q = copy.deepcopy(p)
            q["outage"] = {"BR_ORI_EXP": {"2031": 0.5}}
            hit = E.run_alternative(q, alt)
            i = base["years"].index(2031)
            rows.append({"scenario": sc, "alternative": key,
                         "stress": "Orindiúva incremental module down 6 months in 2031",
                         "sold_2031_base_t": base["sold_t"][i], "sold_2031_stress_t": hit["sold_t"][i],
                         "lost_t": base["sold_t"][i] - hit["sold_t"][i],
                         "npv_change_musd": (hit["npv"] - base["npv"]) / 1e6,
                         "note": "Only the incremental module is modelled; if demand is below capacity the outage "
                                 "is absorbed by spare capacity."})
        th = E.run_alternative(p, cfg["alternatives"]["G_ORI_TH_NOW"])
        i = th["years"].index(2031)
        spare = th["capacity_t"][i] - th["sold_t"][i]
        vc = E.variable_cost(p, "TH_NSN")
        margin = E.price_per_t(p, "SALMON", 2031) - vc * E.infl(p, 2031) - p["freight"]["TH"]["SALMON"]["usd"] * E.infl(p, 2031)
        lost_existing = 0.5 * p["module_t"] * p["oee"]
        backfill = min(spare, lost_existing)
        rows.append({"scenario": sc, "alternative": "G_ORI_TH_NOW",
                     "stress": "Upper bound: Thai spare capacity back-fills existing Orindiúva customers (6-month "
                               "outage of one module-equivalent of existing output, 2031)",
                     "sold_2031_base_t": None, "sold_2031_stress_t": None, "lost_t": lost_existing,
                     "npv_change_musd": backfill * margin / 1e6 * (1 + p["country"]["TH"]["wacc"]) ** -6,
                     "note": f"back-fill {backfill:,.0f} t x margin USD {margin:,.0f}/t; value exists only if the outage "
                             "happens and customers accept Thai-origin product; scenario, not added to NPV."})
    return pd.DataFrame(rows)
