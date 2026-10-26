# Melhores países para a Corbion expandir o AlgaPrime DHA – salmão, camarão e pet food

*Gerado por `python -m src market` · ranking ponderado por nicho (5 critérios: tamanho e crescimento 30%, valor 20%, acesso e posição competitiva 20%, regulação 15%, risco 15%) e ranking geral. O critério de acesso inclui **logística até o cliente** (25% do critério): dias porta a porta desde Orindiúva por rota marítima, LPI 2023 e conectividade marítima (UNCTAD) do destino. Mostra o top 10 de cada nicho; todos os países avaliados estão nos CSVs.*

> **Natureza do resultado.** Score de triagem 0–10, não receita nem VPL. Fontes públicas, em boa parte lidas por trechos de busca; cada valor tem fonte, tipo e confiança em `data/processed/market_inputs_long.csv`. O volume e a receita por mercado continuam no estudo `market_expansion/`.

## 1. Resposta

**Ranking geral (top 5):** 1. Noruega (7,53, melhor nicho: salmão), 2. EUA (7,18, melhor nicho: pet food), 3. Chile (7,12, melhor nicho: salmão), 4. Reino Unido (6,58, melhor nicho: salmão), 5. França (6,30, melhor nicho: pet food).

- **Salmão:** 1º Noruega (7,53), 2º Chile (7,12), 3º Reino Unido (6,76). Noruega é 1º em 96% dos sorteios de pesos e em 74% das simulações de dados; só com métricas quantitativas o 1º é Noruega.
- **Camarão:** 1º China (6,47), 2º Equador (6,14), 3º Vietnã (5,70). China é 1º em 74% dos sorteios de pesos e em 69% das simulações de dados; só com métricas quantitativas o 1º é China.
- **Pet food:** 1º EUA (7,24), 2º França (6,30), 3º Alemanha (6,27). EUA é 1º em 100% dos sorteios de pesos e em 85% das simulações de dados; só com métricas quantitativas o 1º é EUA.

**Consolidar vs. expandir:** países onde a Corbion já tem adoção documentada (score de acesso alto) são consolidação; países com tamanho/crescimento altos e acesso baixo são expansão. Ver seção 3.

## 2. Rankings por nicho

### Salmão – top 10 de 11 países avaliados

| # | País | Score | Tamanho/cresc. (30%) | Valor (20%) | Acesso (20%) | Regulação (15%) | Risco (15%) | Dias desde Orindiúva | DHA técnico (t) | P(1º) pesos | Cobertura de dados |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Noruega | **7,53** | 8,2 | 4,3 | 7,9 | 9,0 | 7,5 | 22 | 13.091 | 96% | 92% |
| 2 | Chile | **7,12** | 8,1 | 2,6 | 8,1 | 8,0 | 7,1 | 18 | 7.632 | 0% | 92% |
| 3 | Reino Unido | **6,76** | 5,3 | 7,3 | 6,7 | 9,0 | 6,5 | 22 | 1.272 | 3% | 86% |
| 4 | Austrália | **5,35** | 4,4 | 7,5 | 5,3 | 4,0 | 6,2 | 34 | 492 | 0% | 83% |
| 5 | Nova Zelândia | **5,13** | 4,2 | 10,0 | 2,2 | 4,0 | 8,9 | 30 | 86 | 1% | 78% |
| 6 | Ilhas Faroé | **5,13** | 6,2 | 5,6 | 2,2 | 6,0 | 7,9 | 23 | 729 | 0% | 83% |
| 7 | Islândia | **5,08** | 6,3 | 3,8 | 2,2 | 7,0 | 8,2 | 23 | 389 | 0% | 81% |
| 8 | China | **4,83** | 6,2 | 3,5 | 4,1 | 5,0 | 5,3 | 35 | 331 | 0% | 85% |
| 9 | Canadá | **4,74** | 3,5 | 4,4 | 3,6 | 5,0 | 9,1 | 32 | 729 | 0% | 81% |
| 10 | EUA | **4,60** | 2,8 | 5,0 | 2,4 | 7,5 | 8,7 | 29 | 80 | 0% | 85% |

### Camarão – top 10 de 12 países avaliados

| # | País | Score | Tamanho/cresc. (30%) | Valor (20%) | Acesso (20%) | Regulação (15%) | Risco (15%) | Dias desde Orindiúva | DHA técnico (t) | P(1º) pesos | Cobertura de dados |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | China | **6,47** | 8,3 | 7,5 | 5,9 | 6,5 | 3,5 | 35 | 4.925 | 74% | 93% |
| 2 | Equador | **6,14** | 9,2 | 2,9 | 6,4 | 5,0 | 4,8 | 22 | 6.696 | 24% | 88% |
| 3 | Vietnã | **5,70** | 6,7 | 7,2 | 4,8 | 5,9 | 4,0 | 33 | 3.024 | 0% | 100% |
| 4 | Tailândia | **5,69** | 4,6 | 8,6 | 5,5 | 6,2 | 4,4 | 34 | 1.021 | 1% | 100% |
| 5 | Indonésia | **5,03** | 5,3 | 6,4 | 4,1 | 6,4 | 3,9 | 31 | 1.134 | 0% | 94% |
| 6 | Índia | **4,91** | 7,7 | 7,1 | 3,4 | 2,1 | 3,9 | 34 | 3.969 | 0% | 100% |
| 7 | Brasil | **4,87** | 6,5 | 5,0 | 3,4 | 5,7 | 4,1 | 3 | 555 | 0% | 89% |
| 8 | México | **4,36** | 5,5 | 5,9 | 3,2 | 4,0 | 3,6 | 26 | 816 | 0% | 85% |
| 9 | Arábia Saudita | **4,26** | 5,5 | 5,0 | 2,4 | 2,5 | 7,0 | 26 | 245 | 0% | 78% |
| 10 | Filipinas | **3,81** | 4,6 | 5,0 | 2,8 | 3,0 | 4,3 | 36 | 266 | 0% | 78% |

