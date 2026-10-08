"""M3 修复回归:review_chapter(auto_revise=True) 返回 diff。

之前 review_chapter 只回 {review, revised},UI 无法知道"改了什么"——
只能把 revised 全量覆盖到编辑器让用户肉眼比对。本 commit 在 auto_revise
触发且真写出修订时,顺手用 difflib.unified_diff 生成行级 diff(去掉
---/+++ 头部),给 UI 一个稳定的"红绿对比"输入。

运行:py -m unittest tests.test_revise_diff 或 py -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation._harness import EvalProject  # noqa: E402


class ReviseDiffTests(unittest.TestCase):
    def setUp(self):
        self.p = EvalProject()
        self.p.init(chapter_count=1)

    def tearDown(self):
        self.p.cleanup()

    def _ensure_chapter(self, chapter_id: str = "c001") -> str:
        """走 write_chapter 但 patch writer.write_chapter 返回固定文本,绕开真实 LLM。"""
        text = (
            "林尘站在悬崖边,冷风吹过衣袍。\n"
            "他低头看着深渊,忽然一道金光从谷底冲天而起。\n"
            "金光中似乎藏着一柄残剑,发出低沉的嗡鸣。\n"
            "他下意识伸手去抓,指尖刚一触碰,剧痛袭来。\n"
            "再次睁眼,他已身处一处石室,周围刻满远古符文。\n"
        )
        with mock.patch.object(self.p.agent.writer, "write_chapter", return_value=text), \
             mock.patch.object(self.p.agent.writer, "summarize", return_value="林尘崖下觉醒"):
            self.p.agent.write_chapter(chapter_id, review=False, verbose=False)
        return text

    def test_diff_field_present_no_revise(self):
        """未触发 auto_revise 时,返回 dict 应含 diff 字段(空 list)。"""
        self._ensure_chapter("c001")
        r = self.p.agent.review_chapter("c001", auto_revise=False)
        self.assertIn("diff", r)
        self.assertIsInstance(r["diff"], list)
        # MockBackend 的 review 不报 high severity → 不会真修订
        self.assertEqual(r["diff"], [])
        self.assertFalse(r["revised_applied"])

    def test_diff_field_keys_complete(self):
        """返回字段集:{review, revised, revised_applied, diff, diff_lines}。"""
        self._ensure_chapter("c001")
        r = self.p.agent.review_chapter("c001", auto_revise=False)
        for k in ("review", "revised", "revised_applied", "diff", "diff_lines"):
            self.assertIn(k, r, f"review_chapter 返回缺 {k}")

    def test_diff_lines_count_matches_diff(self):
        """diff_lines 应等于 len(diff)。"""
        self._ensure_chapter("c001")
        r = self.p.agent.review_chapter("c001", auto_revise=False)
        self.assertEqual(r["diff_lines"], len(r["diff"]))

    def test_diff_strips_header_metadata(self):
        """手动 patch reviewer.revise 触发修订,验证 diff 不含 ---/+++ 头部。"""
        self._ensure_chapter("c001")
        # 让 reviewer.revise 返回明显不同内容,触发实际写盘路径
        revised = (
            "林尘站在悬崖边,寒风凛冽。\n"
            "他俯瞰深渊,一道耀目金光从谷底升腾而起。\n"
            "金光中隐现一柄残破古剑,发出低沉鸣响。\n"
            "他伸手去抓,指尖触及,剧痛贯穿全身。\n"
            "再睁眼,已置身石室,周围刻满远古符文,散发着幽蓝光芒。\n"
        )
        with mock.patch.object(self.p.agent.reviewer, "revise", return_value=revised):
            # 同时把 review 结果改成有 high severity,让 need_revise 触发
            fake_review = {
                "overall": "需修订",
                "issues": [{"severity": "high", "type": "pacing",
                            "description": "节奏拖", "suggestion": "加速"}],
                "continuity_violations": [],
                "deviation": {},
            }
            with mock.patch.object(self.p.agent.reviewer, "review", return_value=fake_review):
                r = self.p.agent.review_chapter("c001", auto_revise=True)
        self.assertTrue(r["revised_applied"])
        self.assertGreater(len(r["diff"]), 0)
        for ln in r["diff"]:
            self.assertFalse(ln.startswith("---"),
                             f"diff 不应含 --- 头部: {ln[:50]}")
            self.assertFalse(ln.startswith("+++"),
                             f"diff 不应含 +++ 头部: {ln[:50]}")
        # 至少有一行 + 或 - (表示真的有改动)
        self.assertTrue(any(ln.startswith(("+", "-")) for ln in r["diff"]),
                        "diff 应至少包含一行 +/-")

    def test_diff_when_revise_returns_short_text(self):
        """revise 返回 < 50 字符(被判定为无效) → 不算修订, diff 应为空。"""
        self._ensure_chapter("c001")
        fake_review = {
            "overall": "需修订",
            "issues": [{"severity": "high", "type": "pacing",
                        "description": "x", "suggestion": "y"}],
            "continuity_violations": [],
            "deviation": {},
        }
        with mock.patch.object(self.p.agent.reviewer, "review", return_value=fake_review), \
             mock.patch.object(self.p.agent.reviewer, "revise", return_value="太短"):
            r = self.p.agent.review_chapter("c001", auto_revise=True)
        self.assertFalse(r["revised_applied"])
        self.assertEqual(r["diff"], [])


if __name__ == "__main__":
    unittest.main()
