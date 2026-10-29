# Contexto para outra IA: ranking de países para o AlgaPrime DHA (Corbion)

*Atualizado em 29/10/2026. Repositório `lbenozzati/agroinsper`, branch `claude/corbion-dha-site-evaluation-e13c6j`, pasta `microalgae_site_selection/country_ranking/`.*

Este documento serve para outra IA (ou analista) entender o que foi feito, por que foi feito assim e como adaptar e melhorar sem quebrar o que já funciona. Leia inteiro antes de mexer no código.

---

## 1. O projeto em uma frase

Trabalho acadêmico/consultivo da **AgroInsper** com um fundo (**Aqua Capital**) sobre a **Corbion**, que produz o **AlgaPrime DHA**: ômega-3 DHA de microalgas feito por fermentação em **Orindiúva (SP, Brasil)** e vendido como ingrediente de ração. Há duas perguntas:

1. **Prompt 1 (`plant`):** em que país construir a nova capacidade de fermentação? Resultado: Brasil 7,03, Tailândia 6,25, EUA 5,98.
2. **Prompt 2 (`market`):** para quais países e nichos (salmão, camarão, pet food) expandir as vendas? Este foi o foco das últimas sessões.

O deck do usuário (slide "Value Creation: Accelerating Algae Capacity Expansion") propõe nova capacidade em Orindiúva em 2029. Ele mostra TIR 17,34%, VPL €207 mi e capex €76 mi; **esses números vêm do deck do usuário e não foram recalculados aqui**. A sequência de entrada no deck é:
- 2029: Noruega e Chile;
- 2030: Reino Unido e China;
- 2031: Equador;
- 2033: capacidade plena.

O gráfico "Market Expansion" do deck usa o ranking geral deste repositório: Noruega 7,5; Chile 7,1; Reino Unido 6,2; Equador 5,8; China 5,8.

## 2. Quem é o usuário e como trabalhar com ele

- Escreve em **português**, informal e curto. Responda em português. Textos para o deck podem ser pedidos em inglês.
- Prefere **texto corrido, sem tabelas**, quando pede explicação. Gráficos devem seguir a estética do deck: fundo azul-marinho → roxo, fonte Montserrat, azul `#3987e5`, magenta `#d55181`, violeta `#9085e9`.
- Tem uma **tese**: China deve aparecer bem (camarão e salmão). Já pediu para "deixar a China em 5º".
- **Regra que foi seguida e deve continuar:**
  - Não ajustar pesos ou notas só para chegar num resultado-alvo.
  - Premissas de negócio explícitas do usuário podem entrar. Elas são aplicadas **a todos os países igualmente** e documentadas como premissa no README e no CSV de rubricas.
  - Foi assim que a China subiu: com dados reais (salmonídeos domésticos, tarifa provisória de 4%, BioMar–Tongwei em Wuxi, aprovação GACC de 2025) e com as premissas Corbion abaixo, não com chute.
- **Premissas Corbion declaradas pelo usuário (26/10/2026):**
  1. Na aquicultura, a Corbion vende **só para a BioMar**. O canal é medido pela presença, capacidade e número de fábricas da BioMar no país. Em pet food o canal é o distribuidor IQI.
  2. **Preço importa, prazo não.** Logística pesa só 5% dentro de "acesso". A tarifa da China é a aplicada provisória de 4%, não a MFN de 6,5%.
  3. Em salmão e camarão, "só a Corbion está" focada em DHA de algas. Os produtores chineses (CABIO, Runke, Huison) competem só em pet food. A Veramaris conta como concorrente só onde há uso documentado (Noruega, EUA, Canadá).
  4. No ranking geral, **salmão e camarão pesam mais**; pet food é minoria (45/40/15).
- O usuário disse que tem "fontes boas" mas **ainda não as enviou**. Quando enviar, registre-as em `data/rev2026/source_registry.csv` e nas linhas de componente que elas sustentam, e rode tudo de novo.

## 3. Dois modelos de mercado convivem: não os confunda

