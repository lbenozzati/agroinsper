# Melhores países para a Corbion expandir o AlgaPrime DHA – salmão, camarão e pet food

*Gerado por `python -m src market` · ranking ponderado por nicho (5 critérios: tamanho e crescimento 30%, valor 20%, acesso e posição competitiva 20%, regulação 15%, risco 15%) e ranking geral.*

> **Natureza do resultado.** Score de triagem 0–10, não receita nem VPL. Fontes públicas, em boa parte lidas por trechos de busca; cada valor tem fonte, tipo e confiança em `data/processed/market_inputs_long.csv`. O volume e a receita por mercado continuam no estudo `market_expansion/`.

## 1. Resposta

**Ranking geral (top 5):** 1. Noruega (7,81, melhor nicho: salmão), 2. EUA (7,30, melhor nicho: pet food), 3. Chile (7,23, melhor nicho: salmão), 4. Reino Unido (6,82, melhor nicho: salmão), 5. Alemanha (6,46, melhor nicho: pet food).

- **Salmão:** 1º Noruega (7,81), 2º Chile (7,23), 3º Reino Unido (7,01). Noruega é 1º em 95% dos sorteios de pesos e em 77% das simulações de dados; só com métricas quantitativas o 1º é Noruega.
- **Camarão:** 1º China (6,34), 2º Tailândia (6,29), 3º Equador (6,05). China é 1º em 32% dos sorteios de pesos e em 50% das simulações de dados; só com métricas quantitativas o 1º é China.
- **Pet food:** 1º EUA (7,36), 2º Alemanha (6,46), 3º França (6,37). EUA é 1º em 89% dos sorteios de pesos e em 86% das simulações de dados; só com métricas quantitativas o 1º é EUA.

**Consolidar vs. expandir:** países onde a Corbion já tem adoção documentada (score de acesso alto) são consolidação; países com tamanho/crescimento altos e acesso baixo são expansão. Ver seção 3.

## 2. Rankings por nicho

### Salmão

| # | País | Score | Tamanho/cresc. (30%) | Valor (20%) | Acesso (20%) | Regulação (15%) | Risco (15%) | DHA técnico (t) | P(1º) pesos | Cobertura de dados | Lacunas |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Noruega | **7,81** | 8,2 | 4,3 | 9,4 | 10,0 | 7,5 | 13.091 | 95% | 92% | sal_market_access_tariff |
| 2 | Chile | **7,23** | 8,1 | 2,6 | 8,5 | 10,0 | 7,1 | 7.632 | 0% | 90% | sal_certification_share, sr_fx_volatility |
| 3 | Reino Unido | **7,01** | 5,3 | 7,3 | 7,4 | 10,0 | 6,5 | 1.272 | 4% | 84% | sal_certification_share, sal_market_access_tariff |
| 4 | Ilhas Faroé | **5,78** | 6,2 | 5,6 | 0,6 | 10,0 | 7,9 | 729 | 0% | 80% | sal_growth_5y_cagr, sal_certification_share, sal_market_access_tariff |
| 5 | Austrália | **5,78** | 4,4 | 7,5 | 6,4 | 5,0 | 6,2 | 492 | 0% | 80% | sal_growth_5y_cagr, sal_certification_share, sal_market_access_tariff |
| 6 | Islândia | **5,51** | 6,3 | 3,8 | 0,6 | 10,0 | 8,2 | 389 | 0% | 79% | sal_certification_share, sal_market_access_tariff, sal_mortality_pct |
| 7 | Nova Zelândia | **5,34** | 4,2 | 10,0 | 0,0 | 5,0 | 8,9 | 86 | 1% | 75% | sal_growth_5y_cagr, sal_certification_share, sal_market_access_tariff, sal_mortality_pct |
| 8 | Canadá | **4,93** | 3,5 | 4,4 | 4,4 | 5,0 | 9,1 | 729 | 0% | 79% | sal_certification_share, sal_market_access_tariff, sal_mortality_pct |
| 9 | EUA | **4,57** | 2,8 | 5,0 | 1,5 | 7,5 | 8,7 | 80 | 0% | 83% | sal_growth_5y_cagr, sal_certification_share, sal_mortality_pct |
| 10 | Turquia | **3,75** | 7,4 | 1,2 | 1,5 | 5,0 | 1,5 | 1.517 | 0% | 75% | sal_growth_5y_cagr, sal_certification_share, sal_market_access_tariff, sal_mortality_pct |

### Camarão

