# Revisão factual dos rankings Corbion – localização de DHA e mercados de destino
*Revisão 2026-10-15 · gerado por `python -m src rev2026` · todos os números vêm de `outputs/rev2026/*.csv`.*

## 1. Em uma página
- **Ranking público de sites (A):** Orindiúva (expansão) lidera pelo **piso garantido** (3,72 de 10; teto 8,64), mas **nenhuma posição está decidida** com dados públicos: todo site pode ficar entre 1º e 4º, porque capex, opex, frete entregue, outorga e backup de utilidades são desconhecidos (42%–52% do peso). Resultado: **shortlist factual com faixas de posição, não ranking completo**.
- **Brasil × Tailândia:** a vantagem de piso de Orindiúva sobre Nakhon Sawan (2,39 ponto) **não é revertida por nenhum documento isolado** (0 métricas capazes); precisaria de vários (capex + opex + frete). Ela vem de fatos: único ativo de DHA operante, equipe no site, contrato de utilidades com a usina, açúcar ~US$ 300/t vs ~US$ 630/t.
- **Retorno incremental (B), só como cenário ASSUMPTION:** VPL do módulo de Orindiúva US$ 80 mi (TIR 23%) em renovação igual; Nakhon Sawan US$ 48 mi; Rayong US$ 23 mi; greenfield BR US$ 22 mi. O valor terminal é 120% do VPL de Orindiúva: sem ele, o VPL fica negativo até 2035. **Com dados públicos, VPL e TIR são 'não estimáveis'.**
- **A renovação de dez/2026 decide o sinal do VPL:** 6 de 24 combinações site×cenário têm VPL negativo (renovar com preço/volume menor ou perder conta); take-or-pay ou âncora nova tornam todos os sites positivos. Nenhum resultado de renovação estava divulgado em 15/10/2026.
- **Nenhum nicho sozinho** sustenta um módulo de 10 kt SKU sob as premissas v3 (VPL por nicho isolado de US$ -153 a -39 mi): o módulo depende do portfólio somado.
- **Mercados (A):** Salmão = Noruega no piso (faixa 1–7); Camarão = China no piso (faixa 1–12); Pet food = EUA no piso (faixa 1–15). Consolidação (adoção histórica documentada) só em salmão Noruega/Chile/Reino Unido e camarão Tailândia; **nenhuma compra 2026 é documentada publicamente**. O preço líquido (25% × 60% do peso) é desconhecido em todos.
- **Por que o melhor ranking público pode não ser o melhor investimento:** o ranking mede o que é público e comparável; o VPL depende de quatro números privados (capex do site, rendimento, preço 2027+ e volume contratado). Um site bem colocado pode ter VPL negativo (ex.: greenfield BR em R1/R4), e um mal colocado pode passar à frente no VPL: Nakhon Sawan supera Orindiúva em R3 maior (155 × 151 US$ mi).

## 2. Lado A – ranking público de sites (pesos propostos 40/25/15/15/5)
| Site | Piso | Teto | Só dados conhecidos | Peso verificado | Julgamento | Desconhecido | Posição (piso) | Faixa | Gates |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| Orindiúva (expansão) | 3,72 | 8,64 | 7,35 | 53% | 5% | 42% | 1 | 1–4 | review/unknown |
| Greenfield BR (GO) | 1,73 | 7,41 | 4,24 | 43% | 5% | 52% | 2 | 1–4 | review/unknown |
| Nakhon Sawan | 1,33 | 6,41 | 3,02 | 48% | 5% | 46% | 3 | 1–4 | review/unknown |
| Rayong | 1,27 | 6,90 | 3,34 | 44% | 5% | 50% | 4 | 1–4 | review/unknown |

Por critério (piso–teto, 0-10):

| Site | Economia da unidade | Acesso econômico aos mercados | Execução industrial Corbion | Resiliência operacional | Opção de expansão futura |
|---|---|---|---|---|---|
| Orindiúva (expansão) | 2,1–9,6 | 3,5–6,5 | 8,8–10,0 | 3,0–9,7 | 5,0–5,0 |
| Greenfield BR (GO) | 2,0–9,6 | 3,4–6,4 | 0,0–1,8 | 0,7–8,2 | 0,0–10,0 |
| Nakhon Sawan | 0,9–8,3 | 3,0–6,0 | 0,0–1,8 | 1,5–5,5 | 0,0–10,0 |
| Rayong | 0,8–8,3 | 3,1–6,1 | 0,6–4,8 | 0,6–5,5 | 0,0–10,0 |

