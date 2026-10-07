#!/usr/bin/env python3
"""Small transparent SPSS-style analysis helper; see the skill references for scope."""
from __future__ import annotations
import argparse
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def clean(obj):
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return None if not math.isfinite(float(obj)) else float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if pd.isna(obj):
        return None
    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj
    return str(obj)


def load_data(cfg):
    path = Path(cfg.get("file", ""))
    if not path.is_file():
        raise ValueError(f"Input file not found: {path}")
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path, sheet_name=cfg.get("sheet", 0))
    if ext == ".csv":
        return pd.read_csv(path, **cfg.get("read_csv", {}))
    if ext in (".tsv", ".tab"):
        return pd.read_csv(path, sep="\t", **cfg.get("read_csv", {}))
    if ext == ".sav":
        try:
            return pd.read_spss(path)
        except ImportError as exc:
            raise ValueError("Reading .sav requires pandas and pyreadstat. Install pyreadstat.") from exc
    raise ValueError("Supported files: .csv, .tsv, .xlsx, .xls, .sav")


def require_columns(df, names):
    absent = [n for n in names if n not in df.columns]
    if absent:
        raise ValueError(f"Columns not found: {absent}. Available columns: {list(df.columns)}")


def numeric_series(df, name):
    require_columns(df, [name])
    s = pd.to_numeric(df[name], errors="coerce")
    if s.notna().sum() == 0:
        raise ValueError(f"{name!r} has no usable numeric values")
    return s


def inventory(df):
    vars_out = []
    for name in df.columns:
        s = df[name]
        nonmissing = s.dropna()
        vars_out.append({
            "variable": str(name), "dtype": str(s.dtype), "n_nonmissing": int(s.notna().sum()),
            "n_missing": int(s.isna().sum()), "missing_pct": round(float(s.isna().mean() * 100), 4),
            "n_unique": int(s.nunique(dropna=True)),
            "sample_values": [clean(v) for v in nonmissing.drop_duplicates().head(5).tolist()],
        })
    return {"action": "inventory", "n_rows": int(len(df)), "n_columns": int(len(df.columns)),
            "duplicate_rows": int(df.duplicated().sum()), "variables": vars_out}


def describe(df, variables):
    require_columns(df, variables)
    out = []
    for name in variables:
        s = df[name]
        numeric = pd.to_numeric(s, errors="coerce")
        if numeric.notna().sum() == s.notna().sum() and numeric.notna().sum() > 0:
            x = numeric.dropna()
            row = {"variable": name, "type": "numeric", "n": int(x.size), "missing_n": int(s.isna().sum()),
                   "mean": x.mean(), "sd_sample": x.std(ddof=1), "median": x.median(),
                   "q1": x.quantile(.25), "q3": x.quantile(.75), "min": x.min(), "max": x.max(),
                   "skew": x.skew() if x.size >= 3 else None}
        else:
            counts = s.value_counts(dropna=True)
            row = {"variable": name, "type": "categorical_or_mixed", "n_valid": int(s.notna().sum()),
                   "missing_n": int(s.isna().sum()), "n_unique": int(s.nunique(dropna=True)),
                   "frequencies": [{"value": clean(k), "count": int(v),
                                    "valid_percent": float(v / max(1, s.notna().sum()) * 100)}
                                   for k, v in counts.items()]}
        out.append(row)
    return {"action": "describe", "variables": out}


def frequencies(df, variables):
    require_columns(df, variables)
    out = []
    for name in variables:
        s = df[name]
        counts = s.value_counts(dropna=True, sort=False)
        denom = int(s.notna().sum())
        out.append({"variable": name, "valid_n": denom, "missing_n": int(s.isna().sum()),
                    "categories": [{"value": clean(k), "count": int(v),
                                    "valid_percent": (float(v / denom * 100) if denom else None)}
                                   for k, v in counts.items()]})
    return {"action": "frequencies", "variables": out}


