#!/usr/bin/env python3
"""SPSS-style formatted output for analyze.py results.

This module only *presents* numbers that analyze.py already computed (plus a few
exact arithmetic derivations such as SE = SD / sqrt(N)). It never changes the JSON
contract, and it never invents a statistic: anything it cannot derive is omitted.

    from spss_format import format_result
    print(format_result(result, style="text"))      # fixed-width text tables
    print(format_result(result, style="markdown"))  # Markdown pipe tables
"""
from __future__ import annotations

import math

# ---------------------------------------------------------------- number formats

def fnum(x, d=3):
    """Fixed decimals; blank for missing, like an SPSS empty cell."""
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return ""
    return f"{x:.{d}f}"


def fsig(p):
    """SPSS Sig. convention: three decimals, no leading zero, '.000' when p < .0005."""
    if p is None or (isinstance(p, float) and not math.isfinite(p)):
        return ""
    if p < 0.0005:
        return ".000"
    return f"{p:.3f}".lstrip("0") if p < 1 else "1.000"


def fcorr(r, d=3):
    """Correlation-like value without a leading zero (.610, -.254)."""
    if r is None:
        return ""
    s = f"{r:.{d}f}"
    if s.startswith("0."):
        return s[1:]
    if s.startswith("-0."):
        return "-" + s[2:]
    return s


def fint(x):
    return "" if x is None else f"{int(x):d}"


def fpct(x, d=1):
    return "" if x is None else f"{x:.{d}f}"


def fcell(v, d=3):
    if isinstance(v, (int,)) and not isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return fnum(v, d)
    return "" if v is None else str(v)


# ---------------------------------------------------------------- table model

class Table:
    def __init__(self, title, columns, rows, notes=None, align=None):
        self.title = title
        self.columns = [str(c) for c in columns]
        self.rows = [[("" if c is None else str(c)) for c in r] for r in rows]
        self.notes = list(notes or [])
        # first column left-aligned, the rest right-aligned unless told otherwise
        self.align = align or (["l"] + ["r"] * (len(self.columns) - 1))

    def widths(self):
        w = [len(c) for c in self.columns]
        for r in self.rows:
            for i, c in enumerate(r):
                w[i] = max(w[i], len(c))
        return w

    def to_text(self):
        w = self.widths()

        def line(cells):
            out = []
            for i, c in enumerate(cells):
                out.append(c.ljust(w[i]) if self.align[i] == "l" else c.rjust(w[i]))
            return "| " + " | ".join(out) + " |"

        rule = "+" + "+".join("-" * (x + 2) for x in w) + "+"
        lines = [self.title, rule, line(self.columns), rule]
        lines += [line(r) for r in self.rows]
        lines.append(rule)
        for n in self.notes:
            lines.append(n)
        return "\n".join(lines)

    def to_markdown(self):
        def esc(c):
            return c.replace("|", "\\|")
        head = "| " + " | ".join(esc(c) for c in self.columns) + " |"
        sep = "|" + "|".join(" :--- " if a == "l" else " ---: " for a in self.align) + "|"
        body = ["| " + " | ".join(esc(c) for c in r) + " |" for r in self.rows]
        out = [f"**{self.title}**", "", head, sep] + body
        if self.notes:
            out.append("")
            out += [f"_{n}_" for n in self.notes]
        return "\n".join(out)


def render(tables, style):
    if style == "markdown":
        return "\n\n".join(t.to_markdown() for t in tables)
    return "\n\n".join(t.to_text() for t in tables)


# ---------------------------------------------------------------- helpers

def _sort_key(v):
    try:
        return (0, float(v), "")
    except (TypeError, ValueError):
        return (1, 0.0, str(v))


def _label(v):
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def audit_notes(res):
    a = res.get("data_audit") or {}
    notes = []
    if a.get("rows_total") is not None:
        used = a.get("rows_used")
        notes.append(f"Rows read: {a['rows_total']}" + (f"; rows used: {used}" if used is not None else "; rows used differ by variable pair (see pairwise N)"))
    for e in a.get("exclusions", []):
        who = f" [{e['variable']}]" if e.get("variable") else (f" [{e['group']}]" if e.get("group") is not None else "")
        notes.append(f"Excluded: {e.get('reason')}{who}: {e.get('count')}")
    return notes


