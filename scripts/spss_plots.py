#!/usr/bin/env python3
"""Charts for analyze.py results (PNG via matplotlib, headless Agg backend).

Plot *data* is prepared by small pure functions (histogram_data, boxplot_stats,
fit_line, ...) so the numbers behind each chart can be unit-tested; the drawing
functions only render those numbers. matplotlib is optional: without it
`make_plots` raises a clear error and every other part of the skill still works.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


def _plt():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:  # pragma: no cover - exercised only without matplotlib
        raise ValueError("Plots require matplotlib. Install it with: python -m pip install matplotlib") from exc
    return plt


# ------------------------------------------------------------ plot data (testable)

def histogram_data(values, bins=None):
    """Counts and edges for a histogram plus normal-curve parameters (SPSS 'show normal curve')."""
    x = np.asarray(pd.to_numeric(pd.Series(values), errors="coerce").dropna(), dtype=float)
    if x.size == 0:
        raise ValueError("No numeric values to plot")
    if bins is None:
        bins = max(1, int(np.ceil(np.log2(x.size) + 1)))  # Sturges' rule
    counts, edges = np.histogram(x, bins=bins)
    sd = float(x.std(ddof=1)) if x.size > 1 else float("nan")
    return {"counts": counts.tolist(), "edges": edges.tolist(), "n": int(x.size),
            "mean": float(x.mean()), "sd": sd}


def boxplot_stats(values):
    """Matplotlib box statistics (linear-interpolated quartiles, not SPSS Tukey hinges): quartiles, whiskers to last point within 1.5 IQR, outliers beyond."""
    x = np.sort(np.asarray(pd.to_numeric(pd.Series(values), errors="coerce").dropna(), dtype=float))
    if x.size == 0:
        raise ValueError("No numeric values to plot")
    q1, med, q3 = (float(np.percentile(x, q)) for q in (25, 50, 75))
    iqr = q3 - q1
    lo_fence, hi_fence = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    inside = x[(x >= lo_fence) & (x <= hi_fence)]
    return {"q1": q1, "median": med, "q3": q3, "whisker_low": float(inside.min()), "whisker_high": float(inside.max()),
            "outliers": x[(x < lo_fence) | (x > hi_fence)].tolist(), "n": int(x.size)}


def fit_line(x, y):
    """OLS line y = a + b*x on complete pairs; returns slope, intercept, r_squared, n."""
    d = pd.DataFrame({"x": pd.to_numeric(pd.Series(x), errors="coerce").to_numpy(),
                      "y": pd.to_numeric(pd.Series(y), errors="coerce").to_numpy()}).dropna()
    if len(d) < 2 or d["x"].std(ddof=1) == 0:
        raise ValueError("Need at least two complete pairs with variation in x")
    b = float(np.cov(d["x"], d["y"], ddof=1)[0, 1] / d["x"].var(ddof=1))
    a = float(d["y"].mean() - b * d["x"].mean())
    r = float(np.corrcoef(d["x"], d["y"])[0, 1])
    return {"slope": b, "intercept": a, "r_squared": r * r, "n": int(len(d))}


def bar_counts(values):
    """Category -> count for a bar chart, ordered like SPSS (ascending value)."""
    s = pd.Series(values).dropna()
    vc = s.value_counts()

    def key(v):
        try:
            return (0, float(v), "")
        except (TypeError, ValueError):
            return (1, 0.0, str(v))
    return [(str(k if not (isinstance(k, float) and k.is_integer()) else int(k)), int(vc[k])) for k in sorted(vc.index, key=key)]


def group_means_ci(df, outcome, group, groups=None, conf=0.95):
    """Group mean and t-based CI half-width (for an error-bar chart)."""
    from scipy import stats
    y = pd.to_numeric(df[outcome], errors="coerce")
    out = []
    labels = groups if groups is not None else sorted(df[group].dropna().unique(), key=str)
    for g in labels:
        v = y[df[group] == g].dropna()
        if len(v) < 2:
            continue
        se = float(v.std(ddof=1) / math.sqrt(len(v)))
        half = float(stats.t.ppf((1 + conf) / 2, len(v) - 1) * se)
        out.append({"group": str(g), "n": int(len(v)), "mean": float(v.mean()), "half_width": half})
    return out


def residual_data(df, outcome, predictors):
    """Fitted values and standardized residuals of the OLS model (for a residual plot)."""
    d = df[[outcome] + predictors].apply(pd.to_numeric, errors="coerce").dropna()
    X = np.column_stack([np.ones(len(d))] + [d[p].to_numpy(float) for p in predictors])
    y = d[outcome].to_numpy(float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    fitted = X @ beta
    resid = y - fitted
    dof = len(y) - X.shape[1]
    s = math.sqrt((resid ** 2).sum() / dof) if dof > 0 else float("nan")
    return {"fitted": fitted.tolist(), "std_resid": (resid / s).tolist() if s else [], "n": int(len(y))}


# ------------------------------------------------------------ drawing

def _save(fig, outdir, name):
    path = Path(outdir) / name
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    _plt().close(fig)
    return path


def _safe(name):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(name))[:60]


def plot_histogram(values, name, outdir):
    plt = _plt()
    h = histogram_data(values)
    fig, ax = plt.subplots(figsize=(6, 4))
    edges = np.array(h["edges"])
    ax.bar(edges[:-1], h["counts"], width=np.diff(edges), align="edge", color="#4c72b0", edgecolor="white")
    if h["sd"] and math.isfinite(h["sd"]) and h["sd"] > 0:
        xs = np.linspace(edges[0], edges[-1], 200)
        width = edges[1] - edges[0]
        ax.plot(xs, h["n"] * width * np.exp(-0.5 * ((xs - h["mean"]) / h["sd"]) ** 2) / (h["sd"] * math.sqrt(2 * math.pi)), color="black", lw=1.2)
    ax.set_title(f"Histogram: {name}")
    ax.set_xlabel(str(name)); ax.set_ylabel("Frequency")
    ax.text(0.98, 0.95, f"Mean = {h['mean']:.2f}\nSD = {h['sd']:.2f}\nN = {h['n']}", transform=ax.transAxes, ha="right", va="top", fontsize=8)
    return _save(fig, outdir, f"histogram_{_safe(name)}.png")


def plot_bar(values, name, outdir):
    plt = _plt()
    data = bar_counts(values)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar([k for k, _ in data], [v for _, v in data], color="#4c72b0")
    ax.set_title(f"Bar chart: {name}"); ax.set_xlabel(str(name)); ax.set_ylabel("Count")
    return _save(fig, outdir, f"bar_{_safe(name)}.png")


def plot_boxplot(df, outcome, group, groups, outdir):
    plt = _plt()
    y = pd.to_numeric(df[outcome], errors="coerce")
    labels = groups if groups is not None else sorted(df[group].dropna().unique(), key=str)
    data = [y[df[group] == g].dropna().to_numpy() for g in labels]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.boxplot(data, tick_labels=[str(g) for g in labels], whis=1.5)
    ax.set_title(f"Boxplot: {outcome} by {group}"); ax.set_xlabel(str(group)); ax.set_ylabel(str(outcome))
    return _save(fig, outdir, f"boxplot_{_safe(outcome)}_by_{_safe(group)}.png")


def plot_errorbar(df, outcome, group, groups, outdir):
    plt = _plt()
    d = group_means_ci(df, outcome, group, groups)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.errorbar([x["group"] for x in d], [x["mean"] for x in d], yerr=[x["half_width"] for x in d], fmt="o", capsize=5, color="#4c72b0")
    ax.set_title(f"Mean of {outcome} by {group} (95% CI)"); ax.set_xlabel(str(group)); ax.set_ylabel(f"Mean {outcome}")
    return _save(fig, outdir, f"errorbar_{_safe(outcome)}_by_{_safe(group)}.png")


def plot_scatter(df, xname, yname, outdir, fit=True):
    plt = _plt()
    d = df[[xname, yname]].apply(pd.to_numeric, errors="coerce").dropna()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(d[xname], d[yname], color="#4c72b0", s=22)
    if fit and len(d) >= 2 and d[xname].std(ddof=1) > 0:
        f = fit_line(d[xname], d[yname])
        xs = np.array([d[xname].min(), d[xname].max()])
        ax.plot(xs, f["intercept"] + f["slope"] * xs, color="black", lw=1.2)
        ax.text(0.02, 0.95, f"R\u00b2 Linear = {f['r_squared']:.3f}", transform=ax.transAxes, va="top", fontsize=8)
    ax.set_title(f"Scatterplot: {yname} by {xname}"); ax.set_xlabel(str(xname)); ax.set_ylabel(str(yname))
    return _save(fig, outdir, f"scatter_{_safe(yname)}_by_{_safe(xname)}.png")


def plot_residuals(df, outcome, predictors, outdir):
    plt = _plt()
    r = residual_data(df, outcome, predictors)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(r["fitted"], r["std_resid"], color="#4c72b0", s=22)
    ax.axhline(0, color="black", lw=1)
    ax.set_title(f"Standardized residuals vs fitted: {outcome}"); ax.set_xlabel("Fitted value"); ax.set_ylabel("Standardized residual")
    return _save(fig, outdir, f"residuals_{_safe(outcome)}.png")


def plot_clustered_bar(df, row, col, outdir):
    plt = _plt()
    pair = df[[row, col]].dropna()
    tab = pd.crosstab(pair[row], pair[col])
    fig, ax = plt.subplots(figsize=(6, 4))
    tab.plot(kind="bar", ax=ax, rot=0)
    ax.set_title(f"Counts: {row} by {col}"); ax.set_xlabel(str(row)); ax.set_ylabel("Count")
    return _save(fig, outdir, f"clustered_bar_{_safe(row)}_by_{_safe(col)}.png")


def plot_paired_diff(df, first, second, outdir):
    plt = _plt()
    d = df[[first, second]].apply(pd.to_numeric, errors="coerce").dropna()
    return plot_histogram(d[second] - d[first], f"{second} - {first}", outdir)


# ------------------------------------------------------------ dispatcher

def make_plots(df, cfg, result, outdir):
    """Write the charts that fit this analysis into `outdir`; return the list of paths."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    if result.get("valid") is False:
        return []
    action = result.get("action")
    paths = []
    if action == "describe":
        for v in result["variables"]:
            if v["type"] == "numeric":
                paths.append(plot_histogram(df[v["variable"]], v["variable"], out))
    elif action == "frequencies":
        for v in result["variables"]:
            paths.append(plot_bar(df[v["variable"]], v["variable"], out))
    elif action == "crosstab":
        paths.append(plot_clustered_bar(df, result["row"], result["column"], out))
    elif action == "ttest_independent_welch":
        groups = [g["group"] for g in result["groups"]]
        mask = df[result["group"]].isin(groups)
        paths.append(plot_boxplot(df[mask], result["outcome"], result["group"], groups, out))
        paths.append(plot_errorbar(df[mask], result["outcome"], result["group"], groups, out))
    elif action == "ttest_paired":
        paths.append(plot_paired_diff(df, result["first"], result["second"], out))
        paths.append(plot_scatter(df, result["first"], result["second"], out))
    elif action == "one_way_anova":
        groups = [g["group"] for g in result["groups"]]
        mask = df[result["group"]].isin(groups)
        paths.append(plot_boxplot(df[mask], result["outcome"], result["group"], groups, out))
        paths.append(plot_errorbar(df[mask], result["outcome"], result["group"], groups, out))
    elif action == "correlation":
        for p in result["pairs"]:
            if p.get("coefficient") is not None:
                paths.append(plot_scatter(df, p["var1"], p["var2"], out, fit=(result["method"] == "pearson")))
    elif action == "linear_regression_OLS":
        if len(result["predictors"]) == 1:
            paths.append(plot_scatter(df, result["predictors"][0], result["outcome"], out))
        paths.append(plot_residuals(df, result["outcome"], result["predictors"], out))
    elif action == "cronbach_alpha":
        pass
    return paths
