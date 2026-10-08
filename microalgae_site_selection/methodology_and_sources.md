# Metodologia e fontes: localização de nova unidade de DHA de microalgas (Corbion)

*Versão 2.0 · dados acessados em 07–08/10/2026 · gerado com `microalgae_site_selection.py` e `brazil_thailand_economics.py`*

> **Status dos resultados.** O ranking abaixo é real no sentido de que todo número sai do arquivo
> `raw_country_data.csv` por fórmula reprodutível. Porém **cerca de 65% do peso do score vem de
> notas qualitativas de analista** (rubricas abaixo) e várias séries quantitativas foram obtidas de
> fontes secundárias, porque os portais institucionais (World Bank API, FAO, OECD, Corbion.com) não
> puderam ser acessados diretamente neste ambiente. Use o resultado como **triagem estruturada para
> discussão**, não como decisão de investimento. A seção 9 lista o que precisa de diligência.

## 0. O que mudou na versão 2

| Tema | v1 | v2 |
|---|---|---|
| Aquafeed | Definições e anos misturados (2014–2025, capacidade no Chile) | Volume comercial de ração aquícola 2024–2025 para todos; hierarquia de fontes: associação nacional > USDA > Alltech > derivado. Tailândia 0,41 → 1,05 Mt (TFMA); Indonésia 3,25 → 1,84 Mt (GPMT); México 0,18 → 0,40 Mt (CONAFAB); Chile 1,5 Mt de capacidade → 1,29 Mt estimado pela produção |
| Açúcar | USDA mai/2025; Indonésia em açúcar branco; Vietnã de fonte secundária; Chile ausente | Uma única fonte: USDA mai/2026, safra 2025/26, raw value. Chile = **0 explícito** a partir de 2026/27 (a Iansa encerrou a compra de beterraba) |
| Eletricidade do Brasil | Snapshot dez/2025 (0,159) | Média 2023–25 (0,131), mesma base dos demais |
| Estresse hídrico | 2018 para sete países e 2021 para o Brasil | 2018 para todos (série 2021+ inacessível para os oito) |
| LPI do México | 2,9 (fonte secundária) | 2,9 **confirmado** na tabela do World Bank (rank 66). O valor 3,0 é uma subdimensão. A flag Review se mantém |
| Concorrência | 10 para todos os países sem produtor local | Regra aplicada a todos: Tailândia, Vietnã e Indonésia vão para 7,5 (importações chinesas com tarifa zero via ACFTA/RCEP; na Tailândia há só pesquisa no BIOTEC). Brasil e México continuam em 10 |
| Distância | Mercado doméstico = 0 km (viés circular para China, Vietnã e Chile) | `export_only`: só os mercados prioritários de exportação; a versão anterior roda como comparação |
| Rubricas | Um avaliador | Suporte a vários avaliadores (`rubric_ratings.csv`): mediana, concordância exata, ±1 nível e alfa de Krippendorff |
| Incerteza | Só cenários de peso | + Monte Carlo sobre os dados (v1 vs v2), ponto de virada da tese e módulo de custo e retorno Brasil vs Tailândia |

Todas as alterações estão em `data_change_log.csv`; os dados v1 estão preservados em `archive/raw_country_data_v1.csv`.

---

## 1. Escopo e lógica industrial

- **Tecnologia:** fermentação heterotrófica em tanques fechados (AlgaPrime DHA). A alga consome
  açúcar vegetal, não luz. Por isso **"clima tropical" não é critério**: seus efeitos entram apenas
  via açúcar competitivo, biomassa/vapor, energia renovável e água.
- **Referência:** a planta de Orindiúva (SP), ao lado de uma usina de cana, com açúcar, vapor e
  energia de bagaço.
- **Mercados-alvo:** aquicultura (prioridade: China, Chile e Vietnã), ração animal, pet food e,
  potencialmente, nutrição humana.
- **Países:** Brasil, Tailândia, China, Vietnã, Índia, Indonésia, Chile e México. Para incluir outro
  país, basta adicionar linhas ao CSV (modelo em `outputs/country_data_template.csv`).

## 2. Pipeline (camadas separadas e auditáveis)

| Camada | Função | Arquivo de saída |
|---|---|---|
| Dados brutos | `load_country_data()` + `validate_input_data()` | `raw_country_data.csv`, `outputs/data_quality_report.csv` |
| Métrica derivada | `add_derived_metrics()` (distância aos mercados prioritários) | `outputs/metric_scores.csv` |
| Normalização 0–10 | `normalize_metric()` / `score_metrics()` | `outputs/metric_scores.csv` |
| Subcritérios | `calculate_subcriterion_scores()` | `outputs/subcriterion_scores.csv` |
| Critérios | `calculate_criterion_scores()` | `outputs/country_scores.csv` |
| Score ponderado e ranking | `calculate_country_score()`, `rank_scores()` | `outputs/country_scores.csv` |
| Confiança dos dados | `calculate_data_confidence()` | `outputs/country_scores.csv` |
| Viabilidade | `assess_viability()` | `outputs/country_scores.csv` |
| Sensibilidade | `run_sensitivity_analysis()` | `outputs/sensitivity_analysis.csv` |

