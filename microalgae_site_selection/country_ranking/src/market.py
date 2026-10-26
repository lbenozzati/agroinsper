"""Prompt 2 – weighted country rankings for growing AlgaPrime DHA sales: one per niche (salmon, shrimp, pet food)
and an overall ranking weighted by each country's technical DHA need per niche."""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import scoring as S
from .plant import COLS, PARENT, RAW, ROOT, _row

OUT = ROOT / "outputs" / "market"
PROC = ROOT / "data" / "processed"
FEED_KEY = {"salmon": "sal_feed_t", "shrimp": "shr_feed_t", "pet": "pet_food_production_t"}
PROD_KEY = {"salmon": "sal_production_t", "shrimp": "shr_production_t", "pet": "pet_food_production_t"}
FCR = {"salmon": 1.25, "shrimp": 1.4, "pet": 1.0}


def load_config() -> dict:
    return yaml.safe_load(open(ROOT / "config_market.yaml"))


def niche_model(cfg: dict, niche: str) -> S.Model:
    n = cfg["niches"][niche]
    c = {"criteria": cfg["criteria"], "scenarios": cfg["scenarios"], "base_scenario": cfg["base_scenario"],
         "subcriteria": {**n["subcriteria"], **cfg["risk_common"]["subcriteria"]},
         "metrics": {**n["metrics"], **cfg["risk_common"]["metrics"]}}
    return S.Model.from_config(c)


def load_inputs() -> pd.DataFrame:
    """Country risk (plant study + market research), niche research, analyst rubrics/fallbacks (later overrides)."""
    frames = []
    fb = RAW / "market_analyst_fallback.csv"
    if fb.exists():
        frames.append(pd.read_csv(fb)[COLS])
    for f in [RAW / "research" / "risk.csv", RAW / "research" / "market_regulation.csv"] + sorted((RAW / "market_research").glob("*.csv")):
        if f.exists():
            d = pd.read_csv(f)
            d["notes"] = f"[{f.stem}] " + d["notes"].fillna("").astype(str)
            frames.append(d[COLS])
    for f in [RAW / "market_rubrics.csv"]:
        if f.exists():
            frames.append(pd.read_csv(f)[COLS])
    data = pd.concat(frames, ignore_index=True)
    data["country"] = data.country.str.replace(r"\s*\(.*\)$", "", regex=True).str.strip()  # "Australia (Tasmania)"
    data = data[pd.to_numeric(data.raw_value, errors="coerce").notna()]
    return data.drop_duplicates(["country", "metric_id"], keep="last").reset_index(drop=True)


def num(d: pd.DataFrame, c: str, m: str) -> float:
    r = d[(d.country == c) & (d.metric_id == m)]
    return float(pd.to_numeric(r.raw_value, errors="coerce").iloc[0]) if len(r) else np.nan


def transit_days(niche: str) -> dict:
    """Door-to-door days Orindiúva -> market port of the niche (same waypoint routing as the plant ranking)."""
    from . import searoutes as SR
    pc = yaml.safe_load(open(RAW / "ports_market.yaml"))
    ports = {"origin": (tuple(pc["origin"]["port"][0]), pc["origin"]["port"][1])}
    for c, v in pc["markets"].items():
        spec = v.get(niche, v.get("all"))
        if spec is not None:
            ports[c] = (tuple(spec[0]), spec[1])
    g = SR.build_graph(ports)
    out = {}
    for c in pc["markets"]:
        if c not in ports:
            continue
        if c in pc.get("domestic_days", {}):
            out[c] = (0.0, pc["domestic_days"][c])
            continue
        nm = SR.shortest_nm(g, "origin", c)
        out[c] = (nm, nm / (pc["speed_knots"] * 24) + 2 * pc["port_days_per_call"] + pc["origin"]["inland_days"]
                  + pc["inland_days_market"])
    return out


RUBRIC_METRIC = {"canal": "{p}_relationship", "registro": "{p}_registration", "competicao": "{p}_competitive"}
TRANSIT_OK_DAYS = 25.0


