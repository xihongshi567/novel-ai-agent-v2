"""M3 修复回归：review_selfcheck / summary_fidelity 指标断言达标。

走 M7 gap_check 真实代码路径（reviewer.review / novel.py write_chapter 兜底），
指标不达标即失败。

运行：py -m unittest tests.test_m3_fix 或 py -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.gap_checks import review_selfcheck, summary_fidelity  # noqa: E402


class M3FixTests(unittest.TestCase):
    def test_review_invalid_surface(self):
        r = review_selfcheck.run()[0]
        self.assertEqual(r["value"], 1.0, f"review_invalid_surface = {r['value']}")

    def test_summary_fidelity_metrics(self):
        by_key = {(g["gap"], g["metric"]): g["value"] for g in summary_fidelity.run()}
        self.assertGreaterEqual(by_key[("summary_fidelity", "summary_entity_recall")], 0.9)
        self.assertEqual(by_key[("summary_fidelity", "fallback_rate")], 0.0)


if __name__ == "__main__":
    unittest.main()
