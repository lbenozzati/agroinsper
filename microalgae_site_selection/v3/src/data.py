"""Inputs: config, evidence registry, assumptions, freight, sites and market demand."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
STATUSES = ("contracted", "qualified_pipeline", "unqualified_potential")
DEMAND_FIELDS = [
    "market", "country", "application", "species", "lifecycle_stage", "customer", "customer_role",
    "product_sku", "year", "eligible_final_product_t", "inclusion_rate", "expected_supplier_share",
    "opportunity_status", "contracted_volume_t", "adoption_probability_scenario",
    "ingredient_dha_fraction", "realized_price_currency_kg", "confidence", "source_id",
]
EVIDENCE_REQUIRED = ["source_id", "title", "publisher", "url", "access_date", "value_type",
                     "reliability", "access_status"]
VALUE_TYPES = {"reported", "derived", "proxy", "assumption", "unknown"}
ACCESS_STATUSES = {"primary_read", "search_snippet", "unavailable", "user_supplied", "inherited_v2"}


class InputError(ValueError):
    """Raised when an input table breaks a documented rule."""


def load_config(path: Path | None = None) -> dict:
    with open(path or ROOT / "config.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def raw_dir(cfg: dict) -> Path:
    return ROOT / cfg["paths"]["raw"]


def file_hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def validate_evidence(ev: pd.DataFrame) -> pd.DataFrame:
    """Reject evidence rows that carry a number without unit or vintage, or use unknown labels."""
    errors = []
    for col in EVIDENCE_REQUIRED:
        if col not in ev.columns:
            raise InputError(f"evidence registry missing column {col}")
        bad = ev[ev[col].isna() | (ev[col].astype(str).str.strip() == "")]
        for sid in bad.get("source_id", pd.Series(dtype=str)).fillna("?"):
            errors.append(f"{sid}: empty {col}")
    if ev["source_id"].duplicated().any():
        errors.append(f"duplicate source_id: {sorted(ev.loc[ev.source_id.duplicated(), 'source_id'])}")
    has_value = ev["value"].notna() & (ev["value"].astype(str).str.strip() != "")
    for _, r in ev[has_value].iterrows():
        if pd.isna(r.get("unit")) or str(r.get("unit")).strip() == "":
            errors.append(f"{r.source_id}: value without unit")
        if pd.isna(r.get("vintage")) or str(r.get("vintage")).strip() == "":
            errors.append(f"{r.source_id}: value without vintage")
    bad_types = set(ev["value_type"]) - VALUE_TYPES
    if bad_types:
        errors.append(f"unknown value_type {bad_types}")
    bad_access = set(ev["access_status"]) - ACCESS_STATUSES
    if bad_access:
        errors.append(f"unknown access_status {bad_access}")
    if errors:
        raise InputError("; ".join(errors))
    return ev


def load_evidence(cfg: dict) -> pd.DataFrame:
    ev = pd.read_csv(raw_dir(cfg) / "evidence_registry.csv")
    return validate_evidence(ev)


def load_assumptions(cfg: dict) -> pd.DataFrame:
    a = pd.read_csv(raw_dir(cfg) / "assumptions.csv")
    if a.duplicated(["parameter", "scope"]).any():
        raise InputError("duplicate (parameter, scope) in assumptions.csv")
    num = a[["base", "low", "high"]]
    if num.isna().any().any():
        raise InputError("assumption without base/low/high")
    if ((a["low"] > a["base"]) | (a["base"] > a["high"])).any():
        bad = a.loc[(a["low"] > a["base"]) | (a["base"] > a["high"]), "parameter"].tolist()
        raise InputError(f"low <= base <= high violated for {bad}")
    ev_ids = set(pd.read_csv(raw_dir(cfg) / "evidence_registry.csv")["source_id"])
    for sids in a["source_id"].dropna():
        for sid in str(sids).split(";"):
            if sid and sid not in ev_ids:
                raise InputError(f"assumption cites unknown source_id {sid}")
    return a


def assumption(a: pd.DataFrame, parameter: str, scope: str = "global", which: str = "base") -> float:
    row = a[(a.parameter == parameter) & (a.scope == scope)]
    if row.empty:
        raise KeyError(f"{parameter}/{scope}")
    return float(row.iloc[0][which])


def load_freight(cfg: dict) -> pd.DataFrame:
    return pd.read_csv(raw_dir(cfg) / "freight_lanes.csv")


def load_sites(cfg: dict) -> pd.DataFrame:
    return pd.read_csv(raw_dir(cfg) / "site_candidates.csv")


def load_gates(cfg: dict) -> pd.DataFrame:
    g = pd.read_csv(raw_dir(cfg) / "site_gates.csv")
    if not set(g["status"]) <= {"PASS", "REVIEW", "FAIL", "NOT_VERIFIED"}:
        raise InputError("gate status must be PASS/REVIEW/FAIL/NOT_VERIFIED")
    return g


SITE_COUNTRY = {"BR_ORI_EXP": "BR", "BR_GF_GO": "BR", "TH_NSN": "TH", "TH_RYG": "TH"}
BROWNFIELD = {"BR_ORI_EXP"}


def build_params(cfg: dict, a: pd.DataFrame, freight: pd.DataFrame, which: str = "base") -> dict:
    """Flatten assumptions into the JSON-serialisable parameter dict the engine (Python and JS) uses."""
    g = lambda p, s="global": assumption(a, p, s, which)  # noqa: E731
    b = lambda p, s="global": assumption(a, p, s, "base")  # noqa: E731
    p: dict = {
        "base_year": cfg["base_year"], "end_year": cfg["end_year"],
        "dha_fraction": g("dha_fraction_sku"), "dha_yield": g("dha_yield_on_sugar"),
        "recovery": g("downstream_recovery"), "kwh_per_t": g("electricity_kwh_per_t"),
        "steam_per_t": g("steam_t_per_t"), "water_per_t": g("water_m3_per_t"),
        "nutrients": g("nutrients_usd_per_t"), "packaging": g("packaging_usd_per_t"),
        "oee": g("oee"), "ramp1": g("rampup_year1"), "ramp2": g("rampup_year2"),
        "module_t": b("module_capacity_t"),
        "capex_intensity": g("capex_intensity_greenfield"),
        "share": {k: b(f"capex_share_{k}") for k in
                  ("fermentation", "downstream", "utilities", "effluent", "buildings", "epc_owner")},
        "bf_utilities": g("brownfield_utilities_factor"), "bf_buildings": g("brownfield_buildings_factor"),
        "bf_owner": g("brownfield_owner_factor"),
        "cont_gf": g("contingency_greenfield"), "cont_bf": g("contingency_brownfield"),
        "import_share": g("imported_equipment_share"), "maint_pct": g("maintenance_pct_capex"),
        "ins_pct": g("insurance_pct_capex"), "wc_pct": g("working_capital_pct_revenue"),
        "dep_years": b("tax_depreciation_years"), "g": g("terminal_growth_nominal"),
        "economic_life": 20,
        "price_dha": g("net_price_usd_per_kg_dha"),
        "price_mult": {r: g(spec["price_param"]) for r, spec in cfg["regions"].items()},
        "passthrough": g("fish_oil_passthrough"), "fish_oil_base": b("fish_oil_base"),
        "fish_oil": b("fish_oil_base"),
        "infl_usd": g("inflation_usd"), "globe_rate": b("globe_min_rate"),
        "sbie_pay": g("sbie_payroll_rate"), "sbie_asset": g("sbie_asset_rate"),
        "transit_rate": g("transit_carry_rate"),
        "outage_prob": g("outage_prob_per_plant_year"), "outage_dur": g("outage_duration_years"),
        "asia_capture_br": g("asia_capture_from_brazil"), "asia_capture_hub": g("asia_capture_with_hub"),
        "west_capture_th": g("west_capture_from_thailand"),
        "hub": {"capex": g("hub_capex_musd", "ASIA_HUB") * 1e6, "opex": g("hub_opex_musd", "ASIA_HUB") * 1e6,
                "handling": g("hub_handling_usd_per_t", "ASIA_HUB"), "capex_year": 2027},
        "staged_trigger_util": g("staged_trigger_utilisation"),
        "th_trigger_t": g("thailand_trigger_asia_t"), "decision_year": int(b("staged_decision_year")),
        "asia_regions": [r for r, s in cfg["regions"].items() if s["asia"]],
        "regions": list(cfg["regions"].keys()),
        "capex_override": {}, "capex_mult": {"BR": 1.0, "TH": 1.0}, "delay": {},
        "outage": {}, "fx_shock": {"BR": 0.0, "TH": 0.0},
    }
    rf, erp, beta = g("risk_free"), g("erp"), g("beta")
    crp_mult, dshare, dmargin = g("crp_multiplier"), g("debt_share"), g("debt_margin")
    p["country"] = {}
    for c in ("BR", "TH"):
        spread, cit = g("default_spread", c), g("cit_rate", c)
        ke = rf + beta * erp + crp_mult * spread
        kd = rf + spread + dmargin
        p["country"][c] = {
            "wacc": (1 - dshare) * ke + dshare * kd * (1 - cit),
            "cit": cit, "nol_cap": g("loss_offset_cap", c), "holiday": int(round(g("boi_holiday_years", c))),
            "globe_applies": int(round(g("globe_topup_applies", c))), "qrtc": g("qrtc_rate", c),
            "leak": g("indirect_tax_leakage", c), "duty": g("import_duty_rate", c),
            "labour": g("labour_usd_per_fte", c),
        }
    p["sites"] = {}
    for s, c in SITE_COUNTRY.items():
        p["sites"][s] = {
            "country": c, "brownfield": s in BROWNFIELD,
            "sugar": g("sugar_usd_per_t", s), "sugar_local": b("sugar_local_share", s),
            "elec": g("electricity_usd_per_kwh", s), "steam": g("steam_usd_per_t", s),
            "water": g("water_usd_per_m3", s), "headcount": g("headcount", s),
            "qa": g("qa_regulatory_fixed_musd", s) * 1e6, "loc": g("location_capex_factor", s),
            "conn": g("connection_capex_musd", s) * 1e6, "land": g("land_musd", s) * 1e6,
            "capex_local": b("capex_local_share", s), "first_capex": int(b("first_capex_year", s)),
            "build": int(b("build_years", s)), "gacc_delay": int(round(g("gacc_delay_years", s))),
        }
    col = {"base": "usd_per_t", "low": "low", "high": "high"}[which]
    p["freight"] = {c: {r["region"]: {"usd": float(r[col]), "days": float(r["transit_days"])}
                        for _, r in freight[freight.origin_country == c].iterrows()}
                    for c in ("BR", "TH")}
    p["scenario_weights"] = {s: {"contracted": 1.0,
                                 "qualified_pipeline": assumption(a, "pipeline_weight", s),
                                 "unqualified_potential": assumption(a, "unqualified_weight", s)}
                             for s in cfg["scenarios"]}
    p["demand"] = {}
    return p


COUNTRY_SPLIT = {
    "SALMON": [("Chile", "salmon", 0.50), ("Norway", "salmon", 0.35), ("United Kingdom", "salmon", 0.15)],
    "SHRIMP_AM": [("Ecuador", "shrimp", 1.0)],
    "SHRIMP_ASIA": [("Thailand", "shrimp", 0.25), ("Vietnam", "shrimp", 0.35), ("India", "shrimp", 0.25),
                    ("Indonesia", "shrimp", 0.15)],
    "CHINA": [("China", "shrimp/fish", 1.0)],
    "PET": [("United States", "pet_food", 0.55), ("European Union", "pet_food", 0.45)],
}
DEFAULT_POTENTIAL = {  # t SKU/yr of incremental potential (all statuses), linear 2028 -> 2035; ASSUMPTION
    "SALMON": (2000, 6000, 0.40), "SHRIMP_AM": (700, 3000, 0.20), "SHRIMP_ASIA": (1000, 5000, 0.25),
    "CHINA": (600, 4000, 0.15), "PET": (800, 2500, 0.50),
}
SPECIES = {"salmon": "Atlantic salmon", "shrimp": "L. vannamei", "shrimp/fish": "mixed aquaculture",
           "pet_food": "dogs/cats"}
STAGE = {"salmon": "grow-out/finishing", "shrimp": "grow-out", "shrimp/fish": "grow-out",
         "pet_food": "adult maintenance"}


def default_demand(cfg: dict, a: pd.DataFrame) -> pd.DataFrame:
    """Placeholder demand: every row is an analyst PREMISE, not an order or a market-study output."""
    rows = []
    price = assumption(a, "net_price_usd_per_kg_dha")
    dha = assumption(a, "dha_fraction_sku")
    inclusion = {"salmon": 0.006, "shrimp": 0.003, "shrimp/fish": 0.002, "pet_food": 0.002}
    share = 0.25
    for region, (v0, v1, qual_share) in DEFAULT_POTENTIAL.items():
        mult = assumption(a, cfg["regions"][region]["price_param"])
        for year in range(2028, cfg["end_year"] + 1):
            total = v0 + (v1 - v0) * (year - 2028) / (cfg["end_year"] - 2028)
            for country, app, w in COUNTRY_SPLIT[region]:
                for status, frac in (("qualified_pipeline", qual_share), ("unqualified_potential", 1 - qual_share)):
                    vol = total * w * frac
                    inc = inclusion[app]
                    rows.append({
                        "market": region, "country": country, "application": app, "species": SPECIES[app],
                        "lifecycle_stage": STAGE[app], "customer": "unidentified (premise)",
                        "customer_role": "feed mill/brand (premise)", "product_sku": "AlgaPrime DHA P3 (powder)",
                        "year": year, "eligible_final_product_t": round(vol / (inc * share), 1),
                        "inclusion_rate": inc, "expected_supplier_share": share,
                        "opportunity_status": status, "contracted_volume_t": 0.0,
                        "adoption_probability_scenario": "see scenario_weights in assumptions.csv (A110/A111)",
                        "ingredient_dha_fraction": dha,
                        "realized_price_currency_kg": round(price * mult * dha, 2),
                        "confidence": "low", "source_id": "ASSUMPTION_DEMAND_V3",
                    })
    return pd.DataFrame(rows, columns=DEMAND_FIELDS)


def validate_demand(d: pd.DataFrame, regions: list[str]) -> pd.DataFrame:
    missing = [c for c in DEMAND_FIELDS if c not in d.columns]
    if missing:
        raise InputError(f"market_demand_scenarios.csv missing fields {missing}")
    if not set(d["opportunity_status"]) <= set(STATUSES):
        raise InputError("opportunity_status must be contracted/qualified_pipeline/unqualified_potential")
    if not set(d["market"]) <= set(regions):
        raise InputError(f"unknown market ids {set(d['market']) - set(regions)}")
    key = ["market", "country", "application", "customer", "product_sku", "year", "opportunity_status"]
    if d.duplicated(key).any():
        raise InputError("duplicate demand rows (double counting) on " + ", ".join(key))
    vol = sku_volume(d)
    if (d["contracted_volume_t"] > vol + 1e-6).any():
        raise InputError("contracted_volume_t exceeds the row's SKU volume")
    if ((d["opportunity_status"] != "contracted") & (d["contracted_volume_t"] > 0)).any():
        raise InputError("contracted_volume_t > 0 on a non-contracted row")
    if ((d["ingredient_dha_fraction"] <= 0) | (d["ingredient_dha_fraction"] > 1)).any():
        raise InputError("ingredient_dha_fraction must be in (0, 1]")
    return d


def sku_volume(d: pd.DataFrame) -> pd.Series:
    return d["eligible_final_product_t"] * d["inclusion_rate"] * d["expected_supplier_share"]


def load_demand(cfg: dict, a: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    path = raw_dir(cfg) / "market_demand_scenarios.csv"
    if path.exists():
        d = pd.read_csv(path)
        origin = "file"
        if (d["source_id"] == "ASSUMPTION_DEMAND_V3").all():
            origin = "default_premises"
    else:
        d = default_demand(cfg, a)
        d.to_csv(path, index=False)
        origin = "default_premises"
    return validate_demand(d, list(cfg["regions"])), origin


def weighted_demand(d: pd.DataFrame, weights: dict, regions: list[str], years: list[int],
                    filters: dict | None = None) -> dict:
    """Region x year demand (t SKU) = contracted + w_pipeline x pipeline + w_unqualified x potential."""
    f = d.copy()
    for col, allowed in (filters or {}).items():
        if allowed:
            f = f[f[col].isin(allowed)]
    vol = sku_volume(f)
    w = f["opportunity_status"].map(weights).astype(float)
    eff = np.where(f["opportunity_status"] == "contracted", f["contracted_volume_t"], vol * w)
    f = f.assign(eff=eff)
    out = {r: {str(y): 0.0 for y in years} for r in regions}
    for (r, y), v in f.groupby(["market", "year"])["eff"].sum().items():
        if r in out and str(int(y)) in out[r]:
            out[r][str(int(y))] = float(v)
    return out


def add_contracted(demand: dict, contracted_t: float, asia_share: float, mix: dict, asia_regions: list[str],
                   start_year: int) -> dict:
    """Add a firm contracted volume, split Asia/non-Asia by asia_share and within each group by mix."""
    out = copy.deepcopy(demand)
    asia = [r for r in out if r in asia_regions]
    west = [r for r in out if r not in asia_regions]
    for group, share in ((asia, asia_share), (west, 1 - asia_share)):
        tot = sum(mix[r] for r in group) or 1.0
        for r in group:
            for y in out[r]:
                if int(y) >= start_year:
                    out[r][y] += contracted_t * share * mix[r] / tot
    return out


def region_mix(d: pd.DataFrame, regions: list[str]) -> dict:
    vol = sku_volume(d).groupby(d["market"]).sum()
    total = vol.sum() or 1.0
    return {r: float(vol.get(r, 0.0) / total) for r in regions}
