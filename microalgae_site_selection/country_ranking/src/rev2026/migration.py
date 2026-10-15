"""Line-by-line migration of the old rubrics, old-vs-new weights and the decision value of missing data."""

from __future__ import annotations

import pandas as pd

from .common import FROZEN

# old rubric metric -> (decision, new_metric, unit, formula, scope, reason)
PLANT_MAP = {
    "pe_steam_biomass_cogeneration": ("movida ao VPL", "v3 A083 steam_usd_per_t + rs_supply_contract",
                                      "US$/t vapor; 0/1", "custo de vapor no opex do DCF; contrato documentado em "
                                      "Resiliência", "site",
                                      "Vapor da usina entra uma única vez (custo no VPL); nota 0-10 de MW de "
                                      "cogeração não mede custo nem disponibilidade contratada."),
    "pe_industrial_water_wastewater_infra": ("substituída por medida observada",
                                             "rs_basin_water_stress; rs_water_grant_incremental",
                                             "Aqueduct 0-4; 0/1", "categoria Aqueduct na coordenada / outorga",
                                             "site", "Nota 'v2' sem documento → estresse local observado e "
                                             "outorga (desconhecida = intervalo)."),
    "pe_construction_epc_capability": ("movida ao VPL", "v3 A030/A087/A092 (contingência, fator local, prazo)",
                                       "fração; anos", "capex × (1+contingência) × fator local", "site",
                                       "Capacidade de EPC afeta custo e prazo do projeto → fluxo de caixa, não nota."),
    "ma_biomar_customer_proximity": ("removida por dupla contagem", "ac_transit_days", "dias",
                                     "Σ peso fixo × dias porta a porta", "site",
                                     "Proximidade já está no prazo de entrega; nota atribuía contrato por "
                                     "proximidade."),
    "cr_existing_manufacturing": ("substituída por medida observada", "ex_dha_asset_operating", "0/1",
                                  "1 se o site opera DHA de algas", "site",
                                  "Fábrica de ácido láctico ≠ capacidade de DHA (Rayong = 0 documentado)."),
    "cr_fermentation_talent": ("substituída por medida observada", "ex_corbion_staff_on_site", "FTE",
                               "headcount Corbion no site", "site", "Nota 'v2' → equipe documentada no site."),
    "cr_commercial_innovation_presence": ("removida por dupla contagem", "market:ac_evidence_stage", "0-10",
                                          "estágio de evidência por conta", "país×nicho",
                                          "Presença comercial pertence ao ranking de mercado (acesso comprovado)."),
    "ri_local_production_permitting": ("movida para gate", "product_regulatory_matrix G01-G20", "pass/review/"
                                       "unknown/fail", "gate não compensatório", "site×cepa×SKU×uso×mercado",
                                       "Licença não compensa outros critérios; 'licenciado e operando' com "
                                       "validade impressa 02/09/2026 = review."),
    "ri_investment_incentives": ("movida ao VPL", "v3 A073/A074/A075 (BOI, top-up 15%, QRTC)", "anos; 0/1; "
                                 "fração", "benefício efetivamente concedido no fluxo de caixa", "site",
                                 "Incentivo potencial não recebe pontos; nenhum certificado BOI para DHA."),
    "ri_trade_fdi_access": ("substituída por medida observada", "ac_fta_share", "fração",
                            "Σ peso destino × acordo em vigor", "site", "Nota 'v2' → lista de acordos vigentes."),
    "sr_local_competition_overcapacity": ("substituída por medida observada",
                                          "market:fc_competitor_documented + competitor_product_matrix",
                                          "1 = concorrente documentado", "fornecedor capaz por país×nicho",
                                          "país×nicho", "Nota 10 por 'único produtor local' removida: "
                                          "concorrência é global e por cliente."),
}
MARKET_MAP = {
    "sal_relationship": ("substituída por medida observada", "ac_evidence_stage", "0-10",
                         "máx. estágio de evidência entre contas identificadas", "país×nicho×conta",
                         "Histórico ≠ atual; relação global ≠ adoção por fábrica."),
    "shr_relationship": ("substituída por medida observada", "ac_evidence_stage", "0-10", "idem",
                         "país×nicho×conta", "idem"),
    "pet_relationship": ("substituída por medida observada", "ac_evidence_stage", "0-10", "idem",
                         "país×nicho×conta", "Canal (IQI) ≠ receita futura."),
    "sal_registration": ("movida para gate", "sku_gate (G05-G11)", "pass/review/unknown/fail",
                         "registro do SKU para o uso e país", "país×uso×SKU",
                         "Categoria genérica ≠ registro da formulação."),
    "pet_market_risk": ("permanece julgamento explícito", "rk_bio (pet)", "0-10", "10 − rubrica",
                        "país×nicho", "Sem série pública de recall/canal comparável; peso 5% do total."),
}
NEW_ABS = {  # new absolute weight of the destination metric (proposed weights)
    "rs_basin_water_stress; rs_water_grant_incremental": 0.15 * (0.35 + 0.25),
    "ac_transit_days": 0.25 * 0.30, "ex_dha_asset_operating": 0.15 * 0.40, "ex_corbion_staff_on_site": 0.15 * 0.25,
    "ac_fta_share": 0.25 * 0.20, "ac_evidence_stage": 0.25 * 0.70, "rk_bio (pet)": 0.10 * 0.50,
    "market:fc_competitor_documented + competitor_product_matrix": 0.15 * 0.50,
    "market:ac_evidence_stage": 0.25 * 0.70,
}