**Fórmula (Base Case):**
`Score = 0,30·PE + 0,20·MA + 0,15·CR + 0,15·RI + 0,20·SR`, com cada critério de 0 a 10.

**Validações automáticas** (o script para com erro se alguma falhar): pesos de cenário somam 100%;
subpesos de cada critério somam 100%; pesos das métricas dentro de cada subcritério somam 100%;
notas qualitativas estão em {0; 2,5; 5; 7,5; 10}; valores quantitativos dentro de faixas plausíveis;
nenhum par país/métrica duplicado; nenhum país com dois códigos ISO (ou ISO com dois nomes); valores
ausentes precisam estar marcados como `missing` e **nunca são convertidos em zero**.

## 3. Critérios, subcritérios e métricas

Peso efetivo = peso do critério × peso do subcritério × peso da métrica (Base Case).

| Critério (peso) | Subcritério (peso) | Métrica | Tipo / direção | Normalização (pior → melhor) | Peso efetivo |
|---|---|---|---|---|---|
| **Production Economics (30%)** | Açúcar/glicose (35%) | Produção doméstica de açúcar, Mt | Quant., maior = melhor | log: 0,5 → 40 Mt | 5,25% |
| | | Posição de custo do açúcar | Rubrica | 0–10 | 5,25% |
| | Energia e vapor (30%) | Preço de eletricidade empresarial, USD/kWh | Quant., menor = melhor | linear: 0,25 → 0,06 | 3,6% |
| | | Participação renovável na geração, % | Quant., maior = melhor | linear: 10 → 90% | 2,7% |
| | | Vapor/cogeração com biomassa | Rubrica | 0–10 | 2,7% |
| | Água e efluentes (20%) | Estresse hídrico SDG 6.4.2, % | Quant., menor = melhor | linear: 80 → 5% | 3,0% |
| | | Infraestrutura de água industrial e efluentes | Rubrica | 0–10 | 3,0% |
| | Mão de obra e construção (15%) | PIB per capita, USD (proxy de salário) | Proxy, menor = melhor | linear: 18.000 → 2.000 | 2,7% |
| | | Capacidade de EPC/construção | Rubrica | 0–10 | 1,8% |
| **Market Access (20%)** | Mercado de aquafeed (35%) | Volume de ração aquícola, Mt | Quant., maior = melhor | log: 0,1 → 25 Mt | 7,0% |
| | Espécies premium (30%) | Presença de espécies intensivas em DHA | Rubrica | 0–10 | 6,0% |
| | Portos e frete (20%) | LPI 2023 do World Bank | Quant., maior = melhor | linear: 2,5 → 4,0 | 2,0% |
| | | Distância média a Xangai, HCMC e Puerto Montt, km (derivada) | Proxy, menor = melhor | linear: 15.000 → 3.000 | 2,0% |
| | BioMar e clientes (15%) | Proximidade da BioMar e de clientes | Rubrica | 0–10 | 3,0% |
| **Corbion Industrial Readiness (15%)** | Plantas, terreno e utilidades (50%) | Manufatura Corbion existente | Rubrica | 0–10 | 7,5% |
| | Pessoal técnico/fermentação (25%) | Talento em fermentação | Rubrica | 0–10 | 3,75% |
| | Escritórios/inovação/suporte (25%) | Presença comercial e de inovação | Rubrica | 0–10 | 3,75% |
| **Regulation & Incentives (15%)** | Aprovações (40%) | Aprovação para VENDER o produto | Rubrica | 0–10 | 3,6% |
| | | Viabilidade de CONSTRUIR/OPERAR localmente | Rubrica | 0–10 | 2,4% |
| | Tributos e incentivos (30%) | Alíquota estatutária de IR corporativo, % | Quant., menor = melhor | linear: 35 → 15% | 2,25% |
| | | Incentivos ao investimento | Rubrica | 0–10 | 2,25% |
| | Comércio e IED (30%) | Acordos comerciais e abertura a IED | Rubrica | 0–10 | 4,5% |
| **Strategic Risk (20%)** *(10 = menor risco)* | Concorrência/excesso de capacidade (50%) | Concorrência local em DHA de algas | Rubrica | 0–10 | 10,0% |
| | Proteção de PI (10%) | Status no USTR Special 301 (2026) | Rubrica | 0–10 | 2,0% |
| | Risco político, cambial e comercial (40%) | Rating soberano S&P (notch, 1 = AAA) | Quant., menor = melhor | linear: 16 (B-) → 4 (AA-) | 4,0% |
| | | Risco político e de política comercial | Rubrica | 0–10 | 4,0% |

## 4. Normalização

- **Goalposts fixos (método do IDH/PNUD).** `nota = 10 × (x − pior) / (melhor − pior)`, limitada a
  [0, 10]. A direção vem da ordem dos goalposts. Como os limites são fixos, **incluir um país não
  altera a nota dos demais**, e um outlier não estica a escala: acima do goalpost "melhor" a nota
  satura em 10.
