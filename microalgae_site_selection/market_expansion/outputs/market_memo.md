# Mercados para expansão e consolidação de DHA (AlgaPrime): memorando

*Corte: 2026-10-14 · commit 2a44797 · seed 42 · 1000 simulações · gerado por `python -m src run`*

> **Natureza do resultado.**
> - É um estudo de mercado independente da localização da fábrica.
> - Os documentos originais (Corbion, BioMar, IFFO, FAO, FEDIAF, USDA) não puderam ser abertos neste ambiente; os números vêm de trechos de busca e estão marcados em `source_registry.csv`.
> - Não há preço público do AlgaPrime, contratos nem tonelagem por cliente. Volumes e receitas são **cenários condicionais a premissas explícitas**, não pedidos nem previsões da Corbion.
> - Nutrição humana (AlgaVia) é oportunidade adjacente e **não entra** nos totais.

## 1. Resposta curta

1. **O negócio de ração é, na prática, salmão.** No cenário-base de 2030, salmão responde por 97% da receita B2B modelada (US$ 52 mi no total).
   - Noruega e Chile concentram 89% do volume incremental.
   - Camarão, China e pet food têm grandes TAMs, mas o SAM é pequeno: em camarão, o DHA da fase de engorda já vem de farinha e óleo de peixe, e só uma fração dos produtores paga por DHA adicional.
2. **Consolidar antes de expandir.** A carteira ótima (MILP: equipe, registros, capacidade e concentração) escolhe Chile · salmão, Norway · salmão, United Kingdom · salmão, com VPL comercial de US$ 53,8 mi.
   - Nenhum mercado de expansão tem VPL comercial positivo com as premissas-base: os volumes não cobrem o custo de equipe, registros e ensaios.
3. **Capacidade que a carteira sustenta** (volume incremental sobre 2025, t de SKU/ano):
   - 2028: 1.797 t (base), faixa 54–10.081;
   - 2030: 3.254 t, faixa 94–19.083;
   - 2035: 5.545 t, faixa 137–36.641.
   - Um módulo de 10 kt (8.500 t efetivas) fica 65% ocupado em 2035 no cenário-base. No Monte Carlo, o p10–p90 de 2035 vai de 2.931 a 7.962 t.
4. **O que mais muda a decisão** (valor de fechar a lacuna):
   - Preço líquido por kg DHA (swing de US$ 89 mi); Preço do óleo de peixe (swing de US$ 50 mi); Participação da Corbion no DHA de algas (swing de US$ 46 mi); Alvo de EPA+DHA na dieta (swing de US$ 46 mi).
   - Preço realizado e participação/alvo de DHA pesam mais que crescimento ou custo variável.
5. **Efeito no estudo da fábrica (v3).** Rodei o motor v3 em memória, sem sobrescrever nada, com esta demanda no lugar das premissas antigas (pesos de pipeline base da v3):
   - A1 Orindiúva: VPL de US$ 79 mi (premissas v3) → -9 (mercado base) e 214 (mercado alto).
   - Preço mínimo de A1: US$ 26,3/kg DHA com o mercado base.
   - G (Orindiúva + Tailândia): -204 (base) e 363 (alto).
   - Leitura: com a demanda bottom-up base, nem a expansão de Orindiúva se paga sem contratos. O investimento depende de converter o pipeline de salmão e de preço. A Tailândia só faz sentido no cenário alto. O Prompt 3 deve integrar isso formalmente.

## 2. Auditoria das afirmações usadas nos slides