Posição pelo piso em cada conjunto de pesos: asia: Orindiúva (expansão) > Greenfield BR (GO) > Nakhon Sawan > Rayong; atuais_mapeados: Orindiúva (expansão) > Greenfield BR (GO) > Nakhon Sawan > Rayong; consolidacao: Orindiúva (expansão) > Greenfield BR (GO) > Nakhon Sawan > Rayong; crescimento: Orindiúva (expansão) > Greenfield BR (GO) > Nakhon Sawan > Rayong; custo: Orindiúva (expansão) > Greenfield BR (GO) > Nakhon Sawan > Rayong; proposto: Orindiúva (expansão) > Greenfield BR (GO) > Nakhon Sawan > Rayong.
±25% relativo em cada critério: ordem pelo piso inalterada (site_weight_perturbation_pm25.csv). Tipping points: site_tipping_points.csv.

**Gates não compensatórios (product_regulatory_matrix.csv):** nenhum site tem `fail`; todos têm itens `review/unknown`. Orindiúva: LO 51001996 com validade impressa 02/09/2026 (renovação tempestiva prorroga – protocolo não visto; **não se afirma descumprimento**), LP/LI para o módulo, e a divergência de cepa (*Prototheca* S2014 OGM na LO/CTNBio × *Schizochytrium* não OGM em textos BioMar/IQI) que exige mapa SKU–cepa–licença. Tailândia: nenhum certificado BOI, licença de fábrica ou registro GACC de estabelecimento.

## 3. Lado B – retorno incremental por site, nicho e cenário (ASSUMPTION)
Demanda da v3: `default_premises` (premissas rotuladas, não pedidos). Módulo entra em 2029 (capacidade atual suficiente até fim-2028/início-2029, H1 2026). WACC por país da v3.

| Site | R1 menor | R2 igual | R3 maior | R4 perda | R5 take-or-pay | R6 âncora |
|---|---:|---:|---:|---:|---:|---:|
| Greenfield BR (GO) | -38 | 22 | 93 | -40 | 81 | 137 |
| Orindiúva (expansão) | 23 | 80 | 151 | 22 | 141 | 198 |
| Nakhon Sawan | -34 | 48 | 155 | -26 | 129 | 197 |
| Rayong | -57 | 23 | 130 | -44 | 97 | 161 |

| Site (R2) | TIR | VT/VPL | VT/EV do projeto | Capex US$/kg·ano DHA | Custo US$/kg DHA | ROIC 2032-35 | Preço de equilíbrio US$/kg DHA | Utilização mínima 2035 | Payback descontado |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Orindiúva (expansão) | 23% | 120% | 62% | 30,1 | 27,0 | 22% | 18,0 | 44% | após 2035 |
| Greenfield BR (GO) | 14% | 337% | 61% | 40,9 | 36,0 | 14% | 23,1 | 66% | após 2035 |
| Nakhon Sawan | 16% | 202% | 67% | 38,2 | 35,0 | 14% | 22,2 | 62% | após 2035 |
| Rayong | 13% | 345% | 66% | 37,9 | 36,5 | 12% | 23,7 | 69% | após 2035 |

Valor de esperar 1 ano pelo resultado da renovação (probabilidades iguais, ASSUMPTION): Orindiúva (expansão) -2,6; Greenfield BR (GO) 11,6; Nakhon Sawan 7,8; Rayong 15,2 US$ mi (negativo = comprometer agora vale mais).
Monte Carlo v3 (volatilidade econômica sob premissas, não probabilidade observada): Orindiúva (expansão) P10/P50/P90 = -2/63/132; Greenfield BR (GO) P10/P50/P90 = -68/2/73; Nakhon Sawan P10/P50/P90 = -74/18/109; Rayong P10/P50/P90 = -93/-7/83.
Maiores sensibilidades de Orindiúva (R2): preço DHA ±30% (amplitude US$ 170 mi); demanda ±30% (amplitude US$ 114 mi); óleo de peixe 2.500/6.800 US$/t (amplitude US$ 110 mi); capex ±30% (amplitude US$ 60 mi); rendimento 0,055/0,10 (amplitude US$ 39 mi).
Astaxantina (Corbion–KAS): **não estimável** – desenvolvimento, sem capex, rendimento, registro ou contrato; não conta como capacidade nem receita (economics_astaxanthin.csv).

