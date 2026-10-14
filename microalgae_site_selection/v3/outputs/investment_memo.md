# Memorando de investimento: próxima capacidade de DHA de microalgas da Corbion (v3)

*Data de corte: 2026-10-14. Gerado automaticamente a partir dos outputs da execução (commit 69634f9, seed 42, 2000 simulações).*

> **Natureza do resultado.**
> - Não houve acesso a documentos internos da Corbion, contratos ou cotações de EPC e frete.
> - Os sites corbion.com, World Bank, WRI, USDA, IFFO e BioMar estavam bloqueados neste ambiente; as fontes foram lidas por trechos de busca e estão marcadas assim.
> - A demanda usada é **PREMISSA**: não há contratos públicos para a nova capacidade.
> - Os números abaixo são condicionais a `assumptions.csv`. O modelo é executável: quando entrarem dados reais, ele recalcula tudo.

## 1. Resposta curta (decisão condicional de hoje)

1. **Primeiro investimento: expandir Orindiúva em módulo (A1).** É a alternativa de maior VPL no cenário-base (79 US$ mi) e a de menor custo pleno (US$ 12,9/kg DHA a 100% do módulo, contra 17,0 em Nakhon Sawan). A vantagem vem do açúcar mais barato, do vapor de bagaço e das utilidades compartilhadas. Tem também a maior probabilidade de VPL > 0 (88%, condicional às distribuições assumidas). O hub asiático sem fermentação (E) empata na prática: média 62 contra 62 US$ mi, com cauda pior (-33 contra -26).
2. **O que move o resultado é demanda e preço, não custo.** Com a demanda-premissa ponderada, o módulo opera a 36% em 2030 e 75% em 2035.
   - O preço mínimo (VPL = 0) sobe de ~US$ 13 (custo pleno) para US$ 18,3/kg DHA.
   - O VPL depende do valor terminal: VT = 97 US$ mi de um VPL de 79; sem ele, o VPL até 2035 é -17 US$ mi.
   - No cenário stress (só 30% do pipeline qualificado e nada do potencial), o VPL é -74 US$ mi.
3. **Uma segunda planta na Tailândia agora (G) destrói valor** com a demanda atual: ΔVPL G − A1 = -165 US$ mi no cenário-base. Ela só passa a agregar valor com **volume asiático contratado** de cerca de 6.000 t/ano a US$ 30/kg DHA, ou 5.000 t/ano a US$ 35 (capex de Orindiúva = US$ 90 mi).
4. **Sequência recomendada: F (Orindiúva agora; Tailândia só com gatilho).**
   - O gatilho é demanda asiática ≥ 2.500 t/ano em 2029, com contratos firmes.
   - Com a demanda-premissa, o gatilho dispara em 0% das simulações. Por isso F = A1 no caso-base: a opção de esperar não custa nada e preserva o direito de construir quando houver contrato.
   - Sem contrato asiático, Nakhon Sawan sozinha (C) só supera Orindiúva com preço ≥ US$ 32,5/kg DHA. Nesse preço pesam o WACC e a isenção do BOI tailandeses, mais o acesso direto à Ásia.
5. **Antes de um FID, faltam evidências indispensáveis** (seção 7): capacidade comprada pelos €50 mi, rendimento industrial, preço líquido realizado, contratos de offtake, vapor/açúcar adicional da usina e escopo GACC por planta.

## 2. O que mudou da v2 para a v3

| Tema | v2 | v3 |
|---|---|---|
| Pergunta | Melhor **país** (score 0–10) | Melhor **sequência de investimento por site** (VPL), com o score só como triagem |
| Capacidade | 20 kt impostos | Módulo de 10 kt como variável; absorção pela demanda testada |
| Açúcar | 3,0 t/t (rendimento de laboratório) | 5,05 t/t (36% DHA ÷ rendimento industrial 0,075 × recuperação 0,95; faixa 0,055–0,10) |
| Capex brownfield | Fator fixo 0,75 | Modular: fermentação, downstream, utilidades, efluentes, prédios, EPC/owner e contingência; compartilhamento explícito |
| Moeda/inflação | USD real, depreciação real (viés) | USD nominal; custos locais por PPP + choque cambial real; WACC nominal em USD |
| Tributos | Piso de 15% fixo na Tailândia | Ledger por entidade: prejuízos (30% no BR), BOI 8 anos, top-up GloBE com SBIE como chave; QRTC como cenário |
| Demanda | Implícita | `market_demand_scenarios.csv` (contracted / qualified_pipeline / unqualified_potential), alocação ótima por rede |
| Monte Carlo | Ruído por rótulo de confiança, sem correlação | Cópula gaussiana com correlações declaradas (PSD checada) e corrida sem correlação como robustez |
| Decisão | MSP | VPL, TIR, MSP, utilização, breakeven, fronteira de decisão, opção de esperar, stress de resiliência |