| ID | Afirmação | Situação | Consequência |
|---|---|---|---|
| C01 | Algae omega-3 'production systems' market (EN page) (USD 720 m (2025) -> USD 2.13 bn (2035)) | rejected_as_tam | Not used as TAM or as a check on SOM |
| C02 | Same report, older/translated page (USD 4.5 bn (2025) -> USD 20.2 bn (2034)) | unresolved_conflict | Unresolved conflict: neither number used |
| C03 | Algal omega-3 volume ~12.5 kt and Corbion 29.3% share (GMI, user-supplied) (12.5 kt; 29.3%) | not_used | Corbion share set by segment assumptions instead |
| C04 | China aquafeed 22.6 Mt (v2 Market Access input) (22.62 Mt) | corrected | Only China shrimp feed (production x FCR) used; China share 10% (local competition) |
| C05 | BioMar ~1 Mt of feed 'containing microalgae' (~70%) (~1 Mt) | reclassified | Not used as AlgaPrime volume |
| C06 | BioMar >40 kt salmon feed with AlgaPrime since 2016 (40 kt feed (cumulative)) | kept_as_evidence | Relationship documented_historical (not current) |
| C07 | Nutrition sales 2024 EUR 157 m; 2030 ambition ~EUR 275 m (EUR 157 m / 275 m) | check_only | Top-down plausibility check only (reconciliation table) |
| C08 | >60 customers in >25 countries (60 / 25) | check_only | Accounts not inferred from count |
| C09 | Thai Union adopted AlgaPrime in shrimp (2020) (sem número) | kept_as_evidence | documented_historical |
| C10 | IQI supplies AlgaPrime to pet food (EU/NA) (sem número) | kept_as_evidence | channel_only; distributor margin netted from price |
| C11 | China GACC approvals = China market (sem número) | reclassified | Regulatory readiness 0.8; no customer assumed |
| C12 | Veramaris capacity ~15% of salmon EPA+DHA demand (1.2 Mt fish-eq) | check_only | Used qualitatively for competitive intensity |
| C13 | Algae DHA 40-50% lower climate impact than fish oil (40-50%) | check_only | Premium not assumed from LCA; price premium is an explicit assumption |
| C14 | Fish oil price 2026 (USD 3.9-6.8 k/t) | driver_range | Driver range 2.5-6.8 k/t |
| C15 | Corbion H1 2026: Nutrition double-digit volume/mix, lower omega-3 oil prices (sem número) | check_only | Volume and price modelled separately |
| C16 | Ecuador shrimp feed ~2.5 Mt (derived 40% x 6.2 Mt) (2.5 Mt) | check_only | Cross-check of production x FCR (2.3 Mt) |
| C17 | EU pet food 8.6 Mt vs 9.1 Mt (same FEDIAF edition) (8.6 / 9.1 Mt) | unresolved_conflict | 8.6 Mt base; 9.1 in high case note |
| C18 | US pet food 10.5 Mt (Alltech 2025) vs 9.8 Mt (IFEEDER 2024) (10.5 / 9.8 Mt) | check_only | 10.5 Mt base |

**GMI:**

- A página em inglês (US$ 720 mi em 2025) e a página antiga (US$ 4,5 bi em 2025) divergem 6× para o mesmo ano.
- Não há documento que reconcilie escopo (sistemas × ingredientes × óleo × downstream) nem a definição de tonelada. O conflito é **insolúvel com dados públicos**.
- Nenhum desses números é usado como TAM. A participação de 29,3% **não** é dado divulgado pela Corbion, e a divisão US$ 720 mi / 12,5 kt **não** é usada como preço.

**DSM-Firmenich e Veramaris:** a Veramaris é uma joint venture 50/50 entre dsm-firmenich e Evonik e é contada **uma única vez**.

## 3. TAM → SAM → SOM (denominadores visíveis)

Definições em `market_definitions.csv`:

- **TAM:** necessidade técnica de DHA.
- **SAM:** espaço que DHA de algas pode suprir, considerando capacidade econômica de pagar, qualificação técnica, prontidão regulatória e o DHA que não vem de ingredientes marinhos.
- **SOM:** SAM × adoção × participação da Corbion.