## 4. Ponte do ranking à decisão e dados necessários para aprovar capex
- **ec_net_price** (mercado): Preço líquido 2027+ por destino (resultado da renovação dez/2026) – detentor: Corbion/clientes; amplitude de VPL ~US$ 262 mi
- **dm_growth** (mercado): Projeção setorial – detentor: associações; amplitude de VPL ~US$ 138 mi
- **ec_opex_usd_per_kg_dha** (site): Rendimento DHA/açúcar industrial e balanço de utilidades – detentor: Corbion; amplitude de VPL ~US$ 104 mi
- **ec_sugar_usd_t** (site): Contrato de açúcar entregue (especificação, entressafra) – detentor: usina; amplitude de VPL ~US$ 102 mi
- **ec_capex_usd_per_kg_dha_yr** (site): Orçamento de capex por site (classe AACE ≥3) e capacidade efetiva – detentor: Corbion; amplitude de VPL ~US$ 98 mi
- **ac_freight_usd_t** (site): Cotações de frete entregue por destino/Incoterm – detentor: Corbion/agente; amplitude de VPL ~US$ 7 mi
- **op_space_documented** (site): Plot plan e reserva de utilidades – detentor: Corbion
- **resultado da renovação dez/2026** (economia): Termos renovados (preço, volume, take-or-pay, prazo) – detentor: Corbion
- Template de dados de gestão (caso `management-data`, vazio até os dados chegarem): `management_data_template.csv`.

## 5. Mercados por nicho (pesos 25/25/25/15/10)

### Salmão
| # piso | País | Piso | Teto | Faixa | Verificado | Papel | Estágio de evidência | Gate SKU | TAM técnico t DHA |
|---:|---|---:|---:|---|---:|---|---:|---|---:|
| 1 | Noruega | 4,99 | 6,86 | 1–7 | 81% | consolidação | 6 | review | 13.091 |
| 2 | Chile | 4,94 | 7,69 | 1–8 | 69% | consolidação | 6 | unknown | 7.632 |
| 3 | Reino Unido | 4,35 | 6,97 | 1–10 | 74% | consolidação | 6 | review | 1.272 |
| 4 | China | 3,30 | 6,18 | 1–11 | 72% | expansão | 3 | review | 344 |
| 5 | Ilhas Faroé | 2,74 | 5,37 | 1–11 | 66% | expansão | 0 | unknown | 729 |
| 6 | Islândia | 2,61 | 5,73 | 1–11 | 61% | expansão | 0 | unknown | 389 |
| 7 | Turquia | 2,60 | 5,72 | 1–11 | 69% | expansão | 0 | unknown | 1.517 |
| 8 | Austrália | 2,33 | 4,95 | 2–11 | 74% | expansão | 0 | unknown | 492 |
| 9 | EUA | 2,30 | 4,30 | 4–11 | 72% | expansão | 0 | unknown | 80 |
| 10 | Canadá | 2,20 | 4,58 | 3–11 | 76% | expansão | 0 | unknown | 729 |
Consolidar: Noruega, Chile, Reino Unido; expandir (melhores pisos): China, Ilhas Faroé, Islândia, Turquia.

