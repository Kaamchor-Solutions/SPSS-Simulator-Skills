"""Tests for the formatted-output layer: spss_format, spss_plots, spss_report."""
import base64
import json
import math
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import analyze  # noqa: E402
import spss_format as sf  # noqa: E402
import spss_plots  # noqa: E402
import spss_report  # noqa: E402

try:
    import matplotlib  # noqa: F401
    HAVE_MPL = True
except ImportError:  # pragma: no cover
    HAVE_MPL = False

EXAMPLES = sorted((ROOT / "examples").glob("*-request.json"))
REQUESTS = [p for p in EXAMPLES if p.name != "report-request.json"]


def run_example(name):
    cfg = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
    cfg["file"] = str(ROOT / cfg["file"])
    return cfg, analyze.run_request(cfg)


def run_cli(args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "analyze.py")] + args, capture_output=True, text=True, cwd=ROOT)


class NumberFormatTests(unittest.TestCase):
    def test_sig_convention(self):
        self.assertEqual(sf.fsig(0.00004), ".000")
        self.assertEqual(sf.fsig(0.0005), ".001")
        self.assertEqual(sf.fsig(0.0353), ".035")
        self.assertEqual(sf.fsig(1.0), "1.000")
        self.assertEqual(sf.fsig(None), "")

    def test_correlation_drops_leading_zero(self):
        self.assertEqual(sf.fcorr(0.6097), ".610")
        self.assertEqual(sf.fcorr(-0.254), "-.254")
        self.assertEqual(sf.fcorr(1.0), "1.000")

    def test_missing_and_nonfinite_are_blank(self):
        self.assertEqual(sf.fnum(None), "")
        self.assertEqual(sf.fnum(float("nan")), "")
        self.assertEqual(sf.fnum(2.0, 1), "2.0")

    def test_apa_p(self):
        self.assertEqual(spss_report.apa_p(0.0002), "p < .001")
        self.assertEqual(spss_report.apa_p(0.0423), "p = .042")


