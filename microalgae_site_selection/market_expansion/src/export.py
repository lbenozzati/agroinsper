"""Interface files for the site study (v3) and the reconciliation / waterfall tables."""

from __future__ import annotations

import importlib.util
import sys

import numpy as np
import pandas as pd

from .data import ROOT

V3_FIELDS = [
    "market", "country", "application", "species", "lifecycle_stage", "customer", "customer_role",
    "product_sku", "year", "eligible_final_product_t", "inclusion_rate", "expected_supplier_share",
    "opportunity_status", "contracted_volume_t", "adoption_probability_scenario",
    "ingredient_dha_fraction", "realized_price_currency_kg", "confidence", "source_id",
]
QUALIFIED = {"documented_current", "documented_historical", "trial", "channel_only"}
APP_MAP = {"salmon": "salmon", "shrimp": "shrimp", "pet_food": "pet_food"}
SPECIES = {"salmon": "Atlantic salmon", "shrimp": "L. vannamei", "pet_food": "dogs/cats"}


def load_v3_data_module(cfg: dict):
    path = ROOT / cfg["paths"]["v3_dir"] / "src" / "data.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("v3_data_module", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["v3_data_module"] = mod
    spec.loader.exec_module(mod)
    return mod


def demand_for_v3(cfg: dict, d: dict, seg: pd.DataFrame, scenario: str) -> pd.DataFrame:
    """Incremental SOM (vs 2025) by country/application/stage/year, split by evidence status. Contracted = 0."""
    A = d["A"]
    dha = A["dha_fraction_sku"]["base"]
    base_y = cfg["base_year"]
    params = d["params"].set_index(["country", "application"])
    rows = []
    for (c, a, stage), g in seg.groupby(["country", "application", "stage"]):
        mp = params.loc[(c, a)]
        g = g.set_index("year")
        documented = mp["relationship_status"] in QUALIFIED
        base_sku = g.loc[base_y, "som_sku_t"] if documented else 0.0
        for y in cfg["export_years"]:
            if y < cfg["first_decision_year"] + int(mp["time_to_revenue"]):
                continue
            inc = max(0.0, g.loc[y, "som_sku_t"] - base_sku)
            if inc <= 0:
                continue
            elig = g.loc[y, "eligible_feed_t"]
            share = g.loc[y, "corbion_share"]
            region = g.loc[y, "region"]
            china = region == "CHINA"
            rows.append({
                "market": region, "country": c, "application": "shrimp/fish" if china else APP_MAP[a],
                "species": SPECIES[a], "lifecycle_stage": stage,
                "customer": "documented accounts (see customer_evidence.csv)" if documented else "unidentified",
                "customer_role": "feed mill / distributor",
                "product_sku": "AlgaPrime DHA P3 (powder)", "year": y, "eligible_final_product_t": round(elig, 3),
                "inclusion_rate": inc / (elig * share) if elig * share > 0 else 0.0, "expected_supplier_share": share,
                "opportunity_status": "qualified_pipeline" if documented else "unqualified_potential",
                "contracted_volume_t": 0.0,
                "adoption_probability_scenario": f"market study scenario={scenario}; v3 applies A110/A111 weights",
                "ingredient_dha_fraction": dha, "realized_price_currency_kg": round(g.loc[y, "price_usd_kg_dha"] * dha, 3),
                "confidence": g.loc[y, "confidence"], "source_id": f"MARKET_STUDY_V1_{scenario.upper()}",
            })
    per_stage = pd.DataFrame(rows, columns=V3_FIELDS)
    if per_stage.empty:
        return per_stage
    per_stage["vol"] = (per_stage.eligible_final_product_t * per_stage.inclusion_rate * per_stage.expected_supplier_share)
    key = ["market", "country", "application", "customer", "product_sku", "year", "opportunity_status"]
    first = {c: "first" for c in V3_FIELDS if c not in key + ["eligible_final_product_t", "lifecycle_stage"]}
    agg = per_stage.groupby(key, as_index=False).agg({**first, "eligible_final_product_t": "sum", "vol": "sum",
                                                      "lifecycle_stage": lambda v: ";".join(sorted(set(v)))})
    agg["inclusion_rate"] = agg["vol"] / (agg["eligible_final_product_t"] * agg["expected_supplier_share"])
    return agg[V3_FIELDS]


def validate_against_v3(cfg: dict, demand: pd.DataFrame) -> str:
    mod = load_v3_data_module(cfg)
    if mod is None:
        return "v3 module not found: schema checked locally only"
    regions = list(mod.load_config()["regions"])
    mod.validate_demand(demand, regions)
    return "validated with v3 src/data.py validate_demand"


