"""Multi-criteria site selection for a new Corbion microalgae (AlgaPrime DHA) plant.

The model reads auditable raw data (``raw_country_data.csv``), converts every
metric into a transparent 0-10 score, aggregates metrics into sub-criteria and
criteria, computes a weighted country score, flags viability issues, runs a
weight-sensitivity analysis and renders slide-ready charts.

Pipeline (each step is a separate function and a separate output file):

    raw data -> normalisation (metric scores) -> sub-criterion scores
             -> criterion scores -> weighted country score -> ranking

Usage::

    pip install -r requirements.txt
    python microalgae_site_selection.py                 # all outputs in ./outputs
    python microalgae_site_selection.py --plotly-static # also try Plotly/Kaleido PNG

Adding a country: append its rows to ``raw_country_data.csv`` (one row per
metric_id; ``outputs/country_data_template.csv`` lists every required metric).
"""

from __future__ import annotations

import argparse
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42  # fixed seed for the Monte Carlo simulation
np.random.seed(SEED)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = BASE_DIR / "raw_country_data.csv"
DEFAULT_OUTPUT = BASE_DIR / "outputs"
DEFAULT_RATINGS = BASE_DIR / "rubric_ratings.csv"  # optional extra raters for rubric metrics
V1_DATA = BASE_DIR / "archive" / "raw_country_data_v1.csv"  # data before the v2 corrections
FONT_DIR = BASE_DIR / "assets" / "fonts"
WORLD_GEOJSON = BASE_DIR / "assets" / "geo" / "ne_110m_admin_0_countries.geojson"
# Plotly base-map topojson (sane-topojson, MIT) embedded so the HTML also works offline.
PLOTLY_TOPOJSON = BASE_DIR / "assets" / "geo" / "plotly_world_110m.topojson.json"

log = logging.getLogger("site_selection")

# --------------------------------------------------------------------------- #
# Model definition                                                            #
# --------------------------------------------------------------------------- #

CRITERIA: dict[str, str] = {
    "production_economics": "Production Economics",
    "market_access": "Market Access",
    "corbion_readiness": "Corbion Industrial Readiness",
    "regulation_incentives": "Regulation & Incentives",
    "strategic_risk": "Strategic Risk",
}

SCENARIOS: dict[str, dict[str, float]] = {
    "Base Case": {
        "production_economics": 0.30, "market_access": 0.20, "corbion_readiness": 0.15,
        "regulation_incentives": 0.15, "strategic_risk": 0.20},
    "Lowest-Cost Production": {
        "production_economics": 0.40, "market_access": 0.15, "corbion_readiness": 0.20,
        "regulation_incentives": 0.10, "strategic_risk": 0.15},
    "Asian Market Expansion": {
        "production_economics": 0.25, "market_access": 0.30, "corbion_readiness": 0.10,
        "regulation_incentives": 0.15, "strategic_risk": 0.20},
}
BASE_SCENARIO = "Base Case"

# Sub-criterion weights inside each criterion (must sum to 1 per criterion).
SUBCRITERIA: dict[str, tuple[str, str, float]] = {
    # id: (criterion, label, weight within criterion)
    "pe_sugar": ("production_economics", "Sugar / glucose cost and availability", 0.35),
    "pe_energy": ("production_economics", "Electricity, renewable energy and steam", 0.30),
    "pe_water": ("production_economics", "Industrial water and waste treatment", 0.20),
    "pe_labor": ("production_economics", "Labour and construction costs", 0.15),
    "ma_aquafeed": ("market_access", "Addressable aquafeed market size", 0.35),
    "ma_species": ("market_access", "Premium, feed-intensive species", 0.30),
    "ma_logistics": ("market_access", "Ports and freight to priority markets", 0.20),
    "ma_customers": ("market_access", "Proximity to BioMar and other customers", 0.15),
    "cr_assets": ("corbion_readiness", "Existing plants, land and utilities", 0.50),
    "cr_talent": ("corbion_readiness", "Technical personnel and fermentation skills", 0.25),
    "cr_commercial": ("corbion_readiness", "Commercial offices / innovation / support", 0.25),
    "ri_approvals": ("regulation_incentives", "Feed, food and industrial approvals", 0.40),
    "ri_tax": ("regulation_incentives", "Corporate tax and investment incentives", 0.30),
    "ri_trade": ("regulation_incentives", "Tariffs, trade agreements and FDI", 0.30),
    "sr_competition": ("strategic_risk", "Local competition / excess capacity", 0.50),
    "sr_ip": ("strategic_risk", "Strain, patent and IP protection", 0.10),
    "sr_country": ("strategic_risk", "Political, currency, regulatory, commercial", 0.40),
}


@dataclass(frozen=True)
class MetricSpec:
    """Definition of how one raw metric becomes a 0-10 score.

    method:
        ``qualitative``  - raw value already is a rubric score (0/2.5/5/7.5/10).
        ``linear``       - goalpost scaling between ``worst`` (0) and ``best`` (10).
        ``log``          - same goalposts applied to log10 values (size metrics).
    Goalposts are fixed (UNDP-HDI style), so adding a country never rescales the
    others, and values beyond a goalpost are capped - a single outlier cannot
    stretch the scale.
    """

    metric_id: str
    subcriterion: str
    weight: float  # within sub-criterion
    method: str
    label: str
    higher_is_better: bool = True
    worst: float | None = None
    best: float | None = None
    valid_range: tuple[float, float] | None = None


METRICS: list[MetricSpec] = [
    # Production economics
    MetricSpec("pe_sugar_production", "pe_sugar", 0.5, "log", "Domestic sugar production (Mt)",
               True, worst=0.5, best=40.0, valid_range=(0, 300)),
    MetricSpec("pe_sugar_cost_position", "pe_sugar", 0.5, "qualitative", "Sugar cost position (rubric)"),
    MetricSpec("pe_electricity_price", "pe_energy", 0.4, "linear", "Business electricity price (USD/kWh)",
               False, worst=0.25, best=0.06, valid_range=(0, 1)),
    MetricSpec("pe_renewable_share_electricity", "pe_energy", 0.3, "linear", "Renewable share of electricity (%)",
               True, worst=10.0, best=90.0, valid_range=(0, 100)),
    MetricSpec("pe_steam_biomass_cogeneration", "pe_energy", 0.3, "qualitative", "Steam / biomass cogeneration (rubric)"),
    MetricSpec("pe_water_stress", "pe_water", 0.5, "linear", "Water stress, SDG 6.4.2 (%)",
               False, worst=80.0, best=5.0, valid_range=(0, 1000)),
    MetricSpec("pe_industrial_water_wastewater_infra", "pe_water", 0.5, "qualitative", "Industrial water & effluent infrastructure (rubric)"),
    MetricSpec("pe_gdp_per_capita", "pe_labor", 0.6, "linear", "GDP per capita (USD, labour-cost proxy)",
               False, worst=18000.0, best=2000.0, valid_range=(0, 200000)),
    MetricSpec("pe_construction_epc_capability", "pe_labor", 0.4, "qualitative", "Construction / EPC capability (rubric)"),
    # Market access
    MetricSpec("ma_aquafeed_volume", "ma_aquafeed", 1.0, "log", "Aquafeed volume (Mt)",
               True, worst=0.1, best=25.0, valid_range=(0, 100)),
    MetricSpec("ma_premium_species", "ma_species", 1.0, "qualitative", "Premium / DHA-intensive species (rubric)"),
    MetricSpec("ma_lpi_score", "ma_logistics", 0.5, "linear", "World Bank LPI 2023 (1-5)",
               True, worst=2.5, best=4.0, valid_range=(1, 5)),
    MetricSpec("ma_distance_priority_markets", "ma_logistics", 0.5, "linear",
               "Mean distance to China, Vietnam, Chile (km, derived)",
               False, worst=15000.0, best=3000.0, valid_range=(0, 25000)),
    MetricSpec("ma_biomar_customer_proximity", "ma_customers", 1.0, "qualitative", "BioMar / customer proximity (rubric)"),
    # Corbion readiness
    MetricSpec("cr_existing_manufacturing", "cr_assets", 1.0, "qualitative", "Existing Corbion manufacturing (rubric)"),
    MetricSpec("cr_fermentation_talent", "cr_talent", 1.0, "qualitative", "Fermentation talent (rubric)"),
    MetricSpec("cr_commercial_innovation_presence", "cr_commercial", 1.0, "qualitative", "Commercial / innovation presence (rubric)"),
    # Regulation & incentives
    MetricSpec("ri_product_approvals", "ri_approvals", 0.6, "qualitative", "Approval to SELL AlgaPrime (rubric)"),
    MetricSpec("ri_local_production_permitting", "ri_approvals", 0.4, "qualitative", "Ability to BUILD/OPERATE locally (rubric)"),
    MetricSpec("ri_corporate_tax_rate", "ri_tax", 0.5, "linear", "Statutory corporate tax rate (%)",
               False, worst=35.0, best=15.0, valid_range=(0, 60)),
    MetricSpec("ri_investment_incentives", "ri_tax", 0.5, "qualitative", "Investment incentives (rubric)"),
    MetricSpec("ri_trade_fdi_access", "ri_trade", 1.0, "qualitative", "Trade agreements & FDI openness (rubric)"),
    # Strategic risk (high score = LOW risk)
    MetricSpec("sr_local_competition_overcapacity", "sr_competition", 1.0, "qualitative", "Local competition / overcapacity (rubric)"),
    MetricSpec("sr_ip_protection", "sr_ip", 1.0, "qualitative", "IP protection - USTR Special 301 status (rubric)"),
    MetricSpec("sr_sovereign_rating_notch", "sr_country", 0.5, "linear", "S&P sovereign rating (notch, 1 = AAA)",
               False, worst=16.0, best=4.0, valid_range=(1, 22)),
    MetricSpec("sr_political_trade_policy_risk", "sr_country", 0.5, "qualitative", "Political / trade-policy risk (rubric)"),
]
METRIC_INDEX = {m.metric_id: m for m in METRICS}

# Metrics computed by the script rather than read from the CSV.
DERIVED_METRICS = {"ma_distance_priority_markets"}

META_METRICS = [
    "meta_display_lat", "meta_display_lon", "meta_port_lat", "meta_port_lon",
    "meta_corbion_manufacturing", "meta_biomar_manufacturing",
]

# Distance metric: "export_only" (default) averages the distance to the priority markets
# OTHER than the country itself, so China, Vietnam and Chile are not rewarded twice for being
# their own market (market size is already scored); "include_domestic" counts the home market
# as 0 km (v1 behaviour, kept for comparison).
DISTANCE_MODES = ("export_only", "include_domestic")
DEFAULT_DISTANCE_MODE = "export_only"

# Monte Carlo noise by confidence level: lognormal sigma for quantitative raw values and the
# probability that a rubric score is one level (2.5) off in either direction.
MC_QUANT_SIGMA = {"High": 0.05, "Medium": 0.15, "Low": 0.30}
MC_RUBRIC_SHIFT_PROB = {"High": 0.10, "Medium": 0.25, "Low": 0.40}
MC_DEFAULT_SIMS = 5000

# Priority markets named in the investment thesis; equal weight each.
PRIORITY_MARKETS = {
    "CHN": ("Shanghai", 31.23, 121.47),
    "VNM": ("Ho Chi Minh City", 10.76, 106.79),
    "CHL": ("Puerto Montt (salmon hub)", -41.47, -72.94),
}

QUALITATIVE_LEVELS = (0.0, 2.5, 5.0, 7.5, 10.0)
QUALITATIVE_LABELS = {0.0: "Highly unfavorable", 2.5: "Unfavorable", 5.0: "Neutral or mixed",
                      7.5: "Favorable", 10.0: "Highly favorable"}
CONFIDENCE_POINTS = {"High": 1.0, "Medium": 0.67, "Low": 0.33}
VALUE_TYPE_FACTOR = {"reported": 1.0, "estimate": 0.85, "proxy": 0.7, "missing": 0.0}
REQUIRED_COLUMNS = ["country", "iso3", "metric_id", "raw_value", "unit", "reference_year",
                    "source_name", "source_url", "date_accessed", "value_type", "confidence", "notes"]
TOLERANCE = 1e-9

# --------------------------------------------------------------------------- #
# Visual identity (sampled from the reference slide)                          #
# --------------------------------------------------------------------------- #

