# Estratégia integrada: capacidade, origem, mercados e momento do investimento em DHA (Corbion)

*Corte 2026-10-14 · commit 2a44797 · v3 3.0.0 · mercado 1.0.0 · seed 42 · 400 simulações conjuntas · testes de origem: v3 24 passed in 1.44s, mercado 13 passed in 8.26s*

**Rótulos usados:**

- **[observado]:** dado público com fonte, lido por trecho de busca.
- **[derivado]:** cálculo sobre dados observados.
- **[hipótese]:** premissa explícita.

Não houve acesso a contratos, preços realizados nem dados internos da Corbion. Toda conclusão abaixo é **condicional**.

## 1. Decisão de hoje

**Não aprovar FID de nova fermentação agora.** [derivado] Com a demanda do estudo de mercado (cenário base, sem contratos públicos), a melhor política é **Esperar (nenhum capex)**.

- Expandir Orindiúva com 1 módulo dá VPL de US$ -32 mi.
- Adiar a expansão em 2 anos dá US$ -23 mi.
- Orindiúva + Tailândia desde o início dá US$ -227 mi.

**Monte Carlo conjunto** (cópula com custos da v3 e premissas de mercado, óleo de peixe compartilhado):

- E[VPL] de A = US$ -38 mi;
- P(VPL > 0) = 26%;
- política de maior E[VPL]: **Esperar (nenhum capex)**.

Essas probabilidades são **condicionais às distribuições assumidas**, não previsões calibradas.

**Primeiro investimento reversível** (custo baixo, preserva a opção):

1. contrato de açúcar e vapor adicionais com a usina de Orindiúva;
2. engenharia conceitual do módulo (fecha a dúvida sobre quanta capacidade os €50 mi compram);
3. conversão do pipeline de salmão (Noruega/Chile) em contratos com volume e preço.

Terreno, EPC e FID da Tailândia ficam para depois dos gatilhos da seção 2.

## 2. Quando a recomendação muda (gatilhos físicos e monetários)

- **Orindiúva (A) passa a ter VPL ≥ 0** com ≥ **5.125 t/ano contratadas firmes** desde 2029, sem nenhum pipeline. Com o pipeline ponderado da v3 somado, bastam ≥ 1.250 t/ano. [derivado]
- **A 2ª planta na Tailândia (B) supera só-Orindiúva** com ≥ **13.385 t/ano de volume asiático contratado** no preço-base, ou ≥ 9.556 t/ano com preço 40% maior. O capex de Orindiúva não move essa fronteira: ele está nas duas políticas e se cancela na diferença. [derivado]
- **Nakhon Sawan como única planta (em vez de Orindiúva)**: menor preço em que vence, por nível de capex de Orindiúva (Fonte: `break_even_frontier_lines.csv`):
  - capex de Orindiúva US$ 60 mi: vence a partir de US$ 40,0/kg DHA, com ≥ 5.000 t/ano asiáticas contratadas;
  - capex de Orindiúva US$ 92 mi: vence a partir de US$ 35,0/kg DHA, com ≥ 4.000 t/ano asiáticas contratadas;
  - capex de Orindiúva US$ 140 mi: vence a partir de US$ 25,0/kg DHA, com ≥ 1.000 t/ano asiáticas contratadas;