def rubric_components(niche: str, transit: dict | None = None) -> pd.DataFrame:
    """Component rubrics (data/raw/market_rubric_components.csv): one row per country × rubric with the
    floor/ceiling sum of A-D and the midpoint used as the score. C2 of 'competicao' = 1 if transit ≤ 25 days."""
    f = RAW / "market_rubric_components.csv"
    if not f.exists():
        return pd.DataFrame(columns=["country", "rubric", "lo", "hi", "mid", "detail"])
    d = pd.read_csv(f)
    d = d[d.niche == niche].astype({"lo": object, "hi": object, "evidence": object}).copy()
    for i in d.index[d.lo == "transit"]:
        days = (transit or {}).get(d.at[i, "country"], (np.nan, np.nan))[1]
        ok = float(days <= TRANSIT_OK_DAYS) if not np.isnan(days) else np.nan
        d.loc[i, ["lo", "hi"]] = (0.0, 1.0) if np.isnan(ok) else (ok, ok)
        d.at[i, "evidence"] = f"prazo desde Orindiúva {days:.0f} dias (limite {TRANSIT_OK_DAYS:.0f})"
    d[["lo", "hi"]] = d[["lo", "hi"]].astype(float)
    rows = []
    for (c, r), g in d.groupby(["country", "rubric"]):
        lo, hi = g.lo.sum(), g.hi.sum()
        det = "; ".join(f"{x.component}={x.lo:g}" + (f"-{x.hi:g}" if x.hi != x.lo else "") + f" ({x.evidence})"
                        for x in g.itertuples())
        rows.append(dict(country=c, rubric=r, lo=lo, hi=hi, mid=(lo + hi) / 2, detail=det))
    return pd.DataFrame(rows)


def derive(data: pd.DataFrame, cfg: dict, niche: str) -> pd.DataFrame:
    """Per-niche frame: niche metrics + shared country risk + derived DHA need and FX volatility."""
    countries = cfg["niches"][niche]["countries"]
    d = data[data.country.isin(countries)].copy()
    rows = []
    g = cfg["dha_g_per_kg_feed"][niche]
    pref = {"salmon": "sal", "shrimp": "shr", "pet": "pet"}[niche]
    td = transit_days(niche)
    for c in countries:
        if c in td:
            nm, days = td[c]
            rows.append(_row(c, f"{pref}_transit_days", round(days, 1), "days", "2026",
                             "Derived: Orindiúva -> Santos -> market port by waypoint sea routing at 15 kn + 2 port calls "
                             "+ inland legs (data/raw/ports_market.yaml)", f"sea distance {nm:,.0f} nm", "Medium", "estimate"))
        feed = num(d, c, FEED_KEY[niche])
        basis = FEED_KEY[niche]
        if np.isnan(feed):
            prod = num(d, c, PROD_KEY[niche])
            feed = prod * FCR[niche] if not np.isnan(prod) else np.nan
            basis = f"{PROD_KEY[niche]} x FCR {FCR[niche]}"
        if not np.isnan(feed):
            rows.append(_row(c, "dha_need_t", round(feed * g / 1000, 1), "t DHA/yr", "2024-25",
                             f"Derived: {basis} x {g} g DHA/kg feed (market_expansion nutrition_requirements)", "",
                             "Medium", "estimate"))
        fx = [num(d, c, f"sr_fx_usd_{y}") for y in range(2020, 2026)]
        if all(not np.isnan(x) and x > 0 for x in fx):
            ch = np.diff(np.log(fx))
            rows.append(_row(c, "sr_fx_volatility", round(float(np.sqrt(np.mean(ch ** 2)) * 100), 2), "%", "2020-2025",
                             "Derived: RMS of annual log changes of LCU/USD", "", "Medium", "reported"))
    rub = rubric_components(niche, td)
    rub_ids = [v.format(p=pref) for v in RUBRIC_METRIC.values()]
    for x in rub[rub.country.isin(countries)].itertuples():
        rows.append(_row(x.country, RUBRIC_METRIC[x.rubric].format(p=pref), round(x.mid, 2), "rubric 0-10", "2026",
                         f"Rubrica por componentes: faixa {x.lo:g}-{x.hi:g}", "", "Medium" if x.hi - x.lo <= 2 else "Low",
                         "estimate"))
        rows[-1]["notes"] = x.detail[:900]
    der = pd.DataFrame(rows, columns=COLS)
    drop = ["dha_need_t", "sr_fx_volatility", f"{pref}_transit_days"] + (rub_ids if len(rub) else [])
    out = pd.concat([d[~d.metric_id.isin(drop)], der],
                    ignore_index=True)
    out["niche"] = niche
    return out