def rubric_migration(site_res: dict, market_res: dict) -> pd.DataFrame:
    rows = []
    old_rank = pd.read_csv(FROZEN / "plant" / "plant_country_ranking.csv").set_index("country")["rank"]
    pms = pd.read_csv(FROZEN / "plant" / "plant_metric_scores.csv")
    pw = pms.drop_duplicates("metric_id").set_index("metric_id").nominal_weight
    tpl = pd.read_csv(FROZEN / "plant" / "plant_rubric_ratings_template.csv")
    for r in tpl.itertuples():
        d = PLANT_MAP[r.metric_id]
        ow = float(pw.get(r.metric_id, float("nan")))
        rows.append({"ranking": "planta/site", "entity": r.country, "old_metric": r.metric_id, "old_weight": ow,
                     "old_value": r.analyst_score, "claimed_evidence": r.notes, "new_metric": d[1],
                     "new_weight": NEW_ABS.get(d[1], 0.0), "measurement_unit": d[2], "formula": d[3],
                     "geographic_scope": d[4], "sku_or_species": "AlgaPrime DHA",
                     "source_id": "ver site_evidence.csv / product_regulatory_matrix.csv",
                     "evidence_date": "2026-10-15", "status": d[0], "reason": d[5],
                     "rank_impact": f"contribuía {ow * float(r.analyst_score):.2f} ponto(s) ao score de {r.country} "
                                    f"(rank antigo {int(old_rank.get(r.country, 0))}); no ranking novo: "
                                    + ("sai do score" if d[0] in ("movida ao VPL", "movida para gate",
                                                                  "removida por dupla contagem") else
                                       "substituída por métrica documentada ou intervalo")})
    mms = pd.read_csv(FROZEN / "market" / "market_metric_scores.csv")
    mw = mms.drop_duplicates(["niche", "metric_id"]).set_index(["niche", "metric_id"]).nominal_weight
    mtpl = pd.read_csv(FROZEN / "market" / "market_rubric_ratings_template.csv")
    for r in mtpl.itertuples():
        d = MARKET_MAP[r.metric_id]
        ow = float(mw.get((r.niche, r.metric_id), float("nan")))
        ent = f"{r.niche}|{r.country}"
        new_rank = ""
        if r.niche in market_res["niches"] and ent in market_res["niches"][r.niche]["table"].index:
            tt = market_res["niches"][r.niche]["table"]
            new_rank = f"; rank novo (piso) {int(tt.at[ent, 'rank_floor'])}, faixa {int(tt.at[ent, 'rank_best'])}" \
                       f"–{int(tt.at[ent, 'rank_worst'])}"
        rows.append({"ranking": f"mercado/{r.niche}", "entity": r.country, "old_metric": r.metric_id,
                     "old_weight": ow, "old_value": r.score, "claimed_evidence": r.notes, "new_metric": d[1],
                     "new_weight": NEW_ABS.get(d[1], 0.0), "measurement_unit": d[2], "formula": d[3],
                     "geographic_scope": d[4], "sku_or_species": r.niche,
                     "source_id": "ver market_evidence.csv / customer_factory_matrix.csv",
                     "evidence_date": "2026-10-15", "status": d[0], "reason": d[5],
                     "rank_impact": f"contribuía {ow * float(r.score):.2f} ponto(s){new_rank}"})
    return pd.DataFrame(rows)