def case_processing(res, n_label="N"):
    a = res.get("data_audit") or {}
    total, used = a.get("rows_total"), a.get("rows_used")
    if total is None or used is None or not total:
        return None
    return Table("Case Processing Summary", ["", "N", "Percent"],
                 [["Valid", used, fpct(used / total * 100)],
                  ["Excluded", total - used, fpct((total - used) / total * 100)],
                  ["Total", total, "100.0"]])


# ---------------------------------------------------------------- per action

def _inventory(res):
    rows = []
    for v in res["variables"]:
        rows.append([v["variable"], v["dtype"], v["n_nonmissing"], v["n_missing"], fpct(v["missing_pct"]), v["n_unique"],
                     ", ".join(_label(x) for x in v["sample_values"][:4])])
    notes = [f"{res['n_rows']} rows x {res['n_columns']} columns; duplicate rows: {res['duplicate_rows']}"]
    notes += [f"{v['variable']}: {v['note']}" for v in res["variables"] if v.get("note")]
    return [Table("Variable Information", ["Variable", "Type", "Valid N", "Missing N", "Missing %", "Unique", "Sample values"],
                  rows, notes, align=["l", "l", "r", "r", "r", "r", "l"])]


def _describe(res):
    tabs = []
    num = [v for v in res["variables"] if v["type"] == "numeric"]
    if num:
        rows = []
        for v in num:
            se = v["sd_sample"] / math.sqrt(v["n"]) if v["n"] > 0 and v["sd_sample"] is not None else None
            rows.append([v["variable"], v["n"], v["missing_n"], fnum(v["min"]), fnum(v["max"]), fnum(v["mean"]), fnum(se),
                         fnum(v["sd_sample"]), fnum(v["median"]), fnum(v["q1"]), fnum(v["q3"]), fnum(v["skew"])])
        tabs.append(Table("Descriptive Statistics",
                          ["Variable", "N", "Missing", "Minimum", "Maximum", "Mean", "Std. Error", "Std. Deviation", "Median", "25th", "75th", "Skewness"],
                          rows, ["Std. Deviation uses n-1. Percentiles are linear-interpolated and may differ slightly from SPSS's default weighted-average method."]))
    for v in res["variables"]:
        if v["type"] != "numeric":
            fr = {"variable": v["variable"], "valid_n": v["n_valid"], "missing_n": v["missing_n"],
                  "categories": v["frequencies"]}
            tabs += _freq_tables(fr)
    return tabs


def _freq_tables(v):
    cats = sorted(v["categories"], key=lambda c: _sort_key(c["value"]))
    valid, miss = v["valid_n"], v["missing_n"]
    total = valid + miss
    rows, cum = [], 0.0
    for c in cats:
        vp = c["valid_percent"] or 0.0
        cum += vp
        rows.append([_label(c["value"]), c["count"], fpct(c["count"] / total * 100 if total else None),
                     fpct(vp), fpct(100.0 if abs(cum - 100) < 1e-9 else cum)])
    rows.append(["Total (valid)", valid, fpct(valid / total * 100 if total else None), "100.0" if valid else "", ""])
    if miss:
        rows.append(["Missing", miss, fpct(miss / total * 100), "", ""])
        rows.append(["Total", total, "100.0", "", ""])
    return [Table(f"Frequencies: {v['variable']}", ["Value", "Frequency", "Percent", "Valid Percent", "Cumulative Percent"], rows,
                  [f"Valid N = {valid}; Missing N = {miss}."])]


def _frequencies(res):
    tabs = []
    stat_rows = [[v["variable"], v["valid_n"], v["missing_n"]] for v in res["variables"]]
    tabs.append(Table("Statistics", ["Variable", "N Valid", "N Missing"], stat_rows))
    for v in res["variables"]:
        tabs += _freq_tables(v)
    return tabs


