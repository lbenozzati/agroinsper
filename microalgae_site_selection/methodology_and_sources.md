# Metodologia e fontes: localização de nova unidade de DHA de microalgas (Corbion)

*Versão 1.0 · dados acessados em 07/10/2026 · gerado com `microalgae_site_selection.py`*

> **Status dos resultados.** O ranking abaixo é real no sentido de que todo número sai do arquivo
> `raw_country_data.csv` por fórmula reprodutível. Porém **cerca de 65% do peso do score vem de
> notas qualitativas de analista** (rubricas abaixo) e várias séries quantitativas foram obtidas de
> fontes secundárias, porque os portais institucionais (World Bank API, FAO, OECD, Corbion.com) não
> puderam ser acessados diretamente neste ambiente. Use o resultado como **triagem estruturada para
> discussão**, não como decisão de investimento. A seção 9 lista o que precisa de diligência.

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

## 8. Resultados

### 8.1 Ranking Base Case

| # | País | Score | PE | MA | CR | RI | SR* | Viabilidade | Data conf. | % do score com baixa confiança |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Brazil | **7,08** | 8,2 | 4,7 | 9,4 | 5,6 | 7,2 | Pass | 64 | 8% |
| 2 | Thailand | **6,88** | 6,6 | 5,6 | 7,5 | 7,3 | 7,8 | Pass | 59 | 22% |
| 3 | China | **5,63** | 5,7 | 8,7 | 4,4 | 6,7 | 2,6 | Pass | 71 | 0% |
| 4 | Vietnam | 5,61 | 5,1 | 7,6 | 1,2 | 6,7 | 6,8 | Pass | 51 | 41% |
| 5 | India | 5,57 | 6,2 | 6,3 | 3,8 | 4,4 | 6,2 | Review (estresse hídrico 66%) | 55 | 28% |
| 6 | Chile | 5,16 | 4,0 | 6,8 | 1,2 | 6,6 | 7,2 | Review (sem base doméstica de açúcar) | 52 | 30% |
| 7 | Indonesia | 5,12 | 5,0 | 5,5 | 1,2 | 5,8 | 7,4 | Pass | 51 | 37% |
| 8 | Mexico | 5,01 | 4,2 | 3,2 | 5,6 | 5,0 | 7,7 | Review (LPI 2,9) | 58 | 30% |

\*SR: 10 = menor risco estratégico.

### 8.2 Sensibilidade

| País | Base Case | Lowest-Cost Production | Asian Market Expansion | Melhor/pior posição | Variação do score | No top 3 |
|---|---|---|---|---|---|---|
| Brazil | 7,08 (#1) | 7,50 (#1) | 6,67 (#2) | 1 / 2 | 0,83 | 3 de 3, **robusto** |
| Thailand | 6,88 (#2) | 6,88 (#2) | 6,74 (#1) | 1 / 2 | 0,14 | 3 de 3, **robusto** |
| China | 5,63 (#3) | 5,53 (#3) | 5,99 (#4) | 3 / 4 | 0,47 | 2 de 3 |
| Vietnam | 5,61 (#4) | 5,13 (#5) | 6,06 (#3) | 3 / 5 | 0,93 | 1 de 3 |
| India | 5,57 (#5) | 5,53 (#4) | 5,71 (#5) | 4 / 5 | 0,18 | 0 |
| Chile | 5,16 (#6) | 4,59 (#8) | 5,57 (#6) | 6 / 8 | 0,99 | 0 |
| Indonesia | 5,12 (#7) | 4,75 (#7) | 5,35 (#7) | 7 / 7 | 0,60 | 0 |
| Mexico | 5,01 (#8) | 4,91 (#6) | 4,83 (#8) | 6 / 8 | 0,17 | 0 |

**Leitura:** só Brasil e Tailândia ficam no top 3 nos três cenários. A terceira posição é
estatisticamente indistinta: China, Vietnã e Índia estão a menos de 0,07 ponto entre si no Base
Case, bem dentro da incerteza das rubricas.

## 9. Limitações e diligência necessária

1. **Rubricas** respondem por 65,5% do peso efetivo (incluindo o status USTR convertido em nota). Elas devem ser validadas com
   a gestão da Corbion e com especialistas locais, especialmente: concorrência local, permissões e
   incentivos.
2. **Coleta indireta.** Os portais primários (World Bank, FAO, OECD, Corbion.com) estavam bloqueados
   no ambiente de coleta. Os valores vieram de PDFs oficiais citados em buscas, de espelhos no GitHub
   (OWID/Ember, datasets/gdp) ou de agregadores (IndexMundi, World Population Review, TradingEconomics).
   É preciso conferir cada valor marcado *Medium/Low* na fonte primária.
3. **Volumes de aquafeed** usam definições e anos diferentes (CFIA 2024, USDA 2025, Alltech 2025,
   consultoria 2023, estimativa acadêmica 2020, dado de 2014 para o México e capacidade instalada para
   o Chile). Isso afeta sobretudo Tailândia (provavelmente subestimada), México e Indonésia.
4. **Estresse hídrico** é de 2018 para sete países e de 2021 (arredondado) para o Brasil. A média
   nacional esconde bacias críticas (Chile central, Bajío no México, norte da China).
5. **Eletricidade:** o Brasil usa um snapshot de dezembro/2025; os demais, a média 2023–2025. Para
   a Índia, as fontes divergem (0,07 a 0,12 USD/kWh).
6. **Produção de açúcar:** usa a safra USDA de maio/2025 para manter uma única vintage (a Índia foi
   revisada para 30 Mt em nov/2025). A Indonésia está em açúcar branco, não em raw value. O Vietnã
   vem de fonte secundária. O Chile está ausente.
7. **Concorrência na China:** as capacidades vêm de relatório de mercado, não de demonstrações
   auditadas (CABIO, SSE 688089; Runke). O paralelo com o PLA (utilização abaixo de 40%) é analógico.
   É necessário levantar a capacidade de biomassa de DHA para aquafeed e a curva de preços.
8. **Aprovações:** a aprovação GACC para vender na China **não** equivale a licença para fabricar
   localmente. Também é preciso verificar se o registro GACC está vinculado à planta brasileira: se
   estiver, uma nova planta em outro país precisaria de novo registro para exportar à China.
   Registros para Vietnã, Índia e Indonésia não foram encontrados.
9. **Brasil = expansão brownfield.** O primeiro lugar reflete a ampliação de Orindiúva (ativos,
   equipe, licenças). Isso **aumenta a concentração geográfica** do suprimento: um único país, safra
   de cana e câmbio do real. Esse risco de concentração não está no modelo e deve ser ponderado pelo
   comitê de investimento.
10. **Tailândia** é a melhor opção greenfield e de diversificação, mas: o volume de aquafeed é de baixa
    confiança, o preço do açúcar sofre com secas, há instabilidade política e o tier exato de
    incentivo BOI para DHA de algas precisa ser confirmado.
11. A distância aos mercados é grande-círculo (proxy), não rota marítima nem frete cotado.

## 10. Fontes

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
