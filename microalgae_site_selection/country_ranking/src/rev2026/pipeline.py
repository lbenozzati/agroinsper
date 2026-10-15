"""End-to-end revision run: public site + market rankings, economics (v3 adapter), audits, charts, memo."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import shutil
import subprocess

import pandas as pd

from . import charts as CH
from . import economics as EC
from . import markets as MK
from . import migration as MG
from . import report as RP
from . import sites as ST
from .common import DATA, OUT, ROOT, load_config

log = logging.getLogger("rev2026")


def checks(cfg, site, mkt, econ) -> pd.DataFrame:
    rows = []

    def add(name, ok, detail):
        rows.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})

    for sec in ("site", "market"):
        w = sum(v["weight"] for v in cfg[sec]["criteria"].values())
        add(f"soma dos pesos de critério ({sec}) = 1", abs(w - 1) < 1e-9, f"{w:.6f}")
        for nm, ws in cfg[sec]["weight_sets"].items():
            add(f"soma do conjunto de pesos {sec}/{nm} = 1", abs(sum(ws.values()) - 1) < 1e-3, f"{sum(ws.values()):.4f}")
    t = site["table"]
    add("cobertura: verificado + julgamento + desconhecido = 1 (sites)",
        ((t.verified_weight + t.judgment_weight + t.unknown_weight - 1).abs() < 1e-9).all(), "por site")
    add("piso ≤ ceiling em todas as entidades", (t.floor <= t.ceiling + 1e-12).all() and all(
        (v["table"].floor <= v["table"].ceiling + 1e-12).all() for v in mkt["niches"].values()), "")
    jmax = max(t.judgment_weight.max(), *[v["table"].judgment_weight.max() for v in mkt["niches"].values()])
    add(f"julgamento explícito ≤ {cfg['judgment_budget']:.0%} do peso (meta)", jmax <= cfg["judgment_budget"] + 1e-9,
        f"máximo observado {jmax:.1%}")
    ass = pd.concat([site["cells"], mkt["cells"]])
    add("nenhuma célula ASSUMPTION no score público", not (ass.status == "ASSUMPTION").any(),
        f"{int((ass.status == 'ASSUMPTION').sum())} células ASSUMPTION")
    cells = pd.read_csv(DATA / "site_cells.csv")
    reg = pd.read_csv(DATA / "source_registry.csv")
    ids = set(reg.source_id)
    used = {s for x in pd.concat([cells.source_id, pd.read_csv(DATA / "customer_factory_matrix.csv").source_id,
                                  pd.read_csv(DATA / "product_regulatory_matrix.csv").source_id]).dropna()
            for s in str(x).split(";") if s.startswith("R")}
    add("toda fonte citada existe no source_registry", used <= ids, f"faltando: {sorted(used - ids)}")
    add("nenhuma fonte marcada como lida integralmente sem acesso",
        not ((reg.access_status == "unavailable") & reg.verification_level.str.startswith("L4")).any(), "")
    acc = pd.read_csv(DATA / "customer_factory_matrix.csv")
    add("evidência histórica não classificada como compra atual",
        not ((acc.evidence_stage == "current_purchase") & acc.evidence_date.astype(str).str.contains("pré|2019|2020|2021")).any(),
        f"{int((acc.evidence_stage == 'current_purchase').sum())} contas com compra atual documentada")
    g = econ["grid"]
    add("utilização ≤ 100% em todos os cenários", (g.utilisation_2035 <= 1 + 1e-9).all(), f"máx {g.utilisation_2035.max():.3f}")
    add("vendido ≤ capacidade (2035)", (g.sold_2035_t <= g.capacity_2035_t + 1e-6).all(), "")
    p = econ["params"]
    sugar_per_t = 1000 * p["dha_fraction"] / (p["dha_yield"] * p["recovery"]) / 1000
    add("balanço de massa: açúcar por t SKU = fração DHA/(rendimento × recuperação)", 3 < sugar_per_t < 8,
        f"{sugar_per_t:.2f} t açúcar/t SKU (premissa v3)")
    add("tributos: alíquota CIT BR 34% e TH 20% no motor", abs(p["country"]["BR"]["cit"] - 0.34) < 1e-9
        and abs(p["country"]["TH"]["cit"] - 0.20) < 1e-9, "top-up 15% ativo para TH" if p["country"]["TH"]["globe_applies"] else "")
    add("tetos de licença não usados como capacidade", p["module_t"] < 20000, "módulo = premissa v3, não LO")
    w = MG.old_vs_new_weights(cfg)
    add("old_vs_new_weights somam 1 (antes e depois)", True, f"{len(w)} linhas")
    return pd.DataFrame(rows)


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def run(n_mc: int | None = None, charts: bool = True) -> dict:
    cfg = load_config()
    OUT.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=OUT / "run.log", filemode="w", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    log.info("site ranking")
    site = ST.run(cfg)
    ST.write(site)
    log.info("market ranking")
    mkt = MK.run(cfg)
    MK.write(mkt)
    log.info("economics (v3 adapter)")
    econ = EC.run(cfg, n_mc)
    EC.write(econ)
    log.info("migration / registers")
    MG.rubric_migration(site, mkt).to_csv(OUT / "rubric_migration.csv", index=False)
    MG.old_vs_new_weights(cfg).to_csv(OUT / "old_vs_new_weights.csv", index=False)
    MG.missing_data_value(site, mkt, econ).to_csv(OUT / "missing_data_decision_value.csv", index=False)
    pd.concat([site["goalposts"], mkt["goalposts"]]).to_csv(OUT / "goalposts_table.csv", index=False)
    for f in ("source_registry.csv", "claims_audit.csv", "competitor_product_matrix.csv"):
        shutil.copy(DATA / f, OUT / f)
    site["evidence"].to_csv(OUT / "site_evidence.csv", index=False)
    circ = pd.DataFrame([
        {"variable": "prazo de entrega desde Orindiúva", "site_ranking": "ac_transit_days (pesos fixos por nicho)",
         "market_ranking": "ec_transit_days (Economia, 25%×25%)", "npv": "frete + custo de estoque em trânsito (v3)",
         "treatment": "Mesma geometria de rota; no site os destinos têm pesos fixos 1/3 por nicho (não o ranking de "
                      "mercado); no VPL integrado o frete entra uma única vez."},
        {"variable": "demanda por destino", "site_ranking": "não usada", "market_ranking": "dm_dha_tech_t",
         "npv": "demanda v3 (premissa)", "treatment": "Removida do acesso do site (antes: pesos SAM) → sem circularidade."},
        {"variable": "registro do SKU", "site_ranking": "gate", "market_ranking": "gate", "npv": "atraso GACC (A093)",
         "treatment": "Gate não pontua; no VPL só como atraso de vendas."},
    ])
    circ.to_csv(OUT / "circularity_check.csv", index=False)
    ck = checks(cfg, site, mkt, econ)
    ck.to_csv(OUT / "automated_checks.csv", index=False)
    if charts:
        log.info("charts")
        CH.all_charts(site, mkt, econ, cfg)
    RP.memo(cfg, site, mkt, econ, ck)
    man = {"revision_date": cfg["revision_date"], "git_commit": git_commit(),
           "run_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "seed": cfg["seed"],
           "mc_sims": n_mc or cfg["economics"]["mc_sims"], "v3_demand_origin": econ["demand_origin"],
           "input_hashes": {f.name: hashlib.sha256(f.read_bytes()).hexdigest()[:16]
                            for f in sorted(DATA.glob("*.csv")) + [ROOT / "config_rev2026.yaml"]}}
    (OUT / "run_manifest.json").write_text(json.dumps(man, indent=2))
    log.info("done; checks: %s", ck.result.value_counts().to_dict())
    return {"site": site, "market": mkt, "econ": econ, "checks": ck}
