"""Investment policies evaluated with the v3 engine on market-study demand: comparison, allocation, frontiers,
stresses, option value, joint Monte Carlo and value of closing information gaps."""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd
from scipy import stats

from .integration import Upstream, integrated_params


def evaluate(up: Upstream, p: dict, policy: dict) -> dict:
    if not policy["units"]:
        ys = up.v3e.years(p)
        z = [0.0] * len(ys)
        return {"years": ys, "npv": 0.0, "npv_ex_tv": 0.0, "tv_pv": 0.0, "irr": None, "utilisation": z, "capacity_t": z,
                "sold_t": z, "fcf": z, "units": [], "lines": {}, "sold_by_region": {r: z for r in p["regions"]},
                "sold_by_site_region": {}, "disc_payback": None, "peak_funding": 0.0, "lcod": None}
    return up.v3e.run_alternative(p, {"units": policy["units"], "hub": policy.get("hub", False)})


def summary_row(p: dict, res: dict) -> dict:
    ys = res["years"]
    L = res.get("lines") or {}
    sold = sum(res["sold_t"])
    kg = sold * p["dha_fraction"] * 1000
    margin = ((sum(L["revenue"]) - sum(L["var_cost"]) - sum(L["freight"]) - sum(L["transit"])) / kg) if kg > 0 else None
    out = {"npv_musd": res["npv"] / 1e6, "npv_ex_tv_musd": res["npv_ex_tv"] / 1e6, "tv_pv_musd": res["tv_pv"] / 1e6,
           "irr": res["irr"], "peak_funding_musd": res["peak_funding"] / 1e6, "disc_payback_year": res["disc_payback"],
           "weighted_delivered_margin_usd_kg_dha": margin,
           "units": "; ".join(f"{u['id']}@{u['online']}" for u in res["units"]) or "none"}
    for y in (2028, 2030, 2035):
        i = ys.index(y)
        out[f"capacity_{y}_t"] = res["capacity_t"][i]
        out[f"sold_{y}_t"] = res["sold_t"][i]
        out[f"utilisation_{y}"] = res["utilisation"][i]
    return out


