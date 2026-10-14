"""investment memo (Portuguese) built from the run's own outputs."""

from __future__ import annotations

import numpy as np
import pandas as pd

APP = {"salmon": "salmão", "shrimp": "camarão", "pet_food": "pet food"}


def f(v, dec=0):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v):
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{100 * v:.0f}%"


def write_memo(r: dict) -> None:
    cfg, out = r["cfg"], r["out"]
    tot, mkt, rk, voi = r["tot"], r["mkt"], r["rk"], r["voi"]
    seg = r["seg"]
    mcq = r["mcq"]
    sel = r["sel"]
    v3 = r.get("v3eff", pd.DataFrame())
    A = r["d"]["A"]
    L = ["# Mercados para expansão e consolidação de DHA (AlgaPrime): memorando", "",
         f"*Corte: {cfg['cutoff_date']} · commit {r['manifest']['git_commit']} · seed {cfg['seed']} · "
         f"{r['manifest']['mc_sims']} simulações · gerado por `python -m src run`*", "",
         "> **Natureza do resultado.**",
         "> - É um estudo de mercado independente da localização da fábrica.",
         "> - Os documentos originais (Corbion, BioMar, IFFO, FAO, FEDIAF, USDA) não puderam ser abertos neste "
         "ambiente; os números vêm de trechos de busca e estão marcados em `source_registry.csv`.",
         "> - Não há preço público do AlgaPrime, contratos nem tonelagem por cliente. Volumes e receitas são "
         "**cenários condicionais a premissas explícitas**, não pedidos nem previsões da Corbion.",
         "> - Nutrição humana (AlgaVia) é oportunidade adjacente e **não entra** nos totais.", "",
         "## 1. Resposta curta", ""]
    b30, b35 = tot["base"][2030], tot["base"][2035]
    salmon = mkt[mkt.application == "salmon"]
    L += [
        f"1. **O negócio de ração é, na prática, salmão.** No cenário-base de 2030, salmão responde por "
        f"{pct(seg[(seg.year == 2030) & (seg.application == 'salmon')].revenue_usd.sum() / seg[seg.year == 2030].revenue_usd.sum())} "
        f"da receita B2B modelada (US$ {f(b30['revenue_musd'])} mi no total).",
        f"   - Noruega e Chile concentram {pct(salmon[salmon.country.isin(['Norway', 'Chile'])].incremental_sku_2030_t.sum() / mkt.incremental_sku_2030_t.sum())} "
        "do volume incremental.",
        "   - Camarão, China e pet food têm grandes TAMs, mas o SAM é pequeno: em camarão, o DHA da fase de engorda já "
        "vem de farinha e óleo de peixe, e só uma fração dos produtores paga por DHA adicional.",
        f"2. **Consolidar antes de expandir.** A carteira ótima (MILP: equipe, registros, capacidade e concentração) "
        f"escolhe {', '.join(sel[sel.selected == 1].country + ' · ' + sel[sel.selected == 1].application.map(APP))}, "
        f"com VPL comercial de US$ {f(r['pinfo']['objective_npv_musd'], 1)} mi.",
        "   - Nenhum mercado de expansão tem VPL comercial positivo com as premissas-base: os volumes não cobrem o "
        "custo de equipe, registros e ensaios.",
        f"3. **Capacidade que a carteira sustenta** (volume incremental sobre 2025, t de SKU/ano):",
        f"   - 2028: {f(tot['base'][2028]['incremental_sku_t'])} t (base), faixa {f(tot['low'][2028]['incremental_sku_t'])}–{f(tot['high'][2028]['incremental_sku_t'])};",
        f"   - 2030: {f(b30['incremental_sku_t'])} t, faixa {f(tot['low'][2030]['incremental_sku_t'])}–{f(tot['high'][2030]['incremental_sku_t'])};",
        f"   - 2035: {f(b35['incremental_sku_t'])} t, faixa {f(tot['low'][2035]['incremental_sku_t'])}–{f(tot['high'][2035]['incremental_sku_t'])}.",
        f"   - Um módulo de 10 kt (8.500 t efetivas) fica {pct(b35['incremental_sku_t'] / 8500)} ocupado em 2035 no "
        f"cenário-base. No Monte Carlo, o p10–p90 de 2035 vai de {f(mcq.loc[0.1, 'incremental_sku_2035_t'])} a "
        f"{f(mcq.loc[0.9, 'incremental_sku_2035_t'])} t.",
        "4. **O que mais muda a decisão** (valor de fechar a lacuna):",
        "   - " + "; ".join(f"{x.label} (swing de US$ {f(x.npv_swing_musd)} mi)" for x in voi.head(4).itertuples()) + ".",
        "   - Preço realizado e participação/alvo de DHA pesam mais que crescimento ou custo variável.",
    ]
    if not v3.empty:
        g = v3[(v3.v3_pipeline_weights == "base")].set_index(["demand_source", "alternative"])
        L += ["5. **Efeito no estudo da fábrica (v3).** Rodei o motor v3 em memória, sem sobrescrever nada, com "
              "esta demanda no lugar das premissas antigas (pesos de pipeline base da v3):",
              f"   - A1 Orindiúva: VPL de US$ {f(g.loc[('v3 default premises', 'A1_ORI'), 'npv_musd'])} mi (premissas v3) → "
              f"{f(g.loc[('market study base', 'A1_ORI'), 'npv_musd'])} (mercado base) e "
              f"{f(g.loc[('market study high', 'A1_ORI'), 'npv_musd'])} (mercado alto).",
              f"   - Preço mínimo de A1: US$ {f(g.loc[('market study base', 'A1_ORI'), 'msp_usd_kg_dha'], 1)}/kg DHA com o mercado base.",
              f"   - G (Orindiúva + Tailândia): {f(g.loc[('market study base', 'G_ORI_TH_NOW'), 'npv_musd'])} (base) e "
              f"{f(g.loc[('market study high', 'G_ORI_TH_NOW'), 'npv_musd'])} (alto).",
              "   - Leitura: com a demanda bottom-up base, nem a expansão de Orindiúva se paga sem contratos. O "
              "investimento depende de converter o pipeline de salmão e de preço. A Tailândia só faz sentido no "
              "cenário alto. O Prompt 3 deve integrar isso formalmente."]
    L += ["", "## 2. Auditoria das afirmações usadas nos slides", "",
          "| ID | Afirmação | Situação | Consequência |", "|---|---|---|---|"]
    for x in r["d"]["claims"].itertuples():
        num = x.number if isinstance(x.number, str) else "sem número"
        L.append(f"| {x.claim_id} | {x.claim} ({num}) | {x.status} | {x.consequence_for_tam_sam_som} |")
    L += ["", "**GMI:**",
          "",
          "- A página em inglês (US$ 720 mi em 2025) e a página antiga (US$ 4,5 bi em 2025) divergem 6× para o "
          "mesmo ano.",
          "- Não há documento que reconcilie escopo (sistemas × ingredientes × óleo × downstream) nem a definição de "
          "tonelada. O conflito é **insolúvel com dados públicos**.",
          "- Nenhum desses números é usado como TAM. A participação de 29,3% **não** é dado divulgado pela Corbion, e "
          "a divisão US$ 720 mi / 12,5 kt **não** é usada como preço.",
          "",
          "**DSM-Firmenich e Veramaris:** a Veramaris é uma joint venture 50/50 entre dsm-firmenich e Evonik e é "
          "contada **uma única vez**.", "",
          "## 3. TAM → SAM → SOM (denominadores visíveis)", "",
          "Definições em `market_definitions.csv`:",
          "",
          "- **TAM:** necessidade técnica de DHA.",
          "- **SAM:** espaço que DHA de algas pode suprir, considerando capacidade econômica de pagar, qualificação "
          "técnica, prontidão regulatória e o DHA que não vem de ingredientes marinhos.",
          "- **SOM:** SAM × adoção × participação da Corbion.", "",
          "| Ano | Cenário | TAM (t DHA) | SAM (t DHA) | DHA de algas (t) | SOM (t DHA) | SOM (t SKU) | Receita B2B (US$ mi) | Contribuição (US$ mi) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for y in cfg["milestones"]:
        for sc in ("low", "base", "high"):
            t = tot[sc][y]
            L.append(f"| {y} | {sc} | {f(t['tam_dha_t'])} | {f(t['sam_dha_t'])} | {f(t['algal_dha_t'])} | {f(t['som_dha_t'])} | "
                     f"{f(t['som_sku_t'])} | {f(t['revenue_musd'], 1)} | {f(t['contribution_musd'], 1)} |")
    w = r["wf"][(r["wf"].scenario == "base") & (r["wf"].year == 2030)]
    L += ["", "**Por nicho em 2030 (base):**", "",
          "| Nicho | Ração (Mt) | TAM | SAM | SOM (t DHA) | SOM (t SKU) | Receita (US$ mi) |", "|---|---|---|---|---|---|---|"]
    for x in w.itertuples():
        L.append(f"| {APP[x.application]} | {f(x.feed_t / 1e6, 2)} | {f(x.tam_dha_t)} | {f(x.sam_dha_t)} | {f(x.som_dha_t)} | "
                 f"{f(x.som_sku_t)} | {f(x.revenue_musd, 1)} |")
    L += ["",
          "- **Cenário baixo:** combina todas as premissas desfavoráveis; funciona como stress, não como "
          "\"provável\".",
          "- **Monte Carlo:** usa multiplicadores globais com óleo de peixe correlacionado à adoção (ρ = 0,4). "
          f"Receita de 2030: p10 US$ {f(mcq.loc[0.1, 'revenue_2030_musd'])} mi, p50 {f(mcq.loc[0.5, 'revenue_2030_musd'])} e "
          f"p90 {f(mcq.loc[0.9, 'revenue_2030_musd'])}.", "",
          "**Margem.** Preço líquido base de US$ 25/kg DHA (premissa: não há preço público), menos custos comerciais, "
          "rebates e capital de giro (13%), custo variável de Orindiúva vindo da v3 "
          f"(US$ {f(A['variable_cost_usd_per_kg_dha']['base'], 2)}/kg DHA) e frete. A margem de contribuição fica "
          f"entre US$ {f(mkt.unit_contribution_usd_kg_dha.min(), 1)} e {f(mkt.unit_contribution_usd_kg_dha.max(), 1)}/kg DHA "
          "conforme o nicho.", "",
          "**Custo na dieta e trade-off DHA:EPA** (`diet_cost_comparison.csv`):",
          "",
          "- Óleo de peixe 18:12 a US$ 2,5–6,8 mil/t custa US$ 8–23 por kg de EPA+DHA, e entrega EPA e DHA juntos.",
          "- O AlgaPrime entrega só DHA: o EPA continua vindo de óleo de peixe ou de óleo de algas EPA+DHA (Veramaris).",
          "- Sem uma matriz de ingredientes defensável, não fiz reformulação por programação linear.", "",
          "## 4. Reconciliação top-down (só plausibilidade)", "", "| Cheque | Bottom-up | Top-down | Status |", "|---|---|---|---|"]
    for x in r["rec"].itertuples():
        L.append(f"| {x.check} | {x.bottom_up} | {x.top_down} | **{x.status}** |")
    L += ["",
          "A maior inconsistência:",
          "",
          "- O SOM bottom-up de 2025 (≈ US$ 25 mi) explica só uma fração das vendas de Nutrition em 2024 "
          "(€157 mi).",
          "- Explicações possíveis, que não consigo separar com dados públicos:",
          "  - (a) a participação de AlgaVia/humana e de pet é maior;",
          "  - (b) o preço realizado é bem maior que US$ 25/kg DHA;",
          "  - (c) as premissas de participação e de adoção estão conservadoras.",
          "- **Isso é a lacuna nº 1 a fechar com a Corbion:** volume e preço por SKU e por mercado.", "",
          "## 5. Rankings condicionados (VPL comercial; o score é só triagem)", "",
          "| Grupo | # | Mercado | Status de relação | VPL comercial (US$ mi) | Incremental 2030 (t) | P(qualificação) | Score de triagem | P(top 3) pesos | Confiança dado |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for x in rk.itertuples():
        L.append(f"| {x.group} | {x.rank_by_npv} | {x.country} · {APP[x.application]} | {x.relationship_status} | "
                 f"{f(x.commercial_npv_musd, 1)} | {f(x.incremental_sku_2030_t)} | {pct(x.p_qualification)} | "
                 f"{f(x.triage_score, 1)} | {pct(x.p_top3_triage_weights)} | {x.data_confidence} |")
    dc = r["dim_corr"]
    L += ["", "**Contagem dupla no score de triagem:** probabilidade de qualificação, canal, tempo até a receita e "
          f"aderência estratégica têm correlação de {f(dc.values[np.triu_indices(len(dc), 1)].max(), 2)} entre si "
          "(`triage_dimension_correlation.csv`). Por isso a decisão usa VPL e volume, não o score.", "",
          "## 6. Onde há adoção documentada e onde é só potencial", ""]
    for x in r["acc"].itertuples():
        L.append(f"- **{x.entity}** ({x.countries}, {APP.get(x.application, x.application)}): `{x.relationship_status}`; "
                 f"evidência: {x.evidence} ({x.evidence_date if isinstance(x.evidence_date, str) else 'sem data'}). "
                 f"Próxima prova: {x.next_proof_needed}.")
    L += ["",
          "- **Nenhuma conta está como `documented_current`:** não há evidência pública de 2025–26 com tonelagem.",
          "- **BioMar (\"~1 Mt de ração com microalgas\")** é ração com algum ingrediente de algas, não volume de "
          "AlgaPrime.",
          "- **JVs da BioMar (Tongwei, Viet-Uc) e GACC** são canal ou acesso, não clientes.",
          "- **IQI** é distribuidor; a demanda final é das marcas.", "",
          "## 7. Carteira e restrições", ""]
    c = r["conc"]
    L += [
        f"- **Ótimo-base:** {', '.join(sel[sel.selected == 1].country)}; usa {f(r['pinfo']['fte_used'], 1)} pessoas (FTE) e "
        f"{f(r['pinfo']['incremental_sku_2030_t'])} t incrementais em 2030. Solver HiGHS, status ótimo, gap "
        f"{r['pinfo']['mip_gap']}. O teste confere o resultado com força bruta.",
        "- **Concentração:**"]
    for x in c[c.max_country_share.notna()].itertuples():
        L.append(f"  - limite por país de {pct(x.max_country_share)} → VPL de US$ {f(x.objective_npv_musd, 1)} mi")
    L += [
        "  - A 40%, nenhuma carteira com VPL positivo é viável: a dependência de Noruega e Chile é estrutural.",
        "- **Orçamento de equipe:** entre 5 e 12 FTE o ótimo não muda. A restrição que pesa é econômica (volume de "
        "expansão pequeno), não de equipe.", "",
        "## 8. Valor da informação (o que coletar primeiro)", "",
        "| Dado | Como fechar | VPL da carteira (min–máx, US$ mi) | Incremental 2030 (t) | Muda a carteira? |", "|---|---|---|---|---|"]
    for x in voi.itertuples():
        L.append(f"| {x.label} | {x.how_to_close_gap} | {f(x.portfolio_npv_low_musd, 1)}–{f(x.portfolio_npv_high_musd, 1)} | "
                 f"{f(x.incremental_2030_low_t)}–{f(x.incremental_2030_high_t)} | {'sim' if x.portfolio_changes else 'não'} |")
    L += ["", "## 9. Sequência comercial recomendada", "",
          "1. **Salmão Chile e Noruega:** converter a relação histórica com a BioMar (e outros formuladores) em contratos "
          "plurianuais com volume e preço. É o que sustenta ou não o módulo de Orindiúva.",
          "2. **Fechar as lacunas de maior valor:**",
          "   - preço líquido por SKU e mercado;",
          "   - participação versus Veramaris nas contas de salmão;",
          "   - especificação de EPA+DHA dos clientes (alvo por fase).",
          "3. **Pet food (EUA/UE, via IQI):** baixo custo de entrada. Precisa de lista de marcas, dose e claims para virar "
          "pipeline qualificado.",
          "4. **Camarão (Equador, Tailândia):** só com ensaio pago e prova de que DHA adicional melhora desempenho ou "
          "permite cortar óleo de peixe. Com as premissas atuais, o VPL é negativo.",
          "5. **China:** acesso regulatório existe (GACC), mas a concorrência local e a falta de clientes documentados "
          "deixam o mercado como opção, não como base de capacidade.",
          "6. **Nutrição humana (AlgaVia):** avaliar em estudo separado. Pode explicar boa parte da receita atual de "
          "Nutrition.", "",
          "## 10. Interface com o estudo da fábrica", "",
          "- **Demanda base:** `market_demand_scenarios.csv`, no esquema da v3 e validado com `validate_demand` da v3.",
          "- **Variantes:** `_low.csv` e `_high.csv`.",
          "- **Classificação dos volumes:**",
          "  - relação documentada → `qualified_pipeline`;",
          "  - demais → `unqualified_potential`;",
          "  - `contracted` = 0.",
          "- **Curvas e limites:** `market_demand_curves.csv` traz as curvas por status, preço, margem e confiança; "
          "`cockpit_bounds.csv` traz os limites e as dependências entre controles.",
          "- **Para alimentar a v3:** `python -m src run --publish-v3`, depois `cd ../v3 && python -m src run`. "
          f"Validação: {r['v3_check']}.", "",
          "## 11. Lacunas que exigem entrevista, contrato ou ensaio", ""]
    for x in pd.read_csv(out / "source_gaps.csv").query("type != 'source'").itertuples():
        L.append(f"- [{x.type}] {x.item}: {x.next_step}")
    L += ["", "Fontes que precisam ser abertas no original antes de qualquer número ir para o comitê: "
          "`source_gaps.csv` (type = source).", ""]
    (out / "market_memo.md").write_text("\n".join(L), encoding="utf-8")