def crosstab(df, row_name, col_name):
    require_columns(df, [row_name, col_name])
    pair = df[[row_name, col_name]].dropna()
    tab = pd.crosstab(pair[row_name], pair[col_name], dropna=False)
    if tab.size == 0:
        raise ValueError("No complete observations for crosstab")
    chi, p, dof, expected = stats.chi2_contingency(tab, correction=False)
    n = int(tab.to_numpy().sum())
    denom = n * max(1, min(tab.shape[0] - 1, tab.shape[1] - 1))
    return {"action": "crosstab", "row": row_name, "column": col_name, "n": n,
            "missing_pairs": int(len(df) - len(pair)),
            "counts": {str(i): {str(j): int(tab.loc[i, j]) for j in tab.columns} for i in tab.index},
            "row_percent": (tab.div(tab.sum(axis=1).replace(0, np.nan), axis=0) * 100).round(6).to_dict(),
            "column_percent": (tab.div(tab.sum(axis=0).replace(0, np.nan), axis=1) * 100).round(6).to_dict(),
            "pearson_chi_square": float(chi), "df": int(dof), "p_two_sided": float(p),
            "cramers_v": float(math.sqrt(chi / denom)) if denom else None,
            "expected_counts_min": float(np.min(expected)),
            "expected_cells_below_5": int(np.sum(expected < 5))}


def ttest(df, cfg):
    yname = cfg.get("outcome")
    if not yname:
        raise ValueError("ttest requires outcome")
    y = numeric_series(df, yname)
    if cfg.get("paired_with"):
        xname = cfg["paired_with"]
        x = numeric_series(df, xname)
        pair = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
        if len(pair) < 2:
            raise ValueError("Paired t-test requires at least two complete pairs")
        d = pair["y"] - pair["x"]
        res = stats.ttest_rel(pair["y"], pair["x"])
        se = d.std(ddof=1) / math.sqrt(len(d))
        ci = stats.t.interval(.95, len(d)-1, loc=d.mean(), scale=se) if se else (d.mean(), d.mean())
        return {"action": "ttest_paired", "first": xname, "second": yname, "n_pairs": int(len(d)),
                "mean_first": float(pair.x.mean()), "mean_second": float(pair.y.mean()),
                "mean_difference_second_minus_first": float(d.mean()), "difference_ci95": list(ci),
                "t": float(res.statistic), "df": int(len(d)-1), "p_two_sided": float(res.pvalue),
                "cohens_dz": float(d.mean()/d.std(ddof=1)) if d.std(ddof=1) else None}
    gname = cfg.get("group")
    if not gname:
        raise ValueError("Independent ttest requires group, or paired_with for paired data")
    require_columns(df, [gname])
    groups = cfg.get("groups")
    if groups is None:
        groups = list(pd.unique(df[gname].dropna()))
    if len(groups) != 2:
        raise ValueError(f"Independent t-test requires exactly two groups; found {groups}")
    vals = []
    summaries = []
    for group in groups:
        x = y[df[gname] == group].dropna().astype(float)
        if len(x) < 2:
            raise ValueError(f"Group {group!r} needs at least two observations")
        vals.append(x)
        summaries.append({"group": clean(group), "n": int(len(x)), "mean": float(x.mean()), "sd": float(x.std(ddof=1))})
    test = stats.ttest_ind(vals[0], vals[1], equal_var=False)
    a, b = vals
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se2 = va/len(a) + vb/len(b)
    dfw = se2**2 / ((va/len(a))**2/(len(a)-1) + (vb/len(b))**2/(len(b)-1)) if se2 else len(a)+len(b)-2
    diff = float(a.mean()-b.mean())
    se = math.sqrt(se2)
    ci = stats.t.interval(.95, dfw, loc=diff, scale=se) if se else (diff, diff)
    pooled = math.sqrt(((len(a)-1)*va + (len(b)-1)*vb)/(len(a)+len(b)-2))
    return {"action": "ttest_independent_welch", "outcome": yname, "group": gname, "groups": summaries,
            "mean_difference_first_minus_second": diff, "difference_ci95": list(ci), "t": float(test.statistic),
            "df_welch": float(dfw), "p_two_sided": float(test.pvalue),
            "cohens_d_pooled_sd_descriptive": float(diff/pooled) if pooled else None}


