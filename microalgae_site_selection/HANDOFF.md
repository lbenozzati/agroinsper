# Briefing: nova capacidade de DHA de microalgas (Corbion) – estado da análise

*Atualizado em 2026-10-14 · branch `claude/corbion-dha-site-evaluation-e13c6j` · último commit do código `bbb761e`.*

## 0. Resumo em 30 segundos
- **Decisão condicional de hoje: não aprovar o FID de nova fermentação; esperar e qualificar demanda.**
  - Com a demanda bottom-up do estudo de mercado (cenário base, sem contratos públicos), esperar é a melhor política.
  - VPL em US$ mi: Orindiúva com 1 módulo = −32; Orindiúva adiada 2 anos = −23; Orindiúva + Tailândia já = −227.
- **Gatilhos que mudam a decisão:**
  - **Orindiúva** passa a ter VPL ≥ 0 com ≥ **5.125 t/ano firmes**, ou ≥ 1.250 t/ano contando o pipeline ponderado.
  - **2ª planta na Tailândia** supera ficar só em Orindiúva com ≥ **13.385 t/ano asiáticas contratadas**, ou 9.556 t/ano com preço 40% maior.
- **Mercado alto:** a melhor política é Orindiúva + Tailândia já (VPL 1.036). Tailândia por gatilho de utilização fica perto (1.019).
- **Origem:** Orindiúva tem a maior margem por kg de DHA em **todas** as rotas, inclusive camarão asiático.
- **Diversificação** vale pouco (≤ ~US$ 10 mi nos stresses) e não justifica a Tailândia sozinha.
- **Lacunas que mais movem a decisão:** mercado capturável, preço líquido, offtake e capex do módulo de Orindiúva (o que os €50 mi compram).

## 1. Contexto e objetivo
Apresentação de Private Equity (AgroInsper / Aqua Capital, slide "Investment Thesis: Algae Platform Expansion").

O produto é o AlgaPrime DHA, DHA de microalgas por fermentação heterotrófica com açúcar. A planta atual fica em Orindiúva-SP, ao lado de uma usina de cana.

**A pergunta evoluiu em quatro etapas:**
1. **v2:** em que país construir.
2. **v3 (Prompt 1):** qual sequência de investimento por site maximiza o VPL.
3. **Estudo de mercado (Prompt 2):** onde vender, quanto e a que margem.
4. **Estratégia integrada (Prompt 3):** que combinação de capacidade, origem, carteira de mercados e momento maximiza o valor ajustado a risco.

**Premissas de escopo:**
- Clima tropical não é critério; seus efeitos entram via açúcar, vapor de biomassa, energia e água.
- Países triados: Brasil, Tailândia, China, Vietnã, Índia, Indonésia, Chile e México.

## 2. Mapa do repositório (`microalgae_site_selection/`)
| Pasta | Etapa | Executar | Testes | Entregáveis principais |
|---|---|---|---|---|
| raiz | v2: score de países + custo BR × TH | `python microalgae_site_selection.py`, `python brazil_thailand_economics.py` | 14 | `outputs/` (mapas, ranking, MSP) |
| `v3/` | Prompt 1: localização e retorno | `cd v3 && python -m src run` | 24 (inclui paridade Python × JS) | `investment_memo.md`, `audit_report.md`, `decision_cockpit.html` |
| `market_expansion/` | Prompt 2: mercados | `cd market_expansion && python -m src run [--publish-v3]` | 13 | `market_memo.md`, `market_explorer.html`, `market_demand_scenarios.csv` |
| `integrated_strategy/` | Prompt 3: integração | `cd integrated_strategy && python -m src run` | 12 | `integrated_investment_memo.md`, `integrated_decision_cockpit.html`, slides `concept_1..3` |

