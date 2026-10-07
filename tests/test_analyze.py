import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze.py"


class AnalyzeCliTests(unittest.TestCase):
    def test_describe_known_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "data.csv"
            source.write_text("x\n1\n2\n3\n4\n", encoding="utf-8")
            config = tmp_path / "request.json"
            config.write_text(json.dumps({
                "file": str(source),
                "action": "describe",
                "variables": ["x"],
            }), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--config", str(config)],
                check=True, capture_output=True, text=True,
            )
            variable = json.loads(result.stdout)["variables"][0]
            self.assertEqual(variable["n"], 4)
            self.assertAlmostEqual(variable["mean"], 2.5)
            self.assertAlmostEqual(variable["sd_sample"], 1.2909944487)

    def test_inventory_reports_missing_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "data.csv"
            source.write_text("x\n1\nNA\n3\n", encoding="utf-8")
            config = tmp_path / "request.json"
            config.write_text(json.dumps({"file": str(source), "action": "inventory"}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--config", str(config)],
                check=True, capture_output=True, text=True,
            )
            inventory = json.loads(result.stdout)
            self.assertEqual(inventory["n_rows"], 3)
            self.assertEqual(inventory["variables"][0]["n_missing"], 1)


if __name__ == "__main__":
    unittest.main()