### Pet food – top 10 de 15 países avaliados

| # | País | Score | Tamanho/cresc. (30%) | Valor (20%) | Acesso (20%) | Regulação (15%) | Risco (15%) | Dias desde Orindiúva | DHA técnico (t) | P(1º) pesos | Cobertura de dados |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | EUA | **7,24** | 6,1 | 9,6 | 6,3 | 7,5 | 8,3 | 23 | 3.465 | 100% | 94% |
| 2 | França | **6,30** | 5,5 | 5,6 | 6,0 | 8,0 | 7,2 | 21 | 609 | 0% | 78% |
| 3 | Alemanha | **6,27** | 3,5 | 5,2 | 7,2 | 8,0 | 8,2 | 22 | 528 | 0% | 86% |
| 4 | Canadá | **6,20** | 4,5 | 7,5 | 5,3 | 7,0 | 8,6 | 28 | 287 | 0% | 86% |
| 5 | Itália | **6,12** | 5,5 | 5,0 | 5,9 | 8,0 | 6,7 | 21 | 222 | 0% | 86% |
| 6 | Austrália | **6,02** | 5,5 | 8,9 | 4,3 | 5,0 | 8,4 | 34 | 148 | 0% | 80% |
| 7 | Reino Unido | **5,88** | 4,4 | 5,5 | 5,6 | 7,5 | 7,8 | 21 | 318 | 0% | 86% |
| 8 | Espanha | **5,83** | 4,6 | 4,0 | 6,0 | 8,0 | 7,2 | 20 | 353 | 0% | 86% |
| 9 | Polônia | **5,60** | 5,5 | 1,5 | 5,9 | 8,0 | 6,8 | 23 | 363 | 0% | 86% |
| 10 | Japão | **5,12** | 4,0 | 5,3 | 4,3 | 6,0 | 7,5 | 40 | 187 | 0% | 80% |

## 3. Ranking geral – top 10 de 29 países

| # | País | Score geral | DHA técnico total (t/ano) | Nichos (score) | Papel |
|---|---|---|---|---|---|
| 1 | Noruega | **7.53** | 13.091 | salmão (7.53) | consolidar |
| 2 | EUA | **7.18** | 3.545 | salmão (4.60), pet (7.24) | consolidar |
| 3 | Chile | **7.12** | 7.632 | salmão (7.12) | consolidar |
| 4 | Reino Unido | **6.58** | 1.590 | salmão (6.76), pet (5.88) | consolidar |
| 5 | França | **6.30** | 609 | pet (6.30) | consolidar |
| 6 | Alemanha | **6.27** | 528 | pet (6.27) | consolidar |
| 7 | China | **6.21** | 5.883 | salmão (4.83), camarão (6.47), pet (4.89) | consolidar |
| 8 | Equador | **6.14** | 6.696 | camarão (6.14) | consolidar |
| 9 | Itália | **6.12** | 222 | pet (6.12) | consolidar |
| 10 | Espanha | **5.83** | 353 | pet (5.83) | consolidar |

*Papel:* consolidar = acesso ≥ 5 no melhor nicho; expandir = acesso < 5 e tamanho/crescimento ≥ 5; monitorar = demais.

## 4. Pontos de virada (líder × 2º de cada nicho)

- **Salmão:** Chile passa Noruega se Acesso e posição competitiva ≥ 77% (base 30%).
- **Camarão:** Equador passa China se Tamanho e crescimento ≥ 44% (base 25%); ou Valor e disposição a pagar ≥ 9% (base 15%); ou Acesso e posição competitiva ≥ 57% (base 30%); ou Risco país e biológico ≥ 32% (base 15%).
- **Pet food:** França passa EUA se Regulação e acesso comercial ≥ 70% (base 15%).

## 5. Limitações

- Muitos valores vieram de trechos de busca e alguns de conhecimento do analista (marcados Low); conferir Medium/Low na fonte primária.
- Rubricas de relacionamento e registro aplicadas por um único analista; template em `outputs/market/market_rubric_ratings_template.csv`.
- Salmão: métricas fora do score por cobertura < 40% dos países: sal_certification_share, sal_market_access_tariff (seguem no CSV para quando houver dado).
- Camarão: métricas fora do score por cobertura < 40% dos países: shr_hatchery_pl_billion (seguem no CSV para quando houver dado).
- Pet food: métricas fora do score por cobertura < 40% dos países: pet_manufacturers, pet_import_tariff (seguem no CSV para quando houver dado).
- A necessidade técnica de DHA usa os mesmos g/kg de ração do estudo de mercado para todos os países do nicho (salmão 5,3; camarão 2,7; pet food 0,33 g DHA/kg).