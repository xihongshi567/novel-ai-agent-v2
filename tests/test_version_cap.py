"""M4 修复回归：章节版本上限。

M4 之前 ChapterStore._archive_version 不删旧版本，长篇项目（100 章 × 几十次
修订 = 数千文件）让 versions 目录无限膨胀，Project.load 速度受影响。本测试
验证 _prune_old_versions 行为不变量。

运行：py -m unittest tests.test_version_cap 或 py -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from novel_agent.core.chapter import Chapter, ChapterStore  # noqa: E402


def _make_plan(cid: str = "c001"):
    from novel_agent.core.outline import ChapterPlan, ChapterStatus

    return ChapterPlan(
        chapter_id=cid, title="测试章", beat="b", goal="g",
        conflict="c", ending="e", status=ChapterStatus.drafted,
    )


class VersionCapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = ROOT / "projects" / "_test_version_cap"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.store = ChapterStore(max_versions_per_chapter=3)

    def tearDown(self):
        import shutil

        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def test_default_cap_is_20(self):
        s = ChapterStore()
        self.assertEqual(s.max_versions_per_chapter, 20)

    def test_archive_keeps_within_cap(self):
        plan = _make_plan()
        for i in range(3):
            self.store.write_chapter(self.tmp, plan, f"内容 v{i+1}", summary="s")
        versions = self.store.list_versions(self.tmp, "c001")
        self.assertEqual(len(versions), 3)

    def test_archive_prunes_when_over_cap(self):
        plan = _make_plan()
        # cap=3, 写 5 次 → 第 1 次写为 chapters/c001.md(无 v 文件), 第 2-5 次各归档一次
        # 归档后 v 文件 v1, v2, v3, v4; cap=3 时裁掉 v1, 留 [v2, v3, v4]
        for i in range(5):
            self.store.write_chapter(self.tmp, plan, f"内容 v{i+1}", summary="s")
        versions = self.store.list_versions(self.tmp, "c001")
        self.assertEqual(len(versions), 3, f"应保留 3 个，实际 {len(versions)}")
        kept_versions = [v["version"] for v in versions]
        self.assertEqual(kept_versions, [2, 3, 4], f"应保留 v2-v4，实际 {kept_versions}")
        # 物理文件也应被删
        vdir = self.tmp / "chapters" / "versions"
        self.assertFalse(
            (vdir / "c001.v1.md").exists(),
            "v1.md 应被删除",
        )

    def test_cap_zero_means_unlimited(self):
        self.store.max_versions_per_chapter = 0
        plan = _make_plan()
        for i in range(10):
            self.store.write_chapter(self.tmp, plan, f"v{i+1}", summary="s")
        versions = self.store.list_versions(self.tmp, "c001")
        self.assertEqual(len(versions), 10)

    def test_pruning_updates_versions_json(self):
        plan = _make_plan()
        for i in range(4):
            self.store.write_chapter(self.tmp, plan, f"v{i+1}", summary="s")
        # 重新 load 后看元信息（4 次写入 cap=3 不裁剪，留 v1-v3）
        new_store = ChapterStore.load(self.tmp)
        versions = new_store.list_versions(self.tmp, "c001")
        self.assertEqual(len(versions), 3)
        kept = [v["version"] for v in versions]
        self.assertEqual(kept, [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
