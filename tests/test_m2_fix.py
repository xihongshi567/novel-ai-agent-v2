"""M2 修复回归：rag_truncation / setting_filter / chunk_boundary 指标断言达标。

走 M7 gap_check 真实代码路径（memory.build_context_bundle / search.chunk_text），
指标不达标即失败。

运行：py -m unittest tests.test_m2_fix 或 py -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.gap_checks import (  # noqa: E402
    chunk_boundary,
    rag_truncation,
    setting_filter,
)


class M2FixTests(unittest.TestCase):
    def test_rag_truncation_metrics(self):
        by_metric = {r["metric"]: r["value"] for r in rag_truncation.run()}
        self.assertEqual(by_metric["truncation_visibility"], 1.0)
        self.assertEqual(by_metric["rag_coverage"], 1.0)

    def test_setting_filter_metrics(self):
        by_metric = {r["metric"]: r["value"] for r in setting_filter.run()}
        self.assertGreaterEqual(by_metric["filter_precision"], 0.9)
        self.assertEqual(by_metric["filter_recall"], 1.0)

    def test_chunk_boundary_metric(self):
        r = chunk_boundary.run()[0]
        self.assertGreaterEqual(r["value"], 0.9)


if __name__ == "__main__":
    unittest.main()