| Ano | Cenário | TAM (t DHA) | SAM (t DHA) | DHA de algas (t) | SOM (t DHA) | SOM (t SKU) | Receita B2B (US$ mi) | Contribuição (US$ mi) |
|---|---|---|---|---|---|---|---|---|
| 2028 | low | 28.748 | 1.441 | 564 | 94 | 282 | 1,1 | 0,2 |
| 2028 | base | 55.334 | 11.647 | 5.031 | 1.586 | 4.771 | 39,7 | 22,2 |
| 2028 | high | 97.116 | 34.528 | 15.086 | 7.018 | 21.108 | 333,1 | 235,3 |
| 2030 | low | 28.673 | 1.439 | 642 | 107 | 322 | 1,3 | 0,3 |
| 2030 | base | 57.797 | 12.127 | 6.572 | 2.070 | 6.226 | 51,9 | 29,0 |
| 2030 | high | 105.128 | 37.292 | 21.553 | 10.008 | 30.100 | 475,2 | 335,7 |
| 2035 | low | 28.516 | 1.436 | 728 | 121 | 364 | 1,4 | 0,3 |
| 2035 | base | 64.525 | 13.421 | 9.070 | 2.832 | 8.517 | 70,9 | 39,7 |
| 2035 | high | 128.470 | 45.260 | 34.545 | 15.846 | 47.659 | 750,6 | 530,0 |

**Por nicho em 2030 (base):**

| Nicho | Ração (Mt) | TAM | SAM | SOM (t DHA) | SOM (t SKU) | Receita (US$ mi) |
|---|---|---|---|---|---|---|
| pet food | 20,07 | 6.625 | 477 | 47 | 142 | 1,4 |
| salmão | 4,73 | 25.046 | 10.509 | 2.002 | 6.022 | 50,1 |
| camarão | 9,68 | 26.126 | 1.141 | 21 | 62 | 0,5 |

- **Cenário baixo:** combina todas as premissas desfavoráveis; funciona como stress, não como "provável".
- **Monte Carlo:** usa multiplicadores globais com óleo de peixe correlacionado à adoção (ρ = 0,4). Receita de 2030: p10 US$ 29 mi, p50 51 e p90 85.

**Margem.** Preço líquido base de US$ 25/kg DHA (premissa: não há preço público), menos custos comerciais, rebates e capital de giro (13%), custo variável de Orindiúva vindo da v3 (US$ 7,37/kg DHA) e frete. A margem de contribuição fica entre US$ 9,7 e 17,2/kg DHA conforme o nicho.

**Custo na dieta e trade-off DHA:EPA** (`diet_cost_comparison.csv`):

- Óleo de peixe 18:12 a US$ 2,5–6,8 mil/t custa US$ 8–23 por kg de EPA+DHA, e entrega EPA e DHA juntos.
- O AlgaPrime entrega só DHA: o EPA continua vindo de óleo de peixe ou de óleo de algas EPA+DHA (Veramaris).
- Sem uma matriz de ingredientes defensável, não fiz reformulação por programação linear.

## 4. Reconciliação top-down (só plausibilidade)

| Cheque | Bottom-up | Top-down | Status |
|---|---|---|---|
| Bottom-up Corbion SOM 2025 vs Nutrition sales 2024 (EUR 157 m) | 2,999 t SKU / USD 25 m | EUR 157 m = USD 181 m -> 20,634 t SKU at USD 8.75/kg SKU | **INCOMPATIBLE SCOPES** |
| Nutrition 2030 ambition (~EUR 275 m) vs bottom-up 2030 revenue | USD 52 m (feed + pet only) | EUR 275 m = USD 316 m | **check only** |
| Salmon feed total vs BioMar salmon volume | 4.28 Mt salmon feed (NO+CL+UK+AU) | BioMar 1.557 Mt x 60% salmon = 0.93 Mt | **plausible** |
| Veramaris capacity ~15% of salmon EPA+DHA demand | 45,325 t EPA+DHA requirement 2025 (model) | 15% = 6,799 t EPA+DHA (if claim applied to this base) | **order of magnitude only** |
| Ecuador shrimp feed: production x eFCR vs Aprobal | 2.31 Mt | 6.2 Mt x 40% = 2.5 Mt (derived) | **consistent (within ~8%)** |
| GMI market value / volume | n/a | USD 720 m / 12.5 kt = USD 57.6/kg (NOT computed for use) | **REJECTED** |

