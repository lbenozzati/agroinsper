"""Triage score, consolidation/expansion rankings, accounts, portfolio MILP, breakeven frontier, value of information."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

from . import model as M

DIMS = ["incremental_contribution", "probability_of_qualification", "competitive_intensity", "regulatory_readiness",
        "channel_access", "time_to_revenue", "price_resilience", "strategic_fit"]


def _minmax(s: pd.Series, invert: bool = False) -> pd.Series:
    lo, hi = s.min(), s.max()
    v = (s - lo) / (hi - lo) * 10 if hi > lo else s * 0 + 5
    return 10 - v if invert else v


def triage(cfg: dict, mkt: pd.DataFrame, n_draws: int = 2000, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    t = mkt.copy()
    t["incremental_contribution"] = _minmax(t["commercial_npv_musd"])
    t["probability_of_qualification"] = t["p_qualification"] * 10
    t["competitive_intensity"] = 10 - t["competitive_intensity"]
    t["regulatory_readiness"] = t["regulatory_readiness"] * 10
    t["channel_access"] = t["channel_access"] * 10
    t["time_to_revenue"] = _minmax(t["time_to_revenue"], invert=True)
    t["price_resilience"] = _minmax(t["price_mult"])
    t["strategic_fit"] = t["strategic_fit"].astype(float)
    w = np.array([cfg["triage_dimensions"][k] for k in DIMS])
    X = t[DIMS].to_numpy(float)
    t["triage_score"] = X @ w
    rng = np.random.default_rng(seed)
    W = rng.dirichlet(w * 40, size=n_draws)
    S = X @ W.T
    ranks = (-S).argsort(axis=0).argsort(axis=0) + 1
    t["p_top3_triage_weights"] = (ranks <= 3).mean(axis=1)
    t["median_rank_triage"] = np.median(ranks, axis=1)
    corr = t[DIMS].corr().round(2)
    return t, corr


def rankings(t: pd.DataFrame) -> pd.DataFrame:
    out = []
    for grp in ("consolidation", "expansion"):
        g = t[t.group == grp].sort_values("commercial_npv_musd", ascending=False).copy()
        g["rank_by_npv"] = range(1, len(g) + 1)
        g["rank_by_triage"] = g["triage_score"].rank(ascending=False, method="min").astype(int)
        out.append(g)
    cols = ["group", "rank_by_npv", "rank_by_triage", "country", "application", "relationship_status",
            "commercial_npv_musd", "incremental_sku_2030_t", "incremental_sku_2035_t", "revenue_2030_musd",
            "p_qualification", "triage_score", "p_top3_triage_weights", "data_confidence"] + DIMS
    return pd.concat(out)[cols]


EVIDENCE_WEIGHT = {"documented_current": 1.0, "documented_historical": 0.7, "trial": 0.5, "channel_only": 0.5,
                   "potential": 0.2, "unknown": 0.1}


def account_ranking(customers: pd.DataFrame, mkt: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, c in customers.iterrows():
        countries = [x.strip() for x in str(c["country"]).split(";")]
        seg = mkt[(mkt.country.isin(countries)) & (mkt.application == c["application"])]
        if c["region"] == "ALL" or seg.empty:
            npv = np.nan
            vol = np.nan
        else:
            npv = seg.commercial_npv_musd.sum()
            vol = seg.incremental_sku_2030_t.sum()
        rows.append({"entity": c["entity"], "countries": c["country"], "application": c["application"],
                     "role": c["role"], "relationship_status": c["relationship_status"],
                     "evidence": c["evidence"], "evidence_date": c["evidence_date"],
                     "segment_npv_musd": npv, "segment_incremental_sku_2030_t": vol,
                     "account_share_of_segment": "unknown (not public)",
                     "account_priority_index": (EVIDENCE_WEIGHT[c["relationship_status"]] * max(npv, 0)
                                                if pd.notna(npv) else np.nan),
                     "next_proof_needed": c["next_proof_needed"], "source_id": c["source_id"]})
    a = pd.DataFrame(rows)
    a["type"] = np.where(a.relationship_status.isin(["documented_current", "documented_historical", "trial", "channel_only"]),
                         "consolidation", "expansion")
    return a.sort_values(["type", "account_priority_index"], ascending=[True, False])


def optimise_portfolio(cfg: dict, d: dict, mkt: pd.DataFrame, A_over: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """Binary market-entry MILP: max sum NPV s.t. FTE, registrations, incremental capacity and country concentration."""
    A = {k: v["base"] for k, v in d["A"].items()}
    A.update(A_over or {})
    m = mkt.reset_index(drop=True)
    n = len(m)
    c = -m["commercial_npv_musd"].to_numpy()
    vol = m["incremental_sku_2030_t"].to_numpy()
    rows, lb, ub = [], [], []
    rows.append(m["fte"].to_numpy()); lb.append(-np.inf); ub.append(A["fte_budget"])
    rows.append(m["registrations"].to_numpy()); lb.append(-np.inf); ub.append(A["registration_budget"])
    rows.append(vol); lb.append(-np.inf); ub.append(A["capacity_increment_2030_t"])
    for country in m.country.unique():
        rows.append(np.where(m.country == country, vol, 0.0) - A["max_country_share"] * vol)
        lb.append(-np.inf); ub.append(0.0)
    res = milp(c, constraints=LinearConstraint(np.array(rows), lb, ub), integrality=np.ones(n), bounds=Bounds(0, 1))
    x = np.round(res.x).astype(int) if res.success else np.zeros(n, int)
    m["selected"] = x
    info = {"status": res.message, "success": bool(res.success), "objective_npv_musd": float(-res.fun) if res.success else 0.0,
            "fte_used": float(m.fte @ x), "registrations_used": float(m.registrations @ x),
            "incremental_sku_2030_t": float(vol @ x), "capacity_limit_t": A["capacity_increment_2030_t"],
            "mip_gap": getattr(res, "mip_gap", None)}
    return m, info


def brute_force(m: pd.DataFrame, A: dict) -> float:
    """Exhaustive check of the MILP for small instances (used in tests)."""
    best = 0.0
    vol = m["incremental_sku_2030_t"].to_numpy()
    for combo in itertools.product([0, 1], repeat=len(m)):
        x = np.array(combo)
        if m.fte.to_numpy() @ x > A["fte_budget"] or m.registrations.to_numpy() @ x > A["registration_budget"]:
            continue
        tot = vol @ x
        if tot > A["capacity_increment_2030_t"]:
            continue
        if any((np.where(m.country == c, vol, 0) @ x) > A["max_country_share"] * tot + 1e-9 for c in m.country.unique()):
            continue
        best = max(best, float(m.commercial_npv_musd.to_numpy() @ x))
    return best


def breakeven_prices(cfg: dict, d: dict) -> pd.DataFrame:
    """Net price (USD/kg DHA) at which each market's commercial NPV = 0, with its incremental volume."""
    base = M.market_table(cfg, d, M.segments_df(cfg, d)).set_index(["country", "application"])
    rows = []
    for key in base.index:
        def f(price):
            seg = M.segments_df(cfg, d, "base", {"price": price})
            mt = M.market_table(cfg, d, seg).set_index(["country", "application"])
            return mt.loc[key, "commercial_npv_musd"]
        lo, hi = 5.0, 200.0
        flo, fhi = f(lo), f(hi)
        be = None
        if flo < 0 < fhi:
            for _ in range(30):
                mid = (lo + hi) / 2
                if f(mid) < 0:
                    lo = mid
                else:
                    hi = mid
            be = (lo + hi) / 2
        elif flo >= 0:
            be = lo
        rows.append({"country": key[0], "application": key[1], "breakeven_price_usd_kg_dha": be,
                     "incremental_sku_2030_t": base.loc[key, "incremental_sku_2030_t"]})
    out = pd.DataFrame(rows).sort_values("breakeven_price_usd_kg_dha", na_position="last")
    out["cumulative_sku_2030_t"] = out["incremental_sku_2030_t"].where(out.breakeven_price_usd_kg_dha.notna(), 0).cumsum()
    return out


