"""End-to-end market study run."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pandas as pd

from . import data as D
from . import decision as X
from . import export as XP
from . import model as M

ROOT = D.ROOT


def run(mc_sims: int | None = None, charts: bool = True, publish_v3: bool = False, out_dir: Path | None = None) -> dict:
    cfg = D.load_config()
    out = Path(out_dir or ROOT / cfg["paths"]["outputs"])
    out.mkdir(parents=True, exist_ok=True)
    cur_dir = ROOT / cfg["paths"]["curated"]
    cur_dir.mkdir(parents=True, exist_ok=True)
    d = D.load_all(cfg)
    n = mc_sims or cfg["mc_sims"]
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:  # noqa: BLE001
        commit = "unknown"
    raw = ROOT / cfg["paths"]["raw"]
    manifest = {"version": cfg["version"], "cutoff_date": cfg["cutoff_date"], "git_commit": commit, "seed": cfg["seed"],
                "run_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "mc_sims": n,
                "variable_cost_source": d["v3_variable_cost_source"],
                "input_hashes": {f.name: hashlib.sha256(f.read_bytes()).hexdigest()[:16] for f in sorted(raw.glob("*.csv"))}}
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2))

    segs = {sc: M.segments_df(cfg, d, sc) for sc in cfg["scenarios"]}
    mkts = {sc: M.market_table(cfg, d, segs[sc]) for sc in cfg["scenarios"]}
    seg, mkt = segs["base"], mkts["base"]
    pd.concat([s.assign(scenario=k) for k, s in segs.items()]).to_csv(cur_dir / "segments_by_year.csv", index=False)
    seg.to_csv(out / "segments_by_year_base.csv", index=False)

    for name in ("sources", "definitions", "claims", "customers", "competitors", "pricing", "products"):
        fname = {"sources": "source_registry.csv", "definitions": "market_definitions.csv",
                 "claims": "market_claims_audit.csv", "customers": "customer_evidence.csv",
                 "competitors": "competitor_assets.csv", "pricing": "pricing_evidence.csv",
                 "products": "product_specs.csv"}[name]
        d[name].to_csv(out / fname, index=False)
    d["feed"].to_csv(out / "country_species_feed.csv", index=False)
    d["nutrition"].to_csv(out / "nutrition_requirements.csv", index=False)
    pd.read_csv(raw / "market_assumptions.csv").to_csv(out / "market_assumptions.csv", index=False)

    t, dim_corr = X.triage(cfg, mkt)
    rk = X.rankings(t)
    rk.to_csv(out / "market_rankings.csv", index=False)
    dim_corr.to_csv(out / "triage_dimension_correlation.csv")
    acc = X.account_ranking(d["customers"], mkt)
    acc.to_csv(out / "account_ranking.csv", index=False)
    sel, pinfo = X.optimise_portfolio(cfg, d, mkt)
    sel.to_csv(out / "portfolio_selection.csv", index=False)
    conc = []
    for s in (0.4, 0.6, 0.8):
        conc.append({"max_country_share": s, **{k: v for k, v in X.optimise_portfolio(cfg, d, mkt, {"max_country_share": s})[1].items()
                                                  if k in ("objective_npv_musd", "incremental_sku_2030_t", "fte_used")}})
    for b in (5, 8, 12):
        conc.append({"fte_budget": b, **{k: v for k, v in X.optimise_portfolio(cfg, d, mkt, {"fte_budget": b})[1].items()
                                         if k in ("objective_npv_musd", "incremental_sku_2030_t", "fte_used")}})
    pd.DataFrame(conc).to_csv(out / "portfolio_constraint_sensitivity.csv", index=False)
    voi = X.value_of_information(cfg, d)
    voi.to_csv(out / "value_of_information.csv", index=False)
    be = X.breakeven_prices(cfg, d)
    be.to_csv(out / "capacity_price_frontier.csv", index=False)

    wf = pd.concat([XP.waterfall(cfg, segs[sc], y).assign(scenario=sc) for sc in cfg["scenarios"] for y in cfg["milestones"]])
    wf.to_csv(out / "market_opportunity_waterfall.csv", index=False)
    rec = XP.reconciliation(cfg, d, seg)
    rec.to_csv(out / "top_down_reconciliation.csv", index=False)
    M.diet_cost_comparison(d).to_csv(out / "diet_cost_comparison.csv", index=False)
    tot = {sc: M.portfolio_totals(segs[sc], mkts[sc], cfg) for sc in cfg["scenarios"]}
    cap_rows = []
    module = d["A"]["capacity_increment_2030_t"]["base"]
    for sc, tt in tot.items():
        for y, v in tt.items():
            cap_rows.append({"scenario": sc, "year": y, **v, "modules_of_8500t_needed": v["incremental_sku_t"] / module})
    pd.DataFrame(cap_rows).to_csv(out / "capacity_supported.csv", index=False)

    demands = {sc: XP.demand_for_v3(cfg, d, segs[sc], sc) for sc in cfg["scenarios"]}
    v3_check = XP.validate_against_v3(cfg, demands["base"])
    for sc, dm in demands.items():
        dm.to_csv(out / ("market_demand_scenarios.csv" if sc == "base" else f"market_demand_scenarios_{sc}.csv"), index=False)
    v3eff = XP.v3_effect(cfg, demands)
    v3eff.to_csv(out / "v3_effect_with_market_demand.csv", index=False)
    curves = XP.curves(cfg, d, segs)
    curves.to_csv(out / "market_demand_curves.csv", index=False)
    XP.cockpit_bounds(d, curves).to_csv(out / "cockpit_bounds.csv", index=False)
    if publish_v3:
        shutil.copy(out / "market_demand_scenarios.csv", ROOT / cfg["paths"]["v3_dir"] / "data" / "raw" / "market_demand_scenarios.csv")

    gaps = []
    for _, r in d["sources"][d["sources"].access_status.isin(["search_snippet", "unavailable", "user_supplied"])].iterrows():
        gaps.append({"type": "source", "id": r.source_id, "item": r.definition, "status": r.access_status,
                     "next_step": f"open original: {r.url}"})
    for r in voi.head(6).itertuples():
        gaps.append({"type": "decision_driver", "id": r.parameter, "item": r.label, "status": "assumption",
                     "next_step": r.how_to_close_gap})
    for _, r in d["customers"].iterrows():
        gaps.append({"type": "account", "id": r.entity, "item": r.relationship_status, "status": "unverified volume",
                     "next_step": r.next_proof_needed})
    pd.DataFrame(gaps).to_csv(out / "source_gaps.csv", index=False)

    mc = M.monte_carlo(cfg, d, n, cfg["seed"])
    mc.to_csv(cur_dir / "monte_carlo_draws.csv", index=False)
    q = mc[["incremental_sku_2030_t", "incremental_sku_2035_t", "commercial_npv_musd", "revenue_2030_musd"]].quantile([0.1, 0.5, 0.9])
    q.to_csv(out / "monte_carlo_summary.csv")

    res = dict(cfg=cfg, d=d, segs=segs, mkts=mkts, seg=seg, mkt=mkt, rk=rk, dim_corr=dim_corr, acc=acc, sel=sel,
               pinfo=pinfo, voi=voi, be=be, wf=wf, rec=rec, tot=tot, demands=demands, v3_check=v3_check,
               curves=curves, v3eff=v3eff, mc=mc, mcq=q, manifest=manifest, out=out, conc=pd.DataFrame(conc))
    if charts:
        from . import charts as C
        C.setup()
        C.bridge(seg, out / "bridge_aquaculture_to_revenue.png")
        C.heatmap(seg, mkt, out / "country_niche_contribution_matrix.png")
        C.adoption_curves(segs, mkts, out / "adoption_curves.png")
        C.competitiveness_margin(mkt, out / "competitiveness_vs_margin.png")
        C.capacity_price_frontier(be, d["A"]["net_price_usd_per_kg_dha"]["base"], module, out / "capacity_price_frontier.png")
        C.rankings_chart(rk, out / "rankings_consolidation_expansion.png")
        C.customer_map(acc, d["feed"], out / "customer_map.png")
        from .explorer import build
        build(out / "market_explorer.html", curves, mkts, manifest["run_utc"][:10])
    from .reports import write_memo
    write_memo(res)
    return res
