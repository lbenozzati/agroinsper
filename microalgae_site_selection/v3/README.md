# Corbion DHA: localização e retorno da próxima capacidade (v3)

**Pergunta:** qual a melhor sequência de investimentos para adicionar capacidade de DHA de microalgas à
Corbion? Em que site, com que capacidade, quando e sob quais condições econômicas?

A v3 **não sobrescreve** a v2 (pasta-mãe). Os insumos da v2 estão congelados em `data/raw/frozen_v2/`, e o
ranking v2 é reproduzido exatamente pelo teste `test_v2_baseline_reproduced_from_frozen_data`.

## Executar

```bash
cd microalgae_site_selection/v3
pip install -r requirements.txt
python -m src run                      # pipeline completo (~1 min, 2.000 simulações)
python -m src run --mc-sims 300 --no-charts
python -m pytest -q tests              # 23 testes (inclui paridade Python × JS via node)
```

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `config.yaml` | Horizonte, seed, alternativas A–G, distribuições e correlações do Monte Carlo, grade da fronteira, paleta |
| `data/raw/evidence_registry.csv` | Toda evidência: URL, data, página/tabela, unidade, vintage, tipo, confiabilidade e **status de acesso** (`search_snippet`, `unavailable`, `user_supplied`, `inherited_v2`) |
| `data/raw/assumptions.csv` | Toda premissa com base/low/high, escopo (global/país/site) e `source_id` |
| `data/raw/site_candidates.csv`, `site_gates.csv` | Sites georreferenciados e gates não compensatórios (PASS/REVIEW/FAIL/NOT_VERIFIED) |
| `data/raw/freight_lanes.csv` | Frete e trânsito por origem × região de demanda |
| `data/raw/market_demand_scenarios.csv` | Interface com o estudo de mercado (Prompt 2). Se não existir, é criado com PREMISSAS rotuladas (`ASSUMPTION_DEMAND_V3`), sem volume contratado |
| `data/raw/audit_findings.csv` | Achados da auditoria forense da v2 |
| `src/engine.py` | Balanço de massa, capex modular, opex, alocação ótima por rede (caminhos mínimos sucessivos), impostos por entidade (prejuízos, BOI, GloBE/QDMTT com SBIE, QRTC) e DCF nominal em USD |
| `src/cockpit_engine.js` | Porte linha a linha do motor, usado pelo painel; o teste de paridade compara os VPLs |
| `src/analysis.py` | Cenários, economia unitária, Monte Carlo com cópula gaussiana, tornado, fronteira e stress de resiliência |
| `src/screening.py` | Triagem de países: reprodução da v2, score só quantitativo, limites para valores ausentes, pesos Dirichlet e robustez dos limites de normalização |
| `src/reports.py` | `audit_report.md`, `investment_memo.md` (gerados a partir dos outputs) |
| `outputs/` | CSVs, PNGs 16:9 e `decision_cockpit.html` (offline) |

## Como trocar premissas por dados reais

1. **Dados Corbion ou EPC:** editar `assumptions.csv` (base/low/high e `source_id`) e adicionar a fonte em
   `evidence_registry.csv`. O validador rejeita valor sem unidade ou vintage.
2. **Demanda do estudo de mercado:** substituir `market_demand_scenarios.csv` (mesmo esquema). Só linhas
   `contracted` entram como volume firme; `qualified_pipeline` e `unqualified_potential` entram ponderadas
   pelo cenário (A110/A111).
3. Rodar `python -m src run`.

## Limites conhecidos

- **Acesso às fontes:** os sites corbion.com, World Bank, WRI, USDA, IFFO e BioMar estavam bloqueados no
  ambiente de construção; os valores vieram de trechos de busca e estão marcados.
- **Premissas não verificadas:** preço do AlgaPrime, capacidade dos €50 mi, rendimento industrial e
  contratos não são públicos. São premissas com faixa, e os resultados são condicionais a elas.
- **Monte Carlo:** é propagação de incerteza sob distribuições assumidas, não probabilidade calibrada.
- **Tributos:** o GloBE é simplificado por unidade; a combinação jurisdicional e as regras de prejuízo
  GloBE exigem parecer.
