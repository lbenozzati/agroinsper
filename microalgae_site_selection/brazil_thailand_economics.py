"""Unit economics of a new AlgaPrime-type DHA unit: Brazil vs Thailand.

The site-selection model ranks attractiveness; this module estimates cost and
return. For each case it computes, in constant 2025 USD:

* capex (greenfield benchmark x location factor x brownfield factor);
* cash cost per tonne of product: sugar, electricity, steam, labour, water and
  effluent, other variable inputs, maintenance and overheads, freight to the
  priority markets and unrecovered indirect taxes;
* effective income tax by year (Brazil 34%; Thailand BOI holiday floored at 15%
  by the Pillar Two top-up tax, then 20%);
* a USD real WACC with a country risk premium;
* the **minimum selling price (MSP)**: the product price at which NPV = 0 at
  that WACC, i.e. the price needed to earn the cost of capital. No market price
  is assumed, so the comparison does not depend on an invented price.

Cases: Brazil brownfield (expansion at Orindiuva), Brazil greenfield (new site,
grid power) and Thailand greenfield (BOI-promoted). It also runs FX / country
risk / tax scenarios, a one-at-a-time tornado on the Thailand-minus-Brazil MSP
gap and a Monte Carlo over the low/high ranges (shared process parameters are
drawn once for all cases, so their uncertainty does not create false gaps).

Every input lives in ``economics_assumptions.csv`` with its source or the label
``assumption``. Process coefficients and capex are placeholders to be replaced
with Corbion plant data and EPC quotes before any investment decision.

Usage::

    python brazil_thailand_economics.py            # outputs in ./outputs
    python brazil_thailand_economics.py --sims 10000
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import microalgae_site_selection as ms

BASE_DIR = Path(__file__).resolve().parent
ASSUMPTIONS = BASE_DIR / "economics_assumptions.csv"
OUTPUT_DIR = BASE_DIR / "outputs"
SEED = 42
log = logging.getLogger("economics")

CASES = {
    "Brazil – Orindiúva expansion": ("brazil", {}),
    "Brazil – greenfield": ("brazil", {"brownfield_capex_factor": None, "headcount": "thailand",
                                       "electricity_price": "brazil_high", "steam_price": "brazil_high"}),
    "Thailand – greenfield (BOI)": ("thailand", {}),
}
BR_BROWN, BR_GREEN, TH = list(CASES)


def load_assumptions(path: Path = ASSUMPTIONS) -> pd.DataFrame:
    """Read and validate the assumption table (low <= base <= high for every case)."""
    df = pd.read_csv(path).set_index("parameter")
    for country in ("brazil", "thailand"):
        lo, base, hi = df[f"{country}_low"], df[country], df[f"{country}_high"]
        bad = df.index[(lo > base + 1e-12) | (base > hi + 1e-12)]
        if len(bad):
            raise ValueError(f"{country}: low/base/high out of order for {list(bad)}")
    shared = df[df["shared"] == "yes"]
    differs = shared.index[(shared["brazil"] != shared["thailand"])
                           | (shared["brazil_low"] != shared["thailand_low"])
                           | (shared["brazil_high"] != shared["thailand_high"])]
    if len(differs):
        raise ValueError(f"Shared parameters must be identical for both countries: {list(differs)}")
    return df


def case_parameters(df: pd.DataFrame, case: str, column: str = "") -> dict[str, float]:
    """Parameter dict for a case. ``column`` '' = base, '_low' or '_high'."""
    country, overrides = CASES[case]
    p = df[f"{country}{column}"].astype(float).to_dict()
    for key, src in overrides.items():
        if src is None:
            p[key] = 1.0
        elif src == "thailand":
            p[key] = float(df.loc[key, "thailand"])
        elif src == "brazil_high":
            p[key] = float(df.loc[key, "brazil_high"])
    return p


@dataclass
class CaseResult:
    capex: float
    cost_lines: dict[str, float]  # USD per t product at steady state
    wacc_real: float
    msp: float  # USD per t product
    msp_per_kg_dha: float
    pv_tax_share: float


def wacc_real(p: dict[str, float], tax_rate: float) -> float:
    """USD real WACC: CAPM cost of equity with country risk premium (default spread x 1.5)."""
    crp = p["default_spread"] * 1.5
    ke = p["risk_free"] + p["beta"] * p["mature_erp"] + crp
    kd = (p["risk_free"] + p["default_spread"] + p["debt_margin"]) * (1 - tax_rate)
    nominal = (1 - p["debt_share"]) * ke + p["debt_share"] * kd
    return (1 + nominal) / (1 + p["inflation_usd"]) - 1


def cost_lines(p: dict[str, float], capex: float, fx_factor: float = 1.0) -> dict[str, float]:
    """Steady-state cost per tonne of product, USD. ``fx_factor`` scales FX-exposed local costs."""
    q = p["capacity"] * p["utilisation_steady"]
    local = {
        "sugar": p["sugar_kg_per_kg"] * p["sugar_price"],
        "electricity": p["electricity_kwh_per_kg"] * 1000 * p["electricity_price"],
        "steam": p["steam_t_per_t"] * p["steam_price"],
        "water_effluent": p["water_m3_per_t"] * p["water_price"],
        "labour": p["headcount"] * p["labour_cost_per_fte"] / q,
    }
    exposed = p["fx_exposed_share_opex"]
    lines = {k: v * (exposed * fx_factor + (1 - exposed)) for k, v in local.items()}
    lines["other_variable"] = p["other_variable"]
    lines["maintenance_overhead"] = (p["maintenance_pct_capex"] + p["overhead_insurance_pct_capex"]) * capex / q
    lines["freight"] = p["freight"]
    lines["indirect_tax_leakage"] = p["indirect_tax_leakage"] * sum(lines.values())
    return lines


def evaluate(p: dict[str, float], fx_factor: float = 1.0, holiday_floor: float | None = None) -> CaseResult:
    """Capex, unit costs, WACC and minimum selling price for one parameter set."""
    capex_local_share = p["fx_exposed_share_capex"]
    capex = (p["capex_greenfield"] * p["capacity"] * p["location_capex_factor"] * p["brownfield_capex_factor"]
             * (capex_local_share * fx_factor + (1 - capex_local_share)))
    lines = cost_lines(p, capex, fx_factor)
    cash_cost = sum(lines.values())
    floor = p["holiday_floor_rate"] if holiday_floor is None else holiday_floor
    years = int(p["project_years"])
    holiday = int(p["tax_holiday_years"])
    rates = np.array([floor if t < holiday else p["income_tax_rate"] for t in range(years)])
    r = wacc_real(p, p["income_tax_rate"])
    util = np.array([0.5, 0.8] + [p["utilisation_steady"]] * (years - 2))
    q = p["capacity"] * util
    dep = np.where(np.arange(years) < p["depreciation_years"], capex / p["depreciation_years"], 0.0)
    fixed = (lines["labour"] + lines["maintenance_overhead"]) * p["capacity"] * p["utilisation_steady"]
    variable_per_t = cash_cost - lines["labour"] - lines["maintenance_overhead"]
    disc_capex = capex * (p["construction_split_y1"] + (1 - p["construction_split_y1"]) / (1 + r))
    t_op = np.arange(years) + 2  # operations start after two build years
    disc = 1 / (1 + r) ** t_op

    def npv(price: float) -> tuple[float, float]:
        revenue = price * q
        ebitda = revenue - variable_per_t * q - fixed
        taxable = ebitda - dep
        loss_cf, tax = 0.0, np.zeros(years)
        for i in range(years):  # simple loss carry-forward
            base = taxable[i] - loss_cf
            tax[i] = max(0.0, base) * rates[i]
            loss_cf = max(0.0, -base)
        wc = p["working_capital_pct_revenue"] * revenue
        d_wc = np.diff(np.concatenate([[0.0], wc]))
        cf = ebitda - tax - d_wc
        cf[-1] += wc[-1]
        return float((cf * disc).sum() - disc_capex), float((tax * disc).sum())

    lo, hi = 0.0, 50_000.0
    for _ in range(45):  # bisection on price (precision < USD 0.01/t)
        mid = (lo + hi) / 2
        if npv(mid)[0] > 0:
            hi = mid
        else:
            lo = mid
    msp = (lo + hi) / 2
    pv_tax = npv(msp)[1]
    pv_rev = float((msp * q * disc).sum())
    return CaseResult(capex=capex, cost_lines=lines, wacc_real=r, msp=msp,
                      msp_per_kg_dha=msp / 1000 / p["dha_content"], pv_tax_share=pv_tax / pv_rev)


def base_results(df: pd.DataFrame) -> pd.DataFrame:
    """Table of base-case results for the three cases."""
    rows = {}
    for case in CASES:
        p = case_parameters(df, case)
        res = evaluate(p)
        cash = sum(res.cost_lines.values())
        row = {f"cost_{k}": v for k, v in res.cost_lines.items()}
        row.update(capex_musd=res.capex / 1e6, capex_per_t_capacity=res.capex / p["capacity"],
                   cash_cost_per_t=cash, capital_and_tax_per_t=res.msp - cash, msp_per_t=res.msp,
                   msp_per_kg_dha=res.msp_per_kg_dha, wacc_real=res.wacc_real,
                   pv_income_tax_pct_of_revenue=res.pv_tax_share)
        rows[case] = row
    return pd.DataFrame(rows).T


def scenarios(df: pd.DataFrame) -> pd.DataFrame:
    """FX, country-risk and tax scenarios on the MSP of each case."""
    def run(case: str, fx: float = 1.0, floor: float | None = None, **over) -> float:
        p = case_parameters(df, case) | over
        return evaluate(p, fx_factor=fx, holiday_floor=floor).msp

    br_fx = df.loc["fx_rate", "brazil"]
    th_fx = df.loc["fx_rate", "thailand"]
    out = []

    def add(name: str, br: float, brg: float, th: float) -> None:
        out.append({"scenario": name, BR_BROWN: br, BR_GREEN: brg, TH: th, "gap_TH_minus_BR_expansion": th - br})

    add("Base", run(BR_BROWN), run(BR_GREEN), run(TH))
    for label, rate in [("BRL depreciates 25% (7.00)", 7.00), ("BRL appreciates 25% (4.20)", 4.20)]:
        f = br_fx / rate
        add(label, run(BR_BROWN, f), run(BR_GREEN, f), run(TH))
    for label, rate in [("THB depreciates 10% (36.1)", 36.10), ("THB appreciates 10% (29.6)", 29.60)]:
        f = th_fx / rate
        add(label, run(BR_BROWN), run(BR_GREEN), run(TH, f))
    br_spread = df.loc["default_spread", "brazil"]
    th_spread = df.loc["default_spread", "thailand"]
    add("Brazil country risk +200 bp", run(BR_BROWN, default_spread=br_spread + 0.02),
        run(BR_GREEN, default_spread=br_spread + 0.02), run(TH))
    add("Thailand country risk +200 bp", run(BR_BROWN), run(BR_GREEN), run(TH, default_spread=th_spread + 0.02))
    add("Thailand: BOI fully effective (QRTC offsets top-up)", run(BR_BROWN), run(BR_GREEN), run(TH, floor=0.0))
    add("Thailand: no BOI holiday (20% from year 1)", run(BR_BROWN), run(BR_GREEN), run(TH, floor=0.20))
    add("Thailand sugar at 25 THB/kg (+3 THB proposal + drought)", run(BR_BROWN), run(BR_GREEN),
        run(TH, sugar_price=25000 / th_fx))
    add("Brazil sugar at export parity high (USD 550/t)", run(BR_BROWN, sugar_price=550),
        run(BR_GREEN, sugar_price=550), run(TH))
    return pd.DataFrame(out).set_index("scenario")


def tornado(df: pd.DataFrame) -> pd.DataFrame:
    """One-at-a-time swings of the Thailand-minus-Brazil(expansion) MSP gap."""
    base_gap = evaluate(case_parameters(df, TH)).msp - evaluate(case_parameters(df, BR_BROWN)).msp
    rows = []
    for param in df.index:
        if (df.loc[param, ["brazil_low", "brazil_high", "thailand_low", "thailand_high"]]
                == df.loc[param, ["brazil", "brazil", "thailand", "thailand"]].values).all():
            continue
        gaps = []
        for col in ("_low", "_high"):
            pb = case_parameters(df, BR_BROWN)
            pt = case_parameters(df, TH)
            if df.loc[param, "shared"] == "yes":
                pb[param] = pt[param] = float(df.loc[param, f"brazil{col}"])
                gaps.append(evaluate(pt).msp - evaluate(pb).msp)
            else:
                pb2 = pb | {param: float(df.loc[param, f"brazil{col}"])}
                gaps.append(evaluate(pt).msp - evaluate(pb2).msp)
                pt2 = pt | {param: float(df.loc[param, f"thailand{col}"])}
                gaps.append(evaluate(pt2).msp - evaluate(pb).msp)
        rows.append(dict(parameter=param, gap_min=min(gaps), gap_max=max(gaps),
                         swing=max(gaps) - min(gaps), shared=df.loc[param, "shared"]))
    out = pd.DataFrame(rows).sort_values("swing", ascending=False)
    out.attrs["base_gap"] = base_gap
    return out


def monte_carlo(df: pd.DataFrame, n: int = 5000, seed: int = SEED) -> pd.DataFrame:
    """Triangular draws within low/high; shared parameters drawn once per run for all cases."""
    rng = np.random.default_rng(seed)
    params = df.index
    out = []
    for _ in range(n):
        draw_shared, draw_country = {}, {"brazil": {}, "thailand": {}}
        for prm in params:
            for country in ("brazil", "thailand"):
                lo, mode, hi = (float(df.loc[prm, f"{country}_low"]), float(df.loc[prm, country]),
                                float(df.loc[prm, f"{country}_high"]))
                if df.loc[prm, "shared"] == "yes":
                    if prm not in draw_shared:
                        draw_shared[prm] = mode if hi == lo else rng.triangular(lo, mode, hi)
                    draw_country[country][prm] = draw_shared[prm]
                else:
                    draw_country[country][prm] = mode if hi == lo else rng.triangular(lo, mode, hi)
        row = {}
        for case, (country, over) in CASES.items():
            p = dict(draw_country[country])
            for key, src in over.items():
                if src is None:
                    p[key] = 1.0
                elif src == "thailand":
                    p[key] = draw_country["thailand"][key]
                elif src == "brazil_high":
                    p[key] = float(df.loc[key, "brazil_high"])
            row[case] = evaluate(p).msp
        out.append(row)
    return pd.DataFrame(out)


def summarize_mc(sims: pd.DataFrame) -> pd.DataFrame:
    rows = {c: dict(p5=sims[c].quantile(0.05), median=sims[c].median(), p95=sims[c].quantile(0.95))
            for c in sims}
    out = pd.DataFrame(rows).T
    out.loc["P(Brazil expansion cheaper than Thailand)", "median"] = (sims[BR_BROWN] < sims[TH]).mean()
    out.loc["P(Brazil greenfield cheaper than Thailand)", "median"] = (sims[BR_GREEN] < sims[TH]).mean()
    return out


# --------------------------------------------------------------------------- #
# Charts (same visual identity as the site-selection model)                   #
# --------------------------------------------------------------------------- #

GROUPS = {
    "Sugar": ["cost_sugar"],
    "Energy & steam": ["cost_electricity", "cost_steam"],
    "Labour & other opex": ["cost_labour", "cost_water_effluent", "cost_other_variable",
                            "cost_maintenance_overhead", "cost_indirect_tax_leakage"],
    "Freight to customers": ["cost_freight"],
    "Capital recovery & income tax": ["capital_and_tax_per_t"],
}
GROUP_COLORS = list(ms.CRITERION_COLORS.values())  # validated 5-colour order


def chart_cost_breakdown(res: pd.DataFrame, output_dir: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb
    from matplotlib.patches import Patch

    fig = ms.new_slide_figure(False)
    ms.draw_header(fig, "Minimum Selling Price per Tonne of Product",
                   "Price that earns each country's cost of capital, built up from unit costs (constant 2025 USD)")
    ax = fig.add_axes([0.24, 0.16, 0.66, 0.60])
    ms._plain_axes(ax)
    cases = list(res.index)[::-1]
    y = np.arange(len(cases))
    left = np.zeros(len(cases))
    for (group, cols), color in zip(GROUPS.items(), GROUP_COLORS):
        vals = res.loc[cases, cols].sum(axis=1).values
        ax.barh(y, vals, left=left, height=0.55, color=color, edgecolor=ms.PALETTE["bg_center"], linewidth=2)
        lum = sum(c * w for c, w in zip(to_rgb(color), (0.299, 0.587, 0.114)))
        for yi, l, v in zip(y, left, vals):
            if v > 260:
                ax.text(l + v / 2, yi, f"{v:,.0f}", ha="center", va="center", fontsize=11, fontweight="semibold",
                        color=ms.PALETTE["bg_center"] if lum > 0.6 else ms.PALETTE["text"])
        left += vals
    for yi, c in zip(y, cases):
        ax.text(left[yi] + 60, yi + 0.08, f"USD {res.loc[c, 'msp_per_t']:,.0f}/t", va="bottom", fontsize=14,
                fontweight="bold")
        ax.text(left[yi] + 60, yi - 0.05, f"≈ USD {res.loc[c, 'msp_per_kg_dha']:.1f}/kg DHA · "
                                           f"WACC {res.loc[c, 'wacc_real']:.1%} real", va="top", fontsize=10.5,
                color=ms.PALETTE["text_secondary"])
        ax.text(-80, yi, c, ha="right", va="center", fontsize=14, fontweight="semibold")
    ax.set_yticks([])
    ax.set_xlim(0, left.max() * 1.32)
    ax.tick_params(axis="x", labelsize=10)
    ax.grid(axis="x", color=ms.PALETTE["text"], alpha=0.1)
    handles = [Patch(color=c, label=g) for g, c in zip(GROUPS, GROUP_COLORS)]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.24, 0.835), ncol=5, frameon=False,
               fontsize=11, labelcolor=ms.PALETTE["text_secondary"], handlelength=1.2)
    fig.text(0.24, 0.065, "Process coefficients and capex are shared placeholder assumptions (economics_assumptions.csv);\n"
                          "differences between bars come from country inputs. Replace with Corbion plant data and EPC quotes.",
             fontsize=9.5, color=ms.PALETTE["text_secondary"])
    ms.draw_source_note(fig, "Sources: CEPEA/ESALQ; Thai OCSB price committee; GlobalPetrolPrices; IBGE PNAD; Bank of Thailand; "
                             "Damodaran (Jan 2026); KPMG/PwC; Thailand Top-Up Tax Decree B.E. 2567; Fed FX 2025; freight "
                             "forwarder quotes. Indicative only.")
    ms.save_figure(fig, output_dir / "economics_cost_breakdown.png")
    plt.close(fig)


def chart_tornado(tor: pd.DataFrame, output_dir: Path, top: int = 12) -> None:
    import matplotlib.pyplot as plt

    t = tor.head(top).iloc[::-1]
    base = tor.attrs["base_gap"]
    fig = ms.new_slide_figure(False)
    ms.draw_header(fig, "What Drives the Thailand–Brazil Cost Gap",
                   f"Minimum selling price gap, Thailand minus Brazil (Orindiúva expansion), USD per tonne · base gap "
                   f"{base:+,.0f}")
    ax = fig.add_axes([0.30, 0.13, 0.62, 0.68])
    ms._plain_axes(ax)
    y = np.arange(len(t))
    ax.barh(y, t["gap_max"] - t["gap_min"], left=t["gap_min"], height=0.55, color=ms.PALETTE["low_risk"])
    ax.axvline(base, color=ms.PALETTE["text"], linewidth=1.2)
    ax.axvline(0, color=ms.PALETTE["high_risk"], linewidth=1.2, linestyle=(0, (3, 3)))
    for yi, (_, r) in zip(y, t.iterrows()):
        ax.text(min(t["gap_min"].min(), 0) - 40, yi, r["parameter"].replace("_", " "),
                ha="right", va="center", fontsize=12)
        ax.text(r["gap_max"] + 15, yi, f"{r['gap_min']:+,.0f} to {r['gap_max']:+,.0f}", va="center", fontsize=10,
                color=ms.PALETTE["text_secondary"])
    ax.set_yticks([])
    ax.tick_params(axis="x", labelsize=10)
    ax.grid(axis="x", color=ms.PALETTE["text"], alpha=0.1)
    ax.set_xlim(min(t["gap_min"].min(), 0) - 30, t["gap_max"].max() * 1.25 + 50)
    fig.text(0.30, 0.075, "Positive = Thailand needs a higher price than Brazil. Dashed line = parity. "
                          "Shared parameters move both countries together.", fontsize=9.5,
             color=ms.PALETTE["text_secondary"])
    ms.draw_source_note(fig, "One-at-a-time sensitivity over the low/high ranges in economics_assumptions.csv. Indicative only.")
    ms.save_figure(fig, output_dir / "economics_tornado.png")
    plt.close(fig)


def run(output_dir: Path = OUTPUT_DIR, sims: int = 5000, charts: bool = True) -> dict[str, pd.DataFrame]:
    df = load_assumptions()
    output_dir.mkdir(parents=True, exist_ok=True)
    res = base_results(df)
    scen = scenarios(df)
    tor = tornado(df)
    mc = monte_carlo(df, sims)
    mc_sum = summarize_mc(mc)
    res.round(4).to_csv(output_dir / "economics_results.csv")
    scen.round(1).to_csv(output_dir / "economics_scenarios.csv")
    tor.round(1).to_csv(output_dir / "economics_tornado.csv", index=False)
    mc_sum.round(4).to_csv(output_dir / "economics_monte_carlo.csv")
    if charts:
        ms.setup_matplotlib()
        chart_cost_breakdown(res, output_dir)
        chart_tornado(tor, output_dir)
    log.info("Base results:\n%s", res[["capex_musd", "cash_cost_per_t", "msp_per_t", "msp_per_kg_dha",
                                       "wacc_real"]].round(3).to_string())
    log.info("Scenarios:\n%s", scen.round(0).to_string())
    log.info("Monte Carlo:\n%s", mc_sum.round(3).to_string())
    return dict(results=res, scenarios=scen, tornado=tor, monte_carlo=mc_sum)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--sims", type=int, default=5000)
    parser.add_argument("--no-charts", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    try:
        run(args.output_dir, args.sims, not args.no_charts)
    except (ValueError, FileNotFoundError) as exc:
        log.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
