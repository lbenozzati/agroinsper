# Melhor país para a nova unidade de DHA de microalgas (Corbion AlgaPrime) – ranking ponderado

*Gerado por `python -m src plant` · pesos 30/20/15/15/20 · 12 países · 34 métricas · cada país avaliado numa usina de referência.*

> **Natureza do resultado.** O score é uma triagem multicritério de 0 a 10, não VPL. Os dados vêm de fontes públicas, lidas na maioria por trechos de busca (portais primários bloqueados neste ambiente); cada valor tem fonte, ano, tipo e confiança em `data/processed/plant_inputs_long.csv`.

## 1. Resposta

**Brasil é o melhor país para a nova unidade** (score 7,03), seguido de Tailândia (6,25) e EUA (5,99).

- **Robustez a pesos:** com pesos sorteados em torno de 30/20/15/15/20, Brasil fica em 1º em 95% dos casos; Tailândia em 5%.
- **Robustez a dados:** com ruído conforme a confiança de cada fonte, Brasil fica em 1º em 95% e no top 3 em 100%.
- **1º lugar por cenário de pesos:** Base Case: Brasil, Lowest-Cost Production: Brasil, Asian Market Expansion: Brasil.
- **Mercados ponderados pela necessidade técnica de DHA (TAM, mais camarão asiático) em vez do SAM:** 1º = Brasil; Tailândia fica em 2º.
- **Só com métricas quantitativas** (sem rubricas): 1º = EUA; Brasil fica em 2º.
- **Gates (nenhum país é excluído, mas ficam em revisão):** México, Equador, Índia, Peru, Chile.

## 2. Ranking

| # | País | Usina de referência | Score | Econ. produção (30%) | Acesso mercados (20%) | Prontidão Corbion (15%) | Regulação (15%) | Risco (20%) | P(1º) pesos | P(top 3) dados | Gate | v2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Brasil | Usina Moema | **7,03** | 8,8 | 4,7 | 9,3 | 4,3 | 7,0 | 95% | 100% | Pass | 1º |
| 2 | Tailândia | KTIS Group | **6,25** | 6,7 | 3,7 | 7,1 | 7,9 | 6,2 | 5% | 99% | Pass | 2º |
| 3 | EUA | Cargill Blair biorefinery campus | **5,99** | 4,8 | 5,6 | 8,8 | 6,5 | 5,7 | 1% | 91% | Pass |  |
| 4 | México | Ingenio Pánuco | **5,47** | 4,9 | 5,8 | 5,0 | 4,4 | 7,1 | 0% | 7% | Review | 6º |
| 5 | Equador | Ingenio San Carlos | **5,22** | 5,6 | 6,6 | 0,9 | 4,9 | 6,7 | 0% | 1% | Review |  |
| 6 | Índia | Balrampur Chini Mills | **5,21** | 6,0 | 5,2 | 4,0 | 4,5 | 5,4 | 0% | 1% | Review | 4º |
| 7 | China | East Asia Sugar Group | **4,98** | 6,4 | 4,8 | 4,2 | 7,1 | 2,1 | 0% | 0% | Pass | 3º |
| 8 | Peru | Casa Grande S.A.A. | **4,89** | 4,0 | 5,8 | 1,1 | 5,9 | 7,3 | 0% | 0% | Review |  |
| 9 | Vietnã | TTC AgriS sugar factory, Tân Châu, Tây Ninh | **4,88** | 5,6 | 4,5 | 0,9 | 7,0 | 5,6 | 0% | 0% | Pass | 5º |
| 10 | Chile | Iansa San Carlos plant | **4,87** | 3,4 | 6,9 | 1,2 | 6,8 | 6,3 | 0% | 0% | Review | 7º |
| 11 | Indonésia | PG Djatiroto | **4,45** | 4,7 | 4,2 | 1,0 | 5,9 | 5,7 | 0% | 0% | Pass | 8º |
| 12 | Filipinas | Victorias Milling Company | **4,32** | 4,5 | 3,2 | 1,2 | 5,4 | 6,6 | 0% | 0% | Pass |  |