PALETTE = {
    "bg_left": "#000E38", "bg_center": "#060216", "bg_right": "#2E0133",
    "panel": "#010924", "text": "#FFFFFF", "text_secondary": "#D5D2DA",
    "silver": "#B6B3BA", "low_risk": "#4057C8", "mid_risk": "#B6B3BA",
    "high_risk": "#8C2F78", "border": "#E7E3EA",
    "land": "#0C1640", "land_edge": "#27306A", "land_focus": "#16215A",
}
# Criterion colours: validated with the dataviz palette checker on #060216
# (adjacent CVD dE >= 25, normal-vision dE >= 29); segments are also direct-labelled.
CRITERION_COLORS = {
    "production_economics": "#3A52C8", "market_access": "#9FB0FA",
    "corbion_readiness": "#A8327F", "regulation_incentives": "#D5D2DA",
    "strategic_risk": "#5C3C9E",
}
FONT_FAMILY = "Montserrat"
FIG_SIZE = (16, 9)  # inches -> 3840 x 2160 px at 240 dpi
FIG_DPI = 240
TITLE = "Best Locations for a New Microalgae Production Unit"
SUBTITLE = ("Weighted assessment of production economics, market access, execution readiness, "
            "regulation and strategic risk")
SOURCE_NOTE = (
    "Sources: Corbion; BioMar; USDA FAS; China Feed Industry Assoc.; Alltech; Sindirações; Ember (via OWID); "
    "FAO AQUASTAT SDG 6.4.2; World Bank WDI & LPI 2023; GlobalPetrolPrices; KPMG/PwC; USTR Special 301 (2026); "
    "S&P. Score 0–10, Base Case weights 30/20/15/15/20. Analyst rubric scores and data limits in "
    "methodology_and_sources.md. Accessed Oct 2026."
)


# --------------------------------------------------------------------------- #
# Data loading and validation                                                 #
# --------------------------------------------------------------------------- #

class DataValidationError(ValueError):
    """Raised when input data or model weights violate a hard rule."""


def load_country_data(path: Path = DEFAULT_DATA) -> pd.DataFrame:
    """Load the long-format raw data file.

    Empty ``raw_value`` cells stay NaN (never zero). Non-empty cells that are
    not numeric raise an error instead of being silently coerced.
    """
    if not path.exists():
        raise FileNotFoundError(f"Raw data file not found: {path}")
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise DataValidationError(f"Missing columns in {path.name}: {missing_cols}")
    df = df[REQUIRED_COLUMNS].copy()
    for col in ["country", "iso3", "metric_id", "value_type", "confidence"]:
        df[col] = df[col].str.strip()
    raw = df["raw_value"].str.strip()
    numeric = pd.to_numeric(raw.where(raw != ""), errors="coerce")
    bad = (raw != "") & numeric.isna()
    if bad.any():
        rows = df.loc[bad, ["country", "metric_id", "raw_value"]].to_dict("records")
        raise DataValidationError(f"Non-numeric raw values: {rows}")
    df["raw_value"] = numeric
    return df


def validate_weights(scenarios: dict[str, dict[str, float]] = SCENARIOS,
                     subcriteria: dict[str, tuple[str, str, float]] = SUBCRITERIA,
                     metrics: list[MetricSpec] = METRICS) -> None:
    """Check that criterion, sub-criterion and metric weights each sum to 100%."""
    errors = []
    for name, weights in scenarios.items():
        if set(weights) != set(CRITERIA):
            errors.append(f"Scenario '{name}' does not cover exactly the five criteria")
        if abs(sum(weights.values()) - 1.0) > TOLERANCE:
            errors.append(f"Scenario '{name}' weights sum to {sum(weights.values()):.4f}")
    for crit in CRITERIA:
        total = sum(w for c, _, w in subcriteria.values() if c == crit)
        if abs(total - 1.0) > TOLERANCE:
            errors.append(f"Sub-weights of '{crit}' sum to {total:.4f}")
    for sub in subcriteria:
        total = sum(m.weight for m in metrics if m.subcriterion == sub)
        if abs(total - 1.0) > TOLERANCE:
            errors.append(f"Metric weights of '{sub}' sum to {total:.4f}")
    for m in metrics:
        if m.subcriterion not in subcriteria:
            errors.append(f"Metric '{m.metric_id}' points to unknown sub-criterion")
        if m.method not in {"qualitative", "linear", "log"}:
            errors.append(f"Metric '{m.metric_id}' has unknown method '{m.method}'")
        if m.method != "qualitative" and (m.worst is None or m.best is None or m.worst == m.best):
            errors.append(f"Metric '{m.metric_id}' needs distinct goalposts")
    if errors:
        raise DataValidationError("Weight validation failed:\n  " + "\n  ".join(errors))
    log.info("Weights validated: criteria, sub-criteria and metric weights sum to 100%.")


def validate_input_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validate the long data set and return a data-quality report.

    Hard errors (raise): duplicate country/metric rows, one country with two
    ISO codes, unknown metric ids, qualitative values off the 0/2.5/5/7.5/10
    scale, values outside the plausible range, invalid type/confidence labels.
    Soft issues (reported, not fatal): missing values and missing metric rows.
    """
    issues: list[dict] = []
    errors: list[str] = []

    dup = df.duplicated(["country", "metric_id"], keep=False)
    if dup.any():
        errors.append(f"Duplicate country/metric rows: {df.loc[dup, ['country', 'metric_id']].values.tolist()}")
    iso = df.groupby("country")["iso3"].nunique()
    if (iso > 1).any():
        errors.append(f"Countries with several ISO codes: {iso[iso > 1].index.tolist()}")
    names = df.groupby("iso3")["country"].nunique()
    if (names > 1).any():
        errors.append(f"ISO codes used by several country names (duplicate country?): {names[names > 1].index.tolist()}")

    known = set(METRIC_INDEX) | set(META_METRICS)
    unknown = sorted(set(df["metric_id"]) - known)
    if unknown:
        errors.append(f"Unknown metric ids: {unknown}")
    derived_in_file = sorted(set(df["metric_id"]) & DERIVED_METRICS)
    if derived_in_file:
        errors.append(f"Derived metrics must not be typed in the CSV: {derived_in_file}")

    bad_type = ~df["value_type"].isin(VALUE_TYPE_FACTOR)
    if bad_type.any():
        errors.append(f"Invalid value_type: {df.loc[bad_type, 'value_type'].unique().tolist()}")
    bad_conf = ~df["confidence"].isin(CONFIDENCE_POINTS)
    if bad_conf.any():
        errors.append(f"Invalid confidence: {df.loc[bad_conf, 'confidence'].unique().tolist()}")

    for row in df.itertuples(index=False):
        spec = METRIC_INDEX.get(row.metric_id)
        value = row.raw_value
        if pd.isna(value):
            issues.append(dict(severity="warning", country=row.country, metric_id=row.metric_id,
                               message="Missing value - excluded from its sub-criterion (weights re-normalised) "
                                       "and penalised in Data Confidence; not set to zero."))
            if row.value_type != "missing":
                errors.append(f"{row.country}/{row.metric_id}: empty value must have value_type 'missing'")
            continue
        if row.value_type == "missing":
            errors.append(f"{row.country}/{row.metric_id}: value present but value_type is 'missing'")
        if spec is None:
            continue
        if spec.method == "qualitative":
            if not any(abs(value - lvl) < TOLERANCE for lvl in QUALITATIVE_LEVELS):
                errors.append(f"{row.country}/{row.metric_id}: qualitative value {value} not in {QUALITATIVE_LEVELS}")
        elif spec.valid_range and not spec.valid_range[0] <= value <= spec.valid_range[1]:
            errors.append(f"{row.country}/{row.metric_id}: {value} outside plausible range {spec.valid_range}")
        if not str(row.source_name).strip():
            issues.append(dict(severity="warning", country=row.country, metric_id=row.metric_id,
                               message="No source recorded."))

    required = (set(METRIC_INDEX) - DERIVED_METRICS) | set(META_METRICS)
    for country, grp in df.groupby("country"):
        for metric_id in sorted(required - set(grp["metric_id"])):
            issues.append(dict(severity="warning", country=country, metric_id=metric_id,
                               message="Metric row absent - treated as missing (not zero)."))
            if metric_id in META_METRICS[:4]:
                errors.append(f"{country}: coordinate metadata '{metric_id}' is required")

    if errors:
        raise DataValidationError("Input validation failed:\n  " + "\n  ".join(errors))
    report = pd.DataFrame(issues, columns=["severity", "country", "metric_id", "message"])
    log.info("Input data validated: %d countries, %d rows, %d warnings.",
             df["country"].nunique(), len(df), len(report))
    return report


# --------------------------------------------------------------------------- #
# Derived metrics and normalisation                                           #
# --------------------------------------------------------------------------- #

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def country_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per country with coordinates and Corbion/BioMar flags."""
    meta = df[df["metric_id"].isin(META_METRICS)].pivot(index="country", columns="metric_id", values="raw_value")
    meta["iso3"] = df.groupby("country")["iso3"].first()
    for flag in ["meta_corbion_manufacturing", "meta_biomar_manufacturing"]:
        meta[flag] = meta.get(flag, pd.Series(0, index=meta.index)).fillna(0).astype(int)
    return meta


def add_derived_metrics(df: pd.DataFrame, distance_mode: str = DEFAULT_DISTANCE_MODE) -> pd.DataFrame:
    """Append the distance-to-priority-markets metric computed from port coordinates.

    Mean great-circle distance from the country's main export port to Shanghai,
    Ho Chi Minh City and Puerto Montt (a transparent freight proxy; sea routes are
    longer). ``export_only`` leaves the country's own market out of the average,
    ``include_domestic`` counts it as 0 km (v1).
    """
    if distance_mode not in DISTANCE_MODES:
        raise DataValidationError(f"distance_mode must be one of {DISTANCE_MODES}")
    meta = country_metadata(df)
    rows = []
    for country, m in meta.iterrows():
        dists = {}
        for iso, (_, lat, lon) in PRIORITY_MARKETS.items():
            if m["iso3"] == iso:
                if distance_mode == "include_domestic":
                    dists[iso] = 0.0
                continue
            dists[iso] = haversine_km(m["meta_port_lat"], m["meta_port_lon"], lat, lon)
        label = ("export markets only (own market excluded)" if distance_mode == "export_only"
                 else "domestic market = 0 km")
        rows.append(dict(
            country=country, iso3=m["iso3"], metric_id="ma_distance_priority_markets",
            raw_value=round(float(np.mean(list(dists.values()))), 0), unit="km (mean great-circle)",
            reference_year=2026,
            source_name=f"Derived: great-circle distance from main port to priority markets; {label}",
            source_url="", date_accessed="", value_type="proxy", confidence="Medium",
            notes=" / ".join(f"{PRIORITY_MARKETS[i][0]}: {d:,.0f} km" for i, d in dists.items())))
    return pd.concat([df, pd.DataFrame(rows)], ignore_index=True)


def normalize_metric(values: pd.Series, spec: MetricSpec) -> pd.Series:
    """Convert raw values of one metric into 0-10 scores.

    * qualitative: the rubric level is the score (validated upstream).
    * linear: ``10 * (x - worst) / (best - worst)``, capped to [0, 10]. Direction
      is encoded by the goalposts (``best < worst`` means lower is better).
    * log: the same formula on log10(x), for size metrics spanning orders of
      magnitude so that one very large market cannot dominate.
    NaN stays NaN.
    """
    x = values.astype(float)
    if spec.method == "qualitative":
        return x.clip(0, 10)
    worst, best = float(spec.worst), float(spec.best)
    non_positive = x <= 0  # e.g. an explicit zero production: worst score, not missing
    if spec.method == "log":
        x = np.log10(x.where(x > 0))
        worst, best = math.log10(worst), math.log10(best)
    score = (10 * (x - worst) / (best - worst)).clip(0, 10)
    if spec.method == "log":
        score[non_positive] = 0.0
    return score


