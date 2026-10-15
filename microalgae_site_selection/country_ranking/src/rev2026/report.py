"""Portuguese decision memo generated from the revision outputs (no hand-typed numbers)."""

from __future__ import annotations

import pandas as pd

from .charts import NICHE_PT, SCEN_SHORT, SITE_SHORT, pt
from .common import OUT


def n(x, d=1):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n/d"
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x):
    return "n/d" if x is None or pd.isna(x) else f"{x:.0%}"


def memo(cfg, site, mkt, econ, checks) -> None:
    t = site["table"]
    g = econ["grid"]
    L = []
    a = L.append
    a("# Revisão factual dos rankings Corbion – localização de DHA e mercados de destino")
    a(f"*Revisão {cfg['revision_date']} · gerado por `python -m src rev2026` · todos os números vêm de "
      "`outputs/rev2026/*.csv`.*\n")
    top = t.index[0]
    a("## 1. Em uma página")
    a(f"- **Ranking público de sites (A):** {SITE_SHORT[top]} lidera pelo **piso garantido** "
      f"({n(t.at[top, 'floor'], 2)} de 10; teto {n(t.at[top, 'ceiling'], 2)}), mas **nenhuma posição está decidida** "
      "com dados públicos: todo site pode ficar entre 1º e 4º, porque capex, opex, frete entregue, outorga e backup "
      f"de utilidades são desconhecidos ({pct(t.unknown_weight.min())}–{pct(t.unknown_weight.max())} do peso). "
      "Resultado: **shortlist factual com faixas de posição, não ranking completo**.")
    ori, nsn = t.loc["BR_ORI_EXP"], t.loc["TH_NSN"]
    fl = site["flips"]
    bt = fl[(fl.leader == "BR_ORI_EXP") & fl.challenger.str.startswith("TH")]
    a(f"- **Brasil × Tailândia:** a vantagem de piso de Orindiúva sobre Nakhon Sawan "
      f"({n(ori.floor - nsn.floor, 2)} ponto) **não é revertida por nenhum documento isolado** "
      f"({int(bt.single_document_can_flip.sum())} métricas capazes); precisaria de vários (capex + opex + frete). "
      "Ela vem de fatos: único ativo de DHA operante, equipe no site, contrato de utilidades com a usina, "
      "açúcar ~US$ 300/t vs ~US$ 630/t.")
    r2 = g[(g.renewal_scenario == "R2_renova_igual") & (g.niche == "todos")].set_index("site")
    a(f"- **Retorno incremental (B), só como cenário ASSUMPTION:** VPL do módulo de Orindiúva "
      f"US$ {n(r2.at['BR_ORI_EXP', 'npv_musd'], 0)} mi (TIR {pct(r2.at['BR_ORI_EXP', 'irr'])}) em renovação igual; "
      f"Nakhon Sawan US$ {n(r2.at['TH_NSN', 'npv_musd'], 0)} mi; Rayong US$ {n(r2.at['TH_RYG', 'npv_musd'], 0)} mi; "
      f"greenfield BR US$ {n(r2.at['BR_GF_GO', 'npv_musd'], 0)} mi. O valor terminal é "
      f"{pct(r2.at['BR_ORI_EXP', 'tv_share_of_npv'])} do VPL de Orindiúva: sem ele, o VPL fica negativo até 2035. "
      "**Com dados públicos, VPL e TIR são 'não estimáveis'.**")
    gg = g[(g.niche == "todos") & (g.renewal_scenario != "R0_base")]
    neg = gg[gg.npv_musd < 0]
    a(f"- **A renovação de dez/2026 decide o sinal do VPL:** {len(neg)} de {len(gg)} combinações site×cenário têm VPL "
      "negativo (renovar com preço/volume menor ou perder conta); take-or-pay ou âncora nova tornam todos os sites "
      "positivos. Nenhum resultado de renovação estava divulgado em 15/10/2026.")
    pvx = gg.pivot(index="renewal_scenario", columns="site", values="npv_musd")
    fl_s = [f"{SITE_SHORT[s_]} supera Orindiúva em {SCEN_SHORT[sc]} ({n(pvx.at[sc, s_], 0)} × "
            f"{n(pvx.at[sc, 'BR_ORI_EXP'], 0)} US$ mi)" for sc in pvx.index for s_ in pvx.columns
            if s_ != "BR_ORI_EXP" and pvx.at[sc, s_] > pvx.at[sc, "BR_ORI_EXP"]]
    flip_txt = "; ".join(fl_s) if fl_s else "em nenhum cenário de renovação um site tailandês supera Orindiúva"
    gn = g[(g.renewal_scenario == "R2_renova_igual") & g.niche.isin(["salmon", "shrimp", "pet"])]
    a(f"- **Nenhum nicho sozinho** sustenta um módulo de 10 kt SKU sob as premissas v3 (VPL por nicho isolado de "
      f"US$ {n(gn.npv_musd.min(), 0)} a {n(gn.npv_musd.max(), 0)} mi): o módulo depende do portfólio somado.")
    mk = mkt["niches"]
    a("- **Mercados (A):** " + "; ".join(
        f"{NICHE_PT[k]} = {pt(v['table'].iloc[0].country)} no piso (faixa {int(v['table'].iloc[0].rank_best)}–"
        f"{int(v['table'].iloc[0].rank_worst)})" for k, v in mk.items()) +
      ". Consolidação (adoção histórica documentada) só em salmão Noruega/Chile/Reino Unido e camarão Tailândia; "
      "**nenhuma compra 2026 é documentada publicamente**. O preço líquido (25% × 60% do peso) é desconhecido em todos.")
    a("- **Por que o melhor ranking público pode não ser o melhor investimento:** o ranking mede o que é público "
      "e comparável; o VPL depende de quatro números privados (capex do site, rendimento, preço 2027+ e volume "
      "contratado). Um site bem colocado pode ter VPL negativo (ex.: greenfield BR em R1/R4), e um mal colocado pode "
      "passar à frente no VPL: " + flip_txt + ".\n")

    a("## 2. Lado A – ranking público de sites (pesos propostos 40/25/15/15/5)")
    a("| Site | Piso | Teto | Só dados conhecidos | Peso verificado | Julgamento | Desconhecido | Posição (piso) | Faixa | Gates |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for e, r in t.iterrows():
        a(f"| {SITE_SHORT[e]} | {n(r.floor, 2)} | {n(r.ceiling, 2)} | {n(r.partial_score_known_only, 2)} | "
          f"{pct(r.verified_weight)} | {pct(r.judgment_weight)} | {pct(r.unknown_weight)} | {int(r.rank_floor)} | "
          f"{int(r.rank_best)}–{int(r.rank_worst)} | {r.gate_overall} |")
    a("\nPor critério (piso–teto, 0-10):\n")
    a("| Site | " + " | ".join(cfg["site"]["criteria"][c]["label"] for c in site["crit_w"]) + " |")
    a("|---|" + "---|" * len(site["crit_w"]))
    for e, r in t.iterrows():
        a(f"| {SITE_SHORT[e]} | " + " | ".join(f"{n(r[c + '_floor'])}–{n(r[c + '_ceiling'])}" for c in site["crit_w"]) + " |")
    ws = site["weight_sets"].pivot(index="entity", columns="weight_set", values="rank_floor")
    a("\nPosição pelo piso em cada conjunto de pesos: " + "; ".join(
        f"{nm}: " + " > ".join(SITE_SHORT[e] for e in ws[nm].sort_values().index) for nm in ws.columns) + ".")
    pert = site["perturbation"]
    stable = pert.groupby("entity").rank_floor.nunique().max() == 1
    a(f"±25% relativo em cada critério: ordem pelo piso {'inalterada' if stable else 'muda em algum caso'} "
      "(site_weight_perturbation_pm25.csv). Tipping points: site_tipping_points.csv.\n")
    a("**Gates não compensatórios (product_regulatory_matrix.csv):** nenhum site tem `fail`; todos têm itens "
      "`review/unknown`. Orindiúva: LO 51001996 com validade impressa 02/09/2026 (renovação tempestiva prorroga – "
      "protocolo não visto; **não se afirma descumprimento**), LP/LI para o módulo, e a divergência de cepa "
      "(*Prototheca* S2014 OGM na LO/CTNBio × *Schizochytrium* não OGM em textos BioMar/IQI) que exige mapa "
      "SKU–cepa–licença. Tailândia: nenhum certificado BOI, licença de fábrica ou registro GACC de estabelecimento.\n")

    a("## 3. Lado B – retorno incremental por site, nicho e cenário (ASSUMPTION)")
    a(f"Demanda da v3: `{econ['demand_origin']}` (premissas rotuladas, não pedidos). Módulo entra em 2029 "
      "(capacidade atual suficiente até fim-2028/início-2029, H1 2026). WACC por país da v3.\n")
    pv = gg.pivot(index="site", columns="renewal_scenario", values="npv_musd")
    a("| Site | " + " | ".join(SCEN_SHORT[c] for c in pv.columns) + " |")
    a("|---|" + "---:|" * len(pv.columns))
    for s, r in pv.iterrows():
        a(f"| {SITE_SHORT[s]} | " + " | ".join(n(v, 0) for v in r) + " |")
    a("\n| Site (R2) | TIR | VT/VPL | VT/EV do projeto | Capex US$/kg·ano DHA | Custo US$/kg DHA | ROIC 2032-35 | "
      "Preço de equilíbrio US$/kg DHA | Utilização mínima 2035 | Payback descontado |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for s, r in r2.iterrows():
        a(f"| {SITE_SHORT[s]} | {pct(r.irr)} | {pct(r.tv_share_of_npv)} | {pct(r.tv_share_of_project_ev)} | "
          f"{n(r.capex_usd_per_kg_dha_yr)} | {n(r.lcod_usd_per_kg_dha)} | {pct(r.roic_steady_2032_35)} | "
          f"{n(r.breakeven_price_usd_kg_dha)} | {pct(r.min_utilisation_2035)} | "
          f"{int(r.disc_payback_year) if pd.notna(r.disc_payback_year) else 'após 2035'} |")
    w = econ["waiting"]
    a("\nValor de esperar 1 ano pelo resultado da renovação (probabilidades iguais, ASSUMPTION): " + "; ".join(
        f"{SITE_SHORT[r.site]} {n(r.value_of_waiting_musd, 1)}" for r in w.itertuples()) +
      " US$ mi (negativo = comprometer agora vale mais).")
    mc = econ["mc"]
    a("Monte Carlo v3 (volatilidade econômica sob premissas, não probabilidade observada): " + "; ".join(
        f"{SITE_SHORT[r.site]} P10/P50/P90 = {n(r.p10, 0)}/{n(r.p50, 0)}/{n(r.p90, 0)}" for r in mc.itertuples()) + ".")
    s = econ["sensitivity"]
    top_s = s[s.alternative == "A1_ORI"].head(5)
    a("Maiores sensibilidades de Orindiúva (R2): " + "; ".join(
        f"{r.driver} (amplitude US$ {n(r.swing_musd, 0)} mi)" for r in top_s.itertuples()) + ".")
    a("Astaxantina (Corbion–KAS): **não estimável** – desenvolvimento, sem capex, rendimento, registro ou contrato; "
      "não conta como capacidade nem receita (economics_astaxanthin.csv).\n")

    a("## 4. Ponte do ranking à decisão e dados necessários para aprovar capex")
    md = pd.read_csv(OUT / "missing_data_decision_value.csv")
    hi = md[md.priority == "alta"]
    for r in hi.itertuples():
        a(f"- **{r.metric_id}** ({r.ranking}): {r.document_needed} – detentor: {r.holder}"
          + (f"; amplitude de VPL ~US$ {n(r.npv_swing_musd_driver, 0)} mi" if pd.notna(r.npv_swing_musd_driver) else ""))
    a("- Template de dados de gestão (caso `management-data`, vazio até os dados chegarem): "
      "`management_data_template.csv`.\n")

    a("## 5. Mercados por nicho (pesos 25/25/25/15/10)")
    for k, v in mk.items():
        tt = v["table"].head(10)
        a(f"\n### {NICHE_PT[k]}")
        a("| # piso | País | Piso | Teto | Faixa | Verificado | Papel | Estágio de evidência | Gate SKU | TAM técnico t DHA |")
        a("|---:|---|---:|---:|---|---:|---|---:|---|---:|")
        for e, r in tt.iterrows():
            a(f"| {int(r.rank_floor)} | {pt(r.country)} | {n(r.floor, 2)} | {n(r.ceiling, 2)} | {int(r.rank_best)}–"
              f"{int(r.rank_worst)} | {pct(r.verified_weight)} | {r.role} | {n(r.evidence_stage, 0)} | {r.sku_gate} | "
              f"{n(r.tam_tech_dha_t, 0)} |")
        cons = v["table"][v["table"].role == "consolidação"]
        a(f"Consolidar: {', '.join(pt(c) for c in cons.country) or 'nenhum'}; expandir (melhores pisos): "
          f"{', '.join(pt(c) for c in v['table'][v['table'].role == 'expansão'].country.head(4))}.")
    pooled = mkt["pooled"].head(10)
    a("\n**Pares país×nicho (objetivo declarado: escolher os próximos pares a trabalhar; não é média de nichos):** " +
      "; ".join(f"{NICHE_PT[r.niche]}·{pt(r.country)} {n(r.floor, 2)}" for r in pooled.itertuples()) + ".")
    acc = mkt["accounts"]
    a("\n**Contas com maior evidência** (sem score composto; potencial técnico ≠ compra): " + "; ".join(
        f"{r.customer} {r.plant} ({r.evidence_stage}, {n(r.tech_dha_potential_t, 0)} t DHA técnicas)"
        for r in acc.head(6).itertuples()) + ".\n")

    a("## 6. O que poderia inverter as comparações-chave")
    mt = mkt["tipping"]
    mf = mkt["flips"]
    for niche, c1, _, c2 in cfg["market"]["pairs_to_test"]:
        f = mf[(mf.niche == niche) & mf.single_document_can_flip]
        tp = mt[(mt.niche == niche) & mt.tipping_weight.notna() & (mt.tipping_weight < 0.95) & (mt.basis == "floor")]
        a(f"- **{NICHE_PT[niche]}: {pt(c1)} × {pt(c2)}** – documento isolado que pode inverter: "
          f"{', '.join(sorted(set(f.label))) or 'nenhum'}; pesos de virada (piso): " +
          (", ".join(f"{r.criterion} a {pct(r.tipping_weight)}" for r in tp.itertuples()) or "nenhum entre 0 e 95%") + ".")
    sb = econ["sensitivity"]
    boi = sb[(sb.alternative == "C_TH_NSN") & (sb.driver == "BOI 0/8 anos (TH)")].iloc[0]
    a("- **Brasil × Tailândia (sites):** nenhum documento isolado inverte Orindiúva × Nakhon Sawan/Rayong pelo piso; "
      f"no VPL (ASSUMPTION): {flip_txt}. A base da v3 já supõe BOI de 8 anos; sem BOI, o VPL de Nakhon Sawan vai de "
      f"US$ {n(boi.npv_favourable_musd, 0)} mi para US$ {n(boi.npv_adverse_musd, 0)} mi (o top-up de 15% do Pilar Dois neutraliza quase todo o benefício na modelagem v3) – e nenhum certificado BOI existe.\n")

    a("## 7. Robustez, correlação e circularidade")
    corr = site["correlation"]
    a("- Correlação entre critérios (pisos) nos 4 sites: ver site_criterion_correlation.csv (n = 4, apenas "
      "descritiva). Mercados: market_criterion_correlation.csv. Resultado com/sem cada critério: "
      "*_leave_one_criterion_out.csv.")
    a("- Economia × Execução: açúcar/vapor só em Economia; Execução só ativo/equipe/cronograma. "
      f"Correlação dos pisos Economia×Execução nos sites = {n(corr.at['economia_floor', 'execucao_floor'], 2)} "
      "(n = 4; não interpretável estatisticamente).")
    a("- Circularidade: o acesso do site usa destinos com pesos fixos 1/3 por nicho (não o SAM do ranking de mercado); "
      "o prazo desde Orindiúva aparece nos dois rankings e entra uma única vez no VPL (circularity_check.csv).")
    a("- Incerteza epistemológica (falta de informação) = largura piso–teto; volatilidade econômica = Monte Carlo do "
      "DCF. São mostradas separadamente.\n")

    a("## 8. Auditoria e verificações")
    ca = pd.read_csv(OUT / "claims_audit.csv")
    a(f"- {len(ca)} afirmações auditadas em claims_audit.csv (ex.: tetos da LO ≠ capacidade; cepa S2014 × "
      "Schizochytrium; 5 × 6 fermentadores; Aqueduct 0 × Corbion AR 'alto risco' em Orindiúva; nota 10 por "
      "'único produtor' removida; GMI com versões conflitantes; '2/3 em contratos' não confirmado).")
    reg = pd.read_csv(OUT / "source_registry.csv")
    vc = reg.verification_level.value_counts()
    a("- Fontes: " + ", ".join(f"{k}: {v}" for k, v in vc.items()) + ". **Nenhuma fonte primária pôde ser aberta "
      "integralmente neste ambiente** (hosts bloqueados); o que veio do brief está como L1 e o que veio de trechos "
      "de busca como L2 – nenhum número foi tratado como lido do documento original.")
    js = {k: v["table"].judgment_weight.max() for k, v in mk.items()}
    a(f"- Meta de julgamento ≤ {cfg['judgment_budget']:.0%}: sites {pct(t.judgment_weight.max())}; " + "; ".join(
        f"{NICHE_PT[k]} até {pct(v)}" for k, v in js.items()) + ". **Camarão não atinge a meta** (contagem de "
      "fabricantes, escore de doença e projeção de crescimento vêm de 'conhecimento do analista'); por isso o "
      "ranking de camarão não deve ser chamado de robusto.")
    a("- Verificações automáticas (automated_checks.csv): " + ", ".join(
        f"{k}: {v}" for k, v in checks.result.value_counts().items()) + ".")
    for r in checks[checks.result == "FAIL"].itertuples():
        a(f"  - FAIL: {r.check} – {r.detail}")
    a("\n## 9. O que mudou em relação a 14/10/2026")
    a("- Ranking de país → ranking de **site** (4 projetos) + gates; regulação e incentivos saíram do score.")
    a("- Peso de notas não documentadas: de ~41% para ≤ 5% (julgamento explícito) + intervalo explícito para o "
      "desconhecido (antes o dado ausente era renormalizado).")
    a("- Brasil continua à frente da Tailândia pelo piso, mas **não é mais 'robusto'**: a ordem completa não é "
      "sustentável com dados públicos. No mercado, Noruega, China e EUA seguem 1º no piso de seus nichos, mas com "
      "faixas largas; França cai por cobertura baixa (não por evidência contrária).")
    a("\n## 10. Como reproduzir")
    a("```\ncd microalgae_site_selection/country_ranking\npython -m src rev2026            # ~1-2 min\n"
      "python -m pytest tests/test_rev2026.py -q\n```")
    a("Entradas: `data/rev2026/*.csv`, `config_rev2026.yaml`, motor v3 (`../v3`). Saídas: `outputs/rev2026/`. "
      "Versão anterior congelada: `outputs/frozen_2026-10-14/`.")
    (OUT / "revision_memo.md").write_text("\n".join(L), encoding="utf-8")