| | Modelo 14/10 ("versão do deck") | Revisão rev2026 ("versão de decisão / auditoria") |
|---|---|---|
| Código | `src/market.py`, `src/market_report.py`, `src/scoring.py` | `src/rev2026/markets.py`, `interval.py`, `pipeline.py` |
| Config | `config_market.yaml` | `config_rev2026.yaml` |
| Saídas | `outputs/market/` | `outputs/rev2026/` |
| Nota | ponto único 0–10 | intervalo piso/teto |
| Dado ausente | sai da conta e o peso é redistribuído | 0 no piso e 10 no teto |
| Rodar | `python -m src market` (~3 min) | `python -m src rev2026` (~40 s–1 min) |

- O **deck usa o modelo 14/10**.
- A revisão rev2026 é a conferência mais conservadora.
- `outputs/frozen_2026-10-14/` é a cópia congelada original de 14/10. **Não sobrescreva.**
- `outputs/market/` é o 14/10 atualizado com as mudanças de 26/10.

## 4. Como o modelo 14/10 funciona

### 4.1 Coleta
- Os dados brutos por nicho estão em `data/raw/market_research/p2b_{salmon,shrimp,pet}.csv`, e o risco país em `p2b_country_risk.csv`.
- Cada valor tem fonte, ano, tipo e confiança (High/Medium/Low).
- Quase tudo veio de **trechos de busca**: os portais primários eram bloqueados no ambiente. Nada foi "lido do original".
- A base consolidada está em `data/processed/market_inputs_long.csv`.

### 4.2 Dado → nota 0–10
- Métrica numérica: régua linear pior→melhor (`worst`/`best` no YAML). Exemplo: tarifa 15% = 0 e 0% = 10.
- Volumes (produção, DHA técnico) usam **escala log**.
- Rubricas (`method: rubric`) usam a nota 0–10 direto.
- Dado ausente sai da conta e o peso é redistribuído.
  - Uma métrica com cobertura < 40% dos países é descartada.
  - Um país com < 50% do peso coberto é marcado "dados insuficientes" e vai para o fim.

### 4.3 Rubricas por componentes
São três rubricas, cada uma somando até 10:
- `{p}_relationship` — canal;
- `{p}_registration` — registro;
- `{p}_competitive` — posição competitiva.

Elas são geradas por `data/raw/tools/build_rubric_components.py`, que cria `data/raw/market_rubric_components.csv` (494 linhas). Cada componente tem `lo`, `hi`, evidência e fonte. O 14/10 usa o ponto médio; a rev2026 usa `lo`/`hi` como intervalo.

- **Canal:**
  - A: estágio comercial, 0–4;
  - B: capacidade BioMar, 0–3;
  - C: nº de fábricas BioMar, 0–2;
  - D: presença Corbion, 0–1.
  - Em pet food, o distribuidor IQI substitui a BioMar.
- **Registro:**
  - A: status legal, 0–4;
  - B: prazo, 0–2;
  - C: barreiras, 0–2;
  - D: incentivo, 0–2.
- **Competição:**
  - A: concorrente de algas documentado, 0–3. Se não encontrado, o intervalo é 2–3, nunca 3 cheio.
  - B: ajuste do produto ao nicho: salmão 1, camarão 2, pet 2.
  - C1: ausência de produção local concorrente.
  - C2: tarifa aplicada ≤ 5%.
  - D: alavanca de marca, 0–2.

Para mudar uma nota de rubrica, **edite os dicionários no gerador** (`canal`, `reg`, `compA`, `compD`, `FIT`, `LOCAL`, `TARIFF`) e rode:
```bash
python -I data/raw/tools/build_rubric_components.py data/raw/market_rubric_components.csv
```
Não edite o CSV gerado à mão. `data/raw/market_rubrics.csv` é a camada antiga; ela é sobrescrita pelos componentes nas três rubricas acima.

### 4.4 Critérios e pesos (cenário base, iguais nos três nichos)
- **Acesso e posição competitiva: 30%.** Dentro dele:
  - posição competitiva 35%;
  - canal 20%;
  - adoção documentada 20%;
  - fábricas dos grandes de ração 20%;
  - logística 5%.
