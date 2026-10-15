"""Public site ranking (40/25/15/15/5) with gates, coverage, position ranges and robustness."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import yaml

from .. import plant as P
from . import interval as I
from .common import CELL_COLS, DATA, OUT


def derived_cells(cfg: dict) -> pd.DataFrame:
    sc = cfg["site"]
    ports = yaml.safe_load(open(P.RAW / "ports.yaml"))
    tm = P.transit_matrix(ports)
    rows = []
    dest_w = {d: w * sc["niche_weights"][n] for n, dd in sc["destination_weights"].items() for d, w in dd.items()}
    assert abs(sum(dest_w.values()) - 1) < 1e-6
    for site in sc["entities"]:
        c = sc["country"][site]
        o_in = ports["origins"][c]["inland_days"]
        days = 0.0
        parts = []
        for d, w in dest_w.items():
            r = tm[(tm.origin == c) & (tm.market == d)].iloc[0]
            dd = r.door_to_door_days - o_in + sc["origin_inland_days"][site]
            days += w * dd
            parts.append(f"{d} {dd:.0f}d×{w:.3f}")
        rows.append({"metric_id": "ac_transit_days", "entity": site, "entity_type": "site", "niche": "all",
                     "value": round(days, 1), "unit": "dias porta a porta (média ponderada fixa)",
                     "start_year": 2026, "end_year": 2026, "as_of_date": cfg["revision_date"],
                     "source_id": "derived:searoutes", "page_or_table": "data/raw/ports.yaml",
                     "evidence_type": "geometric_derivation", "status": "DERIVED",
                     "formula": "Σ peso_destino × (milhas náuticas/(15 nós×24) + 2 escalas×2 d + trechos terrestres)",
                     "verification_level": "L4_reproducible_calc",
                     "notes": "Pesos fixos 1/3 por nicho (config.site.destination_weights), não o SAM do ranking de "
                              "mercado. " + "; ".join(parts)})
        partners = set(sc["fta_partners"][c])
        cov = sum(w for d, w in dest_w.items() if d in partners)
        rows.append({"metric_id": "ac_fta_share", "entity": site, "entity_type": "site", "niche": "all",
                     "value": round(cov, 3), "unit": "fração do peso de destinos", "start_year": 2026,
                     "end_year": 2026, "as_of_date": cfg["revision_date"], "source_id": "R45;R37",
                     "page_or_table": "plant_metric_scores (nota 'Partners')", "evidence_type": "derived_list",
                     "status": "DERIVED", "formula": "Σ peso_destino × 1[acordo em vigor ou doméstico]",
                     "verification_level": "L3_prior_session",
                     "notes": "Acordos assinados e não vigentes (UE–Mercosul, EFTA–Tailândia) NÃO contados; "
                              "cobertos: " + ", ".join(sorted(d for d in dest_w if d in partners))})
    out = pd.DataFrame(rows)
    for col in CELL_COLS:
        if col not in out:
            out[col] = np.nan
    return out[CELL_COLS]


def load_cells(cfg: dict) -> pd.DataFrame:
    base = pd.read_csv(DATA / "site_cells.csv")
    cells = pd.concat([base, derived_cells(cfg)], ignore_index=True)
    missing = set(cfg["site"]["metrics"]) - set(cells.metric_id)
    if missing:
        raise ValueError(f"site metrics without cells: {missing}")
    if cells.duplicated(["entity", "metric_id"]).any():
        raise ValueError("duplicate site cells")
    return cells


def gate_summary(gates: pd.DataFrame, sites: list[str]) -> pd.DataFrame:
    rows = []
    for s in sites:
        g = gates[gates.site == s]
        st = set(g.status)
        overall = "fail" if "fail" in st else ("review/unknown" if st & {"review", "unknown"} else "pass")
        rows.append({"entity": s, "gate_overall": overall, "n_pass": int((g.status == "pass").sum()),
                     "n_review": int((g.status == "review").sum()), "n_unknown": int((g.status == "unknown").sum()),
                     "n_fail": int((g.status == "fail").sum()),
                     "open_items": "; ".join(f"{r.gate_type} ({r.market}): {r.status}" for r in g.itertuples()
                                             if r.status != "pass")})
    return pd.DataFrame(rows).set_index("entity")


def run(cfg: dict) -> dict:
    sc = cfg["site"]
    specs = I.specs_from(sc["metrics"])
    crit_w = {k: v["weight"] for k, v in sc["criteria"].items()}
    I.validate_specs(specs, sc["criteria"])
    cells = load_cells(cfg)
    cs = I.cell_scores(cells, specs)
    t = I.aggregate(cs, specs, crit_w)
    gates = pd.read_csv(DATA / "product_regulatory_matrix.csv")
    gsum = gate_summary(gates, sc["entities"])
    t = t.join(gsum)
    t["label"] = t.index.map(sc["labels"])

    # weight sets and ±25% relative perturbations
    ws_rows, pert_rows = [], []
    for nm, w in sc["weight_sets"].items():
        tt = I.reweight(t, w)
        for e, r in tt.iterrows():
            ws_rows.append({"weight_set": nm, "entity": e, "floor": r.floor, "ceiling": r.ceiling,
                            "rank_floor": r.rank_floor, "rank_best": r.rank_best, "rank_worst": r.rank_worst})
    for c in crit_w:
        for rel in (-0.25, 0.25):
            w = I.perturb(crit_w, c, rel)
            tt = I.reweight(t, w)
            for e, r in tt.iterrows():
                pert_rows.append({"criterion": c, "relative_change": rel, "entity": e, "floor": r.floor,
                                  "ceiling": r.ceiling, "rank_floor": r.rank_floor, "rank_best": r.rank_best,
                                  "rank_worst": r.rank_worst})
    # tipping points and single-document flips for every ordered pair on floor
    order = list(t.index)
    tips, flips = [], []
    for a, b in itertools.combinations(order, 2):
        for c in crit_w:
            for col in ("floor", "ceiling"):
                x = I.tipping(t, crit_w, a, b, c, col)
                tips.append({"leader_on_floor": a, "challenger": b, "criterion": c, "basis": col,
                             "current_weight": crit_w[c], "tipping_weight": x})
        flips.append(I.single_document_flip(cs, specs, crit_w, a, b))
    # criterion correlation (floors) and leave-one-criterion-out
    crit_cols = [f"{c}_floor" for c in crit_w]
    corr = t[crit_cols].astype(float).corr()
    loo = []
    for c in crit_w:
        w = {k: (0.0 if k == c else v / (1 - crit_w[c])) for k, v in crit_w.items()}
        tt = I.reweight(t, w)
        for e, r in tt.iterrows():
            loo.append({"without": c, "entity": e, "floor": r.floor, "ceiling": r.ceiling,
                        "rank_floor": r.rank_floor, "rank_best": r.rank_best, "rank_worst": r.rank_worst})
    ev = cells.merge(cs[["entity", "metric_id", "score_mid", "score_lo", "score_hi", "effective_status"]],
                     on=["entity", "metric_id"], how="left")
    ew = I.effective_weights(cs, specs, crit_w)
    ev = ev.merge(ew, on=["entity", "metric_id"], how="left")
    goal = pd.DataFrame([{"ranking": "site", "niche": "all", "metric_id": k, "criterion": s.criterion,
                          "weight_in_criterion": s.weight, "abs_weight": s.weight * crit_w[s.criterion],
                          "worst": s.worst, "best": s.best, "scale": s.scale, "label": s.label,
                          "component_of": s.component_of or ""} for k, s in specs.items()])
    return {"table": t, "cells": cells, "cell_scores": cs, "evidence": ev, "gates": gates, "specs": specs,
            "crit_w": crit_w, "weight_sets": pd.DataFrame(ws_rows), "perturbation": pd.DataFrame(pert_rows),
            "tipping": pd.DataFrame(tips), "flips": pd.concat(flips, ignore_index=True),
            "dominance": I.dominance(t), "correlation": corr, "leave_one_out": pd.DataFrame(loo),
            "goalposts": goal}


def write(res: dict) -> None:
    o = OUT
    t = res["table"].copy()
    t.index.name = "site"
    t.round(3).to_csv(o / "site_public_scores.csv")
    res["evidence"].to_csv(o / "site_evidence.csv", index=False)
    res["gates"].to_csv(o / "product_regulatory_matrix.csv", index=False)
    res["weight_sets"].round(3).to_csv(o / "site_weight_sets.csv", index=False)
    res["perturbation"].round(3).to_csv(o / "site_weight_perturbation_pm25.csv", index=False)
    res["tipping"].to_csv(o / "site_tipping_points.csv", index=False)
    res["flips"].to_csv(o / "site_single_document_flips.csv", index=False)
    res["dominance"].to_csv(o / "site_pairwise_dominance.csv")
    res["correlation"].round(3).to_csv(o / "site_criterion_correlation.csv")
    res["leave_one_out"].round(3).to_csv(o / "site_leave_one_criterion_out.csv", index=False)
