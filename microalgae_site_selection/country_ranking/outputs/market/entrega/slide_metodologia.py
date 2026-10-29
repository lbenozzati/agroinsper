import sys; sys.path.insert(0, "/home/user/agroinsper/microalgae_site_selection/country_ranking")
from src import charts as C
from matplotlib.patches import FancyBboxPatch
C.setup()
fig = C.slide("Como o ranking de mercado foi construído",
              "Modelo de 14/10 · cenário base · nichos salmão, camarão e pet food",
              "Fontes: config_market.yaml, market_ranking_*.csv. Premissas Corbion: venda via BioMar, preço > prazo, tarifa China 4% (provisória).")
OUT = "/tmp/claude-0/-home-user-agroinsper/f297be62-9787-5f0d-af81-363252c2d474/scratchpad/entrega/slide_metodologia.png"

def card(x, y, w, h, num, title, color):
    fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.012",
                       transform=fig.transFigure, fc="#FFFFFF0D", ec="#FFFFFF26", lw=1))
    fig.patches.append(FancyBboxPatch((x, y + h - 0.006), w, 0.006, boxstyle="square,pad=0",
                       transform=fig.transFigure, fc=color, ec="none"))
    fig.text(x + 0.018, y + h - 0.055, num, fontsize=20, fontweight="bold", color=color)
    fig.text(x + 0.058, y + h - 0.052, title, fontsize=15.5, fontweight="bold")

def lines(x, y, items, dy=0.047, size=11.5):
    for t in items:
        bold, rest = (t.split("|", 1) + [""])[:2] if "|" in t else ("", t)
        if bold:
            tx = fig.text(x, y, bold, fontsize=size, fontweight="bold", color=C.INK)
            fig.canvas.draw() if False else None
            fig.text(x + 0.0062 * len(bold) * size / 11.5, y, rest, fontsize=size, color=C.INK2)
        else:
            fig.text(x, y, rest, fontsize=size, color=C.INK2)
        y -= dy

L, R, W, H = 0.04, 0.515, 0.445, 0.375
TOP, BOT = 0.455, 0.06

# 1 Notas 0-10
card(L, TOP, W, H, "1", "Como cada dado vira nota de 0 a 10", C.BLUE)
lines(L + 0.022, TOP + H - 0.11, [
    "Métrica numérica: régua pior → melhor (ex.: tarifa 15% = 0, 0% = 10)",
    "Escala log para volumes (produção, DHA técnico): evita que gigantes dominem",
    "Rubricas por componentes (canal, registro, competição) somam até 10,",
    "     cada ponto com evidência e fonte; usa-se o ponto médio do intervalo",
    "Dado ausente sai da conta e o peso é redistribuído (nunca vira zero)",
    "Cobertura < 50% do peso → país marcado como \"dados insuficientes\"",
], size=11.2)

# 2 Critérios e pesos
card(R, TOP, W, H, "2", "Critérios e pesos dentro de cada nicho", C.MAGENTA)
crit = [("Acesso e posição competitiva", 0.30, "competição 35% · canal, adoção, fábricas 20% cada · logística 5%"),
        ("Tamanho e crescimento", 0.25, "volume/DHA técnico 65%, crescimento 35%"),
        ("Valor e disposição a pagar", 0.15, "preço do produto final, certificação/intensificação"),
        ("Regulação e acesso comercial", 0.15, "tarifa 50%, registro do ingrediente 50%"),
        ("Risco país e biológico", 0.15, "rating, WGI, câmbio 65% · doenças/mortalidade 35%")]
y = TOP + H - 0.10
x0, bw = R + 0.022, 0.13
for i, (n, w, d) in enumerate(crit):
    col = C.CRIT_COLORS[i]
    fig.patches.append(FancyBboxPatch((x0, y - 0.004), bw * w / 0.30, 0.022, boxstyle="square,pad=0",
                       transform=fig.transFigure, fc=col, ec="none"))
    fig.text(x0 + bw + 0.008, y + 0.003, f"{w:.0%}", fontsize=12.5, fontweight="bold")
    fig.text(x0 + bw + 0.045, y + 0.004, n, fontsize=11.5, fontweight="bold")
    fig.text(x0 + bw + 0.045, y - 0.021, d, fontsize=9.2, color=C.MUTED)
    y -= 0.053

# 3 Ranking geral
card(L, BOT, W, H, "3", "Ranking geral (todos os nichos)", C.VIOLET)
lines(L + 0.022, BOT + H - 0.11, [
    "Peso no portfólio: salmão 45% · camarão 40% · pet food 15%",
    "Qualidade = média das notas de nicho × peso do nicho × DHA técnico",
    "Relevância = quanto do DHA do país está em salmão/camarão (0 a 1)",
    "Nota geral = Qualidade × (0,5 + 0,5 × Relevância)",
], size=11.4)
fig.text(L + 0.022, BOT + 0.085, "Top 5:", fontsize=12, fontweight="bold")
fig.text(L + 0.022, BOT + 0.045, "Noruega 7,53 · Chile 7,12 · Reino Unido 6,25 · Equador 5,80 · China 5,78",
         fontsize=11.6, color=C.INK)
fig.text(L + 0.022, BOT + 0.015, "EUA cai para 12º (4,76): forte em pet food, mas relevância baixa (0,35)",
         fontsize=9.8, color=C.MUTED)

# 4 Robustez
card(R, BOT, W, H, "4", "Testes de robustez", "#5fc4c0")
lines(R + 0.022, BOT + H - 0.11, [
    "5 cenários de pesos (base, 14/10, consolidação, crescimento, mercado)",
    "4.000 sorteios aleatórios de pesos → % de vezes em 1º lugar",
    "600 simulações Monte Carlo variando os dados pela confiança",
    "Notas de controle: só métricas numéricas · ausente = 0 · ausente = 10",
], size=11.2)
stats = [("96%", "Noruega 1º em salmão\n(sorteio de pesos)"), ("74%", "China 1º em camarão\n(sorteio de pesos)"),
         ("100%", "China no top 3\nde camarão")]
for i, (v, t) in enumerate(stats):
    xs = R + 0.022 + i * 0.142
    fig.text(xs, BOT + 0.07, v, fontsize=22, fontweight="bold", color="#5fc4c0")
    fig.text(xs, BOT + 0.018, t, fontsize=9.6, color=C.INK2, linespacing=1.3)

C.save(fig, OUT); print(OUT)