def compare(up: Upstream, cfg: dict, segs: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    rows, flows, alloc, store = [], [], [], {}
    for sc in cfg["market_scenarios"]:
        p, dem, _ = integrated_params(up, cfg, sc, segs[sc])
        for key, pol in cfg["policies"].items():
            res = evaluate(up, p, pol)
            store[(sc, key)] = (p, res, dem)
            rows.append({"market_scenario": sc, "policy": key, "label": pol["label"], **summary_row(p, res)})
            for i, y in enumerate(res["years"]):
                rec = {"market_scenario": sc, "policy": key, "year": y, "capacity_t": res["capacity_t"][i],
                       "sold_t": res["sold_t"][i]}
                for k, v in (res.get("lines") or {}).items():
                    rec[f"{k}_usd"] = v[i]
                flows.append(rec)
            alloc += allocation_rows(sc, key, res, dem, p)
    comp = pd.DataFrame(rows)
    comp["rank_in_scenario"] = comp.groupby("market_scenario")["npv_musd"].rank(ascending=False, method="min").astype(int)
    return comp, pd.DataFrame(flows), pd.DataFrame(alloc), store


def allocation_rows(sc, key, res, dem, p) -> list[dict]:
    """Split each site->region flow to countries/niches pro-rata to that region's demand (engine works by region)."""
    vol = dem.eligible_final_product_t * dem.inclusion_rate * dem.expected_supplier_share
    d = dem.assign(vol=vol)
    rows = []
    for sr, series in res.get("sold_by_site_region", {}).items():
        site, region = sr.split("|")
        for i, y in enumerate(res["years"]):
            t = series[i]
            if t <= 0:
                continue
            g = d[(d.market == region) & (d.year == y)]
            tot = g.vol.sum()
            if tot <= 0:
                rows.append({"market_scenario": sc, "policy": key, "year": y, "site": site, "region": region,
                             "country": "contracted (no study row)", "application": "n/a", "status": "contracted",
                             "allocated_t": t})
                continue
            for (c, a, st), v in g.groupby(["country", "application", "opportunity_status"]).vol.sum().items():
                rows.append({"market_scenario": sc, "policy": key, "year": y, "site": site, "region": region,
                             "country": c, "application": a, "status": st, "allocated_t": t * v / tot})
    return rows


def composition(alloc: pd.DataFrame, comp: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    rows = []
    for (sc, pol), g in alloc.groupby(["market_scenario", "policy"]):
        c = comp[(comp.market_scenario == sc) & (comp.policy == pol)].iloc[0]
        for y in cfg["milestones"]:
            gy = g[g.year == y]
            tot = gy.allocated_t.sum()
            by_c = gy.groupby("country").allocated_t.sum().sort_values(ascending=False)
            rows.append({"market_scenario": sc, "policy": pol, "year": y,
                         "firm_contracted_t": gy[gy.status == "contracted"].allocated_t.sum(),
                         "qualified_pipeline_t": gy[gy.status == "qualified_pipeline"].allocated_t.sum(),
                         "unqualified_potential_t": gy[gy.status == "unqualified_potential"].allocated_t.sum(),
                         "capacity_t": c[f"capacity_{y}_t"], "capacity_gap_t": c[f"capacity_{y}_t"] - tot,
                         "top3_country_share": by_c.head(3).sum() / tot if tot > 0 else None,
                         "top3_countries": ", ".join(by_c.head(3).index),
                         "weighted_margin_usd_kg_dha": c["weighted_delivered_margin_usd_kg_dha"],
                         "disc_payback_year": c["disc_payback_year"],
                         "note": "Account shares unknown: concentration shown by country (formulation geography)."})
    return pd.DataFrame(rows)


def contracted_needed(up: Upstream, cfg: dict, seg: pd.DataFrame, policy_key: str, vs_key: str | None,
                      asia_share: float, price_mult: float = 1.0, capex_ori: float | None = None,
                      firm_only: bool = True) -> float | None:
    """Smallest firm contracted volume (t/yr from contract_start_year) with NPV(policy) - NPV(vs) >= 0."""
    zero = {"contracted": 1.0, "qualified_pipeline": 0.0, "unqualified_potential": 0.0}

    def delta(v):
        p, _, _ = integrated_params(up, cfg, "base", seg, contracted_t=v, asia_share=asia_share,
                                    weights=zero if firm_only else None, price_mult=price_mult)
        if capex_ori:
            p["capex_override"] = {"BR_ORI_EXP": capex_ori * 1e6}
        a = evaluate(up, p, cfg["policies"][policy_key])["npv"]
        b = evaluate(up, p, cfg["policies"][vs_key])["npv"] if vs_key else 0.0
        return a - b
    lo, hi = 0.0, 40000.0
    if delta(lo) >= 0:
        return 0.0
    if delta(hi) < 0:
        return None
    for _ in range(30):
        mid = (lo + hi) / 2
        if delta(mid) >= 0:
            hi = mid
        else:
            lo = mid
    return hi


def frontiers(up: Upstream, cfg: dict, seg: pd.DataFrame) -> pd.DataFrame:
    fr = cfg["frontier"]
    rows = []
    for capex in fr["capex_ori_musd"]:
        for vol in fr["asia_contract_t"]:
            for pm in fr["price_mult"]:
                p, _, _ = integrated_params(up, cfg, "base", seg, contracted_t=vol, asia_share=1.0, price_mult=pm)
                p["capex_override"] = {"BR_ORI_EXP": capex * 1e6}
                npv = {k: evaluate(up, p, cfg["policies"][k])["npv"] / 1e6 for k in
                       ("A_ORI_1", "B_ORI_TH_NOW", "C_ORI_TH_TRIG_ASIA", "D_ORI_HUB", "A_ORI_2_STAGED")}
                th_alone = evaluate(up, p, {"units": [{"site": "TH_NSN"}]})["npv"] / 1e6
                best = max(npv, key=npv.get)
                rows.append({"capex_ori_musd": capex, "asia_contracted_t": vol, "price_mult": pm,
                             "net_price_usd_kg_dha": p["price_dha"], **{f"npv_{k}": v for k, v in npv.items()},
                             "npv_TH_alone": th_alone, "delta_B_vs_A": npv["B_ORI_TH_NOW"] - npv["A_ORI_1"],
                             "delta_THalone_vs_A": th_alone - npv["A_ORI_1"],
                             "best_policy": best if npv[best] > 0 else "WAIT (no positive NPV)"})
    return pd.DataFrame(rows)


def niche_origin_inversions(routes: pd.DataFrame, p: dict) -> pd.DataFrame:
    """For the named niches: which origin delivers the higher margin and what change inverts it."""
    targets = [("Norway", "salmon"), ("Chile", "salmon"), ("Thailand", "shrimp"), ("Ecuador", "shrimp"),
               ("Vietnam", "shrimp"), ("United States", "pet_food"), ("European Union", "pet_food")]
    r = routes[(routes.year == 2030)]
    rows = []
    sugar_t = p["dha_fraction"] / (p["dha_yield"] * p["recovery"])
    for c, n in targets:
        br = r[(r.origin_site == "BR_ORI_EXP") & (r.dest_country == c) & (r.niche == n)]
        th = r[(r.origin_site == "TH_NSN") & (r.dest_country == c) & (r.niche == n)]
        if br.empty or th.empty:
            continue
        b, t = br.iloc[0], th.iloc[0]
        gap = b.contribution_usd_t - t.contribution_usd_t
        winner = "Orindiúva" if gap > 0 else "Nakhon Sawan"
        rows.append({"dest_country": c, "niche": n, "margin_BR_usd_kg_dha": b.contribution_usd_kg_dha,
                     "margin_TH_usd_kg_dha": t.contribution_usd_kg_dha, "higher_margin_origin": winner,
                     "gap_usd_t": gap,
                     "inverts_if_BR_freight_up_usd_t": gap if gap > 0 else None,
                     "inverts_if_TH_freight_up_usd_t": -gap if gap < 0 else None,
                     "inverts_if_TH_sugar_down_usd_t_sucrose": gap / sugar_t if gap > 0 else None,
                     "inverts_if_BR_sugar_up_usd_t_sucrose": gap / sugar_t if gap > 0 else None,
                     "inverts_if_duty_on_BR_origin_pct": gap / b.net_price_usd_t if gap > 0 else None,
                     "dha_content": "same SKU from both plants: DHA content does not change the ranking",
                     "note": "Unit margin only; scale, utilisation and fixed costs decide NPV (see policy comparison)."})
    return pd.DataFrame(rows)


def stress_tests(up: Upstream, cfg: dict, segs: dict) -> pd.DataFrame:
    rows = []
    pols = ("A_ORI_1", "A_ORI_2_STAGED", "B_ORI_TH_NOW", "C_ORI_TH_TRIG_UTIL", "D_ORI_HUB")
    for sc in ("base", "high"):
        p, _, _ = integrated_params(up, cfg, sc, segs[sc])
        base = {k: evaluate(up, p, cfg["policies"][k])["npv"] / 1e6 for k in pols}
        for sk, st in cfg["stresses"].items():
            q = copy.deepcopy(p)
            if "outage" in st:
                q["outage"] = st["outage"]
            if "delay" in st:
                q["delay"] = st["delay"]
            if "freight_mult" in st:
                for c, regs in st["freight_mult"].items():
                    for r, m in regs.items():
                        q["freight"][c][r] = dict(q["freight"][c][r], usd=q["freight"][c][r]["usd"] * m)
            for k in pols:
                v = evaluate(up, q, cfg["policies"][k])["npv"] / 1e6
                rows.append({"market_scenario": sc, "stress": sk, "description": st["desc"], "policy": k,
                             "npv_base_musd": base[k], "npv_stress_musd": v, "loss_musd": base[k] - v})
    df = pd.DataFrame(rows)
    res = []
    for (sc, sk), g in df.groupby(["market_scenario", "stress"]):
        g = g.set_index("policy")
        res.append({"market_scenario": sc, "stress": sk,
                    "resilience_value_B_vs_A_musd": g.loc["A_ORI_1", "loss_musd"] - g.loc["B_ORI_TH_NOW", "loss_musd"],
                    "resilience_value_Cutil_vs_A_musd": g.loc["A_ORI_1", "loss_musd"] - g.loc["C_ORI_TH_TRIG_UTIL", "loss_musd"]})
    return df.merge(pd.DataFrame(res), on=["market_scenario", "stress"])


VAR_ORDER = ["sugar_BR", "sugar_TH", "fx_BR", "fx_TH", "fish_oil", "capex_BR", "capex_TH", "dha_yield", "oee",
             "m_price", "m_econ", "m_target", "m_share", "m_marine", "m_growth", "m_adopt"]


def joint_draws(up: Upstream, n: int, seed: int, correlated: bool = True) -> pd.DataFrame:
    """Gaussian copula over v3 cost variables and market multipliers; fish oil is shared by both studies."""
    mc = up.c3["monte_carlo"]["variables"]
    A = up.dm["A"]
    marg = {k: (mc[k]["low"], mc[k]["mode"], mc[k]["high"]) for k in
            ("sugar_BR", "sugar_TH", "fx_BR", "fx_TH", "fish_oil", "capex_BR", "capex_TH", "dha_yield", "oee")}
    marg.update({"m_price": (A["net_price_usd_per_kg_dha"]["low"], A["net_price_usd_per_kg_dha"]["base"],
                             A["net_price_usd_per_kg_dha"]["high"]),
                 "m_econ": (0.6, 1.0, 1.4), "m_target": (0.6, 1.0, 1.4), "m_share": (0.6, 1.0, 1.4),
                 "m_marine": (0.8, 1.0, 1.2), "m_growth": (-0.02, 0.0, 0.02), "m_adopt": (0.7, 1.0, 1.2)})
    C = np.eye(len(VAR_ORDER))
    pairs = [(a, b, r) for a, b, r in up.c3["monte_carlo"]["correlations"] if a in VAR_ORDER and b in VAR_ORDER]
    pairs += [("fish_oil", "m_adopt", up.cm["monte_carlo"]["fish_oil_adoption_corr"])]
    if correlated:
        for a, b, r in pairs:
            i, j = VAR_ORDER.index(a), VAR_ORDER.index(b)
            C[i, j] = C[j, i] = r
    if np.min(np.linalg.eigvalsh(C)) < -1e-10:
        raise ValueError("joint correlation matrix not PSD")
    rng = np.random.default_rng(seed)
    u = stats.norm.cdf(rng.multivariate_normal(np.zeros(len(VAR_ORDER)), C, size=n))
    out = {}
    for k, name in enumerate(VAR_ORDER):
        lo, mo, hi = marg[name]
        out[name] = stats.triang.ppf(u[:, k], (mo - lo) / (hi - lo), loc=lo, scale=hi - lo)
    df = pd.DataFrame(out)
    df.attrs["corr"] = C
    df["outage_u"] = list(rng.random((n, 4, 10)))
    return df


def apply_costs(up: Upstream, p: dict, d: pd.Series) -> dict:
    q = copy.deepcopy(p)
    mc = up.c3["monte_carlo"]["variables"]
    for s, site in q["sites"].items():
        key = "sugar_BR" if site["country"] == "BR" else "sugar_TH"
        site["sugar"] = up.p0["sites"][s]["sugar"] * d[key] / mc[key]["mode"]
    q["fx_shock"] = {"BR": float(d.fx_BR), "TH": float(d.fx_TH)}
    q["capex_mult"] = {"BR": float(d.capex_BR), "TH": float(d.capex_TH)}
    thr = up.c3["monte_carlo"]["delay_threshold_capex"]
    q["delay"] = {s: (1 if q["capex_mult"][site["country"]] > thr else 0) for s, site in q["sites"].items()}
    q["dha_yield"], q["oee"] = float(d.dha_yield), float(d.oee)
    ys = up.v3e.years(q)
    q["outage"] = {s: {str(y): (q["outage_dur"] if d.outage_u[k][i] < q["outage_prob"] else 0.0)
                       for i, y in enumerate(ys)} for k, s in enumerate(q["sites"])}
    return q


def joint_monte_carlo(up: Upstream, cfg: dict, n: int, seed: int, correlated: bool = True,
                      policies: list[str] | None = None) -> pd.DataFrame:
    draws = joint_draws(up, n, seed, correlated)
    keys = policies or list(cfg["policies"])
    rows = []
    for k in range(n):
        d = draws.iloc[k]
        ov = {"fish_oil": d.fish_oil, "price": d.m_price, "econ_mult": d.m_econ, "target_mult": d.m_target,
              "share_mult": d.m_share, "marine_mult": d.m_marine, "growth_add": d.m_growth, "adoption_mult": d.m_adopt}
        seg = up.market_segments("base", ov)
        p, _, _ = integrated_params(up, cfg, "base", seg)
        q = apply_costs(up, p, d)
        rec = {c: d[c] for c in VAR_ORDER}
        rec["incremental_2030_t"] = sum(q["demand"][r]["2030"] for r in q["regions"])
        for key in keys:
            rec[key] = evaluate(up, q, cfg["policies"][key])["npv"] / 1e6
        rows.append(rec)
    return pd.DataFrame(rows)


def mc_summary(mc: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    best = mc[keys].idxmax(axis=1)
    rows = []
    for k in keys:
        v = mc[k].to_numpy()
        q10 = np.quantile(v, 0.1)
        rows.append({"policy": k, "expected_npv_musd": v.mean(), "p10": q10, "p50": np.quantile(v, 0.5),
                     "p90": np.quantile(v, 0.9), "cvar10_musd": v[v <= q10].mean(), "prob_npv_positive": (v > 0).mean(),
                     "prob_best_conditional": (best == k).mean()})
    return pd.DataFrame(rows)


def best_policy(up, cfg, p, keys=None) -> tuple[str, float]:
    keys = keys or list(cfg["policies"])
    v = {k: evaluate(up, p, cfg["policies"][k])["npv"] / 1e6 for k in keys}
    k = max(v, key=v.get)
    return k, v[k]


def value_of_closing_gaps(up: Upstream, cfg: dict, segs: dict) -> pd.DataFrame:
    rows = []
    p_base, _, _ = integrated_params(up, cfg, "base", segs["base"])
    b_key, b_val = best_policy(up, cfg, p_base)
    for item in cfg["voi"]:
        res = {}
        for side in ("low", "high"):
            v = item[side]
            seg = segs["base"]
            weights = None
            pm = 1.0
            sc = "base"
            if item["key"] == "market_scenario":
                sc, seg = v, segs[v]
            if item["key"] == "pipeline_weight":
                weights = {"contracted": 1.0, "qualified_pipeline": v, "unqualified_potential": v * 0.4}
            if item["key"] == "price_mult":
                pm = v
            p, _, _ = integrated_params(up, cfg, sc, seg, weights=weights, price_mult=pm)
            if item["key"] == "capex_ori_musd":
                p["capex_override"] = {"BR_ORI_EXP": v * 1e6}
            if item["key"] == "dha_yield":
                p["dha_yield"] = v
            if item["key"] == "th_capex_mult":
                p["capex_mult"] = dict(p["capex_mult"], TH=v)
            if item["key"] == "freight_mult":
                for c in p["freight"]:
                    for r in p["freight"][c]:
                        p["freight"][c][r] = dict(p["freight"][c][r], usd=p["freight"][c][r]["usd"] * v)
            if item["key"] == "th_delay":
                p["delay"] = {"TH_NSN": int(v)}
            res[side] = best_policy(up, cfg, p)
        changes = res["low"][0] != b_key or res["high"][0] != b_key
        rows.append({"parameter": item["key"], "label": item["label"], "how_to_close": item["how"], "effort": item["effort"],
                     "best_policy_base": b_key, "best_npv_base_musd": b_val,
                     "best_policy_low": res["low"][0], "best_npv_low_musd": res["low"][1],
                     "best_policy_high": res["high"][0], "best_npv_high_musd": res["high"][1],
                     "decision_changes": changes, "swing_best_npv_musd": abs(res["high"][1] - res["low"][1])})
    df = pd.DataFrame(rows)
    eff = {"low": 1.0, "medium": 2.0, "high": 3.0}
    df["priority_score"] = (df.swing_best_npv_musd * np.where(df.decision_changes, 2.0, 1.0)) / df.effort.map(eff)
    return df.sort_values("priority_score", ascending=False)
