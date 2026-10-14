# Briefing: localização de nova unidade de DHA de microalgas (Corbion) – estado da análise

## 1. Contexto e objetivo
Apresentação de Private Equity (AgroInsper / Aqua Capital, slide "Investment Thesis: Algae Platform Expansion").
Pergunta: em qual país a Corbion deveria construir uma nova unidade de AlgaPrime DHA (DHA de microalgas por
fermentação heterotrófica com açúcar; planta atual em Orindiúva-SP, ao lado de uma usina de cana).
Clima tropical NÃO é critério; seus efeitos entram via açúcar, biomassa/vapor, energia renovável e água.
Países analisados: Brasil, Tailândia, China, Vietnã, Índia, Indonésia, Chile e México.
Mercados prioritários: China, Chile e Vietnã (aquafeed), mais pet food e nutrição humana.

## 2. O que foi construído (Python, pasta `microalgae_site_selection/`)
- `microalgae_site_selection.py`: modelo multicritério → ranking, viabilidade, cenários, Monte Carlo, mapas e gráficos.
- `brazil_thailand_economics.py`: custo e retorno Brasil vs Tailândia (capex, opex, impostos, WACC, preço mínimo de venda).
- `raw_country_data.csv`: dados de entrada em formato longo (país × métrica), com valor, unidade, ano, fonte, URL,
  data de acesso, tipo (reported/estimate/proxy/missing) e confiança (High/Medium/Low).
- `economics_assumptions.csv`: premissas do módulo de custo (base, mínimo e máximo por país; fonte ou "assumption").
- `data_change_log.csv`: 22 correções da v1 para a v2; os dados v1 estão em `archive/`.
- `methodology_and_sources.md`, `due_diligence_brazil_thailand.md`, `README.md` e 14 testes (pytest).
- Saídas em `outputs/`: CSVs de todas as camadas e gráficos no estilo do slide (degradê azul-marinho → roxo, branco/prata,
  Montserrat). Mapa-múndi em várias versões: completa, limpa transparente (bolhas brancas, mais branco = melhor,
  só o 1º destacado) e clara (estilo da referência). Também: ranking, contribuição por critério, sensibilidade,
  Monte Carlo, ponto de virada da tese e gráficos de custo.

## 3. Metodologia
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

## 4. Resultados atuais (v2)
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

## 5. Correções feitas na v2 (detalhe em `data_change_log.csv`)
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

## 6. Limitações (o que mais precisa melhorar)
1. Portais primários (World Bank, FAO, OECD, Corbion, USDA) estavam bloqueados no ambiente: muitos valores foram
   lidos via busca, sem abrir o documento original. Itens Medium/Low precisam de conferência na fonte primária.
2. Rubricas qualitativas (~65% do peso) aplicadas por um único avaliador. Já existe suporte a vários avaliadores
   (`outputs/rubric_ratings_template.csv` → `rubric_ratings.csv`, com mediana e alfa de Krippendorff),
   mas faltam as notas de Corbion, AgroInsper e especialistas locais.
3. Premissas de julgamento puro no módulo de custo:
   - capex greenfield de US$ 8.000/t de capacidade (faixa 5.000–12.000);
   - desconto por ser expansão de 25%;
   - fator de localização: Brasil 1,10, Tailândia 1,00;
   - 2,5 kWh/kg, 5 t de vapor/t e 3 kg de açúcar/kg (este último derivado de um rendimento de laboratório);
   - quadro de pessoal de 70/110;
   - vazamento tributário de 1,5%.

   O desconto por expansão e o fator de localização estão entre os que mais movem a diferença de custo.
4. Estresse hídrico de 2018; distância aos mercados em linha reta (grande-círculo); frete com cotações parciais.
5. Não incluídos: risco de concentração (expandir Orindiúva concentra o suprimento em um país, uma safra e uma moeda)
   e preço de venda real do AlgaPrime (por isso o resultado é MSP, não TIR).
6. Diligência pendente:
   - registro no GACC por planta (uma planta nova provavelmente precisa do próprio para exportar à China);
   - prazos da CETESB e do licenciamento tailandês (ONEP/BOI);
   - contrato de açúcar, vapor e energia com a usina;
   - capacidade auditada dos produtores chineses de DHA;
   - tier do BOI e status do crédito reembolsável (QRTC);
   - site em Nakhon Sawan (polo NBC, com a planta de PLA da NatureWorks desde abr/2026) vs Rayong.

## 7. Sugestões de próximos passos
- Substituir as premissas por dados da Corbion (rendimento, kWh, vapor, pessoal, capex da expansão) e por cotações de EPC e frete.
- Coletar notas de mais 2–3 avaliadores e medir a concordância.
- Atualizar o estresse hídrico (2021–22), checar fontes primárias e adicionar o preço real do AlgaPrime para calcular TIR/VPL.
- Testar outros países (Equador, Peru, Filipinas, EUA/Nebraska) adicionando linhas ao CSV (modelo em `outputs/country_data_template.csv`).
- Incluir o risco de concentração e o cenário de diversificação (duas plantas) na análise de investimento.

## 8. Fontes principais
Corbion (site, Annual Report 2024, resultados de 2025, aprovações GACC); BioMar; USDA FAS (Sugar World Markets
mai/2026, GAIN reports); China Feed Industry Association; Alltech Agri-Food Outlook 2026; Sindirações; GPMT; TFMA;
CONAFAB; FAO (SOFIA 2024, AQUASTAT SDG 6.4.2); World Bank (WDI, LPI 2023); Ember/OWID; GlobalPetrolPrices;
CEPEA/ESALQ; Bank of Thailand; IBGE; KPMG/PwC; Thailand BOI; Top-Up Tax Decree B.E. 2567; Lei 15.079/2024;
USTR Special 301 2026; S&P; Damodaran (jan/2026); Federal Reserve (câmbio).
Lista completa com links: seção 10 de `methodology_and_sources.md`.