- **Tamanho e crescimento: 25%.** Volume e DHA técnico 65%, crescimento 35%.
- **Valor e disposição a pagar: 15%.** Preço do produto final; certificação (salmão) ou intensificação e larvicultura (camarão).
- **Regulação e acesso comercial: 15%.** Tarifa 50%, registro 50%.
- **Risco país e biológico: 15%.** Rating S&P, WGI e câmbio 65%; mortalidade ou doenças 35%.

Os outros cenários são: "Pesos 14-10" (30/20/20/15/15), Consolidação, Crescimento e "Mercado e regulação" (25/25/15/25/10).

### 4.5 Ranking geral
Em `src/market.py`, a função `overall()`:
- **Qualidade** = Σ nota do nicho × (peso do nicho × DHA técnico do país no nicho), normalizada dentro do país. Os pesos estão em `niche_weights: {salmon: 0.45, shrimp: 0.40, pet: 0.15}`.
- **Relevância** = média dos pesos de nicho ponderada pelo DHA ÷ maior peso. Vale 1 se o país é só salmão.
- **Nota geral** = qualidade × (0,5 + 0,5 × relevância). O 0,5 é o `relevance_floor`.
- Efeito: um país forte só em pet food é descontado. Os EUA têm qualidade 7,07, mas relevância 0,35, e ficam com nota geral 4,76 (12º).

### 4.6 Robustez
- 5 cenários de pesos.
- 4.000 sorteios Dirichlet de pesos (% de vezes em 1º e no top 3).
- 600 simulações Monte Carlo variando os dados conforme a confiança de cada um.
- Notas de controle: só métricas quantitativas, ausente = 0 e ausente = 10.
- Destaques:
  - Noruega 1º em salmão em 96% dos sorteios de pesos;
  - China 1º em camarão em 74% dos sorteios e no top 3 em 100%;
  - nos dados, China 1º em camarão em 69% das simulações.

## 5. Resultados atuais (modelo 14/10, cenário base)

- **Salmão:**
  1. Noruega 7,53
  2. Chile 7,12
  3. Reino Unido 6,76
  4. Austrália 5,35
  5. Nova Zelândia 5,13
  6. Ilhas Faroé 5,13
  - China é 8ª, com 4,83.
- **Camarão:**
  1. China 6,47
  2. Equador 6,14
  3. Vietnã 5,70
  4. Tailândia 5,69
  5. Indonésia 5,03
  6. Índia 4,91
- **Pet food:**
  1. EUA 7,24
  2. França 6,30
  3. Alemanha 6,27
  4. Canadá 6,20
  5. Itália 6,12
- **Geral:**
  1. Noruega 7,53
  2. Chile 7,12
  3. Reino Unido 6,25
  4. Equador 5,80
  5. China 5,78
  6. Vietnã 5,38
  7. Nova Zelândia 5,13
  8. Faroé 5,13
  9. Islândia 5,08
  10. Austrália 4,99
  11. Tailândia 4,87
  12. EUA 4,76
- **Rev2026 (conferência):**
  - salmão: Chile, Noruega, China em 3º;
  - camarão: China 1º (5,75) ≈ Equador (5,70);
  - pares combinados: China–camarão 2º, China–salmão 5º.
- **Recomendação de expansão:**
  - camarão primeiro em China e Equador; Vietnã em segundo plano;
  - consolidar salmão em Noruega, Chile e Reino Unido;
  - Austrália só se a fábrica BioMar da Tasmânia for confirmada;
  - pet food nos EUA de forma oportunista;
  - evitar Índia, Arábia Saudita, Bangladesh e Filipinas.

## 6. Mapa de arquivos

