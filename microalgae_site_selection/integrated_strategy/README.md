# Estratégia integrada: capacidade × origem × mercados × momento (Corbion DHA)

**Pergunta:** que combinação de capacidade industrial, origem de fornecimento, carteira de mercados e momento
de investimento maximiza o valor incremental ajustado a risco? Em que condições a recomendação muda entre
Orindiúva, uma segunda planta na Tailândia, esperar ou investir em fases?

Este módulo **não reimplementa** os estudos. O funil de mercado vem de `../market_expansion/src/model.py` e os
fluxos de caixa vêm do motor `../v3/src/engine.py`, o mesmo motor do painel JS, com paridade testada. Aqui só se
harmonizam unidades, preços, Incoterm e demanda, e se comparam políticas.

## Executar

```bash
cd microalgae_site_selection/integrated_strategy
python -m src run                         # roda os testes da v3 e do mercado, depois tudo (~2 min, 400 simulações)
python -m src run --skip-upstream-tests --mc-sims 100
python -m pytest -q tests                 # 12 testes
```

## Saídas (`outputs/`)

- **Integração:** `integration_reconciliation.csv`, `route_economics.csv`, `niche_origin_inversions.csv`.
- **Políticas e alocação:** `allocation_by_scenario.csv`, `project_cashflows.csv`,
  `investment_policy_comparison.csv`, `portfolio_composition.csv`.
- **Decisão:** `break_even_frontiers.csv` (+ `_lines`), `contract_thresholds.csv`, `option_value.csv`.
- **Risco:** `stress_tests.csv`, `monte_carlo_policy_summary.csv`, `joint_correlation_matrix.csv`,
  `risk_dependency_register.csv`, `empirical_series_status.csv`.
- **Diligências:** `diligence_priority.csv`.
- **Relatório e painel:** `integrated_investment_memo.md`, `integrated_decision_cockpit.html` (offline).
- **Gráficos:** PNGs 16:9 (heatmap origem × destino, Sankey, fronteira, superfície de decisão, ponte de VPL,
  carteira × capacidade, mapa de rotas) e os 3 slides conceituais (`concept_1..3`).
- **Rastreabilidade:** `run_manifest.json` (commits, versões, cortes, hashes das tabelas consumidas e resultado
  dos testes dos módulos de origem).

## Políticas

| Código | Política |
|---|---|
| WAIT | Esperar (nenhum capex) |
| A | Orindiúva, 1 módulo |
| A' | Orindiúva adiado |
| A2 / A2' | 2º módulo por gatilho ou fixo |
| B / B' | Orindiúva + Tailândia já ou em 2032 |
| C / C' | Tailândia por gatilho de demanda asiática ou de utilização |
| D | Hub asiático sem fermentação |

As políticas são definidas em `config.yaml`. A comparação é por enumeração auditável. A alocação dentro de cada
política é ótima (caminhos mínimos sucessivos, conferidos com `linprog`).

## Limites

- **Sem contratos públicos:** toda conclusão é condicional.
- **Sem séries históricas suficientes:** nenhuma correlação empírica foi estimada. O Monte Carlo usa priors
  declarados, com matriz PSD verificada e uma corrida independente para robustez.
- **Tarifas não verificadas:** valem 0.
- **Alocação por região do motor v3:** o rateio a países segue a demanda do estudo de mercado.