def _crosstab(res):
    r, c = res["row"], res["column"]
    counts = res["counts"]
    rows_k = sorted(counts, key=_sort_key)
    cols_k = sorted({k for d in counts.values() for k in d}, key=_sort_key)
    tabs = []
    cp = case_processing(res)
    if cp:
        tabs.append(cp)
    body = []
    n = res["n"]
    col_tot = {k: sum(counts[i][k] for i in rows_k) for k in cols_k}
    for i in rows_k:
        tot = sum(counts[i].values())
        body.append([f"{i}", "Count"] + [counts[i][k] for k in cols_k] + [tot])
        body.append(["", f"% within {r}"] + [fpct(counts[i][k] / tot * 100 if tot else None) for k in cols_k] + ["100.0"])
    body.append(["Total", "Count"] + [col_tot[k] for k in cols_k] + [n])
    body.append(["", f"% within {c}"] + [fpct(col_tot[k] / n * 100) for k in cols_k] + ["100.0"])
    tabs.append(Table(f"{r} * {c} Crosstabulation", [r, ""] + [f"{c}={k}" for k in cols_k] + ["Total"], body,
                      align=["l", "l"] + ["r"] * (len(cols_k) + 1)))
    pearson = [["Pearson Chi-Square", fnum(res["pearson_chi_square"]), res["df"], fsig(res["p_two_sided"])], ["N of Valid Cases", n, "", ""]]
    exp_note = (f"{res['expected_cells_below_5']} cells have expected count less than 5. "
                f"The minimum expected count is {fnum(res['expected_counts_min'], 2)}.")
    if res["expected_cells_below_5"]:
        exp_note += " Chi-square approximation may be unreliable; consider Fisher's exact test for 2x2 tables."
    tabs.append(Table("Chi-Square Tests", ["", "Value", "df", "Asymp. Sig. (2-sided)"], pearson,
                      [exp_note, "No continuity correction or likelihood-ratio/Fisher rows are computed by this helper."]))
    tabs.append(Table("Symmetric Measures", ["", "Value"], [["Cramer's V", fnum(res["cramers_v"])], ["N of Valid Cases", n]],
                      ["Cramer's V is computed from the Pearson chi-square; Phi equals V for a 2x2 table."]))
    return tabs


def _ttest_ind(res):
    g = res["groups"]
    rows = [[_label(x["group"]), x["n"], fnum(x["mean"]), fnum(x["sd"]), fnum(x["sd"] / math.sqrt(x["n"]))] for x in g]
    tabs = [Table("Group Statistics", [res["group"], "N", "Mean", "Std. Deviation", "Std. Error Mean"], rows,
                  [f"Dependent variable: {res['outcome']}."])]
    diff, t = res["mean_difference_first_minus_second"], res["t"]
    se = res.get("standard_error_welch", abs(diff / t) if t else None)
    ci = res["difference_ci95"]
    rows = [["Equal variances not assumed (Welch)", fnum(t), fnum(res["df_welch"]), fsig(res["p_two_sided"]), fnum(diff), fnum(se), fnum(ci[0]), fnum(ci[1])]]
    if res.get("pooled_variance"):
        v=res["pooled_variance"]; c=v["difference_ci95"]
        rows.insert(0,["Equal variances assumed", fnum(v["t"]), fnum(v["df"]), fsig(v["p_two_sided"]), fnum(diff), fnum(v["standard_error"]), fnum(c[0]), fnum(c[1])])
    tabs.append(Table("Independent Samples Test", ["", "t", "df", "Sig. (2-tailed)", "Mean Difference", "Std. Error Difference", "95% CI Lower", "95% CI Upper"], rows,
                      [f"Mean difference = mean({_label(g[0]['group'])}) - mean({_label(g[1]['group'])}).", "Welch is the robust default; do not select a row solely from a Levene p-value."]))
    if res.get("levene"):
        v=res["levene"]
        tabs.append(Table("Levene's Test for Equality of Variances", ["Center","F","df1","df2","Sig."], [[v["center"],fnum(v["F"]),v["df1"],v["df2"],fsig(v["p"])]], [] if v["valid"] else ["Levene inference undefined: deviations have zero residual variance."]))
    tabs.append(Table("Independent Samples Effect Size", ["", "Point Estimate"],
                      [["Cohen's d (pooled SD, descriptive)", fnum(res.get("cohens_d_pooled_sd_descriptive"))]]))
    return tabs


