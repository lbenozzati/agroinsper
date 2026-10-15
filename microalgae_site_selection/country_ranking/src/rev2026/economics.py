"""Incremental economics per site × niche × contract-renewal scenario – adapter over the v3 DCF engine.

Nothing is re-implemented: cash flows come from v3/src/engine.py (same as integrated_strategy). This adapter only
(i) sets the module timing implied by the H1-2026 call (capacity sufficient to end-2028/early-2029 → new module
online 2029), (ii) applies the end-2026 contract-renewal scenarios to price and incremental volume, (iii) filters
demand by niche, and (iv) computes the extra metrics the revision asks for.

EVERY economic output here is a SCENARIO built on v3 ASSUMPTION rows (capex intensity, yield, OEE, price, demand).
With public data only, NPV/IRR are "não estimável com dados públicos" (economics_public_only.csv).
"""

from __future__ import annotations

import copy
import importlib
import importlib.util
import sys

import numpy as np
import pandas as pd

from .common import OUT, ROOT

V3 = ROOT.parent / "v3"
NICHE_APPS = {"salmon": ["salmon"], "shrimp": ["shrimp", "shrimp/fish"], "pet": ["pet_food"]}
LABEL = "ASSUMPTION – cenário ilustrativo (premissas v3), não observado"


def _load_v3():
    alias = "v3src"
    if alias not in sys.modules:
        spec = importlib.util.spec_from_file_location(alias, V3 / "src" / "__init__.py",
                                                      submodule_search_locations=[str(V3 / "src")])
        pkg = importlib.util.module_from_spec(spec)
        sys.modules[alias] = pkg
        spec.loader.exec_module(pkg)
    return (importlib.import_module("v3src.data"), importlib.import_module("v3src.engine"),
            importlib.import_module("v3src.analysis"))


class V3Handle:
    def __init__(self, ecfg: dict):
        self.D, self.E, self.A = _load_v3()
        self.c3 = self.D.load_config()
        self.a3 = self.D.load_assumptions(self.c3)
        self.fr3 = self.D.load_freight(self.c3)
        self.p0 = self.D.build_params(self.c3, self.a3, self.fr3)
        self.demand, self.demand_origin = self.D.load_demand(self.c3, self.a3)
        for s, y in ecfg["first_capex_year"].items():
            self.p0["sites"][s]["first_capex"] = int(y)
        self.ecfg = ecfg

    def params(self, sc: dict, niche: str | None = None) -> dict:
        filt = {"application": NICHE_APPS[niche]} if niche else None
        # niche runs exclude the anchor contract (its niche is not known); the all-niche run carries it
        anchor = 0.0 if niche else float(sc.get("anchor_t", 0))
        p = self.A.params_for(self.c3, self.p0, self.demand, "base", contracted_t=anchor, asia_share=0.5,
                              filters=filt)
        p["price_dha"] *= sc["price_mult"]
        freed = float(sc.get("freed_t", 0))
        ys = [str(y) for y in self.E.years(p)]
        for y in ys:
            tot = sum(p["demand"][r][y] for r in p["regions"])
            cut = min(freed, tot) if int(y) >= 2027 else 0.0
            for r in p["regions"]:
                v = p["demand"][r][y] * sc["demand_mult"]
                p["demand"][r][y] = max(0.0, v - (cut * p["demand"][r][y] / tot if tot > 0 else 0.0))
        return p

    def alt(self, key: str) -> dict:
        return self.c3["alternatives"][key]


