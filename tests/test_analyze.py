import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze.py"


def run_cli(cfg, cwd=None):
    """Run analyze.py on a config dict; return (exit_code, parsed_stdout_or_None, stderr)."""
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp) / "request.json"
        config.write_text(json.dumps(cfg), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--config", str(config)],
            capture_output=True, text=True, cwd=cwd,
        )
    parsed = None
    if result.returncode == 0:
        parsed = json.loads(result.stdout)
    return result.returncode, parsed, result.stderr


def run_cli_on_files(files, cfg_body):
    """Write named text files to a temp dir, run a config against them."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for name, text in files.items():
            (tmp_path / name).write_text(text, encoding="utf-8")
        cfg = dict(cfg_body)
        cfg["file"] = str(tmp_path / cfg["file"])
        return run_cli(cfg)


class KnownAnswerTests(unittest.TestCase):
    def test_describe_known_result(self):
        code, out, _ = run_cli_on_files(
            {"data.csv": "x\n1\n2\n3\n4\n"},
            {"file": "data.csv", "action": "describe", "variables": ["x"]})
        self.assertEqual(code, 0)
        variable = out["variables"][0]
        self.assertEqual(variable["n"], 4)
        self.assertAlmostEqual(variable["mean"], 2.5)
        self.assertAlmostEqual(variable["sd_sample"], 1.2909944487)

    def test_inventory_reports_missing_rows(self):
        code, out, _ = run_cli_on_files(
            {"data.csv": "x\n1\nNA\n3\n"},
            {"file": "data.csv", "action": "inventory"})
        self.assertEqual(code, 0)
        self.assertEqual(out["n_rows"], 3)
        self.assertEqual(out["variables"][0]["n_missing"], 1)

    def test_frequencies_known_counts(self):
        code, out, _ = run_cli_on_files(
            {"data.csv": "g\na\nb\na\na\n"},
            {"file": "data.csv", "action": "frequencies", "variables": ["g"]})
        self.assertEqual(code, 0)
        cats = {c["value"]: (c["count"], c["valid_percent"]) for c in out["variables"][0]["categories"]}
        self.assertEqual(cats["a"], (3, 75.0))
        self.assertEqual(cats["b"], (1, 25.0))

    def test_crosstab_known_chi_square(self):
        # 2x2 table [[10,0],[0,10]] -> chi2 = n(ad-bc)^2 / products = 20, V = 1
        rows = ["g,e"] + ["a,0"] * 10 + ["b,1"] * 10
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "crosstab", "row": "g", "column": "e"})
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["pearson_chi_square"], 20.0)
        self.assertEqual(out["df"], 1)
        self.assertAlmostEqual(out["cramers_v"], 1.0)
        self.assertEqual(out["n"], 20)

    def test_welch_ttest_known_result_on_demo(self):
        # Verified against elementary formulas: control 72.5 vs active 81.333,
        # t = -3.6802, Welch df = 8.73294, p = .005343
        code, out, _ = run_cli({"file": "examples/demo.csv", "action": "ttest",
                                "outcome": "score", "group": "group",
                                "groups": ["control", "active"]}, cwd=ROOT)
        self.assertEqual(code, 0)
        groups = {g["group"]: g for g in out["groups"]}
        self.assertAlmostEqual(groups["control"]["mean"], 72.5)
        self.assertAlmostEqual(groups["active"]["mean"], 81.3333333, places=5)
        self.assertAlmostEqual(out["t"], -3.6802, places=3)
        self.assertAlmostEqual(out["df_welch"], 8.73294, places=3)
        self.assertAlmostEqual(out["p_two_sided"], 0.005343, places=5)

    def test_paired_ttest_known_result(self):
        # differences after-before = 1,2,3,4 -> mean 2.5, sd 1.2910, t = 3.873, df = 3
        code, out, _ = run_cli_on_files(
            {"data.csv": "before,after\n1,2\n1,3\n1,4\n1,5\n"},
            {"file": "data.csv", "action": "ttest", "outcome": "after", "paired_with": "before"})
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["mean_difference_second_minus_first"], 2.5)
        self.assertAlmostEqual(out["t"], 3.872983, places=4)
        self.assertEqual(out["df"], 3)
        self.assertTrue(0.02 < out["p_two_sided"] < 0.04)

    def test_anova_known_result(self):
        # A=[1,2,3] B=[4,5,6] C=[7,8,9] -> ss_between=54, ss_within=6, F=27, df=(2,6), eta2=0.9
        rows = ["g,y"] + [f"a,{v}" for v in (1, 2, 3)] + [f"b,{v}" for v in (4, 5, 6)] + [f"c,{v}" for v in (7, 8, 9)]
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "anova", "outcome": "y", "group": "g"})
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["F"], 27.0)
        self.assertEqual(out["df_between"], 2)
        self.assertEqual(out["df_within"], 6)
        self.assertAlmostEqual(out["eta_squared"], 0.9)
        self.assertAlmostEqual(out["p"], 0.001, places=6)

    def test_pearson_perfect_linear(self):
        code, out, _ = run_cli_on_files(
            {"data.csv": "x,y\n1,2\n2,4\n3,6\n4,8\n5,10\n"},
            {"file": "data.csv", "action": "correlation", "variables": ["x", "y"], "method": "pearson"})
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["pairs"][0]["coefficient"], 1.0)
        self.assertLess(out["pairs"][0]["p_two_sided"], 0.001)

    def test_pearson_perfect_negative(self):
        code, out, _ = run_cli_on_files(
            {"data.csv": "x,y\n1,10\n2,8\n3,6\n4,4\n5,2\n"},
            {"file": "data.csv", "action": "correlation", "variables": ["x", "y"], "method": "pearson"})
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["pairs"][0]["coefficient"], -1.0)

    def test_spearman_monotonic_nonlinear(self):
        code, out, _ = run_cli_on_files(
            {"data.csv": "x,y\n1,1\n2,4\n3,9\n4,16\n5,25\n"},
            {"file": "data.csv", "action": "correlation", "variables": ["x", "y"], "method": "spearman"})
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["pairs"][0]["coefficient"], 1.0)

    def test_ols_perfect_line(self):
        # y = 2x + 1 exactly -> slope 2, intercept 1, R^2 = 1
        rows = ["x,y"] + [f"{x},{2*x+1}" for x in range(1, 7)]
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "regression", "outcome": "y", "predictors": ["x"], "model": "linear"})
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["terms"]["x"]["B"], 2.0)
        self.assertAlmostEqual(out["terms"]["const"]["B"], 1.0)
        self.assertAlmostEqual(out["R_squared"], 1.0)
        self.assertEqual(out["n"], 6)

    def test_logistic_converges_with_sane_terms(self):
        xs = list(range(1, 11))
        ys = [0, 0, 0, 0, 1, 0, 1, 1, 1, 1]
        rows = ["x,y"] + [f"{x},{y}" for x, y in zip(xs, ys)]
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "regression", "outcome": "y", "predictors": ["x"], "model": "logistic"})
        self.assertEqual(code, 0)
        self.assertEqual(out["n"], 10)
        self.assertGreater(out["terms"]["x"]["B_log_odds"], 0)
        self.assertGreater(out["terms"]["x"]["OR"], 1)
        self.assertTrue(0 <= out["pseudo_R_squared_McFadden"] <= 1)

    def test_alpha_identical_items(self):
        rows = ["i1,i2,i3"] + [f"{v},{v},{v}" for v in (1, 2, 3, 4, 5)]
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "alpha", "variables": ["i1", "i2", "i3"]})
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["alpha"], 1.0)
        self.assertEqual(out["complete_case_n"], 5)


class AuditAndEdgeTests(unittest.TestCase):
    def test_anova_drops_small_group_with_warning(self):
        # C has one usable row: must be dropped AND reported, not silent
        rows = (["g,y"] + [f"a,{v}" for v in (1, 2)] + [f"b,{v}" for v in (4, 5)] + ["c,9"])
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "anova", "outcome": "y", "group": "g"})
        self.assertEqual(code, 0)
        self.assertEqual(len(out["groups"]), 2)
        dropped = [e for e in out["data_audit"]["exclusions"] if e.get("group") == "c"]
        self.assertEqual(len(dropped), 1)
        self.assertEqual(dropped[0]["usable_n"], 1)
        self.assertEqual(out["n"], 4)
        self.assertEqual(out["source_rows"], 5)

    def test_anova_fails_loudly_when_too_few_groups_remain(self):
        rows = ["g,y", "a,1", "b,4"]
        code, _, err = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "anova", "outcome": "y", "group": "g"})
        self.assertEqual(code, 2)
        self.assertIn("Dropped groups", err)

    def test_bad_numeric_string_is_reported_not_silent(self):
        rows = ["g,y", "a,1", "a,2", "a,3", "b,4", "b,5", "b,oops"]
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "ttest", "outcome": "y", "group": "g", "groups": ["a", "b"]})
        self.assertEqual(code, 0)
        coerced = [e for e in out["data_audit"]["exclusions"]
                   if e["reason"] == "non-numeric value coerced to missing"]
        self.assertEqual(len(coerced), 1)
        self.assertEqual(coerced[0]["count"], 1)
        self.assertIn("oops", coerced[0]["sample_values"])
        groups = {g["group"]: g["n"] for g in out["groups"]}
        self.assertEqual(groups["b"], 2)

    def test_duplicate_groups_rejected(self):
        rows = ["g,y", "a,1", "a,2", "a,3", "a,4"]
        code, _, err = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "ttest", "outcome": "y", "group": "g", "groups": ["a", "a"]})
        self.assertEqual(code, 2)
        self.assertIn("distinct", err)

    def test_ttest_auto_detects_groups_in_observed_order(self):
        rows = ["g,y", "b,1", "b,2", "a,5", "a,6"]
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "ttest", "outcome": "y", "group": "g"})
        self.assertEqual(code, 0)
        self.assertEqual([g["group"] for g in out["groups"]], ["b", "a"])

    def test_correlation_is_pairwise_and_says_so(self):
        # y has one extra missing row vs z: per-pair N must differ and policy must be explicit
        rows = ["x,y,z", "1,1,1", "2,2,2", "3,3,", "4,4,4", "5,,5"]
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "correlation", "variables": ["x", "y", "z"], "method": "pearson"})
        self.assertEqual(code, 0)
        self.assertEqual(out["missing_policy"], "pairwise-complete per variable pair")
        ns = {(p["var1"], p["var2"]): p["n"] for p in out["pairs"]}
        self.assertEqual(ns[("x", "y")], 4)
        self.assertEqual(ns[("x", "z")], 4)
        self.assertEqual(ns[("y", "z")], 3)

    def test_regression_reports_dropped_incomplete_rows(self):
        rows = ["x,y", "1,3", "2,5", "3,oops", "4,9", "5,11", "6,"]
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "regression", "outcome": "y", "predictors": ["x"], "model": "linear"})
        self.assertEqual(code, 0)
        self.assertEqual(out["n"], 4)
        reasons = {e["reason"]: e["count"] for e in out["data_audit"]["exclusions"]}
        self.assertEqual(reasons.get("non-numeric value coerced to missing"), 1)
        self.assertEqual(reasons.get("missing value"), 1)
        self.assertEqual(reasons.get("row dropped: incomplete across outcome/predictors"), 2)

    def test_alpha_reports_dropped_rows(self):
        rows = ["i1,i2,i3", "1,1,1", "2,2,", "3,3,3", "4,4,4"]
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "alpha", "variables": ["i1", "i2", "i3"]})
        self.assertEqual(code, 0)
        self.assertEqual(out["complete_case_n"], 3)
        reasons = {e["reason"]: e["count"] for e in out["data_audit"]["exclusions"]}
        self.assertEqual(reasons.get("row dropped: incomplete across items"), 1)

    def test_crosstab_reports_incomplete_pairs(self):
        rows = ["g,e", "a,1", "a,0", "b,1", "b,", "b,0"]
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "crosstab", "row": "g", "column": "e"})
        self.assertEqual(code, 0)
        self.assertEqual(out["missing_pairs"], 1)
        self.assertEqual(out["n"], 4)

    def test_paired_ttest_reports_dropped_rows(self):
        rows = ["before,after", "1,2", "2,", "3,5", "4,6"]
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "ttest", "outcome": "after", "paired_with": "before"})
        self.assertEqual(code, 0)
        self.assertEqual(out["n_pairs"], 3)
        reasons = {e["reason"]: e["count"] for e in out["data_audit"]["exclusions"]}
        self.assertEqual(reasons.get("missing value"), 1)
        self.assertEqual(reasons.get("row dropped: incomplete pair"), 1)

    def test_describe_flags_mixed_numeric_column(self):
        rows = ["x", "1", "2", "oops"]
        code, out, _ = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "describe", "variables": ["x"]})
        self.assertEqual(code, 0)
        variable = out["variables"][0]
        self.assertEqual(variable["type"], "categorical_or_mixed")
        self.assertEqual(variable["n_numeric_parseable"], 2)
        self.assertIn("data-entry errors", variable["note"])

    def test_labelled_sav_keeps_codes_and_logistic_runs(self):
        try:
            import pyreadstat
        except ImportError:
            self.skipTest("pyreadstat not installed")
        import pandas as pd
        xs = list(range(1, 11))
        ys = [0, 0, 0, 0, 1, 0, 1, 1, 1, 1]
        with tempfile.TemporaryDirectory() as tmp:
            sav = Path(tmp) / "labelled.sav"
            source = pd.DataFrame({"event": ys, "x": xs})
            pyreadstat.write_sav(source, sav, variable_value_labels={"event": {0: "No", 1: "Yes"}})
            code, out, err = run_cli({"file": str(sav), "action": "regression",
                                      "outcome": "event", "predictors": ["x"], "model": "logistic"})
            self.assertEqual(code, 0, msg=err)
            self.assertEqual(out["n"], 10)
            code2, inv, _ = run_cli({"file": str(sav), "action": "inventory"})
            self.assertEqual(code2, 0)
            event_var = [v for v in inv["variables"] if v["variable"] == "event"][0]
            self.assertNotIn("No", event_var["sample_values"])
            self.assertNotIn("Yes", event_var["sample_values"])

    def test_logistic_rejects_non_binary_outcome(self):
        rows = ["x,y", "1,0", "2,1", "3,2", "4,0", "5,1", "6,2"]
        code, _, err = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "regression", "outcome": "y", "predictors": ["x"], "model": "logistic"})
        self.assertEqual(code, 2)
        self.assertIn("0/1", err)

    def test_group_with_one_observation_rejected(self):
        rows = ["g,y", "a,1", "a,2", "b,9"]
        code, _, err = run_cli_on_files(
            {"data.csv": "\n".join(rows) + "\n"},
            {"file": "data.csv", "action": "ttest", "outcome": "y", "group": "g", "groups": ["a", "b"]})
        self.assertEqual(code, 2)
        self.assertIn("at least two observations", err)

    def test_unknown_action_rejected(self):
        code, _, err = run_cli_on_files(
            {"data.csv": "x\n1\n"},
            {"file": "data.csv", "action": "teleport"})
        self.assertEqual(code, 2)
        self.assertIn("Unknown action", err)

    def test_missing_column_lists_available(self):
        code, _, err = run_cli_on_files(
            {"data.csv": "x\n1\n"},
            {"file": "data.csv", "action": "describe", "variables": ["nope"]})
        self.assertEqual(code, 2)
        self.assertIn("Available columns", err)

    def test_missing_file_rejected(self):
        code, _, err = run_cli({"file": "does-not-exist.csv", "action": "inventory"})
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_alpha_needs_two_items(self):
        code, _, err = run_cli_on_files(
            {"data.csv": "i1\n1\n2\n3\n"},
            {"file": "data.csv", "action": "alpha", "variables": ["i1"]})
        self.assertEqual(code, 2)
        self.assertIn("at least two items", err)


class DocumentedExamplesTests(unittest.TestCase):
    """Every request file shipped in examples/ must run cleanly from the repo root."""

    def test_all_example_requests_run(self):
        requests = sorted((ROOT / "examples").glob("*-request.json"))
        self.assertGreaterEqual(len(requests), 10)
        for request in requests:
            with self.subTest(request=request.name):
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--config", str(request)],
                    capture_output=True, text=True, cwd=ROOT,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                json.loads(result.stdout)


if __name__ == "__main__":
    unittest.main()