def _ttest_paired(res):
    n = res["n_pairs"]
    d = res["mean_difference_second_minus_first"]
    t = res["t"]
    se = abs(d / t) if t else None
    ci = res["difference_ci95"]
    sd_d = se * math.sqrt(n) if se is not None else None
    tabs = [Table("Paired Samples Statistics", ["", "Mean", "N"],
                  [[res["first"], fnum(res["mean_first"]), n], [res["second"], fnum(res["mean_second"]), n]])]
    tabs.append(Table("Paired Samples Test",
                      ["Pair", "Mean", "Std. Deviation", "Std. Error Mean", "95% CI Lower", "95% CI Upper", "t", "df", "Sig. (2-tailed)"],
                      [[f"{res['second']} - {res['first']}", fnum(d), fnum(sd_d), fnum(se), fnum(ci[0]), fnum(ci[1]), fnum(t), res["df"], fsig(res["p_two_sided"])]]))
    tabs.append(Table("Paired Samples Effect Size", ["", "Point Estimate"], [["Cohen's dz", fnum(res.get("cohens_dz"))]]))
    return tabs


def _anova(res):
    g = res["groups"]
    rows = []
    for x in g:
        se = x["sd"] / math.sqrt(x["n"])
        rows.append([_label(x["group"]), x["n"], fnum(x["mean"]), fnum(x["sd"]), fnum(se)])
    tot_n = res["n"]
    grand = sum(x["n"] * x["mean"] for x in g) / tot_n
    rows.append(["Total", tot_n, fnum(grand), "", ""])
    tabs = [Table(f"Descriptives: {res['outcome']}", [res["group"], "N", "Mean", "Std. Deviation", "Std. Error"], rows)]
    ss = res.get("sum_of_squares")
    if ss is None:
        ssb = sum(x["n"] * (x["mean"] - grand) ** 2 for x in g)
        ssw = sum((x["n"] - 1) * x["sd"] ** 2 for x in g)
        ss = {"between": ssb, "within": ssw, "total": ssb + ssw}
    msb = ss["between"] / res["df_between"]
    msw = ss["within"] / res["df_within"] if res["df_within"] else None
    tabs.append(Table(f"ANOVA: {res['outcome']}", ["", "Sum of Squares", "df", "Mean Square", "F", "Sig."],
                      [["Between Groups", fnum(ss["between"]), res["df_between"], fnum(msb), fnum(res["F"]), fsig(res["p"])],
                       ["Within Groups", fnum(ss["within"]), res["df_within"], fnum(msw), "", ""],
                       ["Total", fnum(ss["total"]), res["df_between"] + res["df_within"], "", "", ""]],
                      [f"Eta squared = {fnum(res.get('eta_squared'))}.",
                       "Homogeneity of variance (Levene) and post hoc tests are not computed by this helper."]))
    return tabs


def _correlation(res):
    tabs = []
    names = []
    for p in res["pairs"]:
        for v in (p["var1"], p["var2"]):
            if v not in names:
                names.append(v)
    method = "Pearson Correlation" if res["method"] == "pearson" else "Spearman's rho"
    lookup = {}
    for p in res["pairs"]:
        lookup[(p["var1"], p["var2"])] = p
        lookup[(p["var2"], p["var1"])] = p
    rows = []
    for a in names:
        r1, r2, r3 = [a, method], ["", "Sig. (2-tailed)"], ["", "N"]
        for b in names:
            if a == b:
                r1.append("1"); r2.append(""); r3.append("")
            else:
                p = lookup.get((a, b))
                if p is None or p.get("coefficient") is None:
                    r1.append(""); r2.append(""); r3.append(p["n"] if p else "")
                else:
                    r1.append(fcorr(p["coefficient"])); r2.append(fsig(p["p_two_sided"])); r3.append(p["n"])
        rows += [r1, r2, r3]
    tabs.append(Table("Correlations", ["", ""] + names, rows, [
        f"Missing data policy: {res.get('missing_policy', 'pairwise')}. N is per pair.",
        "No multiplicity adjustment is applied; with many pairs, treat p-values as exploratory.",
        "Sig. is two-tailed."], align=["l", "l"] + ["r"] * len(names)))
    return tabs


