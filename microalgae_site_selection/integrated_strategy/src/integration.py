"""Adapters to the site study (v3) and the market study, harmonised parameters, reconciliation and route economics.

Nothing here re-implements either study: the market funnel comes from market_expansion/src/model.py and every
cash flow from v3/src/engine.py. This module only standardises units and joins them.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]


class IntegrationError(ValueError):
    pass


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_pkg(alias: str, src: Path):
    if alias in sys.modules:
        return sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, src / "__init__.py", submodule_search_locations=[str(src)])
    pkg = importlib.util.module_from_spec(spec)
    sys.modules[alias] = pkg
    spec.loader.exec_module(pkg)
    return pkg


class Upstream:
    """Handles to both studies' code and validated inputs."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.v3_dir = (ROOT / cfg["paths"]["v3"]).resolve()
        self.mkt_dir = (ROOT / cfg["paths"]["market"]).resolve()
        for d in (self.v3_dir, self.mkt_dir):
            if not (d / "src").exists():
                raise IntegrationError(f"upstream module missing: {d}")
        _load_pkg("v3src", self.v3_dir / "src")
        _load_pkg("mktsrc", self.mkt_dir / "src")
        self.v3d = importlib.import_module("v3src.data")
        self.v3e = importlib.import_module("v3src.engine")
        self.v3a = importlib.import_module("v3src.analysis")
        self.md = importlib.import_module("mktsrc.data")
        self.mm = importlib.import_module("mktsrc.model")
        self.mx = importlib.import_module("mktsrc.export")
        self.c3 = self.v3d.load_config()
        self.a3 = self.v3d.load_assumptions(self.c3)
        self.fr3 = self.v3d.load_freight(self.c3)
        self.p0 = self.v3d.build_params(self.c3, self.a3, self.fr3)
        self.gates = self.v3d.load_gates(self.c3)
        self.cm = self.md.load_config()
        self.dm = self.md.load_all(self.cm)

    def market_segments(self, scenario: str, ov: dict | None = None) -> pd.DataFrame:
        return self.mm.segments_df(self.cm, self.dm, scenario, ov)

    def market_demand(self, seg: pd.DataFrame, scenario: str) -> pd.DataFrame:
        dem = self.mx.demand_for_v3(self.cm, self.dm, seg, scenario)
        self.v3d.validate_demand(dem, list(self.c3["regions"]))
        return dem


def provenance(up: Upstream, run_tests: bool) -> dict:
    def commit(path):
        try:
            return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=path, text=True).strip()
        except Exception:  # noqa: BLE001
            return "unknown"

    def hashes(folder: Path, pattern: str):
        return {str(f.relative_to(folder.parent)): hashlib.sha256(f.read_bytes()).hexdigest()[:16]
                for f in sorted(folder.glob(pattern))}

    out = {"git_commit": commit(ROOT), "v3_version": up.c3["version"], "market_version": up.cm["version"],
           "v3_cutoff": up.c3["cutoff_date"], "market_cutoff": up.cm["cutoff_date"],
           "consumed_tables": {**hashes(up.v3_dir / "data" / "raw", "*.csv"),
                               **hashes(up.mkt_dir / "data" / "raw", "*.csv"),
                               **hashes(up.v3_dir / "outputs", "unit_economics.csv")}}
    if run_tests:
        for name, d in (("v3", up.v3_dir), ("market", up.mkt_dir)):
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=d, capture_output=True, text=True)
            out[f"{name}_tests"] = (r.stdout.strip().splitlines() or ["?"])[-1]
            if r.returncode != 0:
                raise IntegrationError(f"upstream tests failed in {name}: {out[f'{name}_tests']}")
    return out


