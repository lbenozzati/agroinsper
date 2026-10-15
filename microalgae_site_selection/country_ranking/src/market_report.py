"""Charts and memo for the market-expansion country rankings (Prompt 2)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import charts as C
from .charts import PT, fmt
from .market import OUT

CRIT_SHORT = {"size_growth": "Tamanho e\ncrescimento", "value": "Valor e disposição\na pagar",
              "access": "Acesso e posição\ncompetitiva", "regulatory": "Regulação e\nacesso comercial",
              "risk": "Risco país\ne biológico"}
NICHE_PT = {"salmon": "salmão", "shrimp": "camarão", "pet": "pet food"}
POINTS = {"Faroe Islands": (-6.9, 62.0), "European Union": (10.0, 50.0), "United States": (-98.0, 39.0),
          "Norway": (9.0, 61.0), "Canada": (-105.0, 56.0), "Australia": (146.5, -42.0), "Chile": (-72.5, -41.0)}


def pct(x):
    return f"{x * 100:.0f}%"


def charts(out: dict) -> None:
    C.setup()
    cfg = out["cfg"]
    w = cfg["scenarios"][cfg["base_scenario"]]
    N = cfg.get("top_n", 10)
    for n, r in out["results"].items():
        t = r["table"].head(N)
        note = (f"Top {N} de {len(r['table'])} países avaliados. Score = triagem multicritério (0–10). Pesos base 30/20/20/15/15. Fonte: market_ranking_{n}.csv / "
                "market_inputs_long.csv. Valores ausentes saem da conta (pesos renormalizados), nunca viram zero.")
        C.heatmap(t, CRIT_SHORT, w, OUT / f"market_heatmap_{n}.png",
                  f"Melhores países para expandir o AlgaPrime – {NICHE_PT[n]}",
                  f"Top {N} · score por critério (0–10) e score final ponderado · {len(r['model'].metrics)} métricas, inclui logística desde Orindiúva",
                  note, extra_cols={"DHA (t)": t.dha_need_t.map(lambda x: "" if pd.isna(x) else f"{x:,.0f}".replace(",", "."))})
        C.contributions(r["contributions"], {k: v.replace("\n", " ") for k, v in CRIT_SHORT.items()}, list(t.index),
                        OUT / f"market_contributions_{n}.png", f"De onde vem o score – {NICHE_PT[n]}",
                        "Contribuição de cada critério (score × peso)", note)
    ov = out["overall"].head(N)
    pairs = out["pairs"]
    # overall bar chart coloured by niche contribution
    fig = C.slide(f"Ranking geral: top {N} países para expandir o AlgaPrime DHA",
                  "Score do país = média dos scores por nicho, ponderada pela necessidade técnica de DHA do país em cada nicho",
                  "Fonte: market_ranking_overall.csv. Nichos: salmão, camarão e pet food (ranking próprio em cada um).")
    ax = fig.add_axes([0.20, 0.10, 0.62, 0.72])
    order = list(ov.index)
    y = np.arange(len(order))[::-1]
    cols = {"salmon": C.BLUE, "shrimp": C.MAGENTA, "pet": C.VIOLET}
    for yi, c in zip(y, order):
        g = pairs[pairs.country == c]
        tot = g.dha_need_t.sum()
        left = 0.0
        for _, r in g.iterrows():
            share = r.dha_need_t / tot if tot > 0 else 1 / len(g)
            ax.barh(yi, r.score * share, left=left, color=cols[r.niche], height=0.62, edgecolor=C.SURFACE)
            left += r.score * share
        ax.text(left + 0.06, yi, fmt(ov.overall_score[c], 2), va="center", fontsize=11, fontweight="bold")
    ax.set_yticks(y, [f"{int(ov.overall_rank[c])}. {PT.get(c, c)}" for c in order], fontsize=11.5, color=C.INK)
    ax.set_xlim(0, 10)
    ax.grid(axis="x", color=C.GRID, lw=0.8)
    ax.set_axisbelow(True)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=colr, label=NICHE_PT[n]) for n, colr in cols.items()], ncol=3,
              loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False, fontsize=11)
    ax.text(11.2, y.max() + 1.1, "DHA técnico (t/ano)", fontsize=9.5, color=C.INK2, ha="center", clip_on=False)
    for yi, c in zip(y, order):
        ax.text(11.2, yi, f"{ov.dha_need_total_t[c]:,.0f}".replace(",", "."), fontsize=10, color=C.INK2,
                ha="center", va="center", clip_on=False)
    C.save(fig, OUT / "market_overall_ranking.png")
    t = out["overall"].rename(columns={"overall_score": "score", "overall_rank": "rank"})
    side = {c: " + ".join(NICHE_PT[x.split(" ")[0]] for x in t.niches[c].split(", ")) for c in t.index}
    C.ranked_map(t, OUT / "market_map.png", f"Onde expandir o AlgaPrime DHA: top {N} países",
                 "Cor = score geral (mais claro = melhor); número = posição; nichos ao lado",
                 "Score geral = média dos scores por nicho (salmão, camarão, pet food) ponderada pela necessidade técnica de "
                 "DHA do país. Inclui logística desde Orindiúva. Fonte: market_ranking_overall.csv.",
                 top_n=N, side_text=side, points=POINTS)


def memo(out: dict) -> None:
    cfg = out["cfg"]
    ov, pairs = out["overall"], out["pairs"]
    tips = pd.read_csv(OUT / "market_tipping_points.csv")
    L = ["# Melhores países para a Corbion expandir o AlgaPrime DHA – salmão, camarão e pet food\n",
         "*Gerado por `python -m src market` · ranking ponderado por nicho (5 critérios: tamanho e crescimento 30%, "
         "valor 20%, acesso e posição competitiva 20%, regulação 15%, risco 15%) e ranking geral. "
         "O critério de acesso inclui **logística até o cliente** (25% do critério): dias porta a porta desde "
         "Orindiúva por rota marítima, LPI 2023 e conectividade marítima (UNCTAD) do destino. "
         "Mostra o top 10 de cada nicho; todos os países avaliados estão nos CSVs.*\n",
         "> **Natureza do resultado.** Score de triagem 0–10, não receita nem VPL. Fontes públicas, em boa parte lidas "
         "por trechos de busca; cada valor tem fonte, tipo e confiança em `data/processed/market_inputs_long.csv`. "
         "O volume e a receita por mercado continuam no estudo `market_expansion/`.\n",
         "## 1. Resposta\n"]
    top = list(ov.index[:5])
    L.append("**Ranking geral (top 5):** " + ", ".join(
        f"{int(ov.overall_rank[c])}. {PT.get(c, c)} ({fmt(ov.overall_score[c], 2)}, melhor nicho: "
        f"{NICHE_PT[ov.best_niche[c]]})" for c in top) + ".\n")
    for n, r in out["results"].items():
        t = r["table"]
        a, b = t.index[0], t.index[1]
        L.append(f"- **{NICHE_PT[n].capitalize()}:** 1º {PT.get(a, a)} ({fmt(t.score[a], 2)}), 2º {PT.get(b, b)} "
                 f"({fmt(t.score[b], 2)}), 3º {PT.get(t.index[2], t.index[2])} ({fmt(t.score[t.index[2]], 2)}). "
                 f"{PT.get(a, a)} é 1º em {pct(t.p_rank1_weights[a])} dos sorteios de pesos e em "
                 f"{pct(t.p_rank1_data[a])} das simulações de dados; só com métricas quantitativas o 1º é "
                 f"{PT.get(t.rank_quant_only.idxmin())}.")
    L.append("")
    L.append("**Consolidar vs. expandir:** países onde a Corbion já tem adoção documentada (score de acesso alto) são "
             "consolidação; países com tamanho/crescimento altos e acesso baixo são expansão. Ver seção 3.\n")
    L.append("## 2. Rankings por nicho\n")
    N = cfg.get("top_n", 10)
    for n, r in out["results"].items():
        t = r["table"].head(N)
        L.append(f"### {NICHE_PT[n].capitalize()} – top {N} de {len(r['table'])} países avaliados\n")
        L.append("| # | País | Score | Tamanho/cresc. (30%) | Valor (20%) | Acesso (20%) | Regulação (15%) | Risco (15%) | "
                 "Dias desde Orindiúva | DHA técnico (t) | P(1º) pesos | Cobertura de dados |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        pref = {"salmon": "sal", "shrimp": "shr", "pet": "pet"}[n]
        dd = r["data"]
        days = {c: fmt(float(v), 0) for c, v in dd[dd.metric_id == f"{pref}_transit_days"].set_index("country").raw_value.items()}
        for c in t.index:
            x = t.loc[c]
            dha = "" if pd.isna(x.dha_need_t) else f"{x.dha_need_t:,.0f}".replace(",", ".")
            L.append(f"| {int(x['rank'])} | {PT.get(c, c)} | **{fmt(x.score, 2)}** | {fmt(x.size_growth)} | {fmt(x.value)} | "
                     f"{fmt(x.access)} | {fmt(x.regulatory)} | {fmt(x.risk)} | {days.get(c, '')} | {dha} | {pct(x.p_rank1_weights)} | "
                     f"{pct(x.data_coverage_of_weight)} |")
        L.append("")
    L.append(f"## 3. Ranking geral – top {N} de {len(ov)} países\n")
    L.append("| # | País | Score geral | DHA técnico total (t/ano) | Nichos (score) | Papel |")
    L.append("|---|---|---|---|---|---|")
    for c in ov.index[:N]:
        x = ov.loc[c]
        n = x.best_niche
        acc = out["results"][n]["table"].access[c]
        size = out["results"][n]["table"].size_growth[c]
        role = ("consolidar" if acc >= 5 else "expandir" if size >= 5 else "monitorar")
        L.append(f"| {int(x.overall_rank)} | {PT.get(c, c)} | **{fmt(x.overall_score, 2)}** | "
                 f"{x.dha_need_total_t:,.0f}".replace(",", ".") + f" | {x.niches.replace('salmon', 'salmão').replace('shrimp', 'camarão')} | {role} |")
    L.append("\n*Papel:* consolidar = acesso ≥ 5 no melhor nicho; expandir = acesso < 5 e tamanho/crescimento ≥ 5; "
             "monitorar = demais.\n")
    L.append("## 4. Pontos de virada (líder × 2º de cada nicho)\n")
    for n in out["results"]:
        tt = tips[(tips.niche == n)]
        b = tt.challenger.iloc[0]
        a = tt.leader.iloc[0]
        tt = tt[tt.challenger == b]
        parts = []
        for _, r in tt.iterrows():
            x = r.weight_where_challenger_overtakes
            if not pd.isna(x):
                parts.append(f"{CRIT_SHORT[r.criterion].replace(chr(10), ' ')} ≥ {pct(x)} (base {pct(r.base_weight)})")
        L.append(f"- **{NICHE_PT[n].capitalize()}:** {PT.get(b, b)} passa {PT.get(a, a)} se "
                 + ("; ou ".join(parts) if parts else "nunca, em nenhum peso de critério isolado") + ".")
    L.append("\n## 5. Limitações\n")
    L.append("- Muitos valores vieram de trechos de busca e alguns de conhecimento do analista (marcados Low); "
             "conferir Medium/Low na fonte primária.")
    L.append("- Rubricas de relacionamento e registro aplicadas por um único analista; template em "
             "`outputs/market/market_rubric_ratings_template.csv`.")
    for n, r in out["results"].items():
        if r["dropped"]:
            L.append(f"- {NICHE_PT[n].capitalize()}: métricas fora do score por cobertura < 40% dos países: "
                     + ", ".join(r["dropped"]) + " (seguem no CSV para quando houver dado).")
    L.append("- A necessidade técnica de DHA usa os mesmos g/kg de ração do estudo de mercado para todos os países do "
             "nicho (salmão 5,3; camarão 2,7; pet food 0,33 g DHA/kg).")
    (OUT / "market_country_memo.md").write_text("\n".join(L), encoding="utf-8")
