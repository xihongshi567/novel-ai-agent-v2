"""M5 修复回归：silent_failures / summary_purity 指标断言达标。

走 M7 gap_check 真实代码路径（novel.py write_chapter / review_chapter），
指标不达标即失败。silent_failures 走 _run() 的真实故障注入（mock writer.summarize
/ backup_project / track_chapter 抛错），断言每条降级路径都 surfaced=True，
避免仅靠 value==0.0 的"指标断言"漏掉真实失败被吞的情况。

summary_purity 加直接行为断言：summary 字段不含 [审校] 标记，review_note
独立字段非空——守住 M5 commit 删除的两行代码不被回退。

运行：py -m unittest tests.test_m5_fix 或 py -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation._harness import EvalProject  # noqa: E402
from evaluation.gap_checks import silent_failures, summary_fidelity  # noqa: E402


class M5FixTests(unittest.TestCase):
    def test_silent_swallow_rate(self):
        r = silent_failures.run()[0]
        self.assertEqual(r["value"], 0.0, f"silent_swallow_rate = {r['value']}")

    def test_each_failure_surfaced(self):
        # 真实注入故障：每条降级路径必须 surfaced=True，不能仅依赖聚合指标
        outcomes = silent_failures._run()
        for name, outcome in outcomes.items():
            self.assertTrue(
                outcome.get("surfaced") or outcome.get("raised"),
                f"{name} 降级路径未暴露: {outcome}",
            )

    def test_summary_purity(self):
        for r in summary_fidelity.run():
            if r["gap"] == "summary_purity":
                self.assertEqual(r["value"], 1.0, f"summary_purity = {r['value']}")
                return
        self.fail("summary_purity 指标缺失")

    def test_summary_field_no_review_marker(self):
        """write_chapter 后 summary 字段不得包含 [审校] 标记（守住 M5 删除的两行）。"""
        p = EvalProject()
        try:
            p.init(chapter_count=1)
            p.agent.write_chapter(p.plan.chapter_id, review=False)
            stored = p.agent.store.summaries.get(p.plan.chapter_id)
            self.assertIsNotNone(stored, "未生成 summary")
            self.assertNotIn(
                "[审校]", stored.summary,
                f"summary 字段被审校注记污染: {stored.summary!r}",
            )
        finally:
            p.cleanup()

    def test_review_note_field_populated(self):
        """review_chapter 后 chapter.review_note 独立字段非空（不再依赖拼回 summary）。"""
        p = EvalProject()
        try:
            p.init(chapter_count=1)
            p.agent.write_chapter(p.plan.chapter_id, review=False)
            p.agent.review_chapter(p.plan.chapter_id)
            ch = p.agent.store.read_chapter(p.dir, p.plan.chapter_id)
            self.assertIsNotNone(ch, "章节未写入")
            self.assertTrue(
                ch.review_note and ch.review_note.strip(),
                f"review_note 为空: {ch.review_note!r}",
            )
        finally:
            p.cleanup()


if __name__ == "__main__":
    unittest.main()