def region_prices(up: Upstream, seg: pd.DataFrame, year: int = 2030) -> dict:
    """SOM-weighted net price by v3 region (USD/kg DHA, base-year USD), net of commercial cost and rebates.

    Working-capital carry is NOT deducted because the v3 engine models working capital explicitly.
    """
    A = up.dm["A"]
    deduct = A["commercial_cost_pct"]["base"] + A["rebate_pct"]["base"]
    s = seg[seg.year == year]
    out = {}
    for r in up.c3["regions"]:
        g = s[s.region == r]
        w = g.som_dha_t.sum()
        price = (g.price_usd_kg_dha * g.som_dha_t).sum() / w if w > 0 else g.price_usd_kg_dha.mean()
        out[r] = float(price * (1 - deduct))
    return out


def integrated_params(up: Upstream, cfg: dict, scenario: str = "base", seg: pd.DataFrame | None = None,
                      contracted_t: float = 0.0, asia_share: float = 0.5, weights: str | dict | None = None,
                      price_mult: float = 1.0) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """v3 parameter dict fed with the market study's demand and prices (canonical units)."""
    seg = seg if seg is not None else up.market_segments(scenario)
    dem = up.market_demand(seg, scenario)
    p = copy.deepcopy(up.p0)
    p["dha_fraction"] = cfg["dha_fraction_canonical"]
    prices = region_prices(up, seg)
    p["price_dha"] = up.dm["A"]["net_price_usd_per_kg_dha"]["base"] * price_mult
    p["price_mult"] = {r: prices[r] / up.dm["A"]["net_price_usd_per_kg_dha"]["base"] for r in p["regions"]}
    p["fish_oil"] = p["fish_oil_base"]  # fish-oil pass-through already embedded in the market price
    w = weights if isinstance(weights, dict) else p["scenario_weights"][weights or cfg["pipeline_weights"]]
    ys = [int(y) for y in up.v3e.years(p)]
    demand = up.v3d.weighted_demand(dem, w, p["regions"], ys)
    if contracted_t:
        demand = up.v3d.add_contracted(demand, contracted_t, asia_share, up.v3d.region_mix(dem, p["regions"]),
                                       p["asia_regions"], cfg["contract_start_year"])
    p["demand"] = demand
    return p, dem, seg


def reconciliation(up: Upstream, cfg: dict, p: dict, dem: pd.DataFrame, seg: pd.DataFrame) -> pd.DataFrame:
    vol = up.v3d.sku_volume(dem)
    rows = []
    for y in (2030, 2035):
        mk = up.mm.market_table(up.cm, up.dm, seg)[f"incremental_sku_{y}_t"].sum()
        ex = vol[dem.year == y].sum()
        engine_in = sum(p["demand"][r][str(y)] for r in p["regions"])
        rows.append({"item": f"Incremental demand {y}", "site_study": f"{engine_in:,.0f} t SKU (after v3 status weights)",
                     "market_study": f"{mk:,.0f} t SKU (unweighted incremental SOM)",
                     "export_file": f"{ex:,.0f} t SKU", "conversion": "v3 weights A110/A111 applied to statuses; contracted = 0",
                     "status": "consistent" if abs(mk - ex) < 1e-3 * max(mk, 1) else "MISMATCH"})
    rows += [
        {"item": "DHA per t SKU", "site_study": f"{up.p0['dha_fraction']} (A001 assay assumption)",
         "market_study": f"{up.dm['A']['dha_fraction_sku']['base']} (B002 spec minimum)", "export_file": "",
         "conversion": f"canonical {cfg['dha_fraction_canonical']} used in all integrated runs (revenue per t SKU -2.8% vs v3)",
         "status": "harmonised"},
        {"item": "Price basis", "site_study": "A040 USD 25/kg DHA x region multiplier, FCA plant; freight paid in engine",
         "market_study": "B001 USD 25/kg DHA x country multiplier x fish-oil pass-through; net of 8% commercial + 3% rebates + 2% WC carry",
         "export_file": "realized_price_currency_kg per row",
         "conversion": "integrated price = market SOM-weighted price by region net of commercial and rebates (WC modelled in v3); fish-oil pass-through applied once (v3 fish_oil set to base)",
         "status": "harmonised"},
        {"item": "Incoterm", "site_study": "Corbion pays freight, transit inventory and (if any) non-recoverable duty",
         "market_study": "contribution deducts freight from Brazil", "export_file": "",
         "conversion": "DAP-like: freight and duty deducted once in the v3 engine / route table; not in the price",
         "status": "harmonised"},
        {"item": "Currency / base year", "site_study": "nominal USD, base 2026, US inflation 2.5%",
         "market_study": "USD 2026 (real), base year 2025 for volumes", "export_file": "",
         "conversion": "market prices treated as 2026 USD and inflated by v3; volumes incremental vs 2025",
         "status": "harmonised"},
        {"item": "Variable cost", "site_study": "site-specific (sugar, utilities, nutrients) per v3",
         "market_study": "Orindiúva cost from v3 unit_economics (for ranking only)", "export_file": "",
         "conversion": "integrated uses v3 site costs for every origin", "status": "harmonised"},
        {"item": "Current Corbion volume", "site_study": "excluded (incremental only)",
         "market_study": "2025 SOM of documented markets subtracted", "export_file": "incremental only",
         "conversion": "no current sales attributed to new capacity", "status": "consistent"},
        {"item": "Customer double counting", "site_study": "demand by region", "market_study": "demand by country x niche (formulation geography); accounts are context, not added",
         "export_file": "one row per market/country/application/year/status",
         "conversion": "BioMar volume is not added to salmon farmer volume; IQI not added to brand volume", "status": "consistent"},
    ]
    return pd.DataFrame(rows)