def metrics(h: V3Handle, p: dict, key: str, extra: bool = True) -> dict:
    E = h.E
    alt = h.alt(key)
    res = E.run_alternative(p, alt)
    s = h.A.summarize(res, p)
    site = alt["units"][0]["site"]
    c = p["sites"][site]["country"]
    w = p["country"][c]["wacc"]
    ys = res["years"]
    pv_capex = sum(res["lines"]["capex"][i] * (1 + w) ** -(y - p["base_year"] + 1) for i, y in enumerate(ys)) \
        if res["lines"] else 0.0
    eff_kg_dha = p["module_t"] * p["oee"] * p["dha_fraction"] * 1000
    capex_real = s["capex_real_musd"] * 1e6
    steady = [i for i, y in enumerate(ys) if y >= 2032]
    nopat = np.mean([res["lines"]["ebitda"][i] - res["lines"]["tax"][i] - res["lines"]["topup"][i]
                     - capex_real / p["economic_life"] for i in steady]) if res["lines"] else 0.0
    ev_project = res["npv_ex_tv"] + (-pv_capex if pv_capex < 0 else pv_capex) + res["tv_pv"]
    out = {
        "npv_musd": s["npv_musd"], "irr": s["irr"], "npv_ex_tv_musd": s["npv_ex_tv_musd"],
        "tv_pv_musd": s["tv_pv_musd"],
        "tv_share_of_npv": (s["tv_pv_musd"] / s["npv_musd"]) if abs(s["npv_musd"]) > 1e-9 else np.nan,
        "project_ev_musd": ev_project / 1e6,
        "tv_share_of_project_ev": (res["tv_pv"] / ev_project) if abs(ev_project) > 1e-9 else np.nan,
        "capex_real_musd": s["capex_real_musd"],
        "capex_usd_per_kg_dha_yr": capex_real / eff_kg_dha if eff_kg_dha else np.nan,
        "lcod_usd_per_kg_dha": s["lcod_usd_per_kg_dha"],
        "roic_steady_2032_35": nopat / capex_real if capex_real else np.nan,
        "disc_payback_year": s["disc_payback_year"], "utilisation_2030": s["utilisation_2030"],
        "utilisation_2035": s["utilisation_2035"], "sold_2035_t": s["sold_2035_t"],
        "capacity_2035_t": s["capacity_2035_t"], "peak_funding_musd": s["peak_funding_musd"],
        "online_year": min(u["online"] for u in res["units"]) if res["units"] else np.nan,
    }
    if extra:
        m = E.msp(p, alt)
        out["breakeven_price_usd_kg_dha"] = m
        bdm = E.breakeven_demand_multiplier(p, alt)
        out["breakeven_demand_multiplier"] = bdm
        out["min_utilisation_2035"] = min(1.0, s["utilisation_2035"] * bdm) if bdm is not None else np.nan
    return out


def scenario_grid(h: V3Handle) -> pd.DataFrame:
    rows = []
    for sk, sc in h.ecfg["renewal_scenarios"].items():
        for niche in [None, "salmon", "shrimp", "pet"]:
            p = h.params(sc, niche)
            for key in h.ecfg["alternatives"]:
                m = metrics(h, p, key, extra=(niche is None))
                rows.append({"renewal_scenario": sk, "scenario_label": sc["label"], "niche": niche or "todos",
                             "alternative": key, "site": h.ecfg["site_of"][key], **m, "status": LABEL})
    return pd.DataFrame(rows)


def value_of_waiting(h: V3Handle, grid: pd.DataFrame) -> pd.DataFrame:
    """Commit now (FID 2027) vs wait one year for the renewal outcome (FID 2028, build only if NPV>0).
    Scenario probabilities are EQUAL by declaration (ASSUMPTION) – no renewal outcome is observed."""
    rows = []
    scen = [k for k in h.ecfg["renewal_scenarios"] if k != "R0_base"]
    for key in h.ecfg["alternatives"]:
        site = h.ecfg["site_of"][key]
        now, wait = [], []
        for sk in scen:
            sc = h.ecfg["renewal_scenarios"][sk]
            now.append(float(grid[(grid.renewal_scenario == sk) & (grid.niche == "todos")
                                  & (grid.alternative == key)].npv_musd.iloc[0]))
            p = h.params(sc)
            p["sites"][site]["first_capex"] += 1
            wait.append(max(0.0, metrics(h, p, key, extra=False)["npv_musd"]))
        rows.append({"alternative": key, "site": site, "expected_npv_commit_now_musd": float(np.mean(now)),
                     "expected_npv_wait_1y_then_decide_musd": float(np.mean(wait)),
                     "value_of_waiting_musd": float(np.mean(wait) - max(0.0, np.mean(now))),
                     "n_scenarios": len(scen), "probabilities": "iguais (ASSUMPTION)", "status": LABEL})
    return pd.DataFrame(rows)


SENS = [  # (name, setter low, setter high, description)
    ("demanda ±30%", lambda p: _scale_demand(p, 0.7), lambda p: _scale_demand(p, 1.3)),
    ("preço DHA ±30%", lambda p: _mul(p, "price_dha", 0.7), lambda p: _mul(p, "price_dha", 1.3)),
    ("óleo de peixe 2.500/6.800 US$/t", lambda p: _set(p, "fish_oil", 2500), lambda p: _set(p, "fish_oil", 6800)),
    ("teor DHA 0,35/0,40", lambda p: _set(p, "dha_fraction", 0.35), lambda p: _set(p, "dha_fraction", 0.40)),
    ("açúcar ±30%", lambda p: _sugar(p, 1.3), lambda p: _sugar(p, 0.7)),
    ("rendimento 0,055/0,10", lambda p: _set(p, "dha_yield", 0.055), lambda p: _set(p, "dha_yield", 0.10)),
    ("OEE 0,75/0,92", lambda p: _set(p, "oee", 0.75), lambda p: _set(p, "oee", 0.92)),
    ("frete ±50%", lambda p: _freight(p, 1.5), lambda p: _freight(p, 0.5)),
    ("câmbio local +20%/−20% (custos)", lambda p: _fx(p, 0.2), lambda p: _fx(p, -0.2)),
    ("capex ±30%", lambda p: _capex(p, 1.3), lambda p: _capex(p, 0.7)),
    ("BOI 0/8 anos (TH)", lambda p: _boi(p, 0), lambda p: _boi(p, 8)),
    ("licenciamento +2/0 anos", lambda p: _delay(p, 2), lambda p: _delay(p, 0)),
]


