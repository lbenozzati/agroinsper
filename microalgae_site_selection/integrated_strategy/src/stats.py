"""Empirical co-movement only when the data allow it; otherwise an explicit 'not computed' result."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

MIN_OBS = 24


def empirical_correlation(x: pd.Series, y: pd.Series, max_lag: int = 2) -> dict:
    """Pearson/Spearman on aligned, differenced series with basic diagnostics. Refuses short samples."""
    df = pd.concat([x, y], axis=1).dropna()
    n = len(df)
    if n < MIN_OBS:
        return {"status": "not computed: insufficient observations", "n": n, "min_required": MIN_OBS,
                "pearson": None, "spearman": None, "p_value": None}
    d = df.diff().dropna()  # remove common trend in levels
    a, b = d.iloc[:, 0], d.iloc[:, 1]
    pr, pp = stats.pearsonr(a, b)
    sr, _ = stats.spearmanr(a, b)
    ac = [float(a.autocorr(k)) for k in range(1, max_lag + 1)]
    lags = {k: float(a.corr(b.shift(k))) for k in range(-max_lag, max_lag + 1)}
    z = np.abs(stats.zscore(d))
    return {"status": "computed on first differences", "n": n, "pearson": float(pr), "spearman": float(sr),
            "p_value": float(pp), "autocorr_x": ac, "lead_lag": lags, "outliers_gt3sd": int((z > 3).any(axis=1).sum()),
            "caveat": "co-movement, not causation; check breaks and seasonality before use"}


def series_status(inventory: pd.DataFrame) -> pd.DataFrame:
    inv = inventory.copy()
    inv["correlation_computed"] = inv["observations_available"] >= MIN_OBS
    inv["result"] = np.where(inv["correlation_computed"], "see empirical tests",
                             "not computed: insufficient observations; scenario/priors used instead")
    return inv