def score_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Return the long metric table with raw values, normalised scores and weights."""
    data = df[df["metric_id"].isin(METRIC_INDEX)].copy()
    countries = sorted(df["country"].unique())
    # Make absent metric rows explicit as missing so they are visible in outputs.
    full = pd.MultiIndex.from_product([countries, list(METRIC_INDEX)], names=["country", "metric_id"])
    data = data.set_index(["country", "metric_id"]).reindex(full).reset_index()
    data["value_type"] = data["value_type"].fillna("missing")
    data["confidence"] = data["confidence"].fillna("Low")
    data["normalized_score"] = np.nan
    for metric_id, spec in METRIC_INDEX.items():
        mask = data["metric_id"] == metric_id
        data.loc[mask, "normalized_score"] = normalize_metric(data.loc[mask, "raw_value"], spec)
    data["subcriterion"] = data["metric_id"].map(lambda m: METRIC_INDEX[m].subcriterion)
    data["criterion"] = data["subcriterion"].map(lambda s: SUBCRITERIA[s][0])
    data["metric_label"] = data["metric_id"].map(lambda m: METRIC_INDEX[m].label)
    data["method"] = data["metric_id"].map(lambda m: METRIC_INDEX[m].method)
    data["direction"] = data["metric_id"].map(
        lambda m: "rubric" if METRIC_INDEX[m].method == "qualitative"
        else ("higher is better" if METRIC_INDEX[m].higher_is_better else "lower is better"))
    data["goalpost_worst"] = data["metric_id"].map(lambda m: METRIC_INDEX[m].worst)
    data["goalpost_best"] = data["metric_id"].map(lambda m: METRIC_INDEX[m].best)
    data["weight_in_subcriterion"] = data["metric_id"].map(lambda m: METRIC_INDEX[m].weight)
    data["nominal_weight_base_case"] = data.apply(
        lambda r: SCENARIOS[BASE_SCENARIO][r["criterion"]] * SUBCRITERIA[r["subcriterion"]][2]
        * r["weight_in_subcriterion"], axis=1)
    return data


# --------------------------------------------------------------------------- #
# Aggregation                                                                 #
# --------------------------------------------------------------------------- #

def calculate_subcriterion_scores(metric_scores: pd.DataFrame) -> pd.DataFrame:
    """Weighted average of metric scores per sub-criterion.

    Missing metrics are dropped and the remaining weights re-normalised; the
    list of missing metrics is returned so the gap stays visible. A sub-criterion
    with no data at all is NaN.
    """
    records = []
    for (country, sub), grp in metric_scores.groupby(["country", "subcriterion"]):
        avail = grp.dropna(subset=["normalized_score"])
        w = avail["weight_in_subcriterion"].sum()
        score = (avail["normalized_score"] * avail["weight_in_subcriterion"]).sum() / w if w > 0 else np.nan
        records.append(dict(country=country, subcriterion=sub, criterion=SUBCRITERIA[sub][0],
                            subcriterion_label=SUBCRITERIA[sub][1], score=score,
                            weight_in_criterion=SUBCRITERIA[sub][2],
                            data_coverage=w,
                            missing_metrics=";".join(grp.loc[grp["normalized_score"].isna(), "metric_id"])))
    return pd.DataFrame(records)


def calculate_criterion_scores(sub_scores: pd.DataFrame) -> pd.DataFrame:
    """Weighted average of sub-criterion scores -> country x criterion table (0-10)."""
    out = {}
    for (country, crit), grp in sub_scores.groupby(["country", "criterion"]):
        avail = grp.dropna(subset=["score"])
        w = avail["weight_in_criterion"].sum()
        out[(country, crit)] = (avail["score"] * avail["weight_in_criterion"]).sum() / w if w > 0 else np.nan
    table = pd.Series(out).unstack()[list(CRITERIA)]
    table.index.name = "country"
    if table.isna().any().any():
        log.warning("Some criteria have no data at all: %s", table.isna().stack()[lambda s: s].index.tolist())
    return table


def calculate_country_score(criterion_scores: pd.DataFrame,
                            weights: dict[str, float] | None = None) -> tuple[pd.Series, pd.DataFrame]:
    """Weighted country score (0-10) and the per-criterion contributions.

    Score = 0.30 PE + 0.20 MA + 0.15 CR + 0.15 RI + 0.20 SR (Base Case).
    A criterion with no data is excluded and the weights re-normalised.
    """
    weights = weights or SCENARIOS[BASE_SCENARIO]
    w = pd.Series(weights)[criterion_scores.columns]
    contrib = criterion_scores.mul(w, axis=1)
    effective_w = criterion_scores.notna().mul(w, axis=1).sum(axis=1)
    score = contrib.sum(axis=1, min_count=1) / effective_w
    contrib = contrib.div(effective_w, axis=0)
    return score.rename("score"), contrib


def rank_scores(score: pd.Series) -> pd.Series:
    """Dense 1..n ranking (ties share the best rank)."""
    return score.rank(ascending=False, method="min").astype(int)


def calculate_data_confidence(metric_scores: pd.DataFrame) -> pd.DataFrame:
    """Data Confidence (0-100) per country, independent of the attractiveness score.

    Each metric earns confidence points (High 1.0 / Medium 0.67 / Low 0.33) times
    a value-type factor (reported 1.0 / estimate 0.85 / proxy 0.7 / missing 0),
    weighted by its nominal Base Case weight in the final score.
    """
    m = metric_scores.copy()
    m["quality"] = m["confidence"].map(CONFIDENCE_POINTS) * m["value_type"].map(VALUE_TYPE_FACTOR)
    m.loc[m["raw_value"].isna(), "quality"] = 0.0
    m["is_low"] = (m["confidence"] == "Low") | m["raw_value"].isna()
    rows = []
    for country, grp in m.groupby("country"):
        w = grp["nominal_weight_base_case"]
        rows.append(dict(
            country=country,
            data_confidence=round(100 * (grp["quality"] * w).sum() / w.sum(), 1),
            share_of_score_low_confidence_pct=round(100 * w[grp["is_low"]].sum() / w.sum(), 1),
            low_confidence_metrics=";".join(grp.loc[grp["is_low"], "metric_id"])))
    return pd.DataFrame(rows).set_index("country")


def assess_viability(df: pd.DataFrame, metric_scores: pd.DataFrame) -> pd.DataFrame:
    """Minimum-condition screen run before the ranking (Pass / Review / Fail).

    Countries are never dropped; the flag and its reasons travel with the results.
    """
    raw = metric_scores.pivot(index="country", columns="metric_id", values="raw_value")
    out = []
    for country, r in raw.iterrows():
        fails, reviews = [], []
        # 1. Legal possibility to produce and export
        if r.get("ri_local_production_permitting") == 0:
            fails.append("No legal route to build/operate a plant")
        elif r.get("ri_local_production_permitting", np.nan) <= 2.5:
            reviews.append("Local production permitting unfavourable")
        # 2. Water and energy at industrial scale
        ws = r.get("pe_water_stress")
        if pd.isna(ws):
            reviews.append("Water-stress data missing")
        elif ws >= 100:
            fails.append(f"Critical water stress ({ws:.0f}%)")
        elif ws >= 50:
            reviews.append(f"Medium/high national water stress ({ws:.0f}%) - site-level water rights needed")
        ep = r.get("pe_electricity_price")
        if pd.isna(ep):
            reviews.append("Electricity price missing")
        elif ep >= 0.25:
            reviews.append(f"Very high power price ({ep:.2f} USD/kWh)")
        # 3. Fermentable feedstock
        if r.get("pe_sugar_cost_position") == 0:
            fails.append("No viable fermentable feedstock")
        sp = r.get("pe_sugar_production")
        if pd.isna(sp) or sp < 1.0:
            reviews.append("No/small domestic sugar base - feedstock must be imported")
        # 4. Minimum logistics
        lpi = r.get("ma_lpi_score")
        if pd.isna(lpi) or lpi < 2.5:
            fails.append("Logistics below minimum (LPI < 2.5 or missing)")
        elif lpi < 3.0:
            reviews.append(f"Weak logistics (LPI {lpi:.1f})")
        # 5. Foreign investment possible
        if r.get("ri_trade_fdi_access") == 0:
            fails.append("Foreign investment effectively closed")
        flag = "Fail" if fails else ("Review" if reviews else "Pass")
        out.append(dict(country=country, viability_flag=flag,
                        viability_reasons="; ".join(fails + reviews) or "All minimum conditions met"))
    return pd.DataFrame(out).set_index("country")


def run_sensitivity_analysis(criterion_scores: pd.DataFrame,
                             scenarios: dict[str, dict[str, float]] = SCENARIOS) -> pd.DataFrame:
    """Score and rank every country under each weighting scenario."""
    table = pd.DataFrame(index=criterion_scores.index)
    for name, weights in scenarios.items():
        score, _ = calculate_country_score(criterion_scores, weights)
        table[f"score | {name}"] = score
        table[f"rank | {name}"] = rank_scores(score)
    rank_cols = [c for c in table if c.startswith("rank |")]
    score_cols = [c for c in table if c.startswith("score |")]
    table["best_rank"] = table[rank_cols].min(axis=1)
    table["worst_rank"] = table[rank_cols].max(axis=1)
    table["score_min"] = table[score_cols].min(axis=1)
    table["score_max"] = table[score_cols].max(axis=1)
    table["score_range"] = table["score_max"] - table["score_min"]
    table["scenarios_in_top3"] = (table[rank_cols] <= 3).sum(axis=1)
    table["robust_top3"] = table["scenarios_in_top3"] == len(scenarios)
    return table.sort_values(f"rank | {BASE_SCENARIO}")


def apply_rubric_ratings(df: pd.DataFrame, ratings_path: Path | None = DEFAULT_RATINGS
                         ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Combine several raters' rubric scores and measure their agreement.

    The score already in ``raw_country_data.csv`` counts as rater ``analyst_v1``.
    Extra raters (Corbion, AgroInsper, local experts...) go in ``rubric_ratings.csv``
    with columns ``country, metric_id, rater, score[, notes]``. The model then uses
    the median per country/metric and reports, per metric and overall: number of
    raters, exact agreement, agreement within one rubric level (2.5) and
    Krippendorff's alpha (interval). With a single rater nothing changes.
    """
    rubric_ids = [m.metric_id for m in METRICS if m.method == "qualitative"]
    base = df[df["metric_id"].isin(rubric_ids) & df["raw_value"].notna()][["country", "metric_id", "raw_value"]]
    ratings = base.rename(columns={"raw_value": "score"}).assign(rater="analyst_v1")
    if ratings_path is not None and Path(ratings_path).exists():
        extra = pd.read_csv(ratings_path, dtype={"country": str, "metric_id": str, "rater": str})
        missing_cols = {"country", "metric_id", "rater", "score"} - set(extra.columns)
        if missing_cols:
            raise DataValidationError(f"{Path(ratings_path).name} lacks columns {sorted(missing_cols)}")
        extra = extra.dropna(subset=["score"])
        extra["score"] = pd.to_numeric(extra["score"], errors="raise")
        bad = ~extra["score"].apply(lambda v: any(abs(v - l) < TOLERANCE for l in QUALITATIVE_LEVELS))
        if bad.any():
            raise DataValidationError(f"Ratings off the 0/2.5/5/7.5/10 scale: {extra[bad].to_dict('records')}")
        unknown = set(extra["metric_id"]) - set(rubric_ids)
        if unknown:
            raise DataValidationError(f"Ratings for non-rubric metrics: {sorted(unknown)}")
        ratings = pd.concat([ratings, extra[["country", "metric_id", "rater", "score"]]], ignore_index=True)
    if ratings.duplicated(["country", "metric_id", "rater"]).any():
        raise DataValidationError("A rater scored the same country/metric twice")

    n_raters = ratings["rater"].nunique()
    out = df.copy()
    if n_raters > 1:
        med = ratings.groupby(["country", "metric_id"])["score"].median()
        for (country, metric_id), value in med.items():
            mask = (out["country"] == country) & (out["metric_id"] == metric_id)
            out.loc[mask, "raw_value"] = value
            out.loc[mask, "notes"] = out.loc[mask, "notes"].astype(str) + f" | median of {n_raters} raters"

    def _agreement(grp: pd.DataFrame) -> dict:
        units = [u["score"].values for _, u in grp.groupby(["country", "metric_id"]) if len(u) > 1]
        if not units:
            return dict(n_raters=grp["rater"].nunique(), units_with_2plus=0, exact_agreement_pct=np.nan,
                        within_one_level_pct=np.nan, krippendorff_alpha_interval=np.nan)
        exact = np.mean([np.ptp(u) < TOLERANCE for u in units])
        within = np.mean([np.ptp(u) <= 2.5 + TOLERANCE for u in units])
        within_pairs = [(a - b) ** 2 for u in units for i, a in enumerate(u) for b in u[i + 1:]]
        pooled = np.concatenate(units)
        all_pairs = [(a - b) ** 2 for i, a in enumerate(pooled) for b in pooled[i + 1:]]
        d_e = np.mean(all_pairs) if all_pairs else np.nan
        alpha = 1 - np.mean(within_pairs) / d_e if d_e and d_e > 0 else np.nan
        return dict(n_raters=grp["rater"].nunique(), units_with_2plus=len(units),
                    exact_agreement_pct=round(100 * exact, 1), within_one_level_pct=round(100 * within, 1),
                    krippendorff_alpha_interval=round(alpha, 3) if pd.notna(alpha) else np.nan)

    rows = [dict(metric_id=mid, **_agreement(g)) for mid, g in ratings.groupby("metric_id")]
    rows.append(dict(metric_id="ALL_RUBRICS", **_agreement(ratings)))
    agreement = pd.DataFrame(rows)
    log.info("Rubric raters: %d (%s)", n_raters, ", ".join(sorted(ratings["rater"].unique())))
    return out, agreement


