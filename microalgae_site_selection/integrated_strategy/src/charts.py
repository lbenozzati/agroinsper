"""16:9 slide charts (navy/purple deck; palette validated in the v3 study)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402

from .integration import ROOT  # noqa: E402

SURFACE = "#0B0630"
INK, INK2, MUTED, GRID = "#FFFFFF", "#D5D2DA", "#B6B3BA", "#3A3550"
BLUE, MAGENTA, VIOLET, SILVER = "#3987e5", "#d55181", "#9085e9", "#B6B3BA"
SITE_COLOR = {"BR_ORI_EXP": BLUE, "TH_NSN": MAGENTA, "BR_GF_GO": VIOLET, "TH_RYG": SILVER}
SITE_LABEL = {"BR_ORI_EXP": "Orindiúva", "TH_NSN": "Nakhon Sawan", "BR_GF_GO": "Greenfield GO", "TH_RYG": "Rayong"}
NICHE = {"salmon": "salmão", "shrimp": "camarão", "pet_food": "pet", "shrimp/fish": "China aqua"}
FONTS = ROOT.parent / "assets" / "fonts"


def setup():
    from matplotlib import font_manager
    for f in FONTS.glob("*.ttf"):
        font_manager.fontManager.addfont(str(f))
    plt.rcParams.update({"font.family": "Montserrat", "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.edgecolor": GRID, "axes.facecolor": "none", "savefig.facecolor": SURFACE,
                         "axes.spines.top": False, "axes.spines.right": False, "font.size": 12.5, "text.parse_math": False})


def slide(title, subtitle, note):
    fig = plt.figure(figsize=(16, 9), dpi=160)
    bg = fig.add_axes([0, 0, 1, 1], zorder=-10)
    bg.imshow(np.linspace(0, 1, 256)[:, None], aspect="auto",
              cmap=LinearSegmentedColormap.from_list("bg", ["#000E38", "#060216", "#2E0133"]), extent=[0, 1, 0, 1])
    bg.axis("off")
    fig.text(0.04, 0.93, title, fontsize=25, fontweight="bold")
    fig.text(0.04, 0.885, subtitle, fontsize=13.5, color=INK2)
    fig.text(0.04, 0.022, note, fontsize=9.5, color=MUTED)
    return fig


def save(fig, path):
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _grid(ax, axis="x"):
    ax.grid(axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def route_heatmap(routes: pd.DataFrame, path: Path):
    r = routes[routes.year == 2030].copy()
    r["dest"] = r.dest_country + " · " + r.niche.map(NICHE)
    piv = r.pivot_table(index="origin_site", columns="dest", values="contribution_usd_kg_dha")
    conf = r.groupby("dest").volume_confidence.first().str[0].str.upper()
    order = r.groupby("dest").market_som_sku_t.first().sort_values(ascending=False).index
    piv = piv[order].loc[["BR_ORI_EXP", "BR_GF_GO", "TH_NSN", "TH_RYG"]]
    fig = slide("Margem entregue por origem × destino (2030, US$/kg DHA)",
                "Preço líquido do estudo de mercado − custo variável do site (v3) − frete − estoque em trânsito − tarifa; "
                "[H/M/L] = confiança do volume",
                "Fonte: route_economics.csv. Custos fixos, capex, impostos e capital de giro ficam no fluxo de caixa, não aqui. "
                "Tarifas = 0 (não verificadas). China a partir de planta nova só após registro GACC próprio.")
    ax = fig.add_axes([0.13, 0.30, 0.78, 0.52])
    cmap = LinearSegmentedColormap.from_list("seq", ["#1b1640", BLUE, "#9FB0FA"])
    im = ax.imshow(piv.values, cmap=cmap, aspect="auto")
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            ax.text(j, i, f"{v:.1f}".replace(".", ","), ha="center", va="center", fontsize=10,
                    color=SURFACE if v > np.nanpercentile(piv.values, 70) else INK)
    ax.set_xticks(range(piv.shape[1]), [f"{c} [{conf[c]}]" for c in piv.columns], rotation=40, ha="right", fontsize=9.5)
    ax.set_yticks(range(piv.shape[0]), [SITE_LABEL[s] for s in piv.index], color=INK)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("US$/kg DHA", color=INK2)
    save(fig, path)


def _band(ax, x0, y0a, y0b, x1, y1a, y1b, color, alpha=0.45):
    xm = (x0 + x1) / 2
    verts = [(x0, y0a), (xm, y0a), (xm, y1a), (x1, y1a), (x1, y1b), (xm, y1b), (xm, y0b), (x0, y0b), (x0, y0a)]
    codes = [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.LINETO, MPath.CURVE4, MPath.CURVE4,
             MPath.CURVE4, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none", alpha=alpha))


def sankey(alloc: pd.DataFrame, path: Path, title_suffix: str):
    """Plant -> SKU -> country -> application (no double counting: one flow per allocated tonne)."""
    a = alloc[alloc.allocated_t > 0]
    total = a.allocated_t.sum()
    fig = slide("Capacidade → SKU → mercado → aplicação, sem dupla contagem", title_suffix,
                "Fonte: allocation_by_scenario.csv. Alocação ótima por região no motor v3 (caminhos mínimos sucessivos), "
                "rateada a países pela demanda do estudo de mercado. Um único SKU modelado (AlgaPrime DHA P3).")
    ax = fig.add_axes([0.05, 0.08, 0.90, 0.76])
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 1.08)
    ax.axis("off")
    gap = 0.012
    cols = [a.groupby("site").allocated_t.sum(), pd.Series({"AlgaPrime DHA P3": total}),
            a.groupby("country").allocated_t.sum().sort_values(ascending=False),
            a.groupby("application").allocated_t.sum().sort_values(ascending=False)]
    pos = []
    for k, s in enumerate(cols):
        avail = 1 - gap * (len(s) - 1)
        y = 1.0
        d = {}
        for name, v in s.items():
            h = v / total * avail
            d[name] = [y - h, y]
            y -= h + gap
        pos.append(d)
    x = [0.25, 1.35, 2.45, 3.55]
    w = 0.08
    for k, d in enumerate(pos):
        for name, (lo, hi) in d.items():
            col = SITE_COLOR.get(name, VIOLET if k == 1 else SILVER)
            ax.add_patch(plt.Rectangle((x[k] - w / 2, lo), w, hi - lo, color=col))
            lab = SITE_LABEL.get(name, NICHE.get(name, name))
            ax.text(x[k] + (w / 2 + 0.03 if k < 3 else -w / 2 - 0.03), (lo + hi) / 2,
                    f"{lab}  {cols[k][name]:,.0f} t".replace(",", "."), va="center",
                    ha="left" if k < 3 else "right", fontsize=10, color=INK)
    cursor = {k: {n: v[1] for n, v in d.items()} for k, d in enumerate(pos)}
    for site, v in cols[0].items():
        h = v / total * (1 - gap * (len(cols[0]) - 1))
        t0 = cursor[0][site]
        t1 = cursor[1]["AlgaPrime DHA P3"]
        _band(ax, x[0] + w / 2, t0, t0 - h, x[1] - w / 2, t1, t1 - h, SITE_COLOR.get(site, SILVER))
        cursor[0][site] -= h
        cursor[1]["AlgaPrime DHA P3"] -= h
    sc = a.groupby(["site", "country"]).allocated_t.sum()
    sku_cursor = pos[1]["AlgaPrime DHA P3"][1]
    for (site, c), v in sc.items():
        h = v / total * (1 - gap * (len(cols[1]) - 1))
        h2 = v / total * (1 - gap * (len(cols[2]) - 1))
        t2 = cursor[2][c]
        _band(ax, x[1] + w / 2, sku_cursor, sku_cursor - h, x[2] - w / 2, t2, t2 - h2, SITE_COLOR.get(site, SILVER), 0.35)
        sku_cursor -= h
        cursor[2][c] -= h2
    ca = a.groupby(["country", "application"]).allocated_t.sum()
    c_cur = {n: v[1] for n, v in pos[2].items()}
    for (c, app), v in ca.items():
        h2 = v / total * (1 - gap * (len(cols[2]) - 1))
        h3 = v / total * (1 - gap * (len(cols[3]) - 1))
        t3 = cursor[3][app]
        _band(ax, x[2] + w / 2, c_cur[c], c_cur[c] - h2, x[3] - w / 2, t3, t3 - h3, SILVER, 0.30)
        c_cur[c] -= h2
        cursor[3][app] -= h3
    for k, t in enumerate(["Planta", "SKU", "País de formulação", "Aplicação"]):
        ax.text(x[k], 1.06, t, ha="center", fontsize=12, color=INK2)
    save(fig, path)


def frontier(fr: pd.DataFrame, capex: float, path: Path):
    s = fr[fr.capex_ori_musd == capex]
    piv = s.pivot(index="asia_contracted_t", columns="net_price_usd_kg_dha", values="delta_B_vs_A")
    fig = slide("Fronteira: quando a 2ª planta (Tailândia) se paga frente a só expandir Orindiúva",
                "ΔVPL (B Orindiúva + Nakhon Sawan − A Orindiúva), US$ mi, sobre a demanda-base do estudo de mercado + volume "
                "asiático contratado firme",
                "Fonte: break_even_frontiers.csv. Capex de Orindiúva se cancela nesta diferença (está nas duas políticas). "
                "Linha branca = ΔVPL 0. Preço = preço-base de mercado × multiplicador.")
    ax = fig.add_axes([0.08, 0.13, 0.70, 0.68])
    m = np.nanmax(np.abs(piv.values))
    im = ax.imshow(piv.values, origin="lower", aspect="auto",
                   cmap=LinearSegmentedColormap.from_list("d", [BLUE, "#3a3550", MAGENTA]), norm=TwoSlopeNorm(0, -m, m),
                   extent=[piv.columns.min(), piv.columns.max(), piv.index.min() / 1000, piv.index.max() / 1000])
    X, Y = np.meshgrid(piv.columns.values, piv.index.values / 1000)
    cs = ax.contour(X, Y, piv.values, levels=[0], colors=INK, linewidths=2.5)
    ax.clabel(cs, fmt={0: "ΔVPL = 0"}, fontsize=11)
    ax.set_xlabel("Preço líquido (US$/kg DHA)")
    ax.set_ylabel("Volume asiático contratado (mil t SKU/ano, desde 2029)")
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cb.set_label("ΔVPL B − A (US$ mi)", color=INK2)
    fig.text(0.80, 0.70, "Magenta: 2ª planta\nagrega valor", fontsize=12)
    fig.text(0.80, 0.58, "Azul: só Orindiúva", fontsize=12)
    save(fig, path)


def decision_surface(fr: pd.DataFrame, path: Path):
    caps = sorted(fr.capex_ori_musd.unique())
    fig = slide("Superfície de decisão com o capex de Orindiúva",
                "ΔVPL (Nakhon Sawan como única planta − Orindiúva), US$ mi, por volume asiático contratado × preço, em três "
                "níveis de capex de Orindiúva",
                "Fonte: break_even_frontiers.csv (delta_THalone_vs_A). Linha branca = indiferença. Capex de Orindiúva base do "
                "modelo ≈ US$ 92 mi (premissa modular; €50 mi divulgados sem capacidade).")
    m = np.nanmax(np.abs(fr.delta_THalone_vs_A))
    for k, c in enumerate(caps):
        s = fr[fr.capex_ori_musd == c]
        piv = s.pivot(index="asia_contracted_t", columns="net_price_usd_kg_dha", values="delta_THalone_vs_A")
        ax = fig.add_axes([0.06 + k * 0.31, 0.14, 0.26, 0.64])
        ax.imshow(piv.values, origin="lower", aspect="auto",
                  cmap=LinearSegmentedColormap.from_list("d", [BLUE, "#3a3550", MAGENTA]), norm=TwoSlopeNorm(0, -m, m),
                  extent=[piv.columns.min(), piv.columns.max(), piv.index.min() / 1000, piv.index.max() / 1000])
        X, Y = np.meshgrid(piv.columns.values, piv.index.values / 1000)
        if np.nanmin(piv.values) < 0 < np.nanmax(piv.values):
            ax.contour(X, Y, piv.values, levels=[0], colors=INK, linewidths=2)
        ax.set_title(f"Capex Orindiúva US$ {c:.0f} mi", color=INK, fontsize=13, loc="left")
        ax.set_xlabel("US$/kg DHA")
        if k == 0:
            ax.set_ylabel("Ásia contratada (mil t/ano)")
    save(fig, path)


def npv_waterfall(comp: pd.DataFrame, path: Path):
    fig = slide("Ponte de VPL entre políticas", "US$ mi, nominal, com valor terminal; demanda do estudo de mercado",
                "Fonte: investment_policy_comparison.csv. Cada degrau é a diferença entre duas políticas, não um componente "
                "aditivo. Cenário alto = todas as premissas de mercado favoráveis (não é 'provável').")
    steps = [("A_ORI_1", "A Orindiúva\n1 módulo"), ("A_ORI_2_STAGED", "+2º módulo\nse ≥80%"),
             ("C_ORI_TH_TRIG_UTIL", "2ª planta TH\nse ≥80%"), ("B_ORI_TH_NOW", "TH já\n(B)")]
    for k, sc in enumerate(("base", "high")):
        c = comp[comp.market_scenario == sc].set_index("policy")["npv_musd"]
        ax = fig.add_axes([0.07 + k * 0.48, 0.15, 0.40, 0.64])
        run = 0.0
        for i, (key, lab) in enumerate(steps):
            v = c[key]
            if i == 0:
                ax.bar(i, v, color="none", edgecolor=INK, linewidth=1.5, width=0.6)
                ax.text(i, max(v, 0) + abs(c).max() * 0.03, f"{v:,.0f}".replace(",", "."), ha="center", fontsize=11)
            else:
                d = v - run
                ax.bar(i, d, bottom=run, color=MAGENTA if d > 0 else BLUE, width=0.6, edgecolor=SURFACE)
                ax.text(i, max(run, v) + abs(c).max() * 0.03, f"{d:+,.0f}".replace(",", "."), ha="center", fontsize=11)
            run = v
        ax.bar(len(steps), c["WAIT"], color="none", edgecolor=MUTED, width=0.6, linestyle=":")
        ax.text(len(steps), abs(c).max() * 0.03, "Esperar\n0", ha="center", fontsize=10, color=MUTED)
        ax.axhline(0, color=MUTED, linewidth=1)
        ax.set_xticks(range(len(steps) + 1), [lab for _, lab in steps] + [""], fontsize=10)
        lo, hi = min(0, c.min()), max(0, c.max())
        ax.set_ylim(lo - 0.12 * (hi - lo), hi + 0.15 * (hi - lo))
        ax.set_title(f"Mercado {'base' if sc == 'base' else 'alto'}", color=INK, loc="left", fontsize=14, pad=14)
        _grid(ax, "y")
    save(fig, path)


def portfolio_layers(compo: pd.DataFrame, alloc: pd.DataFrame, comp_flows: pd.DataFrame, path: Path):
    fig = slide("Carteira × capacidade ao longo dos anos",
                "t SKU/ano vendidas por status da demanda (firme / pipeline qualificado / potencial) e capacidade efetiva",
                "Fonte: allocation_by_scenario.csv, project_cashflows.csv. Firme = 0: não há contrato público. Pipeline e "
                "potencial ponderados pelos pesos v3 (A110/A111).")
    for k, (sc, pol) in enumerate((("base", "A_ORI_1"), ("high", "B_ORI_TH_NOW"))):
        g = alloc[(alloc.market_scenario == sc) & (alloc.policy == pol)]
        f = comp_flows[(comp_flows.market_scenario == sc) & (comp_flows.policy == pol)].set_index("year")
        ys = sorted(f.index)
        ax = fig.add_axes([0.07 + k * 0.48, 0.15, 0.40, 0.64])
        bottom = np.zeros(len(ys))
        for st, col, lab in (("contracted", BLUE, "firme"), ("qualified_pipeline", VIOLET, "pipeline qualificado"),
                             ("unqualified_potential", SILVER, "potencial não qualificado")):
            v = np.array([g[(g.year == y) & (g.status == st)].allocated_t.sum() for y in ys])
            ax.bar(ys, v, bottom=bottom, color=col, edgecolor=SURFACE, linewidth=1.5, label=lab)
            bottom += v
        ax.plot(ys, f.capacity_t.values, color=MAGENTA, linewidth=2.2, label="capacidade efetiva")
        ax.set_title(f"Mercado {sc} · política {pol}", color=INK, loc="left", fontsize=13)
        ax.legend(frameon=False, fontsize=9.5, loc="upper left")
        _grid(ax, "y")
    save(fig, path)


def route_map(routes: pd.DataFrame, feed: pd.DataFrame, sites: pd.DataFrame, path: Path):
    import geopandas as gpd
    world = gpd.read_file(next((ROOT.parent / "assets" / "geo").glob("*.geojson")))
    fig = slide("Rotas: custo e tempo de entrega a partir de Orindiúva e Nakhon Sawan",
                "Rótulo = frete (US$/t SKU) e trânsito (dias) em 2030; espessura ∝ volume capturável do mercado (base)",
                "Fonte: route_economics.csv (fretes v3 freight_lanes.csv: cotações indicativas, não firmes).")
    ax = fig.add_axes([0.03, 0.07, 0.94, 0.78])
    world.plot(ax=ax, color="#FFFFFF", alpha=0.10, edgecolor="#FFFFFF", linewidth=0.3)
    pos = feed.set_index("country")[["lat", "lon"]]
    st = sites.set_index("site_id")
    r = routes[(routes.year == 2030) & routes.origin_site.isin(["BR_ORI_EXP", "TH_NSN"])]
    vmax = r.market_som_sku_t.max()
    for _, x in r.iterrows():
        if x.dest_country not in pos.index:
            continue
        o = st.loc[x.origin_site]
        d = pos.loc[x.dest_country]
        ax.plot([o.lon, d.lon], [o.lat, d.lat], color=SITE_COLOR[x.origin_site], alpha=0.5,
                linewidth=0.6 + 4 * x.market_som_sku_t / vmax)
    for s in ("BR_ORI_EXP", "TH_NSN"):
        o = st.loc[s]
        ax.scatter(o.lon, o.lat, marker="D", s=120, color=SITE_COLOR[s], edgecolor=INK, zorder=5)
        ax.text(o.lon + 2, o.lat - 5, SITE_LABEL[s], fontsize=11)
    lab = r.groupby(["dest_country"]).apply(lambda g: " | ".join(
        f"{'BR' if s == 'BR_ORI_EXP' else 'TH'} {v.freight_usd_t:,.0f}$/{v.transit_days:.0f}d"
        for s, v in g.set_index("origin_site").iterrows()))
    for c, txt in lab.items():
        if c in pos.index:
            ax.text(pos.loc[c].lon + 2, pos.loc[c].lat + 2, f"{c}\n{txt}", fontsize=8.5, color=INK)
    ax.set_xlim(-130, 160)
    ax.set_ylim(-55, 75)
    ax.axis("off")
    save(fig, path)


def concept_slides(out: Path, ue: pd.DataFrame, gates: pd.DataFrame, mkt: pd.DataFrame, comp: pd.DataFrame,
                   thresholds: dict, voi: pd.DataFrame):
    # 1. Where to produce
    fig = slide("Onde produzir", "Custo pleno por kg de DHA a 100% do módulo (v3) e situação dos gates de cada site",
                "Fonte: v3 unit_economics.csv e site_gates.csv. Premissas de capex, rendimento e utilidades; nenhum gate "
                "verificado em campo. Utilização real (demanda) muda o custo efetivo: ver 'O que muda a decisão'.")
    ax = fig.add_axes([0.25, 0.18, 0.45, 0.60])
    u = ue.set_index("site_id").loc[["BR_ORI_EXP", "BR_GF_GO", "TH_NSN", "TH_RYG"]]
    y = np.arange(len(u))[::-1]
    ax.barh(y, u.full_cost_usd_per_kg_dha, color=[SITE_COLOR[s] for s in u.index], height=0.55)
    for yi, v in zip(y, u.full_cost_usd_per_kg_dha):
        ax.text(v + 0.3, yi, f"US$ {v:.1f}".replace(".", ","), va="center", fontsize=12)
    ax.set_yticks(y, [SITE_LABEL[s] for s in u.index], color=INK)
    ax.set_xlabel("US$/kg DHA")
    _grid(ax)
    g = gates.groupby("site_id").status.value_counts().unstack(fill_value=0)
    for yi, s in zip(y, u.index):
        row = g.loc[s]
        fig.text(0.74, 0.18 + (yi + 0.5) / len(u) * 0.60 - 0.01,
                 f"PASS {row.get('PASS', 0)} · REVIEW {row.get('REVIEW', 0)} · NÃO VERIF. {row.get('NOT_VERIFIED', 0)}",
                 fontsize=11, color=INK2)
    save(fig, out / "concept_1_where_to_produce.png")
    # 2. Where to sell
    fig = slide("Onde vender", "Volume incremental capturável em 2030 (t SKU) e margem de contribuição por mercado (base)",
                "Fonte: estudo de mercado (market_rankings.csv). Salmão Noruega/Chile concentram o volume; camarão, China e "
                "pet têm TAM grande mas SAM pequeno. Nenhum contrato público.")
    ax = fig.add_axes([0.25, 0.14, 0.60, 0.66])
    m = mkt.sort_values("incremental_sku_2030_t")
    lab = m.country + " · " + m.application.map(NICHE)
    ax.barh(lab, m.incremental_sku_2030_t, color=[BLUE if g == "consolidation" else MAGENTA for g in m.group], height=0.6)
    for yi, (v, mg) in enumerate(zip(m.incremental_sku_2030_t, m.unit_contribution_usd_kg_dha)):
        ax.text(v + 20, yi, f"{v:,.0f} t · US$ {mg:.1f}/kg".replace(",", "."), va="center", fontsize=10)
    ax.tick_params(axis="y", colors=INK)
    ax.set_xlabel("t SKU/ano incrementais (2030)")
    _grid(ax)
    fig.text(0.70, 0.30, "Azul = uso documentado (consolidar)\nMagenta = só potencial (expandir)", fontsize=11, color=INK2)
    save(fig, out / "concept_2_where_to_sell.png")
    # 3. What changes the decision
    fig = slide("O que muda a decisão", "Gatilhos físicos e monetários (estudo integrado) e informações que mais mudam a "
                "política ótima", "Fonte: investment_policy_comparison.csv, break_even_frontiers.csv, diligence_priority.csv. "
                "Valores condicionais às premissas; não são previsões da Corbion.")
    c = comp.set_index(["market_scenario", "policy"]).npv_musd
    n = lambda v: f"{v:,.0f}".replace(",", ".")  # noqa: E731
    hi = comp[comp.market_scenario == "high"].sort_values("npv_musd").iloc[-1]
    lines = [
        f"Hoje (mercado base, sem contratos): melhor = ESPERAR; Orindiúva 1 módulo VPL US$ {n(c[('base', 'A_ORI_1')])} mi",
        f"Orindiúva se paga com ≥ {n(thresholds['A_firm_t'])} t/ano contratadas firmes (sem pipeline)",
        (f"Tailândia (B) supera só-Orindiúva com ≥ {n(thresholds['B_asia_t'])} t/ano asiáticas contratadas (com pipeline base)"
         if thresholds["B_asia_t"] else "Tailândia (B) não supera só-Orindiúva até 40 mil t/ano asiáticas no preço-base"),
        f"Mercado alto: melhor = {hi.label} (VPL US$ {n(hi.npv_musd)} mi)",
        "", "Informações que mais mudam a decisão:"]
    eff = {"low": "baixo", "medium": "médio", "high": "alto"}
    lines += [f"  • {x.label} ({'muda a política' if x.decision_changes else 'não muda a política'}; esforço {eff[x.effort]})"
              for x in voi.head(5).itertuples()]
    for i, t in enumerate(lines):
        fig.text(0.06, 0.78 - i * 0.055, t, fontsize=15 if i < 4 else 13.5,
                 color=INK if i < 4 else INK2, fontweight="bold" if i < 4 else "normal")
    save(fig, out / "concept_3_what_changes_the_decision.png")