def run_niche(cfg: dict, data: pd.DataFrame, niche: str, n_mc: int, n_dir: int) -> dict:
    model = niche_model(cfg, niche)
    countries = cfg["niches"][niche]["countries"]
    d = derive(data, cfg, niche)
    values = S.wide_values(model, d).reindex(countries).apply(pd.to_numeric, errors="coerce")
    conf = d.pivot_table(index="country", columns="metric_id", values="confidence", aggfunc="first") \
        .reindex(index=countries, columns=list(model.metrics))
    ms_all = S.metric_scores(model, values)
    mcov = ms_all.notna().mean()
    dropped = [k for k in model.metrics if mcov[k] < cfg["min_metric_coverage"]]
    ms = ms_all.drop(columns=dropped)
    score, crit, sub = S.aggregate(model, ms)
    cov = S.coverage(model, ms_all)
    cov_used = S.coverage(model, ms.reindex(columns=list(model.metrics)))
    lo, _, _ = S.aggregate(model, ms, fill=0.0)
    hi, _, _ = S.aggregate(model, ms, fill=10.0)
    q, _, _ = S.aggregate(model, ms, keep=[k for k, m in model.metrics.items() if m.method != "rubric"])
    used_w = sum(model.nominal_weight(k) for k in ms.columns)
    insufficient = (cov_used.data_coverage_of_weight / used_w) < cfg["min_country_coverage"]
    scen = {nm: S.aggregate(model, ms, w)[0] for nm, w in model.scenarios.items()}
    base_w = model.scenarios[model.base]
    dr = S.dirichlet_ranks(crit, base_w, n_dir, cfg["seed"])
    keep_vals = values.drop(columns=dropped)
    m_used = copy.deepcopy(model)
    m_used.metrics = {k: v for k, v in model.metrics.items() if k not in dropped}
    mc = S.monte_carlo(m_used, keep_vals, conf.drop(columns=dropped), n_mc, cfg["seed"])
    need = values["dha_need_t"] if "dha_need_t" in values else pd.Series(np.nan, index=countries)
    adj = score.where(~insufficient, score - 100)  # insufficient-data countries ranked after the rest
    tab = pd.DataFrame({
        "niche": niche, "rank": S.rank(adj), "data_status": np.where(insufficient, "dados insuficientes", "ok"), "score": score.round(3), **{c: crit[c].round(2) for c in model.criteria},
        **{f"rank_{n.split()[0].lower()}": S.rank(s) for n, s in scen.items()},
        "score_quant_only": q.round(3), "rank_quant_only": S.rank(q),
        "score_if_missing_0": lo.round(3), "score_if_missing_10": hi.round(3), **cov, **dr.round(4), **mc.round(4),
        "dha_need_t": need.round(0),
    }).sort_values("rank")
    tab.index.name = "country"
    long = ms.stack(future_stack=True).rename("score").reset_index().rename(columns={"level_1": "metric_id"})
    long = long.merge(d[COLS], on=["country", "metric_id"], how="left")
    long["niche"] = niche
    long["sub"] = long.metric_id.map(lambda k: model.metrics[k].sub)
    long["criterion"] = long["sub"].map(lambda s: model.subs[s][0])
    long["method"] = long.metric_id.map(lambda k: model.metrics[k].method)
    long["nominal_weight"] = long.metric_id.map(model.nominal_weight)
    order = list(tab.index)
    tips = []
    for b in order[1:3]:
        for c in model.criteria:
            tips.append(dict(niche=niche, leader=order[0], challenger=b, criterion=c, base_weight=base_w[c],
                             weight_where_challenger_overtakes=S.weight_tipping(crit, base_w, order[0], b, c)))
    pd.DataFrame({"metric_id": list(model.metrics), "coverage": [round(mcov[k], 2) for k in model.metrics],
                  "used": [k not in dropped for k in model.metrics]}).assign(niche=niche) \
        .to_csv(OUT / f"market_metric_coverage_{niche}.csv", index=False)
    return dict(model=model, table=tab, dropped=dropped, long=long, sub=sub, crit=crit, tips=pd.DataFrame(tips), data=d,
                contributions=crit.mul(pd.Series(base_w)))


