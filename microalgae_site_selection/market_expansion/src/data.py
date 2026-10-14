"""Inputs and validation rules for the market study."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
RELATIONSHIP = ("documented_current", "documented_historical", "trial", "channel_only", "potential", "unknown")
VALUE_TYPES = {"reported", "derived", "proxy", "assumption", "unknown"}
ACCESS = {"primary_read", "search_snippet", "unavailable", "user_supplied", "inherited_v2"}


class InputError(ValueError):
    pass


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def raw(cfg: dict, name: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / cfg["paths"]["raw"] / name)


def validate_sources(s: pd.DataFrame) -> pd.DataFrame:
    errs = []
    if s["source_id"].duplicated().any():
        errs.append("duplicate source_id")
    for _, r in s.iterrows():
        has_value = pd.notna(r["value"]) and str(r["value"]).strip() != ""
        if has_value and (pd.isna(r["unit"]) or pd.isna(r["vintage"]) or str(r["vintage"]).strip() == ""):
            errs.append(f"{r.source_id}: value without unit/vintage")
        if r["value_type"] not in VALUE_TYPES:
            errs.append(f"{r.source_id}: bad value_type")
        if r["access_status"] not in ACCESS:
            errs.append(f"{r.source_id}: bad access_status")
        for col in ("url", "publisher", "access_date"):
            if pd.isna(r[col]) or str(r[col]).strip() == "":
                errs.append(f"{r.source_id}: empty {col}")
    if errs:
        raise InputError("; ".join(errs))
    return s


def validate_feed(f: pd.DataFrame) -> pd.DataFrame:
    errs = []
    for _, r in f.iterrows():
        if pd.isna(r["observed_feed_t"]):
            if pd.isna(r["production_t"]) or pd.isna(r["fcr"]):
                errs.append(f"{r.country}/{r.application}: needs observed feed or production x FCR")
            elif not 0.8 <= r["fcr"] <= 2.5:
                errs.append(f"{r.country}/{r.application}: implausible FCR {r['fcr']}")
        if not (r["growth_low"] <= r["growth_base"] <= r["growth_high"]):
            errs.append(f"{r.country}: growth low/base/high order")
    if f.duplicated(["country", "application"]).any():
        errs.append("duplicate country x application (double counting)")
    if errs:
        raise InputError("; ".join(errs))
    return f


def validate_nutrition(n: pd.DataFrame) -> pd.DataFrame:
    errs = []
    for app, g in n.groupby("application"):
        if abs(g["feed_share"].sum() - 1.0) > 1e-9:
            errs.append(f"{app}: stage feed shares sum to {g['feed_share'].sum()}")
    if (n["dha_share_of_target"] >= 1.0).any() or (n["dha_share_of_target"] <= 0).any():
        errs.append("DHA share of EPA+DHA must be in (0,1): DHA != EPA")
    for c in ("marine_supplied_share", "econ_capable_share", "tech_qualified_share"):
        if not n[c].between(0, 1).all():
            errs.append(f"{c} outside [0,1]")
    if errs:
        raise InputError("; ".join(errs))
    return n


def validate_customers(c: pd.DataFrame) -> pd.DataFrame:
    bad = set(c["relationship_status"]) - set(RELATIONSHIP)
    if bad:
        raise InputError(f"unknown relationship status {bad}")
    cur = c[c["relationship_status"] == "documented_current"]
    for _, r in cur.iterrows():
        d = str(r["evidence_date"])
        if not d[:4].isdigit() or int(d[:4]) < 2025:
            raise InputError(f"{r.entity}: 'documented_current' needs evidence dated 2025 or later")
    return c


def validate_params(m: pd.DataFrame) -> pd.DataFrame:
    if not set(m["relationship_status"]) <= set(RELATIONSHIP):
        raise InputError("bad relationship status in market_parameters")
    if ((m["share_low"] > m["corbion_share"]) | (m["corbion_share"] > m["share_high"])).any():
        raise InputError("corbion share order")
    if (m["adoption_start"] > m["adoption_sat"]).any():
        raise InputError("adoption start above saturation")
    return m


def assumptions(cfg: dict) -> dict:
    a = raw(cfg, "market_assumptions.csv")
    if ((a.low > a.base) | (a.base > a.high)).any():
        raise InputError("market_assumptions low<=base<=high")
    return {r.parameter: {"base": float(r.base), "low": float(r.low), "high": float(r.high)} for r in a.itertuples()}


def load_all(cfg: dict) -> dict:
    d = {
        "sources": validate_sources(raw(cfg, "source_registry.csv")),
        "feed": validate_feed(raw(cfg, "country_species_feed.csv")),
        "nutrition": validate_nutrition(raw(cfg, "nutrition_requirements.csv")),
        "products": raw(cfg, "product_specs.csv"),
        "customers": validate_customers(raw(cfg, "customer_evidence.csv")),
        "competitors": raw(cfg, "competitor_assets.csv"),
        "pricing": raw(cfg, "pricing_evidence.csv"),
        "params": validate_params(raw(cfg, "market_parameters.csv")),
        "definitions": raw(cfg, "market_definitions.csv"),
        "claims": raw(cfg, "market_claims_audit.csv"),
        "A": assumptions(cfg),
    }
    if (pd.to_numeric(d["products"]["dha_min_pct"], errors="coerce") > 100).any():
        raise InputError("DHA content above 100%")
    ids = set(d["sources"]["source_id"]) | {"ASSUMPTION"}
    for name in ("feed",):
        for col in ("production_source", "feed_source", "fcr_source"):
            for v in d[name][col].dropna():
                if v not in ids:
                    raise InputError(f"{name}.{col} cites unknown source {v}")
    v3_ue = ROOT / cfg["paths"]["v3_dir"] / "outputs" / "unit_economics.csv"
    d["v3_variable_cost_source"] = "default B007"
    if v3_ue.exists():
        ue = pd.read_csv(v3_ue).set_index("site_id")
        if "BR_ORI_EXP" in ue.index:
            row = ue.loc["BR_ORI_EXP"]
            var = sum(row[c] for c in ue.columns if c.endswith("_usd_per_t") and c.split("_usd_per_t")[0] in (
                "sugar", "electricity", "steam", "water_effluent", "nutrients_packaging", "indirect_tax_leakage"))
            kg = row["cash_cost_usd_per_t"] / row["cash_cost_usd_per_kg_dha"]
            d["A"]["variable_cost_usd_per_kg_dha"]["base"] = float(var / kg)
            d["v3_variable_cost_source"] = "v3 outputs/unit_economics.csv (BR_ORI_EXP variable cost / DHA kg)"
    v3_fr = ROOT / cfg["paths"]["v3_dir"] / "data" / "raw" / "freight_lanes.csv"
    if v3_fr.exists():
        fr = pd.read_csv(v3_fr)
        d["freight_br"] = {r.region: float(r.usd_per_t) for r in fr[fr.origin_country == "BR"].itertuples()}
    else:
        d["freight_br"] = {"SALMON": 140, "SHRIMP_AM": 140, "SHRIMP_ASIA": 105, "CHINA": 88, "PET": 140}
    return d