- **Escala log** para variáveis de tamanho (produção de açúcar e volume de aquafeed), que variam em
  ordens de grandeza. Assim a China (22,6 Mt de aquafeed) recebe 9,8, mas não comprime todos os outros
  para perto de zero, como faria um min-max linear.
- **Rubricas qualitativas:** a nota é o próprio nível (0; 2,5; 5; 7,5; 10). O CSV registra a
  justificativa e a fonte.
- Os valores brutos permanecem intactos no `metric_scores.csv`, ao lado da nota normalizada.

## 5. Rubricas qualitativas (critérios objetivos)

Escala geral: 0 = Highly unfavorable · 2,5 = Unfavorable · 5 = Neutral or mixed · 7,5 = Favorable · 10 = Highly favorable.

| Métrica | 10 | 7,5 | 5 | 2,5 | 0 |
|---|---|---|---|---|---|
| Custo do açúcar | Exportador de baixo custo, preço doméstico ≈ paridade internacional, sem restrições | Exportador com preço próximo da paridade, atritos regulatórios menores | Autossuficiente ou misto; preço administrado ou restrições de exportação | Importador líquido ou mercado protegido com prêmio relevante; ou sem base doméstica, mas com importação aberta | Sem matéria-prima viável |
| Vapor/biomassa | Cogeração com bagaço disponível e generalizada na região canavieira | Cogeração disponível e/ou vapor centralizado em parques | Caldeiras próprias a carvão, gás ou biomassa | Sem cogeração; biomassa limitada | Sem vapor viável |
| Água e efluentes | — | Parques industriais com água e ETE centralizadas e confiáveis | Depende do site; desempenho heterogêneo | Infraestrutura fraca | Inviável |
| EPC/construção | Maior base de EPC em fermentação, custo baixo | Base estabelecida em bioprocessos, custo moderado | EPC industrial geral; pouca experiência em fermentação aeróbia | Limitada e cara | — |
| Espécies premium | Salmonídeos (maior inclusão de DHA) dominantes | Grande setor de camarão/peixe marinho de exportação | Predomínio de tilápia/água doce, com algum camarão | Baixo uso de ração | Sem aquicultura com ração |
| BioMar/clientes | Fábrica BioMar no país | Sem BioMar, mas com adoção comercial documentada de AlgaPrime por grande cliente local | BioMar atende a partir de país vizinho, ou há ≥ 2 grandes fabricantes globais de ração | Indústria local sem vínculo | Desprezível |
| Manufatura Corbion | Planta de algas em operação | Planta de fermentação (não algas) | Outra manufatura | Só entidade comercial/trading ou unidade pequena não confirmada | Nenhuma |
| Talento em fermentação | Equipe Corbion de algas + ecossistema profundo | Equipe Corbion de fermentação ou o maior ecossistema global | Ecossistema relevante (pharma/enzimas) | Pequeno | — |
| Presença comercial/inovação | HQ regional + centro de inovação em algas | Escritório + laboratório de aplicação | Escritório/entidade de vendas | Apenas distribuidor/agente | Nenhuma |
| Aprovação para vender | Produzido e registrado localmente | Registro/uso comercial documentado | Uso provável, sem registro público encontrado | Nenhum registro encontrado | Proibido |
| Construir/operar | Site licenciado em operação | Site Corbion licenciado + licença adicional de ração | IED aberto, licenciamento padrão | Licenciamento desfavorável | Sem rota legal |
| Incentivos | Isenção de IR de 8 anos ou mais (ex.: BOI) | Alíquota reduzida longa ou tax holiday disponível | Incentivos parciais | Poucos | Nenhum |
| Comércio e IED | Rede de acordos com China, Vietnã e Chile + CPTPP/RCEP; IED aberto | RCEP/ASEAN-China + acordo com Chile | Cobertura parcial | Sem acordos com os mercados prioritários; TEC alta | IED fechado |
| Concorrência local | Nenhum produtor local de DHA de algas, nem projetos anunciados | Sem produtor comercial, mas com pilotos ou forte concorrência importada | Um produtor local | Vários produtores locais | ≥ 3 produtores locais com expansões **e** histórico de excesso de capacidade em cadeias análogas |
| PI (USTR 2026) | Não listado | — | Watch List | Priority Watch List | Priority Foreign Country |
| Risco político/comercial | — | Instituições fortes, baixo risco | Risco misto | Risco geopolítico/comercial elevado para empresa estrangeira | — |

### Controle de dupla contagem

- A **planta de Orindiúva** entra só em *Readiness* (ativos e equipe). Em *Production Economics*, o
  Brasil é avaliado no nível do país (açúcar, bagaço, energia), não pelo site da Corbion.
- As **aprovações GACC na China** entram só em *Regulation* (aprovação para vender). A concorrência
  chinesa entra só em *Strategic Risk*.
- A **adoção de AlgaPrime pela Thai Union (Tailândia)** e o **uso em salmão no Chile** aparecem em
  duas métricas, cada uma avaliando uma dimensão diferente: em *Market Access* medem a base de
  clientes; em *Regulation* evidenciam que o uso do produto é legal. Isso está registrado nas notas
  do CSV.