def write_ratings_template(df: pd.DataFrame, output_dir: Path) -> None:
    """Template for additional raters, pre-listing every country x rubric metric."""
    rubric_ids = [m.metric_id for m in METRICS if m.method == "qualitative"]
    rows = []
    for rater in ["corbion", "agroinsper", "local_expert"]:
        for country in sorted(df["country"].unique()):
            for mid in rubric_ids:
                rows.append(dict(country=country, metric_id=mid, rater=rater, score="",
                                 notes="0 / 2.5 / 5 / 7.5 / 10 per methodology_and_sources.md section 5"))
    pd.DataFrame(rows).to_csv(output_dir / "rubric_ratings_template.csv", index=False)


def prepare_data(data_path: Path, distance_mode: str = DEFAULT_DISTANCE_MODE,
                 ratings_path: Path | None = DEFAULT_RATINGS) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load, validate, merge raters and add derived metrics. Returns (data, quality, agreement)."""
    raw = load_country_data(data_path)
    quality = validate_input_data(raw)
    raw, agreement = apply_rubric_ratings(raw, ratings_path)
    return add_derived_metrics(raw, distance_mode), quality, agreement


def score_pipeline(data: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Deterministic scores for one data set: criterion scores + score + rank."""
    metric_scores = score_metrics(data)
    crit = calculate_criterion_scores(calculate_subcriterion_scores(metric_scores))
    score, _ = calculate_country_score(crit, weights)
    out = crit.copy()
    out["score"] = score
    out["rank"] = rank_scores(score)
    return out


def run_monte_carlo(data: pd.DataFrame, n_sims: int = MC_DEFAULT_SIMS, seed: int = SEED,
                    weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Simulate data uncertainty and report how stable each country's rank is.

    Each simulation perturbs every metric according to its confidence level:
    quantitative raw values get multiplicative lognormal noise (sigma 5% / 15% / 30%
    for High / Medium / Low) and rubric scores move one level (2.5) up or down with
    probability 10% / 25% / 40%. Missing values stay missing. Weights are held at the
    scenario values, so the simulation isolates data uncertainty from weighting choices.
    """
    weights = weights or SCENARIOS[BASE_SCENARIO]
    rng = np.random.default_rng(seed)
    ms = score_metrics(data)
    countries = sorted(ms["country"].unique())
    metric_ids = list(METRIC_INDEX)
    raw = ms.pivot(index="country", columns="metric_id", values="raw_value").loc[countries, metric_ids].values
    conf = ms.pivot(index="country", columns="metric_id", values="confidence").loc[countries, metric_ids].values
    n_c, n_m = raw.shape
    qual = np.array([METRIC_INDEX[m].method == "qualitative" for m in metric_ids])

    sigma = np.vectorize(lambda c: MC_QUANT_SIGMA.get(c, 0.30))(conf)
    p_shift = np.vectorize(lambda c: MC_RUBRIC_SHIFT_PROB.get(c, 0.40))(conf)
    sims = np.repeat(raw[None, :, :], n_sims, axis=0)
    noise = np.exp(rng.normal(0.0, 1.0, sims.shape) * sigma[None])
    u = rng.random(sims.shape)
    shift = np.where(u < p_shift[None] / 2, -2.5, np.where(u < p_shift[None], 2.5, 0.0))
    sims = np.where(qual[None, None, :], np.clip(sims + shift, 0, 10), sims * noise)

    # Vectorised normalisation (same formulas as normalize_metric).
    scores = np.empty_like(sims)
    for j, mid in enumerate(metric_ids):
        spec = METRIC_INDEX[mid]
        x = sims[:, :, j]
        if spec.method == "qualitative":
            scores[:, :, j] = np.clip(x, 0, 10)
            continue
        worst, best = float(spec.worst), float(spec.best)
        with np.errstate(divide="ignore", invalid="ignore"):
            if spec.method == "log":
                xs = np.where(x > 0, np.log10(np.where(x > 0, x, 1.0)), -np.inf)
                worst, best = math.log10(worst), math.log10(best)
            else:
                xs = x
            val = np.clip(10 * (xs - worst) / (best - worst), 0, 10)
        scores[:, :, j] = np.where(np.isnan(x), np.nan, val)

    # Aggregate: metric -> sub-criterion -> criterion -> score (missing re-weighted).
    w_metric = np.array([METRIC_INDEX[m].weight for m in metric_ids])
    subs = list(SUBCRITERIA)
    sub_idx = np.array([subs.index(METRIC_INDEX[m].subcriterion) for m in metric_ids])
    sub_scores = np.full((n_sims, n_c, len(subs)), np.nan)
    for k in range(len(subs)):
        cols = sub_idx == k
        sc = scores[:, :, cols]
        w = np.where(np.isnan(sc), 0.0, w_metric[cols])
        tot = w.sum(axis=2)
        with np.errstate(invalid="ignore"):
            sub_scores[:, :, k] = np.where(tot > 0, np.nansum(sc * w, axis=2) / np.where(tot > 0, tot, 1), np.nan)
    crits = list(CRITERIA)
    crit_scores = np.full((n_sims, n_c, len(crits)), np.nan)
    for k, c in enumerate(crits):
        cols = np.array([SUBCRITERIA[sname][0] == c for sname in subs])
        sw = np.array([SUBCRITERIA[sname][2] for sname in subs])[cols]
        sc = sub_scores[:, :, cols]
        w = np.where(np.isnan(sc), 0.0, sw)
        tot = w.sum(axis=2)
        crit_scores[:, :, k] = np.nansum(sc * w, axis=2) / np.where(tot > 0, tot, 1)
    cw = np.array([weights[c] for c in crits])
    total = (crit_scores * cw).sum(axis=2) / cw.sum()

    ranks = (-total).argsort(axis=1).argsort(axis=1) + 1
    out = pd.DataFrame({
        "country": countries,
        "score_mean": total.mean(axis=0),
        "score_p5": np.percentile(total, 5, axis=0),
        "score_p95": np.percentile(total, 95, axis=0),
        "rank_median": np.median(ranks, axis=0),
        "rank_p5": np.percentile(ranks, 5, axis=0),
        "rank_p95": np.percentile(ranks, 95, axis=0),
        "p_rank1": (ranks == 1).mean(axis=0),
        "p_top3": (ranks <= 3).mean(axis=0),
    }).set_index("country")
    pair = {}
    for a in countries:
        for b in countries:
            if a < b:
                pair[f"P({a} > {b})"] = float((total[:, countries.index(a)] > total[:, countries.index(b)]).mean())
    out.attrs["pairwise"] = pair
    out.attrs["n_sims"] = n_sims
    return out.sort_values("score_mean", ascending=False)


def thesis_weight_sweep(criterion_scores: pd.DataFrame, criterion: str,
                        grid: np.ndarray | None = None) -> pd.DataFrame:
    """Scores as one criterion's weight moves, other weights rescaled pro rata from Base Case."""
    grid = np.round(np.arange(0.05, 0.6001, 0.01), 2) if grid is None else grid
    base = SCENARIOS[BASE_SCENARIO]
    rows = []
    for w in grid:
        others = {c: v for c, v in base.items() if c != criterion}
        k = (1 - w) / sum(others.values())
        weights = {c: v * k for c, v in others.items()} | {criterion: w}
        score, _ = calculate_country_score(criterion_scores, weights)
        rows.append(pd.Series(score, name=w))
    out = pd.DataFrame(rows)
    out.index.name = f"weight_{criterion}"
    return out


def find_breakeven(sweep: pd.DataFrame, a: str, b: str) -> float | None:
    """Smallest swept weight at which country b's score reaches country a's (linear interpolation)."""
    diff = (sweep[a] - sweep[b]).values
    w = sweep.index.values
    for i in range(1, len(diff)):
        if np.sign(diff[i]) != np.sign(diff[i - 1]):
            return float(w[i - 1] + (w[i] - w[i - 1]) * diff[i - 1] / (diff[i - 1] - diff[i]))
    return None


# --------------------------------------------------------------------------- #
# Visual helpers                                                              #
# --------------------------------------------------------------------------- #

def setup_matplotlib() -> None:
    """Register Montserrat (bundled, OFL) and set slide-like defaults."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    family = "DejaVu Sans"
    if FONT_DIR.exists():
        for ttf in FONT_DIR.glob("*.ttf"):
            font_manager.fontManager.addfont(str(ttf))
        family = FONT_FAMILY
    else:
        log.warning("Montserrat not found in %s - falling back to DejaVu Sans.", FONT_DIR)
    plt.rcParams.update({
        "font.family": family, "text.color": PALETTE["text"], "axes.labelcolor": PALETTE["text"],
        "xtick.color": PALETTE["text_secondary"], "ytick.color": PALETTE["text_secondary"],
        "axes.edgecolor": PALETTE["silver"], "savefig.dpi": FIG_DPI, "figure.dpi": 100,
    })


def risk_colormap():
    """Blue (low risk) <- silver (intermediate) <- magenta (high risk), on a 0-10 SR score."""
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list(
        "strategic_risk", [(0.0, PALETTE["high_risk"]), (0.5, PALETTE["mid_risk"]), (1.0, PALETTE["low_risk"])])


def gradient_array(width: int = 1024) -> np.ndarray:
    """RGB image of the slide's horizontal navy -> near-black -> plum gradient."""
    from matplotlib.colors import to_rgb
    stops = [to_rgb(PALETTE["bg_left"]), to_rgb(PALETTE["bg_center"]), to_rgb(PALETTE["bg_right"])]
    t = np.linspace(0, 1, width)
    rgb = np.empty((1, width, 3))
    for ch in range(3):
        rgb[0, :, ch] = np.interp(t, [0, 0.5, 1], [s[ch] for s in stops])
    return rgb


def new_slide_figure(transparent: bool):
    """Create a 16:9 figure with the slide gradient (or a transparent canvas)."""
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=FIG_SIZE)
    if transparent:
        fig.patch.set_alpha(0.0)
    else:
        bg = fig.add_axes([0, 0, 1, 1], zorder=-10)
        bg.imshow(gradient_array(), aspect="auto", extent=[0, 1, 0, 1])
        bg.set_axis_off()
    return fig


def draw_header(fig, title: str = TITLE, subtitle: str = SUBTITLE) -> None:
    """Slide-style title block, left aligned like the reference slide."""
    fig.text(0.03, 0.935, title, fontsize=30, fontweight="bold", color=PALETTE["text"], va="center")
    fig.text(0.03, 0.885, subtitle, fontsize=14, color=PALETTE["text_secondary"], va="center")


def draw_source_note(fig, text: str = SOURCE_NOTE, y: float = 0.022) -> None:
    """Concise source line at the bottom of every chart."""
    fig.text(0.03, y, text, fontsize=7.6, color=PALETTE["silver"], va="center", wrap=True)


def save_figure(fig, path: Path, transparent: bool = False) -> None:
    """Save at 3840 x 2160 px (16 x 9 in @ 240 dpi)."""
    fig.savefig(path, dpi=FIG_DPI, transparent=transparent,
                facecolor="none" if transparent else fig.get_facecolor())
    log.info("Saved %s", path.relative_to(BASE_DIR) if path.is_relative_to(BASE_DIR) else path)


# --------------------------------------------------------------------------- #
# Bubble map                                                                  #
# --------------------------------------------------------------------------- #

BUBBLE_PT2_PER_POINT = 300.0  # marker area (pt^2) per score point -> area proportional to score
LABEL_DIRECTIONS = [  # (name, dx, dy) unit offsets; order = placement preference
    ("right", 1, 0), ("left", -1, 0), ("top", 0, 1), ("bottom", 0, -1),
    ("top right", 0.75, 0.75), ("top left", -0.75, 0.75),
    ("bottom right", 0.75, -0.75), ("bottom left", -0.75, -0.75),
]


def _circle_rect_overlap(cx, cy, r, x0, y0, x1, y1) -> bool:
    nx, ny = min(max(cx, x0), x1), min(max(cy, y0), y1)
    return (nx - cx) ** 2 + (ny - cy) ** 2 < r ** 2