def _mul(p, k, f):
    p[k] *= f
    return p


def _set(p, k, v):
    p[k] = v
    return p


def _scale_demand(p, m):
    p["demand"] = {r: {y: v * m for y, v in ys.items()} for r, ys in p["demand"].items()}
    return p


def _sugar(p, f):
    for s in p["sites"]:
        p["sites"][s]["sugar"] *= f
    return p


def _freight(p, f):
    for c in p["freight"]:
        for r in p["freight"][c]:
            p["freight"][c][r]["usd"] *= f
    return p


def _fx(p, x):
    p["fx_shock"] = {c: x for c in p["fx_shock"]}
    return p


def _capex(p, f):
    p["capex_mult"] = {c: f for c in p["capex_mult"]}
    return p


def _boi(p, yrs):
    p["country"]["TH"]["holiday"] = yrs
    return p


def _delay(p, yrs):
    p["delay"] = {s: yrs for s in p["sites"]}
    return p


def sensitivities(h: V3Handle) -> pd.DataFrame:
    base_sc = h.ecfg["renewal_scenarios"]["R2_renova_igual"]
    rows = []
    for key in h.ecfg["alternatives"]:
        b = metrics(h, h.params(base_sc), key, extra=False)["npv_musd"]
        for name, lo, hi in SENS:
            vlo = metrics(h, lo(copy.deepcopy(h.params(base_sc))), key, extra=False)["npv_musd"]
            vhi = metrics(h, hi(copy.deepcopy(h.params(base_sc))), key, extra=False)["npv_musd"]
            rows.append({"alternative": key, "site": h.ecfg["site_of"][key], "driver": name, "npv_base_musd": b,
                         "npv_adverse_musd": vlo, "npv_favourable_musd": vhi, "swing_musd": abs(vhi - vlo),
                         "status": LABEL})
    return pd.DataFrame(rows).sort_values(["alternative", "swing_musd"], ascending=[True, False])


def monte_carlo(h: V3Handle, n: int) -> pd.DataFrame:
    p = h.params(h.ecfg["renewal_scenarios"]["R2_renova_igual"])
    mc = h.A.run_monte_carlo(h.c3, p, n, h.c3["seed"])
    alts = h.ecfg["alternatives"]
    rows = []
    for a in alts:
        v = mc[a].to_numpy()
        rows.append({"alternative": a, "site": h.ecfg["site_of"][a], "mean_npv_musd": v.mean(),
                     "p10": np.quantile(v, .1), "p50": np.quantile(v, .5), "p90": np.quantile(v, .9),
                     "prob_npv_positive_under_assumptions": (v > 0).mean(),
                     "note": "Distribuições/correlações da v3 (config.yaml monte_carlo) – volatilidade econômica "
                             "sob premissas; NÃO inclui a incerteza epistemológica de capex/rendimento desconhecidos "
                             "além das faixas declaradas. Não é probabilidade observada.", "status": LABEL})
    return pd.DataFrame(rows)


def public_only(cfg: dict) -> pd.DataFrame:
    rows = []
    for key, site in cfg["economics"]["site_of"].items():
        for niche in ["todos", "salmon", "shrimp", "pet"]:
            rows.append({"alternative": key, "site": site, "niche": niche,
                         "npv": "não estimável com dados públicos", "irr": "não estimável com dados públicos",
                         "decisive_missing": "capex por kg/ano de DHA do site; rendimento DHA/açúcar industrial; "
                                             "preço líquido 2027+ por destino (resultado da renovação de dez/2026); "
                                             "volume contratado/pipeline qualificado por conta; custo de açúcar/vapor "
                                             "contratual; outorga de água incremental",
                         "who_holds_it": "Corbion (gestão) / usina parceira / clientes"})
    return pd.DataFrame(rows)


MGMT_FIELDS = ["site", "configuration", "entry_year", "customer", "plant", "country", "niche", "sku",
               "capex_usd", "capex_scope", "nameplate_t_sku", "effective_t_sku", "dha_fraction_assay",
               "yield_kg_dha_per_kg_sugar", "sugar_usd_t_contract", "steam_usd_t_contract", "power_usd_kwh",
               "contracted_t", "contract_price", "price_unit", "incoterm", "contract_start", "contract_end",
               "take_or_pay_t", "qualified_pipeline_t", "source_document", "as_of_date"]