- **Mercado alto** (todas as premissas favoráveis): o melhor passa a ser **B Orindiúva + Tailândia desde o início (2030)**, com VPL de US$ 1.036 mi. A Tailândia esperando gatilho de utilização (C') fica próxima: US$ 1.019 mi. [hipótese de mercado]

**Fronteira de contrato asiático por preço e capex** (mínimo para B > A):

| Capex Orindiúva | Preço (US$/kg DHA) | Ásia contratada mínima p/ B > A | Ásia mínima p/ Nakhon Sawan sozinha > Orindiúva | Melhor sem contrato |
|---|---|---|---|---|
| 60 | 15,0 | > 12.000 | > 12.000 | WAIT (no positive NPV) |
| 60 | 20,0 | > 12.000 | > 12.000 | WAIT (no positive NPV) |
| 60 | 25,0 | > 12.000 | > 12.000 | A_ORI_1 |
| 60 | 30,0 | 12.000 | > 12.000 | A_ORI_1 |
| 60 | 35,0 | 10.000 | > 12.000 | A_ORI_1 |
| 60 | 40,0 | 10.000 | 5.000 | A_ORI_1 |
| 60 | 45,0 | 10.000 | 4.000 | A_ORI_1 |
| 92 | 15,0 | > 12.000 | > 12.000 | WAIT (no positive NPV) |
| 92 | 20,0 | > 12.000 | > 12.000 | WAIT (no positive NPV) |
| 92 | 25,0 | > 12.000 | > 12.000 | WAIT (no positive NPV) |
| 92 | 30,0 | 12.000 | > 12.000 | WAIT (no positive NPV) |
| 92 | 35,0 | 10.000 | 4.000 | A_ORI_1 |
| 92 | 40,0 | 10.000 | 3.000 | A_ORI_1 |
| 92 | 45,0 | 10.000 | 2.000 | A_ORI_1 |
| 140 | 15,0 | > 12.000 | > 12.000 | WAIT (no positive NPV) |
| 140 | 20,0 | > 12.000 | > 12.000 | WAIT (no positive NPV) |
| 140 | 25,0 | > 12.000 | 1.000 | WAIT (no positive NPV) |
| 140 | 30,0 | 12.000 | 0 | WAIT (no positive NPV) |
| 140 | 35,0 | 10.000 | 0 | WAIT (no positive NPV) |
| 140 | 40,0 | 10.000 | 0 | WAIT (no positive NPV) |
| 140 | 45,0 | 10.000 | 0 | A_ORI_1 |

## 3. Comparação das políticas

VPL nominal em USD, com valor terminal; demanda do estudo de mercado ponderada pelos pesos da v3.

| Política | Mercado baixo | Mercado base | Mercado alto | E[VPL] MC | p10 | CVaR 10% | P(VPL>0) |
|---|---|---|---|---|---|---|---|
| Esperar (nenhum capex) | 0 | **0** | 0 | 0 | 0 | 0 | 0% |
| A Orindiúva 1 módulo (2028) | -153 | **-32** | 521 | -38 | -110 | -124 | 26% |
| A' Orindiúva 1 módulo adiado (2030) | -135 | **-23** | 439 | -28 | -95 | -107 | 28% |
| A2 Orindiúva 2 módulos (2º se utilização ≥ 80%) | -153 | **-32** | 898 | -38 | -110 | -124 | 25% |
| A2' Orindiúva 2 módulos (2º em 2032) | -280 | **-147** | 864 | -162 | -253 | -272 | 2% |
| B Orindiúva + Tailândia desde o início (2030) | -348 | **-227** | 1.036 | -255 | -333 | -354 | 0% |
| B' Orindiúva + Tailândia 2032 | -329 | **-208** | 977 | -233 | -310 | -330 | 0% |
| C Orindiúva + Tailândia se demanda asiática ≥ gatilho | -153 | **-32** | 521 | -38 | -110 | -124 | 26% |
| C' Orindiúva + Tailândia se Orindiúva ≥ 80% | -153 | **-32** | 1.019 | -38 | -111 | -125 | 25% |
| D Orindiúva + hub asiático (sem fermentação) | -173 | **-48** | 507 | -55 | -130 | -144 | 19% |

- **Maior retorno esperado:** Esperar (nenhum capex).
- **Menor perda extrema entre as políticas com capex:** A' Orindiúva 1 módulo adiado (2030) (CVaR 10% de US$ -107 mi).
- **Robustez à dependência:** com cópula independente, o E[VPL] de A muda de -38 para -37 US$ mi. A ordem das políticas muda; ver monte_carlo_policy_summary.csv.
- **Escopo do modelo:** a otimização de alocação por região é exata (caminhos mínimos sucessivos, conferidos com `linprog`). As políticas são comparadas por enumeração auditável, sem MILP, porque o espaço é pequeno. Ficam fora do modelo: estoque de segurança, múltiplos SKUs, sazonalidade de entressafra e restrição de usina por mês.

## 4. Tamanho da oportunidade por nicho e rota

Margem entregue por kg de DHA em 2030 (preço líquido − custo variável do site − frete − trânsito − tarifa):

| Destino | Orindiúva | Nakhon Sawan | Origem de maior margem | Inverte se frete BR subir (US$/t) | Inverte se açúcar TH cair (US$/t sacarose) |
|---|---|---|---|---|---|
| Norway · salmon | 15,8 | 12,2 | Orindiúva | 1.240 | 253 |
| Chile · salmon | 15,8 | 12,2 | Orindiúva | 1.240 | 253 |
| Thailand · shrimp | 13,3 | 10,4 | Orindiúva | 1.012 | 206 |
| Ecuador · shrimp | 13,3 | 9,8 | Orindiúva | 1.237 | 252 |
| Vietnam · shrimp | 12,1 | 9,2 | Orindiúva | 1.018 | 207 |
| United States · pet_food | 19,4 | 16,0 | Orindiúva | 1.191 | 242 |
| European Union · pet_food | 19,4 | 16,0 | Orindiúva | 1.191 | 242 |

- **Orindiúva tem a maior margem unitária para todos os destinos, inclusive camarão asiático.** O açúcar mais caro na Tailândia pesa mais que o frete mais curto. [derivado]
- **O mercado mais próximo não gera automaticamente o maior VPL:** escala, utilização e a infraestrutura existente em Orindiúva decidem.
- **Teor de DHA:** é o mesmo SKU nas duas plantas, então não altera a escolha da origem.

**Carteira por marco** (política A, mercado base):

| Ano | Firme | Pipeline qualificado | Potencial | Capacidade | Folga | Top-3 países | Participação top-3 |
|---|---|---|---|---|---|---|---|
| 2028 | 0 | 1.040 | 20 | 4.250 | 3.189 | Norway, Chile, United Kingdom | 96% |
| 2030 | 0 | 1.885 | 34 | 8.500 | 6.581 | Norway, Chile, United Kingdom | 95% |
| 2035 | 0 | 3.148 | 81 | 8.500 | 5.272 | Norway, Chile, United Kingdom | 94% |

A concentração aparece por país de formulação. A participação dos três maiores **clientes** é desconhecida, porque a tonelagem por conta não é pública.

## 5. Diversificação: valor sob stress (cenário econômico explícito)

| Mercado | Stress | Perda de A | Perda de B | Valor de resiliência (B − A) |
|---|---|---|---|---|
| base | Fretes do Brasil para Ásia ×3 em toda a vida (ruptura de rota) | 0,0 | 0,0 | 0,0 |
| base | Orindiúva (todas as unidades do site) parada 6 meses em 2031 | 0,0 | 0,0 | 0,0 |
| base | Orindiúva parada 12 meses em 2033 | 7,4 | 2,0 | 5,4 |
| base | Construção asiática atrasa 2 anos | 0,0 | -14,3 | 14,3 |
| high | Fretes do Brasil para Ásia ×3 em toda a vida (ruptura de rota) | 0,0 | 0,0 | -0,0 |
| high | Orindiúva (todas as unidades do site) parada 6 meses em 2031 | 20,3 | 10,5 | 9,8 |
| high | Orindiúva parada 12 meses em 2033 | 36,4 | 35,4 | 0,9 |
| high | Construção asiática atrasa 2 anos | 0,0 | 64,5 | -64,5 |

**Leitura:**

- No mercado base há capacidade ociosa, então paradas custam pouco e a diversificação vale quase nada.
- No mercado alto, uma parada de Orindiúva custa até US$ 36 mi. A segunda planta recupera só uma parte, porque também opera cheia.
- Esse valor de resiliência é pequeno perto do VPL negativo de construir cedo. **A diversificação não justifica sozinha a Tailândia.**
- No stress de atraso da Tailândia, o valor positivo no mercado base significa que **atrasar a planta tailandesa reduz a perda**. Não é um benefício de resiliência.

## 6. Sequência de decisões reversíveis e valor de esperar

- Orindiúva agora vs adiar 2 anos (base): US$ -9,0 mi (positivo = custo de esperar (vendas perdidas) > economia de adiar capex)
- Orindiúva agora vs adiar 2 anos (alto): US$ 81,8 mi (idem)
- E[VPL] Tailândia por gatilho de utilização − Tailândia já (MC): US$ 216,9 mi (valor da opção de esperar pelo gatilho)
- E[VPL] 2º módulo Orindiúva por gatilho − fixo 2032 (MC): US$ 124,2 mi (valor do faseamento)
- E[VPL] melhor política MC − Esperar: US$ 0,0 mi (melhor em média: WAIT)

**Marcos verificáveis:**

1. contratos de açúcar e vapor;
2. engenharia conceitual e capex por módulo;
3. contratos de salmão até ≥ 5.125 t/ano firmes (ou equivalente com pipeline qualificado), o que leva ao FID de Orindiúva;
4. qualificação de clientes asiáticos e estoque avançado (hub, se o custo for menor que a captura extra);
5. volume asiático contratado na fronteira (≥ 13.385 t/ano no preço-base), mais diligência de Nakhon Sawan (terreno, KTIS, água, BOI/GloBE), o que leva ao FID da Tailândia.

## 7. Valor de fechar as lacunas (ordem por impacto na decisão e esforço)

| Informação | Como fechar | Esforço | Melhor política (min → máx) | Muda a decisão? | Swing do melhor VPL (US$ mi) |
|---|---|---|---|---|---|
| Mercado capturável (estudo de mercado baixo/alto) | Entrevistas, ensaios, CRM | high | WAIT → B_ORI_TH_NOW | sim | 1.036,4 |
| Preço líquido por SKU | Contratos e listas de preço | medium | WAIT → A_ORI_DELAY | sim | 29,4 |
| Offtake efetivo (conversão do pipeline) | Contratos com feed mills | high | WAIT → A_ORI_DELAY | sim | 19,0 |
| Capacidade comprada pelos €50 mi (capex por módulo de Orindiúva) | Engenharia conceitual / Corbion | medium | A_ORI_DELAY → WAIT | sim | 11,2 |
| Rendimento industrial DHA/açúcar | Dados de operação de Orindiúva | low | WAIT → WAIT | não | 0,0 |
| Proposta EPC Tailândia | Cotação EPC / FEED | medium | WAIT → WAIT | não | 0,0 |
| Frete cotado | Cotações de forwarders | low | WAIT → WAIT | não | 0,0 |
| Prazo de licenciamento Tailândia (anos de atraso) | BOI / ONEP / DIW | medium | WAIT → WAIT | não | 0,0 |

Sem probabilidades defensáveis para cada informação, isto é o **valor de fechar a lacuna** (variação do melhor VPL e mudança de política), não um valor da informação esperado (EVPI).

## 8. Correlação e risco: o que é estatística e o que é hipótese

- **Séries históricas comparáveis:** não existem no repositório (`empirical_series_status.csv`).
  - O preço do AlgaPrime não é público.
  - Do óleo de peixe há dois pontos conflitantes de 2026.
  - Açúcar e câmbio têm só pontos isolados.
  - Por isso **nenhum coeficiente, beta, R² ou p-valor foi estimado**. A função `stats.empirical_correlation` exige ≥ 24 observações e trabalha em primeiras diferenças.
- **Mecanismos** (`risk_dependency_register.csv`), separados em:
  - documentados (produção → ração; açúcar → custo; câmbio → custo local);
  - hipóteses plausíveis (óleo de peixe → preço via repasse de 0,4; óleo de peixe → adoção);
  - não identificáveis (efeito líquido do óleo de peixe na demanda de ração; El Niño → cana/água).
- **Monte Carlo:** usa priors transparentes (matriz `joint_correlation_matrix.csv`, PSD verificada) e uma corrida independente para robustez.
- **Risco no WACC × no fluxo:** o risco-país entra só no WACC; parada, atraso e demanda entram só no fluxo, sem penalidade dupla.

## 9. Por que difere do heatmap original (score de países v2)

- **O que o v2 respondia:** "qual país pontua melhor". Brasil 7,15 e Tailândia 6,76. Cerca de 65% do peso vinha de rubricas de um único avaliador, e, sem elas, o Brasil cai para 6º. [derivado na v3]
- **O que este estudo responde:** "qual combinação de capacidade, origem, carteira e momento cria valor". Uma boa nota de país não cria demanda.
  - Com a demanda bottom-up do estudo de mercado, o volume incremental plausível em 2030 é de ~3.254 t (base, antes dos pesos de probabilidade da v3).
  - Isso é menos que meio módulo de Orindiúva. Por isso **esperar/qualificar** vence construir.
- **O que se mantém do v2:** o Brasil (Orindiúva) é a origem de menor custo e maior margem em todas as rotas. Quando houver volume, a primeira capacidade deve ser lá.
- **O que muda:** a Tailândia deixa de ser "2º melhor país". Passa a ser uma opção condicionada a ≥ 13.385 t/ano de contratos asiáticos, um volume que o estudo de mercado hoje não sustenta.

## 10. Evidência indispensável antes de qualquer FID

1. Volume e preço realizados por SKU e mercado (Corbion), para reconciliar o SOM bottom-up (~US$ 25 mi) com Nutrition (€157 mi).
2. Contratos ou cartas de intenção de offtake com volume, preço e prazo.
3. Capacidade comprada pelos €50 mi e capex por módulo (engenharia).
4. Contrato de açúcar e vapor com a usina e restrição de entressafra.
5. Escopo GACC por planta.
6. Parecer sobre GloBE/BOI.
7. Cotações de frete e EPC.

## 11. Integração e rastreabilidade

- **Reconciliação** (`integration_reconciliation.csv`):
  - DHA por SKU harmonizado em 0,35;
  - preço de mercado líquido de custos comerciais e rebates (capital de giro na v3);
  - repasse do óleo de peixe aplicado uma única vez;
  - Incoterm tipo DAP;
  - demanda incremental (sem vendas atuais) e sem dupla contagem de clientes.
- **Rotas:** cada uma cita as fontes de preço, custo, frete e tarifa (`route_economics.csv`). As tarifas estão em 0 e **não verificadas**.
- **Proveniência:** commits, versões, datas de corte e hashes das tabelas consumidas estão em `run_manifest.json`.
