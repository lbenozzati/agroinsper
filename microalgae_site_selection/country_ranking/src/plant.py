"""Prompt 1 – country ranking for the next AlgaPrime DHA plant (weights 30/20/15/15/20, deepened sub-criteria)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import scoring as S
from . import searoutes as SR

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs" / "plant"
COLS = ["country", "metric_id", "raw_value", "unit", "reference_year", "source_name", "source_url",
        "date_accessed", "value_type", "confidence", "notes"]
COUNTRIES = ["Brazil", "Thailand", "China", "India", "Vietnam", "Indonesia", "Chile", "Mexico",
             "United States", "Ecuador", "Peru", "Philippines"]
V2_REUSED = {  # v2 metric -> metric id used here
    "pe_sugar_production": "pe_sugar_production", "pe_electricity_price": "pe_electricity_price",
    "pe_renewable_share_electricity": "pe_renewable_share_electricity",
    "pe_steam_biomass_cogeneration": "pe_steam_biomass_cogeneration", "pe_water_stress": "pe_water_stress",
    "pe_industrial_water_wastewater_infra": "pe_industrial_water_wastewater_infra",
    "pe_construction_epc_capability": "pe_construction_epc_capability", "ma_lpi_score": "ma_lpi_score",
    "ma_biomar_customer_proximity": "ma_biomar_customer_proximity",
    "cr_existing_manufacturing": "cr_existing_manufacturing", "cr_fermentation_talent": "cr_fermentation_talent",
    "cr_commercial_innovation_presence": "cr_commercial_innovation_presence",
    "ri_local_production_permitting": "ri_local_production_permitting",
    "ri_investment_incentives": "ri_investment_incentives", "ri_trade_fdi_access": "ri_trade_fdi_access",
    "sr_local_competition_overcapacity": "sr_local_competition_overcapacity", "sr_ip_protection": "sr_ip_special301",
    "sr_sovereign_rating_notch": "sr_sovereign_rating_notch", "ri_corporate_tax_rate": "ri_corporate_tax_rate",
}
STEAM_COST_BY_RUBRIC = {10.0: 9.0, 7.5: 15.0, 5.0: 25.0, 2.5: 35.0, 0.0: 45.0}  # USD/t steam (assumption)
REF_COST = {"sugar_t_per_t": 5.05, "kwh_per_t": 3000, "steam_t_per_t": 6.0, "other_usd_per_t": 360 + 50 * 0.6,
            "dha_kg_per_t": 360}  # same physical basis as v3 assumptions A001-A008


FTA_NAMES = {"Norway": "Norway", "UK": "United Kingdom", "United Kingdom": "United Kingdom", "EU": "European Union",
             "USA": "United States", "United States": "United States", "Chile": "Chile", "Ecuador": "Ecuador",
             "India": "India", "Vietnam": "Vietnam", "Indonesia": "Indonesia", "Thailand": "Thailand", "China": "China"}
# Australia was not in the research brief; in-force agreements with Australia (analyst, verify on DFAT list)
AUSTRALIA_FTA = {c: {"Australia"} for c in ["Chile", "China", "Thailand", "Indonesia", "Vietnam", "India", "United States",
                                              "Peru", "Mexico", "Philippines"]}


def parse_fta(note: str) -> set[str]:
    """'[file] Covered: Chile (...); Ecuador (...). Not counted...' -> {'Chile', 'Ecuador'}."""
    import re
    body = note.split("Covered:", 1)[-1].split(".")[0] if "Covered:" in note else ""
    body = re.sub(r"\([^)]*\)", "", body)
    out = set()
    for part in body.split(";"):
        name = part.strip().split(" ")[0] if part.strip() else ""
        if name in FTA_NAMES:
            out.add(FTA_NAMES[name])
    return out


def load_config() -> dict:
    return yaml.safe_load(open(ROOT / "config_plant.yaml"))


def load_inputs() -> pd.DataFrame:
    """Merge (1) frozen v2 inputs, (2) new research files, (3) analyst rubrics; later sources override earlier."""
    v2 = pd.read_csv(PARENT / "v3" / "data" / "raw" / "frozen_v2" / "raw_country_data.csv")
    v2 = v2[v2.metric_id.isin(V2_REUSED)].copy()
    v2["metric_id"] = v2.metric_id.map(V2_REUSED)
    v2["notes"] = "[v2] " + v2["notes"].fillna("")
    frames = [v2[COLS]]
    fb = RAW / "plant_analyst_fallback.csv"  # analyst values used only where research found nothing
    if fb.exists():
        frames.append(pd.read_csv(fb)[COLS])
    for f in sorted((RAW / "research").glob("*.csv")):
        d = pd.read_csv(f)
        d["notes"] = f"[{f.stem}] " + d["notes"].fillna("").astype(str)
        frames.append(d[COLS])
    rub = RAW / "plant_rubrics.csv"
    if rub.exists():
        d = pd.read_csv(rub)
        frames.append(d[COLS])
    data = pd.concat(frames, ignore_index=True)
    data = data[data.country.isin(COUNTRIES)]
    data["raw_value"] = data["raw_value"]
    num = pd.to_numeric(data.raw_value, errors="coerce")
    data = data[num.notna() | data.metric_id.str.startswith("ref_mill_name")]
    data = data.drop_duplicates(["country", "metric_id"], keep="last")
    return data.reset_index(drop=True)


def _row(country, metric, value, unit, year, source, notes, conf="Medium", vtype="estimate"):
    return dict(country=country, metric_id=metric, raw_value=value, unit=unit, reference_year=year,
                source_name=source, source_url="", date_accessed="2026-10-14", value_type=vtype,
                confidence=conf, notes=notes)


def num(data: pd.DataFrame, country: str, metric: str) -> float:
    r = data[(data.country == country) & (data.metric_id == metric)]
    return float(pd.to_numeric(r.raw_value, errors="coerce").iloc[0]) if len(r) else np.nan


def conf_of(data, country, metric) -> str:
    r = data[(data.country == country) & (data.metric_id == metric)]
    return r.confidence.iloc[0] if len(r) else "Low"


def market_weights(basis: str = "sam_dha_t") -> pd.Series:
    """Priority-market weights = serviceable algal-DHA demand (SAM, t DHA) in 2030 from the market study.
    basis="tam_dha_t" (technical DHA need, shrimp-heavier) is the sensitivity case."""
    seg = pd.read_csv(PARENT / "market_expansion" / "outputs" / "segments_by_year_base.csv")
    w = seg[seg.year == 2030].groupby("country")[basis].sum()
    return w / w.sum()


def transit_matrix(ports_cfg: dict) -> pd.DataFrame:
    ports = {}
    for o, v in ports_cfg["origins"].items():
        for pn, (xy, links) in v["ports"].items():
            ports[f"o:{o}:{pn}"] = (tuple(xy), links)
    for m, v in ports_cfg["markets"].items():
        ports[f"m:{m}"] = (tuple(v["port"][0]), v["port"][1])
        if "alt_port" in v:
            ports[f"m:{m}:alt"] = (tuple(v["alt_port"][0]), v["alt_port"][1])
    g = SR.build_graph(ports)
    kn = ports_cfg["speed_knots"]
    rows = []
    for o, v in ports_cfg["origins"].items():
        for m, mv in ports_cfg["markets"].items():
            best = (math.inf, None, None)
            for pn in v["ports"]:
                for mk in [f"m:{m}"] + ([f"m:{m}:alt"] if "alt_port" in mv else []):
                    nm = SR.shortest_nm(g, f"o:{o}:{pn}", mk)
                    if nm < best[0]:
                        best = (nm, pn, mk)
            nm, pn, _ = best
            if o == m:
                days = v["inland_days"] + mv["inland_days"]
                nm = 0.0
            else:
                days = (nm / (kn * 24) + 2 * ports_cfg["port_days_per_call"] + v["inland_days"] + mv["inland_days"]
                        + ports_cfg.get("transshipment_days", {}).get(o, 0.0))
            rows.append(dict(origin=o, market=m, origin_port=pn, sea_nm=round(nm), door_to_door_days=round(days, 1)))
    return pd.DataFrame(rows)


def derive(data: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Derived metrics with explicit formulas (each row says how it was computed)."""
    rows = []
    ports_cfg = yaml.safe_load(open(RAW / "ports.yaml"))
    tm = transit_matrix(ports_cfg)
    w = market_weights()
    for c in COUNTRIES:
        prod, cons = num(data, c, "pe_sugar_production"), num(data, c, "pe_sugar_consumption")
        if not np.isnan(prod) and not np.isnan(cons) and cons > 0:
            rows.append(_row(c, "pe_sugar_self_sufficiency", round(prod / cons, 3), "ratio", "2025/26",
                             "Derived: production / consumption (USDA FAS)", "", conf_of(data, c, "pe_sugar_consumption"),
                             "reported"))
        t = tm[tm.origin == c].set_index("market").door_to_door_days
        days = float((t.reindex(w.index) * w).sum())
        rows.append(_row(c, "ma_transit_days_weighted", round(days, 2), "days", "2030 weights",
                         "Derived: waypoint sea routing at 15 kn + port calls + inland legs, weighted by 2030 SAM of "
                         "the market study", "Top weights: " + ", ".join(f"{k} {v:.0%}" for k, v in w.nlargest(4).items()),
                         "Medium", "estimate"))
        fta = data[(data.country == c) & (data.metric_id == "ma_fta_priority_markets")]
        if len(fta):
            partners = parse_fta(str(fta.notes.iloc[0])) | AUSTRALIA_FTA.get(c, set())
            share = float(sum(w.get(p, 0.0) for p in partners if p != c) + w.get(c, 0.0))
            rows.append(_row(c, "ma_fta_demand_share", round(share, 3), "share of 2030 SAM", "2026",
                             "Derived: SAM share of priority markets with an in-force trade agreement (domestic counts)",
                             "Partners: " + ", ".join(sorted(partners)), conf_of(data, c, "ma_fta_priority_markets"),
                             "estimate"))
        cit, hol = num(data, c, "ri_corporate_tax_rate"), num(data, c, "ri_tax_holiday_years")
        red = num(data, c, "ri_incentive_rate")
        if not np.isnan(cit):
            h = 0 if np.isnan(hol) else min(hol, 10)
            during = 0.0 if np.isnan(red) else red
            during = max(during, 15.0)  # GloBE floor: Corbion group > EUR 750m (NL IIR / local QDMTT)
            after = max(cit, 15.0)
            eff = (h * min(during, after) + (10 - h) * after) / 10
            rows.append(_row(c, "ri_effective_tax_10y", round(eff, 2), "%", "2026",
                             "Derived: 10-year average of statutory CIT, incentive years and the 15% GloBE floor",
                             f"CIT {cit}%, incentive years {h:g}, incentive rate {during:g}%",
                             conf_of(data, c, "ri_corporate_tax_rate"), "estimate"))
        fx = [num(data, c, f"sr_fx_usd_{y}") for y in range(2020, 2026)]
        if all(not np.isnan(x) for x in fx):
            ch = np.diff(np.log(fx))
            vol = float(np.sqrt(np.mean(ch ** 2)) * 100)
            rows.append(_row(c, "sr_fx_volatility", round(vol, 2), "% (RMS annual log change)", "2020-2025",
                             "Derived: RMS of annual log changes of the average LCU/USD rate", "", "Medium", "reported"))
        sp = num(data, c, "pe_sugar_price_domestic")
        el = num(data, c, "pe_electricity_price")
        st = num(data, c, "pe_steam_biomass_cogeneration")
        if not any(np.isnan(x) for x in (sp, el, st)):
            steam = STEAM_COST_BY_RUBRIC.get(st, 25.0)
            vc = (REF_COST["sugar_t_per_t"] * sp + REF_COST["kwh_per_t"] * el + REF_COST["steam_t_per_t"] * steam
                  + REF_COST["other_usd_per_t"]) / REF_COST["dha_kg_per_t"]
            rows.append(_row(c, "xc_reference_variable_cost", round(vc, 2), "USD/kg DHA", "2026",
                             "Cross-check (not scored): v3 physical basis x local sugar, power and steam prices",
                             f"sugar {sp:.0f} USD/t, power {el:.3f} USD/kWh, steam {steam:.0f} USD/t", "Low", "estimate"))
    der = pd.DataFrame(rows)
    return pd.concat([data[~data.metric_id.isin(der.metric_id.unique())], der], ignore_index=True), tm