def bridge(h: V3Handle, grid: pd.DataFrame) -> pd.DataFrame:
    """capacidade técnica → disponível → contratada → pipeline → utilização → EBITDA → FCF → VPL (A1, R2)."""
    r = grid[(grid.renewal_scenario == "R2_renova_igual") & (grid.niche == "todos")
             & (grid.alternative == "A1_ORI")].iloc[0]
    p = h.params(h.ecfg["renewal_scenarios"]["R2_renova_igual"])
    res = h.E.run_alternative(p, h.alt("A1_ORI"))
    i = res["years"].index(2032)
    rows = [
        ("Planta atual: tetos licenciados (LO)", "100 kt óleo / 80 kt biomassa / 20.625 t suspensão", "L1 brief",
         "NÃO é capacidade nem produção"),
        ("Planta atual: capacidade técnica", "não divulgada", "UNKNOWN", "5 fermentadores (LO, brief) vs. 'seis tanques' (analista)"),
        ("Planta atual: volume produzido/vendido", "não divulgado", "UNKNOWN", "≈2/3 em contratos longos (brief, não confirmado)"),
        ("Planta atual: folga até", "fim 2028 / início 2029", "OBSERVED (declaração)", "H1 2026 com fermentador novo em 2027"),
        ("Novo módulo: capacidade técnica (t SKU/ano)", f"{p['module_t']:,.0f}".replace(",", "."), "ASSUMPTION", "v3 A012"),
        ("Novo módulo: capacidade disponível (t SKU/ano)", f"{p['module_t'] * p['oee']:,.0f}".replace(",", "."), "ASSUMPTION", "× OEE (A009)"),
        ("Volume contratado (t SKU/ano)", "0 público", "UNKNOWN", "cenários R5/R6 adicionam 1.500/3.000 t"),
        ("Vendido 2032 a partir do pipeline ponderado (t SKU)", f"{res['sold_t'][i]:,.0f}".replace(",", "."), "ASSUMPTION", "demanda v3 ponderada (A110/A111)"),
        ("Utilização 2035", f"{r.utilisation_2035:.0%}", "ASSUMPTION", ""),
        ("EBITDA 2032 (US$ mi)", f"{res['lines']['ebitda'][i] / 1e6:.1f}".replace(".", ","), "ASSUMPTION", ""),
        ("FCF 2032 (US$ mi)", f"{res['lines']['fcf'][i] / 1e6:.1f}".replace(".", ","), "ASSUMPTION", ""),
        ("VPL (US$ mi)", f"{r.npv_musd:.1f}".replace(".", ","), "ASSUMPTION", f"VT = {r.tv_share_of_npv:.0%} do VPL"),
    ]
    return pd.DataFrame(rows, columns=["step", "value", "status", "note"])


def run(cfg: dict, n_mc: int | None = None) -> dict:
    h = V3Handle(cfg["economics"])
    grid = scenario_grid(h)
    vow = value_of_waiting(h, grid)
    sens = sensitivities(h)
    mc = monte_carlo(h, n_mc or cfg["economics"]["mc_sims"])
    pub = public_only(cfg)
    br = bridge(h, grid)
    astax = pd.DataFrame([{"product": "astaxantina (Haematococcus heterotrófico, KAS)", "npv": "não estimável",
                           "irr": "não estimável", "status": "desenvolvimento (ago/2025)",
                           "missing": "rendimento, capex próprio, segregação de linha, registro por mercado, preço, "
                                      "contrato; capacidade ociosa hipotética não é volume assegurado",
                           "source_id": "R07"}])
    return {"grid": grid, "waiting": vow, "sensitivity": sens, "mc": mc, "public_only": pub, "bridge": br,
            "astaxanthin": astax, "demand_origin": h.demand_origin, "params": h.p0}


def write(res: dict) -> None:
    o = OUT
    res["grid"].to_csv(o / "economics_by_site_niche_scenario.csv", index=False)
    res["waiting"].to_csv(o / "economics_value_of_waiting.csv", index=False)
    res["sensitivity"].to_csv(o / "economics_sensitivity.csv", index=False)
    res["mc"].to_csv(o / "economics_monte_carlo.csv", index=False)
    res["public_only"].to_csv(o / "economics_public_only.csv", index=False)
    res["bridge"].to_csv(o / "capacity_to_npv_bridge.csv", index=False)
    res["astaxanthin"].to_csv(o / "economics_astaxanthin.csv", index=False)
    pd.DataFrame(columns=MGMT_FIELDS).to_csv(o / "management_data_template.csv", index=False)