**Regras comuns aos módulos:**
- Cada módulo tem `README.md`, `config.yaml`, `data/raw/` (com fonte, vintage, tipo e status de acesso) e `outputs/run_manifest.json` (commit, seed e hashes).
- Os memorandos são gerados a partir dos outputs, sem números digitados à mão.
- Os gráficos seguem o estilo do slide: fundo #0B0630, azul #3987e5, magenta #d55181, violeta #9085e9, prata #B6B3BA, fonte Montserrat (`assets/fonts`).
- Os painéis HTML funcionam offline.

**Dependências entre módulos:**
- A v3 consome a demanda do mercado por `v3/data/raw/market_demand_scenarios.csv`. Sem esse arquivo, usa uma premissa rotulada `ASSUMPTION_DEMAND_V3`.
- O integrado importa os dois motores e não reimplementa nada.

## 3. v2 (base histórica): score de países e custo Brasil × Tailândia
- **Ranking:** Brasil 7,15 > Tailândia 6,76 > China 5,58 > Índia 5,55 > Vietnã 5,32 > México 5,11 > Chile 4,96 > Indonésia 4,80.
- **Custo:** MSP da expansão de Orindiúva ≈ US$ 11,6/kg DHA; Tailândia greenfield com BOI ≈ US$ 14,3/kg DHA.
- **Status:** a v2 está congelada em `v3/data/raw/frozen_v2/` e é reproduzida exatamente por teste. Detalhes no Apêndice A.

## 4. v3 – Prompt 1: localização e retorno da próxima capacidade (`v3/`)
**O que mudou da v2 para a v3:**
- A pergunta passa de "melhor país" para "melhor sequência de investimento por site". O score vira só triagem.
- A capacidade é modular (10 kt nominais, 8.500 t efetivas).
- O açúcar usa rendimento industrial: 5,05 t de açúcar por t de produto (a v2 usava 3,0, rendimento de laboratório).
- O capex é modular, com compartilhamento brownfield explícito.
- Os fluxos estão em USD nominal, com custos locais por PPP mais choque cambial real.
- Os impostos são calculados por entidade:
  - prejuízos fiscais limitados a 30% no Brasil;
  - BOI de 8 anos na Tailândia;
  - top-up GloBE com SBIE;
  - QRTC como cenário.
- A demanda é alocada de forma ótima pela rede de plantas e regiões.
- O Monte Carlo usa cópula gaussiana com correlações declaradas (PSD verificada).
- Saídas: VPL, TIR, MSP, utilização, fronteira de decisão, valor de esperar e stress de resiliência.

**Auditoria forense da v2** (`audit_report.md`, `audit_issues.csv`):
- **1 erro comprovado (AU09):** a v2 aplicava depreciação fiscal sobre fluxos em base real, o que superestimava o benefício fiscal.
- **Comparações inválidas isoladas:**
  - açúcar cristal × branco administrado;
  - tarifa elétrica × custo contratado;
  - estresse hídrico nacional × do site;
  - capex por t de biomassa × por t de óleo;
  - MSP lido como retorno;
  - score de país usado como decisão de site.
- **Hipóteses fracas:**
  - as rubricas de um único avaliador valem ~66% do peso; só com métricas quantitativas, o Brasil cai de 1º para 6º (4,96);
  - Production Economics e Corbion Readiness têm correlação de 0,76 (contagem dupla da integração com a usina).

**Sites** (demanda-premissa da v3, VPL base em US$ mi):
- A1 Orindiúva: 79 (P(VPL > 0) = 88%)
- C Nakhon Sawan: 50
- D Rayong: 26
- B greenfield em Goiás: 25
- G Orindiúva + Tailândia já: −86
- **Custo pleno a 100% de utilização:** US$ 12,9/kg DHA em Orindiúva contra 17,0 em Nakhon Sawan.
- **Vantagem de Orindiúva:** açúcar mais barato, vapor de bagaço e utilidades compartilhadas.

