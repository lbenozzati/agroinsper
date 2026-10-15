"""Interval scoring with explicit coverage (revisão 2026-10-15).

Rules (README §Revisão):
- every cell has a status: OBSERVED, DERIVED, JUDGMENT, ASSUMPTION or UNKNOWN;
- ASSUMPTION never enters a public score: it is treated as UNKNOWN;
- an UNKNOWN cell contributes 0 to the floor and 10 to the ceiling (no invented 5, no zero-as-fact, no blind
  renormalisation of the other criteria); a cell with a documented range contributes its worse/better end;
- a metric flagged `component_of` a parent hands its weight to the parent as soon as the parent is known
  (prevents double counting sugar/power inside opex);
- ordering uses the guaranteed floor; position ranges come from the extreme completions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

KNOWN = {"OBSERVED", "DERIVED", "JUDGMENT"}
STATUSES = KNOWN | {"ASSUMPTION", "UNKNOWN"}


@dataclass(frozen=True)
class Spec:
    metric_id: str
    criterion: str
    weight: float          # weight inside the criterion
    worst: float
    best: float
    scale: str = "linear"
    label: str = ""
    component_of: str | None = None


def specs_from(cfg_metrics: dict) -> dict[str, Spec]:
    out = {}
    for k, v in cfg_metrics.items():
        out[k] = Spec(k, v["criterion"], float(v["weight"]), float(v["worst"]), float(v["best"]),
                      v.get("scale", "linear"), v.get("label", k), v.get("component_of"))
    return out


def validate_specs(specs: dict[str, Spec], criteria: dict) -> None:
    for c in criteria:
        tot = sum(s.weight for s in specs.values() if s.criterion == c)
        if abs(tot - 1.0) > 1e-6:
            raise ValueError(f"metric weights inside criterion {c} sum to {tot}, not 1")
    tot = sum(v["weight"] for v in criteria.values())
    if abs(tot - 1.0) > 1e-6:
        raise ValueError(f"criterion weights sum to {tot}, not 1")


def norm(x: float, s: Spec) -> float:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return float("nan")
    if s.scale == "log":
        x = max(float(x), 1e-9)
        z = (math.log(x) - math.log(s.worst)) / (math.log(s.best) - math.log(s.worst))
    else:
        z = (float(x) - s.worst) / (s.best - s.worst)
    return float(min(1.0, max(0.0, z)) * 10.0)


def cell_scores(cells: pd.DataFrame, specs: dict[str, Spec]) -> pd.DataFrame:
    """One row per (entity, metric): score_mid/lo/hi on 0-10 and the effective status."""
    rows = []
    for _, r in cells.iterrows():
        s = specs.get(r["metric_id"])
        if s is None:
            continue
        st = str(r["status"]).upper()
        if st not in STATUSES:
            raise ValueError(f"unknown status {st} for {r['entity']} {r['metric_id']}")
        v = pd.to_numeric(r.get("value"), errors="coerce")
        lo_v = pd.to_numeric(r.get("value_low"), errors="coerce")
        hi_v = pd.to_numeric(r.get("value_high"), errors="coerce")
        if st in KNOWN and pd.isna(v):
            raise ValueError(f"{r['entity']} {r['metric_id']}: status {st} without value")
        if st in KNOWN:
            ends = [norm(x, s) for x in (lo_v, hi_v) if not pd.isna(x)] + [norm(v, s)]
            mid, lo, hi = norm(v, s), min(ends), max(ends)
            eff = st
        else:   # UNKNOWN or ASSUMPTION -> unknown in the public score
            mid, lo, hi = float("nan"), 0.0, 10.0
            eff = "UNKNOWN"
        rows.append({"entity": r["entity"], "metric_id": r["metric_id"], "criterion": s.criterion,
                     "status": st, "effective_status": eff, "value": v, "score_mid": mid, "score_lo": lo,
                     "score_hi": hi})
    return pd.DataFrame(rows)


def effective_weights(cs: pd.DataFrame, specs: dict[str, Spec], crit_w: dict) -> pd.DataFrame:
    """Absolute weight of each (entity, metric) after the component rule."""
    out = []
    for e, g in cs.groupby("entity", sort=False):
        known = set(g.loc[g.effective_status != "UNKNOWN", "metric_id"])
        w = {k: crit_w[s.criterion] * s.weight for k, s in specs.items()}
        for k, s in specs.items():
            if s.component_of and s.component_of in known:
                w[s.component_of] += w[k]
                w[k] = 0.0
        for k in w:
            out.append({"entity": e, "metric_id": k, "abs_weight": w[k]})
    return pd.DataFrame(out)


def aggregate(cs: pd.DataFrame, specs: dict[str, Spec], crit_w: dict) -> pd.DataFrame:
    ew = effective_weights(cs, specs, crit_w)
    m = cs.merge(ew, on=["entity", "metric_id"], how="right")
    m["effective_status"] = m["effective_status"].fillna("UNKNOWN")
    m["score_lo"] = m["score_lo"].fillna(0.0)
    m["score_hi"] = m["score_hi"].fillna(10.0)
    m["criterion"] = m["metric_id"].map(lambda k: specs[k].criterion)
    rows = []
    for e, g in m.groupby("entity", sort=False):
        kn = g.effective_status != "UNKNOWN"
        rec = {"entity": e,
               "floor": float((g.abs_weight * g.score_lo).sum()),
               "ceiling": float((g.abs_weight * g.score_hi).sum()),
               "known_points": float((g.abs_weight * g.score_mid.where(kn, 0.0)).sum()),
               "verified_weight": float(g.loc[kn & (g.effective_status != "JUDGMENT"), "abs_weight"].sum()),
               "judgment_weight": float(g.loc[g.effective_status == "JUDGMENT", "abs_weight"].sum()),
               "unknown_weight": float(g.loc[~kn, "abs_weight"].sum())}
        kw = rec["verified_weight"] + rec["judgment_weight"]
        rec["partial_score_known_only"] = rec["known_points"] / kw if kw > 0 else float("nan")
        for c in crit_w:
            gc = g[g.criterion == c]
            cw = gc.abs_weight.sum()
            rec[f"{c}_floor"] = float((gc.abs_weight * gc.score_lo).sum() / cw) if cw > 0 else float("nan")
            rec[f"{c}_ceiling"] = float((gc.abs_weight * gc.score_hi).sum() / cw) if cw > 0 else float("nan")
            rec[f"{c}_known_share"] = float(gc.loc[gc.effective_status != "UNKNOWN", "abs_weight"].sum() / cw) \
                if cw > 0 else float("nan")
        rows.append(rec)
    t = pd.DataFrame(rows).set_index("entity")
    t["width"] = t.ceiling - t.floor
    return rank_ranges(t)


def rank_ranges(t: pd.DataFrame) -> pd.DataFrame:
    t = t.copy()
    t["rank_floor"] = t.floor.rank(ascending=False, method="min").astype(int)
    best, worst = {}, {}
    for e in t.index:
        others = t.drop(index=e)
        best[e] = 1 + int((others.floor > t.at[e, "ceiling"]).sum())
        worst[e] = 1 + int((others.ceiling > t.at[e, "floor"]).sum())
    t["rank_best"] = pd.Series(best)
    t["rank_worst"] = pd.Series(worst)
    return t.sort_values(["floor", "ceiling"], ascending=False)


def dominance(t: pd.DataFrame) -> pd.DataFrame:
    """Pairwise: 'A' if A's floor beats B's ceiling, 'B' if the reverse, 'indeciso' otherwise."""
    ents = list(t.index)
    mat = pd.DataFrame("", index=ents, columns=ents)
    for a in ents:
        for b in ents:
            if a == b:
                mat.at[a, b] = "—"
            elif t.at[a, "floor"] > t.at[b, "ceiling"]:
                mat.at[a, b] = "à frente"
            elif t.at[b, "floor"] > t.at[a, "ceiling"]:
                mat.at[a, b] = "atrás"
            else:
                mat.at[a, b] = "indeciso"
    return mat


def perturb(crit_w: dict, c: str, rel: float) -> dict:
    """Change criterion c by `rel` (relative), rescale the others so the sum stays 1."""
    w = dict(crit_w)
    new = w[c] * (1 + rel)
    rest = 1 - w[c]
    for k in w:
        w[k] = new if k == c else w[k] * (1 - new) / rest
    return w


def tipping(t: pd.DataFrame, crit_w: dict, a: str, b: str, c: str, col: str = "floor") -> float | None:
    """Weight x of criterion c (others rescaled by (1-x)/(1-w_c)) at which b's `col` equals a's.
    The score is linear in the weights (the component rule only moves weight inside one criterion), so
    diff(x) = x*D_c + (1-x)/(1-w_c) * sum_{k!=c} w_k D_k with D_k = a_k - b_k (criterion-level values)."""
    D = {k: float(t.at[a, f"{k}_{col}"] - t.at[b, f"{k}_{col}"]) for k in crit_w}
    rest = 1 - crit_w[c]
    R = sum(crit_w[k] * D[k] for k in crit_w if k != c) / rest
    den = D[c] - R
    if abs(den) < 1e-12:
        return None
    x = -R / den
    return float(round(x, 3)) if 0.0 <= x <= 1.0 else None


def reweight(t: pd.DataFrame, crit_w: dict) -> pd.DataFrame:
    """Fast re-aggregation for another criterion-weight vector using the criterion-level floors/ceilings."""
    out = pd.DataFrame(index=t.index)
    out["floor"] = sum(crit_w[c] * t[f"{c}_floor"].fillna(0.0) for c in crit_w)
    out["ceiling"] = sum(crit_w[c] * t[f"{c}_ceiling"].fillna(10.0) for c in crit_w)
    return rank_ranges(out)


def single_document_flip(cs: pd.DataFrame, specs: dict[str, Spec], crit_w: dict, a: str, b: str) -> pd.DataFrame:
    """For a pair where a leads on floor: which single unknown/ranged metric, set best for b and worst for a
    (everything else at floor), would put b ahead?"""
    base = aggregate(cs, specs, crit_w)
    ew = effective_weights(cs, specs, crit_w).set_index(["entity", "metric_id"]).abs_weight
    rows = []
    for k, s in specs.items():
        ca = cs[(cs.entity == a) & (cs.metric_id == k)]
        cb = cs[(cs.entity == b) & (cs.metric_id == k)]
        if ca.empty or cb.empty:
            continue
        ra, rb = ca.iloc[0], cb.iloc[0]
        open_a = ra.score_hi - ra.score_lo > 1e-9
        open_b = rb.score_hi - rb.score_lo > 1e-9
        if not (open_a or open_b):
            continue
        gain_b = ew[(b, k)] * (rb.score_hi - rb.score_lo)
        gap = base.at[a, "floor"] - base.at[b, "floor"]
        flips = gain_b > gap
        rows.append({"leader": a, "challenger": b, "metric_id": k, "label": s.label, "criterion": s.criterion,
                     "status_leader": ra.status, "status_challenger": rb.status,
                     "floor_gap": round(gap, 3), "max_gain_challenger": round(gain_b, 3),
                     "single_document_can_flip": bool(flips)})
    return pd.DataFrame(rows)