### Camarão
| # piso | País | Piso | Teto | Faixa | Verificado | Papel | Estágio de evidência | Gate SKU | TAM técnico t DHA |
|---:|---|---:|---:|---|---:|---|---:|---|---:|
| 1 | China | 4,49 | 6,74 | 1–12 | 65% | expansão | 3 | review | 4.925 |
| 2 | Equador | 4,43 | 7,05 | 1–12 | 61% | expansão | 0 | unknown | 6.696 |
| 3 | Vietnã | 4,09 | 6,34 | 1–12 | 65% | expansão | 3 | unknown | 3.024 |
| 4 | Tailândia | 3,66 | 5,91 | 1–12 | 56% | consolidação | 6 | review | 1.021 |
| 5 | Brasil | 3,60 | 5,85 | 1–12 | 65% | expansão | 0 | unknown | 555 |
| 6 | Índia | 3,12 | 5,37 | 1–12 | 65% | expansão | 0 | unknown | 3.969 |
| 7 | Arábia Saudita | 3,00 | 5,62 | 1–12 | 52% | expansão | 0 | unknown | 245 |
| 8 | Indonésia | 2,88 | 5,63 | 1–12 | 51% | expansão | 0 | unknown | 1.134 |
| 9 | México | 2,71 | 5,33 | 1–12 | 61% | expansão | 0 | unknown | 816 |
| 10 | Filipinas | 2,33 | 4,95 | 1–12 | 52% | expansão | 0 | unknown | 266 |
Consolidar: Tailândia; expandir (melhores pisos): China, Equador, Vietnã, Brasil.

### Pet food
| # piso | País | Piso | Teto | Faixa | Verificado | Papel | Estágio de evidência | Gate SKU | TAM técnico t DHA |
|---:|---|---:|---:|---|---:|---|---:|---|---:|
| 1 | EUA | 3,85 | 6,10 | 1–15 | 72% | expansão | 3 | review | 3.465 |
| 2 | Polônia | 3,34 | 6,71 | 1–15 | 61% | expansão | 3 | review | 363 |
| 3 | Itália | 3,29 | 6,67 | 1–15 | 61% | expansão | 3 | review | 222 |
| 4 | Espanha | 3,28 | 6,66 | 1–15 | 61% | expansão | 3 | review | 353 |
| 5 | Canadá | 3,11 | 6,48 | 1–15 | 61% | expansão | 3 | review | 287 |
| 6 | Brasil | 2,89 | 5,89 | 1–15 | 65% | expansão | 0 | unknown | 1.320 |
| 7 | China | 2,86 | 5,11 | 1–15 | 72% | expansão | 0 | review | 627 |
| 8 | Alemanha | 2,84 | 6,22 | 1–15 | 61% | expansão | 3 | review | 528 |
| 9 | França | 2,71 | 6,96 | 1–15 | 52% | expansão | 3 | review | 609 |
| 10 | Tailândia | 2,60 | 5,98 | 1–15 | 61% | expansão | 0 | unknown | 362 |
Consolidar: nenhum; expandir (melhores pisos): EUA, Polônia, Itália, Espanha.

**Pares país×nicho (objetivo declarado: escolher os próximos pares a trabalhar; não é média de nichos):** Salmão·Noruega 4,99; Salmão·Chile 4,94; Camarão·China 4,49; Camarão·Equador 4,43; Salmão·Reino Unido 4,35; Camarão·Vietnã 4,09; Pet food·EUA 3,85; Camarão·Tailândia 3,66; Camarão·Brasil 3,60; Pet food·Polônia 3,34.

**Contas com maior evidência** (sem score composto; potencial técnico ≠ compra): BioMar Norway Myre (historical_adoption, 1.908 t DHA técnicas); BioMar Norway Karmøy (historical_adoption, 1.908 t DHA técnicas); BioMar Chile Pargua (2 plantas) (historical_adoption, 954 t DHA técnicas); BioMar Chile Ercilla (historical_adoption, 636 t DHA técnicas); BioMar Group (grupo; 16 fábricas) (historical_adoption, n/d t DHA técnicas); BioMar UK Grangemouth (Escócia) (historical_adoption, n/d t DHA técnicas).

