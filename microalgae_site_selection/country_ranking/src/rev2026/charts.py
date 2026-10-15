"""16:9 slides of the 2026-10-15 revision (deck style of src/charts.py).

Palette validated with the dataviz validator on the dark surface #0B0630 (all six checks pass):
blue #3987e5, magenta #d55181, violet #9085e9, teal #16a08f, amber #c4862a.
Observed vs scenario is never colour-only: scenario marks are hollow/hatched AND carry a text tag.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle

from .. import charts as C
from .common import OUT

BLUE, MAGENTA, VIOLET, TEAL, AMBER = "#3987e5", "#d55181", "#9085e9", "#16a08f", "#c4862a"
CRIT_COL = [BLUE, MAGENTA, VIOLET, TEAL, AMBER]
STATUS_COL = {"OBSERVED": BLUE, "DERIVED": VIOLET, "JUDGMENT": AMBER, "ASSUMPTION": MAGENTA, "UNKNOWN": "#4a4560"}
SITE_SHORT = {"BR_ORI_EXP": "Orindiúva (expansão)", "BR_GF_GO": "Greenfield BR (GO)", "TH_NSN": "Nakhon Sawan",
              "TH_RYG": "Rayong"}
NICHE_PT = {"salmon": "Salmão", "shrimp": "Camarão", "pet": "Pet food", "todos": "Todos os nichos"}
SCEN_SHORT = {"R1_renova_menor": "R1 menor", "R2_renova_igual": "R2 igual", "R3_renova_maior": "R3 maior",
              "R4_perda_parcial": "R4 perda", "R5_take_or_pay": "R5 take-or-pay", "R6_ancora_nova": "R6 âncora"}


def pt(c):
    return C.PT.get(c, c)


def f1(x, d=1):
    return C.fmt(x, d)


def interval_rows(ax, t: pd.DataFrame, labels: list[str], color=BLUE, show_cov=True, fs=12):
    y = np.arange(len(t))[::-1]
    for yi, (e, r) in zip(y, t.iterrows()):
        ax.add_patch(Rectangle((0, yi - 0.28), r.floor, 0.56, color=color, lw=0))
        ax.add_patch(Rectangle((r.floor, yi - 0.28), r.ceiling - r.floor, 0.56, fill=False, ec=color, lw=1.2,
                               hatch="///", alpha=0.9))
        ax.text(r.ceiling + 0.12, yi, f"{f1(r.floor)}–{f1(r.ceiling)}", va="center", fontsize=fs - 1.5,
                color=C.INK2)
        if show_cov:
            ax.text(10.4, yi, f"{r.verified_weight + r.judgment_weight:.0%}", va="center", ha="left",
                    fontsize=fs - 1.5, color=C.INK2)
            ax.text(11.9, yi, f"{int(r.rank_best)}–{int(r.rank_worst)}", va="center", ha="left",
                    fontsize=fs - 1.5, color=C.INK2)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=fs)
    ax.set_xlim(0, 13.2)
    ax.set_ylim(-0.7, len(t) - 0.3)
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.grid(axis="x", color=C.GRID, lw=0.6)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)


def decision_panel(site, mkt, econ, path):
    fig = C.slide("Ranking público × retorno incremental: lados diferentes da decisão",
                  "Esquerda: dados públicos (sólido = piso garantido; hachura = o que dados ausentes podem somar). "
                  "Direita: VPL incremental por cenário de renovação de dez/2026.",
                  "Base 2026, US$ nominais; WACC país (v3). Escala 0-10 com pisos/tetos fixos (goalposts_table.csv). "
                  "Direita = ASSUMPTION (premissas v3: capex, rendimento, OEE, preço, demanda) – com dados públicos "
                  "o VPL/TIR é 'não estimável'. Fontes: source_registry.csv; economics_by_site_niche_scenario.csv.")
    t = site["table"]
    ax = fig.add_axes([0.13, 0.52, 0.33, 0.30])
    interval_rows(ax, t, [SITE_SHORT[e] for e in t.index])
    ax.set_title("Sites – score público (0-10)", loc="left", fontsize=14, color=C.INK, pad=22)
    ax.text(10.4, len(t) - 0.15, "cobert.", fontsize=9, color=C.MUTED, transform=ax.transData)
    ax.text(11.9, len(t) - 0.15, "posição", fontsize=9, color=C.MUTED, transform=ax.transData)
    # markets: top 3 per niche by floor
    rows = []
    for n in ("salmon", "shrimp", "pet"):
        tt = mkt["niches"][n]["table"].head(3)
        rows.append(tt)
    mt = pd.concat(rows)
    ax2 = fig.add_axes([0.13, 0.10, 0.33, 0.36])
    labs = [f"{NICHE_PT[r.niche]} · {pt(r.country)}" + ("  (C)" if r.role == "consolidação" else "")
            for r in mt.itertuples()]
    interval_rows(ax2, mt, labs, color=VIOLET, fs=11)
    ax2.set_title("Mercados – 3 melhores por nicho ((C) = adoção histórica documentada)", loc="left",
                  fontsize=13, color=C.INK, pad=8)
    # right: NPV by site × renewal scenario
    g = econ["grid"]
    gg = g[(g.niche == "todos") & (g.renewal_scenario != "R0_base")]
    ax3 = fig.add_axes([0.58, 0.40, 0.38, 0.37])
    sites = list(t.index)
    keys = {v: k for k, v in econ_site_of(econ).items()}
    marker = {"R1_renova_menor": "v", "R4_perda_parcial": "P", "R2_renova_igual": "o", "R5_take_or_pay": "s",
              "R6_ancora_nova": "D", "R3_renova_maior": "^"}
    for i, s in enumerate(sites):
        yi = len(sites) - 1 - i
        d = gg[gg.site == s]
        ax3.plot([d.npv_musd.min(), d.npv_musd.max()], [yi, yi], color=C.MUTED, lw=1.5, zorder=1)
        for r in d.itertuples():
            ax3.scatter(r.npv_musd, yi, marker=marker[r.renewal_scenario], s=60, facecolor="none"
                        if r.renewal_scenario != "R2_renova_igual" else MAGENTA, edgecolor=MAGENTA, lw=1.4, zorder=3)
        r2 = d[d.renewal_scenario == "R2_renova_igual"].iloc[0]
        irr = f"TIR {r2.irr:.0%}" if pd.notna(r2.irr) else "TIR n/d"
        ax3.text(d.npv_musd.max() + 8, yi, f"R2: {f1(r2.npv_musd, 0)} · {irr} · VT {r2.tv_share_of_npv:.0%} do VPL",
                 va="center", fontsize=10, color=C.INK2)
    ax3.axvline(0, color=C.INK, lw=1)
    ax3.set_yticks(range(len(sites))[::-1])
    ax3.set_yticklabels([SITE_SHORT[s] for s in sites], fontsize=12)
    ax3.set_xlabel("VPL incremental (US$ mi)")
    ax3.set_xlim(gg.npv_musd.min() - 20, gg.npv_musd.max() + 190)
    ax3.grid(axis="x", color=C.GRID, lw=0.6)
    ax3.spines["left"].set_visible(False)
    ax3.tick_params(axis="y", length=0)
    ax3.set_title("Sites – VPL por cenário [ASSUMPTION]; só com dados públicos: não estimável", loc="left",
                  fontsize=13, color=C.INK, pad=22)
    hs = [plt.Line2D([], [], marker=marker[k], ls="", mec=MAGENTA, mfc=MAGENTA if k == "R2_renova_igual" else "none",
                     label=SCEN_SHORT[k]) for k in marker]
    ax3.legend(handles=hs, ncol=6, fontsize=9, frameon=False, loc="upper left", bbox_to_anchor=(0, 1.09),
               labelcolor=C.INK2, handletextpad=0.2, columnspacing=0.8)
    # right bottom: niche-only NPV under R2
    ax4 = fig.add_axes([0.58, 0.13, 0.38, 0.17])
    gn = g[(g.renewal_scenario == "R2_renova_igual") & (g.niche.isin(["salmon", "shrimp", "pet"]))]
    w = 0.25
    for j, n in enumerate(["salmon", "shrimp", "pet"]):
        d = gn[gn.niche == n].set_index("site").reindex(sites)
        x = np.arange(len(sites)) + (j - 1) * w
        ax4.bar(x, d.npv_musd, width=w * 0.9, color=[BLUE, TEAL, AMBER][j], label=NICHE_PT[n])
    ax4.axhline(0, color=C.INK, lw=1)
    ax4.set_xticks(range(len(sites)))
    ax4.set_xticklabels([SITE_SHORT[s] for s in sites], fontsize=10)
    ax4.set_ylabel("US$ mi", fontsize=10)
    ax4.legend(ncol=3, fontsize=9, frameon=False, loc="lower left", bbox_to_anchor=(0, -0.42), labelcolor=C.INK2)
    ax4.set_title("Um nicho sozinho (R2): nenhum enche um módulo de 10 kt  [ASSUMPTION]", loc="left", fontsize=12,
                  color=C.INK)
    ax4.grid(axis="y", color=C.GRID, lw=0.6)
    C.save(fig, path)


def econ_site_of(econ):
    g = econ["grid"]
    return dict(zip(g.alternative, g.site))


def bridge_chart(econ, path):
    b = econ["bridge"]
    fig = C.slide("Da capacidade técnica ao VPL: onde estão as lacunas",
                  "Planta atual (cinza = não divulgado) e novo módulo em Orindiúva no cenário R2 (renovação igual). "
                  "Cada passo leva sua etiqueta de evidência.",
                  "Fontes: LO CETESB 51001996 via brief (L1); transcrições H1 2026 (L2); demais valores = premissas v3 "
                  "(ASSUMPTION, assumptions.csv A009/A012/A110/A111). Unidade: t SKU (AlgaPrime DHA P3 ≈ 35-36% DHA). "
                  "capacity_to_npv_bridge.csv.")
    col = {"UNKNOWN": "#4a4560", "ASSUMPTION": MAGENTA, "L1 brief": VIOLET, "OBSERVED (declaração)": BLUE}
    import textwrap
    n = len(b)
    ax = fig.add_axes([0.04, 0.07, 0.92, 0.74])
    ax.set_xlim(0, 4)
    ax.set_ylim(-0.08, 3.25)
    ax.axis("off")
    for i, r in enumerate(b.itertuples()):
        cx, cy = (i % 4), 2.2 - (i // 4) * 1.1
        c = col.get(r.status, VIOLET)
        hollow = r.status in ("ASSUMPTION", "UNKNOWN")
        ax.add_patch(FancyBboxPatch((cx + 0.05, cy), 0.86, 0.92, boxstyle="round,pad=0.01,rounding_size=0.04",
                                    fc="none" if hollow else c, ec=c, lw=2, alpha=0.95))
        if r.status == "ASSUMPTION":
            ax.add_patch(Rectangle((cx + 0.05, cy + 0.86), 0.86, 0.06, fc=c, ec="none", hatch=None))
        ax.text(cx + 0.09, cy + 0.80, textwrap.fill(f"{i + 1}. {r.step}", 34), fontsize=10.5, color=C.INK, va="top")
        val = str(r.value)
        ax.text(cx + 0.09, cy + 0.42, textwrap.fill(val, 26), fontsize=17 if len(val) < 16 else 11.5,
                fontweight="bold", color=C.INK, va="center")
        ax.text(cx + 0.09, cy + 0.06, textwrap.fill(f"[{r.status}] {r.note}", 44), fontsize=8.5, color=C.INK2,
                va="bottom")
        if i % 4 != 3 and i < n - 1:
            ax.annotate("", xy=(cx + 1.05, cy + 0.45), xytext=(cx + 0.92, cy + 0.45),
                        arrowprops=dict(arrowstyle="->", color=C.MUTED, lw=1.5))
    hs = [Patch(fc=BLUE, label="Declaração observada"), Patch(fc=VIOLET, label="Brief (documento não lido aqui)"),
          Patch(fc="none", ec=MAGENTA, lw=2, label="ASSUMPTION (faixa magenta)"),
          Patch(fc="none", ec="#4a4560", lw=2, label="UNKNOWN")]
    fig.legend(handles=hs, loc="upper left", bbox_to_anchor=(0.04, 0.865), ncol=4, frameon=False, fontsize=10,
               labelcolor=C.INK2)
    C.save(fig, path)


STAGE_COL = {"current_purchase": BLUE, "historical_adoption": TEAL, "trial": VIOLET, "channel_only": AMBER,
             "registration_only": MAGENTA, "none_found": "#4a4560", "unknown": "#4a4560"}
STAGE_PT = {"current_purchase": "compra atual", "historical_adoption": "adoção histórica", "trial": "teste",
            "channel_only": "só canal/JV", "registration_only": "só registro", "none_found": "nenhuma evidência",
            "unknown": "desconhecido"}


def evidence_matrix(mkt, path):
    acc = mkt["accounts"]
    fig = C.slide("Mercado × nicho × fábricas/clientes × estágio de evidência",
                  "O que existe de prova comercial por país e nicho, separado do tamanho técnico (TAM). "
                  "Nenhuma compra 2026 está documentada publicamente.",
                  "TAM técnico = ração × g DHA/kg (t DHA/ano, 2024-25) – não é SAM nem SOM. Estágio = melhor evidência "
                  "pública por conta (customer_factory_matrix.csv). Capacidade = nominal de ração (prospecto BioMar via "
                  "brief, L1) – não é compra de AlgaPrime. Gate = registro do SKU para o uso no país.")
    rows = []
    for n in ("salmon", "shrimp", "pet"):
        t = mkt["niches"][n]["table"].sort_values("tam_tech_dha_t", ascending=False).head(6)
        for e, r in t.iterrows():
            a = acc[(acc.country == r.country) & ((acc.niche == n) | (acc.niche == "all"))]
            best = a.assign(s=a.evidence_score.fillna(-1)).sort_values("s").iloc[-1] if len(a) else None
            names = "; ".join(f"{x.customer.split(' (')[0]}" + (f" {x.plant}" if x.entity_level == "fábrica" else "")
                              for x in a.itertuples())[:70]
            cap = a.feed_capacity_t.sum() if len(a) else np.nan
            rows.append(dict(niche=n, country=r.country, tam=r.tam_tech_dha_t, names=names or "—",
                             stage=best.evidence_stage if best is not None else "none_found",
                             cap=cap, gate=r.sku_gate))
    d = pd.DataFrame(rows)
    ax = fig.add_axes([0.04, 0.09, 0.92, 0.76])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, len(d) + 1.2)
    ax.axis("off")
    heads = [(0, "Nicho · país"), (17, "TAM técnico (t DHA)"), (40, "Contas/fábricas identificadas"),
             (72, "Estágio de evidência"), (87, "Ração (kt)"), (94, "Gate SKU")]
    for x, h in heads:
        ax.text(x, len(d) + 0.6, h, fontsize=11, color=C.MUTED, fontweight="bold")
    tmax = d.tam.max()
    for i, r in enumerate(d.itertuples()):
        y = len(d) - i - 0.2
        if i and d.niche.iloc[i - 1] != r.niche:
            ax.plot([0, 100], [y + 0.55, y + 0.55], color=C.GRID, lw=0.8)
        ax.text(0, y, f"{NICHE_PT[r.niche]} · {pt(r.country)}", fontsize=11, va="center")
        if pd.notna(r.tam):
            ax.add_patch(Rectangle((17, y - 0.3), 18 * r.tam / tmax, 0.6, color=VIOLET, lw=0))
            ax.text(17.3 + 18 * r.tam / tmax, y, f"{r.tam:,.0f}".replace(",", "."), fontsize=9.5, va="center",
                    color=C.INK2)
        ax.text(40, y, r.names[:62], fontsize=9.5, va="center", color=C.INK2)
        c = STAGE_COL.get(r.stage, "#4a4560")
        ax.add_patch(FancyBboxPatch((72, y - 0.3), 13.5, 0.6, boxstyle="round,pad=0,rounding_size=0.2", fc=c,
                                    ec="none"))
        ax.text(78.75, y, STAGE_PT.get(r.stage, r.stage), fontsize=9.5, va="center", ha="center", color=C.INK)
        ax.text(87, y, "—" if pd.isna(r.cap) or r.cap == 0 else f"{r.cap / 1000:,.0f}".replace(",", "."),
                fontsize=10, va="center", color=C.INK2)
        ax.text(94, y, r.gate, fontsize=10, va="center", color=C.INK2)
    C.save(fig, path)


def faceoff(site, econ, path):
    t = site["table"]
    ev = site["evidence"].set_index(["entity", "metric_id"])
    g = econ["grid"]
    r2 = g[(g.renewal_scenario == "R2_renova_igual") & (g.niche == "todos")].set_index("site")
    sites = ["BR_ORI_EXP", "TH_NSN", "TH_RYG", "BR_GF_GO"]
    fig = C.slide("Confronto Brasil × Tailândia: o que se sabe e o que falta",
                  "Linhas com etiqueta de evidência; 'não público' indica dado que só a Corbion/parceiros têm.",
                  "Açúcar: CEPEA/MAPA VHP SP 2026 e preço ex-fábrica TH 2024 (L2). Água: Aqueduct 3.0 + Corbion AR "
                  "2025 (conflito em Orindiúva). Prazo: rota marítima calculada (pesos fixos por nicho). Frete por destino "
                  "= v3 freight_lanes (parte cotação jan/2026, parte premissa). Volume âncora = volume vendido 2035 × "
                  "multiplicador de equilíbrio (ASSUMPTION).")
    tm = None
    try:
        import yaml
        from .. import plant as P
        tm = P.transit_matrix(yaml.safe_load(open(P.RAW / "ports.yaml")))
    except Exception:  # noqa: BLE001
        pass
    fr = pd.read_csv(OUT.parents[1].parent / "v3" / "data" / "raw" / "freight_lanes.csv")

    def cell(s, k, fmtf):
        try:
            r = ev.loc[(s, k)]
        except KeyError:
            return "—", "UNKNOWN"
        if r.status in ("UNKNOWN", "ASSUMPTION") or pd.isna(r.value):
            return "não público", r.status
        txt = fmtf(r.value)
        if pd.notna(r.value_low) and pd.notna(r.value_high) and r.value_low != r.value_high:
            txt += f" [{fmtf(r.value_low)}–{fmtf(r.value_high)}]"
        return txt, r.status

    def days(s, dest):
        if tm is None:
            return "—"
        c = "Brazil" if s.startswith("BR") else "Thailand"
        r = tm[(tm.origin == c) & (tm.market == dest)].iloc[0]
        adj = {"BR_ORI_EXP": 0.0, "BR_GF_GO": 0.6, "TH_NSN": 0.0, "TH_RYG": -0.8}[s]
        return f"{r.door_to_door_days + adj:.0f} d"

    def freight(s, region):
        c = "BR" if s.startswith("BR") else "TH"
        r = fr[(fr.origin_country == c) & (fr.region == region)].iloc[0]
        return f"US$ {r.usd_per_t:.0f}/t"

    lines = [
        ("Açúcar entregue (US$/t)", lambda s: cell(s, "ec_sugar_usd_t", lambda v: f"{v:.0f}")),
        ("Capex incremental (US$/kg·ano DHA)", lambda s: cell(s, "ec_capex_usd_per_kg_dha_yr", lambda v: f"{v:.0f}")),
        ("Estresse hídrico local (0-4)", lambda s: cell(s, "rs_basin_water_stress", lambda v: f"{v:.1f}".rstrip("0").rstrip(".").replace(".", ","))),
        ("Outorga de água incremental", lambda s: cell(s, "rs_water_grant_incremental", lambda v: f"{v:.0f}")),
        ("Meses FID → 1º DHA (julgamento)", lambda s: cell(s, "ex_months_to_first_dha", lambda v: f"{v:.0f}")),
        ("Prazo a Noruega / Vietnã / EUA", lambda s: (f"{days(s, 'Norway')} / {days(s, 'Vietnam')} / "
                                                      f"{days(s, 'United States')}", "DERIVED")),
        ("Frete salmão / camarão Ásia / pet", lambda s: (f"{freight(s, 'SALMON')} / {freight(s, 'SHRIMP_ASIA')} / "
                                                         f"{freight(s, 'PET')}", "ASSUMPTION")),
        ("Gates (pass / review / unknown)", lambda s: (f"{int(t.at[s, 'n_pass'])} / {int(t.at[s, 'n_review'])} / "
                                                       f"{int(t.at[s, 'n_unknown'])}", "OBSERVED")),
        ("Volume âncora p/ VPL=0 (t SKU/ano)", lambda s: (
            f"{r2.at[s, 'sold_2035_t'] * r2.at[s, 'breakeven_demand_multiplier']:,.0f}".replace(",", ".")
            if pd.notna(r2.at[s, "breakeven_demand_multiplier"]) else "n/d", "ASSUMPTION")),
        ("VPL R2 / TIR (US$ mi)", lambda s: (f"{f1(r2.at[s, 'npv_musd'], 0)} / {r2.at[s, 'irr']:.0%}"
                                             if pd.notna(r2.at[s, 'irr']) else f"{f1(r2.at[s, 'npv_musd'], 0)} / n/d",
                                             "ASSUMPTION")),
    ]
    ax = fig.add_axes([0.04, 0.10, 0.92, 0.74])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, len(lines) + 1.3)
    ax.axis("off")
    xs = [28, 46, 64, 82]
    for x, s in zip(xs, sites):
        ax.text(x, len(lines) + 0.7, SITE_SHORT[s], fontsize=13, fontweight="bold")
    tagc = {"OBSERVED": BLUE, "DERIVED": VIOLET, "JUDGMENT": AMBER, "ASSUMPTION": MAGENTA, "UNKNOWN": "#8a84a0"}
    for i, (lab, fn) in enumerate(lines):
        y = len(lines) - i - 0.1
        ax.text(0, y, lab, fontsize=11.5, va="center")
        ax.plot([0, 100], [y - 0.5, y - 0.5], color=C.GRID, lw=0.5)
        for x, s in zip(xs, sites):
            txt, st = fn(s)
            ax.text(x, y + 0.13, txt, fontsize=10.5, va="center", color=C.INK)
            ax.text(x, y - 0.25, st, fontsize=8, va="center", color=tagc.get(st, C.MUTED))
    C.save(fig, path)


def before_after(site, mkt, cfg, path):
    from .common import FROZEN
    fig = C.slide("Antes × depois: pesos, posições e peso de notas não documentadas",
                  "Mudar os pesos não 'melhora' o ranking: o que muda é o que conta como evidência e o que vira gate "
                  "ou fluxo de caixa.",
                  "Antes = rankings congelados de 14/10/2026 (outputs/frozen_2026-10-14). Depois = rev2026 com pesos "
                  "propostos (escolha estratégica). Posição nova = pelo piso garantido; faixa = melhor/pior completando "
                  "dados ausentes. old_vs_new_weights.csv; rubric_migration.csv.")
    # A: weights
    ax = fig.add_axes([0.04, 0.14, 0.24, 0.66])
    old_s = [0.30, 0.20, 0.15, 0.15, 0.20]
    new_s = [cfg["site"]["criteria"][k]["weight"] for k in ("economia", "acesso", "execucao", "resiliencia", "opcao")]
    labs_old = ["Economia de produção", "Acesso a mercados", "Prontidão Corbion", "Regulação/incentivos",
                "Risco estratégico"]
    labs_new = ["Economia da unidade", "Acesso econômico", "Execução Corbion", "Resiliência", "Opção de expansão"]
    for j, (vals, labs) in enumerate(((old_s, labs_old), (new_s, labs_new))):
        b = 0
        for k, (v, l) in enumerate(zip(vals, labs)):
            hatch = "//" if (j == 0 and k == 3) else None
            ax.bar(j, v, bottom=b, color=CRIT_COL[k], width=0.6, edgecolor=C.SURFACE, lw=2, hatch=hatch)
            ax.text(j, b + v / 2, f"{l}\n{v:.0%}", ha="center", va="center", fontsize=8.5, color=C.INK)
            b += v
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Site: antes", "Site: depois"], fontsize=11)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_title("Pesos (planta/site)", loc="left", fontsize=13, color=C.INK)
    ax.text(0, -0.08, "Regulação → gate + caixa", ha="center", fontsize=9, color=C.MUTED, transform=ax.transData)
    # B: positions
    ax2 = fig.add_axes([0.50, 0.14, 0.17, 0.66])
    old = pd.read_csv(FROZEN / "plant" / "plant_country_ranking.csv").set_index("country")
    t = site["table"]
    items = [("Brasil (país) → Orindiúva", old.at["Brazil", "rank"], "BR_ORI_EXP"),
             ("Tailândia (país) → Nakhon Sawan", old.at["Thailand", "rank"], "TH_NSN")]
    om = {}
    for n in ("salmon", "shrimp", "pet"):
        om[n] = pd.read_csv(FROZEN / "market" / f"market_ranking_{n}.csv").set_index("country")["rank"]
    for n, c in (("salmon", "Norway"), ("salmon", "Chile"), ("shrimp", "China"), ("shrimp", "Thailand"),
                 ("pet", "United States"), ("pet", "France")):
        items.append((f"{NICHE_PT[n]} · {pt(c)}", om[n].get(c, np.nan), f"{n}|{c}"))
    for i, (lab, o, e) in enumerate(items):
        y = len(items) - i
        tt = t if e in t.index else mkt["niches"][e.split("|")[0]]["table"]
        nf, nb, nw = tt.at[e, "rank_floor"], tt.at[e, "rank_best"], tt.at[e, "rank_worst"]
        ax2.plot([nb, nw], [y, y], color=VIOLET, lw=6, alpha=0.5, solid_capstyle="round")
        ax2.scatter([o], [y], marker="o", s=70, facecolor="none", edgecolor=C.INK, zorder=3)
        ax2.scatter([nf], [y], marker="o", s=70, color=VIOLET, zorder=4)
    ax2.set_xlim(0.3, 15.5)
    ax2.set_xticks([1, 5, 10, 15])
    ax2.set_ylim(0.3, len(items) + 0.8)
    ax2.invert_xaxis()
    ax2.set_yticks([len(items) - i for i in range(len(items))])
    ax2.set_yticklabels([it[0] for it in items], fontsize=9.5)
    ax2.tick_params(axis="y", length=0)
    ax2.spines["left"].set_visible(False)
    ax2.set_xlabel("posição (1 = melhor)")
    ax2.set_title("Posição: antes (vazio) × depois (cheio) e faixa", loc="right", fontsize=13, color=C.INK)
    ax2.grid(axis="x", color=C.GRID, lw=0.5)
    # C: undocumented share
    ax3 = fig.add_axes([0.72, 0.14, 0.24, 0.66])
    old_rub = float(old["rubric_share_of_weight"].iloc[0])
    new_j = float(t.judgment_weight.mean())
    new_u = float(t.unknown_weight.mean())
    bars = [("Antes: rubricas\nnão documentadas", old_rub, AMBER, None),
            ("Depois: julgamento\nexplícito", new_j, AMBER, None),
            ("Depois: peso\ndesconhecido (intervalo)", new_u, "#4a4560", "//")]
    for i, (l, v, c, h) in enumerate(bars):
        ax3.bar(i, v, color=c, width=0.6, hatch=h, edgecolor=C.SURFACE)
        ax3.text(i, v + 0.01, f"{v:.0%}", ha="center", fontsize=12, fontweight="bold")
    ax3.axhline(cfg["judgment_budget"], color=C.MUTED, ls="--", lw=1)
    ax3.text(2.45, cfg["judgment_budget"] + 0.01, "meta ≤ 10%", fontsize=9, color=C.MUTED, ha="right")
    ax3.set_xticks(range(3))
    ax3.set_xticklabels([b[0] for b in bars], fontsize=9)
    ax3.set_yticks([])
    ax3.spines["left"].set_visible(False)
    ax3.set_title("Peso sem documentação (sites)", loc="left", fontsize=13, color=C.INK)
    C.save(fig, path)


def niche_intervals(mkt, niche, path):
    t = mkt["niches"][niche]["table"]
    fig = C.slide(f"{NICHE_PT[niche]}: ranking público com cobertura e faixa de posição",
                  "Piso sólido = garantido pelos dados; hachura = máximo que dados ausentes podem somar. "
                  "Ordem pelo piso; faixa = melhor/pior posição possível.",
                  "Pesos 25/25/25/15/10 (escolha estratégica). 'Economia' (25%) sem preço público → aparece como intervalo. "
                  f"market_public_scores_{niche}.csv; market_evidence.csv. (C) = adoção histórica documentada (consolidação).")
    ax = fig.add_axes([0.20, 0.10, 0.62, 0.74])
    labs = [f"{pt(r.country)}" + ("  (C)" if r.role == "consolidação" else "") + f"  [{r.sku_gate}]"
            for r in t.itertuples()]
    interval_rows(ax, t, labs, color=VIOLET if niche != "pet" else BLUE)
    ax.text(10.4, len(t) - 0.15, "cobert.", fontsize=9, color=C.MUTED)
    ax.text(11.9, len(t) - 0.15, "posição", fontsize=9, color=C.MUTED)
    C.save(fig, path)


def site_intervals(site, path):
    t = site["table"]
    fig = C.slide("Sites: ranking público com cobertura e faixa de posição",
                  "Nenhuma posição está decidida só com dados públicos: capex, opex, frete entregue e outorgas são "
                  "desconhecidos.",
                  "Pesos 40/25/15/15/5 (escolha estratégica). Regulação = gate (todos 'review/unknown'). site_public_scores.csv.")
    ax = fig.add_axes([0.24, 0.30, 0.58, 0.50])
    interval_rows(ax, t, [f"{SITE_SHORT[e]}  [{t.at[e, 'gate_overall']}]" for e in t.index])
    ax.text(10.4, len(t) - 0.15, "cobert.", fontsize=9, color=C.MUTED)
    ax.text(11.9, len(t) - 0.15, "posição", fontsize=9, color=C.MUTED)
    # criterion floors/ceilings table
    crit = list(site["crit_w"])
    labels = {"economia": "Economia 40%", "acesso": "Acesso 25%", "execucao": "Execução 15%",
              "resiliencia": "Resiliência 15%", "opcao": "Opção 5%"}
    for j, c in enumerate(crit):
        fig.text(0.24 + j * 0.12, 0.22, labels[c], fontsize=11, color=C.MUTED)
        for i, e in enumerate(t.index):
            fig.text(0.24 + j * 0.12, 0.19 - i * 0.03,
                     f"{f1(t.at[e, c + '_floor'])}–{f1(t.at[e, c + '_ceiling'])}", fontsize=10.5, color=C.INK2)
    for i, e in enumerate(t.index):
        fig.text(0.05, 0.19 - i * 0.03, SITE_SHORT[e], fontsize=10.5)
    C.save(fig, path)


def all_charts(site, mkt, econ, cfg):
    C.setup()
    decision_panel(site, mkt, econ, OUT / "slide1_decision_panel.png")
    bridge_chart(econ, OUT / "slide2_capacity_to_npv_bridge.png")
    evidence_matrix(mkt, OUT / "slide3_market_evidence_matrix.png")
    faceoff(site, econ, OUT / "slide4_brazil_thailand_faceoff.png")
    before_after(site, mkt, cfg, OUT / "slide5_before_after_weights.png")
    site_intervals(site, OUT / "site_intervals.png")
    for n in ("salmon", "shrimp", "pet"):
        niche_intervals(mkt, n, OUT / f"market_intervals_{n}.png")