A maior inconsistência:

- O SOM bottom-up de 2025 (≈ US$ 25 mi) explica só uma fração das vendas de Nutrition em 2024 (€157 mi).
- Explicações possíveis, que não consigo separar com dados públicos:
  - (a) a participação de AlgaVia/humana e de pet é maior;
  - (b) o preço realizado é bem maior que US$ 25/kg DHA;
  - (c) as premissas de participação e de adoção estão conservadoras.
- **Isso é a lacuna nº 1 a fechar com a Corbion:** volume e preço por SKU e por mercado.

## 5. Rankings condicionados (VPL comercial; o score é só triagem)

| Grupo | # | Mercado | Status de relação | VPL comercial (US$ mi) | Incremental 2030 (t) | P(qualificação) | Score de triagem | P(top 3) pesos | Confiança dado |
|---|---|---|---|---|---|---|---|---|---|
| consolidation | 1 | Norway · salmão | documented_historical | 29,4 | 1.652 | 75% | 7,8 | 99% | medium |
| consolidation | 2 | Chile · salmão | documented_historical | 21,9 | 1.251 | 75% | 7,6 | 100% | medium |
| consolidation | 3 | United Kingdom · salmão | documented_historical | 2,5 | 160 | 75% | 6,4 | 26% | low |
| consolidation | 4 | United States · pet food | channel_only | -0,4 | 52 | 60% | 6,6 | 74% | medium |
| consolidation | 5 | European Union · pet food | channel_only | -0,5 | 43 | 60% | 6,6 | 1% | medium |
| consolidation | 6 | Thailand · camarão | documented_historical | -1,2 | 11 | 68% | 5,5 | 0% | low |
| expansion | 1 | Australia · salmão | potential | -0,9 | 38 | 32% | 4,4 | 0% | low |
| expansion | 2 | Vietnam · camarão | potential | -1,9 | 4 | 18% | 3,0 | 0% | medium |
| expansion | 3 | Indonesia · camarão | potential | -1,9 | 1 | 14% | 2,1 | 0% | medium |
| expansion | 4 | Ecuador · camarão | potential | -2,5 | 26 | 21% | 3,8 | 0% | medium |
| expansion | 5 | India · camarão | potential | -2,7 | 2 | 14% | 1,9 | 0% | medium |
| expansion | 6 | China · camarão | potential | -3,0 | 15 | 28% | 3,0 | 0% | medium |

**Contagem dupla no score de triagem:** probabilidade de qualificação, canal, tempo até a receita e aderência estratégica têm correlação de 0,96 entre si (`triage_dimension_correlation.csv`). Por isso a decisão usa VPL e volume, não o score.

## 6. Onde há adoção documentada e onde é só potencial