**Leituras da v3:**
- O resultado depende de demanda e preço, não de custo.
- O valor terminal responde por 97 dos 79 US$ mi de A1; sem ele, A1 tem VPL de −17 até 2035.
- A Tailândia só faz sentido com volume asiático contratado (~6.000 t/ano a US$ 30/kg DHA).

**Correção feita no Prompt 3:** a alocação por caminhos mínimos sucessivos podia entrar em loop infinito (ciclo de predecessores causado por ruído numérico nas margens). Foi corrigida em `engine.py` e em `cockpit_engine.js`, com teste de regressão. Os outputs foram regenerados.

## 5. Prompt 2: mercados para expansão e consolidação (`market_expansion/`)
**Escopo:**
- É um estudo independente da fábrica.
- O funil é: ração → TAM (necessidade técnica de DHA) → SAM (espaço servível por DHA de algas) → SOM Corbion → t SKU → receita → contribuição → VPL comercial.
- Os estágios de cultivo são separados.
- DHA e EPA são tratados separadamente (o AlgaPrime supre só DHA).
- Nutrição humana fica fora dos totais.

**Auditoria das afirmações** (`market_claims_audit.csv`):
- **GMI:** US$ 720 mi contra US$ 4,5 bi para o mesmo ano e escopo indefinido. Rejeitado como TAM.
- **Participação de 29,3% da Corbion:** não é dado da Corbion; não foi usada.
- **China:** os 22,6 Mt de ração não são mercado endereçável.
- **BioMar:** "~1 Mt de ração com microalgas" não equivale a volume de AlgaPrime.
- **Veramaris:** contada uma única vez (JV dsm-firmenich + Evonik).

**Resultados** (cenário base):
- **O negócio de ração é, na prática, salmão:** 97% da receita B2B de 2030 (~US$ 52 mi); Noruega e Chile somam 89% do volume incremental.
- **Camarão, China e pet food:** têm TAM grande, mas SAM pequeno.
- **Carteira ótima (MILP):** consolidar Chile, Noruega e Reino Unido em salmão, com VPL comercial de US$ 53,8 mi. Nenhum mercado de expansão tem VPL comercial positivo no base.
- **Volume incremental sobre 2025** (t de SKU/ano):

  | Ano | Base | Faixa |
  |---|---|---|
  | 2028 | 1.797 | 54–10.081 |
  | 2030 | 3.254 | 94–19.083 |
  | 2035 | 5.545 | 137–36.641 |

  Um módulo de 8.500 t efetivas fica ~65% ocupado em 2035.
- **Lacunas que mais movem o valor** (swing em US$ mi):
  - preço líquido por kg DHA: 89;
  - preço do óleo de peixe: 50;
  - participação da Corbion: 46;
  - alvo de EPA+DHA na dieta: 46.
- **Interface com a v3:** exporta `market_demand_scenarios.csv` (+ `_low`, `_high`). O volume contratado é sempre 0, porque não há contrato público.

## 6. Prompt 3: estratégia integrada (`integrated_strategy/`)
**Harmonização** (`integration_reconciliation.csv`):
- DHA de 0,35 por SKU.
- Preço de mercado líquido de custos comerciais e rebates, com capital de giro na v3.
- Repasse do óleo de peixe aplicado uma única vez.
- Incoterm tipo DAP.
- Só demanda incremental, sem dupla contagem de clientes.
- Pesos de status da v3 (A110/A111) para pipeline e potencial; contratado = 0.

Por isso o VPL de Orindiúva no base é −32, contra −9 no teste rápido do Prompt 2. A diferença vem principalmente do preço: o integrado usa o preço de mercado líquido de custos comerciais e rebates, em vez do preço-premissa A040 da v3 (US$ 25/kg DHA × multiplicador regional).

**Políticas** (`config.yaml`), VPL em US$ mi, em três cenários de mercado mais um Monte Carlo conjunto de 400 rodadas:

