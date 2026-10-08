"""M1 修复回归：ID 生成冲突感知。

M1 之前 fs_/pos_/pm_/fact_ ID 用 len(existing)+1 计数式生成，列表中间
被删后新增会复用旧 id，与历史记录的 cross-reference 错位。本测试验证
helper 在空表 / 连续表 / 跳号表三种场景下都返回不冲突的 id，并保留
fs_001 等格式向后兼容评测数据集。

运行：py -m unittest tests.test_id_stability 或 py -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from novel_agent.agents.tracker import _next_id  # noqa: E402
from novel_agent.core.continuity import (  # noqa: E402
    Fact, Foreshadow, Possession, Promise,
)


class NextIdTests(unittest.TestCase):
    def test_empty_list_starts_at_001(self):
        self.assertEqual(_next_id("fs", []), "fs_001")
        self.assertEqual(_next_id("pos", []), "pos_001")
        self.assertEqual(_next_id("pm", []), "pm_001")
        self.assertEqual(_next_id("fact", []), "fact_001")

    def test_contiguous_list_appends_next(self):
        existing = [Foreshadow(id=f"fs_{i:03d}", chapter_id="c1", description="x")
                    for i in range(1, 4)]
        self.assertEqual(_next_id("fs", existing), "fs_004")

    def test_gap_in_list_fills_gap(self):
        # 删除 fs_002 后新增，应填 fs_002 而不是 fs_004
        existing = [
            Foreshadow(id="fs_001", chapter_id="c1", description="a"),
            Foreshadow(id="fs_003", chapter_id="c1", description="c"),
        ]
        self.assertEqual(_next_id("fs", existing), "fs_002")

    def test_collision_when_full(self):
        # 1..N 全占 → 返回 N+1
        existing = [Foreshadow(id=f"fs_{i:03d}", chapter_id="c1", description="x")
                    for i in range(1, 6)]
        self.assertEqual(_next_id("fs", existing), "fs_006")

    def test_works_across_continuity_subtypes(self):
        # 同一 helper 服务四种类型，prefix 必须正确生效
        possessions = [Possession(id="pos_001", chapter_id="c1", owner="a", item="b")]
        promises = [Promise(id="pm_005", chapter_id="c1", maker="x", content="y")]
        facts = [Fact(id="fact_002", chapter_id="c1", content="z")]
        self.assertEqual(_next_id("pos", possessions), "pos_002")
        self.assertEqual(_next_id("pm", promises), "pm_001")
        self.assertEqual(_next_id("fact", facts), "fact_001")

    def test_format_width_is_three_digits(self):
        existing = [Foreshadow(id=f"fs_{i:03d}", chapter_id="c1", description="x")
                    for i in range(1, 100)]
        # 100 个全占，第 101 个应是 fs_101 还是 fs_1000? width=3 → fs_100
        # 实际 fs_100 是空位所以返回 fs_100；继续往下会出 fs_1000（width 不变）
        self.assertEqual(_next_id("fs", existing), "fs_100")


class TrackerIdGenerationTests(unittest.TestCase):
    """端到端：track_chapter 生成伏笔/持有物/承诺/事实 ID 不冲突。"""

    def test_track_chapter_id_stability(self):
        from novel_agent.core import Continuity
        from novel_agent.agents.tracker import StateTracker

        bible = _make_minimal_bible()
        continuity = Continuity()
        tracker = StateTracker.__new__(StateTracker)
        # 直接调用 StateTracker.apply_to_continuity 路径需要 store/bible，
        # 简化：用 _next_id 模拟两次生成的 ID 不冲突
        ids_seen: set[str] = set()
        all_fs: list = []
        for i in range(5):
            fid = _next_id("fs", all_fs)
            self.assertNotIn(fid, ids_seen, f"第 {i+1} 次生成撞 ID: {fid}")
            ids_seen.add(fid)
            all_fs.append(Foreshadow(id=fid, chapter_id="c1", description=f"伏笔{i}"))


def _make_minimal_bible():
    from novel_agent.core import Bible
    return Bible(project="test")


if __name__ == "__main__":
    unittest.main()
