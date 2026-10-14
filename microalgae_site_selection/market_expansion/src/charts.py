"""16:9 slide charts on the navy/purple deck background (palette validated for the v3 study)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

PLAIN = FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", "."))

from .data import ROOT  # noqa: E402

SURFACE = "#0B0630"
INK, INK2, MUTED, GRID = "#FFFFFF", "#D5D2DA", "#B6B3BA", "#3A3550"
BLUE, MAGENTA, VIOLET, SILVER = "#3987e5", "#d55181", "#9085e9", "#B6B3BA"
APP_COLOR = {"salmon": BLUE, "shrimp": MAGENTA, "pet_food": VIOLET, "china": SILVER}
APP_LABEL = {"salmon": "Salmão", "shrimp": "Camarão (ex-China)", "pet_food": "Pet food", "china": "China (camarão)"}
FONT_DIR = ROOT.parent / "assets" / "fonts"


def setup():
    from matplotlib import font_manager
    for f in FONT_DIR.glob("*.ttf"):
        font_manager.fontManager.addfont(str(f))
    plt.rcParams.update({
        "font.family": "Montserrat", "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2,
        "ytick.color": INK2, "axes.edgecolor": GRID, "axes.facecolor": "none", "savefig.facecolor": SURFACE,
        "axes.spines.top": False, "axes.spines.right": False, "font.size": 12.5, "text.parse_math": False})


def slide(title, subtitle, note):
    fig = plt.figure(figsize=(16, 9), dpi=160)
    bg = fig.add_axes([0, 0, 1, 1], zorder=-10)
    cmap = LinearSegmentedColormap.from_list("bg", ["#000E38", "#060216", "#2E0133"])
    bg.imshow(np.linspace(0, 1, 256)[:, None], aspect="auto", cmap=cmap, extent=[0, 1, 0, 1])
    bg.axis("off")
    fig.text(0.04, 0.93, title, fontsize=25, fontweight="bold")
    fig.text(0.04, 0.885, subtitle, fontsize=13.5, color=INK2)
    fig.text(0.04, 0.025, note, fontsize=9.5, color=MUTED)
    return fig


def _grid(ax, axis="x"):
    ax.grid(axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, path):
    fig.savefig(path, dpi=160)
    plt.close(fig)


def niche(df: pd.DataFrame) -> pd.Series:
    return np.where(df["region"] == "CHINA", "china", df["application"])


def bridge(seg: pd.DataFrame, path: Path, year: int = 2030):
    s = seg[seg.year == year].copy()
    s["niche"] = niche(s)
    steps = [("stage_feed_t", "Ração (t)"), ("tam_dha_t", "TAM (t DHA)"), ("sam_dha_t", "SAM (t DHA)"),
             ("algal_dha_t", "DHA de algas (t)"), ("som_dha_t", "SOM Corbion (t DHA)")]
    fig = slide(f"Da aquicultura à receita: ponte por nicho ({year}, cenário base)",
                "Cada barra é um denominador visível; escala logarítmica. Receita B2B líquida à Corbion à direita",
                "Fonte: segments_by_year.csv. TAM = necessidade técnica de DHA; SAM = espaço que DHA de algas pode suprir "
                "(econômico, técnico, regulatório, não suprido por marinhos);\nSOM = SAM × adoção × participação. "
                "PREMISSAS em nutrition_requirements.csv e market_parameters.csv.")
    order = ["salmon", "shrimp", "china", "pet_food"]
    for k, n in enumerate(order):
        g = s[s.niche == n]
        ax = fig.add_axes([0.13 + k * 0.215, 0.14, 0.17, 0.62])
        vals = [g[c].sum() for c, _ in steps]
        y = np.arange(len(steps))[::-1]
        ax.barh(y, vals, color=APP_COLOR[n], height=0.6, edgecolor=SURFACE)
        ax.set_xscale("log")
        ax.set_xlim(1, 1e8)
        for yi, v in zip(y, vals):
            ax.text(v * 1.4 if v > 0 else 1.5, yi, f"{v:,.0f}".replace(",", "."), va="center", fontsize=10, color=INK)
        ax.set_yticks(y, [lab for _, lab in steps] if k == 0 else [""] * len(steps), color=INK, fontsize=10.5)
        ax.set_title(f"{APP_LABEL[n]}\nreceita US$ {g.revenue_usd.sum() / 1e6:,.1f} mi".replace(".", ","), color=INK,
                     fontsize=12.5, loc="left")
        ax.set_xticks([1e1, 1e3, 1e5, 1e7])
        ax.xaxis.set_major_formatter(PLAIN)
        ax.xaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
        ax.tick_params(axis="x", labelsize=8.5)
        _grid(ax)
    save(fig, path)


def heatmap(seg: pd.DataFrame, mkt: pd.DataFrame, path: Path, year: int = 2030):
    s = seg[(seg.year == year) & (seg.stage != "wet_treats_excluded")].copy()
    base = seg[seg.year == 2025][["country", "stage", "contribution_usd"]].rename(columns={"contribution_usd": "c25"})
    s = s.merge(base, on=["country", "stage"])
    doc = mkt.set_index("country")["group"].eq("consolidation")
    s["inc"] = (s.contribution_usd - np.where(s.country.map(doc), s.c25, 0)) / 1e6
    s["col"] = s.application.map({"salmon": "Salmão", "shrimp": "Camarão", "pet_food": "Pet"}) + " · " + s.stage
    piv = s.pivot_table(index="country", columns="col", values="inc", aggfunc="sum")
    conf = mkt.set_index("country")["data_confidence"].str[0].str.upper()
    piv = piv.loc[piv.sum(axis=1).sort_values(ascending=False).index]
    fig = slide(f"Contribuição incremental por país × nicho ({year}, US$ mi/ano)",
                "Vazio = combinação inexistente. Letra = confiança do dado de volume (H/M/L). Incremental sobre 2025 nos "
                "mercados com relação documentada",
                "Fonte: segments_by_year.csv, market_rankings.csv. Contribuição = volume × (preço líquido − custo variável − "
                "frete − custos comerciais). Valores de premissa; sem contratos públicos.")
    ax = fig.add_axes([0.16, 0.20, 0.70, 0.62])
    cmap = LinearSegmentedColormap.from_list("seq", ["#1b1640", BLUE, "#9FB0FA"])
    vals = piv.values
    im = ax.imshow(np.where(np.isnan(vals), np.nan, np.log10(np.clip(vals, 0.001, None))), cmap=cmap, aspect="auto")
    for i in range(vals.shape[0]):
        for j in range(vals.shape[1]):
            if not np.isnan(vals[i, j]):
                ax.text(j, i, f"{vals[i, j]:.2f}".replace(".", ","), ha="center", va="center", fontsize=10.5,
                        color=INK if vals[i, j] < 2 else SURFACE)
    ax.set_xticks(range(piv.shape[1]), [c.replace("_", " ") for c in piv.columns], rotation=30, ha="right", fontsize=10)
    ax.set_yticks(range(piv.shape[0]), [f"{c}  [{conf.get(c, '?')}]" for c in piv.index], color=INK)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("log10 US$ mi", color=INK2)
    save(fig, path)


def adoption_curves(segs: dict, mkts: dict, path: Path):
    fig = slide("Volume incremental capturável pela Corbion, 2025–2035",
                "t SKU/ano acima de 2025 (mercados documentados) ou desde a entrada (novos); faixa = cenários baixo–alto",
                "Fonte: market_demand_curves.csv. Curva S só onde há qualificação/processo comercial; sem CAGR de relatório de "
                "mercado. Cenário baixo combina todas as premissas desfavoráveis (stress).")
    ax = fig.add_axes([0.08, 0.13, 0.70, 0.68])
    for n in ["salmon", "shrimp", "china", "pet_food"]:
        band = {}
        for sc, seg in segs.items():
            s = seg.copy()
            s["niche"] = niche(s)
            docs = set(mkts[sc][mkts[sc].group == "consolidation"].country)
            g = s[s.niche == n].groupby(["country", "year"]).som_sku_t.sum().unstack(0)
            inc = pd.DataFrame({c: (g[c] - g[c].iloc[0]) if c in docs else g[c] for c in g.columns}).clip(lower=0)
            band[sc] = inc.sum(axis=1)
        x = band["base"].index
        ax.fill_between(x, band["low"], band["high"], color=APP_COLOR[n], alpha=0.18, linewidth=0)
        ax.plot(x, band["base"], color=APP_COLOR[n], linewidth=2.2, label=APP_LABEL[n])
        ax.text(x[-1] + 0.15, band["base"].iloc[-1], APP_LABEL[n], color=INK, fontsize=11, va="center")
    ax.set_yscale("symlog", linthresh=100)
    ax.yaxis.set_major_formatter(PLAIN)
    ax.set_ylabel("t SKU/ano (escala simlog)")
    ax.legend(frameon=False, loc="upper left")
    _grid(ax, "y")
    save(fig, path)


def competitiveness_margin(mkt: pd.DataFrame, path: Path):
    fig = slide("Competitividade × margem unitária por mercado",
                "x = intensidade competitiva (julgamento 0–10); y = margem de contribuição por kg DHA; área = volume incremental 2030",
                "Fonte: market_rankings.csv. Margem usa custo variável de Orindiúva (v3) + frete do Brasil. Azul = consolidação "
                "(relação documentada), magenta = expansão.")
    ax = fig.add_axes([0.08, 0.13, 0.84, 0.68])
    for _, r in mkt.iterrows():
        col = BLUE if r.group == "consolidation" else MAGENTA
        ax.scatter(r.competitive_intensity, r.unit_contribution_usd_kg_dha, s=60 + r.incremental_sku_2030_t / 4,
                   color=col, alpha=0.75, edgecolor=SURFACE, linewidth=2)
        ax.annotate(f"{r.country} ({APP_LABEL['china' if r.region == 'CHINA' else r.application].split(' ')[0]})",
                    (r.competitive_intensity, r.unit_contribution_usd_kg_dha), xytext=(8, 6), textcoords="offset points",
                    fontsize=10, color=INK)
    ax.set_xlabel("Intensidade competitiva (10 = mais intensa)")
    ax.set_ylabel("Margem de contribuição (US$/kg DHA)")
    _grid(ax, "both")
    save(fig, path)


def capacity_price_frontier(be: pd.DataFrame, price: float, module_t: float, path: Path):
    b = be.dropna(subset=["breakeven_price_usd_kg_dha"])
    fig = slide("Capacidade vendável × preço necessário",
                "Volume incremental 2030 acumulado dos mercados cujo VPL comercial é positivo a cada preço líquido",
                f"Fonte: capacity_price_frontier.csv. Linha tracejada = preço-base (US$ {price:.0f}/kg DHA, premissa); "
                f"pontilhada = 1 módulo v3 ({module_t:,.0f} t efetivas). Mercados sem breakeven até US$ 200 omitidos.")
    ax = fig.add_axes([0.08, 0.13, 0.84, 0.68])
    xs, ys = [0], [0.0]
    for r in b.itertuples():
        xs += [r.breakeven_price_usd_kg_dha, r.breakeven_price_usd_kg_dha]
        ys += [ys[-1], ys[-1] + r.incremental_sku_2030_t]
        ax.annotate(r.country, (r.breakeven_price_usd_kg_dha, ys[-1]), xytext=(6, 4), textcoords="offset points",
                    fontsize=10, color=INK)
    xs.append(max(130, xs[-1] + 5))
    ys.append(ys[-1])
    ax.plot(xs, ys, color=BLUE, linewidth=2.5, drawstyle="default")
    ax.axvline(price, color=MAGENTA, linestyle="--", linewidth=1.5)
    ax.axhline(module_t, color=MUTED, linestyle=":", linewidth=1.5)
    ax.set_xlabel("Preço líquido necessário (US$/kg DHA)")
    ax.set_ylabel("Volume incremental 2030 acumulado (t SKU)")
    ax.set_xlim(0, 130)
    _grid(ax, "both")
    save(fig, path)


def rankings_chart(rk: pd.DataFrame, path: Path):
    fig = slide("Dois rankings separados: consolidar × expandir",
                "VPL comercial ponderado pela probabilidade de qualificação (2026–2035, US$ mi, 10% a.a.)",
                "Fonte: market_rankings.csv. Inclui custos de equipe comercial/técnica, registros e ensaios. Volumes são "
                "PREMISSAS; nenhum contrato público.")
    for k, (grp, title, col) in enumerate((("consolidation", "Consolidação (uso documentado)", BLUE),
                                          ("expansion", "Expansão (sem uso documentado)", MAGENTA))):
        g = rk[rk.group == grp].sort_values("commercial_npv_musd")
        ax = fig.add_axes([0.14 + k * 0.48, 0.13, 0.32, 0.66])
        lab = g.country + " · " + g.application.map({"salmon": "salmão", "shrimp": "camarão", "pet_food": "pet"})
        ax.barh(lab, g.commercial_npv_musd, color=col, height=0.6, edgecolor=SURFACE)
        for yi, v in enumerate(g.commercial_npv_musd):
            ax.text(v + (0.5 if v >= 0 else -0.5), yi, f"{v:,.1f}".replace(".", ","), va="center",
                    ha="left" if v >= 0 else "right", fontsize=10.5, color=INK)
        ax.axvline(0, color=MUTED, linewidth=1)
        ax.set_title(title, loc="left", color=INK, fontsize=14)
        ax.tick_params(axis="y", colors=INK)
        _grid(ax)
    save(fig, path)


def customer_map(acc: pd.DataFrame, feed: pd.DataFrame, path: Path):
    import geopandas as gpd
    geo = next((ROOT.parent / "assets" / "geo").glob("*.geojson"))
    world = gpd.read_file(geo)
    fig = slide("Contas e fluxos: onde há uso documentado × apenas potencial",
                "Azul = relação documentada (histórica/canal); magenta = potencial; linhas = rotas a partir de Orindiúva",
                "Fonte: customer_evidence.csv. Documentado ≠ volume atual: continuidade e tonelagem precisam de prova "
                "(next_proof_needed). GACC/JV = acesso, não cliente.")
    ax = fig.add_axes([0.03, 0.08, 0.94, 0.78])
    world.plot(ax=ax, color="#FFFFFF", alpha=0.10, edgecolor="#FFFFFF", linewidth=0.3)
    pos = feed.set_index("country")[["lat", "lon"]]
    ori = (-20.18, -49.35)
    best: dict[str, bool] = {}
    for _, a in acc.iterrows():
        for c in str(a["countries"]).split(";"):
            c = c.strip()
            if c in pos.index:
                best[c] = best.get(c, False) or a.type == "consolidation"
    drawn = set(best)
    for c, doc in best.items():
        lat, lon = pos.loc[c]
        col = BLUE if doc else MAGENTA
        ax.plot([ori[1], lon], [ori[0], lat], color=col, alpha=0.35, linewidth=1)
        ax.scatter(lon, lat, s=140, color=col, edgecolor=INK, linewidth=0.8, alpha=0.85, zorder=4)
    for c in drawn:
        lat, lon = pos.loc[c]
        ax.text(lon + 2, lat + 2, c, fontsize=9.5, color=INK)
    ax.scatter(ori[1], ori[0], marker="D", s=90, color=VIOLET, edgecolor=INK, zorder=5)
    ax.text(ori[1] + 2, ori[0] - 4, "Orindiúva", fontsize=10, color=INK)
    ax.set_xlim(-130, 160)
    ax.set_ylim(-55, 75)
    ax.axis("off")
    save(fig, path)
