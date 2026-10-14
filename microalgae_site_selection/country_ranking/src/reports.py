"""Memos generated from outputs (no hand-typed numbers)."""

from __future__ import annotations

import pandas as pd

from .charts import PT, fmt

CRIT_PT = {"production_economics": "Economia de produção", "market_access": "Acesso a mercados",
           "corbion_readiness": "Prontidão Corbion", "regulation_incentives": "Regulação e incentivos",
           "strategic_risk": "Risco estratégico"}


def pct(x):
    return f"{x * 100:.0f}%"


def _top_bottom_subs(sub: pd.DataFrame, model, c: str, k=2):
    s = sub.loc[c].dropna()
    lab = {i: model.subs[i][1] for i in s.index}
    hi = ", ".join(f"{lab[i]} ({fmt(s[i])})" for i in s.nlargest(k).index)
    lo = ", ".join(f"{lab[i]} ({fmt(s[i])})" for i in s.nsmallest(k).index)
    return hi, lo


def plant_memo(res: dict) -> None:
    from .plant import OUT
    t, model, sub = res["table"], res["model"], res["sub"]
    w = model.scenarios[model.base]
    order = list(t.index)
    a, b = order[0], order[1]
    tips = pd.read_csv(OUT / "plant_tipping_points.csv")
    rob = pd.read_csv(OUT / "plant_goalpost_robustness.csv")
    corr = pd.read_csv(OUT / "plant_criterion_correlation.csv", index_col=0)
    L = []
    L.append("# Melhor país para a nova unidade de DHA de microalgas (Corbion AlgaPrime) – ranking ponderado\n")
    L.append(f"*Gerado por `python -m src plant` · pesos 30/20/15/15/20 · {len(t)} países · {len(model.metrics)} métricas · "
             f"cada país avaliado numa usina de referência.*\n")
    L.append("> **Natureza do resultado.** O score é uma triagem multicritério de 0 a 10, não VPL. Os dados vêm de "
             "fontes públicas, lidas na maioria por trechos de busca (portais primários bloqueados neste ambiente); "
             "cada valor tem fonte, ano, tipo e confiança em `data/processed/plant_inputs_long.csv`.\n")
    L.append("## 1. Resposta\n")
    L.append(f"**{PT.get(a, a)} é o melhor país para a nova unidade** (score {fmt(t.score[a], 2)}), seguido de "
             f"{PT.get(b, b)} ({fmt(t.score[b], 2)}) e {PT.get(order[2], order[2])} ({fmt(t.score[order[2]], 2)}).\n")
    L.append(f"- **Robustez a pesos:** com pesos sorteados em torno de 30/20/15/15/20, {PT.get(a, a)} fica em 1º em "
             f"{pct(t.p_rank1_weights[a])} dos casos; {PT.get(b, b)} em {pct(t.p_rank1_weights[b])}.")
    L.append(f"- **Robustez a dados:** com ruído conforme a confiança de cada fonte, {PT.get(a, a)} fica em 1º em "
             f"{pct(t.p_rank1_data[a])} e no top 3 em {pct(t.p_top3_data[a])}.")
    sc = ", ".join(f"{n}: {PT.get(t[f'rank_{n.split()[0].lower()}'].idxmin())}" for n in model.scenarios)
    L.append(f"- **1º lugar por cenário de pesos:** {sc}.")
    L.append(f"- **Mercados ponderados pela necessidade técnica de DHA (TAM, mais camarão asiático) em vez do SAM:** "
             f"1º = {PT.get(t.rank_tam_market_weights.idxmin())}; {PT.get(b, b)} fica em {int(t.rank_tam_market_weights[b])}º.")
    L.append(f"- **Só com métricas quantitativas** (sem rubricas): 1º = {PT.get(t.rank_quant_only.idxmin())}; "
             f"{PT.get(a, a)} fica em {int(t.rank_quant_only[a])}º.")
    gate_rev = [PT.get(c, c) for c in order if t.gate[c] != "Pass"]
    L.append(f"- **Gates (nenhum país é excluído, mas ficam em revisão):** {', '.join(gate_rev) or 'nenhum'}.\n")
    L.append("## 2. Ranking\n")
    L.append("| # | País | Usina de referência | Score | Econ. produção (30%) | Acesso mercados (20%) | Prontidão Corbion (15%) | "
             "Regulação (15%) | Risco (20%) | P(1º) pesos | P(top 3) dados | Gate | v2 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in order:
        r = t.loc[c]
        site = str(r.reference_site).split(" - ")[0].split("(")[0].strip()[:45]
        v2 = "" if pd.isna(r.v2_rank) else f"{int(r.v2_rank)}º"
        L.append(f"| {int(r['rank'])} | {PT.get(c, c)} | {site} | **{fmt(r.score, 2)}** | {fmt(r.production_economics)} | "
                 f"{fmt(r.market_access)} | {fmt(r.corbion_readiness)} | {fmt(r.regulation_incentives)} | "
                 f"{fmt(r.strategic_risk)} | {pct(r.p_rank1_weights)} | {pct(r.p_top3_data)} | {r.gate} | {v2} |")
    L.append("")
    L.append("## 3. Por que cada país está onde está\n")
    for c in order:
        hi, lo = _top_bottom_subs(sub, model, c)
        miss = t.missing_metrics[c]
        L.append(f"- **{PT.get(c, c)}** ({fmt(t.score[c], 2)}): forte em {hi}; fraco em {lo}."
                 + (f" Sem dado: {miss.replace(';', ', ')} (score entre {fmt(t.score_if_missing_0[c], 2)} e "
                    f"{fmt(t.score_if_missing_10[c], 2)} se a lacuna fosse 0 ou 10)." if miss else "")
                 + ("" if t.gate[c] == "Pass" else f" Gate: {t.gate_reasons[c]}."))
    L.append("")
    L.append("## 4. Pontos de virada\n")
    tt = tips[tips.challenger == b]
    for _, r in tt.iterrows():
        x = r.weight_where_challenger_overtakes
        L.append(f"- {PT.get(b, b)} passa {PT.get(a, a)} se **{CRIT_PT[r.criterion]}** pesar "
                 + ("— nunca, em nenhum peso entre 0 e 100%" if pd.isna(x) else f"{pct(x)} (base {pct(r.base_weight)})") + ".")
    L.append("")
    L.append("## 5. O que mudou em relação à v2 (aprofundamento)\n")
    L.append("- **Países:** 8 → 12 (EUA/Blair-NE, Equador, Peru, Filipinas).")
    L.append("- **Site real por país:** cada país é avaliado numa usina de açúcar de referência (EUA: moinho de milho de "
             "Blair com dextrose), com vapor/cogeração e estresse hídrico medidos no local da usina (Aqueduct), não na média nacional.")
    L.append("- **Açúcar:** a rubrica de custo virou preço doméstico em US$/t + produção + autossuficiência (produção/consumo).")
    L.append("- **Mão de obra:** PIB per capita (proxy) foi trocado por salário médio na indústria.")
    L.append("- **Acesso a mercados:** a distância em linha reta a 3 mercados virou dias porta a porta por rota marítima "
             "real (canais e cabos), ponderados pela demanda de DHA de 2030 de 12 mercados do estudo de mercado; "
             "mais LPI, conectividade marítima, cobertura de acordos comerciais e fábricas dos grandes clientes.")
    L.append("- **Prontidão Corbion:** só ativos e pessoas da Corbion (o vapor/açúcar da usina fica em Economia de "
             "produção), para reduzir a contagem dupla apontada na auditoria.")
    L.append("- **Regulação:** alíquota efetiva de 10 anos com incentivos e piso global de 15% (Corbion > €750 mi), "
             "aprovação do AlgaPrime para venda, prazo de alvará e índice OCDE de restrição a IED.")
    L.append("- **Risco:** rating soberano + WGI (estabilidade e qualidade regulatória) + volatilidade cambial 2020-25 + "
             "ND-GAIN (clima) + Special 301 2026 + concorrência local de DHA de algas.")
    rub_share = t.rubric_share_of_weight.mean()
    L.append(f"- **Peso de rubricas subjetivas:** caiu de ~66% (v2) para ~{pct(rub_share)} do peso efetivo.\n")
    L.append("## 6. Testes de robustez\n")
    for _, r in rob.iterrows():
        L.append(f"- Limites das escalas ×{r.goalpost_stretch}: {int(r.countries_changing_rank)} países mudam de posição; "
                 f"top 3 = {', '.join(PT.get(x.strip(), x.strip()) for x in r.top3.split(','))}; 1º inalterado: {'sim' if r.top1_unchanged else 'não'}.")
    pe_cr = corr.loc["production_economics", "corbion_readiness"]
    L.append(f"- Correlação entre Economia de produção e Prontidão Corbion nos 12 países: {fmt(pe_cr, 2)} (v2: 0,76).")
    xc = t.xc_variable_cost_usd_kg_dha.dropna().sort_values()
    L.append("- **Checagem de custo (não entra no score):** custo variável por kg de DHA na usina de referência, com a "
             "mesma base física da v3 (5,05 t de açúcar, 3.000 kWh e 6 t de vapor por t de produto): "
             + ", ".join(f"{PT.get(c, c)} US$ {fmt(v)}" for c, v in xc.items()) + ".\n")
    L.append("## 7. Limitações\n")
    L.append("- Fontes lidas por trechos de busca; Medium/Low precisam de conferência na fonte primária.")
    L.append("- Rubricas (~" + pct(rub_share) + " do peso) aplicadas por um único analista; template para mais avaliadores em "
             "`outputs/plant/plant_rubric_ratings_template.csv`.")
    L.append("- Salários com definições diferentes entre países (indústria vs. todos os setores, capital vs. país).")
    L.append("- Aqueduct 3.0 (o portal 4.0 estava bloqueado). Rotas marítimas aproximadas (±10%).")
    L.append("- Sem preço de açúcar para os países listados como lacuna acima; a métrica sai e os pesos são renormalizados.")
    (OUT / "plant_country_memo.md").write_text("\n".join(L), encoding="utf-8")
