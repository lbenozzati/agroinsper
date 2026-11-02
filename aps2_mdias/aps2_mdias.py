# -*- coding: utf-8 -*-
"""
APS 2 - Financas I - Avaliacao de Projeto de Investimento
Empresa: M. Dias Branco S.A. (MDIA3)
Projeto: linha de barras de proteina

O script reproduz o fluxo de caixa da planilha (aba Projeto) e faz:
  (1) caso base: VPL, TIR e payback descontado
  (2) ponto de equilibrio em quantidade e em preco
  (3) analise de sensibilidade (graficos spider e tornado)
  (4) simulacao de Monte Carlo com 100.000 cenarios (histograma do VPL)

Valores em R$ milhoes; quantidades em milhoes de unidades.
Programa feito para rodar no Spyder (Python 3).
"""

import os
import numpy as np
import matplotlib.pyplot as plt

# Pasta onde os graficos serao salvos (mesma pasta do script)
try:
    PASTA = os.path.dirname(os.path.abspath(__file__))
except NameError:               # rodando celula a celula no console
    PASTA = os.getcwd()

# =============================================================================
# 1. PREMISSAS (mesmos valores da aba Premissas do Excel)
# =============================================================================
TMA = 0.27                  # taxa minima de atratividade (% a.a.)
N = 5                       # horizonte do projeto (anos)
IR = 0.34                   # aliquota de IR + CSLL (25% + 9%)
DIAS = 360                  # base de dias para os prazos medios

# Receita
PRECO_1 = 4.50              # preco liquido por unidade no ano 1 (R$/unid.)
CAPEX_BASE = 0.05 * 5987.6  # CAPEX = 5% do imobilizado + intangivel (R$ 299,38 mi)
GIRO_ATIVO = 0.8310654256   # giro do ativo da M. Dias em 2025 (aba Historico)
QTD_1 = GIRO_ATIVO * CAPEX_BASE / PRECO_1   # quantidade do ano 1 (~55,29 mi unid.)
CRESC_VOL = 0.0111894966    # crescimento real do volume a partir do ano 2
REAJ_REAL = 0.0             # reajuste real de preco (acima do IPCA)

# Inflacao (IPCA) usada para corrigir precos e custos a partir do ano 2
# (ano 2 = IPCA 2027; anos 3 a 5 = IPCA 2028 a 2030)
IPCA = np.array([0.045422, 0.04, 0.04, 0.04])

# Custos e despesas (% da receita, base historico M. Dias 2025)
CUSTO_UNIT_1 = 1.80         # custo variavel unitario no ano 1 (R$/unid.)
SUBVENCAO = 0.044397179     # subvencoes fiscais (% da receita)
DESP_VENDAS = 0.186326359   # despesas com vendas (% da receita)
GA = 0.037824787            # despesas gerais e administrativas (% da receita)
CUSTO_FIXO = 0.0            # custos fixos de producao (ja no custo unitario)

# Investimento e depreciacao
TX_DEPREC = 0.0622          # taxa de depreciacao (maquinas, % a.a.)
VENDA_ATIVO = 1.00          # valor de venda no ano 5 (% do valor contabil)

# Capital de giro (prazos medios de 2025)
PMR = 63.5870315            # prazo medio de recebimento (dias)
PME = 79.9501591            # prazo medio de estocagem (dias)
PMP = 67.6956522            # prazo medio de pagamento (dias)

# Canibalizacao, sinergias e custo de oportunidade: nao considerados (zero)