def old_vs_new_weights(cfg: dict) -> pd.DataFrame:
    rows = []
    old_site = {"production_economics": 0.30, "market_access": 0.20, "corbion_readiness": 0.15,
                "regulation_incentives": 0.15, "strategic_risk": 0.20}
    map_site = {"production_economics": "economia", "market_access": "acesso", "corbion_readiness": "execucao",
                "regulation_incentives": "(gate + fluxo de caixa)", "strategic_risk": "resiliencia (+ concorrência → "
                "ranking de mercado)"}
    new_site = {k: v["weight"] for k, v in cfg["site"]["criteria"].items()}
    for k, w in old_site.items():
        nk = map_site[k]
        rows.append({"ranking": "planta/site", "old_criterion": k, "old_weight": w, "new_criterion": nk,
                     "new_weight": new_site.get(nk.split(" ")[0], 0.0), "change_date": cfg["revision_date"],
                     "reason": cfg["weights_change_reason"]})
    rows.append({"ranking": "planta/site", "old_criterion": "(novo)", "old_weight": 0.0, "new_criterion": "opcao",
                 "new_weight": new_site["opcao"], "change_date": cfg["revision_date"],
                 "reason": "Opção de 2º módulo/produto documentada (astaxantina não conta como capacidade)."})
    old_m = {"size_growth": 0.30, "value": 0.20, "access": 0.20, "regulatory": 0.15, "risk": 0.15}
    map_m = {"size_growth": "demanda", "value": "economia", "access": "acesso", "regulatory": "(gate de registro do SKU)",
             "risk": "risco"}
    new_m = {k: v["weight"] for k, v in cfg["market"]["criteria"].items()}
    for k, w in old_m.items():
        nk = map_m[k]
        rows.append({"ranking": "mercado", "old_criterion": k, "old_weight": w, "new_criterion": nk,
                     "new_weight": new_m.get(nk, 0.0), "change_date": cfg["revision_date"],
                     "reason": cfg["weights_change_reason"]})
    rows.append({"ranking": "mercado", "old_criterion": "(novo)", "old_weight": 0.0, "new_criterion": "adequacao",
                 "new_weight": new_m["adequacao"], "change_date": cfg["revision_date"],
                 "reason": "Adequação DHA/EPA e concorrência documentada por país×nicho."})
    t = pd.DataFrame(rows)
    for rk in t.ranking.unique():
        s = t[t.ranking == rk]
        assert abs(s.old_weight.sum() - 1) < 1e-9 and abs(s.new_weight.sum() - 1) < 1e-9, rk
    return t


DOC = {  # metric -> (document that would resolve it, holder, economic driver in the sensitivity table)
    "ec_capex_usd_per_kg_dha_yr": ("Orçamento de capex por site (classe AACE ≥3) e capacidade efetiva", "Corbion",
                                   "capex ±30%"),
    "ec_opex_usd_per_kg_dha": ("Rendimento DHA/açúcar industrial e balanço de utilidades", "Corbion",
                               "rendimento 0,055/0,10"),
    "ec_sugar_usd_t": ("Contrato de açúcar entregue (especificação, entressafra)", "usina", "açúcar ±30%"),
    "ec_power_usd_kwh": ("Contrato de energia/vapor", "usina", "—"),
    "ac_freight_usd_t": ("Cotações de frete entregue por destino/Incoterm", "Corbion/agente", "frete ±50%"),
    "ex_corbion_staff_on_site": ("Organograma do site", "Corbion", "—"),
    "ex_months_to_first_dha": ("Cronograma de engenharia + licenciamento", "Corbion/EPC", "licenciamento +2/0 anos"),
    "rs_basin_water_stress": ("Balanço hídrico do site e outorga", "Corbion/órgão gestor", "—"),
    "rs_water_grant_incremental": ("Outorga para a demanda incremental", "DAEE-SP Águas / órgão TH",
                                   "licenciamento +2/0 anos"),
    "rs_utility_backup": ("Plano de backup de vapor/energia na entressafra", "Corbion/usina", "—"),
    "op_space_documented": ("Plot plan e reserva de utilidades", "Corbion", "—"),
    "ec_net_price": ("Preço líquido 2027+ por destino (resultado da renovação dez/2026)", "Corbion/clientes",
                     "preço DHA ±30%"),
    "fc_competitor_documented": ("Lista de fornecedores qualificados por fábrica de ração", "clientes", "—"),
    "rk_fx_vol": ("Série cambial", "público", "—"),
    "dm_dha_tech_t": ("Produção de ração por espécie/fase", "associações/FAO", "demanda ±30%"),
    "dm_growth": ("Projeção setorial", "associações", "demanda ±30%"),
}