class FormattedTablesKnownAnswer(unittest.TestCase):
    def test_every_example_formats_in_both_styles(self):
        for path in REQUESTS:
            with self.subTest(example=path.name):
                _, res = run_example(path.name)
                for style in ("text", "markdown"):
                    out = sf.format_result(res, style=style)
                    self.assertGreater(len(out), 80)
                    self.assertNotIn("nan", out.lower().replace("cohen", ""))
                    self.assertNotIn("None", out)

    def test_markdown_tables_are_rectangular(self):
        for path in REQUESTS:
            _, res = run_example(path.name)
            _, tables, _ = sf.build_tables(res)
            for t in tables:
                with self.subTest(example=path.name, table=t.title):
                    for row in t.rows:
                        self.assertEqual(len(row), len(t.columns))
                    md = t.to_markdown().splitlines()
                    pipes = [ln.count("|") for ln in md if ln.startswith("|")]
                    self.assertEqual(len(set(pipes)), 1)

    def test_welch_table_matches_hand_calculation(self):
        _, res = run_example("ttest-request.json")
        out = sf.format_result(res)
        # SE of difference = sqrt(sd1^2/6 + sd2^2/6); t = diff / SE
        se = math.sqrt(3.271085446759225 ** 2 / 6 + 4.88535225614967 ** 2 / 6)
        self.assertIn(f"{se:.3f}", out)
        for token in ("-3.680", "8.733", ".005", "-8.833", "-14.288", "-3.378", "Independent Samples Test", "Group Statistics"):
            self.assertIn(token, out)

    def test_anova_sums_of_squares_are_exact(self):
        _, res = run_example("anova-request.json")
        ss = res["sum_of_squares"]
        self.assertAlmostEqual(ss["between"], 234.0833333, places=5)
        self.assertAlmostEqual(ss["within"], 172.8333333, places=5)
        self.assertAlmostEqual(ss["between"] + ss["within"], ss["total"], places=9)
        self.assertAlmostEqual(ss["between"] / ss["total"], res["eta_squared"], places=9)
        # F recovered from the table must equal scipy's F
        f = (ss["between"] / res["df_between"]) / (ss["within"] / res["df_within"])
        self.assertAlmostEqual(f, res["F"], places=8)
        out = sf.format_result(res)
        for token in ("234.083", "172.833", "406.917", "17.283", "13.544", ".004", "Between Groups", "Within Groups"):
            self.assertIn(token, out)

    def test_regression_summary_is_internally_consistent(self):
        _, res = run_example("regression-linear-request.json")
        ms = res["model_summary"]
        ss = ms["sum_of_squares"]
        self.assertAlmostEqual(ss["regression"] + ss["residual"], ss["total"], places=8)
        self.assertAlmostEqual(ss["regression"] / ss["total"], res["R_squared"], places=9)
        self.assertAlmostEqual(ms["R"] ** 2, res["R_squared"], places=9)
        self.assertAlmostEqual(ms["std_error_of_estimate"], math.sqrt(ss["residual"] / res["F_df"][1]), places=9)
        # with one predictor, standardized beta equals Pearson r
        _, corr = run_example("correlation-request.json")
        self.assertAlmostEqual(res["terms"]["age"]["beta_standardized"], corr["pairs"][0]["coefficient"], places=9)
        out = sf.format_result(res)
        for token in ("Model Summary", "Std. Error of the Estimate", "5.056", "(Constant)", "Beta", ".610", "151.269", "255.648"):
            self.assertIn(token, out)

    def test_logistic_extras_are_consistent(self):
        _, res = run_example("regression-logistic-request.json")
        cl, mf = res["classification"], res["model_fit"]
        total = sum(cl[k] for k in cl if k.startswith("observed"))
        self.assertEqual(total, res["n"])
        correct = cl["observed_0_predicted_0"] + cl["observed_1_predicted_1"]
        self.assertAlmostEqual(cl["overall_percent_correct"], correct / total * 100, places=9)
        self.assertAlmostEqual(mf["neg2_log_likelihood_null"] - mf["neg2_log_likelihood"], mf["chi_square"], places=8)
        self.assertGreaterEqual(mf["nagelkerke_R2"], mf["cox_snell_R2"])
        self.assertLessEqual(mf["nagelkerke_R2"], 1.0)
        out = sf.format_result(res)
        wald = (res["terms"]["age"]["B_log_odds"] / res["terms"]["age"]["SE"]) ** 2
        self.assertIn(f"{wald:.3f}", out)
        for token in ("Variables in the Equation", "Exp(B)", "Classification Table", "Nagelkerke", "Constant"):
            self.assertIn(token, out)

    def test_crosstab_percentages_and_chisquare_rows(self):
        _, res = run_example("crosstab-request.json")
        out = sf.format_result(res)
        for token in ("group * event Crosstabulation", "33.3", "66.7", "83.3", "16.7", "3.086", ".079", "0.507", "Case Processing Summary"):
            self.assertIn(token, out)
        self.assertIn("4 cells have expected count less than 5", out)

    def test_correlation_matrix_layout(self):
        _, res = run_example("correlation-request.json")
        out = sf.format_result(res)
        self.assertIn("Pearson Correlation", out)
        self.assertIn("Sig. (2-tailed)", out)
        self.assertIn(".610", out)
        self.assertIn(".035", out)

    def test_paired_sd_of_differences_is_recovered(self):
        _, res = run_example("ttest-paired-request.json")
        out = sf.format_result(res)
        # SD of differences = |d| * sqrt(n) / |t|
        sd = abs(res["mean_difference_second_minus_first"]) * math.sqrt(res["n_pairs"]) / abs(res["t"])
        self.assertIn(f"{sd:.3f}", out)
        self.assertIn("after - before", out)

    def test_alpha_report(self):
        _, res = run_example("alpha-request.json")
        out = sf.format_result(res)
        self.assertIn("Reliability Statistics", out)
        self.assertIn("0.932", out)

    def test_frequencies_sorted_with_missing_and_cumulative(self):
        import pandas as pd
        df = pd.DataFrame({"x": [3, 1, 1, 2, 2, 2, None, None]})
        res = analyze.frequencies(df, ["x"])
        res["valid"] = True
        _, tables, _ = sf.build_tables({**res, "action": "frequencies"})
        freq = [t for t in tables if t.title.startswith("Frequencies")][0]
        labels = [r[0] for r in freq.rows]
        self.assertEqual(labels[:3], ["1", "2", "3"])
        self.assertIn("Missing", labels)
        self.assertEqual(freq.rows[2][4], "100.0")  # cumulative valid percent ends at 100
        self.assertEqual(freq.rows[0][2], "25.0")   # Percent uses all 8 cases (2/8)
        self.assertEqual(freq.rows[0][3], "33.3")   # Valid percent uses 6 valid cases (2/6)

    def test_invalid_result_prints_reason_not_inference(self):
        import pandas as pd
        df = pd.DataFrame({"y": [5.0, 5.0, 5.0, 5.0], "g": ["a", "a", "b", "b"]})
        res = analyze.run_request({"file": str(ROOT / "examples" / "demo.csv"), "action": "ttest", "outcome": "y", "group": "g"}, df)
        self.assertFalse(res["valid"])
        out = sf.format_result(res)
        self.assertIn("RESULT INVALID", out)
        self.assertNotIn("Independent Samples Test", out)
        md = sf.format_result(res, style="markdown")
        self.assertIn("RESULT INVALID", md)

    def test_unknown_action_and_style_raise(self):
        with self.assertRaises(ValueError):
            sf.format_result({"action": "mystery", "valid": True})
        _, res = run_example("describe-request.json")
        with self.assertRaises(ValueError):
            sf.format_result(res, style="pdf")


