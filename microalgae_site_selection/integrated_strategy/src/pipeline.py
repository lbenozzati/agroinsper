"""Integrated run: provenance -> harmonised inputs -> routes -> policies -> risk -> frontiers -> outputs."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd

from . import integration as I
from . import policies as P
from . import stats as ST

ROOT = I.ROOT


def run(mc_sims: int | None = None, run_upstream_tests: bool = True, charts: bool = True,
        out_dir: Path | None = None) -> dict:
    cfg = I.load_config()
    out = Path(out_dir or ROOT / cfg["paths"]["outputs"])
    out.mkdir(parents=True, exist_ok=True)
    proc = ROOT / cfg["paths"]["processed"]
    proc.mkdir(parents=True, exist_ok=True)
    raw = ROOT / cfg["paths"]["raw"]
    n = mc_sims or cfg["mc_sims"]
    up = I.Upstream(cfg)
    prov = I.provenance(up, run_upstream_tests)
    prov.update(run_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), mc_sims=n, seed=cfg["seed"],
                cutoff_date=cfg["cutoff_date"])
    (out / "run_manifest.json").write_text(json.dumps(prov, indent=2))

    segs = {sc: up.market_segments(sc) for sc in cfg["market_scenarios"]}
    tariffs = pd.read_csv(raw / "tariff_assumptions.csv")
    p_base, dem_base, seg_base = I.integrated_params(up, cfg, "base", segs["base"])
    rec = I.reconciliation(up, cfg, p_base, dem_base, seg_base)
    rec.to_csv(out / "integration_reconciliation.csv", index=False)
    routes = I.route_economics(up, cfg, p_base, seg_base, tariffs)
    routes.to_csv(out / "route_economics.csv", index=False)
    inv = P.niche_origin_inversions(routes, p_base)
    inv.to_csv(out / "niche_origin_inversions.csv", index=False)

    comp, flows, alloc, store = P.compare(up, cfg, segs)
    comp.to_csv(out / "investment_policy_comparison.csv", index=False)
    flows.to_csv(out / "project_cashflows.csv", index=False)
    alloc.to_csv(out / "allocation_by_scenario.csv", index=False)
    compo = P.composition(alloc, comp, cfg)
    compo.to_csv(out / "portfolio_composition.csv", index=False)

    th = {"A_firm_t": P.contracted_needed(up, cfg, segs["base"], "A_ORI_1", None, 0.5, firm_only=True),
          "A_firm_t_with_pipeline": P.contracted_needed(up, cfg, segs["base"], "A_ORI_1", None, 0.5, firm_only=False),
          "B_asia_t": P.contracted_needed(up, cfg, segs["base"], "B_ORI_TH_NOW", "A_ORI_1", 1.0, firm_only=False),
          "B_asia_t_price_1_4": P.contracted_needed(up, cfg, segs["base"], "B_ORI_TH_NOW", "A_ORI_1", 1.0, 1.4, firm_only=False)}
    fr = P.frontiers(up, cfg, segs["base"])
    lines = []
    for (cap, pm), g in fr.groupby(["capex_ori_musd", "price_mult"]):
        g = g.sort_values("asia_contracted_t")
        posB = g[g.delta_B_vs_A > 0]
        posT = g[g.delta_THalone_vs_A > 0]
        lines.append({"capex_ori_musd": cap, "price_mult": pm, "net_price_usd_kg_dha": g.net_price_usd_kg_dha.iloc[0],
                      "min_asia_contract_for_B_gt_A_t": posB.asia_contracted_t.min() if not posB.empty else None,
                      "min_asia_contract_for_THalone_gt_A_t": posT.asia_contracted_t.min() if not posT.empty else None,
                      "best_policy_at_zero_contract": g.iloc[0].best_policy})
    frl = pd.DataFrame(lines)
    fr.to_csv(out / "break_even_frontiers.csv", index=False)
    frl.to_csv(out / "break_even_frontier_lines.csv", index=False)
    pd.DataFrame([{"threshold": k, "value_t_per_year": v} for k, v in th.items()]).to_csv(out / "contract_thresholds.csv", index=False)

    stress = P.stress_tests(up, cfg, segs)
    stress.to_csv(out / "stress_tests.csv", index=False)

    keys = list(cfg["policies"])
    mc = P.joint_monte_carlo(up, cfg, n, cfg["seed"], True)
    mc.to_csv(proc / "joint_mc_draws.csv", index=False)
    mcs = P.mc_summary(mc, keys)
    mc0 = P.joint_monte_carlo(up, cfg, max(100, n // 3), cfg["seed"] + 1, False,
                              ["A_ORI_1", "A_ORI_2_STAGED", "B_ORI_TH_NOW", "C_ORI_TH_TRIG_UTIL", "D_ORI_HUB"])
    mcs0 = P.mc_summary(mc0, [k for k in mc0.columns if k in keys])
    mcs = mcs.merge(mcs0[["policy", "expected_npv_musd", "cvar10_musd"]].rename(
        columns={"expected_npv_musd": "expected_npv_independent", "cvar10_musd": "cvar10_independent"}), on="policy", how="left")
    mcs.to_csv(out / "monte_carlo_policy_summary.csv", index=False)
    corr = pd.DataFrame(P.joint_draws(up, 10, cfg["seed"]).attrs["corr"], index=P.VAR_ORDER, columns=P.VAR_ORDER)
    corr.to_csv(out / "joint_correlation_matrix.csv")

    reg = pd.read_csv(raw / "risk_dependency_register.csv")
    reg.to_csv(out / "risk_dependency_register.csv", index=False)
    series = ST.series_status(pd.read_csv(raw / "series_inventory.csv"))
    series.to_csv(out / "empirical_series_status.csv", index=False)

    voi = P.value_of_closing_gaps(up, cfg, segs)
    cat = pd.read_csv(raw / "diligence_catalog.csv").rename(columns={"parameter_key": "parameter"}).drop(columns=["effort"])
    dil = voi.merge(cat, on="parameter", how="left")
    dil.to_csv(out / "diligence_priority.csv", index=False)

    best_base = comp[comp.market_scenario == "base"].sort_values("npv_musd", ascending=False).iloc[0]
    option = pd.DataFrame([
        {"comparison": "Orindiúva agora vs adiar 2 anos (base)", "value_musd":
            comp.set_index(["market_scenario", "policy"]).npv_musd[("base", "A_ORI_1")]
            - comp.set_index(["market_scenario", "policy"]).npv_musd[("base", "A_ORI_DELAY")],
         "reading": "positivo = custo de esperar (vendas perdidas) > economia de adiar capex"},
        {"comparison": "Orindiúva agora vs adiar 2 anos (alto)", "value_musd":
            comp.set_index(["market_scenario", "policy"]).npv_musd[("high", "A_ORI_1")]
            - comp.set_index(["market_scenario", "policy"]).npv_musd[("high", "A_ORI_DELAY")], "reading": "idem"},
        {"comparison": "E[VPL] Tailândia por gatilho de utilização − Tailândia já (MC)", "value_musd":
            mcs.set_index("policy").expected_npv_musd["C_ORI_TH_TRIG_UTIL"] - mcs.set_index("policy").expected_npv_musd["B_ORI_TH_NOW"],
         "reading": "valor da opção de esperar pelo gatilho"},
        {"comparison": "E[VPL] 2º módulo Orindiúva por gatilho − fixo 2032 (MC)", "value_musd":
            mcs.set_index("policy").expected_npv_musd["A_ORI_2_STAGED"] - mcs.set_index("policy").expected_npv_musd["A_ORI_2_FIXED"],
         "reading": "valor do faseamento"},
        {"comparison": "E[VPL] melhor política MC − Esperar", "value_musd": mcs.expected_npv_musd.max(),
         "reading": f"melhor em média: {mcs.sort_values('expected_npv_musd').policy.iloc[-1]}"},
    ])
    option.to_csv(out / "option_value.csv", index=False)

    res = dict(cfg=cfg, up=up, prov=prov, segs=segs, rec=rec, routes=routes, inv=inv, comp=comp, flows=flows,
               alloc=alloc, compo=compo, th=th, fr=fr, frl=frl, stress=stress, mc=mc, mcs=mcs, reg=reg, series=series,
               dil=dil, option=option, out=out, best_base=best_base, p_base=p_base)
    if charts:
        make_outputs(res)
    from .reports import write_memo
    write_memo(res)
    return res


def make_outputs(r: dict) -> None:
    from . import charts as C
    from .cockpit import build
    up, cfg, out = r["up"], r["cfg"], r["out"]
    C.setup()
    C.route_heatmap(r["routes"], out / "origin_destination_heatmap.png")
    a = r["alloc"]
    C.sankey(a[(a.market_scenario == "high") & (a.policy == "B_ORI_TH_NOW") & (a.year == 2035)],
             out / "sankey_high_B_2035.png", "Mercado alto, política B (Orindiúva + Nakhon Sawan), 2035, t SKU")
    C.sankey(a[(a.market_scenario == "base") & (a.policy == "A_ORI_1") & (a.year == 2035)],
             out / "sankey_base_A_2035.png", "Mercado base, política A (Orindiúva 1 módulo), 2035, t SKU")
    C.frontier(r["fr"], 92 if 92 in r["fr"].capex_ori_musd.values else r["fr"].capex_ori_musd.median(),
               out / "npv_frontier_B_vs_A.png")
    C.decision_surface(r["fr"], out / "decision_surface_capex.png")
    C.npv_waterfall(r["comp"], out / "npv_waterfall_policies.png")
    C.portfolio_layers(r["compo"], a, r["flows"], out / "portfolio_vs_capacity.png")
    sites = pd.read_csv(up.v3_dir / "data" / "raw" / "site_candidates.csv")
    C.route_map(r["routes"], up.dm["feed"], sites, out / "route_map.png")
    ue = pd.read_csv(up.v3_dir / "outputs" / "unit_economics.csv")
    mkt = up.mm.market_table(up.cm, up.dm, r["segs"]["base"])
    C.concept_slides(out, ue, up.gates, mkt, r["comp"], r["th"], r["dil"])

    payload_p, demand, mix = {}, {}, {}
    for sc in cfg["market_scenarios"]:
        p, dem, _ = I.integrated_params(up, cfg, sc, r["segs"][sc])
        payload_p[sc] = p
        demand[sc] = dem.to_dict(orient="records")
        mix[sc] = up.v3d.region_mix(dem, p["regions"])
    g = up.gates
    gates = {s: {row.gate: {"status": row.status, "basis": row.basis} for row in grp.itertuples()} for s, grp in g.groupby("site_id")}
    cap = up.v3e.unit_capex(payload_p["base"], {"site": "BR_ORI_EXP"})["total"]
    hi_pipe = r["compo"]
    curves = pd.read_csv(up.mkt_dir / "outputs" / "market_demand_curves.csv") if (up.mkt_dir / "outputs" / "market_demand_curves.csv").exists() else None
    ct_bound = float(curves[(curves.scenario == "high") & (curves.year == 2030)].qualified_pipeline_t.sum()) if curves is not None else 20000.0
    payload = {"p": payload_p, "demand": demand, "mix": mix, "policies": cfg["policies"], "years": up.v3e.years(payload_p["base"]),
               "regions": payload_p["base"]["regions"], "contract_start": cfg["contract_start_year"],
               "capex_ori_base": cap, "fish_oil_base": payload_p["base"]["fish_oil_base"],
               "bounds": {"pm": [0.6, 1.6], "cx": [cap / 1e6 * 0.6, cap / 1e6 * 1.6], "ct": ct_bound},
               "fr": {"vols": [0, 2000, 4000, 6000, 8000, 10000, 14000, 20000], "pms": [0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8]},
               "p10": {row.policy: row.p10 for row in r["mcs"].itertuples()},
               "routes": r["routes"][r["routes"].year == 2030].to_dict(orient="records"),
               "gates": gates, "gate_names": sorted(g.gate.unique()),
               "app_label": {"salmon": "salmão", "shrimp": "camarão", "pet_food": "pet food", "shrimp/fish": "China aqua"},
               "demand_source": "market_expansion (estudo de mercado) via demand_for_v3; contratado = 0",
               "v3_version": up.c3["version"], "generated": r["prov"]["run_utc"][:10]}
    del hi_pipe
    build(out / "integrated_decision_cockpit.html", (up.v3_dir / "src" / "cockpit_engine.js").read_text(encoding="utf-8"),
          payload, cfg["contract_start_year"])