def _linear(res):
    ms = res.get("model_summary", {})
    tabs = [Table("Model Summary", ["R", "R Square", "Adjusted R Square", "Std. Error of the Estimate"],
                  [[fnum(ms.get("R")), fnum(res["R_squared"]), fnum(res["adjusted_R_squared"]), fnum(ms.get("std_error_of_estimate"))]],
                  [f"Dependent variable: {res['outcome']}. Predictors: (Constant), {', '.join(res['predictors'])}."])]
    ss = ms.get("sum_of_squares")
    if ss:
        dfr, dfe = res["F_df"]
        msr = ss["regression"] / dfr
        mse = ss["residual"] / dfe
        tabs.append(Table("ANOVA", ["", "Sum of Squares", "df", "Mean Square", "F", "Sig."],
                          [["Regression", fnum(ss["regression"]), int(dfr), fnum(msr), fnum(res["F"]), fsig(res["model_p"])],
                           ["Residual", fnum(ss["residual"]), int(dfe), fnum(mse), "", ""],
                           ["Total", fnum(ss["total"]), int(dfr + dfe), "", "", ""]]))
    rows = []
    for name, tm in res["terms"].items():
        label = "(Constant)" if name == res.get("_intercept", "const") or name not in res["predictors"] else name
        rows.append([label, fnum(tm["B"]), fnum(tm["SE"]), fcorr(tm.get("beta_standardized")) if name in res["predictors"] else "",
                     fnum(tm["t"]), fsig(tm["p"]), fnum(tm["CI95"][0]), fnum(tm["CI95"][1])])
    tabs.append(Table("Coefficients", ["", "B", "Std. Error", "Beta", "t", "Sig.", "95% CI Lower (B)", "95% CI Upper (B)"], rows,
                      [f"Dependent variable: {res['outcome']}. Classical (non-robust) standard errors."]))
    return tabs


def _logistic(res):
    tabs = []
    mf = res.get("model_fit")
    if mf:
        tabs.append(Table("Omnibus Test of Model Coefficients", ["", "Chi-square", "df", "Sig."],
                          [["Model", fnum(mf["chi_square"]), mf["df"], fsig(res["model_LR_p"])]]))
        tabs.append(Table("Model Summary", ["-2 Log likelihood", "Cox & Snell R Square", "Nagelkerke R Square", "McFadden R Square"],
                          [[fnum(mf["neg2_log_likelihood"]), fnum(mf["cox_snell_R2"]), fnum(mf["nagelkerke_R2"]), fnum(res["pseudo_R_squared_McFadden"])]],
                          [f"Event modeled: {res['outcome']} = {res['event_value']}."]))
    cl = res.get("classification")
    if cl:
        n0 = cl["observed_0_predicted_0"] + cl["observed_0_predicted_1"]
        n1 = cl["observed_1_predicted_0"] + cl["observed_1_predicted_1"]
        pc0 = cl["observed_0_predicted_0"] / n0 * 100 if n0 else None
        pc1 = cl["observed_1_predicted_1"] / n1 * 100 if n1 else None
        tabs.append(Table(f"Classification Table (cut value {cl['cutoff']})",
                          ["Observed", "Predicted 0", "Predicted 1", "Percentage Correct"],
                          [["0", cl["observed_0_predicted_0"], cl["observed_0_predicted_1"], fpct(pc0)],
                           ["1", cl["observed_1_predicted_0"], cl["observed_1_predicted_1"], fpct(pc1)],
                           ["Overall Percentage", "", "", fpct(cl["overall_percent_correct"])]]))
    rows = []
    for name, tm in res["terms"].items():
        wald = (tm["B_log_odds"] / tm["SE"]) ** 2 if tm["SE"] else None
        label = name if name in res["predictors"] else "Constant"
        rows.append([label, fnum(tm["B_log_odds"]), fnum(tm["SE"]), fnum(wald), 1, fsig(tm["Wald_p"]), fnum(tm["OR"]),
                     fnum(tm["OR_CI95"][0]), fnum(tm["OR_CI95"][1])])
    tabs.append(Table("Variables in the Equation", ["", "B", "S.E.", "Wald", "df", "Sig.", "Exp(B)", "95% CI Exp(B) Lower", "95% CI Exp(B) Upper"], rows,
                      ["Wald = (B / S.E.)^2. Intercept row is labeled Constant."]))
    return tabs