## 3. Erros comprovados × lacunas

**Erro comprovado (1):**

- **AU09**: a v2 descontava fluxos reais com depreciação fiscal em base real e superestimava o benefício fiscal. Corrigido com fluxos nominais.

**Comparações inválidas (corrigidas ou isoladas):**

- açúcar cristal × branco administrado, em datas diferentes (AU15);
- tarifa elétrica × custo contratado (AU16);
- estresse hídrico nacional × do site (AU17);
- capex por t de biomassa × óleo/DHA (AU18);
- MSP lido como retorno (AU19);
- TIR do programa CMD × TIR do projeto (AU28);
- definições de aquafeed diferentes entre países (AU14);
- score de país usado como decisão de site (AU05).

**Hipóteses fracas, com destaque:**

- **AU01:** as rubricas de um único avaliador valem 66% do peso. Só com métricas quantitativas, o Brasil cai para 4,96 (atrás de China, Tailândia, Índia, Vietnã e Indonésia).
- **AU03:** Production Economics e Corbion Readiness têm correlação de 0,76 entre os países (contagem dupla da integração com a usina).
- **AU06–AU08:** brownfield, capacidade e rendimento.
- **AU26:** demanda.

## 4. Dois rankings, que não se misturam

**(a) Triagem de países** (`ranking_v3.csv`). O score é filtro de diligência, não VPL.

| País | Score v3 (= v2) | Só quantitativo | P(1º) com pesos incertos | P(top 3) | Gate nacional | Shortlist |
|---|---|---|---|---|---|---|
| Brazil | 7,15 | 4,96 | 89% | 100% | Pass | yes |
| Thailand | 6,76 | 6,30 | 10% | 100% | Pass | yes |
| China | 5,58 | 7,04 | 1% | 50% | Pass | no |
| India | 5,55 | 5,92 | 0% | 33% | Review | no |
| Vietnam | 5,32 | 5,90 | 0% | 5% | Pass | no |
| Mexico | 5,11 | 3,75 | 0% | 11% | Review | no |
| Chile | 4,96 | 4,71 | 0% | 2% | Review | no |
| Indonesia | 4,80 | 5,74 | 0% | 0% | Pass | no |

EUA (Blair NE), Equador, Peru e Filipinas ficam como `not_scored`: os dados não foram coletados, e o motivo e os dados necessários estão listados no CSV.

**(b) Sites por VPL** (cenário-base de demanda, uma unidade, `site_npv_ranking.csv`).

| Site | VPL base (US$ mi) | VPL médio no MC | Gates |
|---|---|---|---|
| BR_ORI_EXP | 79 | 62 | CONDITIONAL |
| TH_NSN | 50 | 20 | CONDITIONAL |
| TH_RYG | 26 | -2 | CONDITIONAL |
| BR_GF_GO | 25 | 6 | CONDITIONAL |

Todos os sites estão **CONDITIONAL**: nenhum gate está em FAIL, mas vários ainda estão NOT_VERIFIED (água outorgável, vapor adicional, licenças, EPC). Nenhum número alto compensa um impedimento legal real.

## 5. Alternativas: intervalos e riscos

VPL nominal em USD, com valor terminal. As colunas p10/p50/p90, P(VPL > 0) e ES10 vêm do Monte Carlo correlacionado (cenário-base), e as probabilidades são **condicionais às distribuições assumidas**.