# =============================================================================
# 2. FUNCAO QUE MONTA O FLUXO DE CAIXA E CALCULA O VPL
#    Aceita numeros ou vetores (numpy) -> serve para o Monte Carlo
# =============================================================================
def fluxo_projeto(f_vol=1.0, f_preco=1.0, f_custo=1.0, f_desp=1.0,
                  f_capex=1.0, detalhado=False):
    """
    f_vol, f_preco, f_custo, f_desp, f_capex: multiplicadores sobre o caso
    base (1,0 = caso base; 1,10 = +10%).
    Retorna o VPL (e, se detalhado=True, as linhas da DRE e do fluxo).
    """
    t = np.arange(1, N + 1)

    # Indice de inflacao acumulado (ano 1 = 1)
    indice = np.concatenate(([1.0], np.cumprod(1 + IPCA)))

    # Volume, preco e custo unitario em cada ano
    volume = QTD_1 * (1 + CRESC_VOL) ** (t - 1)
    preco = PRECO_1 * indice * (1 + REAJ_REAL) ** (t - 1)
    custo_unit = CUSTO_UNIT_1 * indice

    # Aplica os choques (np.outer permite vetores no Monte Carlo)
    volume = np.outer(np.atleast_1d(f_vol), volume)
    preco = np.outer(np.atleast_1d(f_preco), preco)
    custo_unit = np.outer(np.atleast_1d(f_custo), custo_unit)
    f_desp = np.atleast_1d(f_desp)[:, None]
    capex = CAPEX_BASE * np.atleast_1d(f_capex)

    # ---------------- DRE do projeto ----------------
    receita = volume * preco                          # Receita = Q x P
    cpv = volume * custo_unit                         # CPV = Q x custo unit.
    custo_fixo = CUSTO_FIXO * indice
    subv = SUBVENCAO * receita
    lucro_bruto = receita - cpv - custo_fixo + subv
    despesas = (DESP_VENDAS + GA) * receita * f_desp
    ebitda = lucro_bruto - despesas
    deprec = (TX_DEPREC * capex)[:, None] * np.ones(N)
    ebit = ebitda - deprec
    imposto = IR * ebit
    nopat = ebit - imposto
    fco = nopat + deprec                              # FCO = NOPAT + depreciacao

    # ---------------- Capital de giro ----------------
    cr = receita * PMR / DIAS                         # contas a receber
    est = (cpv + custo_fixo) * PME / DIAS             # estoques
    forn = (cpv + custo_fixo) * PMP / DIAS            # fornecedores
    cgl = cr + est - forn                             # capital de giro necessario

    # Investimento: no ano t investe a necessidade do ano t+1;
    # no ano 5 recupera todo o capital de giro
    var_cgl = np.zeros((cgl.shape[0], N + 1))
    var_cgl[:, 0] = -cgl[:, 0]
    var_cgl[:, 1:N] = -(cgl[:, 1:] - cgl[:, :-1])
    var_cgl[:, N] = cgl[:, -1]

    # ---------------- Valor residual ----------------
    valor_contabil = capex * (1 - TX_DEPREC * N)
    valor_venda = valor_contabil * VENDA_ATIVO
    ir_ganho = IR * (valor_venda - valor_contabil)
    residual = valor_venda - ir_ganho

    # ---------------- Fluxo de caixa livre ----------------
    fcl = np.zeros((cgl.shape[0], N + 1))
    fcl[:, 0] = -capex
    fcl[:, 1:] = fco
    fcl += var_cgl
    fcl[:, N] += residual

    # VPL = soma de FCL_t / (1 + TMA)^t
    desconto = 1 / (1 + TMA) ** np.arange(N + 1)
    vpl = (fcl * desconto).sum(axis=1)

    if detalhado:
        return float(vpl[0]), dict(receita=receita[0], cpv=cpv[0],
                                   ebitda=ebitda[0], ebit=ebit[0],
                                   nopat=nopat[0], fco=fco[0],
                                   cgl=var_cgl[0], fcl=fcl[0],
                                   residual=float(residual[0]))
    return vpl if vpl.size > 1 else float(vpl[0])


def tir(fluxos):
    """TIR pelo metodo da bissecao (taxa que zera o VPL)."""
    baixo, alto = -0.99, 5.0
    for _ in range(200):
        meio = (baixo + alto) / 2
        v = sum(f / (1 + meio) ** i for i, f in enumerate(fluxos))
        if v > 0:
            baixo = meio
        else:
            alto = meio
    return meio


def payback_descontado(fluxos, taxa):
    """Ano em que o fluxo descontado acumulado fica positivo."""
    acum = 0.0
    for i, f in enumerate(fluxos):
        fd = f / (1 + taxa) ** i
        if acum < 0 and acum + fd >= 0:
            return i - 1 + (-acum) / fd
        acum += fd
    return None


def fmt(x, casas=2):
    """Formato brasileiro: 1.000,00"""
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def salvar(nome):
    """Salva o grafico na pasta do script e mostra na tela."""
    plt.savefig(os.path.join(PASTA, nome), dpi=200)
    plt.show()


