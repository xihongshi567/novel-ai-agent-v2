"""M1 修复回归：name_matching / foreshadow_recovery 指标断言达标。

走 M7 gap_check 真实代码路径（tracker.py 的 apply_to_bible /
apply_to_continuity），指标不达标即失败。修复落地后此测试是验收证明。

运行：py -m unittest tests.test_m1_fix 或 py -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.gap_checks import foreshadow_recovery, name_matching  # noqa: E402


class M1FixTests(unittest.TestCase):
    def test_name_resolution_rate(self):
        r = name_matching.run()[0]
        self.assertEqual(r["value"], 1.0, f"name_resolution_rate = {r['value']}")

    def test_foreshadow_metrics(self):
        by_metric = {r["metric"]: r["value"] for r in foreshadow_recovery.run()}
        for metric, expected in (
            ("resolution_accuracy", 1.0),
            ("resolution_precision", 1.0),
            ("resolution_recall", 1.0),
        ):
            self.assertEqual(by_metric[metric], expected,
                             f"{metric} = {by_metric[metric]}")


if __name__ == "__main__":
    unittest.main()