- **BioMar Group** (Norway;Chile;United Kingdom, salmão): `documented_historical`; evidência: >40 kt salmon feed with AlgaPrime since 2016 (cumulative) (undated). Próxima prova: Current annual AlgaPrime tonnage and contract term.
- **Lerøy, Kvarøy Arctic, Ventisqueros** (Norway;Chile, salmão): `documented_historical`; evidência: Cited in v2 due diligence (inherited, not re-verified) (pre-2026). Próxima prova: Re-verify current programmes.
- **Thai Union / Thai Union Feedmill** (Thailand, camarão): `documented_historical`; evidência: 2020 expansion of AlgaPrime into shrimp feed (2020). Próxima prova: Continuity and tonnage 2025-26.
- **IQI Petfood** (United States;European Union, pet food): `channel_only`; evidência: Distribution partnership for pet food (EU, NA) (2024). Próxima prova: Brand-level customers and volumes.
- **Skretting (Nutreco)** (Norway;Chile;Ecuador, salmão): `potential`; evidência: No public evidence (sem data). Próxima prova: Impact report 2025 algal oil supplier.
- **Cargill Aqua Nutrition** (Norway;Chile, salmão): `potential`; evidência: No public evidence (sem data). Próxima prova: Supplier disclosure.
- **Mowi Feed** (Norway;United Kingdom, salmão): `potential`; evidência: No public evidence of AlgaPrime use; Skretting partnership from Q4-2025 (2026-02). Próxima prova: Ingredient sourcing policy.
- **BioMar - Tongwei JV** (China, camarão): `potential`; evidência: JV channel only; GACC approval = access not sales (2025). Próxima prova: Trial or order evidence.
- **BioMar - Viet-Uc JV** (Vietnam, camarão): `potential`; evidência: JV channel only (sem data). Próxima prova: Trial or order evidence.
- **BioMar Ecuador** (Ecuador, camarão): `potential`; evidência: New lines planned 2026 (2026). Próxima prova: Trial evidence.
- **Agripac / other Ecuador mills** (Ecuador, camarão): `potential`; evidência: No public evidence (sem data). Próxima prova: Trial evidence.
- **BioMar Group (microalgae claim)** (Global, salmão): `unknown`; evidência: Feed containing SOME algal ingredient - not evidence of AlgaPrime (2025). Próxima prova: Split by supplier (Corbion vs Veramaris vs others).
- **Undisclosed (>60 customers, >25 countries)** (Global, all): `unknown`; evidência: Corbion CMD 2025 statement (user-supplied) (2025-11). Próxima prova: Customer list with tonnage (Corbion commercial).

- **Nenhuma conta está como `documented_current`:** não há evidência pública de 2025–26 com tonelagem.
- **BioMar ("~1 Mt de ração com microalgas")** é ração com algum ingrediente de algas, não volume de AlgaPrime.
- **JVs da BioMar (Tongwei, Viet-Uc) e GACC** são canal ou acesso, não clientes.
- **IQI** é distribuidor; a demanda final é das marcas.

## 7. Carteira e restrições

- **Ótimo-base:** Chile, Norway, United Kingdom; usa 2,5 pessoas (FTE) e 3.063 t incrementais em 2030. Solver HiGHS, status ótimo, gap 0.0. O teste confere o resultado com força bruta.
- **Concentração:**
  - limite por país de 40% → VPL de US$ -0,0 mi
  - limite por país de 60% → VPL de US$ 53,8 mi
  - limite por país de 80% → VPL de US$ 53,8 mi
  - A 40%, nenhuma carteira com VPL positivo é viável: a dependência de Noruega e Chile é estrutural.
- **Orçamento de equipe:** entre 5 e 12 FTE o ótimo não muda. A restrição que pesa é econômica (volume de expansão pequeno), não de equipe.

## 8. Valor da informação (o que coletar primeiro)

| Dado | Como fechar | VPL da carteira (min–máx, US$ mi) | Incremental 2030 (t) | Muda a carteira? |
|---|---|---|---|---|
| Preço líquido por kg DHA | contrato/cotação com clientes | 18,3–107,6 | 3.254–3.254 | sim |
| Preço do óleo de peixe | série IFFO / contratos | 28,1–78,0 | 2.611–3.644 | sim |
| Participação da Corbion no DHA de algas | inteligência competitiva (Veramaris, chineses) | 31,0–76,6 | 1.952–4.556 | sim |
| Alvo de EPA+DHA na dieta | ensaios / especificações dos clientes | 31,0–76,6 | 1.952–4.556 | sim |
| Saturação da adoção de algas | pipeline qualificado / ensaios | 26,7–71,8 | 1.725–4.273 | não |
| Parcela da ração que paga por DHA | entrevistas com fabricantes de ração | 31,0–65,7 | 1.952–3.961 | sim |
| Probabilidade de qualificação | histórico de ensaios / CRM | 36,7–70,9 | 3.254–3.254 | não |
| Crescimento da produção animal | FAO / associações | 41,6–67,4 | 2.667–3.889 | não |
| DHA já suprido por ingredientes marinhos | matriz de formulação / dados de compra | 42,8–64,7 | 2.589–3.924 | não |
| Custo variável (US$/kg DHA) | dados de operação Orindiúva | 43,0–59,3 | 3.254–3.254 | não |