def curves(cfg: dict, d: dict, segs: dict) -> pd.DataFrame:
    """Per scenario/year/niche/country: incremental volume by status, price, unit margin, confidence."""
    rows = []
    params = d["params"].set_index(["country", "application"])
    for sc, seg in segs.items():
        agg = seg.groupby(["country", "application", "region", "year"], as_index=False).agg(
            som_sku_t=("som_sku_t", "sum"), price=("price_usd_kg_dha", "first"),
            margin=("unit_contribution_usd_kg_dha", "first"), confidence=("confidence", "first"))
        for (c, a), g in agg.groupby(["country", "application"]):
            st = params.loc[(c, a), "relationship_status"]
            base = g[g.year == cfg["base_year"]].som_sku_t.iloc[0] if st in QUALIFIED else 0.0
            for r in g.itertuples():
                inc = max(0.0, r.som_sku_t - base)
                rows.append({"scenario": sc, "year": r.year, "region": r.region, "country": c, "application": a,
                             "contracted_t": 0.0,
                             "qualified_pipeline_t": inc if st in QUALIFIED else 0.0,
                             "unqualified_potential_t": 0.0 if st in QUALIFIED else inc,
                             "net_price_usd_kg_dha": r.price, "unit_margin_usd_kg_dha": r.margin,
                             "confidence": r.confidence})
    return pd.DataFrame(rows)


def cockpit_bounds(d: dict, cur: pd.DataFrame) -> pd.DataFrame:
    A = d["A"]
    b = cur[cur.year == 2030].groupby("scenario")[["qualified_pipeline_t", "unqualified_potential_t"]].sum()
    return pd.DataFrame([
        {"control": "contracted_t", "low": 0.0, "base": 0.0,
         "high": float(b.loc["high", "qualified_pipeline_t"]),
         "dependency": "Contracts cannot exceed qualified pipeline of documented accounts (2030, high scenario)",
         "evidence": "no public contracts"},
        {"control": "price_usd_kg_dha", "low": A["net_price_usd_per_kg_dha"]["low"], "base": A["net_price_usd_per_kg_dha"]["base"],
         "high": A["net_price_usd_per_kg_dha"]["high"],
         "dependency": "Price and volume co-move through fish oil (pass-through 0.4; gap elasticity 0.3): high price with low "
                       "fish oil is inconsistent", "evidence": "B001/B005/B006"},
        {"control": "capex_ori_musd", "low": None, "base": None, "high": None,
         "dependency": "Set in the site study (v3); independent of market variables", "evidence": "v3 A020-A031"},
    ])


def reconciliation(cfg: dict, d: dict, seg: pd.DataFrame) -> pd.DataFrame:
    A = d["A"]
    fx = A["fx_eurusd"]["base"]
    s25 = seg[seg.year == cfg["base_year"]]
    bu_sku = s25.som_sku_t.sum()
    bu_rev = s25.revenue_usd.sum() / 1e6
    price_sku = A["net_price_usd_per_kg_dha"]["base"] * A["dha_fraction_sku"]["base"]
    salmon_feed = seg[(seg.year == 2025) & (seg.application == "salmon")].groupby("country").feed_t.first().sum()
    salmon_epa_dha = (seg[(seg.year == 2025) & (seg.application == "salmon")].tam_dha_t.sum() / 0.5)
    ecu = seg[(seg.year == 2025) & (seg.country == "Ecuador")].groupby("country").feed_t.first().sum()
    rows = [
        {"check": "Bottom-up Corbion SOM 2025 vs Nutrition sales 2024 (EUR 157 m)", "bottom_up": f"{bu_sku:,.0f} t SKU / USD {bu_rev:,.0f} m",
         "top_down": f"EUR 157 m = USD {157 * fx:,.0f} m -> {157 * fx * 1e6 / (price_sku * 1000):,.0f} t SKU at USD {price_sku:.2f}/kg SKU",
         "status": "INCOMPATIBLE SCOPES", "interpretation": "Nutrition includes AlgaVia (human) and pet; realised prices may be well above "
         "the USD 25/kg DHA premise; SOM premises may be conservative. Gap cannot be resolved with public data."},
        {"check": "Nutrition 2030 ambition (~EUR 275 m) vs bottom-up 2030 revenue",
         "bottom_up": f"USD {seg[seg.year == 2030].revenue_usd.sum() / 1e6:,.0f} m (feed + pet only)",
         "top_down": f"EUR 275 m = USD {275 * fx:,.0f} m", "status": "check only",
         "interpretation": "Target is revenue across products; not a volume or a feed-only figure."},
        {"check": "Salmon feed total vs BioMar salmon volume", "bottom_up": f"{salmon_feed / 1e6:.2f} Mt salmon feed (NO+CL+UK+AU)",
         "top_down": "BioMar 1.557 Mt x 60% salmon = 0.93 Mt", "status": "plausible",
         "interpretation": f"Implies BioMar ~{0.934e6 / salmon_feed:.0%} of modelled salmon feed."},
        {"check": "Veramaris capacity ~15% of salmon EPA+DHA demand", "bottom_up": f"{salmon_epa_dha:,.0f} t EPA+DHA requirement 2025 (model)",
         "top_down": f"15% = {0.15 * salmon_epa_dha:,.0f} t EPA+DHA (if claim applied to this base)", "status": "order of magnitude only",
         "interpretation": "Fish-equivalent claim not convertible without assay; used for competitive intensity only."},
        {"check": "Ecuador shrimp feed: production x eFCR vs Aprobal", "bottom_up": f"{ecu / 1e6:.2f} Mt",
         "top_down": "6.2 Mt x 40% = 2.5 Mt (derived)", "status": "consistent (within ~8%)", "interpretation": "Supports Ecuador feed base."},
        {"check": "GMI market value / volume", "bottom_up": "n/a", "top_down": "USD 720 m / 12.5 kt = USD 57.6/kg (NOT computed for use)",
         "status": "REJECTED", "interpretation": "Scope (systems/ingredients/oil) and tonne definition unknown; 6x conflict with USD 4.5 bn page."},
    ]
    return pd.DataFrame(rows)


