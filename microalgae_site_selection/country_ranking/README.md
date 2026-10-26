# Rankings Corbion AlgaPrime DHA

> **Revisão factual de 15/10/2026 (`rev2026`) – versão de decisão.** Os rankings de país de 14/10/2026 (seções
> abaixo) ficam **congelados** em `outputs/frozen_2026-10-14/` só para comparação.

## Revisão 2026-10-15 (`python -m src rev2026`)

```bash
cd microalgae_site_selection/country_ranking
python -m src rev2026                 # ~40 s (inclui o motor DCF da v3 e Monte Carlo de 1.000 sorteios)
python -m pytest -q tests/test_rev2026.py
```

**Duas análises, dois lados da decisão:**
- **(A) ranking público** – sites (Orindiúva, greenfield BR, Nakhon Sawan, Rayong) com pesos 40/25/15/15/5 e
  mercados país×nicho com pesos 25/25/25/15/10. Os pesos são **escolhas estratégicas** (config_rev2026.yaml).
- **(B) retorno incremental** – DCF da v3 (`../v3/src/engine.py`, não reimplementado) por site × nicho ×
  cenário de renovação dos contratos de dez/2026 (R1-R6). **Tudo em B é ASSUMPTION**; com dados públicos o VPL/TIR
  é "não estimável" (`economics_public_only.csv`).

**Regras do score público (`src/rev2026/interval.py`):**
- cada célula tem `status` OBSERVED / DERIVED / JUDGMENT / ASSUMPTION / UNKNOWN (schema do brief §6 em
  `data/rev2026/site_cells.csv` e `outputs/rev2026/market_evidence.csv`, com `value_low/value_high` e `absence_type`
  = documented_no / no_public_evidence);
- ASSUMPTION nunca pontua; UNKNOWN entra como 0 no **piso** e 10 no **teto** (sem nota 5 inventada, sem zero como
  fato, sem renormalizar os pesos conhecidos); faixas documentadas entram pelas pontas;
- açúcar e energia são componentes do opex: se o opex for observado, o peso deles passa para o opex (sem dupla
  contagem);
- ordem pelo piso garantido; **faixa de posição** = melhor/pior completando os desconhecidos; dominância par a par;
- regulação/licenciamento = **gates** (`product_regulatory_matrix.csv`), não pontos; tributos e BOI só no caixa;
- goalposts fixos publicados em `goalposts_table.csv`. Nota de transparência: os goalposts de capex/opex foram
  corrigidos de escala (US$ por kg/ano de DHA) durante a montagem, quando todos os valores ainda eram UNKNOWN –
  sem efeito na ordem.

**Saídas (`outputs/rev2026/`):** `old_vs_new_weights.csv`, `rubric_migration.csv`, `source_registry.csv`,
`claims_audit.csv`, `product_regulatory_matrix.csv`, `customer_factory_matrix.csv`, `competitor_product_matrix.csv`,
`site_evidence.csv`, `missing_data_decision_value.csv`, `site_public_scores.csv`, `market_public_scores_*.csv`,
`economics_*.csv`, `capacity_to_npv_bridge.csv`, sensibilidades (`*_weight_perturbation_pm25.csv`,
`*_tipping_points.csv`, `*_single_document_flips.csv`, `*_leave_one_criterion_out.csv`, correlações),
`circularity_check.csv`, `automated_checks.csv`, `management_data_template.csv`, `run.log`, `run_manifest.json`,
memo `revision_memo.md` e slides `slide1..5_*.png` (+ `site_intervals.png`, `market_intervals_*.png`).

**Fontes:** nenhum documento primário pôde ser aberto integralmente neste ambiente (hosts bloqueados). Cada fonte
tem `verification_level`: L1 = conteúdo relatado pelo brief do cliente, L2 = trecho de busca, L3 = sessão anterior,
L0 = indisponível. Nada é apresentado como lido do original.

---

# Rankings de países (14/10/2026 – congelados)

Dois rankings ponderados, no mesmo formato da v2 (critérios com pesos → score 0–10), aprofundados:

1. **Prompt 1 – `plant`:** qual país é o melhor para a nova unidade de fermentação de DHA de microalgas.
2. **Prompt 2 – `market`:** quais países são os melhores para a Corbion expandir vendas em
   salmão, camarão e pet food — um ranking por nicho e um geral.