## 9. Sequência comercial recomendada

1. **Salmão Chile e Noruega:** converter a relação histórica com a BioMar (e outros formuladores) em contratos plurianuais com volume e preço. É o que sustenta ou não o módulo de Orindiúva.
2. **Fechar as lacunas de maior valor:**
   - preço líquido por SKU e mercado;
   - participação versus Veramaris nas contas de salmão;
   - especificação de EPA+DHA dos clientes (alvo por fase).
3. **Pet food (EUA/UE, via IQI):** baixo custo de entrada. Precisa de lista de marcas, dose e claims para virar pipeline qualificado.
4. **Camarão (Equador, Tailândia):** só com ensaio pago e prova de que DHA adicional melhora desempenho ou permite cortar óleo de peixe. Com as premissas atuais, o VPL é negativo.
5. **China:** acesso regulatório existe (GACC), mas a concorrência local e a falta de clientes documentados deixam o mercado como opção, não como base de capacidade.
6. **Nutrição humana (AlgaVia):** avaliar em estudo separado. Pode explicar boa parte da receita atual de Nutrition.

## 10. Interface com o estudo da fábrica

- **Demanda base:** `market_demand_scenarios.csv`, no esquema da v3 e validado com `validate_demand` da v3.
- **Variantes:** `_low.csv` e `_high.csv`.
- **Classificação dos volumes:**
  - relação documentada → `qualified_pipeline`;
  - demais → `unqualified_potential`;
  - `contracted` = 0.
- **Curvas e limites:** `market_demand_curves.csv` traz as curvas por status, preço, margem e confiança; `cockpit_bounds.csv` traz os limites e as dependências entre controles.
- **Para alimentar a v3:** `python -m src run --publish-v3`, depois `cd ../v3 && python -m src run`. Validação: validated with v3 src/data.py validate_demand.

## 11. Lacunas que exigem entrevista, contrato ou ensaio

- [decision_driver] Preço líquido por kg DHA: contrato/cotação com clientes
- [decision_driver] Preço do óleo de peixe: série IFFO / contratos
- [decision_driver] Participação da Corbion no DHA de algas: inteligência competitiva (Veramaris, chineses)
- [decision_driver] Alvo de EPA+DHA na dieta: ensaios / especificações dos clientes
- [decision_driver] Saturação da adoção de algas: pipeline qualificado / ensaios
- [decision_driver] Parcela da ração que paga por DHA: entrevistas com fabricantes de ração
- [account] documented_historical: Current annual AlgaPrime tonnage and contract term
- [account] unknown: Split by supplier (Corbion vs Veramaris vs others)
- [account] potential: Ingredient sourcing policy
- [account] potential: Impact report 2025 algal oil supplier
- [account] potential: Supplier disclosure
- [account] documented_historical: Re-verify current programmes
- [account] documented_historical: Continuity and tonnage 2025-26
- [account] potential: Trial or order evidence
- [account] potential: Trial or order evidence
- [account] potential: Trial evidence
- [account] potential: Trial evidence
- [account] channel_only: Brand-level customers and volumes
- [account] unknown: Customer list with tonnage (Corbion commercial)

Fontes que precisam ser abertas no original antes de qualquer número ir para o comitê: `source_gaps.csv` (type = source).
