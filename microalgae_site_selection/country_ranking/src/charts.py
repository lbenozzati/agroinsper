"""16:9 slide charts in the deck's navy/purple style, shared by the plant and market rankings."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import geopandas as gpd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT.parent / "assets"
SURFACE = "#0B0630"
INK, INK2, MUTED, GRID = "#FFFFFF", "#D5D2DA", "#B6B3BA", "#3A3550"
BLUE, MAGENTA, VIOLET, SILVER = "#3987e5", "#d55181", "#9085e9", "#B6B3BA"
CRIT_COLORS = [BLUE, MAGENTA, VIOLET, SILVER, "#5fc4c0", "#e3a857"]
SEQ = LinearSegmentedColormap.from_list("seq", ["#1b1640", "#3b2f7a", BLUE, "#9FB0FA"])
PT = {"Brazil": "Brasil", "Thailand": "Tailândia", "China": "China", "India": "Índia", "Vietnam": "Vietnã",
      "Indonesia": "Indonésia", "Chile": "Chile", "Mexico": "México", "United States": "EUA", "Ecuador": "Equador",
      "Peru": "Peru", "Philippines": "Filipinas", "Norway": "Noruega", "United Kingdom": "Reino Unido",
      "Australia": "Austrália", "Canada": "Canadá", "Faroe Islands": "Ilhas Faroé", "Iceland": "Islândia",
      "European Union": "União Europeia", "Japan": "Japão", "Germany": "Alemanha", "France": "França",
      "Bangladesh": "Bangladesh", "Honduras": "Honduras", "Saudi Arabia": "Arábia Saudita", "Turkey": "Turquia",
      "Greece": "Grécia", "Spain": "Espanha", "Italy": "Itália", "Poland": "Polônia", "Argentina": "Argentina",
      "South Korea": "Coreia do Sul", "Russia": "Rússia", "New Zealand": "Nova Zelândia"}


def fmt(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def setup():
    from matplotlib import font_manager
    for f in (ASSETS / "fonts").glob("*.ttf"):
        font_manager.fontManager.addfont(str(f))
    plt.rcParams.update({"font.family": "Montserrat", "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.edgecolor": GRID, "axes.facecolor": "none",
                         "savefig.facecolor": SURFACE, "axes.spines.top": False, "axes.spines.right": False,
                         "font.size": 12.5, "text.parse_math": False})


def slide(title, subtitle, note):
    fig = plt.figure(figsize=(16, 9), dpi=160)
    bg = fig.add_axes([0, 0, 1, 1], zorder=-10)
    bg.imshow(np.linspace(0, 1, 256)[:, None], aspect="auto",
              cmap=LinearSegmentedColormap.from_list("bg", ["#000E38", "#060216", "#2E0133"]), extent=[0, 1, 0, 1])
    bg.axis("off")
    fig.text(0.04, 0.93, title, fontsize=25, fontweight="bold")
    fig.text(0.04, 0.885, subtitle, fontsize=13.5, color=INK2)
    fig.text(0.04, 0.022, note, fontsize=9.5, color=MUTED, wrap=True)
    return fig


def save(fig, path: Path):
    fig.savefig(path, dpi=160)
    plt.close(fig)


def heatmap(tab: pd.DataFrame, crit_labels: dict, weights: dict, path: Path, title: str, subtitle: str, note: str,
            extra_cols: dict | None = None):
    """Rows = countries sorted by score; columns = criteria (weight in header) + total."""
    cols = list(crit_labels)
    mat = tab[cols].to_numpy(dtype=float)
    fig = slide(title, subtitle, note)
    n = len(tab)
    ax = fig.add_axes([0.20, 0.10, 0.62, 0.72])
    ax.imshow(mat, cmap=SEQ, vmin=0, vmax=10, aspect="auto")
    for i in range(n):
        for j in range(len(cols)):
            v = mat[i, j]
            ax.text(j, i, "–" if np.isnan(v) else fmt(v), ha="center", va="center", fontsize=12,
                    color=SURFACE if (not np.isnan(v) and v >= 7.2) else INK)
    ax.set_xticks(range(len(cols)), [f"{crit_labels[c]}\n{weights[c]:.0%}" for c in cols], fontsize=10.5)
    ax.xaxis.tick_top()
    ax.set_yticks(range(n), [f"{int(r)}. {PT.get(c, c)}" for c, r in zip(tab.index, tab["rank"])], fontsize=13,
                  color=INK)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax2 = fig.add_axes([0.83, 0.10, 0.07, 0.72])
    ax2.imshow(tab[["score"]].to_numpy(dtype=float), cmap=SEQ, vmin=0, vmax=10, aspect="auto")
    for i, v in enumerate(tab["score"]):
        ax2.text(0, i, fmt(v, 2), ha="center", va="center", fontsize=13, fontweight="bold",
                 color=SURFACE if v >= 7.2 else INK)
    ax2.set_xticks([0], ["Score\nfinal"], fontsize=11)
    ax2.xaxis.tick_top()
    ax2.set_yticks([])
    ax2.tick_params(length=0)
    for s in ax2.spines.values():
        s.set_visible(False)
    if extra_cols:
        for k, (label, series) in enumerate(extra_cols.items()):
            x = 0.915 + k * 0.045
            fig.text(x, 0.835, label, fontsize=9.5, color=INK2, ha="center")
            for i, c in enumerate(tab.index):
                y = 0.82 - (i + 0.5) * 0.72 / n
                fig.text(x, y, str(series.get(c, "")), fontsize=10, color=INK2, ha="center", va="center")
    save(fig, path)


def contributions(contrib: pd.DataFrame, crit_labels: dict, order: list[str], path: Path, title: str, subtitle: str,
                  note: str):
    fig = slide(title, subtitle, note)
    ax = fig.add_axes([0.16, 0.12, 0.78, 0.68])
    y = np.arange(len(order))[::-1]
    left = np.zeros(len(order))
    for k, c in enumerate(crit_labels):
        v = contrib.loc[order, c].fillna(0).to_numpy()
        ax.barh(y, v, left=left, color=CRIT_COLORS[k], height=0.62, label=crit_labels[c], edgecolor=SURFACE, lw=1)
        left += v
    for yi, tot in zip(y, left):
        ax.text(tot + 0.05, yi, fmt(tot, 2), va="center", fontsize=12, fontweight="bold")
    ax.set_yticks(y, [PT.get(c, c) for c in order], fontsize=13, color=INK)
    ax.set_xlim(0, 10)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.legend(ncol=len(crit_labels), loc="lower center", bbox_to_anchor=(0.45, 1.0), frameon=False, fontsize=11)
    save(fig, path)


def rank_probability(tab: pd.DataFrame, path: Path, title: str, subtitle: str, note: str):
    order = list(tab.index)
    fig = slide(title, subtitle, note)
    ax = fig.add_axes([0.16, 0.12, 0.78, 0.68])
    y = np.arange(len(order))[::-1]
    h = 0.26
    series = [("p_rank1_weights", "P(1º) – pesos incertos", BLUE), ("p_rank1_data", "P(1º) – dados incertos", MAGENTA),
              ("p_top3_data", "P(top 3) – dados incertos", VIOLET)]
    for k, (col, lab, colr) in enumerate(series):
        ax.barh(y + (1 - k) * h, tab[col].to_numpy(), height=h, color=colr, label=lab)
    ax.set_yticks(y, [PT.get(c, c) for c in order], fontsize=13, color=INK)
    ax.set_xlim(0, 1)
    ax.set_xticks(np.linspace(0, 1, 6), [f"{int(v * 100)}%" for v in np.linspace(0, 1, 6)])
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.45, 1.0), frameon=False, fontsize=11)
    save(fig, path)


def bubble_map(tab: pd.DataFrame, path: Path, title: str, subtitle: str, note: str, extent=(-130, 160, -50, 65),
               points: dict | None = None):
    """Bubble area proportional to score (triage, not NPV); only the leader is highlighted."""
    world = gpd.read_file(ASSETS / "geo" / "ne_110m_admin_0_countries.geojson")
    fig = slide(title, subtitle, note)
    ax = fig.add_axes([0.03, 0.08, 0.94, 0.76])
    world.plot(ax=ax, color="#1d1846", edgecolor="#3a3466", linewidth=0.4)
    sel = world[world.NAME.isin(tab.index)]
    sel.plot(ax=ax, color="#2c2566", edgecolor="#5b5399", linewidth=0.6)
    leader = tab["rank"].idxmin()
    for c, r in tab.iterrows():
        if points and c in points:
            lon, lat = points[c]
        else:
            g = world[world.NAME == c]
            if g.empty:
                continue
            pt = g.geometry.iloc[0].representative_point()
            lon, lat = pt.x, pt.y
        size = (r.score / 10) ** 2 * 2600
        ax.scatter(lon, lat, s=size, color=INK if c == leader else BLUE, alpha=0.9 if c == leader else 0.55,
                   edgecolor=INK, linewidth=0.8, zorder=5)
        ax.text(lon, lat - 4 - np.sqrt(size) / 9, f"{int(r['rank'])}. {PT.get(c, c)}  {fmt(r.score, 2)}",
                ha="center", va="top", fontsize=10.5, color=INK, zorder=6, fontweight="bold" if c == leader else None)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.axis("off")
    save(fig, path)


def matrix(df: pd.DataFrame, path: Path, title: str, subtitle: str, note: str, fmt_d=0, cmap=None, vmin=None,
           vmax=None, reverse=False):
    fig = slide(title, subtitle, note)
    ax = fig.add_axes([0.16, 0.10, 0.80, 0.68])
    cm = cmap or (SEQ.reversed() if reverse else SEQ)
    ax.imshow(df.to_numpy(dtype=float), cmap=cm, aspect="auto", vmin=vmin, vmax=vmax)
    hi = np.nanpercentile(df.to_numpy(dtype=float), 30 if reverse else 70)
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            v = df.iat[i, j]
            dark = (v <= hi) if reverse else (v >= hi)
            ax.text(j, i, "–" if pd.isna(v) else fmt(v, fmt_d), ha="center", va="center", fontsize=10.5,
                    color=SURFACE if dark else INK)
    ax.set_xticks(range(df.shape[1]), [PT.get(c, c) for c in df.columns], rotation=35, ha="left", fontsize=10.5)
    ax.xaxis.tick_top()
    ax.set_yticks(range(df.shape[0]), [PT.get(c, c) for c in df.index], fontsize=12, color=INK)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    save(fig, path)
