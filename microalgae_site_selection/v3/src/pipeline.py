"""End-to-end v3 run: audit inputs, screening, site economics, Monte Carlo, frontier, charts, cockpit, memo."""

from __future__ import annotations

import datetime as dt
import json
import logging
import subprocess
from pathlib import Path

import pandas as pd

from . import analysis as A
from . import data as D
from . import engine as E
from . import screening as S

ROOT = D.ROOT


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def run(out_dir: Path | None = None, mc_sims: int | None = None, charts: bool = True, cockpit: bool = True,
        reports: bool = True) -> dict:
    logging.getLogger("microalgae_site_selection").setLevel(logging.ERROR)
    cfg = D.load_config()
    out = Path(out_dir or ROOT / cfg["paths"]["outputs"])
    out.mkdir(parents=True, exist_ok=True)
    proc = ROOT / cfg["paths"]["processed"]
    proc.mkdir(parents=True, exist_ok=True)
    n = mc_sims or cfg["mc_sims"]

    ev = D.load_evidence(cfg)
    a = D.load_assumptions(cfg)
    fr = D.load_freight(cfg)
    sites = D.load_sites(cfg)
    gates = D.load_gates(cfg)
    demand, origin = D.load_demand(cfg, a)
    p0 = D.build_params(cfg, a, fr)
    p = A.params_for(cfg, p0, demand, "base")

    raw = ROOT / cfg["paths"]["raw"]
    manifest = {"version": cfg["version"], "cutoff_date": cfg["cutoff_date"], "seed": cfg["seed"],
                "git_commit": git_commit(), "run_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "mc_sims": n, "demand_origin": origin,
                "input_hashes": {f.name: D.file_hash(f) for f in sorted(raw.rglob("*.csv"))}}
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2))
    (proc / "params_base.json").write_text(json.dumps(p, indent=1))

    ev.to_csv(out / "evidence_registry.csv", index=False)
    a.to_csv(out / "assumptions.csv", index=False)
    site_gate = gates.pivot(index="site_id", columns="gate", values="status")
    site_gate["gate_summary"] = site_gate.apply(
        lambda r: "FAIL" if (r == "FAIL").any() else ("CONDITIONAL" if ((r == "REVIEW") | (r == "NOT_VERIFIED")).any()
                                                      else "PASS"), axis=1)
    sites.merge(site_gate.reset_index(), on="site_id").to_csv(out / "site_candidates.csv", index=False)
    gates.to_csv(out / "site_gates.csv", index=False)

    repro = S.reproduce_v2()
    repro.to_csv(out / "baseline_v2_reproduction.csv")
    ranking, extra = S.ranking_v3(cfg)
    ranking.to_csv(out / "ranking_v3_screening.csv", index=False)
    extra["criterion_correlation"].to_csv(out / "criterion_correlation.csv")
    extra["bounds_robustness"].to_csv(out / "goalpost_robustness.csv", index=False)

    ue = A.unit_economics(cfg, p)
    ue["msp_usd_per_kg_dha_A1_like"] = None
    for s_id, alt_key in (("BR_ORI_EXP", "A1_ORI"), ("BR_GF_GO", "B_BR_GF"), ("TH_NSN", "C_TH_NSN"),
                          ("TH_RYG", "D_TH_RYG")):
        ue.loc[ue.site_id == s_id, "msp_usd_per_kg_dha_A1_like"] = E.msp(p, cfg["alternatives"][alt_key])
    ue = ue.rename(columns={"msp_usd_per_kg_dha_A1_like": "msp_usd_per_kg_dha_base_demand"})
    ue.to_csv(out / "unit_economics.csv", index=False)
    A.implied_capacity_of_eur50m(p, D.assumption(a, "eurusd")).to_csv(out / "eur50m_implied_capacity_sensitivity.csv",
                                                                         index=False)

    summ, flows = A.scenario_table(cfg, p0, demand)
    for sc in cfg["scenarios"]:
        q = A.params_for(cfg, p0, demand, sc)
        for key in cfg["alternatives"]:
            mask = (summ.scenario == sc) & (summ.alternative == key)
            summ.loc[mask, "msp_usd_per_kg_dha"] = E.msp(q, cfg["alternatives"][key])
            m = E.breakeven_demand_multiplier(q, cfg["alternatives"][key])
            summ.loc[mask, "breakeven_demand_multiplier"] = m
    flows.to_csv(out / "cashflow_by_scenario.csv", index=False)
    summ.to_csv(out / "npv_by_scenario.csv", index=False)

    t_a1 = A.tornado(cfg, p, a, lambda q: E.run_alternative(q, cfg["alternatives"]["A1_ORI"])["npv"] / 1e6)
    t_d = A.tornado(cfg, p, a, lambda q: (E.run_alternative(q, cfg["alternatives"]["C_TH_NSN"])["npv"]
                                          - E.run_alternative(q, cfg["alternatives"]["A1_ORI"])["npv"]) / 1e6)
    t_a1.to_csv(out / "tornado_npv_A1.csv", index=False)
    t_d.to_csv(out / "tornado_delta_C_vs_A1.csv", index=False)

    frontier = A.decision_frontier(cfg, p0, demand)
    frontier.to_csv(out / "decision_frontier.csv", index=False)

    mc = A.run_monte_carlo(cfg, p, n, cfg["seed"], correlated=True)
    mc0 = A.run_monte_carlo(cfg, p, n, cfg["seed"], correlated=False)
    alts = list(cfg["alternatives"])
    mcs = A.mc_summary(mc, alts)
    mcs0 = A.mc_summary(mc0, alts).add_suffix("_nocorr").rename(columns={"alternative_nocorr": "alternative"})
    mcs = mcs.merge(mcs0[["alternative", "mean_npv_musd_nocorr", "p10_nocorr", "prob_best_conditional_nocorr"]],
                    on="alternative")
    mc.to_csv(proc / "monte_carlo_draws.csv", index=False)
    mcs.to_csv(out / "monte_carlo_summary.csv", index=False)
    names, corr = A.correlation_matrix(cfg)
    pd.DataFrame(corr, index=names, columns=names).to_csv(out / "mc_correlation_matrix.csv")
    trig = {k: float(mc[f"{k}_triggered"].mean()) for k in ("F_ORI_THEN_TH", "A2_ORI_STAGED")}

    res_stress = A.resilience_stress(cfg, p0, demand)
    res_stress.to_csv(out / "resilience_stress.csv", index=False)

    base_sum = summ[summ.scenario == "base"].set_index("alternative")
    site_alt = {"BR_ORI_EXP": "A1_ORI", "BR_GF_GO": "B_BR_GF", "TH_NSN": "C_TH_NSN", "TH_RYG": "D_TH_RYG"}
    npv_rank = pd.DataFrame([{"site_id": s, "alternative": k, "npv_base_musd": base_sum.loc[k, "npv_musd"],
                              "npv_mc_mean_musd": mcs.set_index("alternative").loc[k, "mean_npv_musd"],
                              "gate_summary": site_gate.loc[s, "gate_summary"]} for s, k in site_alt.items()])
    npv_rank["rank_by_npv_base"] = npv_rank["npv_base_musd"].rank(ascending=False).astype(int)
    country_rank = npv_rank.assign(country=npv_rank.site_id.str[:2].map({"BR": "Brazil", "TH": "Thailand"}))
    best_site = country_rank.sort_values("npv_base_musd", ascending=False).drop_duplicates("country")
    rank_v3 = ranking.merge(best_site[["country", "site_id", "npv_base_musd", "rank_by_npv_base", "gate_summary"]],
                            on="country", how="left")
    rank_v3.to_csv(out / "ranking_v3.csv", index=False)
    npv_rank.to_csv(out / "site_npv_ranking.csv", index=False)

    src_gaps = source_gaps(ev, a, gates, t_a1, t_d)
    src_gaps.to_csv(out / "source_gaps.csv", index=False)

    results = dict(cfg=cfg, p=p, p0=p0, a=a, ev=ev, demand=demand, origin=origin, ue=ue, summ=summ, flows=flows,
                   t_a1=t_a1, t_d=t_d, frontier=frontier, mc=mc, mcs=mcs, trig=trig, ranking=ranking, extra=extra,
                   repro=repro, gates=gates, site_gate=site_gate, sites=sites, res_stress=res_stress,
                   npv_rank=npv_rank, src_gaps=src_gaps, manifest=manifest, out=out)
    if charts:
        make_charts(results)
    if cockpit:
        from .cockpit import build_cockpit
        cap = E.unit_capex(p, {"site": "BR_ORI_EXP"})["total"]
        build_cockpit(out / "decision_cockpit.html", p0, cfg, demand, origin, manifest["run_utc"][:10], cap,
                      (D.assumption(a, "net_price_usd_per_kg_dha", which="low"),
                       D.assumption(a, "net_price_usd_per_kg_dha", which="high")))
    if reports:
        from . import reports as R
        R.write_audit(results)
        R.write_memo(results)
    return results


