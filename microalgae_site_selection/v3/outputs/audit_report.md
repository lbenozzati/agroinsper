# Relatório de auditoria forense: v2 → v3

*Corte: 2026-10-14 · commit 2a44797 · gerado por `python -m src run`*

## Como ler

- **confirmed_error**: erro demonstrável no método ou no cálculo.
- **invalid_comparison**: compara bases, unidades, datas ou escopos diferentes.
- **weak_hypothesis**: premissa sem evidência suficiente, que pode estar certa ou não.
- **unknown**: a fonte pública não permite concluir.

Nada foi chamado de erro se ainda depende de confirmação.

Contagem: weak_hypothesis = 14, invalid_comparison = 10, unknown = 4, confirmed_error = 1. Lista completa em `audit_issues.csv` (linha/função afetada, afirmação antiga, evidência nova, materialidade, correção e impacto).

## Limitação de acesso às fontes

Os domínios corbion.com, annualreport.corbion.com, globenewswire.com, World Bank, WRI, USDA, IFFO e BioMar estavam bloqueados neste ambiente (403/DNS). Nenhum PDF original foi aberto. Os números vieram de trechos de busca (`access_status = search_snippet`), de valores informados pelo usuário (`user_supplied`) ou herdados da v2. `evidence_registry.csv` registra isso linha a linha, e `source_gaps.csv` lista o que precisa ser aberto no original antes de um FID.

## Checagens automáticas (recalculadas a cada execução)

| ID | Tema | Resultado | Implicação |
|---|---|---|---|
| AC01 | peso das rubricas | Rubricas = 66% do peso efetivo. Score só quantitativo: Brasil 4,96 (6º), China 7,04, Thailand 6,30, India 5,92 | O 1º lugar do Brasil na v2 depende de rubricas de um avaliador (CR é 100% rubrica). |
| AC02 | correlação entre critérios | corr(PE, CR) entre os 8 países = 0,76; corr(MA, SR) = -0,81 | Integração com usina e ativos existentes premiam os mesmos países duas vezes. |
| AC03 | robustez aos pesos | Sorteios de pesos Dirichlet (n=2000): P(rank 1) Brazil 89%, Thailand 10%; P(top 3) China 50%, India 33% | Top 2 robusto aos pesos; a 3ª posição não. |
| AC04 | limites de normalização | fator 0.75: 2 países mudam de posição; fator 1.25: 2 países mudam de posição | Limites escolhidos a posteriori só mexem nas posições 3–7. |
| AC05 | reprodução da v2 | máx |score recalculado − v2 congelado| = 0,0004; ranking idêntico: True | Baseline reproduzido a partir dos dados congelados. |
| AC06 | balanço de massa do açúcar | v2 3,0 t açúcar/t produto (30% DHA) vs v3 5,05 t sacarose/t SKU (36% DHA, yield 0.075, recovery 0.95) | Custo de açúcar por t ~+65%. |
| AC07 | capex brownfield | v2 fator fixo 0,75 × localização 1,10 = 0,83 do greenfield; v3 modular = 0,79 do greenfield no mesmo site (utilidades compartilhadas 0.5, prédios 0.4, owner 0.6) | Vantagem agora explícita e testável (caso sem vapor ocioso no tornado). |
| AC08 | custo unitário v2 vs v3 | v2 MSP Orindiúva 11,6 US$/kg DHA (20 kt, 90% de utilização); v3 custo pleno a 100% do módulo 12,9; v3 MSP com demanda-base 18,3 | É a utilização (demanda), e não o custo, que define o preço necessário. |
| AC09 | valor terminal | VPL base de A1 79,2 US$ mi, dos quais VT 96,6 (122%); VPL sem VT -17,4 | Com horizonte 2026–2035 e ramp-up lento, o valor está depois de 2035. |
| AC10 | demanda vs capacidade | Demanda-base ponderada 2030 = 3.405 t; um módulo = 8.500 t efetivas; contratado (público) = 0 t | A restrição é a absorção pela demanda, não a capacidade. |

## Achados de alta materialidade

| ID | Onde | Classe | Correção na v3 |
|---|---|---|---|
| AU01 | `microalgae_site_selection.py METRICS (rubric metrics)` | weak_hypothesis | v3 reports rubric share, a quant-only score and rank frequencies; agreement only computed when real ratings are supplied |
| AU02 | `SCENARIOS (30/20/15/15/20)` | weak_hypothesis | v3 samples weights from a Dirichlet around each scenario and reports rank frequency instead of a single order |
| AU05 | `country score -> site decision` | invalid_comparison | v3 separates country screening (ranking_v3.csv) from site economics (unit_economics.csv, cashflow_by_scenario.csv) and site gates |
| AU06 | `brazil_thailand_economics.py:133 (brownfield_capex_factor 0.75)` | weak_hypothesis | v3 builds capex by module (fermentation, downstream, utilities, effluent, buildings, EPC/owner) with explicit shared-utility factors and a 'no spare steam' case |
| AU07 | `economics_assumptions.csv capacity=20000` | weak_hypothesis | Module size is a decision variable (5-20 kt); demand absorption tested; EUR 50m shown only as an implied-capacity sensitivity |
| AU08 | `economics_assumptions.csv sugar_kg_per_kg=3.0` | weak_hypothesis | v3 mass balance: sugar = DHA fraction / (yield x recovery); base 0.075 g/g with 0.055-0.10 range -> ~5 kg sucrose/kg SKU |
| AU15 | `economics_assumptions.csv sugar_price` | invalid_comparison | v3 uses delivered-sucrose prices per site with explicit basis (S017 Aug-2026; S018/S019) and ranges |
| AU18 | `economics_results.csv capex per t` | invalid_comparison | v3 canonical units: t SKU (P3 powder), kg DHA; capex per t/yr SKU nameplate; no comparison with oil-based plants without conversion |
| AU20 | `due_diligence_brazil_thailand.md GACC` | unknown | Route plant->China enabled only after gacc_delay_years for new plants; status unknown for Orindiúva SKUs |
| AU26 | `HANDOFF (market priorities)` | weak_hypothesis | Demand file separates contracted / qualified_pipeline / unqualified_potential; only contracted is firm (0 public) |
| AU27 | `price` | unknown | Price is an explicit slider/assumption with fish-oil pass-through; NPV shown across price range |

## Itens mantidos com trilha

- **LPI do México = 2,9**: confirmado no World Bank (S025) e não substituído por palpite.
- **Chile, açúcar doméstico = 0 a partir de 2026/27**: zero verdadeiro (S026), não valor ausente. Fica com gate REVIEW, porque a importação de açúcar continua possível.
- **Aprovações GACC (2025)**: o escopo por SKU e por planta é `unknown`. Uma planta nova entra com atraso de registro (`gacc_delay_years`) para vender à China.
- **Pillar Two na Tailândia**: o top-up é modelado como (15% − ETR) × (lucro GloBE − SBIE) e funciona como chave liga/desliga, porque a combinação com as entidades tributáveis da Corbion em Rayong pode anulá-lo. Parecer jurídico pendente. O QRTC fica fora do caso base (vale 0).
- **CMD 2025**: TIR de 20% e payback de 4,5 anos referem-se ao programa agregado de expansão. Os €50 mi de Orindiúva não têm capacidade divulgada. `eur50m_implied_capacity_sensitivity.csv` mostra só o que essa verba compraria em cada intensidade de capex, e não é um dado divulgado.