## 6. O que poderia inverter as comparações-chave
- **Salmão: Noruega × Chile** – documento isolado que pode inverter: Concorrente algal documentado no país×nicho (1 = sim), Preço líquido realizável (US$/kg DHA), Volatilidade cambial do destino (%/ano); pesos de virada (piso): acesso a 20%, economia a 28%, risco a 6%.
- **Camarão: China × Tailândia** – documento isolado que pode inverter: Preço líquido realizável (US$/kg DHA); pesos de virada (piso): demanda a 2%, acesso a 92%, risco a 53%.
- **Pet food: EUA × França** – documento isolado que pode inverter: Preço líquido realizável (US$/kg DHA); pesos de virada (piso): nenhum entre 0 e 95%.
- **Brasil × Tailândia (sites):** nenhum documento isolado inverte Orindiúva × Nakhon Sawan/Rayong pelo piso; no VPL (ASSUMPTION): Nakhon Sawan supera Orindiúva em R3 maior (155 × 151 US$ mi). A base da v3 já supõe BOI de 8 anos; sem BOI, o VPL de Nakhon Sawan vai de US$ 48 mi para US$ 47 mi (o top-up de 15% do Pilar Dois neutraliza quase todo o benefício na modelagem v3) – e nenhum certificado BOI existe.

## 7. Robustez, correlação e circularidade
- Correlação entre critérios (pisos) nos 4 sites: ver site_criterion_correlation.csv (n = 4, apenas descritiva). Mercados: market_criterion_correlation.csv. Resultado com/sem cada critério: *_leave_one_criterion_out.csv.
- Economia × Execução: açúcar/vapor só em Economia; Execução só ativo/equipe/cronograma. Correlação dos pisos Economia×Execução nos sites = 0,59 (n = 4; não interpretável estatisticamente).
- Circularidade: o acesso do site usa destinos com pesos fixos 1/3 por nicho (não o SAM do ranking de mercado); o prazo desde Orindiúva aparece nos dois rankings e entra uma única vez no VPL (circularity_check.csv).
- Incerteza epistemológica (falta de informação) = largura piso–teto; volatilidade econômica = Monte Carlo do DCF. São mostradas separadamente.

## 8. Auditoria e verificações
- 21 afirmações auditadas em claims_audit.csv (ex.: tetos da LO ≠ capacidade; cepa S2014 × Schizochytrium; 5 × 6 fermentadores; Aqueduct 0 × Corbion AR 'alto risco' em Orindiúva; nota 10 por 'único produtor' removida; GMI com versões conflitantes; '2/3 em contratos' não confirmado).
- Fontes: L2_search_digest: 29, L3_prior_session: 11, L1_user_brief: 6, L0_unavailable: 4. **Nenhuma fonte primária pôde ser aberta integralmente neste ambiente** (hosts bloqueados); o que veio do brief está como L1 e o que veio de trechos de busca como L2 – nenhum número foi tratado como lido do documento original.
- Meta de julgamento ≤ 10%: sites 5%; Salmão até 8%; Camarão até 21%; Pet food até 5%. **Camarão não atinge a meta** (contagem de fabricantes, escore de doença e projeção de crescimento vêm de 'conhecimento do analista'); por isso o ranking de camarão não deve ser chamado de robusto.
- Verificações automáticas (automated_checks.csv): PASS: 25, FAIL: 1.
  - FAIL: julgamento explícito ≤ 10% do peso (meta) – máximo observado 21.2%

## 9. O que mudou em relação a 14/10/2026
- Ranking de país → ranking de **site** (4 projetos) + gates; regulação e incentivos saíram do score.
- Peso de notas não documentadas: de ~41% para ≤ 5% (julgamento explícito) + intervalo explícito para o desconhecido (antes o dado ausente era renormalizado).
- Brasil continua à frente da Tailândia pelo piso, mas **não é mais 'robusto'**: a ordem completa não é sustentável com dados públicos. No mercado, Noruega, China e EUA seguem 1º no piso de seus nichos, mas com faixas largas; França cai por cobertura baixa (não por evidência contrária).

## 10. Como reproduzir
```
cd microalgae_site_selection/country_ranking
python -m src rev2026            # ~1-2 min
python -m pytest tests/test_rev2026.py -q
```
Entradas: `data/rev2026/*.csv`, `config_rev2026.yaml`, motor v3 (`../v3`). Saídas: `outputs/rev2026/`. Versão anterior congelada: `outputs/frozen_2026-10-14/`.