def source_gaps(ev, a, gates, t_a1, t_d) -> pd.DataFrame:
    rows = []
    for _, r in ev[ev.access_status.isin(["unavailable", "search_snippet", "user_supplied"])].iterrows():
        rows.append({"type": "evidence", "id": r.source_id, "item": r.definition, "status": r.access_status,
                     "why_it_matters": r.notes, "next_step": f"Open original: {r.url}"})
    for _, r in gates[gates.status.isin(["NOT_VERIFIED", "REVIEW"])].iterrows():
        rows.append({"type": "site_gate", "id": f"{r.site_id}:{r.gate}", "item": r.gate, "status": r.status,
                     "why_it_matters": r.basis, "next_step": "Site diligence / authority consultation"})
    top = set(t_a1.head(6)["parameter"]) | set(t_d.head(6)["parameter"])
    for k in sorted(top):
        rows.append({"type": "decision_driver", "id": k, "item": k, "status": "assumption-driven",
                     "why_it_matters": "Top-6 swing in tornado (NPV A1 or C-A1)",
                     "next_step": "Replace with Corbion data / EPC quote / contract terms"})
    return pd.DataFrame(rows)


def make_charts(r: dict) -> None:
    from . import charts as C
    C.setup()
    out = r["out"]
    labels = {k: v["label"] for k, v in r["cfg"]["alternatives"].items()}
    C.cost_waterfall(r["ue"], out / "cost_per_kg_dha_waterfall.png")
    C.tornado_chart(r["t_a1"], r["t_d"], out / "tornado.png")
    mid = sorted(r["cfg"]["frontier"]["capex_ori_musd"])[1]
    C.frontier_chart(r["frontier"], mid, out / "decision_frontier.png")
    C.risk_return(r["mcs"], labels, out / "risk_return_matrix.png")
    C.npv_ranges(r["mcs"], labels, out / "npv_ranges.png")
    C.site_map(r["ranking"], r["sites"], out / "site_map.png")
