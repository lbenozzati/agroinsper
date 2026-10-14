"""integrated_investment_memo.md, generated from this run's outputs."""

from __future__ import annotations

import numpy as np
import pandas as pd


def f(v, d=0):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v):
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{100 * v:.0f}%"


def write_memo(r: dict) -> None:
    cfg, out, comp, mcs, th = r["cfg"], r["out"], r["comp"], r["mcs"], r["th"]
    lab = {k: v["label"] for k, v in cfg["policies"].items()}
    c = comp.set_index(["market_scenario", "policy"])
    best = {sc: comp[comp.market_scenario == sc].sort_values("npv_musd").iloc[-1] for sc in cfg["market_scenarios"]}
    m = mcs.set_index("policy")
    mc_best = mcs.sort_values("expected_npv_musd").iloc[-1]
    risk_min = mcs[mcs.policy != "WAIT"].sort_values("cvar10_musd").iloc[-1]
    dil, inv, frl, st, compo = r["dil"], r["inv"], r["frl"], r["stress"], r["compo"]
    prov = r["prov"]
    th_lines = []
    for cap, g in frl.groupby("capex_ori_musd"):
        ok = g.dropna(subset=["min_asia_contract_for_THalone_gt_A_t"]).sort_values("net_price_usd_kg_dha")
        if ok.empty:
            th_lines.append(f"  - capex de Orindiúva US$ {f(cap)} mi: não vence em nenhum preço da grade (até US$ 45/kg DHA);")
        else:
            x = ok.iloc[0]
            th_lines.append(f"  - capex de Orindiúva US$ {f(cap)} mi: vence a partir de US$ {f(x.net_price_usd_kg_dha, 1)}/kg DHA, "
                            f"com ≥ {f(x.min_asia_contract_for_THalone_gt_A_t)} t/ano asiáticas contratadas;")
    order_corr = list(mcs.dropna(subset=["expected_npv_independent"]).sort_values("expected_npv_musd").policy)
    order_ind = list(mcs.dropna(subset=["expected_npv_independent"]).sort_values("expected_npv_independent").policy)
    order_msg = "A ordem das políticas não muda." if order_corr == order_ind else "A ordem das políticas muda; ver monte_carlo_policy_summary.csv."
    base_inc_2030 = r["up"].mm.market_table(r["up"].cm, r["up"].dm, r["segs"]["base"]).incremental_sku_2030_t.sum()
    hi_loss = st[(st.market_scenario == "high") & (st.policy == "A_ORI_1") & st.stress.str.startswith("ori_outage")].loss_musd.max()
    L = ["# Estratégia integrada: capacidade, origem, mercados e momento do investimento em DHA (Corbion)", "",
         f"*Corte {cfg['cutoff_date']} · commit {prov['git_commit']} · v3 {prov['v3_version']} · mercado {prov['market_version']} · "
         f"seed {cfg['seed']} · {prov['mc_sims']} simulações conjuntas · testes de origem: v3 {prov.get('v3_tests', 'não executados')}, "
         f"mercado {prov.get('market_tests', 'não executados')}*", "",
         "**Rótulos usados:**",
         "",
         "- **[observado]:** dado público com fonte, lido por trecho de busca.",
         "- **[derivado]:** cálculo sobre dados observados.",
         "- **[hipótese]:** premissa explícita.",
         "",
         "Não houve acesso a contratos, preços realizados nem dados internos da Corbion. Toda conclusão abaixo é "
         "**condicional**.", "",
         "## 1. Decisão de hoje", "",
         f"**Não aprovar FID de nova fermentação agora.** [derivado] Com a demanda do estudo de mercado (cenário base, "
         f"sem contratos públicos), a melhor política é **{lab[best['base'].policy]}**.",
         "",
         f"- Expandir Orindiúva com 1 módulo dá VPL de US$ {f(c.loc[('base', 'A_ORI_1'), 'npv_musd'])} mi.",
         f"- Adiar a expansão em 2 anos dá US$ {f(c.loc[('base', 'A_ORI_DELAY'), 'npv_musd'])} mi.",
         f"- Orindiúva + Tailândia desde o início dá US$ {f(c.loc[('base', 'B_ORI_TH_NOW'), 'npv_musd'])} mi.",
         "",
         f"**Monte Carlo conjunto** (cópula com custos da v3 e premissas de mercado, óleo de peixe compartilhado):",
         "",
         f"- E[VPL] de A = US$ {f(m.loc['A_ORI_1', 'expected_npv_musd'])} mi;",
         f"- P(VPL > 0) = {pct(m.loc['A_ORI_1', 'prob_npv_positive'])};",
         f"- política de maior E[VPL]: **{lab[mc_best.policy]}**.",
         "",
         "Essas probabilidades são **condicionais às distribuições assumidas**, não previsões calibradas.", "",
         "**Primeiro investimento reversível** (custo baixo, preserva a opção):",
         "",
         "1. contrato de açúcar e vapor adicionais com a usina de Orindiúva;",
         "2. engenharia conceitual do módulo (fecha a dúvida sobre quanta capacidade os €50 mi compram);",
         "3. conversão do pipeline de salmão (Noruega/Chile) em contratos com volume e preço.",
         "",
         "Terreno, EPC e FID da Tailândia ficam para depois dos gatilhos da seção 2.", "",
         "## 2. Quando a recomendação muda (gatilhos físicos e monetários)", "",
         f"- **Orindiúva (A) passa a ter VPL ≥ 0** com ≥ **{f(th['A_firm_t'])} t/ano contratadas firmes** desde "
         f"{cfg['contract_start_year']}, sem nenhum pipeline. Com o pipeline ponderado da v3 somado, bastam "
         f"≥ {f(th['A_firm_t_with_pipeline'])} t/ano. [derivado]",
         f"- **A 2ª planta na Tailândia (B) supera só-Orindiúva** com ≥ **{f(th['B_asia_t'])} t/ano de volume asiático "
         f"contratado** no preço-base, ou ≥ {f(th['B_asia_t_price_1_4'])} t/ano com preço 40% maior. "
         "O capex de Orindiúva não move essa fronteira: ele está nas duas políticas e se cancela na diferença. "
         "[derivado]",
         "- **Nakhon Sawan como única planta (em vez de Orindiúva)**: menor preço em que vence, por nível de capex de "
         "Orindiúva (Fonte: `break_even_frontier_lines.csv`):"] + th_lines + [
         f"- **Mercado alto** (todas as premissas favoráveis): o melhor passa a ser **{lab[best['high'].policy]}**, com "
         f"VPL de US$ {f(best['high'].npv_musd)} mi. A Tailândia esperando gatilho de utilização (C') fica próxima: "
         f"US$ {f(c.loc[('high', 'C_ORI_TH_TRIG_UTIL'), 'npv_musd'])} mi. [hipótese de mercado]", "",
         "**Fronteira de contrato asiático por preço e capex** (mínimo para B > A):", "",
         "| Capex Orindiúva | Preço (US$/kg DHA) | Ásia contratada mínima p/ B > A | Ásia mínima p/ Nakhon Sawan sozinha > Orindiúva | Melhor sem contrato |",
         "|---|---|---|---|---|"]
    for x in frl.itertuples():
        L.append(f"| {f(x.capex_ori_musd)} | {f(x.net_price_usd_kg_dha, 1)} | {f(x.min_asia_contract_for_B_gt_A_t) if x.min_asia_contract_for_B_gt_A_t == x.min_asia_contract_for_B_gt_A_t else '> 12.000'} | "
                 f"{f(x.min_asia_contract_for_THalone_gt_A_t) if x.min_asia_contract_for_THalone_gt_A_t == x.min_asia_contract_for_THalone_gt_A_t else '> 12.000'} | {x.best_policy_at_zero_contract} |")
    L += ["", "## 3. Comparação das políticas", "",
          "VPL nominal em USD, com valor terminal; demanda do estudo de mercado ponderada pelos pesos da v3.", "",
          "| Política | Mercado baixo | Mercado base | Mercado alto | E[VPL] MC | p10 | CVaR 10% | P(VPL>0) |",
          "|---|---|---|---|---|---|---|---|"]
    for k in cfg["policies"]:
        L.append(f"| {lab[k]} | {f(c.loc[('low', k), 'npv_musd'])} | **{f(c.loc[('base', k), 'npv_musd'])}** | {f(c.loc[('high', k), 'npv_musd'])} | "
                 f"{f(m.loc[k, 'expected_npv_musd'])} | {f(m.loc[k, 'p10'])} | {f(m.loc[k, 'cvar10_musd'])} | {pct(m.loc[k, 'prob_npv_positive'])} |")
    L += ["",
          f"- **Maior retorno esperado:** {lab[mc_best.policy]}.",
          f"- **Menor perda extrema entre as políticas com capex:** {lab[risk_min.policy]} (CVaR 10% de US$ "
          f"{f(risk_min.cvar10_musd)} mi).",
          "- **Robustez à dependência:** com cópula independente, o E[VPL] de A muda de "
          f"{f(m.loc['A_ORI_1', 'expected_npv_musd'])} para {f(m.loc['A_ORI_1', 'expected_npv_independent'])} US$ mi. "
          + order_msg,
          "- **Escopo do modelo:** a otimização de alocação por região é exata (caminhos mínimos sucessivos, conferidos "
          "com `linprog`). As políticas são comparadas por enumeração auditável, sem MILP, porque o espaço "
          "é pequeno. Ficam fora do modelo: estoque de segurança, múltiplos SKUs, sazonalidade de entressafra e "
          "restrição de usina por mês.", "",
          "## 4. Tamanho da oportunidade por nicho e rota", "",
          "Margem entregue por kg de DHA em 2030 (preço líquido − custo variável do site − frete − trânsito − tarifa):", "",
          "| Destino | Orindiúva | Nakhon Sawan | Origem de maior margem | Inverte se frete BR subir (US$/t) | Inverte se açúcar TH cair (US$/t sacarose) |",
          "|---|---|---|---|---|---|"]
    for x in inv.itertuples():
        L.append(f"| {x.dest_country} · {x.niche} | {f(x.margin_BR_usd_kg_dha, 1)} | {f(x.margin_TH_usd_kg_dha, 1)} | {x.higher_margin_origin} | "
                 f"{f(x.inverts_if_BR_freight_up_usd_t)} | {f(x.inverts_if_TH_sugar_down_usd_t_sucrose)} |")
    L += ["",
          "- **Orindiúva tem a maior margem unitária para todos os destinos, inclusive camarão asiático.** O açúcar mais "
          "caro na Tailândia pesa mais que o frete mais curto. [derivado]",
          "- **O mercado mais próximo não gera automaticamente o maior VPL:** escala, utilização e a infraestrutura "
          "existente em Orindiúva decidem.",
          "- **Teor de DHA:** é o mesmo SKU nas duas plantas, então não altera a escolha da origem.", "",
          "**Carteira por marco** (política A, mercado base):", "",
          "| Ano | Firme | Pipeline qualificado | Potencial | Capacidade | Folga | Top-3 países | Participação top-3 |",
          "|---|---|---|---|---|---|---|---|"]
    for x in compo[(compo.market_scenario == "base") & (compo.policy == "A_ORI_1")].itertuples():
        L.append(f"| {x.year} | {f(x.firm_contracted_t)} | {f(x.qualified_pipeline_t)} | {f(x.unqualified_potential_t)} | {f(x.capacity_t)} | "
                 f"{f(x.capacity_gap_t)} | {x.top3_countries} | {pct(x.top3_country_share)} |")
    L += ["",
          "A concentração aparece por país de formulação. A participação dos três maiores **clientes** é "
          "desconhecida, porque a tonelagem por conta não é pública.", "",
          "## 5. Diversificação: valor sob stress (cenário econômico explícito)", "",
          "| Mercado | Stress | Perda de A | Perda de B | Valor de resiliência (B − A) |", "|---|---|---|---|---|"]
    for (sc, sk), g in st.groupby(["market_scenario", "stress"]):
        g = g.set_index("policy")
        L.append(f"| {sc} | {g.description.iloc[0]} | {f(g.loc['A_ORI_1', 'loss_musd'], 1)} | {f(g.loc['B_ORI_TH_NOW', 'loss_musd'], 1)} | "
                 f"{f(g.resilience_value_B_vs_A_musd.iloc[0], 1)} |")
    L += ["",
          "**Leitura:**",
          "",
          "- No mercado base há capacidade ociosa, então paradas custam pouco e a diversificação vale quase nada.",
          f"- No mercado alto, uma parada de Orindiúva custa até US$ {f(hi_loss)} mi. A segunda planta recupera só uma "
          "parte, porque também opera cheia.",
          "- Esse valor de resiliência é pequeno perto do VPL negativo de construir cedo. **A diversificação não "
          "justifica sozinha a Tailândia.**",
          "- No stress de atraso da Tailândia, o valor positivo no mercado base significa que **atrasar a planta "
          "tailandesa reduz a perda**. Não é um benefício de resiliência.", "",
          "## 6. Sequência de decisões reversíveis e valor de esperar", ""]
    for x in r["option"].itertuples():
        L.append(f"- {x.comparison}: US$ {f(x.value_musd, 1)} mi ({x.reading})")
    L += ["", "**Marcos verificáveis:**",
          "",
          "1. contratos de açúcar e vapor;",
          "2. engenharia conceitual e capex por módulo;",
          f"3. contratos de salmão até ≥ {f(th['A_firm_t'])} t/ano firmes (ou equivalente com pipeline qualificado), "
          "o que leva ao FID de Orindiúva;",
          "4. qualificação de clientes asiáticos e estoque avançado (hub, se o custo for menor que a captura extra);",
          f"5. volume asiático contratado na fronteira (≥ {f(th['B_asia_t'])} t/ano no preço-base), mais diligência de "
          "Nakhon Sawan (terreno, KTIS, água, BOI/GloBE), o que leva ao FID da Tailândia.", "",
          "## 7. Valor de fechar as lacunas (ordem por impacto na decisão e esforço)", "",
          "| Informação | Como fechar | Esforço | Melhor política (min → máx) | Muda a decisão? | Swing do melhor VPL (US$ mi) |",
          "|---|---|---|---|---|---|"]
    for x in dil.itertuples():
        L.append(f"| {x.label} | {x.how_to_close} | {x.effort} | {x.best_policy_low} → {x.best_policy_high} | "
                 f"{'sim' if x.decision_changes else 'não'} | {f(x.swing_best_npv_musd, 1)} |")
    L += ["",
          "Sem probabilidades defensáveis para cada informação, isto é o **valor de fechar a lacuna** (variação do "
          "melhor VPL e mudança de política), não um valor da informação esperado (EVPI).", "",
          "## 8. Correlação e risco: o que é estatística e o que é hipótese", "",
          "- **Séries históricas comparáveis:** não existem no repositório (`empirical_series_status.csv`).",
          "  - O preço do AlgaPrime não é público.",
          "  - Do óleo de peixe há dois pontos conflitantes de 2026.",
          "  - Açúcar e câmbio têm só pontos isolados.",
          "  - Por isso **nenhum coeficiente, beta, R² ou p-valor foi estimado**. A função "
          "`stats.empirical_correlation` exige ≥ 24 observações e trabalha em primeiras diferenças.",
          "- **Mecanismos** (`risk_dependency_register.csv`), separados em:",
          "  - documentados (produção → ração; açúcar → custo; câmbio → custo local);",
          "  - hipóteses plausíveis (óleo de peixe → preço via repasse de 0,4; óleo de peixe → adoção);",
          "  - não identificáveis (efeito líquido do óleo de peixe na demanda de ração; El Niño → cana/água).",
          "- **Monte Carlo:** usa priors transparentes (matriz `joint_correlation_matrix.csv`, PSD verificada) e uma "
          "corrida independente para robustez.",
          "- **Risco no WACC × no fluxo:** o risco-país entra só no WACC; parada, atraso e demanda entram só no fluxo, "
          "sem penalidade dupla.", "",
          "## 9. Por que difere do heatmap original (score de países v2)", "",
          "- **O que o v2 respondia:** \"qual país pontua melhor\". Brasil 7,15 e Tailândia 6,76. Cerca de 65% do peso "
          "vinha de rubricas de um único avaliador, e, sem elas, o Brasil cai para 6º. [derivado na v3]",
          "- **O que este estudo responde:** \"qual combinação de capacidade, origem, carteira e momento cria valor\". "
          "Uma boa nota de país não cria demanda.",
          f"  - Com a demanda bottom-up do estudo de mercado, o volume incremental plausível em 2030 é de ~{f(base_inc_2030)} t "
          "(base, antes dos pesos de probabilidade da v3).",
          "  - Isso é menos que meio módulo de Orindiúva. Por isso **esperar/qualificar** vence construir.",
          "- **O que se mantém do v2:** o Brasil (Orindiúva) é a origem de menor custo e maior margem em todas as rotas. "
          "Quando houver volume, a primeira capacidade deve ser lá.",
          "- **O que muda:** a Tailândia deixa de ser \"2º melhor país\". Passa a ser uma opção condicionada a "
          f"≥ {f(th['B_asia_t'])} t/ano de contratos asiáticos, um volume que o estudo de mercado hoje não sustenta.", "",
          "## 10. Evidência indispensável antes de qualquer FID", "",
          "1. Volume e preço realizados por SKU e mercado (Corbion), para reconciliar o SOM bottom-up "
          "(~US$ 25 mi) com Nutrition (€157 mi).",
          "2. Contratos ou cartas de intenção de offtake com volume, preço e prazo.",
          "3. Capacidade comprada pelos €50 mi e capex por módulo (engenharia).",
          "4. Contrato de açúcar e vapor com a usina e restrição de entressafra.",
          "5. Escopo GACC por planta.",
          "6. Parecer sobre GloBE/BOI.",
          "7. Cotações de frete e EPC.", "",
          "## 11. Integração e rastreabilidade", "",
          "- **Reconciliação** (`integration_reconciliation.csv`):",
          "  - DHA por SKU harmonizado em 0,35;",
          "  - preço de mercado líquido de custos comerciais e rebates (capital de giro na v3);",
          "  - repasse do óleo de peixe aplicado uma única vez;",
          "  - Incoterm tipo DAP;",
          "  - demanda incremental (sem vendas atuais) e sem dupla contagem de clientes.",
          "- **Rotas:** cada uma cita as fontes de preço, custo, frete e tarifa (`route_economics.csv`). As tarifas "
          "estão em 0 e **não verificadas**.",
          "- **Proveniência:** commits, versões, datas de corte e hashes das tabelas consumidas estão em "
          "`run_manifest.json`.", ""]
    (out / "integrated_investment_memo.md").write_text("\n".join(L), encoding="utf-8")