## Executar

```bash
cd microalgae_site_selection/country_ranking
python -m src plant            # ~2 min (1.000 simulações de dados + 4.000 sorteios de pesos)
python -m src market           # ~2 min (3 nichos)
python -m pytest -q tests      # 17 testes
```

## Prompt 1 – método

- **Pesos dos critérios (mantidos da v2):** Economia de produção 30%, Acesso a mercados 20%, Prontidão Corbion 15%,
  Regulação e incentivos 15%, Risco estratégico 20%. Cenários alternativos: Lowest-Cost (40/15/20/10/15) e
  Asian Market (25/30/10/15/20). Sub-critérios e métricas em `config_plant.yaml`.
- **12 países**, cada um avaliado numa **usina de referência** (açúcar, vapor e energia vêm da usina; EUA = moinho
  de milho/dextrose de Blair-NE). Lista e coordenadas em `data/raw/research/sugar_mills.csv`.
- **Normalização:** régua fixa (piso/teto) por métrica, como o IDH; escala log para tamanhos. Incluir um país não
  muda a nota dos outros (teste).
- **Valor ausente nunca vira zero:** a métrica sai, os pesos são renormalizados e o ranking mostra o score se a
  lacuna fosse 0 ou 10.
- **Métricas derivadas** (fórmula na própria linha do dado):
  - dias porta a porta da usina a 12 mercados por rota marítima com canais/estreitos/cabos (`src/searoutes.py`),
    ponderados pelo SAM de DHA 2030 do estudo de mercado (sensibilidade: TAM);
  - fração da demanda prioritária coberta por acordos comerciais em vigor;
  - alíquota efetiva de 10 anos com incentivos e piso de 15% (Pilar 2);
  - volatilidade cambial 2020–25; autossuficiência em açúcar.
- **Robustez:** Monte Carlo de dados (ruído conforme a confiança), pesos Dirichlet, só-quantitativo, limites das
  escalas ±25–50%, pontos de virada por critério, correlação entre critérios.
- **Rubricas** (~42% do peso, antes ~66%): definidas e justificadas linha a linha em `data/raw/plant_rubrics.csv`;
  template para outros avaliadores em `outputs/plant/plant_rubric_ratings_template.csv`.

## Prompt 2 – método

- **Mesmos 5 critérios em todos os nichos** (scores comparáveis): Tamanho e crescimento 30%, Valor e disposição a
  pagar 20%, Acesso a clientes e posição competitiva 20%, Regulação e acesso comercial 15%, Risco país e biológico 15%.
  Cenários: Consolidação (20/20/35/15/10) e Crescimento (40/20/10/15/15). Métricas por nicho em `config_market.yaml`.
- **Nichos e países:** salmão (10), camarão (12), pet food (15); gráficos e memo mostram o top 10 de cada nicho e do geral.
- **Logística até o cliente** (25% do critério Acesso): dias porta a porta desde Orindiúva (Santos → porto do nicho, mesma
  rota marítima do Prompt 1; portos em `data/raw/ports_market.yaml`), LPI 2023 e conectividade marítima UNCTAD do destino.
- **Necessidade técnica de DHA** (derivada): ração × g de DHA/kg do estudo de mercado (salmão 5,3; camarão 2,7;
  pet 0,33), com a mesma régua log nos três nichos.
- **Ranking geral:** média dos scores do país por nicho, ponderada pela necessidade técnica de DHA do país em cada nicho.
- **Regras de cobertura:** métrica com dado em < 40% dos países do nicho sai do score (fica no CSV);
  país com < 50% do peso coberto é marcado "dados insuficientes" e ranqueado depois dos demais.
- Mesmas análises de robustez do Prompt 1 (Monte Carlo de dados, Dirichlet de pesos, só-quantitativo, pontos de virada).

Saídas em `outputs/market/`: `market_ranking_{salmon,shrimp,pet}.csv`, `market_ranking_overall.csv`,
`market_ranking_country_niche_pairs.csv`, `market_metric_scores.csv`, `market_metric_coverage_*.csv`,
`market_tipping_points.csv`, `market_country_memo.md` e gráficos (`market_heatmap_*.png`, `market_contributions_*.png`,
`market_overall_ranking.png`, `market_map.png`). Entradas: `data/raw/market_research/*.csv`,
`data/raw/market_rubrics.csv`, `data/raw/market_analyst_fallback.csv`.