| Política | Baixo | Base | Alto | E[VPL] MC | P(VPL>0) |
|---|---|---|---|---|---|
| Esperar | 0 | **0** | 0 | 0 | 0% |
| A Orindiúva 1 módulo (2028) | −153 | −32 | 521 | −38 | 26% |
| A' Orindiúva adiada (2030) | −135 | −23 | 439 | −28 | 28% |
| A2 2º módulo por gatilho de utilização | −153 | −32 | 898 | −38 | 25% |
| A2' 2º módulo fixo em 2032 | −280 | −147 | 864 | −162 | 2% |
| B Orindiúva + Tailândia já | −348 | −227 | **1.036** | −255 | 0% |
| B' Tailândia em 2032 | −329 | −208 | 977 | −233 | 0% |
| C Tailândia por gatilho de demanda asiática | −153 | −32 | 521 | −38 | 26% |
| C' Tailândia se Orindiúva ≥ 80% | −153 | −32 | 1.019 | −38 | 25% |
| D Orindiúva + hub asiático | −173 | −48 | 507 | −55 | 19% |

**Rotas** (`route_economics.csv`):
- **Margem em 2030** (US$/kg DHA), Orindiúva contra Nakhon Sawan:
  - salmão: 15,8 contra 12,2;
  - camarão Tailândia: 13,3 contra 10,4;
  - pet food: 19,4 contra 16,0.
- **Inversão da origem:** exigiria frete do Brasil +US$ 1.000–1.240/t ou açúcar tailandês US$ 206–253/t mais barato.

**Fronteiras** (`break_even_frontiers.csv`):
- O capex de Orindiúva não move a fronteira B × A, porque está nas duas políticas e se cancela na diferença.
- Nakhon Sawan sozinha vence Orindiúva só com preço alto: ≥ US$ 35/kg DHA e ≥ 4.000 t asiáticas, com capex de Orindiúva de US$ 92 mi.

**Stress de resiliência:**
- No mercado base há capacidade ociosa, então uma parada de Orindiúva custa pouco.
- No mercado alto, uma parada custa até US$ 36 mi, e a 2ª planta recupera só uma parte, porque também opera cheia.

**Opção de esperar** (Monte Carlo):
- Tailândia por gatilho em vez de já: +217.
- 2º módulo por gatilho em vez de fixo: +124.

**Valor de fechar lacunas** (variação do melhor VPL):

| Lacuna | Swing (US$ mi) |
|---|---|
| Mercado capturável | 1.036 |
| Preço líquido | 29 |
| Offtake | 19 |
| Capex de Orindiúva | 11 |

Rendimento, EPC da Tailândia, frete e prazo de licenciamento não mudam a decisão.

**Estatística:**
- Não há série com ≥ 24 observações, então nenhuma correlação empírica foi estimada.
- O Monte Carlo usa priors declarados (matriz PSD).
- A corrida com riscos independentes muda a ordem das políticas, o que mostra que as correlações importam.

**Sequência reversível:**
1. Contratos de açúcar e vapor com a usina.
2. Engenharia conceitual do módulo.
3. Contratos de salmão até ≥ 5.125 t/ano firmes, o que leva ao FID de Orindiúva.
4. Qualificação de clientes na Ásia e hub, se compensar.
5. ≥ 13.385 t/ano asiáticas contratadas mais diligência de Nakhon Sawan, o que leva ao FID da Tailândia.

**Entregáveis:**
- Gráficos: heatmap origem × destino, Sankey (base A e alto B, 2035), fronteira B × A, superfície de decisão, ponte de VPL, carteira × capacidade e mapa de rotas.
- Slides conceituais:
  - `concept_1_where_to_produce`;
  - `concept_2_where_to_sell`;
  - `concept_3_what_changes_the_decision`.
- Cockpit offline (motor JS da v3), testado contra o Python.

