# Rankings de países – Corbion AlgaPrime DHA

Dois rankings ponderados, no mesmo formato da v2 (critérios com pesos → score 0–10), aprofundados:

1. **Prompt 1 – `plant`:** qual país é o melhor para a nova unidade de fermentação de DHA de microalgas.
2. **Prompt 2 – `market`** (em construção): quais países são os melhores para a Corbion expandir vendas em
   salmão, camarão e pet food — um ranking por nicho e um geral.

## Executar

```bash
cd microalgae_site_selection/country_ranking
python -m src plant            # ~2 min (1.000 simulações de dados + 4.000 sorteios de pesos)
python -m pytest -q tests      # 10 testes
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
- `data/raw/market_research_partial/` guarda a pesquisa incompleta do Prompt 2 (limite de buscas atingido).