def _alpha(res):
    tabs = [Table("Case Processing Summary", ["", "N", "Percent"], _alpha_cases(res)),
            Table("Reliability Statistics", ["Cronbach's Alpha", "N of Items"], [[fnum(res["alpha"]), res["k"]]])]
    return tabs


def _alpha_cases(res):
    a = res.get("data_audit") or {}
    total, used = a.get("rows_total"), res["complete_case_n"]
    total = total or used
    return [["Valid", used, fpct(used / total * 100)], ["Excluded (listwise)", total - used, fpct((total - used) / total * 100)],
            ["Total", total, "100.0"]]


TITLES = {
    "inventory": "Data Inventory", "describe": "Descriptives", "frequencies": "Frequencies", "crosstab": "Crosstabs",
    "ttest_independent_welch": "T-Test", "ttest_paired": "T-Test", "one_way_anova": "Oneway",
    "correlation": "Correlations", "linear_regression_OLS": "Regression", "binary_logistic_regression": "Logistic Regression",
    "cronbach_alpha": "Reliability",
}
BUILDERS = {
    "inventory": _inventory, "describe": _describe, "frequencies": _frequencies, "crosstab": _crosstab,
    "ttest_independent_welch": _ttest_ind, "ttest_paired": _ttest_paired, "one_way_anova": _anova,
    "correlation": _correlation, "linear_regression_OLS": _linear, "binary_logistic_regression": _logistic,
    "cronbach_alpha": _alpha,
}


def build_tables(res):
    """Return (title, [Table, ...], warnings) for one analyze.py result."""
    action = res.get("action")
    title = TITLES.get(action, str(action))
    warnings = []
    if res.get("valid") is False:
        warnings.append(f"RESULT INVALID: {res.get('reason', 'inference not defined')}. No inferential statistics are reported.")
        tables = []
        if res.get("groups") and isinstance(res["groups"][0], dict):
            tables.append(Table("Group Statistics", ["Group", "N", "Mean", "Std. Deviation"],
                                [[_label(g["group"]), g["n"], fnum(g["mean"]), fnum(g["sd"])] for g in res["groups"]]))
        for w in res.get("warnings", []):
            warnings.append(str(w))
        if res.get("converged") is False:
            warnings.append("Convergence: the maximum-likelihood fit did not converge.")
        return title, tables, warnings
    if action == "correlation":
        # correlation may be valid overall but contain pair-level undefined results
        for p in res.get("pairs", []):
            if p.get("valid") is False:
                warnings.append(f"Pair {p['var1']} x {p['var2']}: {p.get('reason', 'correlation undefined')}.")
    builder = BUILDERS.get(action, _extended)
    if builder is None:
        raise ValueError(f"No formatter for action {action!r}")
    tables = builder(res)
    for w in res.get("warnings", []) or []:
        warnings.append(str(w))
    return title, tables, warnings