## 7. Limitações (o que mais precisa melhorar)
1. **Sem contratos, preço realizado do AlgaPrime nem dados internos da Corbion.** Toda conclusão é condicional.
   - O SOM bottom-up de ração (~US$ 25–52 mi) ainda não foi reconciliado com a receita de Nutrition (€157 mi em 2024).
2. **Portais primários bloqueados** (Corbion, World Bank, WRI, USDA, IFFO, BioMar, FAO): muitos valores vieram de trechos de busca e estão marcados como `search_snippet`.
3. **Premissas de julgamento:**
   - capacidade comprada pelos €50 mi;
   - capex modular e compartilhamento brownfield;
   - rendimento industrial (0,055–0,10);
   - adoção e participação por mercado;
   - pesos de conversão do pipeline (A110/A111).
4. **Tarifas** todas em 0 e não verificadas. Fretes com cotações parciais.
5. **Correlações** do Monte Carlo são priors, não estimativas. As probabilidades não são calibradas.
6. **GloBE simplificado** por unidade. A combinação jurisdicional e os prejuízos GloBE exigem parecer.
7. **Rubricas da triagem de países:** um único avaliador. Há template para vários avaliadores (`outputs/rubric_ratings_template.csv`).
8. **Diligência pendente:**
   - escopo GACC por planta;
   - contrato de açúcar, vapor e entressafra com a usina;
   - licenciamento CETESB e ONEP/BOI;
   - tier BOI e QRTC;
   - terreno, água e KTIS em Nakhon Sawan;
   - capacidade auditada dos concorrentes chineses.

## 8. Próximos passos sugeridos
- **Dados reais:**
  - substituir premissas por dados da Corbion em `v3/data/raw/assumptions.csv`: rendimento, capex do módulo, preço por SKU e volumes por conta;
  - rodar `market_expansion` com `--publish-v3` e depois `integrated_strategy`.
- **Volume de clientes:** transformar o pipeline de salmão (Noruega, Chile, Reino Unido) em volumes com probabilidade por conta, alimentando `customer_evidence.csv`.
- **Custos externos:** cotar frete, tarifas e EPC; preencher `integrated_strategy/data/raw/tariff_assumptions.csv`.
- **Séries históricas:** coletar ≥ 24 observações (óleo de peixe, açúcar, câmbio, preço de DHA) em `series_inventory.csv` para estimar correlações empíricas.
- **Triagem de países:**
  - testar outros países (EUA/Blair NE, Equador, Peru, Filipinas), hoje marcados como `not_scored`;
  - coletar notas de 2–3 avaliadores.

## 9. Fontes principais
Corbion (site, Annual Report 2024, resultados de 2025, aprovações GACC); BioMar; USDA FAS (Sugar World Markets
mai/2026, GAIN reports); China Feed Industry Association; Alltech Agri-Food Outlook 2026; Sindirações; GPMT; TFMA;
CONAFAB; FAO (SOFIA 2024, AQUASTAT SDG 6.4.2); World Bank (WDI, LPI 2023); Ember/OWID; GlobalPetrolPrices;
CEPEA/ESALQ; Bank of Thailand; IBGE; KPMG/PwC; Thailand BOI; Top-Up Tax Decree B.E. 2567; Lei 15.079/2024;
USTR Special 301 2026; S&P; Damodaran (jan/2026); Federal Reserve (câmbio).
Lista completa com links: seção 10 de `methodology_and_sources.md`.
Mercado (Prompt 2): USDA FAS (Noruega), Sernapesca (via imprensa), Rabobank, FAO GLOBEFISH, IFFO, Aprobal, FEDIAF, Alltech, AAFCO, Mowi, BioMar, Veramaris, Thai Union, IQI, Corbion (FY2025, CMD 2025, H1 2026, GACC, LCA). Lista completa em `market_expansion/outputs/source_registry.csv` e `v3/outputs/evidence_registry.csv`.

## Apêndice A – Detalhe da v2