def anova(df, cfg):
    y = numeric_series(df, cfg.get("outcome", ""))
    gname = cfg.get("group")
    if not gname:
        raise ValueError("anova requires group")
    require_columns(df, [gname])
    groups = []
    summaries = []
    for label, subset in df.assign(__y=y).groupby(gname, observed=True, dropna=True):
        vals = subset["__y"].dropna().astype(float)
        if len(vals) >= 2:
            groups.append(vals)
            summaries.append({"group": clean(label), "n": int(len(vals)), "mean": float(vals.mean()), "sd": float(vals.std(ddof=1))})
    if len(groups) < 2:
        raise ValueError("ANOVA needs at least two groups with two observations each")
    f, p = stats.f_oneway(*groups)
    all_y = np.concatenate([g.to_numpy() for g in groups])
    grand = float(all_y.mean())
    ss_between = sum(len(g)*(float(g.mean())-grand)**2 for g in groups)
    ss_total = float(((all_y-grand)**2).sum())
    n, k = len(all_y), len(groups)
    return {"action": "one_way_anova", "outcome": cfg["outcome"], "group": gname, "groups": summaries,
            "n": int(n), "F": float(f), "df_between": int(k-1), "df_within": int(n-k),
            "p": float(p), "eta_squared": float(ss_between/ss_total) if ss_total else None,
            "note": "Classical one-way ANOVA; equal-variance robustness not assessed by this helper."}


def correlation(df, cfg):
    variables = cfg.get("variables", [])
    if len(variables) < 2:
        raise ValueError("correlation requires at least two variables")
    require_columns(df, variables)
    method = cfg.get("method", "pearson").lower()
    if method not in ("pearson", "spearman"):
        raise ValueError("method must be pearson or spearman")
    out = []
    for i, a in enumerate(variables):
        for b in variables[i+1:]:
            pair = pd.DataFrame({"a": numeric_series(df, a), "b": numeric_series(df, b)}).dropna()
            if len(pair) < 3:
                raise ValueError(f"Correlation {a}/{b} needs at least 3 complete pairs")
            result = stats.pearsonr(pair.a, pair.b) if method == "pearson" else stats.spearmanr(pair.a, pair.b)
            out.append({"var1": a, "var2": b, "method": method, "n": int(len(pair)),
                        "coefficient": float(result.statistic), "p_two_sided": float(result.pvalue)})
    return {"action": "correlation", "method": method, "pairs": out}