def _rect_overlap(a, b, pad: float) -> bool:
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def place_labels(fig, ax, centers_px: np.ndarray, radii_px: np.ndarray,
                 sizes_px: list[tuple[float, float]], order: list[int]) -> list[dict]:
    """Greedy, deterministic label placement in display space.

    For each bubble (highest score first) try 8 directions at increasing
    distances and keep the first box that overlaps no bubble, no earlier label
    and stays inside the map; if none is free, keep the least-overlapping one.
    """
    ax_box = ax.get_window_extent()
    placed: list[tuple[float, float, float, float]] = []
    result: list[dict] = [dict() for _ in range(len(centers_px))]
    gap = 8 * FIG_DPI / 72 * fig.dpi / FIG_DPI
    for i in order:
        cx, cy = centers_px[i]
        w, h = sizes_px[i]
        best, best_cost = None, math.inf
        for tier, extra in enumerate([0, 30, 60, 100]):
            for name, dx, dy in LABEL_DIRECTIONS:
                d = radii_px[i] + gap + extra * fig.dpi / 100
                ax_ = cx + dx * d
                ay_ = cy + dy * d
                x0 = ax_ if dx > 0 else (ax_ - w if dx < 0 else ax_ - w / 2)
                y0 = ay_ if dy > 0 else (ay_ - h if dy < 0 else ay_ - h / 2)
                rect = (x0, y0, x0 + w, y0 + h)
                cost = 0.0
                for j, (ox, oy) in enumerate(centers_px):
                    if _circle_rect_overlap(ox, oy, radii_px[j] + 2, *rect):
                        cost += 10
                for other in placed:
                    if _rect_overlap(rect, other, pad=4):
                        cost += 10
                if rect[0] < ax_box.x0 or rect[2] > ax_box.x1 or rect[1] < ax_box.y0 or rect[3] > ax_box.y1:
                    cost += 5
                cost += tier * 0.5
                if cost < best_cost:
                    best, best_cost = (name, rect, tier), cost
            if best_cost < 1:
                break
        name, rect, tier = best
        placed.append(rect)
        result[i] = dict(direction=name, rect=rect, tier=tier)
    return result


def create_bubble_map(results: pd.DataFrame, meta: pd.DataFrame, output_dir: Path,
                      plotly_static: bool = False) -> None:
    """Main visual: world bubble map (interactive HTML + 16:9 PNGs).

    Bubble area = Base Case score; colour = Strategic Risk score (blue low risk,
    silver intermediate, magenta high risk); white outline = Corbion manufacturing;
    thick white outline + dashed ring = top 3; silver star = BioMar manufacturing.
    """
    directions = _create_bubble_map_matplotlib(results, meta, output_dir / "microalgae_bubble_map.png", False)
    _create_bubble_map_matplotlib(results, meta, output_dir / "microalgae_bubble_map_transparent.png", True)
    _create_bubble_map_plotly(results, meta, directions, output_dir, plotly_static)


def _create_bubble_map_matplotlib(results: pd.DataFrame, meta: pd.DataFrame, path: Path,
                                  transparent: bool) -> dict[str, str]:
    import geopandas as gpd
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.lines import Line2D
    from pyproj import Transformer

    crs = "ESRI:54030"  # Robinson
    world = gpd.read_file(WORLD_GEOJSON)
    world = world[world["NAME"] != "Antarctica"].to_crs(crs)
    to_rob = Transformer.from_crs("EPSG:4326", crs, always_xy=True)

    fig = new_slide_figure(transparent)
    draw_header(fig)
    ax = fig.add_axes([0.01, 0.13, 0.98, 0.72])
    ax.set_axis_off()
    focus = world["ISO_A3"].isin(meta["iso3"])
    world[~focus].plot(ax=ax, color=PALETTE["land"], edgecolor=PALETTE["land_edge"], linewidth=0.35)
    world[focus].plot(ax=ax, color=PALETTE["land_focus"], edgecolor="#3B4685", linewidth=0.6)
    # Vertical extent is fixed; horizontal extent follows the 16:9 axes so the
    # map fills the frame without distortion.
    _, y0 = to_rob.transform(0, -47)
    _, y1 = to_rob.transform(0, 57)
    xc, _ = to_rob.transform(17, 0)
    ax_w, ax_h = 0.98 * FIG_SIZE[0], 0.72 * FIG_SIZE[1]
    half_w = (y1 - y0) * ax_w / ax_h / 2
    ax.set_xlim(xc - half_w, xc + half_w)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal", adjustable="box")

    df = results.join(meta[["meta_display_lat", "meta_display_lon", "meta_corbion_manufacturing",
                            "meta_biomar_manufacturing"]])
    xs, ys = to_rob.transform(df["meta_display_lon"].values, df["meta_display_lat"].values)
    sizes = BUBBLE_PT2_PER_POINT * df["score"].values
    cmap, norm = risk_colormap(), Normalize(0, 10)
    top3 = df["rank"] <= 3
    corbion = df["meta_corbion_manufacturing"] == 1
    # Base edge: subtle; Corbion: white; Top 3: thick white (+ dashed ring below).
    edge_c = np.where(corbion | top3, PALETTE["text"], PALETTE["border"])
    edge_w = np.where(top3, 3.6, np.where(corbion, 1.8, 0.6))
    draw_order = np.argsort(-sizes)  # small bubbles on top
    ax.scatter(xs[draw_order], ys[draw_order], s=sizes[draw_order],
               c=cmap(norm(df["strategic_risk"].values[draw_order])),
               edgecolors=edge_c[draw_order], linewidths=edge_w[draw_order], alpha=0.95, zorder=5)
    radii_pt = np.sqrt(sizes / math.pi)
    ring = (2 * (radii_pt + 6)) ** 2
    ax.scatter(xs[top3.values], ys[top3.values], s=ring[top3.values], facecolors="none",
               edgecolors=PALETTE["text"], linewidths=1.1, linestyles=(0, (3, 2.5)), zorder=4)

    # BioMar star at the upper-right rim of the bubble.
    from matplotlib.transforms import offset_copy
    for k, (x, y) in enumerate(zip(xs, ys)):
        if df["meta_biomar_manufacturing"].iloc[k] == 1:
            off = radii_pt[k] * 0.72
            tr = offset_copy(ax.transData, fig=fig, x=off, y=off, units="points")
            ax.scatter([x], [y], s=190, marker="*", color=PALETTE["text_secondary"],
                       edgecolors=PALETTE["bg_center"], linewidths=0.6, transform=tr, zorder=7)

    # Labels: name (semibold) over score (bold); top 3 carry their rank.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    names, scores_txt, sizes_px = [], [], []
    for k, (country, row) in enumerate(df.iterrows()):
        label = f"{int(row['rank'])}. {country}" if row["rank"] <= 3 else country
        t1 = ax.text(0, 0, label, fontsize=12.5, fontweight="semibold", color=PALETTE["text"], zorder=8)
        t2 = ax.text(0, 0, f"{row['score']:.1f}", fontsize=15, fontweight="bold", color=PALETTE["text"], zorder=8)
        b1, b2 = t1.get_window_extent(renderer), t2.get_window_extent(renderer)
        names.append(t1)
        scores_txt.append(t2)
        sizes_px.append((max(b1.width, b2.width), b1.height + b2.height))
    centers = ax.transData.transform(np.column_stack([xs, ys]))
    radii_px = radii_pt * fig.dpi / 72 + edge_w * fig.dpi / 72
    order = list(np.argsort(-df["score"].values))
    placement = place_labels(fig, ax, centers, radii_px, sizes_px, order)
    inv = ax.transData.inverted()
    directions = {}
    for k, country in enumerate(df.index):
        x0p, y0p, x1p, y1p = placement[k]["rect"]
        direction = placement[k]["direction"]
        directions[country] = direction
        ha = "left" if "right" in direction else ("right" if "left" in direction else "center")
        xa = {"left": x0p, "right": x1p, "center": (x0p + x1p) / 2}[ha]
        ymid = y0p + sizes_px[k][1] - names[k].get_window_extent(renderer).height
        names[k].set_position(inv.transform((xa, ymid)))
        names[k].set_ha(ha)
        names[k].set_va("bottom")
        scores_txt[k].set_position(inv.transform((xa, ymid)))
        scores_txt[k].set_ha(ha)
        scores_txt[k].set_va("top")
        if placement[k]["tier"] > 0:  # leader line for displaced labels
            cx, cy = centers[k]
            tx = min(max(cx, x0p), x1p)
            ty = min(max(cy, y0p), y1p)
            vec = np.array([tx - cx, ty - cy])
            start = centers[k] + vec / (np.linalg.norm(vec) + 1e-9) * radii_px[k]
            ax.plot(*inv.transform(np.array([start, (tx, ty)])).T, color=PALETTE["silver"],
                    linewidth=0.8, zorder=6)

    _draw_map_legend(fig, cmap)
    draw_source_note(fig)
    save_figure(fig, path, transparent)
    plt.close(fig)
    return directions


def create_clean_map(results: pd.DataFrame, meta: pd.DataFrame, output_dir: Path) -> None:
    """Slide-insert version of the map: transparent background, no title, legend or notes.

    White bubbles whose opacity (and area) grow with the Base Case score, so a
    brighter white means a better location; only the #1 country is highlighted
    (thick outline + dashed ring, as in the slide's dashed boxes). Writes one
    version with country/score labels and one with bubbles only.
    """
    import geopandas as gpd
    import matplotlib.pyplot as plt
    from pyproj import Transformer

    crs = "ESRI:54030"  # Robinson
    world = gpd.read_file(WORLD_GEOJSON)
    world = world[world["NAME"] != "Antarctica"].to_crs(crs)
    to_rob = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    df = results.join(meta[["iso3", "meta_display_lat", "meta_display_lon"]])
    xs, ys = to_rob.transform(df["meta_display_lon"].values, df["meta_display_lat"].values)
    scores = df["score"].values
    lo, hi = scores.min(), scores.max()
    alpha = 0.55 + 0.45 * (scores - lo) / (hi - lo if hi > lo else 1)  # weakest 55% -> best 100% white
    sizes = BUBBLE_PT2_PER_POINT * 1.15 * scores
    best = df["rank"].values == 1
    _, y0 = to_rob.transform(0, -47)
    _, y1 = to_rob.transform(0, 57)
    xc, _ = to_rob.transform(17, 0)
    width_in, height_in = 16.0, 7.2

    for with_labels in (True, False):
        fig = plt.figure(figsize=(width_in, height_in))
        fig.patch.set_alpha(0.0)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        ax.patch.set_alpha(0.0)
        focus = world["ISO_A3"].isin(df["iso3"])
        # Land as translucent white so it sits on any part of the slide gradient.
        world[~focus].plot(ax=ax, color=(1, 1, 1, 0.16), edgecolor=(1, 1, 1, 0.32), linewidth=0.4)
        world[focus].plot(ax=ax, color=(1, 1, 1, 0.26), edgecolor=(1, 1, 1, 0.55), linewidth=0.7)
        half_w = (y1 - y0) * width_in / height_in / 2
        ax.set_xlim(xc - half_w, xc + half_w)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal", adjustable="box")

        order = np.argsort(-sizes)
        colors = [(1, 1, 1, a) for a in alpha]
        ax.scatter(xs[order], ys[order], s=sizes[order], c=[colors[i] for i in order],
                   edgecolors=[(1, 1, 1, min(1.0, a + 0.2)) for a in alpha[order]],
                   linewidths=[3.2 if best[i] else 0.8 for i in order], zorder=5)
        ring = (2 * (np.sqrt(sizes / math.pi) + 7)) ** 2
        ax.scatter(xs[best], ys[best], s=ring[best], facecolors="none", edgecolors="white",
                   linewidths=1.3, linestyles=(0, (3, 2.5)), zorder=4)

        if with_labels:
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            names, vals, boxes = [], [], []
            for k, (country, row) in enumerate(df.iterrows()):
                bold = best[k]
                t1 = ax.text(0, 0, country, fontsize=15 if bold else 13,
                             fontweight="bold" if bold else "semibold", color="white", zorder=8)
                t2 = ax.text(0, 0, f"{row['score']:.1f}", fontsize=17 if bold else 14, fontweight="bold",
                             color="white" if bold else PALETTE["text_secondary"], zorder=8)
                b1, b2 = t1.get_window_extent(renderer), t2.get_window_extent(renderer)
                names.append(t1)
                vals.append(t2)
                boxes.append((max(b1.width, b2.width), b1.height + b2.height))
            centers = ax.transData.transform(np.column_stack([xs, ys]))
            radii_px = np.sqrt(sizes / math.pi) * fig.dpi / 72 + 3
            placement = place_labels(fig, ax, centers, radii_px, boxes, list(np.argsort(-scores)))
            inv = ax.transData.inverted()
            for k in range(len(df)):
                x0p, y0p, x1p, _ = placement[k]["rect"]
                d = placement[k]["direction"]
                ha = "left" if "right" in d else ("right" if "left" in d else "center")
                xa = {"left": x0p, "right": x1p, "center": (x0p + x1p) / 2}[ha]
                ymid = y0p + boxes[k][1] - names[k].get_window_extent(renderer).height
                for t, va in ((names[k], "bottom"), (vals[k], "top")):
                    t.set_position(inv.transform((xa, ymid)))
                    t.set_ha(ha)
                    t.set_va(va)

        name = "microalgae_bubble_map_clean.png" if with_labels else "microalgae_bubble_map_clean_nolabels.png"
        fig.savefig(output_dir / name, dpi=FIG_DPI, transparent=True)
        plt.close(fig)
        log.info("Saved outputs/%s", name)