### A.1 Metodologia v2
Pipeline: dados brutos → nota 0–10 por métrica → subcritério → critério → score ponderado → ranking.

**Normalização**
- Métricas quantitativas: régua fixa de piso e teto (método do IDH),
  nota = 10 × (x − pior) / (melhor − pior), limitada a [0, 10].
  Métricas de tamanho (açúcar, aquafeed) usam escala log.
  Como os limites são fixos, incluir um país não muda a nota dos outros, e um outlier não estica a escala.
- Métricas qualitativas: régua de 5 níveis (0 / 2,5 / 5 / 7,5 / 10) com critérios escritos antes de pontuar
  (seção 5 da metodologia). Representam cerca de 65% do peso efetivo e foram aplicadas por um único avaliador (o analista).
- Valor ausente nunca vira zero: sai do subcritério, os pesos restantes são renormalizados e a falta é sinalizada.
- Data Confidence (0–100), separado do score: confiança × tipo do dado, ponderado pelo peso da métrica.

**Critérios e pesos (Base Case)**
- Production Economics 30%:
  - açúcar 35%
  - energia, renovável e vapor 30%
  - água e efluentes 20%
  - mão de obra e construção 15%
- Market Access 20%:
  - volume de aquafeed 35%
  - espécies premium/intensivas em DHA 30%
  - logística (LPI + distância aos mercados prioritários) 20%
  - proximidade da BioMar e de clientes 15%
- Corbion Industrial Readiness 15%:
  - fábricas existentes 50%
  - talento em fermentação 25%
  - presença comercial 25%
- Regulation & Incentives 15%:
  - aprovações 40% (vender ≠ fabricar)
  - impostos e incentivos 30%
  - comércio e investimento estrangeiro 30%
- Strategic Risk 20% (10 = menor risco):
  - concorrência local e excesso de capacidade 50%
  - risco político, cambial e comercial 40% (rating S&P + rubrica)
  - propriedade intelectual 10% (USTR Special 301)

**Viabilidade (Pass/Review/Fail, antes do ranking; nenhum país é excluído)**
| Condição | Régua |
|---|---|
| Possibilidade legal de produzir e exportar | Review se a nota de licenciamento local for ≤ 2,5 |
| Água e energia em escala industrial | Review se estresse hídrico ≥ 50% ou energia ≥ US$ 0,25/kWh |
| Matéria-prima fermentável | Review se a produção de açúcar for < 1 Mt |
| Logística mínima | Review se o LPI for < 3,0; Fail se < 2,5 |
| Abertura a investimento estrangeiro | Fail se fechado |

**Cenários de peso (PE/MA/CR/RI/SR)**
- Base Case: 30/20/15/15/20
- Lowest-Cost Production: 40/15/20/10/15
- Asian Market Expansion: 25/30/10/15/20

### A.2 Resultados v2
| # | País | Score | PE | MA | CR | RI | SR | Viabilidade |
|---|---|---|---|---|---|---|---|---|
| 1 | Brasil | 7,15 | 8,4 | 4,8 | 9,4 | 5,6 | 7,2 | Pass |
| 2 | Tailândia | 6,76 | 6,6 | 6,2 | 7,5 | 7,3 | 6,6 | Pass |
| 3 | China | 5,58 | 5,7 | 8,4 | 4,4 | 6,7 | 2,6 | Pass |
| 4 | Índia | 5,55 | 6,1 | 6,3 | 3,8 | 4,4 | 6,2 | Review (estresse hídrico 66%) |
| 5 | Vietnã | 5,32 | 5,1 | 7,4 | 1,2 | 6,7 | 5,6 | Pass |
| 6 | México | 5,11 | 4,2 | 3,7 | 5,6 | 5,0 | 7,7 | Review (LPI 2,9, confirmado no World Bank) |
| 7 | Chile | 4,96 | 3,5 | 6,5 | 1,2 | 6,6 | 7,2 | Review (sem açúcar doméstico a partir de 2026/27) |
| 8 | Indonésia | 4,80 | 5,0 | 5,1 | 1,2 | 5,8 | 6,2 | Pass |