def waterfall(cfg: dict, seg: pd.DataFrame, year: int = 2030) -> pd.DataFrame:
    s = seg[seg.year == year]
    g = s.groupby("application").agg(feed_t=("stage_feed_t", "sum"), tam_dha_t=("tam_dha_t", "sum"),
                                     sam_dha_t=("sam_dha_t", "sum"), algal_dha_t=("algal_dha_t", "sum"),
                                     som_dha_t=("som_dha_t", "sum"), som_sku_t=("som_sku_t", "sum"),
                                     revenue_musd=("revenue_usd", lambda v: v.sum() / 1e6),
                                     contribution_musd=("contribution_usd", lambda v: v.sum() / 1e6)).reset_index()
    g.insert(0, "year", year)
    return g


def v3_effect(cfg: dict, demands: dict) -> pd.DataFrame:
    """Run the v3 site engine in memory with this study's demand (no file is overwritten)."""
    import importlib
    v3src = ROOT / cfg["paths"]["v3_dir"] / "src"
    if not (v3src / "engine.py").exists():
        return pd.DataFrame()
    spec = importlib.util.spec_from_file_location("v3src", v3src / "__init__.py", submodule_search_locations=[str(v3src)])
    pkg = importlib.util.module_from_spec(spec)
    sys.modules["v3src"] = pkg
    spec.loader.exec_module(pkg)
    v3d = importlib.import_module("v3src.data")
    v3e = importlib.import_module("v3src.engine")
    v3a = importlib.import_module("v3src.analysis")
    c3 = v3d.load_config()
    a3 = v3d.load_assumptions(c3)
    p0 = v3d.build_params(c3, a3, v3d.load_freight(c3))
    rows = []
    for source, dem in [("v3 default premises", v3d.load_demand(c3, a3)[0])] + [(f"market study {k}", v) for k, v in demands.items()]:
        for weights in ("base", "upside"):
            p = v3a.params_for(c3, p0, dem, weights)
            for alt in ("A1_ORI", "C_TH_NSN", "F_ORI_THEN_TH", "G_ORI_TH_NOW"):
                r = v3e.run_alternative(p, c3["alternatives"][alt])
                ys = r["years"]
                rows.append({"demand_source": source, "v3_pipeline_weights": weights, "alternative": alt,
                             "npv_musd": r["npv"] / 1e6, "npv_ex_tv_musd": r["npv_ex_tv"] / 1e6,
                             "utilisation_2030": r["utilisation"][ys.index(2030)],
                             "utilisation_2035": r["utilisation"][ys.index(2035)],
                             "units": "; ".join(f"{u['id']}@{u['online']}" for u in r["units"]),
                             "msp_usd_kg_dha": v3e.msp(p, c3["alternatives"][alt]) if alt == "A1_ORI" else None})
    return pd.DataFrame(rows)