- O **rating soberano** (risco macro e cambial) e a **rubrica política/comercial** (geopolítica,
  tarifas, imprevisibilidade regulatória) foram definidos para não se sobrepor. A instabilidade de
  regras de comércio fica na rubrica política, não em *Comércio e IED*, que avalia apenas a cobertura
  de acordos e a abertura a IED.

## 6. Valores ausentes e Data Confidence

- **Ausente ≠ zero.** Uma métrica ausente sai do seu subcritério, os pesos restantes são
  renormalizados e a lacuna aparece em `missing_metrics`. Caso atual: produção de açúcar do Chile.
- **Data Confidence (0–100)** não altera o score. Cada métrica soma pontos de confiança (High 1,0 /
  Medium 0,67 / Low 0,33) multiplicados por um fator de tipo (reported 1,0 / estimate 0,85 / proxy
  0,7 / missing 0), ponderados pelo peso efetivo no Base Case. Todas as rubricas de analista são do
  tipo `estimate`, por isso nenhum país passa de cerca de 85.
- `share_of_score_low_confidence_pct` mostra a parcela do score apoiada em dados de baixa confiança
  ou ausentes.

## 7. Viability flags (triagem antes do ranking; nenhum país é excluído)

| Condição | Fail | Review |
|---|---|---|
| Possibilidade jurídica de produzir/exportar | Permissão local = 0 | Permissão local ≤ 2,5 |
| Água e energia em escala industrial | Estresse hídrico ≥ 100% | Estresse ≥ 50%, dado ausente ou eletricidade ≥ 0,25 USD/kWh |
| Matéria-prima fermentável | Custo de açúcar = 0 | Produção doméstica < 1 Mt ou ausente |
| Infraestrutura logística mínima | LPI < 2,5 ou ausente | LPI < 3,0 |
| Investimento estrangeiro | Comércio/IED = 0 | — |

## 8. Resultados (v2)

### 8.1 Ranking Base Case

| # | País | Score | PE | MA | CR | RI | SR* | Viabilidade | Data conf. | % do score com baixa confiança |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Brazil | **7,15** | 8,4 | 4,8 | 9,4 | 5,6 | 7,2 | Pass | 64 | 8% |
| 2 | Thailand | **6,76** | 6,6 | 6,2 | 7,5 | 7,3 | 6,6 | Pass | 60 | 15% |
| 3 | China | **5,58** | 5,7 | 8,4 | 4,4 | 6,7 | 2,6 | Pass | 70 | 0% |
| 4 | India | 5,55 | 6,1 | 6,3 | 3,8 | 4,4 | 6,2 | Review (estresse hídrico 66%) | 55 | 28% |
| 5 | Vietnam | 5,32 | 5,1 | 7,4 | 1,2 | 6,7 | 5,6 | Pass | 53 | 36% |
| 6 | Mexico | 5,11 | 4,2 | 3,7 | 5,6 | 5,0 | 7,7 | Review (LPI 2,9) | 59 | 21% |
| 7 | Chile | 4,96 | 3,5 | 6,5 | 1,2 | 6,6 | 7,2 | Review (sem base doméstica de açúcar) | 56 | 24% |
| 8 | Indonesia | 4,80 | 5,0 | 5,1 | 1,2 | 5,8 | 6,2 | Pass | 54 | 30% |

\*SR: 10 = menor risco estratégico. v1 → v2: Brasil +0,07; Tailândia −0,12 (concorrência importada);
Vietnã −0,30; Indonésia −0,32; Chile −0,20 (açúcar = 0); México +0,10.

### 8.2 Sensibilidade aos pesos

