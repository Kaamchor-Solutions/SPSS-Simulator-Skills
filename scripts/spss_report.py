#!/usr/bin/env python3
"""Turn one or more analyses into a readable SPSS-style report (Markdown or HTML).

    python scripts/spss_report.py --config report-request.json --output report.html

report-request.json:
    {"file": "examples/demo.csv", "title": "Treatment study",
     "analyses": [{"action": "describe", "variables": ["score"]},
                  {"action": "ttest", "outcome": "score", "group": "group", "groups": ["control", "active"]}],
     "plots": true}

Every number in the report comes from analyze.py; this layer only formats, words,
and assembles. Output ending in .html is self-contained (charts embedded as PNG);
anything else is Markdown (charts are written next to the file and linked).
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import math
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze  # noqa: E402
import spss_format as sf  # noqa: E402


# ------------------------------------------------------------------ APA wording

def apa_p(p):
    if p is None:
        return "p = n/a"
    if p < 0.001:
        return "p < .001"
    return "p = " + f"{p:.3f}".lstrip("0")


def _n(x, d=2):
    return f"{x:.{d}f}"


def _r(x, d=2):
    s = f"{x:.{d}f}"
    return s.replace("0.", ".", 1) if s.startswith("0.") else s.replace("-0.", "-.", 1)


def verdict(p, alpha=0.05):
    return "statistically significant" if p is not None and p < alpha else "not statistically significant"


def interpret(res):
    """Plain-language, APA-style sentences for one result. Association wording only."""
    a = res.get("action")
    if res.get("valid") is False:
        return [f"This analysis could not be interpreted: {res.get('reason', 'inference is undefined')}."]
    if a == "inventory":
        flagged = [v["variable"] for v in res["variables"] if v["n_missing"]]
        s = f"The file has {res['n_rows']} rows and {res['n_columns']} variables ({res['duplicate_rows']} duplicate rows)."
        if flagged:
            s += f" Variables with missing values: {', '.join(flagged)}."
        return [s]
    if a == "describe":
        out = []
        for v in res["variables"]:
            if v["type"] == "numeric":
                out.append(f"{v['variable']}: M = {_n(v['mean'])}, SD = {_n(v['sd_sample'])}, Mdn = {_n(v['median'])}, range {_n(v['min'])} to {_n(v['max'])}, n = {v['n']}.")
            else:
                top = max(v["frequencies"], key=lambda f: f["count"])
                out.append(f"{v['variable']}: {v['n_unique']} categories; most common is {sf._label(top['value'])} ({_n(top['valid_percent'], 1)}%).")
        return out
    if a == "frequencies":
        out = []
        for v in res["variables"]:
            if v["categories"]:
                top = max(v["categories"], key=lambda c: c["count"])
                out.append(f"{v['variable']}: {v['valid_n']} valid cases; most common is {sf._label(top['value'])} ({_n(top['valid_percent'], 1)}%)." + (f" {v['missing_n']} missing." if v["missing_n"] else ""))
        return out
    if a == "crosstab":
        return [f"A chi-square test of association between {res['row']} and {res['column']} was {verdict(res['p_two_sided'])}, "
                f"chi-square({res['df']}, N = {res['n']}) = {_n(res['pearson_chi_square'])}, {apa_p(res['p_two_sided'])}, Cramer's V = {_r(res['cramers_v'])}."
                + (f" {res['expected_cells_below_5']} cells have expected counts below 5, so the approximation may be unreliable." if res["expected_cells_below_5"] else "")]
    if a == "ttest_independent_welch":
        g1, g2 = res["groups"]
        d = res["mean_difference_first_minus_second"]
        ci = res["difference_ci95"]
        return [f"A Welch independent-samples t test compared {res['outcome']} for {sf._label(g1['group'])} (M = {_n(g1['mean'])}, SD = {_n(g1['sd'])}, n = {g1['n']}) "
                f"and {sf._label(g2['group'])} (M = {_n(g2['mean'])}, SD = {_n(g2['sd'])}, n = {g2['n']}). The difference was {verdict(res['p_two_sided'])}, "
                f"t({_n(res['df_welch'])}) = {_n(res['t'])}, {apa_p(res['p_two_sided'])}; mean difference = {_n(d)}, 95% CI [{_n(ci[0])}, {_n(ci[1])}], Cohen's d = {_n(res['cohens_d_pooled_sd_descriptive'])}."]
    if a == "ttest_paired":
        ci = res["difference_ci95"]
        return [f"A paired-samples t test compared {res['second']} (M = {_n(res['mean_second'])}) with {res['first']} (M = {_n(res['mean_first'])}) across {res['n_pairs']} pairs. "
                f"The mean change was {_n(res['mean_difference_second_minus_first'])}, 95% CI [{_n(ci[0])}, {_n(ci[1])}], t({res['df']}) = {_n(res['t'])}, {apa_p(res['p_two_sided'])}, "
                f"{verdict(res['p_two_sided'])}; Cohen's dz = {_n(res['cohens_dz'])}."]
    if a == "one_way_anova":
        return [f"A one-way ANOVA of {res['outcome']} across {len(res['groups'])} {res['group']} groups was {verdict(res['p'])}, "
                f"F({res['df_between']}, {res['df_within']}) = {_n(res['F'])}, {apa_p(res['p'])}, eta squared = {_r(res['eta_squared'])}. "
                "A significant F does not say which groups differ; post hoc comparisons are not computed here."]
    if a == "correlation":
        name = "Pearson r" if res["method"] == "pearson" else "Spearman rho"
        out = []
        for p in res["pairs"]:
            if p.get("coefficient") is None:
                out.append(f"{p['var1']} and {p['var2']}: correlation undefined ({p.get('reason', 'no variation')}).")
            else:
                out.append(f"{p['var1']} and {p['var2']}: {name} = {_r(p['coefficient'])}, {apa_p(p['p_two_sided'])}, n = {p['n']} ({verdict(p['p_two_sided'])}).")
        return out
    if a == "linear_regression_OLS":
        dfr, dfe = res["F_df"]
        s = (f"The linear model predicting {res['outcome']} explained R squared = {_r(res['R_squared'])} of the variance (adjusted {_r(res['adjusted_R_squared'])}), "
             f"F({int(dfr)}, {int(dfe)}) = {_n(res['F'])}, {apa_p(res['model_p'])}, N = {res['n']}.")
        parts = [f"{p}: B = {_n(res['terms'][p]['B'])}, 95% CI [{_n(res['terms'][p]['CI95'][0])}, {_n(res['terms'][p]['CI95'][1])}], {apa_p(res['terms'][p]['p'])}" for p in res["predictors"]]
        return [s, "Coefficients: " + "; ".join(parts) + ". These are associations, not causal effects."]
    if a == "binary_logistic_regression":
        mf = res.get("model_fit", {})
        s = f"The logistic model for {res['outcome']} = {res['event_value']} (N = {res['n']}) "
        if mf:
            s += f"{'was' if res['model_LR_p'] < .05 else 'was not'} statistically significant overall, chi-square({mf['df']}) = {_n(mf['chi_square'])}, {apa_p(res['model_LR_p'])}; Nagelkerke R squared = {_r(mf['nagelkerke_R2'])}."
        parts = [f"{p}: OR = {_n(res['terms'][p]['OR'])}, 95% CI [{_n(res['terms'][p]['OR_CI95'][0])}, {_n(res['terms'][p]['OR_CI95'][1])}], {apa_p(res['terms'][p]['Wald_p'])}" for p in res["predictors"]]
        return [s, "Odds ratios: " + "; ".join(parts) + ". These are associations, not causal effects."]
    if a == "cronbach_alpha":
        al = res["alpha"]
        band = "excellent" if al >= .9 else "good" if al >= .8 else "acceptable" if al >= .7 else "questionable" if al >= .6 else "poor"
        return [f"Internal consistency of the {res['k']} items was {band} by conventional thresholds, Cronbach's alpha = {_r(al)} (n = {res['complete_case_n']}). Alpha does not establish validity or unidimensionality."]
    return []


def limitations(res):
    out = []
    if res.get("note"):
        out.append(res["note"])
    for w in res.get("warnings", []) or []:
        out.append(f"Warning: {w}")
    for e in (res.get("data_audit") or {}).get("exclusions", []):
        out.append(f"Exclusion: {e.get('reason')} ({e.get('count')})")
    return out


# ------------------------------------------------------------------ SPSS syntax

def spss_syntax(cfg, res):
    """Equivalent SPSS command syntax for a request. Not executed by this tool."""
    a = cfg.get("action", "inventory").lower()
    f = cfg.get("file", "")
    if a == "inventory":
        return "DISPLAY DICTIONARY."
    if a == "describe":
        return f"DESCRIPTIVES VARIABLES={' '.join(cfg.get('variables', []))} /STATISTICS=MEAN STDDEV MIN MAX SEMEAN SKEWNESS."
    if a == "frequencies":
        return f"FREQUENCIES VARIABLES={' '.join(cfg.get('variables', []))} /ORDER=ANALYSIS."
    if a == "crosstab":
        return f"CROSSTABS /TABLES={cfg.get('row')} BY {cfg.get('column')} /STATISTICS=CHISQ PHI /CELLS=COUNT ROW COLUMN."
    if a == "ttest":
        if cfg.get("paired_with"):
            return f"T-TEST PAIRS={cfg['outcome']} WITH {cfg['paired_with']} (PAIRED) /CRITERIA=CI(.95)."
        g = cfg.get("groups") or [x["group"] for x in res.get("groups", [])]
        codes = " ".join(str(x) for x in g)
        return (f"T-TEST GROUPS={cfg.get('group')}({codes}) /VARIABLES={cfg['outcome']} /CRITERIA=CI(.95).\n"
                "* Both equal-variance and Welch rows are computed; interpretation defaults to Welch.")
    if a == "anova":
        return f"ONEWAY {cfg['outcome']} BY {cfg['group']} /STATISTICS DESCRIPTIVES HOMOGENEITY."
    if a == "correlation":
        m = "SPEARMAN" if cfg.get("method") == "spearman" else "CORRELATIONS"
        if m == "SPEARMAN":
            return f"NONPAR CORR /VARIABLES={' '.join(cfg['variables'])} /PRINT=SPEARMAN TWOTAIL /MISSING=PAIRWISE."
        return f"CORRELATIONS /VARIABLES={' '.join(cfg['variables'])} /PRINT=TWOTAIL /MISSING=PAIRWISE."
    if a == "regression":
        if cfg.get("model", "linear").lower() == "logistic":
            return f"LOGISTIC REGRESSION VARIABLES={cfg['outcome']} /METHOD=ENTER {' '.join(cfg['predictors'])} /PRINT=CI(95)."
        return (f"REGRESSION /MISSING LISTWISE /STATISTICS COEFF OUTS CI(95) R ANOVA /DEPENDENT {cfg['outcome']} "
                f"/METHOD=ENTER {' '.join(cfg['predictors'])}.")
    if a == "alpha":
        return f"RELIABILITY /VARIABLES={' '.join(cfg['variables'])} /MODEL=ALPHA."
    return ""


# ------------------------------------------------------------------ assembly

def run_report_request(req, plots_dir=None):
    """Run every analysis in `req`; return (title, [section dicts])."""
    if not isinstance(req, dict) or not isinstance(req.get("analyses"), list) or not req["analyses"]:
        raise ValueError("Report request needs a non-empty 'analyses' list")
    base = {k: v for k, v in req.items() if k in ("file", "sheet", "read_csv", "read_spss")}
    df = analyze.load_data(base)
    sections = []
    for i, sub in enumerate(req["analyses"], 1):
        if not isinstance(sub, dict):
            raise ValueError("Each analysis must be a JSON object")
        cfg = {**base, **sub}
        try:
            res = analyze.run_request(cfg, df)
            error = None
        except ValueError as exc:  # keep going: a failed analysis is reported, not hidden
            res, error = None, str(exc)
        sec = {"index": i, "cfg": cfg, "result": res, "error": error, "plots": []}
        if res is not None and plots_dir is not None:
            import spss_plots
            sec["plots"] = [Path(p) for p in spss_plots.make_plots(df, cfg, res, Path(plots_dir) / f"analysis{i}")]
        sections.append(sec)
    return req.get("title") or "Statistical analysis report", sections, df


def build_markdown(title, sections, df, req, image_refs):
    first = sections[0]["result"] or {}
    lines = [f"# {title}", ""]
    lines += ["## Executive result", ""]
    any_ok = False
    for s in sections:
        if s["result"] is not None:
            for sentence in interpret(s["result"])[:1]:
                lines.append(f"- {sentence}")
                any_ok = True
        else:
            lines.append(f"- Analysis {s['index']} ({s['cfg'].get('action')}) did not run: {s['error']}")
    lines += ["", "## Data and decisions", ""]
    lines.append(f"- Source file: `{Path(req['file']).name}` ({len(df)} rows, {len(df.columns)} columns).")
    for s in sections:
        if s["result"] and s["result"].get("data_audit"):
            a = s["result"]["data_audit"]
            used = a.get("rows_used")
            lines.append(f"- Analysis {s['index']} ({s['result']['action']}): rows read {a['rows_total']}, rows used {used if used is not None else 'varies by pair'}."
                         + "".join(f" Excluded: {e.get('reason')} ({e.get('count')})." for e in a.get("exclusions", [])))
    lines.append("- The source data were read, not modified. No recoding, weighting, imputation or outlier removal was applied.")
    lines += ["", "## Results", ""]
    for s in sections:
        lines.append(f"### Analysis {s['index']}: {sf.TITLES.get(s['result']['action'], s['result']['action']) if s['result'] else s['cfg'].get('action')}")
        lines.append("")
        if s["result"] is None:
            lines += [f"**Did not run:** {s['error']}", ""]
            continue
        title_, tables, warns = sf.build_tables(s["result"])
        for w in warns:
            lines.append(f"> {w}")
        if warns:
            lines.append("")
        lines.append(sf.render(tables, "markdown"))
        lines.append("")
        for ref in image_refs.get(s["index"], []):
            lines += [f"![{Path(ref).stem}]({ref})", ""]
    lines += ["## Interpretation", ""]
    for s in sections:
        if s["result"] is not None:
            lines += [f"**Analysis {s['index']}.** " + " ".join(interpret(s["result"])), ""]
    lines += ["## Diagnostics and limitations", ""]
    for s in sections:
        if s["result"] is not None:
            for item in limitations(s["result"]):
                lines.append(f"- Analysis {s['index']}: {item}")
    lines += ["- Significance (p < .05 is used only as a conventional reference) is not the same as importance; read effect sizes and intervals.",
              "- Results describe associations in this sample; causal claims need a design that supports them.",
              "- Diagnostics not computed by this helper (for example Levene, residual normality, collinearity) are not claimed to have passed.",
              "", "## Reproducibility", ""]
    sw = first.get("software", {})
    lines.append("- Software: " + ", ".join(f"{k} {v}" for k, v in sw.items()) + ".")
    lines.append(f"- Generated: {date.today().isoformat()}.")
    lines += ["", "Equivalent SPSS syntax (not executed here; run it in licensed SPSS to compare):", "", "```spss"]
    for s in sections:
        lines.append(spss_syntax(s["cfg"], s["result"] or {}))
    lines += ["```", "", "Request used:", "", "```json", json.dumps(req, indent=2, ensure_ascii=False), "```", ""]
    lines.append("_Produced by an analytical assistant, not IBM SPSS. Differences from SPSS output can arise from version, options and rounding._")
    return "\n".join(lines) + "\n"


def markdown_to_html(md, title, images_b64):
    """Small, dependency-free Markdown subset renderer for our own report output."""
    out, i, lines = [], 0, md.split("\n")
    in_code = False
    code = []

    def inline(t):
        t = html.escape(t)
        import re
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<![\w*])_(.+?)_(?![\w*])", r"<em>\1</em>", t)
        t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
        return t

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            if in_code:
                out.append("<pre>" + html.escape("\n".join(code)) + "</pre>")
                code, in_code = [], False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code.append(ln); i += 1; continue
        if ln.startswith("!["):
            import re
            m = re.match(r"!\[(.*?)\]\((.*?)\)", ln)
            src = images_b64.get(m.group(2), m.group(2)) if m else ""
            out.append(f'<p><img alt="{html.escape(m.group(1))}" src="{src}" style="max-width:520px"></p>')
        elif ln.startswith("|"):
            block = []
            while i < len(lines) and lines[i].startswith("|"):
                block.append(lines[i]); i += 1
            def cells(r):
                import re
                parts = re.split(r"(?<!\\)\|", r.strip())
                return [c.strip().replace("\\|", "|") for c in parts[1:-1]]
            head, sep, body = cells(block[0]), block[1], [cells(r) for r in block[2:]]
            aligns = ["left" if ":---" in c else "right" for c in sep.strip("|").split("|")]
            t = ["<table>", "<thead><tr>" + "".join(f'<th style="text-align:{aligns[j]}">{inline(c)}</th>' for j, c in enumerate(head)) + "</tr></thead><tbody>"]
            for r in body:
                t.append("<tr>" + "".join(f'<td style="text-align:{aligns[j] if j < len(aligns) else "right"}">{inline(c)}</td>' for j, c in enumerate(r)) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue
        elif ln.startswith("### "):
            out.append(f"<h3>{inline(ln[4:])}</h3>")
        elif ln.startswith("## "):
            out.append(f"<h2>{inline(ln[3:])}</h2>")
        elif ln.startswith("# "):
            out.append(f"<h1>{inline(ln[2:])}</h1>")
        elif ln.startswith("> "):
            out.append(f'<blockquote>{inline(ln[2:])}</blockquote>')
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{inline(lines[i][2:])}</li>"); i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        elif ln.strip():
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    css = ("body{font-family:Segoe UI,Arial,sans-serif;max-width:900px;margin:2em auto;padding:0 1em;color:#222}"
           "table{border-collapse:collapse;margin:.6em 0;font-size:.9em}th,td{border:1px solid #bbb;padding:3px 9px}"
           "th{background:#e8edf3}pre{background:#f5f5f5;padding:.8em;overflow-x:auto}blockquote{border-left:4px solid #c33;margin:.5em 0;padding:.2em .8em;background:#fdf0f0}"
           "h2{border-bottom:1px solid #ccc;padding-bottom:.2em}")
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title><style>{css}</style></head><body>\n" + "\n".join(out) + "\n</body></html>\n"


def write_report(req, output, plots=True):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    is_html = output.suffix.lower() in (".html", ".htm")
    plots_dir = (output.parent / (output.stem + "_figures")) if plots else None
    title, sections, df = run_report_request(req, plots_dir)
    image_refs, images_b64 = {}, {}
    for s in sections:
        refs = []
        for p in s["plots"]:
            rel = str(Path(p).relative_to(output.parent))
            refs.append(rel)
            if is_html:
                images_b64[rel] = "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode("ascii")
        image_refs[s["index"]] = refs
    md = build_markdown(title, sections, df, req, image_refs)
    if is_html:
        output.write_text(markdown_to_html(md, title, images_b64), encoding="utf-8")
        if plots_dir and plots_dir.exists():
            import shutil
            shutil.rmtree(plots_dir)  # images are embedded; leave a single file
    else:
        output.write_text(md, encoding="utf-8")
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, help="Path to a report request JSON (see module docstring)")
    ap.add_argument("--output", required=True, help="Report path: .html (self-contained) or .md")
    ap.add_argument("--no-plots", action="store_true", help="Skip charts")
    args = ap.parse_args()
    try:
        req = json.loads(Path(args.config).read_text(encoding="utf-8"))
        want_plots = (not args.no_plots) and req.get("plots", True)
        print(write_report(req, args.output, plots=want_plots))
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