# =============================================================================
# 3. CASO BASE
# =============================================================================
vpl_base, d = fluxo_projeto(detalhado=True)
tir_base = tir(d["fcl"])
pb = payback_descontado(d["fcl"], TMA)

print("=" * 60)
print("CASO BASE")
print("=" * 60)
print("Ano        " + "".join(f"{a:>11}" for a in range(N + 1)))
print("FCL (R$mi) " + "".join(f"{fmt(v):>11}" for v in d["fcl"]))
print(f"\nVPL  = R$ {fmt(vpl_base)} mi")
print(f"TIR  = {fmt(tir_base * 100)}%  (TMA = {fmt(TMA * 100)}%)")
print("Payback descontado = " +
      (f"{fmt(pb)} anos" if pb is not None else "nao se paga em 5 anos"))
print("Decisao: " + ("APROVAR" if vpl_base > 0 else "REJEITAR"))


# =============================================================================
# 4. PONTO DE EQUILIBRIO (base: ano 1)
# =============================================================================
desp_var = DESP_VENDAS + GA - SUBVENCAO                 # % do preco
mc_unit = PRECO_1 * (1 - desp_var) - CUSTO_UNIT_1       # margem de contribuicao
deprec_1 = TX_DEPREC * CAPEX_BASE
fator_anuidade = (1 - (1 + TMA) ** -N) / TMA
# Investimento liquido em valor presente: CAPEX + capital de giro
# - valor presente do capital de giro recuperado e do valor residual
# (valor residual liquido de IR, o mesmo usado no fluxo de caixa)
desc = 1 / (1 + TMA) ** np.arange(N + 1)
vp_invest = CAPEX_BASE - np.sum(d["cgl"] * desc) - d["residual"] * desc[N]
cae = vp_invest / fator_anuidade                       # custo anual equivalente

q_contabil = (CUSTO_FIXO + deprec_1) / mc_unit
q_economico = (CUSTO_FIXO * (1 - IR) + cae - deprec_1 * IR) / (mc_unit * (1 - IR))
p_economico = ((CUSTO_FIXO * (1 - IR) + cae - deprec_1 * IR) / (1 - IR)
               / QTD_1 + CUSTO_UNIT_1) / (1 - desp_var)

print("\n" + "=" * 60)
print("PONTO DE EQUILIBRIO (ano 1)")
print("=" * 60)
print(f"Margem de contribuicao unitaria: R$ {fmt(mc_unit)}")
print(f"Custo anual equivalente (CAE):   R$ {fmt(cae)} mi")
print(f"Q contabil:  {fmt(q_contabil)} mi unid.")
print(f"Q economico: {fmt(q_economico)} mi unid. (projetado: {fmt(QTD_1)})")
print(f"Preco economico: R$ {fmt(p_economico)} (projetado: R$ {fmt(PRECO_1)})")


# =============================================================================
# 5. ANALISE DE SENSIBILIDADE (uma variavel por vez, de -30% a +30%)
# =============================================================================
variacoes = np.linspace(-0.30, 0.30, 13)
variaveis = {
    "Volume": "f_vol",
    "Preco": "f_preco",
    "Custo variavel unitario": "f_custo",
    "Despesas (vendas + G&A)": "f_desp",
    "CAPEX": "f_capex",
}

resultados = {}
for nome, arg in variaveis.items():
    resultados[nome] = [fluxo_projeto(**{arg: 1 + v}) for v in variacoes]

print("\n" + "=" * 60)
print("SENSIBILIDADE - VPL (R$ mi)")
print("=" * 60)
print(f"{'Variacao':<26}" + "".join(f"{v:>9.0%}" for v in variacoes[::2]))
for nome, vpls in resultados.items():
    print(f"{nome:<26}" + "".join(f"{fmt(x):>9}" for x in vpls[::2]))

# Grafico 1: spider (VPL x variacao de cada premissa)
plt.figure(figsize=(9, 5.5))
for nome, vpls in resultados.items():
    plt.plot(variacoes * 100, vpls, marker="o", label=nome)