def missing_data_value(site_res: dict, market_res: dict, econ: dict | None) -> pd.DataFrame:
    sens = econ["sensitivity"] if econ else pd.DataFrame()
    rows = []
    sf = site_res["flips"]
    cs = site_res["cell_scores"]
    for k, (doc, holder, driver) in DOC.items():
        if k not in site_res["specs"]:
            continue
        unknown_at = sorted(cs[(cs.metric_id == k) & (cs.effective_status == "UNKNOWN")].entity)
        ranged = sorted(cs[(cs.metric_id == k) & (cs.score_hi - cs.score_lo > 1e-9)
                           & (cs.effective_status != "UNKNOWN")].entity)
        f = sf[(sf.metric_id == k)]
        br_th = f[f.leader.str.startswith("BR") & f.challenger.str.startswith("TH")]
        swing = sens[sens.driver == driver].swing_musd.max() if driver != "—" and not sens.empty else float("nan")
        rows.append({"ranking": "site", "metric_id": k, "abs_weight": site_res["specs"][k].weight
                     * site_res["crit_w"][site_res["specs"][k].criterion],
                     "unknown_at": ";".join(unknown_at), "ranged_at": ";".join(ranged),
                     "single_doc_can_flip_any_pair": bool(f.single_document_can_flip.any()),
                     "single_doc_can_flip_brazil_thailand": bool(br_th.single_document_can_flip.any()),
                     "pairs_flippable": ";".join(f"{a}>{b}" for a, b in
                                                 f[f.single_document_can_flip][["leader", "challenger"]].values),
                     "npv_swing_musd_driver": swing, "economic_driver": driver,
                     "document_needed": doc, "holder": holder})
    mf = market_res["flips"]
    for k, (doc, holder, driver) in DOC.items():
        f = mf[mf.metric_id == k]
        if f.empty:
            continue
        swing = sens[sens.driver == driver].swing_musd.max() if driver != "—" and not sens.empty else float("nan")
        rows.append({"ranking": "mercado", "metric_id": k, "abs_weight": float("nan"),
                     "unknown_at": ";".join(sorted(set(f.challenger) | set(f.leader))), "ranged_at": "",
                     "single_doc_can_flip_any_pair": bool(f.single_document_can_flip.any()),
                     "single_doc_can_flip_brazil_thailand": False,
                     "pairs_flippable": ";".join(f"{a}>{b}" for a, b in
                                                 f[f.single_document_can_flip][["leader", "challenger"]].values),
                     "npv_swing_musd_driver": swing, "economic_driver": driver,
                     "document_needed": doc, "holder": holder})
    rows.append({"ranking": "gate", "metric_id": "G04 reconciliação SKU–cepa–licença", "abs_weight": float("nan"),
                 "unknown_at": "todos os mercados", "ranged_at": "", "single_doc_can_flip_any_pair": True,
                 "single_doc_can_flip_brazil_thailand": False, "pairs_flippable": "gate (não compensatório)",
                 "npv_swing_musd_driver": float("nan"), "economic_driver": "—",
                 "document_needed": "Mapa SKU–cepa–fábrica–licença–mercado assinado", "holder": "Corbion"})
    rows.append({"ranking": "economia", "metric_id": "resultado da renovação dez/2026", "abs_weight": float("nan"),
                 "unknown_at": "todas as alternativas", "ranged_at": "", "single_doc_can_flip_any_pair": True,
                 "single_doc_can_flip_brazil_thailand": True,
                 "pairs_flippable": "sinal do VPL de B/C/D (R1/R4 negativos, R3/R5/R6 positivos)",
                 "npv_swing_musd_driver": float("nan"), "economic_driver": "cenários R1-R6",
                 "document_needed": "Termos renovados (preço, volume, take-or-pay, prazo)", "holder": "Corbion"})
    t = pd.DataFrame(rows)
    t["priority"] = t.apply(lambda r: "alta" if r.single_doc_can_flip_brazil_thailand or
                            (pd.notna(r.npv_swing_musd_driver) and r.npv_swing_musd_driver > 100) else
                            ("média" if r.single_doc_can_flip_any_pair else "baixa"), axis=1)
    return t.sort_values(["priority", "npv_swing_musd_driver"], ascending=[True, False])
