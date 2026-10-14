"""Bottom-up TAM -> SAM -> SOM with visible denominators, forecast by drivers, and market economics.

All quantities are per (country, application, stage, year). Pure-Python loops so the same function serves
the deterministic run, sensitivities and the Monte Carlo.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

LEVELS = ("low", "base", "high")


def _pick(row, col, level):
    """Choose the low/base/high column of a table row (e.g. growth_low, growth_base, growth_high)."""
    if level == "base":
        return float(row[f"{col}_base"] if f"{col}_base" in row else row[col])
    return float(row[f"{col}_{level}"])


def logistic_share(y: int, start: float, sat: float, mid: float, k: float, base_year: int) -> float:
    l0 = 1 / (1 + math.exp(-k * (base_year - mid)))
    ly = 1 / (1 + math.exp(-k * (y - mid)))
    return start + (sat - start) * max(0.0, (ly - l0) / (1 - l0))


def scenario_settings(cfg: dict, scenario: str) -> dict:
    return dict(cfg["scenarios"][scenario])


def run_segments(cfg: dict, d: dict, scenario: str = "base", ov: dict | None = None) -> list[dict]:
    """One record per country x application x stage x year with every denominator of the bridge."""
    ov = ov or {}
    s = scenario_settings(cfg, scenario)
    A = d["A"]
    g = lambda k, lvl="base": A[k][lvl]  # noqa: E731
    fo = ov.get("fish_oil", g("fish_oil_base_usd_t", s["fish_oil"]))
    fo_base = g("fish_oil_base_usd_t")
    price_dha = ov.get("price", g("net_price_usd_per_kg_dha", s["price"])) * (fo / fo_base) ** g("fish_oil_price_passthrough")
    gap_adj = (fo_base / fo) ** g("fish_oil_gap_elasticity")
    dha_frac, eff = g("dha_fraction_sku"), g("formulation_efficiency")
    var_cost = ov.get("var_cost", g("variable_cost_usd_per_kg_dha"))
    deduct = g("commercial_cost_pct") + g("rebate_pct") + g("wc_carry_pct")
    params = d["params"].set_index(["country", "application"])
    nut = d["nutrition"]
    out = []
    years = range(cfg["base_year"], cfg["end_year"] + 1)
    for _, f in d["feed"].iterrows():
        key = (f["country"], f["application"])
        mp = params.loc[key]
        if pd.notna(f["observed_feed_t"]):
            feed0 = float(f["observed_feed_t"])
        else:
            feed0 = float(f["production_t"]) * float(f["fcr"]) * float(f["commercial_feed_share"])
        growth = _pick(f, "growth", s["growth"]) + ov.get("growth_add", 0.0)
        share = {"low": mp["share_low"], "base": mp["corbion_share"], "high": mp["share_high"]}[s["share"]]
        share = min(1.0, share * ov.get("share_mult", 1.0))
        sat = min(1.0, mp["adoption_sat"] * s["adoption_mult"] * ov.get("adoption_mult", 1.0))
        freight_kg = d["freight_br"].get(f["region"], 120.0) / (dha_frac * 1000)
        p_kg = price_dha * mp["price_mult"]
        unit_contrib = p_kg * (1 - deduct) - var_cost - freight_kg
        for _, st in nut[nut.application == f["application"]].iterrows():
            target = (st["epa_dha_g_per_kg"] if s["target"] == "base" else st[f"epa_dha_{s['target']}"]) * ov.get("target_mult", 1.0)
            marine = (st["marine_supplied_share"] if s["marine"] == "base" else st[f"marine_{s['marine']}"])
            marine = min(1.0, marine * ov.get("marine_mult", 1.0) * gap_adj)
            econ = (st["econ_capable_share"] if s["econ"] == "base" else st[f"econ_{s['econ']}"])
            econ = min(1.0, econ * ov.get("econ_mult", 1.0))
            for y in years:
                feed = feed0 * (1 + growth) ** (y - cfg["base_year"])
                stage_feed = feed * st["feed_share"]
                tam = stage_feed * target / 1000 * st["dha_share_of_target"]  # t DHA (g/kg x t / 1000)
                sam = tam * econ * st["tech_qualified_share"] * mp["regulatory_readiness"] * (1 - marine)
                adopt = logistic_share(y, mp["adoption_start"], max(sat, mp["adoption_start"]), mp["adoption_mid"],
                                       mp["adoption_k"], cfg["base_year"])
                algal = sam * adopt
                som_dha = algal * share
                sku = som_dha / (dha_frac * eff)
                cap = stage_feed * st["max_inclusion_sku"]
                sku = min(sku, cap)
                som_dha = sku * dha_frac * eff
                out.append({
                    "country": f["country"], "application": f["application"], "region": f["region"],
                    "stage": st["stage"], "year": y, "feed_t": feed, "stage_feed_t": stage_feed,
                    "eligible_feed_t": stage_feed * econ * st["tech_qualified_share"] * mp["regulatory_readiness"],
                    "epa_dha_g_per_kg": target, "tam_dha_t": tam, "sam_dha_t": sam, "adoption": adopt,
                    "algal_dha_t": algal, "corbion_share": share, "som_dha_t": som_dha, "som_sku_t": sku,
                    "inclusion_cap_sku_t": cap, "price_usd_kg_dha": p_kg, "revenue_usd": som_dha * 1000 * p_kg,
                    "unit_contribution_usd_kg_dha": unit_contrib, "contribution_usd": som_dha * 1000 * unit_contrib,
                    "relationship_status": mp["relationship_status"], "confidence": f["confidence"],
                })
    return out


def segments_df(cfg, d, scenario="base", ov=None) -> pd.DataFrame:
    return pd.DataFrame(run_segments(cfg, d, scenario, ov))


def status_probability(d: dict, status: str) -> float:
    return d["A"][f"status_prob_{status}"]["base"]


def market_table(cfg: dict, d: dict, seg: pd.DataFrame, ov: dict | None = None) -> pd.DataFrame:
    """Country x application economics: incremental SOM, probability-weighted NPV of the commercial effort."""
    ov = ov or {}
    A = d["A"]
    r = A["discount_rate"]["base"]
    fte_cost = A["fte_cost_musd"]["base"] * 1e6
    base_y, first = cfg["base_year"], cfg["first_decision_year"]
    agg = seg.groupby(["country", "application", "region", "year"], as_index=False).agg(
        som_sku_t=("som_sku_t", "sum"), som_dha_t=("som_dha_t", "sum"), tam_dha_t=("tam_dha_t", "sum"),
        sam_dha_t=("sam_dha_t", "sum"), revenue_usd=("revenue_usd", "sum"), contribution_usd=("contribution_usd", "sum"),
        unit_contribution=("unit_contribution_usd_kg_dha", "first"), price=("price_usd_kg_dha", "first"))
    params = d["params"].set_index(["country", "application"])
    feedconf = d["feed"].set_index(["country", "application"])["confidence"]
    rows = []
    for (c, a, reg), g in agg.groupby(["country", "application", "region"]):
        mp = params.loc[(c, a)]
        g = g.set_index("year")
        documented = mp["relationship_status"] in cfg["status_groups"]["consolidation"]
        baseline_sku = g.loc[base_y, "som_sku_t"] if documented else 0.0
        baseline_dha = g.loc[base_y, "som_dha_t"] if documented else 0.0
        status = mp["relationship_status"]
        p_q = min(1.0, status_probability(d, status) * mp["regulatory_readiness"] * ov.get("pq_mult", 1.0))
        npv = 0.0
        inc = {}
        for y in range(first, cfg["end_year"] + 1):
            active = y >= first + int(mp["time_to_revenue"])
            inc_dha = max(0.0, g.loc[y, "som_dha_t"] - baseline_dha) if active else 0.0
            inc[y] = max(0.0, g.loc[y, "som_sku_t"] - baseline_sku) if active else 0.0
            contrib = inc_dha * 1000 * g.loc[y, "unit_contribution"] * p_q
            cost = mp["fte"] * fte_cost + (mp["entry_cost_musd"] * 1e6 + mp["registrations"] * 0.3e6 if y == first else 0.0)
            npv += (contrib - cost) / (1 + r) ** (y - base_y)
        rows.append({
            "country": c, "application": a, "region": reg, "relationship_status": status,
            "group": "consolidation" if documented else "expansion",
            "tam_dha_2030_t": g.loc[2030, "tam_dha_t"], "sam_dha_2030_t": g.loc[2030, "sam_dha_t"],
            "som_sku_2025_t": g.loc[base_y, "som_sku_t"], "som_sku_2030_t": g.loc[2030, "som_sku_t"],
            "som_sku_2035_t": g.loc[2035, "som_sku_t"],
            "incremental_sku_2028_t": inc[2028], "incremental_sku_2030_t": inc[2030], "incremental_sku_2035_t": inc[2035],
            "revenue_2030_musd": g.loc[2030, "revenue_usd"] / 1e6, "price_usd_kg_dha": g.loc[2030, "price"],
            "unit_contribution_usd_kg_dha": g.loc[2030, "unit_contribution"], "p_qualification": p_q,
            "commercial_npv_musd": npv / 1e6, "competitive_intensity": mp["competitive_intensity"],
            "regulatory_readiness": mp["regulatory_readiness"], "channel_access": mp["channel_access"],
            "time_to_revenue": mp["time_to_revenue"], "price_mult": mp["price_mult"], "strategic_fit": mp["strategic_fit"],
            "fte": mp["fte"], "registrations": mp["registrations"], "data_confidence": feedconf.loc[(c, a)],
        })
    return pd.DataFrame(rows)


def portfolio_totals(seg: pd.DataFrame, mkt: pd.DataFrame, cfg: dict) -> dict:
    out = {}
    for y in cfg["milestones"]:
        s = seg[seg.year == y]
        out[y] = {"tam_dha_t": s.tam_dha_t.sum(), "sam_dha_t": s.sam_dha_t.sum(), "algal_dha_t": s.algal_dha_t.sum(),
                  "som_dha_t": s.som_dha_t.sum(), "som_sku_t": s.som_sku_t.sum(),
                  "revenue_musd": s.revenue_usd.sum() / 1e6, "contribution_musd": s.contribution_usd.sum() / 1e6,
                  "incremental_sku_t": mkt[f"incremental_sku_{y}_t"].sum()}
    return out


def diet_cost_comparison(d: dict) -> pd.DataFrame:
    """Cost of delivering 1 kg of DHA (and of EPA+DHA) from fish oil vs AlgaPrime at three fish-oil prices."""
    A = d["A"]
    rows = []
    for fo in (2500, 4500, 6800):
        price = A["net_price_usd_per_kg_dha"]["base"] * (fo / A["fish_oil_base_usd_t"]["base"]) ** A["fish_oil_price_passthrough"]["base"]
        rows.append({
            "fish_oil_usd_t": fo,
            "fish_oil_usd_per_kg_epa_dha": fo / 1000 / 0.30,
            "fish_oil_usd_per_kg_dha_if_only_dha_valued": fo / 1000 / 0.12,
            "algaprime_usd_per_kg_dha_net": price,
            "algaprime_vs_fishoil_dha_only": price / (fo / 1000 / 0.12),
            "note": "Fish oil 18:12 supplies EPA too; AlgaPrime supplies DHA only, so EPA must be sourced separately. "
                    "No ingredient matrix -> no LP reformulation.",
        })
    return pd.DataFrame(rows)


def monte_carlo(cfg: dict, d: dict, n: int, seed: int) -> pd.DataFrame:
    """Global multipliers drawn from triangular(low, base, high); fish oil correlated with adoption."""
    rng = np.random.default_rng(seed)
    A = d["A"]
    rho = cfg["monte_carlo"]["fish_oil_adoption_corr"]
    z = rng.multivariate_normal([0, 0], [[1, rho], [rho, 1]], size=n)
    from scipy import stats
    u = stats.norm.cdf(z)

    def tri(uu, lo, mode, hi):
        c = (mode - lo) / (hi - lo)
        return stats.triang.ppf(uu, c, loc=lo, scale=hi - lo)
    fo = tri(u[:, 0], A["fish_oil_base_usd_t"]["low"], A["fish_oil_base_usd_t"]["base"], A["fish_oil_base_usd_t"]["high"])
    adopt = tri(u[:, 1], 0.7, 1.0, 1.2)
    rest = rng.random((n, 6))
    price = tri(rest[:, 0], A["net_price_usd_per_kg_dha"]["low"], A["net_price_usd_per_kg_dha"]["base"], A["net_price_usd_per_kg_dha"]["high"])
    econ = tri(rest[:, 1], 0.6, 1.0, 1.4)
    target = tri(rest[:, 2], 0.6, 1.0, 1.4)
    share = tri(rest[:, 3], 0.6, 1.0, 1.4)
    marine = tri(rest[:, 4], 0.8, 1.0, 1.2)
    growth = tri(rest[:, 5], -0.02, 0.0, 0.02)
    rows = []
    for k in range(n):
        ov = {"fish_oil": fo[k], "adoption_mult": adopt[k], "price": price[k], "econ_mult": econ[k],
              "target_mult": target[k], "share_mult": share[k], "marine_mult": marine[k], "growth_add": growth[k]}
        seg = segments_df(cfg, d, "base", ov)
        mkt = market_table(cfg, d, seg)
        rows.append({**ov, "incremental_sku_2030_t": mkt.incremental_sku_2030_t.sum(),
                     "incremental_sku_2035_t": mkt.incremental_sku_2035_t.sum(),
                     "som_sku_2030_t": seg[seg.year == 2030].som_sku_t.sum(),
                     "commercial_npv_musd": mkt.commercial_npv_musd.sum(),
                     "revenue_2030_musd": seg[seg.year == 2030].revenue_usd.sum() / 1e6})
    return pd.DataFrame(rows)