class SampleOutputTests(unittest.TestCase):
    def test_gallery_is_current(self):
        """docs/sample-output.txt must be what the shipped examples really produce."""
        gallery = (ROOT / "docs" / "sample-output.txt").read_text(encoding="utf-8")
        for name in ("describe-request.json", "frequencies-request.json", "crosstab-request.json", "ttest-request.json", "anova-request.json",
                     "correlation-request.json", "regression-linear-request.json", "regression-logistic-request.json"):
            with self.subTest(example=name):
                _, res = run_example(name)
                self.assertIn(sf.format_result(res), gallery)


class JsonContractTests(unittest.TestCase):
    def test_default_cli_output_is_still_pure_json_with_original_keys(self):
        proc = run_cli(["--config", str(ROOT / "examples" / "ttest-request.json")])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        for key in ("action", "groups", "t", "df_welch", "p_two_sided", "difference_ci95", "data_audit", "valid", "software"):
            self.assertIn(key, out)
        self.assertNotIn("plots", out)

    def test_run_request_matches_cli_json(self):
        for path in REQUESTS:
            with self.subTest(example=path.name):
                proc = run_cli(["--config", str(path)])
                self.assertEqual(proc.returncode, 0, proc.stderr)
                _, res = run_example(path.name)
                self.assertEqual(json.loads(proc.stdout), json.loads(json.dumps(res)))

    def test_cli_text_and_markdown_formats(self):
        proc = run_cli(["--config", str(ROOT / "examples" / "anova-request.json"), "--format", "text"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ANOVA: score", proc.stdout)
        self.assertTrue(proc.stdout.lstrip().startswith("Oneway"))
        proc = run_cli(["--config", str(ROOT / "examples" / "anova-request.json"), "--format", "markdown"])
        self.assertIn("| Between Groups |", proc.stdout)

    def test_cli_bad_format_rejected(self):
        proc = run_cli(["--config", str(ROOT / "examples" / "anova-request.json"), "--format", "pdf"])
        self.assertNotEqual(proc.returncode, 0)


class PlotDataTests(unittest.TestCase):
    def test_histogram_counts_and_moments(self):
        h = spss_plots.histogram_data([1, 2, 2, 3, 3, 3, 4, 4, 5, 9], bins=4)
        self.assertEqual(sum(h["counts"]), 10)
        self.assertEqual(h["counts"], [3, 5, 1, 1])  # edges 1,3,5,7,9; last bin includes 9
        self.assertAlmostEqual(h["mean"], 3.6)
        self.assertEqual(len(h["edges"]), 5)
        self.assertEqual(h["edges"][0], 1.0)
        self.assertEqual(h["edges"][-1], 9.0)

    def test_histogram_ignores_nonnumeric_and_rejects_empty(self):
        h = spss_plots.histogram_data(["1", "2", "x", None, 3], bins=2)
        self.assertEqual(h["n"], 3)
        with self.assertRaises(ValueError):
            spss_plots.histogram_data(["a", "b"])

    def test_boxplot_stats_flags_outlier(self):
        b = spss_plots.boxplot_stats([1, 2, 3, 4, 100])
        self.assertEqual((b["q1"], b["median"], b["q3"]), (2.0, 3.0, 4.0))
        self.assertEqual(b["outliers"], [100.0])
        self.assertEqual(b["whisker_low"], 1.0)
        self.assertEqual(b["whisker_high"], 4.0)

    def test_fit_line_known_answer(self):
        f = spss_plots.fit_line([1, 2, 3, 4], [3, 5, 7, 9])
        self.assertAlmostEqual(f["slope"], 2.0)
        self.assertAlmostEqual(f["intercept"], 1.0)
        self.assertAlmostEqual(f["r_squared"], 1.0)
        with self.assertRaises(ValueError):
            spss_plots.fit_line([1, 1, 1], [1, 2, 3])

    def test_fit_line_matches_regression_helper(self):
        import pandas as pd
        df = pd.read_csv(ROOT / "examples" / "demo.csv")
        f = spss_plots.fit_line(df["age"], df["score"])
        _, res = run_example("regression-linear-request.json")
        self.assertAlmostEqual(f["slope"], res["terms"]["age"]["B"], places=9)
        self.assertAlmostEqual(f["intercept"], res["terms"]["const"]["B"], places=9)
        self.assertAlmostEqual(f["r_squared"], res["R_squared"], places=9)

    def test_bar_counts_order(self):
        self.assertEqual(spss_plots.bar_counts([2, 1, 2, None, 10]), [("1", 1), ("2", 2), ("10", 1)])
        self.assertEqual(spss_plots.bar_counts(["b", "a", "b"]), [("a", 1), ("b", 2)])

    def test_group_mean_ci_known_answer(self):
        import pandas as pd
        df = pd.DataFrame({"y": [1, 2, 3, 10, 12, 14], "g": ["a"] * 3 + ["b"] * 3})
        out = spss_plots.group_means_ci(df, "y", "g")
        a = out[0]
        self.assertEqual(a["mean"], 2.0)
        # se = 1/sqrt(3); t(.975, 2) = 4.302653
        self.assertAlmostEqual(a["half_width"], 4.302653 / math.sqrt(3), places=4)

    def test_residual_data_sums_to_zero(self):
        import pandas as pd
        df = pd.read_csv(ROOT / "examples" / "demo.csv")
        r = spss_plots.residual_data(df, "score", ["age"])
        self.assertEqual(r["n"], 12)
        # raw residuals have zero mean, so fitted mean equals outcome mean
        self.assertAlmostEqual(sum(r["fitted"]) / 12, df["score"].mean(), places=9)
        self.assertAlmostEqual(sum(r["std_resid"]), 0.0, places=8)


@unittest.skipUnless(HAVE_MPL, "matplotlib not installed")
class PlotFileTests(unittest.TestCase):
    PNG = b"\x89PNG\r\n\x1a\n"

    def test_charts_are_valid_pngs_for_each_supported_action(self):
        expect = {"describe-request.json": 2, "frequencies-request.json": 1, "crosstab-request.json": 1, "ttest-request.json": 2,
                  "ttest-paired-request.json": 2, "anova-request.json": 2, "correlation-request.json": 1, "regression-linear-request.json": 2}
        for name, count in expect.items():
            with self.subTest(example=name), tempfile.TemporaryDirectory() as tmp:
                cfg, res = run_example(name)
                df = analyze.load_data(cfg)
                paths = spss_plots.make_plots(df, cfg, res, tmp)
                self.assertEqual(len(paths), count)
                for p in paths:
                    data = Path(p).read_bytes()
                    self.assertTrue(data.startswith(self.PNG))
                    self.assertGreater(len(data), 3000)

    def test_no_charts_for_invalid_or_chartless_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg, res = run_example("alpha-request.json")
            self.assertEqual(spss_plots.make_plots(analyze.load_data(cfg), cfg, res, tmp), [])
            self.assertEqual(spss_plots.make_plots(None, {}, {"valid": False, "action": "ttest_independent_welch"}, tmp), [])

    def test_cli_plots_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = run_cli(["--config", str(ROOT / "examples" / "ttest-request.json"), "--plots-dir", tmp])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            self.assertEqual(len(out["plots"]), 2)
            for p in out["plots"]:
                self.assertTrue(Path(p).is_file())


class InterpretationTests(unittest.TestCase):
    def test_ttest_sentence_known_answer(self):
        _, res = run_example("ttest-request.json")
        s = spss_report.interpret(res)[0]
        self.assertIn("t(8.73) = -3.68, p = .005", s)
        self.assertIn("statistically significant", s)
        self.assertIn("mean difference = -8.83", s)
        self.assertIn("95% CI [-14.29, -3.38]", s)

    def test_nonsignificant_is_worded_as_such(self):
        _, res = run_example("crosstab-request.json")
        s = spss_report.interpret(res)[0]
        self.assertIn("not statistically significant", s)
        self.assertIn("p = .079", s)

    def test_regression_never_claims_causation(self):
        _, res = run_example("regression-linear-request.json")
        text = " ".join(spss_report.interpret(res))
        self.assertIn("not causal", text)
        self.assertNotIn("caused", text)
        self.assertIn("R squared = .37", text)

    def test_every_example_gets_an_interpretation(self):
        for path in REQUESTS:
            if path.name == "inventory-request.json":
                continue
            with self.subTest(example=path.name):
                _, res = run_example(path.name)
                self.assertTrue(spss_report.interpret(res))

    def test_invalid_result_interpretation(self):
        s = spss_report.interpret({"valid": False, "reason": "zero variance", "action": "anova"})[0]
        self.assertIn("could not be interpreted", s)


class SyntaxTests(unittest.TestCase):
    def test_syntax_for_each_example_names_the_variables(self):
        wanted = {"describe-request.json": "DESCRIPTIVES VARIABLES=score age", "frequencies-request.json": "FREQUENCIES VARIABLES=group",
                  "crosstab-request.json": "CROSSTABS /TABLES=group BY event", "ttest-request.json": "T-TEST GROUPS=group(control active) /VARIABLES=score",
                  "ttest-paired-request.json": "T-TEST PAIRS=before WITH after (PAIRED)", "anova-request.json": "ONEWAY score BY group",
                  "correlation-request.json": "CORRELATIONS /VARIABLES=age score", "regression-linear-request.json": "/DEPENDENT score",
                  "regression-logistic-request.json": "LOGISTIC REGRESSION VARIABLES=event", "alpha-request.json": "RELIABILITY /VARIABLES=item1 item2 item3"}
        for name, fragment in wanted.items():
            with self.subTest(example=name):
                cfg, res = run_example(name)
                self.assertIn(fragment, spss_report.spss_syntax(cfg, res))


class ReportTests(unittest.TestCase):
    def request(self, **extra):
        req = json.loads((ROOT / "examples" / "report-request.json").read_text(encoding="utf-8"))
        req["file"] = str(ROOT / req["file"])
        req.update(extra)
        return req

    def test_markdown_report_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = spss_report.write_report(self.request(), Path(tmp) / "r.md", plots=False)
            text = out.read_text(encoding="utf-8")
            for heading in ("# Demo study", "## Executive result", "## Data and decisions", "## Results", "## Interpretation",
                            "## Diagnostics and limitations", "## Reproducibility"):
                self.assertIn(heading, text)
            self.assertIn("```spss", text)
            self.assertIn("T-TEST GROUPS=group(control active)", text)
            self.assertIn("not IBM SPSS", text)
            self.assertIn("Independent Samples Test", text)
            self.assertNotIn("![", text)  # plots=False
            self.assertNotIn(str(ROOT), text.split("Request used:")[0])  # no absolute paths in the prose/results

    @unittest.skipUnless(HAVE_MPL, "matplotlib not installed")
    def test_html_report_is_self_contained(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = spss_report.write_report(self.request(), Path(tmp) / "r.html", plots=True)
            text = out.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("<!doctype html>"))
            self.assertGreaterEqual(text.count("data:image/png;base64,"), 8)
            self.assertNotIn('src="report_figures', text)
            self.assertFalse((Path(tmp) / "r_figures").exists())
            # embedded images decode to real PNGs
            m = re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", text)
            self.assertTrue(base64.b64decode(m.group(1)).startswith(b"\x89PNG"))
            # every table row has as many cells as its header
            for table in re.findall(r"<table>.*?</table>", text, re.S):
                width = len(re.findall(r"<th ", table))
                for row in re.findall(r"<tr>(.*?)</tr>", table, re.S)[1:]:
                    self.assertEqual(len(re.findall(r"<td", row)), width)

    @unittest.skipUnless(HAVE_MPL, "matplotlib not installed")
    def test_markdown_report_links_figures(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = spss_report.write_report(self.request(), Path(tmp) / "r.md", plots=True)
            text = out.read_text(encoding="utf-8")
            links = re.findall(r"!\[.*?\]\((.*?)\)", text)
            self.assertGreaterEqual(len(links), 8)
            for link in links:
                self.assertTrue((Path(tmp) / link).is_file(), link)

    def test_failed_analysis_is_reported_not_hidden(self):
        req = self.request(analyses=[{"action": "describe", "variables": ["score"]},
                                     {"action": "ttest", "outcome": "score", "group": "nope"}])
        with tempfile.TemporaryDirectory() as tmp:
            text = spss_report.write_report(req, Path(tmp) / "r.md", plots=False).read_text(encoding="utf-8")
            self.assertIn("did not run", text)
            self.assertIn("Columns not found", text)
            self.assertIn("Analysis 1: Descriptives", text)

    def test_html_escapes_untrusted_text(self):
        req = self.request(title="<script>alert(1)</script> study", analyses=[{"action": "describe", "variables": ["score"]}])
        with tempfile.TemporaryDirectory() as tmp:
            text = spss_report.write_report(req, Path(tmp) / "r.html", plots=False).read_text(encoding="utf-8")
            self.assertNotIn("<script>alert", text)
            self.assertIn("&lt;script&gt;", text)

    def test_report_request_validation(self):
        for bad in ({"file": str(ROOT / "examples" / "demo.csv")}, {"file": str(ROOT / "examples" / "demo.csv"), "analyses": []},
                    {"file": str(ROOT / "examples" / "demo.csv"), "analyses": ["describe"]}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    spss_report.run_report_request(bad)

    def test_report_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            req = self.request()
            cfgp = Path(tmp) / "req.json"
            cfgp.write_text(json.dumps(req), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "spss_report.py"), "--config", str(cfgp),
                                   "--output", str(Path(tmp) / "out" / "rep.md"), "--no-plots"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((Path(tmp) / "out" / "rep.md").is_file())
            bad = subprocess.run([sys.executable, str(ROOT / "scripts" / "spss_report.py"), "--config", str(Path(tmp) / "missing.json"),
                                  "--output", str(Path(tmp) / "x.md")], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 2)
            self.assertIn("ERROR", bad.stderr)


if __name__ == "__main__":
    unittest.main()