| # | País | Score | Tamanho/cresc. (30%) | Valor (20%) | Acesso (20%) | Regulação (15%) | Risco (15%) | DHA técnico (t) | P(1º) pesos | Cobertura de dados | Lacunas |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | China | **6,34** | 8,3 | 7,5 | 4,8 | 5,9 | 3,5 | 4.925 | 32% | 91% | shr_export_price_usd_kg |
| 2 | Tailândia | **6,29** | 4,6 | 8,6 | 7,0 | 7,5 | 4,4 | 1.021 | 45% | 100% | – |
| 3 | Equador | **6,05** | 9,2 | 2,9 | 6,2 | 5,0 | 4,8 | 6.696 | 23% | 87% | shr_hatchery_pl_billion, shr_import_tariff |
| 4 | Vietnã | **5,86** | 6,7 | 7,2 | 4,8 | 5,6 | 4,0 | 3.024 | 0% | 100% | – |
| 5 | Índia | **5,25** | 7,7 | 7,1 | 2,4 | 3,1 | 3,9 | 3.969 | 0% | 100% | – |
| 6 | Indonésia | **5,06** | 5,3 | 6,4 | 3,0 | 6,9 | 3,9 | 1.134 | 0% | 93% | shr_hatchery_pl_billion, sr_fx_volatility |
| 7 | Brasil | **4,80** | 6,5 | 5,0 | 1,8 | 5,7 | 4,1 | 555 | 0% | 85% | shr_export_price_usd_kg, shr_hatchery_pl_billion |
| 8 | Arábia Saudita | **4,58** | 5,5 | 5,0 | 0,6 | 5,0 | 7,0 | 245 | 0% | 74% | shr_growth_5y_cagr, shr_export_price_usd_kg, shr_hatchery_pl_billion, shr_import_tariff |
| 9 | México | **4,46** | 5,5 | 5,9 | 1,8 | 5,0 | 3,6 | 816 | 0% | 83% | shr_growth_5y_cagr, shr_hatchery_pl_billion, shr_import_tariff |
| 10 | Filipinas | **4,00** | 4,6 | 5,0 | 1,2 | 5,0 | 4,3 | 266 | 0% | 74% | shr_growth_5y_cagr, shr_export_price_usd_kg, shr_hatchery_pl_billion, shr_import_tariff |
| 11 | Bangladesh | **3,38** | 4,8 | 4,5 | 0,6 | 5,0 | 1,2 | 544 | 0% | 83% | shr_growth_5y_cagr, shr_hatchery_pl_billion, shr_import_tariff |
| 12 | Honduras | **3,13** | 1,6 | 5,2 | 1,2 | 5,0 | 4,1 | 103 | 0% | 83% | shr_growth_5y_cagr, shr_hatchery_pl_billion, shr_import_tariff |

### Pet food

| # | País | Score | Tamanho/cresc. (30%) | Valor (20%) | Acesso (20%) | Regulação (15%) | Risco (15%) | DHA técnico (t) | P(1º) pesos | Cobertura de dados | Lacunas |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | EUA | **7,36** | 6,1 | 9,6 | 8,1 | 5,0 | 8,3 | 3.465 | 89% | 93% | pet_manufacturers |
| 2 | Alemanha | **6,46** | 3,5 | 5,2 | 8,1 | 10,0 | 8,2 | 528 | 8% | 86% | pet_manufacturers, pet_import_tariff |
| 3 | França | **6,37** | 5,5 | 5,6 | 5,0 | 10,0 | 7,2 | 609 | 3% | 75% | pet_growth_5y_cagr, pet_manufacturers, pet_import_tariff |
| 4 | Itália | **6,16** | 5,5 | 5,0 | 5,0 | 10,0 | 6,7 | 222 | 0% | 86% | pet_manufacturers, pet_import_tariff |
| 5 | Reino Unido | **6,08** | 4,4 | 5,5 | 5,0 | 10,0 | 7,8 | 318 | 0% | 86% | pet_manufacturers, pet_import_tariff |
| 6 | Austrália | **5,93** | 5,5 | 8,9 | 2,5 | 5,0 | 8,4 | 148 | 0% | 77% | pet_algal_dha_adoption, pet_manufacturers, pet_import_tariff |
| 7 | Canadá | **5,89** | 4,5 | 7,5 | 5,0 | 5,0 | 8,6 | 287 | 0% | 86% | pet_manufacturers, pet_import_tariff |
| 8 | Espanha | **5,76** | 4,6 | 4,0 | 5,0 | 10,0 | 7,2 | 353 | 0% | 86% | pet_manufacturers, pet_import_tariff |
| 9 | Brasil | **5,60** | 4,5 | 2,6 | 8,1 | 10,0 | 4,1 | 1.320 | 0% | 93% | pet_manufacturers |
| 10 | Polônia | **5,48** | 5,5 | 1,5 | 5,0 | 10,0 | 6,8 | 363 | 0% | 86% | pet_manufacturers, pet_import_tariff |
| 11 | China | **5,35** | 7,8 | 4,1 | 4,0 | 5,0 | 4,3 | 627 | 0% | 93% | pet_manufacturers |
| 12 | Japão | **4,63** | 4,0 | 5,3 | 2,5 | 5,0 | 7,5 | 187 | 0% | 77% | pet_algal_dha_adoption, pet_manufacturers, pet_import_tariff |
| 13 | Tailândia | **4,44** | 5,5 | 3,8 | 2,5 | 5,0 | 5,3 | 362 | 0% | 77% | pet_algal_dha_adoption, pet_manufacturers, pet_import_tariff |
| 14 | Argentina | **3,37** | 4,4 | 2,8 | 2,5 | 5,0 | 1,7 | 330 | 0% | 67% | pet_growth_5y_cagr, pet_algal_dha_adoption, pet_manufacturers, pet_import_tariff |
| 15 | México | **3,31** | 3,8 | 1,3 | 2,5 | 5,0 | 4,5 | 457 | 0% | 77% | pet_algal_dha_adoption, pet_manufacturers, pet_import_tariff |

