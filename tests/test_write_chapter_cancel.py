"""M5 修复回归:write_chapter 接受 cancel_event 可中断。

之前 write_chapter 一旦开始,UI/CLI 想中断只能等 LLM 跑完 + 审校跑完——
3 分钟起步。本 commit 让调用方注入 threading.Event,write_chapter 在
每个 LLM 调用前/后/审校前检查,触发即把 plan.status 回退 pending
并抛 WriteChapterCancelled(RuntimeError 子类)。

运行:py -m unittest tests.test_write_chapter_cancel 或 py -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
import threading
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation._harness import EvalProject  # noqa: E402
from novel_agent.agents.novel import WriteChapterCancelled  # noqa: E402
from novel_agent.core import ChapterStatus  # noqa: E402


class WriteChapterCancelTests(unittest.TestCase):
    def setUp(self):
        self.p = EvalProject()
        self.p.init(chapter_count=2)

    def tearDown(self):
        self.p.cleanup()

    def test_no_cancel_event_runs_through(self):
        """不传 cancel_event 时,行为与旧版一致(全流程跑通)。"""
        text = "林尘下崖,得传承。" * 10
        with mock.patch.object(self.p.agent.writer, "write_chapter", return_value=text), \
             mock.patch.object(self.p.agent.writer, "summarize", return_value="林尘得传承"):
            r = self.p.agent.write_chapter("c001", review=False, verbose=False)
        self.assertIn("content", r)
        self.assertEqual(self.p.agent.outline.find("c001").status,
                         ChapterStatus.drafted)

    def test_pre_set_event_raises_immediately(self):
        """先 set event 再调,首句 _check_cancel 抛 WriteChapterCancelled。"""
        ev = threading.Event()
        ev.set()
        with self.assertRaises(WriteChapterCancelled) as cm:
            self.p.agent.write_chapter("c001", review=False, verbose=False,
                                       cancel_event=ev)
        self.assertIn("c001", str(cm.exception))
        # plan.status 应回退 pending(即使这次没改成 writing 也无副作用)
        st = self.p.agent.outline.find("c001").status
        self.assertIn(st, (ChapterStatus.pending, ChapterStatus.writing))

    def test_set_event_during_writer_raises(self):
        """writer.write_chapter 被调时若 event 已 set,抛 WriteChapterCancelled。"""
        text = "林尘下崖,得传承。" * 10
        def fake_write(*args, **kwargs):
            ev.set()
            return text
        ev = threading.Event()
        with mock.patch.object(self.p.agent.writer, "write_chapter", side_effect=fake_write), \
             mock.patch.object(self.p.agent.writer, "summarize", return_value="x"):
            with self.assertRaises(WriteChapterCancelled):
                self.p.agent.write_chapter("c001", review=False, verbose=False,
                                           cancel_event=ev)

    def test_status_reverted_on_cancel(self):
        """cancel 触发后 plan.status 应回退 pending(不卡在 writing)。"""
        ev = threading.Event()
        ev.set()
        with self.assertRaises(WriteChapterCancelled):
            self.p.agent.write_chapter("c001", review=False, verbose=False,
                                       cancel_event=ev)
        # 显式 set 场景:writing → 立即 cancel → 状态回 pending
        st = self.p.agent.outline.find("c001").status
        self.assertEqual(st, ChapterStatus.pending,
                         f"cancel 后 status 应为 pending,实际 {st}")

    def test_no_crash_without_cancel_kwarg(self):
        """老调用方式(无 cancel_event 参数)仍可用。"""
        text = "林尘下崖,得传承。" * 10
        with mock.patch.object(self.p.agent.writer, "write_chapter", return_value=text), \
             mock.patch.object(self.p.agent.writer, "summarize", return_value="x"):
            # 不传 cancel_event
            r = self.p.agent.write_chapter("c001", review=False, verbose=False)
        self.assertIn("content", r)

    def test_cancelled_is_runtime_error_subclass(self):
        """WriteChapterCancelled 必须是 RuntimeError 子类,老代码 except RuntimeError 能捕获。"""
        self.assertTrue(issubclass(WriteChapterCancelled, RuntimeError))
        ev = threading.Event()
        ev.set()
        with self.assertRaises(RuntimeError):
            self.p.agent.write_chapter("c001", review=False, verbose=False,
                                       cancel_event=ev)


if __name__ == "__main__":
    unittest.main()