VOI_PARAMS = [
    ("price", "Preço líquido por kg DHA", {"price": 15.0}, {"price": 40.0}, "contrato/cotação com clientes"),
    ("econ_mult", "Parcela da ração que paga por DHA", {"econ_mult": 0.6}, {"econ_mult": 1.4}, "entrevistas com fabricantes de ração"),
    ("marine_mult", "DHA já suprido por ingredientes marinhos", {"marine_mult": 1.2}, {"marine_mult": 0.8}, "matriz de formulação / dados de compra"),
    ("target_mult", "Alvo de EPA+DHA na dieta", {"target_mult": 0.6}, {"target_mult": 1.4}, "ensaios / especificações dos clientes"),
    ("adoption_mult", "Saturação da adoção de algas", {"adoption_mult": 0.7}, {"adoption_mult": 1.2}, "pipeline qualificado / ensaios"),
    ("share_mult", "Participação da Corbion no DHA de algas", {"share_mult": 0.6}, {"share_mult": 1.4}, "inteligência competitiva (Veramaris, chineses)"),
    ("fish_oil", "Preço do óleo de peixe", {"fish_oil": 2500.0}, {"fish_oil": 6800.0}, "série IFFO / contratos"),
    ("growth_add", "Crescimento da produção animal", {"growth_add": -0.02}, {"growth_add": 0.02}, "FAO / associações"),
    ("var_cost", "Custo variável (US$/kg DHA)", {"var_cost": 10.0}, {"var_cost": 6.0}, "dados de operação Orindiúva"),
    ("pq_mult", "Probabilidade de qualificação", {"pq_mult": 0.7}, {"pq_mult": 1.3}, "histórico de ensaios / CRM"),
]