plt.axhline(0, color="black", linewidth=0.8)
plt.axvline(0, color="grey", linestyle="--", linewidth=0.8)
plt.xlabel("Variacao sobre o caso base (%)")
plt.ylabel("VPL (R$ mi)")
plt.title("Analise de sensibilidade do VPL")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
salvar("sensibilidade_spider.png")

# Grafico 2: tornado (VPL com -10% e +10% em cada premissa)
baixo = [fluxo_projeto(**{a: 0.9}) for a in variaveis.values()]
alto = [fluxo_projeto(**{a: 1.1}) for a in variaveis.values()]
ordem = np.argsort([abs(a - b) for a, b in zip(alto, baixo)])
nomes = np.array(list(variaveis.keys()))[ordem]
plt.figure(figsize=(9, 5))
for i, k in enumerate(ordem):
    plt.barh(i, baixo[k] - vpl_base, left=vpl_base, color="#C0504D")
    plt.barh(i, alto[k] - vpl_base, left=vpl_base, color="#4F81BD")
plt.axvline(vpl_base, color="black", linewidth=0.8)
plt.yticks(range(len(nomes)), nomes)
plt.xlabel("VPL (R$ mi)")
plt.title("Tornado: VPL com -10% (vermelho) e +10% (azul)")
plt.tight_layout()
salvar("sensibilidade_tornado.png")


# =============================================================================
# 6. SIMULACAO DE MONTE CARLO (100.000 cenarios)
# =============================================================================
# Variaveis aleatorias (multiplicadores sobre o caso base):
#  - Preco: triangular (min. R$ 4,00; moda R$ 4,50; max. R$ 5,00)
#        -> concorrencia de marcas como Bold e Integralmedica limita o preco
#  - Volume: normal (media 100%; desvio-padrao 15%)
#        -> aceitacao de produto novo e incerta, simetrica em torno do base
#  - Custo unitario: triangular (min. R$ 1,50; moda R$ 1,70; max. R$ 2,20)
#        -> proteina (whey) e cotada em dolar: risco maior de alta
#        -> media da triangular = (1,50 + 1,70 + 2,20) / 3 = R$ 1,80 (caso base)
N_SIM = 100_000
rng = np.random.default_rng(seed=42)        # semente fixa = resultado reproduzivel

sim_preco = rng.triangular(4.00, 4.50, 5.00, N_SIM) / PRECO_1
sim_vol = np.clip(rng.normal(1.0, 0.15, N_SIM), 0, None)
sim_custo = rng.triangular(1.50, 1.70, 2.20, N_SIM) / CUSTO_UNIT_1

vpl_sim = fluxo_projeto(f_vol=sim_vol, f_preco=sim_preco, f_custo=sim_custo)

print("\n" + "=" * 60)
print(f"MONTE CARLO - {fmt(N_SIM, 0)} simulacoes")
print("=" * 60)
print(f"VPL medio:        R$ {fmt(vpl_sim.mean())} mi")
print(f"VPL mediano:      R$ {fmt(np.median(vpl_sim))} mi")
print(f"Desvio-padrao:    R$ {fmt(vpl_sim.std())} mi")
print(f"P(VPL < 0):       {fmt((vpl_sim < 0).mean() * 100)}%")
print(f"Percentil 5%:     R$ {fmt(np.percentile(vpl_sim, 5))} mi")
print(f"Percentil 95%:    R$ {fmt(np.percentile(vpl_sim, 95))} mi")
print(f"Minimo / Maximo:  R$ {fmt(vpl_sim.min())} / R$ {fmt(vpl_sim.max())} mi")

# Grafico 3: histograma do VPL
plt.figure(figsize=(9, 5.5))
plt.hist(vpl_sim, bins=100, color="#4F81BD", edgecolor="white")
plt.axvline(0, color="red", linewidth=1.5, label="VPL = 0")
plt.axvline(vpl_sim.mean(), color="black", linestyle="--",
            label=f"VPL medio = R$ {fmt(vpl_sim.mean())} mi")
plt.xlabel("VPL (R$ mi)")
plt.ylabel("Frequencia")
plt.title(f"Monte Carlo - distribuicao do VPL ({fmt(N_SIM, 0)} simulacoes)")
plt.legend()
plt.tight_layout()
salvar("monte_carlo_histograma.png")