## 3. Ranking geral e papel de cada país

| # | País | Score geral | DHA técnico total (t/ano) | Nichos (score) | Papel |
|---|---|---|---|---|---|
| 1 | Noruega | **7.81** | 13.091 | salmão (7.81) | consolidar |
| 2 | EUA | **7.30** | 3.545 | salmão (4.57), pet (7.36) | consolidar |
| 3 | Chile | **7.23** | 7.632 | salmão (7.23) | consolidar |
| 4 | Reino Unido | **6.82** | 1.590 | salmão (7.01), pet (6.08) | consolidar |
| 5 | Alemanha | **6.46** | 528 | pet (6.46) | consolidar |
| 6 | França | **6.37** | 609 | pet (6.37) | consolidar |
| 7 | China | **6.23** | 5.552 | camarão (6.34), pet (5.35) | expandir |
| 8 | Itália | **6.16** | 222 | pet (6.16) | consolidar |
| 9 | Equador | **6.05** | 6.696 | camarão (6.05) | consolidar |
| 10 | Vietnã | **5.86** | 3.024 | camarão (5.86) | expandir |
| 11 | Austrália | **5.81** | 640 | salmão (5.78), pet (5.93) | expandir |
| 12 | Tailândia | **5.80** | 1.383 | camarão (6.29), pet (4.44) | consolidar |
| 13 | Ilhas Faroé | **5.78** | 729 | salmão (5.78) | expandir |
| 14 | Espanha | **5.76** | 353 | pet (5.76) | consolidar |
| 15 | Islândia | **5.51** | 389 | salmão (5.51) | expandir |
| 16 | Polônia | **5.48** | 363 | pet (5.48) | consolidar |
| 17 | Brasil | **5.36** | 1.875 | camarão (4.80), pet (5.60) | consolidar |
| 18 | Nova Zelândia | **5.34** | 86 | salmão (5.34) | monitorar |
| 19 | Índia | **5.25** | 3.969 | camarão (5.25) | expandir |
| 20 | Canadá | **5.20** | 1.016 | salmão (4.93), pet (5.89) | consolidar |
| 21 | Indonésia | **5.06** | 1.134 | camarão (5.06) | expandir |
| 22 | Japão | **4.63** | 187 | pet (4.63) | monitorar |
| 23 | Arábia Saudita | **4.58** | 245 | camarão (4.58) | expandir |
| 24 | México | **4.05** | 1.273 | camarão (4.46), pet (3.31) | expandir |
| 25 | Filipinas | **4.00** | 266 | camarão (4.00) | monitorar |
| 26 | Turquia | **3.75** | 1.517 | salmão (3.75) | expandir |
| 27 | Bangladesh | **3.38** | 544 | camarão (3.38) | monitorar |
| 28 | Argentina | **3.37** | 330 | pet (3.37) | monitorar |
| 29 | Honduras | **3.13** | 103 | camarão (3.13) | monitorar |

*Papel:* consolidar = acesso ≥ 5 no melhor nicho; expandir = acesso < 5 e tamanho/crescimento ≥ 5; monitorar = demais.

## 4. Pontos de virada (líder × 2º de cada nicho)

- **Salmão:** Chile passa Noruega se nunca, em nenhum peso de critério isolado.
- **Camarão:** Tailândia passa China se Tamanho e crescimento ≥ 29% (base 30%); ou Valor e disposição a pagar ≥ 24% (base 20%); ou Acesso e posição competitiva ≥ 22% (base 20%); ou Regulação e acesso comercial ≥ 18% (base 15%); ou Risco país e biológico ≥ 20% (base 15%).
- **Pet food:** Alemanha passa EUA se Regulação e acesso comercial ≥ 28% (base 15%).

## 5. Limitações

- Muitos valores vieram de trechos de busca e alguns de conhecimento do analista (marcados Low); conferir Medium/Low na fonte primária.
- Rubricas de relacionamento e registro aplicadas por um único analista; template em `outputs/market/market_rubric_ratings_template.csv`.
- Salmão: métricas fora do score por cobertura < 40% dos países: sal_certification_share, sal_market_access_tariff (seguem no CSV para quando houver dado).
- Camarão: métricas fora do score por cobertura < 40% dos países: shr_hatchery_pl_billion (seguem no CSV para quando houver dado).
- Pet food: métricas fora do score por cobertura < 40% dos países: pet_manufacturers, pet_import_tariff (seguem no CSV para quando houver dado).
- A necessidade técnica de DHA usa os mesmos g/kg de ração do estudo de mercado para todos os países do nicho (salmão 5,3; camarão 2,7; pet food 0,33 g DHA/kg).