| País | Base Case | Lowest-Cost Production | Asian Market Expansion | Melhor/pior posição | Variação do score | No top 3 |
|---|---|---|---|---|---|---|
| Brazil | 7,15 (#1) | 7,58 (#1) | 6,74 (#1) | 1 / 1 | 0,85 | 3 de 3, **robusto** |
| Thailand | 6,76 (#2) | 6,80 (#2) | 6,68 (#2) | 2 / 2 | 0,12 | 3 de 3, **robusto** |
| China | 5,58 (#3) | 5,49 (#4) | 5,91 (#3) | 3 / 4 | 0,42 | 2 de 3 |
| India | 5,55 (#4) | 5,50 (#3) | 5,69 (#5) | 3 / 5 | 0,19 | 1 de 3 |
| Vietnam | 5,32 (#5) | 4,91 (#6) | 5,73 (#4) | 4 / 6 | 0,82 | 0 de 3 |
| Mexico | 5,11 (#6) | 4,99 (#5) | 4,99 (#8) | 5 / 8 | 0,12 | 0 de 3 |
| Chile | 4,96 (#7) | 4,36 (#8) | 5,36 (#6) | 6 / 8 | 1,00 | 0 de 3 |
| Indonesia | 4,80 (#8) | 4,51 (#7) | 5,00 (#7) | 7 / 8 | 0,48 | 0 de 3 |

### 8.3 Tese: em que peso a Tailândia passa o Brasil

Os demais pesos são reescalados proporcionalmente a partir do Base Case (`thesis_breakeven.csv`).
- **Market Access ≥ 37%** (Base Case 20%; cenário asiático 30%): a Tailândia empata com o Brasil.
- **Production Economics ≤ 11%** (Base Case 30%): idem.

Ou seja, só uma tese explicitamente "Ásia acima de tudo" inverte a ordem. Com os pesos definidos
pelo comitê, o Brasil fica em 1º em todos os cenários testados.

### 8.4 Monte Carlo sobre os dados (5.000 rodadas, pesos do Base Case)

As métricas variam conforme a confiança. Valores quantitativos recebem ruído lognormal de σ 5%,
15% ou 30% (High, Medium, Low). Rubricas sobem ou descem um nível com probabilidade de 10%, 25% ou 40%.

| País | P(1º) v1 | P(1º) v2 | P(top 3) v1 | P(top 3) v2 | Score médio v2 (P5–P95) |
|---|---|---|---|---|---|
| Brazil | 71% | **83%** | 100% | 100% | 7,05 (6,70–7,36) |
| Thailand | 29% | 17% | 100% | 100% | 6,75 (6,32–7,18) |
| China | 0% | 0% | 39% | **46%** | 5,59 (5,27–5,92) |
| India | 0% | 0% | 31% | **40%** | 5,55 (5,09–6,02) |
| Vietnam | 0% | 0% | 28% | **12%** | 5,32 (4,90–5,76) |
| Mexico | 0% | 0% | 0% | 1% | 5,06 |
| Chile | 0% | 0% | 2% | 0% | 4,95 |
| Indonesia | 0% | 0% | 0% | 0% | 4,82 |

A correção dos dados reforçou Brasil e Tailândia e reduziu o Vietnã. A 3ª vaga segue indefinida
entre China (46%) e Índia (40%). O teste de distância sem viés circular quase não muda o ranking:
a China perde 0,06 e o Chile 0,05 (`distance_mode_comparison.csv`).

### 8.5 Custo e retorno: Brasil vs Tailândia (`brazil_thailand_economics.py`)

Métrica: **preço mínimo de venda (MSP)**, o preço do produto que dá VPL = 0 ao WACC real em USD de
cada país. Não se assume preço de mercado. A unidade tem 20 kt/ano de biomassa com cerca de 30% de DHA.

| Caso | Capex | Custo caixa/t | MSP/t | MSP por kg DHA | WACC real |
|---|---|---|---|---|---|
| Brasil – expansão de Orindiúva | US$ 132 mi | US$ 2.417 | **US$ 3.493** | US$ 11,6 | 8,1% |
| Brasil – greenfield | US$ 176 mi | US$ 2.702 | US$ 4.130 | US$ 13,8 | 8,1% |
| Tailândia – greenfield (BOI) | US$ 160 mi | US$ 3.225 | US$ 4.275 | US$ 14,3 | 7,0% |

- **O que explica a diferença** (tornado de MSP Tailândia − Brasil, base +US$ 783/t):
  - preço do açúcar (+409 a +1.150);
  - fator brownfield (+507 a +1.058);
  - fator de localização do capex;
  - consumo de açúcar por kg;
  - spread soberano.

  Frete, mão de obra e vapor movem a diferença em menos de US$ 160/t.
- **Monte Carlo (5.000 rodadas):** P(expansão Brasil mais barata que Tailândia) = **99,9%**.
  P(Brasil greenfield mais barato que Tailândia) = **66%**. Ou seja, a vantagem do Brasil vem
  principalmente de ser **expansão**; numa comparação greenfield contra greenfield, o resultado é
  quase empate.
- **Câmbio e risco-país (`economics_scenarios.csv`):**
  - Real −25% (R$ 7,00): diferença sobe para +1.116.
  - Real +25% (R$ 4,20): diferença cai para +235.
  - Baht ±10%: diferença vai de +549 a +1.069.
  - Risco-Brasil +200 bp: diferença cai para +511.
  - Açúcar tailandês a 25 THB/kg: diferença sobe para +1.153.
  - Açúcar brasileiro a US$ 550/t: diferença cai para +409.
- **Impostos efetivos:**
  - **Brasil:** 34% (o Pillar Two não muda nada, porque a alíquota já é maior que 15%). Há ainda um
    vazamento estimado de 1,5% dos custos em créditos de ICMS/PIS/COFINS não recuperados. A
    reforma tributária (CBS/IBS a partir de 2027, com imunidade às exportações) deve reduzir esse
    vazamento.
  - **Tailândia:** a isenção BOI de 8 anos fica limitada a **15% pelo Pillar Two**. A Corbion fatura
    €1.267 mi, acima do limite de €750 mi, e o Decreto de Top-Up Tax vigora desde 2025. O crédito
    reembolsável (QRTC) proposto pelo BOI devolveria esse benefício.
  - O efeito no MSP é pequeno: cerca de US$ 30/t entre isenção plena e piso de 15%.
- **Limitação:** o capex por tonelada, os coeficientes de processo (açúcar, energia e vapor por
  kg), o quadro de pessoal e os fatores de localização e brownfield são **premissas**, marcadas
  como tal. Os valores absolutos de MSP são indicativos; a **diferença** entre os países é mais
  robusta, porque as premissas de processo são compartilhadas.

## 9. Limitações e diligência necessária

1. **Rubricas:** respondem por 65,5% do peso efetivo. A estrutura para vários avaliadores existe
   (`outputs/rubric_ratings_template.csv`). Falta coletar as notas da Corbion, da AgroInsper e de
   especialistas locais e checar a concordância (`rubric_rater_agreement.csv`; alfa ≥ 0,67 como
   referência mínima).
2. **Coleta indireta:** os portais primários continuam inacessíveis neste ambiente. Situação de cada
   correção pedida:
   - LPI do México: verificado.
   - Eletricidade do Brasil: corrigida.
   - Açúcar: padronizado em USDA mai/2026.
   - Aquafeed: padronizado em 2024–25. O Chile segue estimado pela produção.
   - Estresse hídrico: valores de 2021+ não obtidos; padronizado em 2018.
   - Demais valores *Medium/Low*: ainda precisam de conferência na fonte primária.
3. **México (incerteza menor):** o valor de açúcar foi lido de uma tabela USDA cujo alinhamento de
   colunas não foi verificado; o aquafeed vem de uma nota de imprensa da CONAFAB.
4. **Concorrência na China:** capacidades não auditadas (CABIO, SSE 688089; Runke). É preciso
   levantar a capacidade de biomassa de DHA para aquafeed e a curva de preços.
5. **Aprovações:** é preciso verificar se o registro GACC está vinculado à planta brasileira. Se
   estiver, uma planta nova na Tailândia precisaria de novo registro para exportar à China.
6. **Concentração:** a expansão em Orindiúva concentra o suprimento num só país, numa só safra de
   cana e numa só moeda. O modelo não captura esse risco.
7. **Distância:** usa grande-círculo; o frete cotado entra só no módulo de economia (faixas indicativas).
8. **Economia:** os parâmetros de processo e capex são premissas e devem ser substituídos por dados
   da Corbion e cotações de EPC. Ver `due_diligence_brazil_thailand.md`.

## 10. Fontes

**Adicionadas na v2:** USDA FAS Sugar: World Markets and Trade (mai/2026) https://www.fas.usda.gov/data/sugar-world-markets-and-trade-05282026 ·
USDA China Sugar Annual 2026 https://www.fas.usda.gov/data/gain/2026/04/china-sugar-annual ·
Emol – radiografia da beterraba (Iansa) https://www.emol.com/noticias/Economia/2026/05/11/1199512/radiografia-remolacha-chile.html ·
Aqua Culture Asia Pacific – Aquafeeds in 2025 https://aquaasiapac.com/2026/06/30/aquafeeds-in-2025-disrupted-by-tariffs/ ·
Sindirações 2025 (Band) https://www.band.com.br/agro/noticias/producao-de-racoes-para-animais-tem-alta-de-28-em-2025-aponta-sindicato-202512051209 ·
CONAFAB acuacultura https://www.liderempresarial.com/conafab-destaca-el-crecimiento-del-6-en-la-acuacultura-mexicana/ ·
SeafoodSource – Chile salmon exports 2025 https://www.seafoodsource.com/news/supply-trade/chile-s-salmon-exports-surpass-usd-6-5-billion-in-2025 ·
World Bank LPI 2023 (documento) https://documents1.worldbank.org/curated/en/099042123145531599/pdf/P17146804a6a570ac0a4f80895e320dda1e.pdf ·
CEPEA açúcar cristal https://cepea.org.br/br/diarias-de-mercado/acucar-cepea-indicador-tem-nova-alta.aspx ·
Preço de açúcar tailandês (Bangkok Post / Pattaya Mail) https://www.pattayamail.com/thailandnews/sugar-price-hike-canceled-after-pm-flags-impact-on-households-and-retailers-525552 ·
Intratec gás natural Tailândia https://www.intratec.us/solutions/energy-prices-markets/commodity/natural-gas-price-thailand ·
UFF Engevista – cogeração de bagaço https://periodicos.uff.br/engevista/article/view/9103/6576 ·
Bank of Thailand salário manufatura (Trading Economics) https://tradingeconomics.com/thailand/wages-in-manufacturing ·
IBGE PNAD 2025 (Exame) https://exame.com/brasil/rendimento-medio-do-brasileiro-chega-a-r-3-367-maior-valor-da-historia/ ·
Damodaran country risk https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html e ERP jan/2026 https://www.bvresources.com/articles/bvwire/damodaran-posts-his-first-data-update-for-2026 ·
Thailand Top-Up Tax Decree (Forvis Mazars) https://www.forvismazars.com/th/en/insights/doing-business-in-thailand/tax/global-minimum-tax-top-up-tax ·
Brazil Lei 15.079/2024 (Trench Rossi) https://www.trenchrossi.com/en/legal-alerts/brazil-law-15079-establishing-the-oecd-pillar-two-global-minimum-tax-in-brazil-qdmtt-has-been-approved/ ·
Corbion FY2025 (receita €1.267,4 mi) https://millingmea.com/corbion-reports-strong-2025-results-with-26-7-organic-growth-in-adjusted-ebitda/ ·
Fed FX 2025 https://fred.stlouisfed.org/series/AEXBZUS e https://fred.stlouisfed.org/series/AEXTHUS ·
Veramaris US$ 200 mi https://www.seafoodsource.com/news/aquaculture/veramaris-opens-usd-200-million-algal-oil-facility ·
Solazyme 10-K 2014 https://www.sec.gov/Archives/edgar/data/1311230/000155566715000031/solazyme10k2014-12x31.htm ·
Fretes: https://agorafreight.net/shipping-quotes/fcl-from-santos-to-shanghai/ , https://www.sino-shipping.com/freight-china-chile/ ·
NatureWorks Nakhon Sawan https://renewable-carbon.eu/news/?p=179603 · IEAT BCG estate https://washingtondc.thaiembassy.org/en/content/thailand-builds-industrial-estate-for-bio-green-ci

**Fontes da v1:**

Todas acessadas em 07/10/2026. A fonte de cada valor está no `raw_country_data.csv`.

**Corbion / BioMar / clientes**
- Corbion – Our global presence: https://www.corbion.com/about-us/our-company/our-global-presence
- Corbion – Omega-3 DHA from algae (Orindiúva): https://www.corbion.com/solutions/algae/sustainable-omega-3-sourcing
- Corbion Annual Report 2024 – Group structure: https://annualreport.corbion.com/annual-report-2024/other-information-1/group-structure
- Corbion Q4/FY2024 press release: https://www.corbion.com/-/media/corbion/files/quarterly/2024/2025-02-27_corbion_press-release-4q-fy-2024.pdf
- Corbion – GACC approvals AlgaPrime/AlgaVia (jul/2025): https://www.mfn.se/one/a/corbion-n-v/corbion-secures-chinese-regulatory-approvals-for-algae-derived-omega-3-dha-products-in-human-and-animal-nutrition-ca1e6ba2
- Corbion – New lactic acid plant, Rayong: https://www.foodtechbiz.com/business-updates/corbion-announces-completion-of-its-new-circular-lactic-acid-plant-in-thailand
- Corbion – Querétaro upgrade (set/2024): https://www.globenewswire.com/de/news-release/2024/09/24/2952199/0/en/Corbion-steps-up-in-region-customer-support-with-major-facility-upgrade-in-Quer%C3%A9taro-Mexico.html
- Corbion – Novotech acquisition, India (ago/2024): https://www.globenewswire.com/fr/news-release/2024/08/07/2925640/0/en/Corbion-acquires-bread-improver-business-from-Novotech-bolstering-Indian-market-strategy.html
- Undercurrent News – Corbion algal business (2021): https://www.undercurrentnews.com/2021/06/30/corbions-algal-business-starting-to-blossom-as-firm-ramps-up-volumes-markets/
- Thai Union/Corbion – AlgaPrime in shrimp feed (2020): https://www.globenewswire.com/news-release/2020/10/13/2107266/0/en/Thai-Union-and-Corbion-Expand-Adoption-of-AlgaPrime-DHA-into-Shrimp-Aquaculture.html
- Undercurrent – Ventisqueros/BioMar AlgaPrime (Chile): https://www.undercurrentnews.com/2017/04/26/chilean-farmer-ventisqueros-to-use-algaprime-based-feed/
- Azelis distributes Corbion (incl. Indonesia): https://www.foodbusinessmea.com/corbion-and-azelis-expand-partnership-onto-new-horizons/
- BioMar – Our history: https://www.biomar.com/our-story/our-history
- BioMar – Wuxi expansion (China JV): https://www.fishfarmingexpert.com/aquafeed-biomar-factory-expansion/biomar-targets-new-species-with-factory-expansion-in-china/2068647
- BioMar – Viet-Uc partnership: https://www.biomar.com/insights/insights-hub/biomar-and-viet-uc-enter-a-strategic-partnership-to-develop-the-aquafeed-business-in-vietnam
- SeafoodSource – Shrimp-feed consolidation: https://www.seafoodsource.com/news/premium/supply-trade/consolidation-creating-big-players-in-the-global-shrimp-feed-industry
- Skretting Surat (India): https://thefishsite.com/es/articles/skretting-opens-18-5-million-feed-facility-in-surat-india

**Concorrência em DHA de algas**
- Relatório de mercado de óleo de DHA de algas (capacidade da Runke): https://file.echemi.com/upload/eu/files/DHAAlgaeOilMarketReport.pdf
- CABIO Biotech – perfil: https://www.cabio.com/about/our-company
- Excesso de capacidade de PLA na China: https://faxiangongchang.com/en/reports/china-bioplastic-pla-2026
- Veramaris (Evonik): https://elements.evonik.com/en/articles/OnlineOnly/veramaris.html
- Pilotos de DHA na Índia: https://www.indiascienceandtechnology.gov.in/node/166202
- *Nota:* os produtores chineses (CABIO, Runke, Huison, Fuxing) atendem principalmente a nutrição
  humana (fórmula infantil, suplementos). Foram tratados como risco de capacidade porque a mesma
  fermentação pode ser redirecionada para biomassa de aquafeed, não como concorrentes diretos atuais
  em aquafeed.

**Açúcar, energia e água**
- USDA FAS – Sugar: World Markets and Trade (mai/2025): https://www.fas.usda.gov/sites/default/files/2025-05/sugar.pdf
- USDA FAS GAIN – Indonesia Sugar Annual 2026: https://www.fas.usda.gov/data/gain-report/2026/04/Sugar%20Annual_Jakarta_Indonesia_ID2026-0014.pdf
- VSSA / YN Sugar (Vietnã): https://www.ynsugar.com/vietnam-sugar-output-2025-26-prices-three-year-low/
- VietnamPlus – comparação regional de preços: https://en.vietnamplus.vn/vietnams-sugar-prices-move-against-global-trends-post311895.vnp
- KRISNA – preço do açúcar na Indonésia: https://www.krisna.or.id/en/post/gula/
- Czapp – custo de produção de açúcar: https://www.czapp.com/analyst-insights/sugar-cost-of-production-across-the-world/
- Iansa (Chile) – fim da compra de beterraba: https://www.biobiochile.cl/noticias/economia/negocios-y-empresas/2026/04/29/duro-golpe-para-la-industria-de-la-remolacha-iansa-anuncia-que-no-comprara-en-el-mercado-chileno.shtml
- GlobalPetrolPrices – eletricidade empresarial: https://www.globalpetrolprices.com/electricity_prices/ e https://www.globalpetrolprices.com/Brazil/electricity_prices/
- Ember via OWID energy-data: https://github.com/owid/energy-data
- FAO AQUASTAT SDG 6.4.2 via IndexMundi: https://www.indexmundi.com/facts/indicators/ER.H2O.FWST.ZS/rankings · UN-Water SDG6 (Brasil): https://sdg6data.org/country-or-area/Brazil

**Mercado, logística e macro**
- China Feed Industry Association 2024: https://www.chinafeed.org.cn/hyfx/202502/t20250215_452996.htm
- USDA FAS GAIN – Vietnam Grain and Feed Annual 2026: https://www.fas.usda.gov/data/gain-report/2026/04/Grain%20and%20Feed%20Annual_Ho%20Chi%20Minh%20City_Vietnam_VM2026-0012.pdf
- Alltech Agri-Food Outlook 2026: https://assets.ctfassets.net/yd4nuh0j3lyv/6PUPaUJ2d1mLRQDYiZgPXt/f533f66c13df1cce98c5acfb1d2bfd9c/Alltech_Agri-Food_Outlook_2026_-_English.pdf
- Sindirações 2024: https://www.foodagribusiness.world/feed/brazilian-feed-industry-forecasts-2-3-production-increase-in-2024
- Peixe BR 2024: https://www.foodbusinessmea.com/brazils-aquaculture-industry-production-hit-more-than-900000-tonnes-in-2024-brazilian-farming-fish-association/
- IMARC – Thailand aquafeed: https://www.imarcgroup.com/thailand-aquafeed-market · Aquafeed Thailand status: https://www.aquafeed.co.uk/?p=17725
- Indonesian aquafeed (JIPD): https://systems.enpress-publisher.com/index.php/jipd/article/download/4552/3210
- Salmon Business – capacidade de ração no Chile: https://www.salmonbusiness.com/salmon-feed-producer-expands-by-100000-tonnes-per-year/?amp=1
- SERNAPESCA via World Fishing: https://www.worldfishing.net/?p=28325
- WATTAgNet – México: https://www.wattagnet.com/articles/19476-mexican-feed-production-on-the-rise
- FAO SOFIA 2024: https://www.fao.org/3/cd0683en/online/sofia/2024/aquaculture-production.html
- World Bank LPI 2023: https://lpi.worldbank.org/sites/default/files/2023-04/LPI_2023_report.pdf · tabela secundária: https://worldpopulationreview.com/country-rankings/logistics-performance-index-by-country
- World Bank WDI (PIB e população) via datasets/gdp e datasets/population: https://github.com/datasets/gdp
- KPMG – tabela de alíquotas corporativas: https://kpmg.com/dk/en/services/tax/corporate-tax/corporate-tax-rates-table.html · PwC Tax Summaries: https://taxsummaries.pwc.com/
- USTR 2026 Special 301: https://ustr.gov/about/policy-offices/press-office/press-releases/2026/april/ustr-releases-2026-special-301-report-intellectual-property-protection-and-enforcement
- Ratings soberanos S&P (agregador): https://tradingeconomics.com/country-list/rating

**Ativos visuais:** fonte Montserrat (SIL OFL, `assets/fonts/OFL.txt`); Natural Earth 110m
(domínio público); sane-topojson (MIT, `assets/geo/LICENSE_sane-topojson.txt`).
