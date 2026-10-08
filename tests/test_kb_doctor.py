"""M7 修复回归：kb doctor 诊断命令。

kb doctor 之前缺位:用户改 bible/continuity/threads 后没有"数据完整性体检"
入口,只能等写到一半报 KeyError。doctor() 跨 5 个子表校验 id 唯一/必填
字段/状态一致性,返回 healthy/issues/summary 三段。

运行：py -m unittest tests.test_kb_doctor 或 py -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation._harness import EvalProject  # noqa: E402


class KbDoctorTests(unittest.TestCase):
    def setUp(self):
        self.p = EvalProject()
        self.p.init(chapter_count=2)

    def tearDown(self):
        self.p.cleanup()

    def test_healthy_project(self):
        """新建项目无 error/warning。"""
        r = self.p.agent.kb.doctor()
        self.assertTrue(r["healthy"], f"新建项目应 healthy,issues={r['issues']}")
        self.assertEqual(r["errors"], 0)
        self.assertIsInstance(r["issues"], list)

    def test_summary_keys(self):
        """summary 应含 5 个子表的统计。"""
        s = self.p.agent.kb.doctor()["summary"]
        for k in ("bible", "continuity", "world", "ideas", "threads"):
            self.assertIn(k, s, f"summary 缺 {k}")

    def test_bible_counts_match_loaded(self):
        """bible summary 数字应等于实际加载数。"""
        kb = self.p.agent.kb
        r = kb.doctor()
        b = r["summary"]["bible"]
        self.assertEqual(b["characters"], len(kb.bible.characters))
        self.assertEqual(b["locations"], len(kb.bible.locations))
        self.assertEqual(b["factions"], len(kb.bible.factions))
        self.assertEqual(b["items"], len(kb.bible.items))
        self.assertEqual(b["lore"], len(kb.bible.lore))

    def test_detect_duplicate_foreshadow_id(self):
        """同 id 的伏笔应报 error。"""
        kb = self.p.agent.kb
        # 注入两个 id 重复的 foreshadow
        from novel_agent.core.continuity import Foreshadow, ForeshadowStatus
        kb.continuity.foreshadows.append(
            Foreshadow(id="fs_dup", chapter_id="c001", description="A", status=ForeshadowStatus.planted)
        )
        kb.continuity.foreshadows.append(
            Foreshadow(id="fs_dup", chapter_id="c002", description="B", status=ForeshadowStatus.planted)
        )
        r = kb.doctor()
        self.assertFalse(r["healthy"])
        msgs = [i for i in r["issues"] if i["module"] == "continuity" and "fs_dup" in i["path"]]
        self.assertGreater(len(msgs), 0, "未捕获 fs_dup 重复")

    def test_detect_planted_foreshadow_missing_chapter(self):
        """planted 状态缺 chapter_id 应报 error。"""
        kb = self.p.agent.kb
        from novel_agent.core.continuity import Foreshadow, ForeshadowStatus
        kb.continuity.foreshadows.append(
            Foreshadow(id="fs_x", chapter_id="", description="X", status=ForeshadowStatus.planted)
        )
        r = kb.doctor()
        self.assertFalse(r["healthy"])
        self.assertTrue(any("chapter_id" in i["message"] for i in r["issues"]))

    def test_detect_timeline_missing_chapter(self):
        """timeline 事件缺 chapter_id 应报 error。"""
        kb = self.p.agent.kb
        from novel_agent.core.continuity import TimelineEvent
        kb.continuity.timeline.append(
            TimelineEvent(chapter_id="", event="失踪", time_label="", anchor="", duration="")
        )
        r = kb.doctor()
        self.assertFalse(r["healthy"])
        self.assertTrue(any("chapter_id" in i["message"] and i["module"] == "continuity" for i in r["issues"]))

    def test_detect_empty_world_element(self):
        """world element 缺 name 应报 error。"""
        kb = self.p.agent.kb
        from novel_agent.core.world import WorldElement, WorldCategory
        kb.world.elements.append(WorldElement(id="we_x", name="", category=WorldCategory.rule, summary=""))
        r = kb.doctor()
        self.assertFalse(r["healthy"])
        self.assertTrue(any(i["module"] == "world" and "name" in i["message"] for i in r["issues"]))

    def test_warnings_for_empty_fact(self):
        """空 content 的 fact 应报 warning(不阻断 healthy)。"""
        kb = self.p.agent.kb
        from novel_agent.core.continuity import Fact
        kb.continuity.facts.append(Fact(id="f_empty", chapter_id="c001", category="event", content=""))
        r = kb.doctor()
        # 仍 healthy(warning 不计入)
        self.assertTrue(r["healthy"])
        self.assertGreater(r["warnings"], 0)

    def test_open_foreshadows_counted(self):
        """planted 状态计入 open_foreshadows。"""
        kb = self.p.agent.kb
        from novel_agent.core.continuity import Foreshadow, ForeshadowStatus
        kb.continuity.foreshadows.append(
            Foreshadow(id="fs_a", chapter_id="c001", description="A", status=ForeshadowStatus.planted)
        )
        kb.continuity.foreshadows.append(
            Foreshadow(id="fs_b", chapter_id="c001", description="B", status=ForeshadowStatus.resolved)
        )
        r = kb.doctor()
        self.assertEqual(r["summary"]["continuity"]["foreshadows"], 2)
        self.assertEqual(r["summary"]["continuity"]["open_foreshadows"], 1)


if __name__ == "__main__":
    unittest.main()