| Alternativa | VPL stress / **base** / upside | VPL sem VT | TIR base | MSP base (US$/kg DHA) | Utiliz. 2030 / 2035 | p10 / p50 / p90 | P(VPL>0) | ES 10% |
|---|---|---|---|---|---|---|---|---|
| A1 Orindiúva: 1 módulo | -74 / **79** / 171 | -17 | 21,1% | 18,3 | 36% / 75% | -6 / 61 / 131 | 88% | -26 |
| A2 Orindiúva: 2 módulos faseados | -74 / **79** / 171 | -17 | 21,1% | 18,3 | 36% / 75% | -6 / 61 / 131 | 88% | -27 |
| B Greenfield Brasil (GO, ilustrativo) | -125 / **25** / 104 | -51 | 14,7% | 22,7 | 64% / 75% | -59 / 6 / 72 | 54% | -80 |
| C Tailândia: Nakhon Sawan | -125 / **50** / 144 | -47 | 17,4% | 22,0 | 61% / 78% | -66 / 20 / 108 | 61% | -93 |
| D Tailândia: Rayong | -128 / **26** / 110 | -54 | 13,8% | 23,4 | 61% / 78% | -84 / -3 / 84 | 48% | -112 |
| E Orindiúva + hub asiático (sem fermentação) | -87 / **83** / 163 | -21 | 20,8% | 18,7 | 39% / 84% | -12 / 63 / 136 | 86% | -33 |
| F Orindiúva agora + Tailândia se gatilho | -74 / **79** / 171 | -17 | 21,1% | 18,3 | 36% / 75% | -6 / 61 / 131 | 88% | -26 |
| G Orindiúva + Tailândia já | -263 / **-86** / 101 | -126 | 0,1% | 31,2 | 26% / 43% | -209 / -125 / -36 | 4% | -240 |

- **A2** (2º módulo em Orindiúva) e **F** (Tailândia por gatilho) só divergem de A1 quando seus gatilhos disparam. Com a demanda-premissa, isso quase nunca acontece: A2 em 0% e F em 0% das simulações.
- **DSCR:** não se aplica, porque o modelo assume financiamento corporativo, sem dívida de projeto.
- **Robustez à dependência:** sem correlações, o VPL médio de A1 vai de 62 para 62 US$ mi; a ordem das alternativas por VPL médio se mantém.

## 6. Pontos de virada (o que inverte a decisão)

- **Tornado do VPL de A1:**
  Preço líquido (USD/kg DHA): -43 → 311; Multiplicador de demanda: -22 → 149; Capex greenfield (USD/t·ano): 114 → 20; WACC Brasil: 120 → 43; Rendimento DHA/açúcar: 55 → 95.
- **Tornado de ΔVPL (C Tailândia − A1):**
  Preço líquido (USD/kg DHA): -81 → 67; WACC Brasil: -70 → 7; Açúcar Tailândia (USD/t): -2 → -64; Rendimento DHA/açúcar: -56 → -11; Açúcar Brasil (USD/t): -41 → -3.
  Premissas que, sozinhas no extremo da faixa, invertem o sinal (Tailândia passa Orindiúva): Preço líquido (USD/kg DHA), WACC Brasil.
- **Fronteira da 2ª unidade** (`decision_frontier.csv` e `decision_frontier.png`), volume asiático contratado a partir do qual G − A1 > 0:

| Preço líquido | US$ 25/kg DHA | US$ 30 | US$ 35 |
|---|---|---|---|
| Volume asiático contratado mínimo para G − A1 > 0 | 8.000 t/ano | 6.000 t/ano | 5.000 t/ano |

O capex de Orindiúva **não move** essa fronteira, porque está nas duas alternativas e se cancela na diferença. Ele importa na outra escolha: **qual site recebe a única unidade**. Preço mínimo a partir do qual Nakhon Sawan sozinha (C) supera Orindiúva (A1):

| Capex Orindiúva (US$ mi) | sem contrato asiático | 3.000 t asiáticas contratadas | 6.000 t |
|---|---|---|---|
| 60 | US$ 40,0 | US$ 35,0 | US$ 40,0 |
| 90 | US$ 32,5 | US$ 30,0 | US$ 32,5 |
| 120 | US$ 25,0 | US$ 25,0 | US$ 27,5 |