def regression(df, cfg):
    try:
        import statsmodels.api as sm
    except ImportError as exc:
        raise ValueError("Regression requires statsmodels") from exc
    outcome = cfg.get("outcome")
    predictors = cfg.get("predictors", [])
    if not outcome or not predictors:
        raise ValueError("regression requires outcome and non-empty predictors")
    require_columns(df, [outcome] + predictors)
    data = df[[outcome] + predictors].apply(pd.to_numeric, errors="coerce").dropna()
    if len(data) <= len(predictors) + 1:
        raise ValueError("Too few complete observations for this model")
    X = sm.add_constant(data[predictors].astype(float), has_constant="add")
    model_type = cfg.get("model", "linear").lower()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        if model_type == "linear":
            fit = sm.OLS(data[outcome].astype(float), X).fit()
            ci = fit.conf_int()
            terms = {str(term): {"B": float(fit.params[term]), "SE": float(fit.bse[term]),
                                 "CI95": [float(ci.loc[term, 0]), float(ci.loc[term, 1])],
                                 "t": float(fit.tvalues[term]), "p": float(fit.pvalues[term])}
                     for term in fit.params.index}
            return {"action": "linear_regression_OLS", "outcome": outcome, "predictors": predictors,
                    "n": int(fit.nobs), "terms": terms, "R_squared": float(fit.rsquared),
                    "adjusted_R_squared": float(fit.rsquared_adj), "F": float(fit.fvalue),
                    "F_df": [float(fit.df_model), float(fit.df_resid)], "model_p": float(fit.f_pvalue),
                    "warnings": [str(w.message) for w in caught],
                    "note": "Numeric predictors only. Classical standard errors; residual and collinearity diagnostics are not included."}
        if model_type == "logistic":
            y = data[outcome]
            if not set(y.unique()).issubset({0, 1}):
                raise ValueError("Logistic outcome must be coded exactly 0/1; specify event coding explicitly before analysis")
            if y.nunique() != 2:
                raise ValueError("Logistic outcome has only one observed class")
            fit = sm.Logit(y.astype(float), X).fit(disp=False, maxiter=200)
            ci = fit.conf_int()
            terms = {str(term): {"B_log_odds": float(fit.params[term]), "SE": float(fit.bse[term]),
                                 "CI95_B": [float(ci.loc[term, 0]), float(ci.loc[term, 1])],
                                 "OR": float(np.exp(fit.params[term])),
                                 "OR_CI95": [float(np.exp(ci.loc[term, 0])), float(np.exp(ci.loc[term, 1]))],
                                 "Wald_p": float(fit.pvalues[term])}
                     for term in fit.params.index}
            return {"action": "binary_logistic_regression", "outcome": outcome, "event_value": 1,
                    "predictors": predictors, "n": int(fit.nobs), "terms": terms,
                    "pseudo_R_squared_McFadden": float(fit.prsquared), "model_LR_p": float(fit.llr_pvalue),
                    "warnings": [str(w.message) for w in caught],
                    "note": "Numeric predictors only; assess separation, model specification, calibration, and logit linearity."}
    raise ValueError("model must be linear or logistic")


def alpha(df, variables):
    if len(variables) < 2:
        raise ValueError("alpha requires at least two items")
    require_columns(df, variables)
    x = df[variables].apply(pd.to_numeric, errors="coerce").dropna()
    k = len(variables)
    if len(x) < 2:
        raise ValueError("Not enough complete cases to estimate alpha")
    variances = x.var(axis=0, ddof=1)
    total_variance = x.sum(axis=1).var(ddof=1)
    result = (k/(k-1)) * (1 - variances.sum()/total_variance) if total_variance > 0 else None
    return {"action": "cronbach_alpha", "items": variables, "k": k, "complete_case_n": int(len(x)),
            "alpha": float(result) if result is not None else None,
            "note": "Listwise-complete items; reverse-code according to the instrument key first. Alpha does not establish validity or unidimensionality."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to UTF-8 JSON analysis request")
    parser.add_argument("--output", help="Write JSON results here (default: stdout)")
    args = parser.parse_args()
    try:
        with open(args.config, encoding="utf-8") as f:
            cfg = json.load(f)
        df = load_data(cfg)
        action = cfg.get("action", "inventory").lower()
        if action == "inventory": result = inventory(df)
        elif action == "describe": result = describe(df, cfg.get("variables", list(df.columns)))
        elif action == "frequencies": result = frequencies(df, cfg.get("variables", []))
        elif action == "crosstab": result = crosstab(df, cfg.get("row", ""), cfg.get("column", ""))
        elif action == "ttest": result = ttest(df, cfg)
        elif action == "anova": result = anova(df, cfg)
        elif action == "correlation": result = correlation(df, cfg)
        elif action == "regression": result = regression(df, cfg)
        elif action == "alpha": result = alpha(df, cfg.get("variables", []))
        else: raise ValueError(f"Unknown action {action!r}")
        result["source_file"] = Path(cfg["file"]).name
        result["source_rows"] = int(len(df))
        result["source_columns"] = int(len(df.columns))
        result["software"] = {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__, "scipy": __import__("scipy").__version__}
        text = json.dumps(clean(result), indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        else:
            print(text, end="")
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