def overall(results: dict) -> pd.DataFrame:
    """Country score = sum over niches of niche score x share of the country's technical DHA need in that niche.
    Niche goalposts for DHA need are common (30–10,000 t), so size is comparable across niches."""
    rows = []
    for niche, r in results.items():
        t = r["table"]
        for c in t.index:
            rows.append(dict(country=c, niche=niche, score=t.score[c], dha_need_t=t.dha_need_t[c],
                             niche_rank=int(t["rank"][c])))
    pairs = pd.DataFrame(rows)
    pairs["dha_need_t"] = pairs.dha_need_t.fillna(0.0)
    out = []
    for c, g in pairs.groupby("country"):
        w = g.dha_need_t / g.dha_need_t.sum() if g.dha_need_t.sum() > 0 else pd.Series(1 / len(g), index=g.index)
        best = g.sort_values("score", ascending=False).iloc[0]
        out.append(dict(country=c, overall_score=float((g.score * w).sum()), dha_need_total_t=g.dha_need_t.sum(),
                        niches=", ".join(f"{n} ({s:.2f})" for n, s in zip(g.niche, g.score)),
                        best_niche=best.niche, best_niche_score=best.score, n_niches=len(g)))
    ov = pd.DataFrame(out).set_index("country")
    ov["overall_rank"] = S.rank(ov.overall_score)
    return ov.sort_values("overall_rank"), pairs.sort_values("score", ascending=False)


def run_all(n_mc: int | None = None, charts: bool = True) -> dict:
    cfg = load_config()
    data = load_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)
    res = {n: run_niche(cfg, data, n, n_mc or cfg["mc_sims"], cfg["dirichlet_draws"]) for n in cfg["niches"]}
    ov, pairs = overall(res)
    pd.concat([r["data"] for r in res.values()]).sort_values(["niche", "country", "metric_id"]) \
        .to_csv(PROC / "market_inputs_long.csv", index=False)
    for n, r in res.items():
        r["table"].to_csv(OUT / f"market_ranking_{n}.csv")
        r["sub"].round(3).to_csv(OUT / f"market_subcriteria_{n}.csv")
    pd.concat([r["long"] for r in res.values()]).to_csv(OUT / "market_metric_scores.csv", index=False)
    pd.concat([r["tips"] for r in res.values()]).to_csv(OUT / "market_tipping_points.csv", index=False)
    ov.round(3).to_csv(OUT / "market_ranking_overall.csv")
    pairs.round(3).to_csv(OUT / "market_ranking_country_niche_pairs.csv", index=False)
    rub = pd.concat([r["long"][r["long"].method == "rubric"][["niche", "country", "metric_id", "score", "notes"]]
                     for r in res.values()])
    rub.assign(evaluator="", evaluator_score="").to_csv(OUT / "market_rubric_ratings_template.csv", index=False)
    out = dict(cfg=cfg, results=res, overall=ov, pairs=pairs)
    if charts:
        from . import market_report
        market_report.charts(out)
    from . import market_report
    market_report.memo(out)
    return out