- **Resiliência:** com demanda alta (upside), uma parada de 6 meses do módulo incremental em 2031 tira 2.196 t de vendas e 4,4 US$ mi de VPL de A1. Com demanda base, a capacidade ociosa absorve a parada. O valor de diversificar (Tailândia cobrindo clientes atuais de Orindiúva) aparece só como limite superior de cenário em `resilience_stress.csv`, sem prêmio somado ao VPL.

## 7. Lacunas que impedem o investimento (ordem de impacto na decisão)

1. **Preço líquido realizado por SKU e mercado** (A040). É o maior swing nos dois tornados; não há preço público do AlgaPrime e as leituras do óleo de peixe em 2026 conflitam (S015).
2. **Offtake contratado e pipeline qualificado** (`market_demand_scenarios.csv`, a ser substituído pelo estudo de mercado, Prompt 2).
3. **Capacidade comprada pelos €50 mi** e capex por módulo (cotação de EPC); ver `eur50m_implied_capacity_sensitivity.csv`.
4. **Rendimento industrial** de DHA sobre açúcar, OEE e teor de DHA por lote (dados de operação de Orindiúva).
5. **Usina vizinha:** contrato de açúcar (especificação, VHP/caldo, entressafra) e vapor/energia adicionais. Define o fator de utilidades compartilhadas.
6. **Escopo GACC** por SKU e por planta; registro de um novo estabelecimento.
7. **Tributário:** parecer sobre o top-up GloBE na Tailândia (combinação com Rayong, SBIE), tier do BOI e QRTC; vazamento de créditos no Brasil.
8. **Site:** outorga de água e Aqueduct por sub-bacia; licenças CETESB/ONEP; prazos.
9. **Cotações de frete** por SKU e prazos de entrega (a captura da Ásia a partir do Brasil, 70%, é julgamento).

## 8. Gatilhos e marcos verificáveis (sequência reversível)

1. **Agora:** contrato de açúcar e vapor adicionais com a usina; engenharia conceitual do módulo em Orindiúva; consulta prévia à CETESB.
2. **FID de A1:** contratos ou pipeline qualificado cobrindo pelo menos o breakeven (≈ 60% da demanda-base ponderada) e preço ≥ US$ 18,3/kg DHA.
3. **Em paralelo e barato:** qualificação de clientes asiáticos e estoque avançado / hub (E), testando a captura da Ásia antes de construir na Ásia.
4. **Gatilho da Tailândia (2029):** demanda asiática contratada no nível da fronteira (tabela da seção 6); diligência de Nakhon Sawan (terreno no estate do IEAT, contrato KTIS, água, BOI/GloBE); depois, FID.
5. **Segundo módulo em Orindiúva:** utilização de A1 ≥ 80% no ano de decisão, com vapor da usina ou caldeira nova orçada.

## 9. Como executar

```bash
cd microalgae_site_selection/v3
pip install -r requirements.txt
python -m src run              # tudo: outputs/, painel, memorando (≈1–2 min)
python -m src run --mc-sims 300 --no-charts   # rápido
python -m pytest -q tests
```

Para usar a demanda do estudo de mercado, substitua `data/raw/market_demand_scenarios.csv` (mesmo esquema) e rode de novo.
Para usar dados da Corbion, edite `data/raw/assumptions.csv` (base/low/high e source_id).

**Principais saídas** (`outputs/`):

- **Painel interativo:** `decision_cockpit.html` (abre offline).
- **Relatórios:** `investment_memo.md`, `audit_report.md`, `audit_issues.csv`.
- **Fontes e premissas:** `evidence_registry.csv`, `assumptions.csv`, `source_gaps.csv`.
- **Sites e economia:** `site_candidates.csv`, `unit_economics.csv`, `cashflow_by_scenario.csv`, `npv_by_scenario.csv`.
- **Decisão e ranking:** `decision_frontier.csv`, `ranking_v3.csv`, `monte_carlo_summary.csv`.
- **Gráficos:** `cost_per_kg_dha_waterfall.png`, `tornado.png`, `decision_frontier.png`, `risk_return_matrix.png`, `npv_ranges.png`, `site_map.png`.
