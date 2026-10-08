"""M2 修复回归：ContextBundle.section_stats。

M2 之前只有 rag_stats，其他 section 的注入量不透明——排查"为什么 LLM 上下文
这么长"只能全文搜。本测试验证 section_stats 覆盖所有 section，chars / items
字段对得上实际注入量。

运行：py -m unittest tests.test_section_stats 或 py -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation._harness import EvalProject  # noqa: E402


class SectionStatsTests(unittest.TestCase):
    def setUp(self):
        self.p = EvalProject()
        self.p.init(chapter_count=2)

    def tearDown(self):
        self.p.cleanup()

    def test_section_stats_field_present(self):
        bundle = self.p.agent._memory().build_context_bundle("c001")
        self.assertTrue(hasattr(bundle, "section_stats"))
        self.assertIsInstance(bundle.section_stats, dict)

    def test_section_stats_includes_bible(self):
        bundle = self.p.agent._memory().build_context_bundle("c001")
        self.assertIn("bible", bundle.section_stats)
        stats = bundle.section_stats["bible"]
        self.assertIn("chars", stats)
        self.assertIn("items", stats)
        self.assertGreater(stats["chars"], 0)

    def test_section_stats_includes_outline(self):
        bundle = self.p.agent._memory().build_context_bundle("c001")
        self.assertIn("outline", bundle.section_stats)
        self.assertGreater(bundle.section_stats["outline"]["chars"], 0)

    def test_section_stats_includes_current_plan(self):
        bundle = self.p.agent._memory().build_context_bundle("c001")
        self.assertIn("current_plan", bundle.section_stats)
        self.assertGreater(bundle.section_stats["current_plan"]["chars"], 0)

    def test_empty_section_not_in_stats(self):
        """空 section 不应在 stats 里（避免噪音）。"""
        # MockBackend 不生成 manifesto / world_constraints / threads
        bundle = self.p.agent._memory().build_context_bundle("c001")
        # 至少有 bible / outline / current_plan 这些非空项
        non_empty = ["bible", "outline", "current_plan"]
        for s in non_empty:
            self.assertIn(s, bundle.section_stats, f"{s} 应有 stats")

    def test_chars_matches_section_text(self):
        """section_stats.chars 应等于实际注入的 text 长度（不含标题行前缀）。"""
        bundle = self.p.agent._memory().build_context_bundle("c001")
        # 验证 bible:从 text 里切出"===== 故事设定 ====="后的内容长度
        bible_stats = bundle.section_stats["bible"]
        text = bundle.text
        marker = "===== 故事设定 =====\n\n"
        if marker in text:
            start = text.index(marker) + len(marker)
            # 找下一个 "=====" 或结尾
            end = text.find("=====", start)
            if end == -1:
                end = len(text)
            actual_chars = text[start:end].rstrip("\n").rstrip()
            self.assertEqual(bible_stats["chars"], len(actual_chars),
                             f"bible chars 期望 {len(actual_chars)}，实际 {bible_stats['chars']}")


if __name__ == "__main__":
    unittest.main()