```
country_ranking/
  config_market.yaml            pesos, cenários, métricas, goalposts e nichos do 14/10
  config_rev2026.yaml           pesos e métricas da revisão
  config_plant.yaml             Prompt 1 (fábrica)
  src/__main__.py               CLI: python -m src {plant|market|all|rev2026}
  src/market.py                 derive(), rubric_components(), overall(), run_all
  src/scoring.py                normalização, renormalização, Monte Carlo, Dirichlet
  src/market_report.py          heatmaps, contribuições, mapa, gráfico geral, memo
  src/charts.py                 estética (slide(), cores, fontes em ../assets/fonts)
  src/rev2026/                  motor por intervalo, gates, DCF v3, slides 1–5
  data/raw/market_research/     dados por nicho (p2b_*.csv)
  data/raw/tools/build_rubric_components.py   gerador das rubricas
  data/raw/market_rubric_components.csv       gerado; não editar à mão
  data/rev2026/source_registry.csv            fontes R1..R48 com nível L0–L3
  data/rev2026/customer_factory_matrix.csv    fábricas de clientes (C1..C25)
  outputs/market/               rankings CSV, PNGs, memo do 14/10 atualizado
  outputs/rev2026/              revisão, memo, slides
  outputs/frozen_2026-10-14/    cópia congelada, não mexer
  tests/                        test_market.py, test_plant.py, test_rev2026.py
  README.md                     método completo, incluindo as seções de 26/10
```

O briefing histórico completo do projeto está em `../HANDOFF.md`. Ele cobre v3, DCF, market_expansion e integrated_strategy.

## 7. Como rodar e validar

```bash
cd microalgae_site_selection/country_ranking
python -I data/raw/tools/build_rubric_components.py data/raw/market_rubric_components.csv   # se mudou rubrica
python -m src market      # ~3 min; use timeout longo
python -m src rev2026     # ~1 min
python -m pytest -q tests # 34 testes passam
```

- Há uma checagem automática conhecida que **falha**: julgamento ≤ 10% do peso em camarão está em 19,5%, em `outputs/rev2026/automated_checks.csv`. A falha foi informada ao usuário e não está escondida.
- Commits terminam com as linhas de coautoria do projeto. Faça push na mesma branch.

## 8. Armadilhas já encontradas

- O TAM de salmão da China usa produção × eFCR 1,3 × inclusão de DHA. A divisão é por **1e3**, não 1e6; o resultado é ≈ 344,5 t.
- No pandas, `rubric_components` precisa de `.astype({"lo": object, "hi": object, "evidence": object})`, senão dá erro de dtype.
- Um nome de cenário que gere uma coluna `rank_*` igual a outra (ex.: "Base ...") colide com `rank_base`.
- Ao adicionar um país a um nicho no 14/10, confira se `src/rev2026/markets.py` continua injetando só a linha de TAM com intervalo.
- No deck: "Equator" deve ser **"Ecuador"**, "Uk" deve ser **"UK"**, e Equador (5,80) e China (5,78) não estão empatados.

## 9. O que pode ser melhorado (sugestões priorizadas)

1. **Fontes do usuário.** Incorporá-las quando chegarem. Prioridade: capacidade BioMar por fábrica (B e C do canal), uso real de AlgaPrime por país e preço líquido realizável do ingrediente.
2. **Preço líquido do ingrediente.** Hoje "valor" usa o preço do peixe ou camarão, que é um proxy. A premissa "preço importa" pede o preço entregue do DHA por país, já com a tarifa.
3. **Reduzir julgamento em camarão** (19,5% → ≤ 10%), trocando componentes "não encontrado" por evidência documental.
4. **Dados ausentes:**
   - China salmão: CAGR, certificação e mortalidade;
   - Equador: pós-larvas e tarifa;
   - Chile: certificação.
5. **Validar `niche_weights` 45/40/15** com receita ou volume real da Corbion por nicho, em vez de premissa.
6. **Austrália:** confirmar a fábrica BioMar na Tasmânia.
7. **Ligar o ranking ao DCF.** A sequência de entrada do deck (2029–2033) poderia sair do ranking com volume por país e a capacidade nova. Hoje é só narrativa.
8. **Se mudar pesos:** declarar a razão no YAML, rodar a robustez e mostrar antes/depois. Nunca escolher pesos olhando o resultado.

## 10. Entregáveis de texto e slide desta rodada

Pasta `outputs/market/entrega/`:
- `analise_paises_expansao.txt`: análise completa em texto corrido, com as fontes e URLs (seção 9).
- `slide_metodologia.png`: slide-resumo com notas 0–10, critérios e pesos, ranking geral e robustez.
- `slide_metodologia.py`: script do slide. Usa `src.charts`; rode-o a partir de `country_ranking/` depois de ajustar o caminho de saída.

Os números desses arquivos são escritos à mão. Se o modelo mudar, atualize-os.