def _extended(res):
    if res["action"] == "prepare":
        return [Table("Transformation audit", ["Kind","Source","Target / reference","Matched","Unmatched"], [[t["kind"],t["source"],t.get("target",t.get("reference")),t.get("matched"),t.get("unmatched_nonmissing")] for t in res["transformations"]], ["Source columns preserved. Raw records are not displayed in reports."])]
    if res["action"] == "levene":
        return [Table("Test of Homogeneity of Variances", ["Center","F","df1","df2","Sig."], [[res["center"],fnum(res["F"]),res["df1"],res["df2"],fsig(res["p"])]])]
    if res["action"] in ("mann_whitney","wilcoxon","kruskal_wallis","fisher_exact"):
        return [Table("Test Statistics", ["Procedure","N","Statistic / Odds ratio","df","Sig. (2-sided)","Method"], [[res["action"],res["n"],fnum(res.get("statistic",res.get("odds_ratio"))),res.get("df"),fsig(res["p"]),res["method"]]])]
    if res["action"] == "welch_anova":
        return [Table("Robust Tests of Equality of Means", ["","F","df1","df2","Sig."], [["Welch",fnum(res["F"]),fnum(res["df1"]),fnum(res["df2"]),fsig(res["p"])]])]
    if res["action"] in ("tukey","games_howell"):
        return [Table("Multiple Comparisons: " + res["action"], ["First","Second","Difference (second-first)","Sig. adjusted","CI Lower","CI Upper"], [[p["first"],p["second"],fnum(p["difference_second_minus_first"]),fsig(p["p_adjusted"]),fnum(p["ci95"][0]),fnum(p["ci95"][1])] for p in res["comparisons"]])]
    if res["action"] in ("anova_two_way","ancova"):
        return [Table("Tests of Between-Subjects Effects", ["Source","Type " + str(res["ss_type"]) + " SS","df","F","Sig."], [[r["term"],fnum(r["sum_sq"]),fnum(r["df"]),fnum(r["F"]),fsig(r["p"])] for r in res["terms"]], ["Sum-to-zero contrasts; listwise complete cases."])]
    if res["action"] == "anova_repeated":
        rows=[["Sphericity assumed",1,fnum(res["F"]),fnum(res["df1"]),fnum(res["df2"]),fsig(res["p"])]]
        rows += [[name,fnum(c["epsilon"]),fnum(res["F"]),fnum(c["df1"]),fnum(c["df2"]),fsig(c["p"])] for name,c in res["corrections"].items() if c["valid"]]
        v=res["sphericity"]
        return [Table("Tests of Within-Subjects Effects",["Correction","Epsilon","F","df1","df2","Sig."],rows),Table("Mauchly's Test of Sphericity",["W","Chi-square","df","Sig."],[[fnum(v["W"]),fnum(v["chi_square"]),v["df"],fsig(v["p"])]],[] if v["valid"] else ["Sphericity diagnostic undefined; not evidence it passed."])]
    if res["action"] == "pca":
        return [Table("Total Variance Explained (retained components)",["Component","Eigenvalue","Percent"],[[i+1,fnum(v),fpct(res["explained_variance_ratio"][i]*100)] for i,v in enumerate(res["eigenvalues"])]),Table("Component Matrix: " + res["rotation"],["Variable"]+[str(i+1) for i in range(res["n_components"])]+["Communality"],[[v]+[fnum(x) for x in res["loadings"][i]]+[fnum(res["communalities"][i])] for i,v in enumerate(res["variables"])])]
    raise ValueError(f"No formatter for action {res['action']!r}")


def format_result(res, style="text"):
    """Render one analysis result as SPSS-style tables."""
    if style not in ("text", "markdown"):
        raise ValueError("style must be 'text' or 'markdown'")
    title, tables, warnings = build_tables(res)
    head = [title] if style == "text" else [f"## {title}"]
    parts = ["\n".join(head)]
    if warnings:
        parts.append("\n".join(("Warnings:" if style == "text" else "**Warnings**") + "\n" + "\n".join(f"- {w}" for w in warnings)
                               for _ in [0]))
    if tables:
        parts.append(render(tables, style))
    notes = audit_notes(res)
    if notes:
        parts.append(("Data audit:\n" if style == "text" else "**Data audit**\n\n") + "\n".join(f"- {n}" for n in notes))
    if res.get("note"):
        parts.append(f"Note: {res['note']}")
    return "\n\n".join(parts)