def create_soft_map(results: pd.DataFrame, meta: pd.DataFrame, output_dir: Path) -> None:
    """Minimal light version of the map: blurred pale continents, soft grey bubbles, score only.

    Bubble area and grey depth both grow with the Base Case score (darker = better).
    Layers are rendered separately so that land and bubbles can be blurred while the
    numbers stay sharp. Writes a white-background PNG and a transparent one.
    """
    import io
    import geopandas as gpd
    import matplotlib.pyplot as plt
    from PIL import Image, ImageFilter
    from pyproj import Transformer

    crs = "ESRI:54030"
    world = gpd.read_file(WORLD_GEOJSON)
    world = world[world["NAME"] != "Antarctica"].to_crs(crs)
    to_rob = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
    df = results.join(meta[["meta_display_lat", "meta_display_lon"]])
    xs, ys = to_rob.transform(df["meta_display_lon"].values, df["meta_display_lat"].values)
    scores = df["score"].values
    lo, hi = scores.min(), scores.max()
    t = (scores - lo) / (hi - lo if hi > lo else 1)
    grey = 0.93 - 0.17 * t  # 0.93 (weakest) -> 0.76 (best)
    sizes = BUBBLE_PT2_PER_POINT * 1.15 * scores
    _, y0 = to_rob.transform(0, -47)
    _, y1 = to_rob.transform(0, 57)
    xc, _ = to_rob.transform(17, 0)
    width_in, height_in = 16.0, 7.2
    half_w = (y1 - y0) * width_in / height_in / 2

    def layer(draw, blur: float) -> Image.Image:
        fig = plt.figure(figsize=(width_in, height_in))
        fig.patch.set_alpha(0.0)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        ax.patch.set_alpha(0.0)
        ax.set_xlim(xc - half_w, xc + half_w)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal", adjustable="box")
        draw(fig, ax)
        buf = io.BytesIO()
        fig.savefig(buf, dpi=FIG_DPI, transparent=True)
        plt.close(fig)
        img = Image.open(io.BytesIO(buf.getvalue())).convert("RGBA")
        return img.filter(ImageFilter.GaussianBlur(blur)) if blur else img

    land = layer(lambda f, a: world.plot(ax=a, color=(0.80, 0.80, 0.84, 0.17), linewidth=0), blur=10)
    bubbles = layer(lambda f, a: a.scatter(xs, ys, s=sizes, c=[(g, g, g + 0.02, 0.85) for g in grey],
                                           linewidths=0), blur=3)

    def draw_labels(fig, ax):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        texts, boxes = [], []
        for k in range(len(df)):
            txt = ax.text(0, 0, f"{scores[k]:.1f}", fontsize=14, fontweight="semibold",
                          color=(0.70, 0.69, 0.74))
            b = txt.get_window_extent(renderer)
            texts.append(txt)
            boxes.append((b.width, b.height))
        centers = ax.transData.transform(np.column_stack([xs, ys]))
        radii_px = np.sqrt(sizes / math.pi) * fig.dpi / 72 + 6
        placement = place_labels(fig, ax, centers, radii_px, boxes, list(np.argsort(-scores)))
        inv = ax.transData.inverted()
        for k, txt in enumerate(texts):
            x0p, y0p, x1p, y1p = placement[k]["rect"]
            txt.set_position(inv.transform((x0p, (y0p + y1p) / 2)))
            txt.set_ha("left")
            txt.set_va("center")

    labels = layer(draw_labels, blur=0)
    composed = Image.alpha_composite(Image.alpha_composite(land, bubbles), labels)
    composed.save(output_dir / "microalgae_bubble_map_soft_transparent.png")
    white = Image.new("RGBA", composed.size, (255, 255, 255, 255))
    Image.alpha_composite(white, composed).convert("RGB").save(output_dir / "microalgae_bubble_map_soft.png")
    log.info("Saved outputs/microalgae_bubble_map_soft.png and _soft_transparent.png")


def _draw_map_legend(fig, cmap) -> None:
    """Bottom legend strip: size, colour, outlines, star - no boxes."""
    y = 0.085
    txt = dict(color=PALETTE["text_secondary"], fontsize=10, va="center")
    head = dict(color=PALETTE["text"], fontsize=10.5, fontweight="semibold", va="center")

    # 1) Size (same pt^2-per-point scale as the map)
    fig.text(0.03, y + 0.046, "Bubble area = overall score (Base Case, 0–10)", **head)
    lax = fig.add_axes([0.03, y - 0.032, 0.22, 0.05])
    lax.set_axis_off()
    lax.set_xlim(0, 1)
    lax.set_ylim(0, 1)
    for xpos, val in zip([0.07, 0.36, 0.69], [4, 6, 8]):
        lax.scatter([xpos], [0.5], s=BUBBLE_PT2_PER_POINT * val, facecolors="none",
                    edgecolors=PALETTE["silver"], linewidths=1.0, clip_on=False)
        lax.text(xpos + 0.085 + 0.009 * val, 0.5, f"{val}", **txt)

    # 2) Colour
    fig.text(0.30, y + 0.046, "Bubble colour = strategic risk", **head)
    cax = fig.add_axes([0.30, y - 0.004, 0.18, 0.016])
    cax.imshow(np.linspace(10, 0, 256)[None, :], aspect="auto", cmap=cmap, vmin=0, vmax=10)
    cax.set_axis_off()
    fig.text(0.30, y - 0.028, "Lower risk", color=PALETTE["text_secondary"], fontsize=9.5, va="center")
    fig.text(0.39, y - 0.028, "Intermediate", color=PALETTE["text_secondary"], fontsize=9.5, va="center",
             ha="center")
    fig.text(0.48, y - 0.028, "Higher risk", color=PALETTE["text_secondary"], fontsize=9.5, va="center", ha="right")

    # 3) Outlines and star, one per line
    kax = fig.add_axes([0.55, y - 0.05, 0.25, 0.10])
    kax.set_axis_off()
    kax.set_xlim(0, 1)
    kax.set_ylim(0, 1)
    rows = [0.84, 0.5, 0.16]
    kax.scatter([0.03], [rows[0]], s=150, facecolors=PALETTE["silver"], edgecolors=PALETTE["text"],
                linewidths=1.8, clip_on=False)
    kax.text(0.09, rows[0], "White outline: Corbion manufacturing", **txt)
    kax.scatter([0.03], [rows[1]], s=150, facecolors=PALETTE["silver"], edgecolors=PALETTE["text"],
                linewidths=3.2, clip_on=False)
    kax.scatter([0.03], [rows[1]], s=420, facecolors="none", edgecolors=PALETTE["text"], linewidths=0.9,
                linestyles=(0, (3, 2.5)), clip_on=False)
    kax.text(0.09, rows[1], "Thick outline + dashed ring: top 3", **txt)
    kax.scatter([0.03], [rows[2]], s=200, marker="*", color=PALETTE["text_secondary"], clip_on=False)
    kax.text(0.09, rows[2], "Star: BioMar feed manufacturing", **txt)


def _create_bubble_map_plotly(results: pd.DataFrame, meta: pd.DataFrame, directions: dict[str, str],
                              output_dir: Path, plotly_static: bool) -> None:
    import plotly.graph_objects as go

    df = results.join(meta)
    # Plotted as risk level (10 - Strategic Risk score) so the colour bar reads low -> high risk left to right.
    colorscale = [[0.0, PALETTE["low_risk"]], [0.5, PALETTE["mid_risk"]], [1.0, PALETTE["high_risk"]]]
    max_px = 70
    sizeref = 2.0 * 10 / max_px ** 2
    top3 = df["rank"] <= 3
    corbion = df["meta_corbion_manufacturing"] == 1
    line_w = np.where(top3, 4, np.where(corbion, 2, 0.6))
    line_c = np.where(corbion | top3, PALETTE["text"], PALETTE["border"])
    hover = [
        (f"<b>{c}</b> — rank {int(r['rank'])}, score {r['score']:.2f}<br>"
         f"Production Economics: {r['production_economics']:.1f}<br>"
         f"Market Access: {r['market_access']:.1f}<br>"
         f"Corbion Readiness: {r['corbion_readiness']:.1f}<br>"
         f"Regulation & Incentives: {r['regulation_incentives']:.1f}<br>"
         f"Strategic Risk (10 = low risk): {r['strategic_risk']:.1f}<br>"
         f"Viability: {r['viability_flag']} — {r['viability_reasons']}<br>"
         f"Data Confidence: {r['data_confidence']:.0f}/100")
        for c, r in df.iterrows()]
    pos_map = {"right": "middle right", "left": "middle left", "top": "top center", "bottom": "bottom center",
               "top right": "top right", "top left": "top left", "bottom right": "bottom right",
               "bottom left": "bottom left"}
    fig = go.Figure()
    fig.add_trace(go.Choropleth(
        locations=df["iso3"], z=[1] * len(df), colorscale=[[0, PALETTE["land_focus"]], [1, PALETTE["land_focus"]]],
        showscale=False, marker_line_color="#3B4685", marker_line_width=0.6, hoverinfo="skip"))
    fig.add_trace(go.Scattergeo(
        lon=df["meta_display_lon"], lat=df["meta_display_lat"], mode="markers+text",
        text=[f"{(str(int(r['rank'])) + '. ') if r['rank'] <= 3 else ''}{c}<br><b>{r['score']:.1f}</b>"
              for c, r in df.iterrows()],
        textposition=[pos_map[directions.get(c, 'right')] for c in df.index],
        textfont=dict(family="Montserrat, Arial, sans-serif", size=13, color=PALETTE["text"]),
        marker=dict(size=df["score"], sizemode="area", sizeref=sizeref, color=10 - df["strategic_risk"],
                    colorscale=colorscale, cmin=0, cmax=10, opacity=0.95,
                    line=dict(color=line_c, width=line_w),
                    colorbar=dict(title=dict(text="Strategic risk", font=dict(color=PALETTE["text"])),
                                  orientation="h", x=0.84, y=-0.035, len=0.28, thickness=10,
                                  tickvals=[0, 5, 10], ticktext=["Lower risk", "Intermediate", "Higher risk"],
                                  tickfont=dict(color=PALETTE["text_secondary"]), outlinewidth=0)),
        hovertext=hover, hoverinfo="text", name="Country (area = score)"))
    fig.add_trace(go.Scattergeo(
        lon=df.loc[top3, "meta_display_lon"], lat=df.loc[top3, "meta_display_lat"], mode="markers",
        marker=dict(size=np.sqrt(2 * df.loc[top3, "score"] / sizeref) + 16, symbol="circle-open",
                    color=PALETTE["text"], line=dict(width=1.2)),
        hoverinfo="skip", name="Top 3 (Base Case)"))
    bm = df[df["meta_biomar_manufacturing"] == 1]
    fig.add_trace(go.Scattergeo(
        lon=bm["meta_display_lon"] + 2.8, lat=bm["meta_display_lat"] + 2.8, mode="markers",
        marker=dict(symbol="star", size=13, color=PALETTE["text_secondary"]),
        hoverinfo="skip", name="BioMar feed manufacturing"))
    fig.add_trace(go.Scattergeo(lon=[None], lat=[None], mode="markers", name="Corbion manufacturing (white outline)",
                                marker=dict(size=12, color=PALETTE["silver"], line=dict(color="white", width=2))))
    fig.update_geos(projection_type="robinson", showland=True, landcolor=PALETTE["land"],
                    showcountries=True, countrycolor=PALETTE["land_edge"], showcoastlines=False,
                    showocean=False, showlakes=False, showframe=False, bgcolor="rgba(0,0,0,0)",
                    lataxis_range=[-47, 58], lonaxis_range=[-130, 170])
    fig.update_layout(
        title=dict(text=f"<b>{TITLE}</b><br><span style='font-size:15px;color:{PALETTE['text_secondary']}'>"
                        f"{SUBTITLE}</span>", x=0.02, y=0.96, font=dict(size=28, color=PALETTE["text"])),
        font=dict(family="Montserrat, Arial, sans-serif", color=PALETTE["text"]),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=110, b=120), height=920, width=1600,
        legend=dict(orientation="h", x=0.0, y=-0.02, font=dict(color=PALETTE["text_secondary"], size=11),
                    entrywidth=270, entrywidthmode="pixels",
                    bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=PALETTE["panel"], font=dict(color=PALETTE["text"])),
        annotations=[dict(text=SOURCE_NOTE.replace("; S&P.", "; S&P.<br>"), x=0.0, y=-0.12, xref="paper", yref="paper", showarrow=False,
                          align="left", font=dict(size=10, color=PALETTE["silver"]))])
    body = fig.to_html(full_html=False, include_plotlyjs=True, config={"displaylogo": False, "responsive": True})
    geo_assets = ""
    if PLOTLY_TOPOJSON.exists():  # plotly.js reads window.PlotlyGeoAssets before fetching from its CDN
        geo_assets = ("<script>window.PlotlyGeoAssets={topojson:{world_110m:"
                      + PLOTLY_TOPOJSON.read_text(encoding="utf-8") + "}};</script>")
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Microalgae Site Selection</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
<style>
 html{{background:{PALETTE['bg_center']}}}
 body{{margin:0;min-height:100vh;background:linear-gradient(90deg,{PALETTE['bg_left']} 0%,{PALETTE['bg_center']} 50%,{PALETTE['bg_right']} 100%);
 color:{PALETTE['text']};font-family:Montserrat,Arial,sans-serif}}
 .wrap{{max-width:1640px;margin:0 auto;padding:16px}}
