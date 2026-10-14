"""Generic weighted multi-criteria scoring shared by the plant and the market rankings.

Pipeline: raw value -> 0-10 metric score (fixed goalposts, HDI style) -> sub-criterion -> criterion -> country.
Missing values are never zero: the metric drops out, weights are renormalised, and the gap is reported together
with the score bounds obtained by filling the gap with 0 and with 10.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

RUBRIC_LEVELS = (0.0, 2.5, 5.0, 7.5, 10.0)
MC_QUANT_SIGMA = {"High": 0.05, "Medium": 0.15, "Low": 0.30}
MC_RUBRIC_SHIFT = {"High": 0.10, "Medium": 0.25, "Low": 0.40}


@dataclass(frozen=True)
class Metric:
    metric_id: str
    sub: str
    weight: float
    method: str  # linear | log | rubric (analyst judgement) | mapped (public list mapped to 0/5/10)
    label: str
    worst: float | None = None
    best: float | None = None


@dataclass
class Model:
    criteria: dict[str, str]  # id -> label
    scenarios: dict[str, dict[str, float]]
    base: str
    subs: dict[str, tuple[str, str, float]]  # id -> (criterion, label, weight in criterion)
    metrics: dict[str, Metric]

    @classmethod
    def from_config(cls, cfg: dict) -> "Model":
        subs = {k: (v["criterion"], v["label"], float(v["weight"])) for k, v in cfg["subcriteria"].items()}
        metrics = {}
        for k, v in cfg["metrics"].items():
            metrics[k] = Metric(k, v["sub"], float(v["weight"]), v["method"], v["label"],
                                v.get("worst"), v.get("best"))
        m = cls(cfg["criteria"], cfg["scenarios"], cfg["base_scenario"], subs, metrics)
        m.validate()
        return m

    def validate(self) -> None:
        for name, w in self.scenarios.items():
            assert set(w) == set(self.criteria), f"scenario {name} must weight every criterion"
            assert abs(sum(w.values()) - 1) < 1e-9, f"scenario {name} weights must sum to 1"
        for c in self.criteria:
            tot = sum(w for (cc, _, w) in self.subs.values() if cc == c)
            assert abs(tot - 1) < 1e-9, f"sub-criteria of {c} sum to {tot}"
        for s in self.subs:
            tot = sum(m.weight for m in self.metrics.values() if m.sub == s)
            assert abs(tot - 1) < 1e-9, f"metrics of {s} sum to {tot}"
        for m in self.metrics.values():
            assert m.sub in self.subs, m.metric_id
            if m.method not in ("rubric", "mapped"):
                assert m.worst is not None and m.best is not None and m.worst != m.best, m.metric_id

    def nominal_weight(self, metric_id: str, scenario: str | None = None) -> float:
        m = self.metrics[metric_id]
        c, _, ws = self.subs[m.sub]
        return self.scenarios[scenario or self.base][c] * ws * m.weight


def normalise(x: pd.Series, m: Metric, stretch: float = 1.0) -> pd.Series:
    """0-10 score. `stretch` widens the goalposts symmetrically around their midpoint (robustness test)."""
    x = pd.to_numeric(x, errors="coerce").astype(float)
    if m.method in ("rubric", "mapped"):
        return x.clip(0, 10)
    worst, best = float(m.worst), float(m.best)
    nonpos = x <= 0
    if m.method == "log":
        x = np.log10(x.where(x > 0))
        worst, best = math.log10(worst), math.log10(best)
    if stretch != 1.0:
        mid, half = (worst + best) / 2, (best - worst) / 2 * stretch
        worst, best = mid - half, mid + half
    s = (10 * (x - worst) / (best - worst)).clip(0, 10)
    if m.method == "log":
        s[nonpos] = 0.0
    return s


def wide_values(model: Model, data: pd.DataFrame) -> pd.DataFrame:
    """country x metric raw values (only scored metrics)."""
    d = data[data.metric_id.isin(model.metrics)]
    w = d.pivot_table(index="country", columns="metric_id", values="raw_value", aggfunc="first")
    return w.reindex(columns=list(model.metrics))


def metric_scores(model: Model, values: pd.DataFrame, stretch: float = 1.0) -> pd.DataFrame:
    return pd.DataFrame({k: normalise(values[k], m, stretch) for k, m in model.metrics.items()}, index=values.index)


def aggregate(model: Model, ms: pd.DataFrame, weights: dict | None = None, fill: float | None = None,
              keep: list[str] | None = None) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame]:
    """Returns (country score, criterion scores, sub-criterion scores).

    fill: value used for missing metrics (None = drop and renormalise). keep: restrict to these metrics.
    """
    weights = weights or model.scenarios[model.base]
    ms = ms.copy()
    if keep is not None:
        ms = ms[[c for c in ms.columns if c in keep]]
    if fill is not None:
        ms = ms.fillna(fill)
    sub = {}
    for s in model.subs:
        cols = [k for k in ms.columns if model.metrics[k].sub == s]
        if not cols:
            sub[s] = pd.Series(np.nan, index=ms.index)
            continue
        w = pd.Series({k: model.metrics[k].weight for k in cols})
        val = ms[cols]
        num = (val * w).sum(axis=1, min_count=1)
        den = val.notna().mul(w).sum(axis=1)
        sub[s] = num / den.replace(0, np.nan)
    sub = pd.DataFrame(sub)
    crit = {}
    for c in model.criteria:
        cols = [s for s in model.subs if model.subs[s][0] == c]
        w = pd.Series({s: model.subs[s][2] for s in cols})
        val = sub[cols]
        crit[c] = (val * w).sum(axis=1, min_count=1) / val.notna().mul(w).sum(axis=1).replace(0, np.nan)
    crit = pd.DataFrame(crit)
    w = pd.Series(weights)[list(model.criteria)]
    score = (crit * w).sum(axis=1, min_count=1) / crit.notna().mul(w).sum(axis=1)
    return score.rename("score"), crit, sub


def rank(score: pd.Series) -> pd.Series:
    return score.rank(ascending=False, method="min").astype(int)


def coverage(model: Model, ms: pd.DataFrame) -> pd.DataFrame:
    """Share of nominal weight with data, share of weight that is rubric, and the missing metrics."""
    nw = pd.Series({k: model.nominal_weight(k) for k in model.metrics})
    have = ms.notna()
    rub = pd.Series({k: model.metrics[k].method == "rubric" for k in model.metrics})
    out = pd.DataFrame({
        "data_coverage_of_weight": have.mul(nw).sum(axis=1) / nw.sum(),
        "rubric_share_of_weight": have.mul(nw * rub).sum(axis=1) / have.mul(nw).sum(axis=1),
        "missing_metrics": have.apply(lambda r: ";".join(r.index[~r]), axis=1),
    })
    return out


def dirichlet_ranks(crit: pd.DataFrame, base_w: dict, n: int, seed: int, concentration: float = 20.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cols = list(base_w)
    W = rng.dirichlet(np.array([base_w[c] for c in cols]) * concentration, size=n)
    C = crit[cols].fillna(crit[cols].mean()).to_numpy()
    S = C @ W.T
    R = (-S).argsort(axis=0).argsort(axis=0) + 1
    return pd.DataFrame({"p_rank1_weights": (R == 1).mean(axis=1), "p_top3_weights": (R <= 3).mean(axis=1),
                         "median_rank_weights": np.median(R, axis=1)}, index=crit.index)


def monte_carlo(model: Model, values: pd.DataFrame, conf: pd.DataFrame, n: int, seed: int,
                weights: dict | None = None) -> pd.DataFrame:
    """Data-uncertainty MC: lognormal noise on quantitative inputs and one-level rubric shifts, by confidence."""
    rng = np.random.default_rng(seed)
    countries = list(values.index)
    ranks = np.zeros((len(countries), n), dtype=int)
    scores = np.zeros((len(countries), n))
    for i in range(n):
        v = values.copy()
        for k, m in model.metrics.items():
            c = conf[k].fillna("Low")
            col = pd.to_numeric(v[k], errors="coerce")
            if m.method in ("rubric", "mapped"):
                p = c.map(MC_RUBRIC_SHIFT).astype(float)
                shift = np.where(rng.random(len(col)) < p, rng.choice([-2.5, 2.5], len(col)), 0.0)
                v[k] = (col + shift).clip(0, 10)
            else:
                sig = c.map(MC_QUANT_SIGMA).astype(float)
                v[k] = col * np.exp(rng.normal(0, 1, len(col)) * sig - sig ** 2 / 2)
        s, _, _ = aggregate(model, metric_scores(model, v), weights)
        scores[:, i] = s.to_numpy()
        ranks[:, i] = rank(s).to_numpy()
    return pd.DataFrame({"mc_mean_score": scores.mean(axis=1), "mc_p10": np.percentile(scores, 10, axis=1),
                         "mc_p90": np.percentile(scores, 90, axis=1), "p_rank1_data": (ranks == 1).mean(axis=1),
                         "p_top3_data": (ranks <= 3).mean(axis=1), "median_rank_data": np.median(ranks, axis=1)},
                        index=countries)


def weight_tipping(crit: pd.DataFrame, base_w: dict, a: str, b: str, criterion: str) -> float | None:
    """Weight of `criterion` (others rescaled proportionally) at which b overtakes a; None if never in [0,1]."""
    others = {k: v for k, v in base_w.items() if k != criterion}
    tot = sum(others.values())
    grid = np.linspace(0, 1, 1001)
    prev = None
    for x in grid:
        w = {criterion: x, **{k: v / tot * (1 - x) for k, v in others.items()}}
        diff = sum(crit.loc[a, k] * w[k] for k in w) - sum(crit.loc[b, k] * w[k] for k in w)
        if prev is not None and np.sign(diff) != np.sign(prev) and diff != 0:
            return float(x)
        prev = diff
    return None
