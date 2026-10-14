# Corbion DHA: mercados para expansão e consolidação (estudo independente da fábrica)

**Pergunta:** em quais países, espécies, fases, clientes e formatos a Corbion deveria expandir ou consolidar
o AlgaPrime DHA? Que volume, receita e margem incremental poderia capturar até 2030/2035?

## Executar

```bash
cd microalgae_site_selection/market_expansion
pip install -r requirements.txt
python -m src run                 # ~75 s (1.000 simulações); gera outputs/ e market_memo.md
python -m src run --publish-v3    # também copia a demanda para ../v3/data/raw (alimenta o estudo da fábrica)
python -m pytest -q tests         # 13 testes
```

## Lógica (denominadores visíveis)

`ração → TAM (necessidade técnica de DHA) → SAM (espaço servível por DHA de algas) → DHA de algas (curva S) → SOM Corbion → t SKU → receita B2B → contribuição → VPL comercial ponderado pela probabilidade de qualificação`

- **Ração:** volume observado (Noruega, pet food) ou produção × eFCR × parcela de ração comercial.
- **Estágios:** hatchery/smolt, engorda e finishing (salmão); hatchery/nursery e engorda (camarão); cão seco e
  gato seco (pet food; úmido e petiscos excluídos).
- **DHA e EPA são separados:** o AlgaPrime supre só DHA.
- **Demanda para a nova capacidade:** só o volume incremental sobre 2025 vai para a v3. Volumes atuais da
  Corbion não são atribuídos à nova capacidade.

## Entradas (`data/raw/`)

| Arquivo | Conteúdo |
|---|---|
| `source_registry.csv` | Fonte, URL, data, vintage, unidade, método, tipo, confiabilidade e status de acesso |
| `country_species_feed.csv` | Produção, eFCR, ração e crescimento por país × espécie |
| `nutrition_requirements.csv` | Estágios, alvo EPA+DHA, parcela DHA, DHA já suprido por marinhos, capacidade de pagar, inclusão máxima |
| `product_specs.csv`, `competitor_assets.csv`, `pricing_evidence.csv` | Produtos, concorrentes (JV contada uma vez), evidência de preço |
| `customer_evidence.csv` | Contas com status documented_current/historical, trial, channel_only, potential ou unknown, e próxima prova |
| `market_parameters.csv`, `market_assumptions.csv` | Premissas por mercado e globais (base/low/high) |
| `market_definitions.csv`, `market_claims_audit.csv` | Definições TAM/SAM/SOM; auditoria das afirmações (GMI, BioMar, Nutrition etc.) |

## Saídas principais (`outputs/`)

- **Interface com a v3:** `market_demand_scenarios.csv` (+ `_low`, `_high`), no esquema da v3.
- **Curvas e limites:** `market_demand_curves.csv` e `cockpit_bounds.csv`.
- **Funil e rankings:** `market_opportunity_waterfall.csv`, `market_rankings.csv` (consolidação e expansão
  separadas), `account_ranking.csv`.
- **Carteira e decisão:** `portfolio_selection.csv` (MILP HiGHS), `value_of_information.csv`,
  `capacity_price_frontier.csv`, `capacity_supported.csv`.
- **Plausibilidade e efeito na fábrica:** `top_down_reconciliation.csv`, `v3_effect_with_market_demand.csv`.
- **Lacunas:** `source_gaps.csv`.
- **Gráficos e páginas:** PNGs 16:9 e `market_explorer.html` (offline).

## Limites

- **Fontes:** os documentos originais estavam bloqueados no ambiente de construção. Os números vieram de
  trechos de busca e estão marcados em `source_registry.csv`.
- **Premissas:** preço do AlgaPrime, tonelagem por cliente e contratos não são públicos. São premissas
  explícitas com faixas.
- **Reformulação:** não há programação linear de formulação, porque falta uma matriz de ingredientes
  defensável.