- **Cenários:** Brasil em 1º e Tailândia em 2º nos três (robustos). A 3ª vaga alterna entre China, Índia e Vietnã.
- **Monte Carlo** (5.000 rodadas; ruído conforme a confiança de cada dado):
  - P(1º): Brasil 83%, Tailândia 17%.
  - P(top 3): Brasil e Tailândia ~100%, China 46%, Índia 40%, Vietnã 12%.
- **Ponto de virada da tese:** a Tailândia só passa o Brasil se Market Access pesar ≥ 37% (base 20%)
  ou Production Economics ≤ 11% (base 30%).
- **Distância sem viés circular** (o próprio mercado não conta como 0 km): muda pouco (China −0,06).

**Custo e retorno: preço mínimo de venda (MSP), o preço que dá VPL = 0 ao WACC real em USD de cada país**
Unidade de 20 kt/ano de biomassa com ~30% de DHA.
| Caso | Capex | Custo caixa | MSP | Por kg de DHA | WACC real |
|---|---|---|---|---|---|
| Brasil – expansão de Orindiúva | US$ 132 mi | US$ 2.417/t | US$ 3.493/t | ≈ US$ 11,6 | 8,1% |
| Brasil – planta nova | US$ 176 mi | — | US$ 4.130/t | ≈ US$ 13,8 | 8,1% |
| Tailândia – planta nova com BOI | US$ 160 mi | US$ 3.225/t | US$ 4.275/t | ≈ US$ 14,3 | 7,0% |

- **Monte Carlo:** P(expansão no Brasil mais barata que a Tailândia) = 99,9%; P(planta nova no Brasil mais barata que a Tailândia) = 66%.
- **O que explica a diferença:**
  - preço do açúcar (Brasil ~US$ 430/t pelo CEPEA; Tailândia ~US$ 640/t, preço controlado);
  - desconto de capex por ser expansão;
  - fator de localização do capex;
  - açúcar consumido por kg;
  - spread soberano.

  Frete, mão de obra e vapor pesam pouco.
- **Impostos:**
  - Brasil: 34%, mais vazamento estimado de créditos de ICMS/PIS/COFINS.
  - Tailândia: o imposto mínimo global (Pillar Two) limita a isenção do BOI a 15%, porque a Corbion fatura €1.267 mi (> €750 mi).
- **Câmbio:** real a R$ 7,00 aumenta a vantagem do Brasil para US$ 1.116/t; real a R$ 4,20 reduz para US$ 235/t.
  Mais 200 bp de risco-Brasil reduzem para US$ 511/t.

### A.3 Correções da v1 para a v2 (detalhe em `data_change_log.csv`)
- **Açúcar:** uma única fonte para todos (USDA FAS mai/2026, safra 2025/26, raw value).
  Chile = 0 explícito, porque a Iansa encerra o processamento de beterraba nacional em 2026/27.
- **Aquafeed:** volume comercial de 2024–25 para todos, pela hierarquia de fontes:
  associação nacional > USDA > Alltech > derivado.
  - China 22,6 Mt; Vietnã 6,5; Índia 2,89; Brasil 1,9; Indonésia 1,84; Chile 1,29 (estimado pela produção de salmão);
    Tailândia 1,05; México 0,40 Mt.
- **Eletricidade do Brasil:** média 2023–25 (US$ 0,131/kWh), mesma base dos demais.
- **Estresse hídrico:** 2018 para todos (2021+ não acessível).
- **LPI do México:** confirmado 2,9.
- **Concorrência:** Tailândia, Vietnã e Indonésia passaram de 10 para 7,5 (importação chinesa de DHA de algas sem tarifa).

