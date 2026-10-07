"""M5 修复回归：silent_failures / summary_purity 指标断言达标。

走 M7 gap_check 真实代码路径（novel.py write_chapter / review_chapter），
指标不达标即失败。

运行：py -m unittest tests.test_m5_fix 或 py -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.gap_checks import silent_failures, summary_fidelity  # noqa: E402


class M5FixTests(unittest.TestCase):
    def test_silent_swallow_rate(self):
        r = silent_failures.run()[0]
        self.assertEqual(r["value"], 0.0, f"silent_swallow_rate = {r['value']}")

    def test_summary_purity(self):
        for r in summary_fidelity.run():
            if r["gap"] == "summary_purity":
                self.assertEqual(r["value"], 1.0, f"summary_purity = {r['value']}")
                return
        self.fail("summary_purity 指标缺失")


if __name__ == "__main__":
    unittest.main()