## 3. Por que cada país está onde está

- **Brasil** (7,03): forte em Ativos industriais da Corbion no país (10,0), Concorrência local de DHA de algas / excesso de capacidade (10,0); fraco em Carga tributária efetiva e incentivos (1,9), Fábricas de ração dos grandes clientes (2,5).
- **Tailândia** (6,25): forte em Carga tributária efetiva e incentivos (10,0), Mão de obra e construção (8,6); fraco em Tempo de trânsito aos mercados de DHA (ponderado pela demanda) (1,1), Fábricas de ração dos grandes clientes (3,8).
- **EUA** (5,99): forte em Base de fermentação industrial e talento (10,0), Presença comercial / inovação (10,0); fraco em Concorrência local de DHA de algas / excesso de capacidade (2,5), Açúcar/glicose: preço, escala e excedente (2,9).
- **México** (5,47): forte em Acordos comerciais com os mercados prioritários (10,0), Concorrência local de DHA de algas / excesso de capacidade (10,0); fraco em Fábricas de ração dos grandes clientes (2,5), Base de fermentação industrial e talento (2,6). Sem dado: pe_sugar_price_domestic (score entre 5,21 e 5,68 se a lacuna fosse 0 ou 10). Gate: Logística fraca (LPI 2.9).
- **Equador** (5,22): forte em Acordos comerciais com os mercados prioritários (10,0), Concorrência local de DHA de algas / excesso de capacidade (10,0); fraco em Ativos industriais da Corbion no país (0,0), Base de fermentação industrial e talento (1,2). Sem dado: pe_sugar_price_domestic (score entre 5,12 e 5,60 se a lacuna fosse 0 ou 10). Gate: Pouca produção de açúcar (0.516 Mt): matéria-prima importada; Logística fraca (LPI 2.88).
- **Índia** (5,21): forte em Acordos comerciais com os mercados prioritários (10,0), Mão de obra e construção (8,8); fraco em Proteção de PI (cepa, processo) (0,0), Água (nacional e na bacia do site) e efluentes (2,0). Gate: Estresse hídrico alto na bacia do site (4/5); Estresse hídrico nacional 66.5%.
- **China** (4,98): forte em Qualidade logística e conectividade marítima (9,0), Mão de obra e construção (8,8); fraco em Concorrência local de DHA de algas / excesso de capacidade (0,0), Proteção de PI (cepa, processo) (0,0).
- **Peru** (4,89): forte em Acordos comerciais com os mercados prioritários (10,0), Abertura a investimento estrangeiro (10,0); fraco em Ativos industriais da Corbion no país (0,0), Base de fermentação industrial e talento (2,0). Gate: Estresse hídrico alto na bacia do site (4/5).
- **Vietnã** (4,88): forte em Abertura a investimento estrangeiro (10,0), Carga tributária efetiva e incentivos (9,2); fraco em Ativos industriais da Corbion no país (0,0), Proteção de PI (cepa, processo) (0,0).
- **Chile** (4,87): forte em Acordos comerciais com os mercados prioritários (10,0), Abertura a investimento estrangeiro (10,0); fraco em Açúcar/glicose: preço, escala e excedente (0,0), Ativos industriais da Corbion no país (0,0). Sem dado: pe_sugar_price_domestic, cr_ethanol_production (score entre 4,82 e 5,48 se a lacuna fosse 0 ou 10). Gate: Pouca produção de açúcar (0.0 Mt): matéria-prima importada.
- **Indonésia** (4,45): forte em Acordos comerciais com os mercados prioritários (10,0), Carga tributária efetiva e incentivos (8,5); fraco em Ativos industriais da Corbion no país (0,0), Proteção de PI (cepa, processo) (0,0).
- **Filipinas** (4,32): forte em Proteção de PI (cepa, processo) (10,0), Carga tributária efetiva e incentivos (8,2); fraco em Ativos industriais da Corbion no país (0,0), Tempo de trânsito aos mercados de DHA (ponderado pela demanda) (0,3).