def gates(data: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    g = cfg["gates"]
    out = []
    for c in COUNTRIES:
        reasons, flag = [], "Pass"
        prod, imp = num(data, c, "pe_sugar_production"), num(data, c, "pe_sugar_self_sufficiency")
        if c == "United States":
            pass  # corn dextrose at the Blair wet mill is the feedstock; sugar balance not a constraint
        elif np.isnan(prod) or prod < g["sugar_min_mt"]:
            reasons.append(f"Pouca produção de açúcar ({prod} Mt): matéria-prima importada"); flag = "Review"
        bws = num(data, c, "pe_basin_water_stress")
        if not np.isnan(bws) and bws >= g["basin_stress_review"]:
            reasons.append(f"Estresse hídrico alto na bacia do site ({bws:g}/5)"); flag = "Review"
        ws = num(data, c, "pe_water_stress")
        if not np.isnan(ws) and ws >= g["national_stress_review"]:
            reasons.append(f"Estresse hídrico nacional {ws:g}%"); flag = "Review"
        lpi = num(data, c, "ma_lpi_score")
        if not np.isnan(lpi) and lpi < g["lpi_fail"]:
            reasons.append(f"LPI {lpi}"); flag = "Fail"
        elif not np.isnan(lpi) and lpi < g["lpi_review"]:
            reasons.append(f"Logística fraca (LPI {lpi})"); flag = "Review" if flag == "Pass" else flag
        fdi = num(data, c, "ri_fdi_restrictiveness")
        if not np.isnan(fdi) and fdi >= g["fdi_fail"]:
            reasons.append("Fechado a IED"); flag = "Fail"
        out.append(dict(country=c, gate=flag, gate_reasons="; ".join(reasons) or "Todas as condições mínimas atendidas"))
    return pd.DataFrame(out).set_index("country")


def run(n_mc: int | None = None, n_dir: int | None = None) -> dict:
    cfg = load_config()
    model = S.Model.from_config(cfg)
    data, tm = derive(load_inputs(), cfg)
    PROC.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    data.sort_values(["country", "metric_id"]).to_csv(PROC / "plant_inputs_long.csv", index=False)
    tm.to_csv(OUT / "plant_transit_matrix.csv", index=False)
    values = S.wide_values(model, data).reindex(COUNTRIES)
    conf = data.pivot_table(index="country", columns="metric_id", values="confidence", aggfunc="first") \
        .reindex(index=COUNTRIES, columns=list(model.metrics))
    ms = S.metric_scores(model, values)
    score, crit, sub = S.aggregate(model, ms)
    cov = S.coverage(model, ms)
    lo, _, _ = S.aggregate(model, ms, fill=0.0)
    hi, _, _ = S.aggregate(model, ms, fill=10.0)
    quant = [k for k, m in model.metrics.items() if m.method != "rubric"]
    q, qcrit, _ = S.aggregate(model, ms, keep=quant)
    scen = {name: S.aggregate(model, ms, w)[0] for name, w in model.scenarios.items()}
    base_w = model.scenarios[model.base]
    dr = S.dirichlet_ranks(crit, base_w, n_dir or cfg["dirichlet_draws"], cfg["seed"])
    mc = S.monte_carlo(model, values, conf, n_mc or cfg["mc_sims"], cfg["seed"])
    gt = gates(data, cfg)
    # sensitivity: transit weighted by TAM (technical DHA need) instead of SAM
    wt = market_weights("tam_dha_t")
    v_tam = values.copy()
    for c in COUNTRIES:
        tt = tm[tm.origin == c].set_index("market").door_to_door_days
        v_tam.loc[c, "ma_transit_days_weighted"] = float((tt.reindex(wt.index) * wt).sum())
    s_tam, _, _ = S.aggregate(model, S.metric_scores(model, v_tam.apply(pd.to_numeric, errors="coerce")))
    v2 = pd.read_csv(PARENT / "v3" / "data" / "raw" / "frozen_v2" / "v2_country_scores.csv").set_index("country")
    ref = data[data.metric_id == "ref_mill_name"].set_index("country").raw_value
    xc = data[data.metric_id == "xc_reference_variable_cost"].set_index("country").raw_value
    rk = S.rank(score)
    tab = pd.DataFrame({
        "rank": rk, "score": score.round(3), **{c: crit[c].round(2) for c in model.criteria},
        **{f"rank_{n.split()[0].lower()}": S.rank(s) for n, s in scen.items()},
        "transit_days_tam_weighted": v_tam["ma_transit_days_weighted"].astype(float).round(1),
        "rank_tam_market_weights": S.rank(s_tam),
        "score_quant_only": q.round(3), "rank_quant_only": S.rank(q),
        "score_if_missing_0": lo.round(3), "score_if_missing_10": hi.round(3),
        **cov, **dr.round(4), **mc.round(4), "gate": gt.gate, "gate_reasons": gt.gate_reasons,
        "v2_score": v2.score.reindex(COUNTRIES), "v2_rank": v2.score.reindex(COUNTRIES).rank(ascending=False, method="min"),
        "reference_site": ref.reindex(COUNTRIES),
        "xc_variable_cost_usd_kg_dha": pd.to_numeric(xc, errors="coerce").reindex(COUNTRIES),
    }).sort_values("rank")
    tab.index.name = "country"
    tab.to_csv(OUT / "plant_country_ranking.csv")
    long = ms.stack(future_stack=True).rename("score").reset_index().rename(columns={"level_1": "metric_id"})
    long = long.merge(data[["country", "metric_id", "raw_value", "unit", "reference_year", "source_name", "source_url",
                            "value_type", "confidence", "notes"]], on=["country", "metric_id"], how="left")
    long["sub"] = long.metric_id.map(lambda k: model.metrics[k].sub)
    long["criterion"] = long["sub"].map(lambda s: model.subs[s][0])
    long["method"] = long.metric_id.map(lambda k: model.metrics[k].method)
    long["nominal_weight"] = long.metric_id.map(model.nominal_weight)
    long.to_csv(OUT / "plant_metric_scores.csv", index=False)
    sub.round(3).to_csv(OUT / "plant_subcriteria_scores.csv")
    pd.DataFrame({n: s.round(3) for n, s in scen.items()}).to_csv(OUT / "plant_weight_scenarios.csv")
    crit[list(model.criteria)].corr().round(2).to_csv(OUT / "plant_criterion_correlation.csv")
    # goalpost robustness
    rob = []
    for st in (0.75, 1.25, 1.5):
        s2, _, _ = S.aggregate(model, S.metric_scores(model, values, stretch=st))
        r2 = S.rank(s2)
        rob.append(dict(goalpost_stretch=st, countries_changing_rank=int((r2 != rk).sum()),
                        top3=", ".join(r2.sort_values().index[:3]), top1_unchanged=r2.idxmin() == rk.idxmin()))
    pd.DataFrame(rob).to_csv(OUT / "plant_goalpost_robustness.csv", index=False)
    # tipping points: leader vs each of the next 3
    order = list(rk.sort_values().index)
    tips = []
    for b in order[1:4]:
        for c in model.criteria:
            x = S.weight_tipping(crit, base_w, order[0], b, c)
            tips.append(dict(leader=order[0], challenger=b, criterion=c, base_weight=base_w[c],
                             weight_where_challenger_overtakes=x))
    pd.DataFrame(tips).to_csv(OUT / "plant_tipping_points.csv", index=False)
    # rubric template for independent evaluators
    rub = long[long.method == "rubric"][["country", "metric_id", "score", "notes"]].rename(columns={"score": "analyst_score"})
    rub["evaluator"] = ""
    rub["evaluator_score"] = ""
    rub.to_csv(OUT / "plant_rubric_ratings_template.csv", index=False)
    return dict(cfg=cfg, model=model, data=data, values=values, ms=ms, crit=crit, sub=sub, table=tab, tm=tm,
                qcrit=qcrit, contributions=crit.mul(pd.Series(base_w)), weights=market_weights())