</style>{geo_assets}</head><body><div class="wrap">{body}</div></body></html>"""
    path = output_dir / "microalgae_bubble_map.html"
    path.write_text(html, encoding="utf-8")
    log.info("Saved %s", path.name)
    if plotly_static:
        try:
            fig.update_layout(paper_bgcolor=PALETTE["bg_center"])
            fig.write_image(output_dir / "microalgae_bubble_map_plotly.png", width=1920, height=1080, scale=2)
            log.info("Saved Plotly static image (Kaleido).")
        except Exception as exc:  # Kaleido needs Chrome and internet access for map topojson
            log.warning("Plotly static export failed (%s); Matplotlib PNGs remain the static deliverables.", exc)


# --------------------------------------------------------------------------- #
# Complementary charts                                                        #
# --------------------------------------------------------------------------- #

def _plain_axes(ax) -> None:
    for side in ["top", "right", "left", "bottom"]:
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    ax.set_facecolor("none")


def create_ranking_chart(results: pd.DataFrame, output_dir: Path) -> None:
    """Horizontal bar chart of Base Case scores with viability and data confidence."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    df = results.sort_values("rank")
    fig = new_slide_figure(False)
    draw_header(fig, "Country Ranking — Base Case",
                "Weighted score 0–10 (30% production economics, 20% market access, 15% readiness, "
                "15% regulation, 20% strategic risk)")
    ax = fig.add_axes([0.16, 0.15, 0.62, 0.67])
    _plain_axes(ax)
    y = np.arange(len(df))[::-1]
    colors = [PALETTE["low_risk"] if r <= 3 else PALETTE["silver"] for r in df["rank"]]
    ax.barh(y, df["score"], height=0.56, color=colors, zorder=3)
    for yi, (c, r) in zip(y, df.iterrows()):
        ax.text(r["score"] + 0.08, yi, f"{r['score']:.2f}", va="center", fontsize=15, fontweight="bold")
        ax.text(-0.15, yi, f"{int(r['rank'])}.  {c}", va="center", ha="right", fontsize=14,
                fontweight="semibold" if r["rank"] <= 3 else "regular")
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.7, len(df) - 0.3)
    ax.set_yticks([])
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.tick_params(axis="x", labelsize=10)
    ax.grid(axis="x", color=PALETTE["text"], alpha=0.10, linewidth=0.8, zorder=0)
    top = y[: min(3, len(y))]
    if len(top):
        ax.add_patch(FancyBboxPatch((-2.35, top.min() - 0.42), 12.5, top.max() - top.min() + 0.84,
                                    boxstyle="square,pad=0", fill=False, linestyle=(0, (4, 3)),
                                    edgecolor=PALETTE["text"], linewidth=1.1, clip_on=False))
    fig.text(0.815, 0.835, "Viability", fontsize=11, fontweight="semibold", ha="left")
    fig.text(0.895, 0.835, "Data conf.", fontsize=11, fontweight="semibold", ha="left")
    for yi, (c, r) in zip(y, df.iterrows()):
        yf = ax.transData.transform((0, yi))
        yfig = fig.transFigure.inverted().transform(yf)[1]
        fig.text(0.815, yfig, r["viability_flag"], fontsize=12, va="center", color=PALETTE["text_secondary"])
        fig.text(0.895, yfig, f"{r['data_confidence']:.0f}/100", fontsize=12, va="center",
                 color=PALETTE["text_secondary"])
    fig.text(0.16, 0.085, "Blue bars and dashed box: top 3. Viability: minimum-condition screen "
                          "(Pass / Review / Fail). Data confidence does not change the score.",
             fontsize=9.5, color=PALETTE["text_secondary"])
    draw_source_note(fig)
    save_figure(fig, output_dir / "country_ranking.png")
    plt.close(fig)


def create_score_contribution_chart(results: pd.DataFrame, contributions: pd.DataFrame, output_dir: Path) -> None:
    """Stacked bars: weighted contribution of each criterion to the Base Case score."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb
    from matplotlib.patches import Patch

    order = results.sort_values("rank").index
    contrib = contributions.loc[order]
    fig = new_slide_figure(False)
    draw_header(fig, "What Drives Each Country's Score",
                "Weighted contribution of each criterion to the Base Case score (points out of 10)")
    ax = fig.add_axes([0.16, 0.12, 0.74, 0.66])
    _plain_axes(ax)
    y = np.arange(len(order))[::-1]
    left = np.zeros(len(order))
    for crit in CRITERIA:
        vals = contrib[crit].fillna(0).values
        ax.barh(y, vals, left=left, height=0.58, color=CRITERION_COLORS[crit],
                edgecolor=PALETTE["bg_center"], linewidth=2, zorder=3)
        lum = sum(c * w for c, w in zip(to_rgb(CRITERION_COLORS[crit]), (0.299, 0.587, 0.114)))
        for yi, l, v in zip(y, left, vals):
            if v >= 0.42:
                ax.text(l + v / 2, yi, f"{v:.1f}", ha="center", va="center", fontsize=11, fontweight="semibold",
                        color=PALETTE["bg_center"] if lum > 0.6 else PALETTE["text"], zorder=4)
        left += vals
    for yi, c, total in zip(y, order, left):
        ax.text(total + 0.1, yi, f"{total:.2f}", va="center", fontsize=14, fontweight="bold")
        ax.text(-0.15, yi, f"{int(results.loc[c, 'rank'])}.  {c}", va="center", ha="right", fontsize=14)
    ax.set_xlim(0, 10)
    ax.set_yticks([])
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.grid(axis="x", color=PALETTE["text"], alpha=0.10, linewidth=0.8, zorder=0)
    w = SCENARIOS[BASE_SCENARIO]
    handles = [Patch(color=CRITERION_COLORS[c], label=f"{CRITERIA[c]} ({w[c]:.0%})") for c in CRITERIA]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.16, 0.845), ncol=5, frameon=False,
               fontsize=11, handlelength=1.2, columnspacing=1.6, labelcolor=PALETTE["text_secondary"])
    draw_source_note(fig)
    save_figure(fig, output_dir / "score_contribution.png")
    plt.close(fig)


def create_sensitivity_chart(sensitivity: pd.DataFrame, output_dir: Path) -> None:
    """Rank of each country under the three weighting scenarios (bump chart)."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    names = list(SCENARIOS)
    n = len(sensitivity)
    fig = new_slide_figure(False)
    draw_header(fig, "Ranking Robustness Across Weighting Scenarios",
                "Rank and score under Base Case, Lowest-Cost Production and Asian Market Expansion weights")
    ax = fig.add_axes([0.20, 0.12, 0.60, 0.68])
    _plain_axes(ax)
    xs = np.arange(len(names))
    ax.add_patch(Rectangle((-0.12, 0.5), len(names) - 1 + 0.24, 3.0, fill=False, linestyle=(0, (4, 3)),
                           edgecolor=PALETTE["text"], linewidth=1.0, zorder=1))
    ax.text(0.5, 3.42, "Top 3", ha="center", va="bottom", fontsize=10, color=PALETTE["text_secondary"])
    for c, r in sensitivity.iterrows():
        ranks = [r[f"rank | {s}"] for s in names]
        scores = [r[f"score | {s}"] for s in names]
        robust = bool(r["robust_top3"])
        color = PALETTE["low_risk"] if robust else PALETTE["silver"]
        ax.plot(xs, ranks, color=color, linewidth=3.2 if robust else 1.8, alpha=1 if robust else 0.75, zorder=3)
        ax.scatter(xs, ranks, s=150, color=color, edgecolors=PALETTE["bg_center"], linewidths=2, zorder=4)
        for xi, rk, sc in zip(xs, ranks, scores):
            ax.text(xi, rk - 0.28, f"{sc:.2f}", ha="center", va="bottom", fontsize=9.5,
                    color=PALETTE["text_secondary"], zorder=5)
        weight = "bold" if robust else "regular"
        ax.text(-0.18, ranks[0], f"{c}", ha="right", va="center", fontsize=13, fontweight=weight)
        ax.text(xs[-1] + 0.18, ranks[-1], f"{c}", ha="left", va="center", fontsize=13, fontweight=weight)
    ax.set_ylim(n + 0.6, 0.4)
    ax.set_xlim(-0.35, len(names) - 0.65)
    ax.set_xticks(xs)
    ax.set_xticklabels(names, fontsize=12, color=PALETTE["text"], fontweight="semibold")
    ax.xaxis.tick_top()
    ax.set_yticks(range(1, n + 1))
    ax.set_yticklabels([f"#{i}" for i in range(1, n + 1)], fontsize=11)
    ax.tick_params(axis="y", pad=110)
    fig.text(0.20, 0.085, "Blue lines: countries in the top 3 under all three scenarios (robust choices). "
                          "Numbers above markers: scenario score (0–10).",
             fontsize=9.5, color=PALETTE["text_secondary"])
    draw_source_note(fig)
    save_figure(fig, output_dir / "ranking_sensitivity.png")
    plt.close(fig)


def create_thesis_chart(sweeps: dict[str, pd.DataFrame], results: pd.DataFrame, output_dir: Path) -> None:
    """Score vs weight of Market Access and of Production Economics (thesis choice)."""
    import matplotlib.pyplot as plt

    fig = new_slide_figure(False)
    draw_header(fig, "Which Thesis Decides Brazil vs Thailand?",
                "Base Case score as one criterion's weight changes (other weights rescaled pro rata)")
    top = list(results.sort_values("rank").index[:5])
    panels = [("market_access", "Market Access weight (Asia thesis)"),
              ("production_economics", "Production Economics weight (cost thesis)")]
    for k, (crit, label) in enumerate(panels):
        ax = fig.add_axes([0.06 + k * 0.48, 0.16, 0.40, 0.62])
        _plain_axes(ax)
        sweep = sweeps[crit]
        span = sweep[top].values.max() - sweep[top].values.min()
        ends = sorted(((sweep[c].iloc[-1], c) for c in top))
        label_y, last = {}, -np.inf
        for yv, c in ends:  # nudge end labels apart (min gap 5% of range)
            label_y[c] = max(yv, last + 0.05 * span)
            last = label_y[c]
        for c in top:
            hi = c in ("Brazil", "Thailand")
            color = {"Brazil": PALETTE["text"], "Thailand": PALETTE["low_risk"]}.get(c, PALETTE["silver"])
            ax.plot(sweep.index * 100, sweep[c], color=color, linewidth=3 if hi else 1.4, alpha=1 if hi else 0.6)
            ax.text(sweep.index[-1] * 100 + 0.8, label_y[c], c, va="center", fontsize=11,
                    fontweight="bold" if hi else "regular", color=color)
        base_w = SCENARIOS[BASE_SCENARIO][crit] * 100
        ax.axvline(base_w, color=PALETTE["silver"], linestyle=(0, (3, 3)), linewidth=1)
        ax.text(base_w, ax.get_ylim()[1], " Base Case", fontsize=10, color=PALETTE["text_secondary"], va="top")
        be = find_breakeven(sweep, "Brazil", "Thailand")
        if be is not None:
            ax.axvline(be * 100, color=PALETTE["low_risk"], linewidth=1.4)
            ax.text(be * 100, ax.get_ylim()[0], f" Thailand = Brazil at {be:.0%}", fontsize=11,
                    color=PALETTE["text"], va="bottom", fontweight="semibold")
        ax.set_xlabel(label, fontsize=12, color=PALETTE["text"])
        ax.tick_params(labelsize=10)
        ax.grid(axis="y", color=PALETTE["text"], alpha=0.10)
        ax.set_xlim(sweep.index[0] * 100, sweep.index[-1] * 100 + 9)
    draw_source_note(fig)
    save_figure(fig, output_dir / "thesis_weight_sweep.png")
    plt.close(fig)