## 4. Pontos de virada

- Tailândia passa Brasil se **Economia de produção** pesar — nunca, em nenhum peso entre 0 e 100%.
- Tailândia passa Brasil se **Acesso a mercados** pesar — nunca, em nenhum peso entre 0 e 100%.
- Tailândia passa Brasil se **Prontidão Corbion** pesar — nunca, em nenhum peso entre 0 e 100%.
- Tailândia passa Brasil se **Regulação e incentivos** pesar 30% (base 15%).
- Tailândia passa Brasil se **Risco estratégico** pesar — nunca, em nenhum peso entre 0 e 100%.

## 5. O que mudou em relação à v2 (aprofundamento)

- **Países:** 8 → 12 (EUA/Blair-NE, Equador, Peru, Filipinas).
- **Site real por país:** cada país é avaliado numa usina de açúcar de referência (EUA: moinho de milho de Blair com dextrose), com vapor/cogeração e estresse hídrico medidos no local da usina (Aqueduct), não na média nacional.
- **Açúcar:** a rubrica de custo virou preço doméstico em US$/t + produção + autossuficiência (produção/consumo).
- **Mão de obra:** PIB per capita (proxy) foi trocado por salário médio na indústria.
- **Acesso a mercados:** a distância em linha reta a 3 mercados virou dias porta a porta por rota marítima real (canais e cabos), ponderados pela demanda de DHA de 2030 de 12 mercados do estudo de mercado; mais LPI, conectividade marítima, cobertura de acordos comerciais e fábricas dos grandes clientes.
- **Prontidão Corbion:** só ativos e pessoas da Corbion (o vapor/açúcar da usina fica em Economia de produção), para reduzir a contagem dupla apontada na auditoria.
- **Regulação:** alíquota efetiva de 10 anos com incentivos e piso global de 15% (Corbion > €750 mi), aprovação do AlgaPrime para venda, prazo de alvará e índice OCDE de restrição a IED.
- **Risco:** rating soberano + WGI (estabilidade e qualidade regulatória) + volatilidade cambial 2020-25 + ND-GAIN (clima) + Special 301 2026 + concorrência local de DHA de algas.
- **Peso de rubricas subjetivas:** caiu de ~66% (v2) para ~42% do peso efetivo.

## 6. Testes de robustez

- Limites das escalas ×0.75: 3 países mudam de posição; top 3 = Brasil, Tailândia, EUA; 1º inalterado: sim.
- Limites das escalas ×1.25: 2 países mudam de posição; top 3 = Brasil, Tailândia, EUA; 1º inalterado: sim.
- Limites das escalas ×1.5: 2 países mudam de posição; top 3 = Brasil, Tailândia, EUA; 1º inalterado: sim.
- Correlação entre Economia de produção e Prontidão Corbion nos 12 países: 0,63 (v2: 0,76).
- **Checagem de custo (não entra no score):** custo variável por kg de DHA na usina de referência, com a mesma base física da v3 (5,05 t de açúcar, 3.000 kWh e 6 t de vapor por t de produto): Brasil US$ 8,3, Índia US$ 9,4, Vietnã US$ 11,8, Tailândia US$ 11,9, China US$ 12,9, Indonésia US$ 14,1, Peru US$ 15,7, EUA US$ 15,8, Filipinas US$ 18,9.

## 7. Limitações

- Fontes lidas por trechos de busca; Medium/Low precisam de conferência na fonte primária.
- Rubricas (~42% do peso) aplicadas por um único analista; template para mais avaliadores em `outputs/plant/plant_rubric_ratings_template.csv`.
- Salários com definições diferentes entre países (indústria vs. todos os setores, capital vs. país).
- Aqueduct 3.0 (o portal 4.0 estava bloqueado). Rotas marítimas aproximadas (±10%).
- Sem preço de açúcar para os países listados como lacuna acima; a métrica sai e os pesos são renormalizados.