## Entradas

| Arquivo | Conteúdo |
|---|---|
| `../v3/data/raw/frozen_v2/raw_country_data.csv` | Dados v2 reaproveitados (8 países) |
| `data/raw/research/*.csv` | Pesquisa desta rodada (fonte, URL, ano, tipo, confiança, notas) |
| `data/raw/plant_rubrics.csv` | Rubricas do analista e ajustes de estrutura de incentivos |
| `data/raw/plant_analyst_fallback.csv` | Valores do analista usados só onde a pesquisa não achou nada (Low) |
| `data/raw/ports.yaml` | Portos de saída/chegada e trechos terrestres |
| `data/processed/plant_inputs_long.csv` | Tudo junto, com proveniência |

## Saídas (`outputs/plant/`)

`plant_country_ranking.csv`, `plant_metric_scores.csv`, `plant_subcriteria_scores.csv`, `plant_weight_scenarios.csv`,
`plant_tipping_points.csv`, `plant_goalpost_robustness.csv`, `plant_criterion_correlation.csv`,
`plant_transit_matrix.csv`, `plant_country_memo.md` e gráficos 16:9 (`plant_heatmap.png`, `plant_contributions.png`,
`plant_map.png`, `plant_rank_probability.png`, `plant_transit_days.png`).

## Limites

- Portais primários bloqueados: quase tudo veio de trechos de busca (marcado nas notas).
- Sem preço de açúcar para México, Equador e Chile; OECD FDI Index só existia para 3 países e ficou fora do score.
- Salários com definições diferentes; Aqueduct 3.0 (portal 4.0 bloqueado); rotas ±10%.
- `data/raw/market_research_partial/` guarda a primeira tentativa (incompleta) da pesquisa do Prompt 2.

## Rubricas por componentes (rev. 26/10/2026)

As rubricas de degrau único (canal 0/2,5/5/7,5/10 e registro) foram substituídas por notas somadas de componentes,
cada ponto com evidência e fonte em `data/raw/market_rubric_components.csv` (gerado por
`data/raw/tools/build_rubric_components.py`). Componente sem evidência entra como faixa (piso–teto); o modelo 14/10
usa o ponto médio, a revisão 15/10 usa piso e teto.

- **Canal (0-10):** A estágio comercial 0-4 (4 compra recorrente ≤12 meses; 3 compra pontual/adoção histórica; 2 teste;
  1 canal formal/cliente global com fábrica; evidência >3 anos perde 1); B cobertura do canal na ração do país 0-3
  (≥50% / 20-50% / <20%); C profundidade 0-2 (nº de clientes independentes); D presença Corbion 0-1.
- **Registro (0-10):** A status legal 0-4 (4 registro com nº verificado; 3 aprovação anunciada ou uso comercial;
  2 catálogo genérico; 1 pedido protocolado); B prazo 0-2; C barreiras específicas 0-2; D incentivo regulatório/
  certificação ao DHA de algas 0-2. Tarifa fica fora (métrica própria).
- **Posição competitiva (0-10, novo):** A concorrência algal documentada 0-3 (não encontrado = faixa 2-3); B ajuste
  do produto ao nicho 0-3 (salmão 1: só DHA vs Veramaris EPA+DHA; camarão 2; pet 2); C custo entregue 0-2 (C1 sem
  produção concorrente local; C2 prazo desde Orindiúva ≤25 dias); D alavanca de marca/sustentabilidade 0-2.
- **Pesos:** modelo 14/10 – acesso/posição competitiva 20%→30% (dentro: competição 30%, canal 20%, adoção 20%,
  fábricas 15%, logística 15%); tamanho 30%→25%, valor 20%→15%; cenário "Pesos 14-10" mantém os antigos.
  Revisão 15/10 – posição competitiva 15%→25%, demanda e economia 25%→20%; conjunto `pesos_15_10` mantém os antigos.
  Racional: ingrediente B2B vendido a poucas fábricas de ração; a venda é decidida contra Veramaris, óleo de peixe e
  DHA algal local, não pelo tamanho do país.