def create_monte_carlo_chart(mc_v1: pd.DataFrame, mc_v2: pd.DataFrame, output_dir: Path) -> None:
    """P(top 3) before and after the data corrections."""
    import matplotlib.pyplot as plt

    order = mc_v2.sort_values("p_top3", ascending=True).index
    fig = new_slide_figure(False)
    draw_header(fig, "How Often Each Country Lands in the Top 3",
                f"Monte Carlo on data uncertainty ({mc_v2.attrs.get('n_sims', 0):,} runs, Base Case weights): "
                "v1 data vs corrected v2 data")
    ax = fig.add_axes([0.16, 0.13, 0.70, 0.68])
    _plain_axes(ax)
    y = np.arange(len(order))
    ax.barh(y + 0.2, mc_v1.loc[order, "p_top3"] * 100, height=0.36, color=PALETTE["silver"], label="v1 data")
    ax.barh(y - 0.2, mc_v2.loc[order, "p_top3"] * 100, height=0.36, color=PALETTE["low_risk"], label="v2 data")
    for yi, c in zip(y, order):
        ax.text(-1.5, yi, c, ha="right", va="center", fontsize=14)
        ax.text(mc_v2.loc[c, "p_top3"] * 100 + 1, yi - 0.2, f"{mc_v2.loc[c, 'p_top3']:.0%}", va="center",
                fontsize=12, fontweight="bold")
        ax.text(mc_v1.loc[c, "p_top3"] * 100 + 1, yi + 0.2, f"{mc_v1.loc[c, 'p_top3']:.0%}", va="center",
                fontsize=10, color=PALETTE["text_secondary"])
    ax.set_xlim(0, 108)
    ax.set_yticks([])
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=10)
    ax.grid(axis="x", color=PALETTE["text"], alpha=0.10)
    ax.legend(loc="lower right", frameon=False, fontsize=12, labelcolor=PALETTE["text_secondary"])
    draw_source_note(fig)
    save_figure(fig, output_dir / "monte_carlo_top3.png")
    plt.close(fig)


def create_ranking_table(results: pd.DataFrame, output_dir: Path) -> None:
    """Slide-style table image with the full ranking and criterion scores."""
    import matplotlib.pyplot as plt

    df = results.sort_values("rank")
    cols = ["Rank", "Country", "Score", "Prod. Econ.", "Market", "Readiness", "Regulation",
            "Strat. Risk*", "Viability", "Data conf."]
    xpos = [0.03, 0.08, 0.24, 0.33, 0.43, 0.52, 0.62, 0.72, 0.82, 0.92]
    fig = new_slide_figure(False)
    draw_header(fig, "Full Ranking — Base Case", "Criterion scores 0–10; *Strategic Risk: 10 = lowest risk")
    top, row_h = 0.79, 0.075
    for x, c in zip(xpos, cols):
        fig.text(x, top, c, fontsize=12, fontweight="bold", va="center")
    fig.add_artist(plt.Line2D([0.03, 0.97], [top - 0.03, top - 0.03], color=PALETTE["border"], linewidth=1))
    for i, (c, r) in enumerate(df.iterrows()):
        yy = top - 0.07 - i * row_h
        vals = [f"{int(r['rank'])}", c, f"{r['score']:.2f}", f"{r['production_economics']:.1f}",
                f"{r['market_access']:.1f}", f"{r['corbion_readiness']:.1f}", f"{r['regulation_incentives']:.1f}",
                f"{r['strategic_risk']:.1f}", r["viability_flag"], f"{r['data_confidence']:.0f}"]
        for j, (x, v) in enumerate(zip(xpos, vals)):
            fig.text(x, yy, v, fontsize=13, va="center",
                     fontweight="bold" if j in (1, 2) and r["rank"] <= 3 else "regular",
                     color=PALETTE["text"] if j < 3 else PALETTE["text_secondary"])
        if r["rank"] == 3:
            fig.add_artist(plt.Line2D([0.03, 0.97], [yy - row_h / 2, yy - row_h / 2], color=PALETTE["text"],
                                      linewidth=1, linestyle=(0, (4, 3))))
    draw_source_note(fig)
    save_figure(fig, output_dir / "ranking_table.png")
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Export                                                                      #
# --------------------------------------------------------------------------- #

def write_template(output_dir: Path) -> None:
    """Blank template listing every metric needed to add a country."""
    rows = []
    for mid in META_METRICS + [m.metric_id for m in METRICS if m.metric_id not in DERIVED_METRICS]:
        spec = METRIC_INDEX.get(mid)
        rows.append(dict(country="<Country>", iso3="<ISO3>", metric_id=mid, raw_value="", unit="",
                         reference_year="", source_name="", source_url="", date_accessed="",
                         value_type="reported|estimate|proxy|missing", confidence="High|Medium|Low",
                         notes=(f"{spec.label}; method={spec.method}"
                                + ("; allowed 0/2.5/5/7.5/10" if spec and spec.method == "qualitative" else "")
                                if spec else "metadata")))
    pd.DataFrame(rows, columns=REQUIRED_COLUMNS).to_csv(output_dir / "country_data_template.csv", index=False)


def export_results(output_dir: Path, results: pd.DataFrame, metric_scores: pd.DataFrame,
                   sub_scores: pd.DataFrame, sensitivity: pd.DataFrame, quality: pd.DataFrame) -> None:
    """Write every layer of the calculation to CSV for audit."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cols = (["rank", "score", "viability_flag", "viability_reasons", "data_confidence",
             "share_of_score_low_confidence_pct"] + list(CRITERIA)
            + [f"contribution_{c}" for c in CRITERIA] + ["missing_metrics", "low_confidence_metrics"])
    out = results.sort_values("rank")[cols].copy()
    out.insert(0, "country", out.index)
    num = out.select_dtypes("number").columns.drop("rank")
    out[num] = out[num].round(3)
    out.to_csv(output_dir / "country_scores.csv", index=False)
    sens = sensitivity.copy()
    sens[sens.select_dtypes("float").columns] = sens.select_dtypes("float").round(3)
    sens.insert(0, "country", sens.index)
    sens.to_csv(output_dir / "sensitivity_analysis.csv", index=False)
    ms = metric_scores[["country", "criterion", "subcriterion", "metric_id", "metric_label", "raw_value", "unit",
                        "reference_year", "method", "direction", "goalpost_worst", "goalpost_best",
                        "normalized_score", "weight_in_subcriterion", "nominal_weight_base_case",
                        "value_type", "confidence", "source_name", "source_url", "notes"]].copy()
    ms["normalized_score"] = ms["normalized_score"].round(3)
    ms.sort_values(["country", "criterion", "subcriterion", "metric_id"]).to_csv(
        output_dir / "metric_scores.csv", index=False)
    ss = sub_scores.copy()
    ss["score"] = ss["score"].round(3)
    ss.to_csv(output_dir / "subcriterion_scores.csv", index=False)
    quality.to_csv(output_dir / "data_quality_report.csv", index=False)
    write_template(output_dir)
    log.info("CSV outputs written to %s", output_dir)


# --------------------------------------------------------------------------- #
# Orchestration                                                               #
# --------------------------------------------------------------------------- #

def run(data_path: Path = DEFAULT_DATA, output_dir: Path = DEFAULT_OUTPUT, plotly_static: bool = False,
        make_charts: bool = True, distance_mode: str = DEFAULT_DISTANCE_MODE,
        ratings_path: Path | None = DEFAULT_RATINGS, mc_sims: int = MC_DEFAULT_SIMS,
        compare_path: Path | None = V1_DATA) -> pd.DataFrame:
    """Run the full pipeline and return the Base Case results table."""
    validate_weights()
    data, quality, agreement = prepare_data(data_path, distance_mode, ratings_path)
    meta = country_metadata(data)

    metric_scores = score_metrics(data)
    sub_scores = calculate_subcriterion_scores(metric_scores)
    criterion_scores = calculate_criterion_scores(sub_scores)
    score, contributions = calculate_country_score(criterion_scores)
    confidence = calculate_data_confidence(metric_scores)
    viability = assess_viability(data, metric_scores)
    sensitivity = run_sensitivity_analysis(criterion_scores)

    missing = sub_scores.groupby("country")["missing_metrics"].apply(lambda s: ";".join(x for x in s if x))
    results = criterion_scores.copy()
    results["score"] = score
    results["rank"] = rank_scores(score)
    for c in CRITERIA:
        results[f"contribution_{c}"] = contributions[c]
    results = results.join(confidence).join(viability)
    results["missing_metrics"] = missing

    output_dir.mkdir(parents=True, exist_ok=True)
    export_results(output_dir, results, metric_scores, sub_scores, sensitivity, quality)
    agreement.to_csv(output_dir / "rubric_rater_agreement.csv", index=False)
    write_ratings_template(data, output_dir)

    # Thesis: weight at which Thailand overtakes Brazil.
    sweeps = {c: thesis_weight_sweep(criterion_scores, c) for c in ("market_access", "production_economics")}
    be_rows = []
    for crit, sweep in sweeps.items():
        be = find_breakeven(sweep, "Brazil", "Thailand") if {"Brazil", "Thailand"} <= set(sweep) else None
        be_rows.append(dict(criterion=crit, base_case_weight=SCENARIOS[BASE_SCENARIO][crit],
                            breakeven_weight_thailand_equals_brazil=None if be is None else round(be, 3)))
        sweep.round(4).to_csv(output_dir / f"thesis_sweep_{crit}.csv")
    pd.DataFrame(be_rows).to_csv(output_dir / "thesis_breakeven.csv", index=False)

    # Distance-mode sensitivity (circularity check).
    alt_mode = [m for m in DISTANCE_MODES if m != distance_mode][0]
    alt_data, _, _ = prepare_data(data_path, alt_mode, ratings_path)
    alt = score_pipeline(alt_data)
    dist_cmp = pd.DataFrame({f"score | {distance_mode}": results["score"], f"rank | {distance_mode}": results["rank"],
                             f"score | {alt_mode}": alt["score"], f"rank | {alt_mode}": alt["rank"]})
    dist_cmp.sort_values(f"rank | {distance_mode}").round(3).to_csv(output_dir / "distance_mode_comparison.csv")

    # Monte Carlo before/after the data corrections.
    mc = run_monte_carlo(data, mc_sims)
    mc.round(4).to_csv(output_dir / "monte_carlo_results.csv")
    pd.Series(mc.attrs["pairwise"]).round(4).to_csv(output_dir / "monte_carlo_pairwise.csv", header=["probability"])
    mc_v1 = None
    if compare_path is not None and Path(compare_path).exists():
        v1_data, _, _ = prepare_data(compare_path, "include_domestic", None)
        v1 = score_pipeline(v1_data)
        mc_v1 = run_monte_carlo(v1_data, mc_sims)
        cmp = pd.DataFrame({"score_v1": v1["score"], "rank_v1": v1["rank"],
                            "score_v2": results["score"], "rank_v2": results["rank"],
                            "p_top3_v1": mc_v1["p_top3"], "p_top3_v2": mc["p_top3"],
                            "p_rank1_v1": mc_v1["p_rank1"], "p_rank1_v2": mc["p_rank1"]})
        cmp["score_change"] = cmp["score_v2"] - cmp["score_v1"]
        cmp.sort_values("rank_v2").round(4).to_csv(output_dir / "version_comparison.csv")

    if make_charts:
        setup_matplotlib()
        create_bubble_map(results, meta, output_dir, plotly_static)
        create_clean_map(results, meta, output_dir)
        create_soft_map(results, meta, output_dir)
        create_ranking_chart(results, output_dir)
        create_score_contribution_chart(results, contributions, output_dir)
        create_sensitivity_chart(sensitivity, output_dir)
        create_ranking_table(results, output_dir)
        create_thesis_chart(sweeps, results, output_dir)
        if mc_v1 is not None:
            create_monte_carlo_chart(mc_v1, mc, output_dir)
    summary = results.sort_values("rank")[["rank", "score", "strategic_risk", "viability_flag", "data_confidence"]]
    log.info("Base Case ranking:\n%s", summary.round(2).to_string())
    log.info("Monte Carlo (%d runs):\n%s", mc_sims, mc[["score_mean", "p_rank1", "p_top3"]].round(3).to_string())
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="raw data CSV (long format)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT, help="folder for outputs")
    parser.add_argument("--plotly-static", action="store_true",
                        help="also try a Plotly/Kaleido PNG (needs Chrome and internet for map data)")
    parser.add_argument("--no-charts", action="store_true", help="only compute and export CSVs")
    parser.add_argument("--distance-mode", choices=DISTANCE_MODES, default=DEFAULT_DISTANCE_MODE,
                        help="export_only (default) excludes each country's own market from the distance metric")
    parser.add_argument("--ratings", type=Path, default=DEFAULT_RATINGS,
                        help="optional CSV with additional rubric raters (country, metric_id, rater, score)")
    parser.add_argument("--mc-sims", type=int, default=MC_DEFAULT_SIMS, help="Monte Carlo simulations")
    parser.add_argument("--compare", type=Path, default=V1_DATA,
                        help="earlier data file to compare against (v1); pass a missing path to skip")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    try:
        run(args.data, args.output_dir, args.plotly_static, not args.no_charts, args.distance_mode,
            args.ratings, args.mc_sims, args.compare)
    except (DataValidationError, FileNotFoundError) as exc:
        log.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
