"""Country screening v3: v2 baseline reproduced from frozen data, then robustness, coverage and gates.

The score is a triage filter for which sites deserve diligence. It is never an NPV.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .data import ROOT

V2_DIR = ROOT.parent
FROZEN = ROOT / "data" / "raw" / "frozen_v2"


def load_v2():
    if "microalgae_site_selection" in sys.modules:
        return sys.modules["microalgae_site_selection"]
    spec = importlib.util.spec_from_file_location("microalgae_site_selection", V2_DIR / "microalgae_site_selection.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["microalgae_site_selection"] = mod
    spec.loader.exec_module(mod)
    return mod


def reproduce_v2() -> pd.DataFrame:
    """Re-run the v2 scoring on the frozen copy of its inputs and compare with the frozen v2 output."""
    m = load_v2()
    raw = m.load_country_data(FROZEN / "raw_country_data.csv")
    res = m.score_pipeline(m.add_derived_metrics(raw))
    ref = pd.read_csv(FROZEN / "v2_country_scores.csv").set_index("country")
    out = pd.DataFrame({"score_rerun": res["score"], "score_frozen_v2": ref["score"],
                        "rank_rerun": res["rank"], "rank_frozen_v2": ref["rank"]})
    out["abs_diff"] = (out["score_rerun"] - out["score_frozen_v2"]).abs()
    return out


def _scores(m, data, weights=None, metric_filter=None, fill=None):
    ms = m.score_metrics(data)
    if metric_filter is not None:
        ms = ms.copy()
        ms.loc[~ms["metric_id"].isin(metric_filter), "normalized_score"] = np.nan
    if fill is not None:
        ms = ms.copy()
        ms["normalized_score"] = ms["normalized_score"].fillna(fill)
    crit = m.calculate_criterion_scores(m.calculate_subcriterion_scores(ms))
    score, _ = m.calculate_country_score(crit, weights)
    return score, crit, ms


def ranking_v3(cfg: dict, n_weight_draws: int = 2000, seed: int = 42) -> tuple[pd.DataFrame, dict]:
    m = load_v2()
    raw = m.load_country_data(FROZEN / "raw_country_data.csv")
    data = m.add_derived_metrics(raw)
    base_w = m.SCENARIOS[m.BASE_SCENARIO]
    score, crit, ms = _scores(m, data)
    qual = [k for k, spec in m.METRIC_INDEX.items() if spec.method == "qualitative"]
    quant = [k for k in m.METRIC_INDEX if k not in qual]
    q_score, _, _ = _scores(m, data, metric_filter=quant)
    lo, _, _ = _scores(m, data, fill=0.0)
    hi, _, _ = _scores(m, data, fill=10.0)
    eff = ms.assign(w=ms["nominal_weight_base_case"]).dropna(subset=["normalized_score"])
    rubric_share = eff[eff.metric_id.isin(qual)].groupby("country")["w"].sum() / eff.groupby("country")["w"].sum()
    coverage = eff.groupby("country")["w"].sum() / ms.groupby("country")["nominal_weight_base_case"].sum()

    rng = np.random.default_rng(seed)
    crits = list(base_w)
    alpha = np.array([base_w[c] for c in crits]) * 20
    W = rng.dirichlet(alpha, size=n_weight_draws)
    C = crit[crits].to_numpy()
    S = C @ W.T
    ranks = (-S).argsort(axis=0).argsort(axis=0) + 1
    countries = list(crit.index)
    p1 = {c: float((ranks[i] == 1).mean()) for i, c in enumerate(countries)}
    p3 = {c: float((ranks[i] <= 3).mean()) for i, c in enumerate(countries)}
    med = {c: float(np.median(ranks[i])) for i, c in enumerate(countries)}

    viab = m.assess_viability(data, ms)
    v2ref = pd.read_csv(FROZEN / "v2_country_scores.csv").set_index("country")
    shortlist = {
        "Brazil": ("yes", "Sites BR_ORI_EXP (brownfield) and BR_GF_GO (illustrative greenfield) evaluated by NPV"),
        "Thailand": ("yes", "Sites TH_NSN and TH_RYG evaluated by NPV"),
        "China": ("no", "Strategic-risk score 2.6 (local over-capacity, IP) and no Corbion fermentation asset; "
                        "served as a demand node instead"),
        "India": ("no", "National water stress 66% (REVIEW); no Corbion asset; revisit with site-level water data"),
        "Vietnam": ("no", "Sugar 1.35 Mt and no Corbion asset; USTR Priority Foreign Country; demand node"),
        "Mexico": ("no", "Low aquafeed demand nearby; LPI 2.9 (REVIEW); no cost advantage vs Brazil"),
        "Chile": ("no", "No domestic sugar from 2026/27 (true zero, S026); demand node for salmon"),
        "Indonesia": ("no", "Lowest score; no Corbion asset; sugar importer"),
    }
    out = pd.DataFrame({
        "country": countries,
        "screening_score_v3": [score[c] for c in countries],
        "screening_score_v2_frozen": [v2ref.loc[c, "score"] for c in countries],
        "rank_v3": pd.Series(score).rank(ascending=False, method="min").astype(int).reindex(countries).values,
        "score_quant_only": [q_score[c] for c in countries],
        "score_if_missing_0": [lo[c] for c in countries], "score_if_missing_10": [hi[c] for c in countries],
        "rubric_share_of_weight": [rubric_share.get(c, np.nan) for c in countries],
        "data_coverage_of_weight": [coverage.get(c, np.nan) for c in countries],
        "p_rank1_weight_uncertainty": [p1[c] for c in countries],
        "p_top3_weight_uncertainty": [p3[c] for c in countries],
        "median_rank_weight_uncertainty": [med[c] for c in countries],
        "national_gate": [viab.loc[c, "viability_flag"] for c in countries],
        "national_gate_reasons": [viab.loc[c, "viability_reasons"] for c in countries],
        "shortlist": [shortlist[c][0] for c in countries],
        "shortlist_reason": [shortlist[c][1] for c in countries],
        "score_meaning": "triage only - not NPV",
    }).sort_values("screening_score_v3", ascending=False)
    extra = pd.read_csv(ROOT / "data" / "raw" / "country_screening_extra.csv")
    extra = extra.rename(columns={"reason": "shortlist_reason"}).assign(
        shortlist="not_scored", score_meaning="not scored: data not collected")[
        ["country", "shortlist", "shortlist_reason", "score_meaning", "data_needed"]]
    out = pd.concat([out, extra], ignore_index=True)
    crit_corr = crit[crits].corr().round(2)
    widened = bounds_robustness(m, data)
    return out, {"criterion_correlation": crit_corr, "bounds_robustness": widened,
                 "rubric_metrics": qual, "weight_draws": n_weight_draws}


def bounds_robustness(m, data) -> pd.DataFrame:
    """Widen/narrow every quantitative goalpost by 25% and report rank changes."""
    import dataclasses
    orig = dict(m.METRIC_INDEX)
    base_rank = m.score_pipeline(data)["rank"]
    rows = []
    try:
        for factor in (0.75, 1.25):
            for k, spec in orig.items():
                if spec.method == "qualitative":
                    continue
                lw, lb = (np.log10(spec.worst), np.log10(spec.best)) if spec.method == "log" else (spec.worst, spec.best)
                mid, half = (lw + lb) / 2, (lb - lw) / 2 * factor
                nw, nb = mid - half, mid + half
                if spec.method == "log":
                    nw, nb = 10 ** nw, 10 ** nb
                m.METRIC_INDEX[k] = dataclasses.replace(spec, worst=nw, best=nb)
            r = m.score_pipeline(data)["rank"]
            rows.append({"goalpost_range_factor": factor,
                         "countries_changing_rank": int((r != base_rank).sum()),
                         "top2_unchanged": bool((r[r <= 2].sort_index().index.tolist()
                                                 == base_rank[base_rank <= 2].sort_index().index.tolist())),
                         "ranks": "; ".join(f"{c}:{int(r[c])}" for c in r.sort_values().index)})
            m.METRIC_INDEX.update(orig)
    finally:
        m.METRIC_INDEX.update(orig)
    return pd.DataFrame(rows)
