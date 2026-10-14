"""Slide charts (16:9, navy/purple background). Palette validated with the dataviz validator on #0B0630:
blue #3987e5, magenta #d55181, violet #9085e9 (all checks pass); silver for 'other' / neutral."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402

from .data import ROOT  # noqa: E402

SURFACE = "#0B0630"
BG_TOP, BG_BOTTOM = "#000E38", "#2E0133"
INK, INK2, MUTED, GRID = "#FFFFFF", "#D5D2DA", "#B6B3BA", "#3A3550"
BLUE, MAGENTA, VIOLET, SILVER = "#3987e5", "#d55181", "#9085e9", "#B6B3BA"
FONT_DIR = ROOT.parent / "assets" / "fonts"


def setup():
    from matplotlib import font_manager
    for f in FONT_DIR.glob("*.ttf"):
        font_manager.fontManager.addfont(str(f))
    names = {font_manager.FontProperties(fname=str(f)).get_name() for f in FONT_DIR.glob("*.ttf")}
    plt.rcParams.update({
        "font.family": "Montserrat" if "Montserrat" in names else "DejaVu Sans",
        "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "axes.edgecolor": GRID, "axes.facecolor": "none", "savefig.facecolor": SURFACE,
        "axes.spines.top": False, "axes.spines.right": False, "font.size": 13, "text.parse_math": False,
    })


def slide(title: str, subtitle: str, note: str):
    fig = plt.figure(figsize=(16, 9), dpi=160)
    bg = fig.add_axes([0, 0, 1, 1], zorder=-10)
    grad = np.linspace(0, 1, 256)[:, None]
    cmap = LinearSegmentedColormap.from_list("bg", [BG_TOP, "#060216", BG_BOTTOM])
    bg.imshow(grad, aspect="auto", cmap=cmap, extent=[0, 1, 0, 1], origin="upper")
    bg.axis("off")
    fig.text(0.04, 0.93, title, fontsize=26, fontweight="bold", color=INK)
    fig.text(0.04, 0.885, subtitle, fontsize=14, color=INK2)
    fig.text(0.04, 0.025, note, fontsize=9.5, color=MUTED, wrap=True)
    return fig


def _grid(ax, axis="x"):
    ax.grid(axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, path: Path):
    fig.savefig(path, dpi=160)
    plt.close(fig)


def cost_waterfall(ue: pd.DataFrame, path: Path):
    """Left: full cost per kg DHA by site (stacked). Right: bridge Orindiúva -> Nakhon Sawan."""
    comp = pd.DataFrame({
        "Açúcar": ue["sugar_usd_per_t"],
        "Energia, vapor e água": ue["electricity_usd_per_t"] + ue["steam_usd_per_t"] + ue["water_effluent_usd_per_t"],
        "Encargo de capital": ue["capital_charge_usd_per_t"],
        "Outros (insumos, fixos, frete, tributos)": ue["nutrients_packaging_usd_per_t"] + ue["indirect_tax_leakage_usd_per_t"]
        + ue["fixed_usd_per_t"] + ue["freight_avg_usd_per_t"],
    })
    dha_kg = float((ue["cash_cost_usd_per_t"] / ue["cash_cost_usd_per_kg_dha"]).iloc[0])
    comp = comp / dha_kg
    comp.index = ue["site"]
    colors = [BLUE, MAGENTA, VIOLET, SILVER]
    fig = slide("Custo pleno por kg de DHA, por site (regime, 100% do módulo)",
                "USD de 2026 por kg de DHA no SKU P3 (36% DHA); encargo de capital = capex × fator de recuperação ao WACC do país",
                "Fonte: modelo v3 (unit_economics.csv). Açúcar: CEPEA ago/2026 (BR) e preço administrado 21 THB/kg (TH) — S017/S018; "
                "rendimento, capex e coeficientes de processo são PREMISSAS (assumptions.csv), não dados da Corbion.")
    ax = fig.add_axes([0.20, 0.12, 0.36, 0.62])
    left = np.zeros(len(comp))
    y = np.arange(len(comp))[::-1]
    for (name, col), c in zip(comp.items(), colors):
        ax.barh(y, col.values, left=left, color=c, edgecolor=SURFACE, linewidth=2, height=0.6, label=name)
        left += col.values
    for yi, tot in zip(y, left):
        ax.text(tot + 0.3, yi, f"US$ {tot:.1f}", va="center", color=INK, fontsize=13, fontweight="bold")
    ax.set_yticks(y, comp.index, color=INK)
    ax.set_xlabel("USD por kg de DHA")
    ax.set_xlim(0, left.max() * 1.22)
    _grid(ax)
    ax.legend(loc="lower left", bbox_to_anchor=(-0.38, 1.02), ncol=2, frameon=False, fontsize=11)

    a = comp.loc[comp.index[0]]
    b = comp.loc["Nakhon Sawan"]
    steps = [("Orindiúva", a.sum(), None)] + [(k, b[k] - a[k], k) for k in comp.columns] + [("Nakhon Sawan", b.sum(), None)]
    ax2 = fig.add_axes([0.64, 0.14, 0.33, 0.62])
    run = 0.0
    for i, (lab, val, key) in enumerate(steps):
        if key is None:
            ax2.bar(i, val, color="none", edgecolor=INK, linewidth=1.5, width=0.6)
            ax2.text(i, val + 0.3, f"{val:.1f}", ha="center", color=INK, fontsize=12, fontweight="bold")
            run = val
        else:
            ax2.bar(i, val, bottom=run, color=dict(zip(comp.columns, colors))[key], edgecolor=SURFACE, linewidth=2,
                    width=0.6)
            ax2.text(i, run + max(val, 0) + 0.3, f"{val:+.1f}", ha="center", color=INK2, fontsize=11)
            run += val
    ax2.set_xticks(range(len(steps)), ["Orindiúva", "Açúcar", "Energia\n/água", "Capital", "Outros", "Nakhon\nSawan"],
                   fontsize=10.5)
    ax2.set_ylabel("USD/kg DHA")
    ax2.set_title("Ponte de custo: Orindiúva → Nakhon Sawan", color=INK, fontsize=14, loc="left")
    _grid(ax2, "y")
    save(fig, path)


def tornado_chart(t1: pd.DataFrame, t2: pd.DataFrame, path: Path):
    fig = slide("O que mais move o resultado",
                "Variação de cada premissa entre o mínimo e o máximo da faixa, com as demais no caso base (cenário de demanda base)",
                "Fonte: modelo v3 (tornado_*.csv). Faixas em assumptions.csv. Barras azuis = valor no limite inferior da premissa; "
                "magenta = limite superior. VPL nominal em USD, inclui valor terminal.")
    for k, (t, title) in enumerate(((t1, "VPL de A1 (Orindiúva, 1 módulo), US$ mi"),
                                     (t2, "Diferença de VPL: C Tailândia − A1 Orindiúva, US$ mi"))):
        ax = fig.add_axes([0.20 + k * 0.45, 0.12, 0.30, 0.68])
        t = t.head(9).iloc[::-1]
        base = t["base"].iloc[0]
        y = np.arange(len(t))
        ax.barh(y, t["metric_at_low"] - base, left=base, color=BLUE, height=0.6, edgecolor=SURFACE)
        ax.barh(y, t["metric_at_high"] - base, left=base, color=MAGENTA, height=0.6, edgecolor=SURFACE)
        ax.axvline(base, color=INK2, linewidth=1)
        ax.axvline(0, color=MUTED, linewidth=1, linestyle=":")
        ax.set_yticks(y, t["label"], fontsize=10.5, color=INK)
        ax.set_title(title, color=INK, fontsize=13, loc="left")
        _grid(ax)
    save(fig, path)


def frontier_chart(fr: pd.DataFrame, capex: float, path: Path):
    s = fr[fr.capex_ori_musd == capex]
    piv = s.pivot(index="asia_contracted_t", columns="price_usd_kg_dha", values="delta_G_vs_A1")
    fig = slide("Quando a segunda unidade (Tailândia) se paga frente a só expandir Orindiúva",
                f"VPL incremental de G (Orindiúva + Nakhon Sawan já) − A1 (só Orindiúva), US$ mi; capex de Orindiúva = US$ {capex:.0f} mi",
                "Fonte: decision_frontier.csv. Volume asiático contratado = firme, adicional à demanda ponderada do cenário base "
                "(PREMISSAS, não pedidos). Linha branca = fronteira VPL incremental = 0. Não é previsão da Corbion.")
    ax = fig.add_axes([0.08, 0.13, 0.68, 0.68])
    vmax = np.nanmax(np.abs(piv.values))
    cmap = LinearSegmentedColormap.from_list("div", [BLUE, "#3a3550", MAGENTA])
    im = ax.imshow(piv.values, origin="lower", aspect="auto", cmap=cmap, norm=TwoSlopeNorm(0, -vmax, vmax),
                   extent=[piv.columns.min(), piv.columns.max(), piv.index.min() / 1000, piv.index.max() / 1000])
    X, Y = np.meshgrid(piv.columns.values, piv.index.values / 1000)
    cs = ax.contour(X, Y, piv.values, levels=[0], colors=INK, linewidths=2.5)
    ax.clabel(cs, fmt={0: "ΔVPL = 0"}, colors=INK, fontsize=11)
    ax.set_xlabel("Preço líquido realizado (US$/kg DHA)")
    ax.set_ylabel("Volume asiático contratado (mil t SKU/ano, a partir de 2029)")
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("ΔVPL G − A1 (US$ mi)", color=INK2)
    cb.ax.yaxis.set_tick_params(color=INK2)
    fig.text(0.80, 0.70, "Magenta: a 2ª unidade\nna Tailândia agrega valor", color=INK, fontsize=12)
    fig.text(0.80, 0.58, "Azul: melhor só\nexpandir Orindiúva", color=INK, fontsize=12)
    save(fig, path)


def risk_return(summary: pd.DataFrame, labels: dict, path: Path):
    fig = slide("Retorno esperado × perda nas caudas (Monte Carlo correlacionado)",
                "Média do VPL × expected shortfall dos 10% piores casos, US$ mi — condicionais às distribuições assumidas",
                "Fonte: monte_carlo_summary.csv (cópula gaussiana, correlações e faixas em config.yaml). Probabilidades são "
                "propagação de premissas, não previsão calibrada.")
    ax = fig.add_axes([0.08, 0.13, 0.86, 0.68])
    groups: list[list] = []
    for _, r in summary.iterrows():
        for g in groups:
            if abs(g[0].mean_npv_musd - r.mean_npv_musd) < 1.0 and abs(g[0].expected_shortfall_10pct - r.expected_shortfall_10pct) < 1.0:
                g.append(r)
                break
        else:
            groups.append([r])
    for g in groups:
        r = g[0]
        col = MAGENTA if "TH" in r.alternative and "ORI" not in r.alternative else (VIOLET if "TH" in r.alternative else BLUE)
        ax.scatter(r.expected_shortfall_10pct, r.mean_npv_musd, s=220, color=col, edgecolor=SURFACE, linewidth=2, zorder=3)
        text = labels[r.alternative] if len(g) == 1 else " = ".join(x.alternative.split("_")[0] for x in g) + " (gatilhos não disparam)"
        right = r.expected_shortfall_10pct > -60
        dy = -22 if r.alternative.startswith("E_") else 8
        ax.annotate(text, (r.expected_shortfall_10pct, r.mean_npv_musd), xytext=(-12 if right else 12, dy),
                    textcoords="offset points", color=INK, fontsize=11, ha="right" if right else "left")
    ax.axhline(0, color=MUTED, linewidth=1, linestyle=":")
    ax.axvline(0, color=MUTED, linewidth=1, linestyle=":")
    ax.set_xlabel("Expected shortfall 10% (média dos 10% piores VPLs, US$ mi) → menos risco à direita")
    ax.set_ylabel("VPL médio (US$ mi)")
    _grid(ax, "both")
    save(fig, path)


def site_map(ranking: pd.DataFrame, sites: pd.DataFrame, path: Path):
    import geopandas as gpd
    geo = next((ROOT.parent / "assets" / "geo").glob("*.geojson"))
    world = gpd.read_file(geo)
    fig = slide("Triagem de países e sites candidatos",
                "Área da bolha proporcional ao score de triagem (0–10) · azul = país na shortlist, prata = fora · losangos = sites avaliados por VPL",
                "O score é TRIAGEM, não VPL; ~65% do peso vem de rubricas de um avaliador. Fonte: ranking_v3.csv, "
                "site_candidates.csv. Natural Earth.")
    ax = fig.add_axes([0.03, 0.08, 0.94, 0.78])
    world.plot(ax=ax, color="#FFFFFF", alpha=0.10, edgecolor="#FFFFFF", linewidth=0.3)
    pos = {"Brazil": (-10.5, -52), "Thailand": (15.5, 101), "China": (34, 104), "India": (22, 79), "Vietnam": (14, 108),
           "Mexico": (23, -102), "Chile": (-33, -71), "Indonesia": (-2, 117)}
    label_off = {"Vietnam": (3.5, -6, "left"), "Thailand": (-1, -6, "center")}
    r = ranking.dropna(subset=["screening_score_v3"])
    for _, row in r.iterrows():
        lat, lon = pos[row.country]
        col = BLUE if row.shortlist == "yes" else SILVER
        ax.scatter(lon, lat, s=row.screening_score_v3 ** 2 * 18, color=col, alpha=0.55, edgecolor=INK, linewidth=0.8)
        dx, dy, ha = label_off.get(row.country, (0, -5.5, "center"))
        ax.text(lon + dx, lat + dy, f"{row.country} {row.screening_score_v3:.1f}", ha=ha, color=INK, fontsize=10)
    for _, srow in sites.iterrows():
        ax.scatter(srow.lon, srow.lat, marker="D", s=60, color=MAGENTA, edgecolor=INK, linewidth=0.8, zorder=5)
    ax.set_xlim(-120, 150)
    ax.set_ylim(-50, 55)
    ax.axis("off")
    save(fig, path)


def npv_ranges(summary: pd.DataFrame, labels: dict, path: Path):
    s = summary.sort_values("p50")
    fig = slide("VPL por alternativa: faixa p10–p90 e mediana",
                "US$ mi, nominal, inclui valor terminal; cenário base de demanda com incerteza correlacionada",
                "Fonte: monte_carlo_summary.csv. A demanda é PREMISSA (sem contratos públicos para nova capacidade).")
    ax = fig.add_axes([0.30, 0.12, 0.52, 0.70])
    y = np.arange(len(s))
    ax.hlines(y, s.p10, s.p90, color=VIOLET, linewidth=6)
    ax.scatter(s.p50, y, color=INK, s=70, zorder=3)
    for yi, (_, r) in zip(y, s.iterrows()):
        ax.text(r.p90 + 5, yi, f"p50 {r.p50:,.0f} · P(VPL>0) {r.prob_npv_positive:.0%}".replace(",", "."), va="center", color=INK2, fontsize=10)
    ax.axvline(0, color=MUTED, linestyle=":")
    ax.set_yticks(y, [labels[a] for a in s.alternative], color=INK, fontsize=11)
    ax.set_xlabel("VPL (US$ mi)")
    _grid(ax)
    save(fig, path)