def value_of_information(cfg: dict, d: dict) -> pd.DataFrame:
    base_seg = M.segments_df(cfg, d)
    base_mkt = M.market_table(cfg, d, base_seg)
    _, base_info = optimise_portfolio(cfg, d, base_mkt)
    base_top = list(base_mkt[base_mkt.group == "expansion"].sort_values("commercial_npv_musd", ascending=False).head(3).country)
    rows = []
    for key, label, lo, hi, how in VOI_PARAMS:
        res = {}
        for side, ov in (("low", lo), ("high", hi)):
            mkt_ov = {k: v for k, v in ov.items() if k == "pq_mult"}
            seg_ov = {k: v for k, v in ov.items() if k != "pq_mult"}
            seg = M.segments_df(cfg, d, "base", seg_ov)
            mkt = M.market_table(cfg, d, seg, mkt_ov)
            sel, info = optimise_portfolio(cfg, d, mkt)
            top = list(mkt[mkt.group == "expansion"].sort_values("commercial_npv_musd", ascending=False).head(3).country)
            res[side] = (info["objective_npv_musd"], mkt.incremental_sku_2030_t.sum(), top,
                         set(sel[sel.selected == 1].country + "/" + sel[sel.selected == 1].application))
        rows.append({"parameter": key, "label": label, "how_to_close_gap": how,
                     "portfolio_npv_low_musd": res["low"][0], "portfolio_npv_high_musd": res["high"][0],
                     "npv_swing_musd": abs(res["high"][0] - res["low"][0]),
                     "incremental_2030_low_t": res["low"][1], "incremental_2030_high_t": res["high"][1],
                     "expansion_top3_changes": (res["low"][2] != base_top) or (res["high"][2] != base_top),
                     "portfolio_changes": res["low"][3] != res["high"][3],
                     "base_portfolio_npv_musd": base_info["objective_npv_musd"]})
    return pd.DataFrame(rows).sort_values("npv_swing_musd", ascending=False)