def route_economics(up: Upstream, cfg: dict, p: dict, seg: pd.DataFrame, tariffs: pd.DataFrame,
                    years=(2030, 2035)) -> pd.DataFrame:
    """Delivered contribution per t SKU and per kg DHA for every plant x (country, niche) x year."""
    v3e = up.v3e
    A = up.dm["A"]
    deduct = A["commercial_cost_pct"]["base"] + A["rebate_pct"]["base"]
    tar = tariffs.set_index("destination_region")
    s = seg[seg.year.isin(years)].groupby(["country", "application", "region", "year"], as_index=False).agg(
        price=("price_usd_kg_dha", "first"), som_sku_t=("som_sku_t", "sum"), confidence=("confidence", "first"))
    rows = []
    for _, m in s.iterrows():
        for site, sp in p["sites"].items():
            c = sp["country"]
            y = int(m.year)
            infl = v3e.infl(p, y)
            price_t = m.price * (1 - deduct) * p["dha_fraction"] * 1000 * infl
            vc = v3e.variable_cost(p, site) * infl
            fr = p["freight"][c][m.region]
            freight = fr["usd"] * infl
            transit = price_t * fr["days"] / 365 * p["transit_rate"]
            origin_duty = 0.0 if (c == "TH" and m.region in ("SHRIMP_ASIA", "CHINA")) else tar.loc[m.region, "import_duty_on_feed_ingredient"]
            duty = origin_duty * price_t
            online = sp["first_capex"] + sp["build"]
            legal = not (m.region == "CHINA" and not sp["brownfield"])  # new plants need own GACC registration
            contrib = price_t - vc - freight - transit - duty
            rows.append({"origin_site": site, "origin_country": c, "dest_country": m.country, "niche": m.application,
                         "region": m.region, "year": y, "net_price_usd_t": price_t, "variable_cost_usd_t": vc,
                         "freight_usd_t": freight, "transit_inventory_usd_t": transit, "duty_usd_t": duty,
                         "contribution_usd_t": contrib,
                         "contribution_usd_kg_dha": contrib / (p["dha_fraction"] * 1000),
                         "transit_days": fr["days"], "incoterm": "DAP-like (Corbion pays freight/duty)",
                         "route_legal_at_start": legal,
                         "route_note": ("new plant: China only after own GACC registration "
                                        f"({sp['gacc_delay']} yr after {online})") if not legal else "",
                         "market_som_sku_t": m.som_sku_t, "volume_confidence": m.confidence,
                         "sources": "price B001/B005 (market); cost v3 A001-A008,A080-A084; freight v3 freight_lanes.csv; duty tariff_assumptions.csv (unverified)"})
    return pd.DataFrame(rows)
