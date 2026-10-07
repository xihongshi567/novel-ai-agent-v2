"""M7 回归基线完整性测试：runner 能跑、9 缺口在册、schema 合法。

不断言各缺口 value 达标（当前缺陷未修复，指标会 fail）；修复落地后由
对应模块的修复测试断言指标达标。
运行：py tests/test_m7_regression.py 或 py -m unittest discover tests
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EXPECTED_GAPS = {
    "name_matching", "foreshadow_recovery", "summary_fidelity", "summary_purity",
    "rag_truncation", "setting_filter", "review_selfcheck", "silent_failures",
    "chunk_boundary", "chapter_fit", "continuity", "retrieval",
}


class M7RegressionTests(unittest.TestCase):
    def test_runner_outputs_valid_schema(self):
        from evaluation.run_evaluation import main

        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "results.json"
            rc = main(out_path=out)
            self.assertEqual(rc, 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)
            gaps = payload["gaps"]
            self.assertIsInstance(gaps, list)
            present = {g["gap"] for g in gaps}
            for expected in EXPECTED_GAPS:
                self.assertIn(expected, present, f"缺少套件/指标: {expected}")
            for g in gaps:
                self.assertIsInstance(g["cases"], int)
                self.assertGreaterEqual(g["cases"], 1)
                self.assertIn(g["status"], ("pass", "fail", "na"))
                if g["status"] != "na":
                    self.assertIsInstance(g["value"], (int, float))
                    self.assertIsInstance(g["target"], (int, float))
                    self.assertTrue(0.0 <= g["value"] <= max(g["cases"], 1.0),
                                    f"{g['gap']}.{g['metric']} value 越界: {g['value']}")


if __name__ == "__main__":
    unittest.main()
