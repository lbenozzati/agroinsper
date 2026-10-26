"""Public market ranking (25/25/25/15/10) per niche, split consolidation vs expansion, plus account table.

Country × niche cells are rebuilt from the market research of 2026-10-14 (data/raw/market_research) with each
value's status mapped from its own value_type, plus the account/competitor matrices of this revision.
Niches are ranked separately; the pooled list is a ranking of (country, niche) pairs under a declared objective
("pick the next country-niche pairs to work"), never an average of niche scores.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import yaml

from .. import market as M
from . import interval as I
from .common import CELL_COLS, DATA, OUT

PREF = {"salmon": "sal", "shrimp": "shr", "pet": "pet"}
GROWTH = {"salmon": "sal_growth_outlook_2030", "shrimp": "shr_growth_outlook", "pet": "pet_growth_5y_cagr"}
PLANTS = {"salmon": ("sal_feed_suppliers", 4), "shrimp": ("shr_feed_suppliers", 6), "pet": ("pet_manufacturers", 20)}
TARIFF = {"salmon": "sal_market_access_tariff", "shrimp": "shr_import_tariff", "pet": "pet_import_tariff"}
# biological / channel risk source per niche, mapped to 0-10 where 10 = worst
BIO = {"salmon": ("sal_mortality_pct", 5.0, 25.0, False), "shrimp": ("shr_disease_risk", 1.0, 5.0, False),
       "pet": ("pet_market_risk", 10.0, 0.0, True)}
# competitor algal supply documented in country × niche (competitor_product_matrix.csv); absence = UNKNOWN
COMPETITOR_DOCUMENTED = {("salmon", "Norway"): "Veramaris via Skretting (Lingalaks 2018) – R31",
                         ("salmon", "United States"): "Veramaris via Skretting (Atlantic Sapphire 2021) – R31",
                         ("salmon", "Canada"): "Veramaris em teste Cargill–Cermaq Canada – R31",
                         ("pet", "United States"): "dsm-firmenich Veramaris O3 Max Pure (abr/2026) – R21",
                         ("pet", "China"): "CABIO DHA algal para pet (catálogo) – R22"}
# China entra no salmão pela criação DOMÉSTICA (o salmão importado foi alimentado no país de origem e já está no
# TAM de Noruega/Chile). Produção doméstica de salmonídeos (faixa): ~47,5 kt de água fria (Qinghai 19 kt ≈ 40%, R46)
# + navios offshore (Su Hai No.1 > 8 kt previsto, R47) → 40–65 kt, base 50 kt; ração = produção × eFCR 1,3 (R39).
CN_SALMON_T = (40_000, 50_000, 65_000)
SALMONID_EFCR = 1.3
# SKU registration gate by (use, country) from product_regulatory_matrix.csv
EU = {"Germany", "France", "Italy", "Spain", "Poland"}


def market_gate(niche: str, country: str) -> tuple[str, str]:
    if country == "China":
        return "review", "G05: GACC anunciado (marca), números/SKU não vistos"
    if niche != "pet" and country in {"Norway", "United Kingdom"} | EU:
        return "review", "G06: categoria genérica UE ≠ registro do SKU"
    if niche == "shrimp" and country == "Thailand":
        return "review", "G09: uso histórico TFM; registro vigente não visto"
    if niche == "pet" and country in {"United States", "Canada"} | EU:
        return "review", "G10: canal IQI; registro/definição do SKU para pet não vistos"
    if country == "Brazil":
        return "unknown", "G11: registro MAPA não verificado"
    return "unknown", "Sem documento de registro do SKU para o uso"


def _status(vtype: str, source: str) -> str:
    s = str(source).lower()
    if "rubric" in s or "analyst" in s:
        return "JUDGMENT"
    return "OBSERVED" if str(vtype).lower() == "reported" else "DERIVED"


def build_cells(cfg: dict) -> pd.DataFrame:
    mc = M.load_config()
    data = M.load_inputs()
    acc = pd.read_csv(DATA / "customer_factory_matrix.csv")
    stage_score = cfg["market"]["evidence_stage_score"]
    rows = []

    def add(niche, country, metric, value, status, unit, source, notes, formula="", lo=np.nan, hi=np.nan,
            absence=""):
        rows.append({"metric_id": metric, "entity": f"{niche}|{country}", "entity_type": "country_niche",
                     "niche": niche, "sku": "AlgaPrime DHA", "value": value, "value_low": lo, "value_high": hi,
                     "unit": unit, "start_year": np.nan, "end_year": np.nan, "as_of_date": cfg["revision_date"],
                     "source_id": source, "page_or_table": "", "evidence_type": "", "status": status,
                     "absence_type": absence, "formula": formula,
                     "verification_level": "L3_prior_session" if source.startswith("R37") else "L2_search_digest",
                     "notes": notes})

    for niche in cfg["market"]["niches"]:
        d = M.derive(data, mc, niche)
        countries = mc["niches"][niche]["countries"]

        def get(c, m):
            r = d[(d.country == c) & (d.metric_id == m)]
            if r.empty or pd.isna(pd.to_numeric(r.raw_value.iloc[0], errors="coerce")):
                return None
            return r.iloc[0]

        for c in countries:
            r = get(c, "dha_need_t")
            if r is not None:
                add(niche, c, "dm_dha_tech_t", float(r.raw_value), "DERIVED", "t DHA/ano (TAM técnico)",
                    "R37;R39", str(r.source_name), formula=f"ração × {cfg['market']['dha_g_per_kg_feed'][niche]} "
                    "g DHA/kg (alvo EPA+DHA × fração DHA) / 1000; TAM técnico ≠ SAM ≠ SOM")
            else:
                add(niche, c, "dm_dha_tech_t", np.nan, "UNKNOWN", "t DHA/ano", "", "volume de ração ausente")
            for metric, src, unit in (("dm_growth", GROWTH[niche], "%/ano"),
                                      ("ac_feed_plants", PLANTS[niche][0], "nº"),
                                      ("ec_tariff_pct", TARIFF[niche], "%"),
                                      ("rk_fx_vol", "sr_fx_volatility", "%/ano"),
                                      ("ec_transit_days", f"{PREF[niche]}_transit_days", "dias")):
                r = get(c, src)
                if r is None:
                    add(niche, c, metric, np.nan, "UNKNOWN", unit, "", f"{src} ausente")
                else:
                    st = "DERIVED" if metric == "ec_transit_days" else _status(r.value_type, r.source_name)
                    add(niche, c, metric, float(r.raw_value), st, unit, "R37", f"{src}: {r.source_name}"[:240])
            src, good, bad, rubric = BIO[niche]
            r = get(c, src)
            if r is None:
                add(niche, c, "rk_bio", np.nan, "UNKNOWN", "0-10", "", f"{src} ausente")
            else:
                v = float(r.raw_value)
                risk = (v - good) / (bad - good) * 10 if not rubric else (10 - v)
                st = "JUDGMENT" if rubric or niche == "shrimp" else _status(r.value_type, r.source_name)
                add(niche, c, "rk_bio", round(float(np.clip(risk, 0, 10)), 2), st, "0-10 (10 = pior)", "R37",
                    f"{src}={v} ({r.source_name})"[:240], formula=f"({src} − {good})/({bad} − {good})×10"
                    if not rubric else "10 − rubrica")
            # proven commercial access: best evidence stage among identified accounts
            a = acc[(acc.country == c) & ((acc.niche == niche) | (acc.niche == "all"))]
            if a.empty:
                add(niche, c, "ac_evidence_stage", 0.0, "OBSERVED", "0-10", "", "Nenhuma conta com evidência pública "
                    "encontrada nesta revisão (ausência de prova = 0 por definição do critério)",
                    absence="no_public_evidence")
            else:
                best = a.assign(s=a.evidence_stage.map(stage_score).fillna(0)).sort_values("s").iloc[-1]
                add(niche, c, "ac_evidence_stage", float(best.s), "OBSERVED", "0-10", str(best.source_id),
                    f"{best.customer} / {best.plant}: {best.evidence_stage} ({best.evidence_date})")
            add(niche, c, "ec_net_price", np.nan, "UNKNOWN", "US$/kg DHA", "R29",
                "Preço líquido realizável por destino não é público (H1 2026: '€4.000-5.000 por unidade' agregado, "
                "unidade ambígua; 2027 em negociação)")
            add(niche, c, "fc_dha_fit", cfg["market"]["dha_fit"][niche], "DERIVED", "fração", "R39",
                "market_expansion/nutrition_requirements.csv (dha_share_of_target)",
                formula="fração DHA do alvo EPA+DHA da espécie (produto só-DHA não supre EPA)")
            comp = COMPETITOR_DOCUMENTED.get((niche, c))
            if comp:
                add(niche, c, "fc_competitor_documented", 1.0, "OBSERVED", "1 = sim", comp.split("– ")[-1], comp)
            else:
                add(niche, c, "fc_competitor_documented", np.nan, "UNKNOWN", "1 = sim", "",
                    "Não encontrado ≠ ausente: tratado como desconhecido (sem bônus por falta de dado)")
    # rubricas por componentes (canal e posição competitiva) com piso/teto; o registro segue como gate
    for niche in cfg["market"]["niches"]:
        td = {r["entity"].split("|")[1]: (np.nan, r["value"]) for r in rows
              if r["niche"] == niche and r["metric_id"] == "ec_transit_days" and pd.notna(r["value"])}
        rub = M.rubric_components(niche, td)
        for x in rub.itertuples():
            mid = {"canal": "ac_channel_rubric", "competicao": "fc_competitive_rubric"}.get(x.rubric)
            if mid:
                add(niche, x.country, mid, x.mid, "DERIVED", "0-10 (soma A-D)", "market_rubric_components.csv",
                    x.detail[:240], formula="soma dos componentes A-D; faixa = componentes não encontrados",
                    lo=x.lo, hi=x.hi)
    # salmão|China: dados brutos (p2b_salmon.csv) cobrem as métricas; o TAM técnico usa a faixa de produção
    rows = [r for r in rows if not (r["entity"] == "salmon|China" and r["metric_id"] == "dm_dha_tech_t")]
    g = cfg["market"]["dha_g_per_kg_feed"]["salmon"]
    lo, mid, hi = (x * SALMONID_EFCR * g / 1e3 for x in CN_SALMON_T)
    add("salmon", "China", "dm_dha_tech_t", round(mid, 1), "DERIVED", "t DHA/ano (TAM técnico)", "R46;R47;R39",
        "Só criação doméstica; importação (161 kt em 2025) excluída para não contar duas vezes",
        formula=f"produção doméstica {CN_SALMON_T} t × eFCR {SALMONID_EFCR} × {g} g DHA/kg / 1e3",
        lo=round(lo, 1), hi=round(hi, 1))
    out = pd.DataFrame(rows)
    return out[CELL_COLS]


def run(cfg: dict) -> dict:
    mk = cfg["market"]
    specs = I.specs_from(mk["metrics"])
    crit_w = {k: v["weight"] for k, v in mk["criteria"].items()}
    I.validate_specs(specs, mk["criteria"])
    cells = build_cells(cfg)
    per_niche, all_cs = {}, []
    for niche in mk["niches"]:
        sp = dict(specs)
        top = PLANTS[niche][1]
        sp["ac_feed_plants"] = I.Spec("ac_feed_plants", "acesso", specs["ac_feed_plants"].weight, 0, top, "linear",
                                      specs["ac_feed_plants"].label)
        cn = cells[cells.niche == niche]
        cs = I.cell_scores(cn, sp)
        t = I.aggregate(cs, sp, crit_w)
        t["niche"] = niche
        t["country"] = [e.split("|")[1] for e in t.index]
        stage = cn[cn.metric_id == "ac_evidence_stage"].set_index("entity").value.astype(float)
        t["evidence_stage"] = stage.reindex(t.index)
        t["role"] = np.where(t.evidence_stage >= 6, "consolidação", "expansão")
        g = [market_gate(niche, c) for c in t.country]
        t["sku_gate"] = [x[0] for x in g]
        t["sku_gate_note"] = [x[1] for x in g]
        dha = cn[cn.metric_id == "dm_dha_tech_t"].set_index("entity").value
        t["tam_tech_dha_t"] = pd.to_numeric(dha, errors="coerce").reindex(t.index)
        sets = {}
        for nm, w in mk["weight_sets"].items():
            sets[nm] = I.reweight(t, w)
        t["rank_consolidacao_set"] = sets["consolidacao"].rank_floor.reindex(t.index)
        t["rank_crescimento_set"] = sets["crescimento"].rank_floor.reindex(t.index)
        t["rank_atuais_mapeados"] = sets["atuais_mapeados"].rank_floor.reindex(t.index)
        t["rank_within_role"] = t.groupby("role").floor.rank(ascending=False, method="min").astype(int)
        per_niche[niche] = {"table": t, "cs": cs, "specs": sp, "sets": sets}
        all_cs.append(cs)
    pooled = pd.concat([v["table"] for v in per_niche.values()])
    pooled = I.rank_ranges(pooled.drop(columns=["rank_floor", "rank_best", "rank_worst"]))
    # robustness: ±25% per criterion, tipping points and single-document flips for the named pairs
    pert, tips, flips = [], [], []
    for niche, v in per_niche.items():
        t = v["table"]
        for c in crit_w:
            for rel in (-0.25, 0.25):
                tt = I.reweight(t, I.perturb(crit_w, c, rel))
                for e, r in tt.iterrows():
                    pert.append({"niche": niche, "criterion": c, "relative_change": rel, "entity": e,
                                 "floor": r.floor, "rank_floor": r.rank_floor, "rank_best": r.rank_best,
                                 "rank_worst": r.rank_worst})
    for n1, c1, n2, c2 in mk["pairs_to_test"]:
        assert n1 == n2
        t, cs, sp = per_niche[n1]["table"], per_niche[n1]["cs"], per_niche[n1]["specs"]
        e1, e2 = f"{n1}|{c1}", f"{n2}|{c2}"
        a, b = (e1, e2) if t.at[e1, "floor"] >= t.at[e2, "floor"] else (e2, e1)
        for c in crit_w:
            for col in ("floor", "ceiling"):
                tips.append({"niche": n1, "leader_on_floor": a, "challenger": b, "criterion": c, "basis": col,
                             "current_weight": crit_w[c], "tipping_weight": I.tipping(t, crit_w, a, b, c, col)})
        flips.append(I.single_document_flip(cs, sp, crit_w, a, b).assign(niche=n1))
    # correlation of criterion floors across all country-niche pairs; leave-one-criterion-out ranks
    corr = pooled[[f"{c}_floor" for c in crit_w]].astype(float).corr()
    loo = []
    for niche, v in per_niche.items():
        for c in crit_w:
            w = {k: (0.0 if k == c else x / (1 - crit_w[c])) for k, x in crit_w.items()}
            tt = I.reweight(v["table"], w)
            for e, r in tt.iterrows():
                loo.append({"niche": niche, "without": c, "entity": e, "rank_floor": r.rank_floor})
    accounts = account_table(cfg)
    goal = []
    for niche, v in per_niche.items():
        for k, s in v["specs"].items():
            goal.append({"ranking": "market", "niche": niche, "metric_id": k, "criterion": s.criterion,
                         "weight_in_criterion": s.weight, "abs_weight": s.weight * crit_w[s.criterion],
                         "worst": s.worst, "best": s.best, "scale": s.scale, "label": s.label, "component_of": ""})
    cs_all = pd.concat(all_cs, ignore_index=True)
    evidence = cells.merge(cs_all[["entity", "metric_id", "score_mid", "score_lo", "score_hi"]],
                           on=["entity", "metric_id"], how="left")
    return {"niches": per_niche, "pooled": pooled, "cells": cells, "evidence": evidence, "crit_w": crit_w,
            "perturbation": pd.DataFrame(pert), "tipping": pd.DataFrame(tips),
            "flips": pd.concat(flips, ignore_index=True), "correlation": corr, "leave_one_out": pd.DataFrame(loo),
            "accounts": accounts, "goalposts": pd.DataFrame(goal)}


def account_table(cfg: dict) -> pd.DataFrame:
    """Account × plant evidence table (no composite score): stage first, then technical DHA potential."""
    acc = pd.read_csv(DATA / "customer_factory_matrix.csv")
    g = cfg["market"]["dha_g_per_kg_feed"]
    st = cfg["market"]["evidence_stage_score"]
    acc["evidence_score"] = acc.evidence_stage.map(st)
    acc["tech_dha_potential_t"] = [
        (r.feed_capacity_t * g.get(r.niche, np.nan) / 1000) if pd.notna(r.feed_capacity_t) and r.niche in g else np.nan
        for r in acc.itertuples()]
    acc["sku_gate"] = [market_gate(r.niche, r.country)[0] if r.niche in g else "n/a" for r in acc.itertuples()]
    acc["note"] = ("Potencial técnico = capacidade de ração × g DHA/kg; NÃO é volume comprado nem SOM. "
                   "Capacidade nominal de ração (prospecto) ≠ produção.")
    return acc.sort_values(["evidence_score", "tech_dha_potential_t"], ascending=False)


def write(res: dict) -> None:
    o = OUT
    for niche, v in res["niches"].items():
        t = v["table"].copy()
        t.index.name = "entity"
        t.round(3).to_csv(o / f"market_public_scores_{niche}.csv")
    p = res["pooled"].copy()
    p.index.name = "entity"
    p.round(3).to_csv(o / "market_public_scores_pooled_pairs.csv")
    res["evidence"].to_csv(o / "market_evidence.csv", index=False)
    res["perturbation"].round(3).to_csv(o / "market_weight_perturbation_pm25.csv", index=False)
    res["tipping"].to_csv(o / "market_tipping_points.csv", index=False)
    res["flips"].to_csv(o / "market_single_document_flips.csv", index=False)
    res["correlation"].round(3).to_csv(o / "market_criterion_correlation.csv")
    res["leave_one_out"].to_csv(o / "market_leave_one_criterion_out.csv", index=False)
    res["accounts"].round(1).to_csv(o / "customer_factory_matrix.csv", index=False)
