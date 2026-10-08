"""M2 修复回归：SearchEngine 增量 add_doc / remove_doc。

M2 之前 SearchEngine 只暴露全量 index_project()。频繁改 bible/idea/continuity
（kb_agent.enrich / audit）会触发 is_stale → 全量重 embed，30 章 + 50 设定
项目一次约 10s+。本 commit 加 add_doc / remove_doc，让 M5 编排者可以单条
更新而不走全量重建。ensure_index_fresh 暂未接入增量模式（仍走全量），
本测试只验证新 API 自身行为。

运行：py -m unittest tests.test_incremental_index 或 py -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from novel_agent.core.search import Doc, SearchEngine  # noqa: E402


class IncrementalIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = ROOT / "projects" / "_test_inc_index"
        if self.tmp.exists():
            import shutil
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import shutil
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def test_add_doc_text_only(self):
        """无 embedder 时 add_doc 只写文本索引，关键词搜索能找到。"""
        engine = SearchEngine(self.tmp)
        d = Doc(id="char:linchen", kind="character", ref="char_linchen",
                text="林尘：废柴少年实为上古血脉", title="林尘")
        engine.add_doc(d)
        self.assertIn("char:linchen", engine.docs)
        hits = engine.search_keyword("林尘")
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0].doc.id, "char:linchen")

    def test_add_doc_persists(self):
        """add_doc 后重新 load 仍能找到。"""
        engine = SearchEngine(self.tmp)
        d = Doc(id="loc:qingyun", kind="location", ref="loc_qingyun",
                text="青云村：主角故乡", title="青云村")
        engine.add_doc(d)
        # 重新构造 engine 模拟 load
        engine2 = SearchEngine(self.tmp)
        self.assertIn("loc:qingyun", engine2.docs)
        hits = engine2.search_keyword("青云村")
        self.assertGreater(len(hits), 0)

    def test_add_doc_empty_text_skipped(self):
        """空文本 doc 不会写入。"""
        engine = SearchEngine(self.tmp)
        d = Doc(id="empty", kind="character", ref="x", text="   ", title="")
        engine.add_doc(d)
        self.assertNotIn("empty", engine.docs)

    def test_add_doc_overwrites_same_id(self):
        """同 id 重复 add_doc 会替换内容。"""
        engine = SearchEngine(self.tmp)
        engine.add_doc(Doc(id="x", kind="character", ref="r",
                           text="旧内容 原始设定", title="x"))
        engine.add_doc(Doc(id="x", kind="character", ref="r",
                           text="新内容 升级后", title="x"))
        self.assertEqual(len(engine.docs), 1)
        hits = engine.search_keyword("升级后")
        self.assertGreater(len(hits), 0)

    def test_remove_doc(self):
        """remove_doc 后关键词搜不到。"""
        engine = SearchEngine(self.tmp)
        engine.add_doc(Doc(id="to_remove", kind="character", ref="r",
                           text="独特关键词 quanjimao", title="x"))
        hits_before = engine.search_keyword("quanjimao")
        self.assertGreater(len(hits_before), 0)
        engine.remove_doc("to_remove")
        self.assertNotIn("to_remove", engine.docs)
        hits_after = engine.search_keyword("quanjimao")
        self.assertEqual(len(hits_after), 0)

    def test_remove_nonexistent_doc_noop(self):
        """删除不存在的 doc 不报错。"""
        engine = SearchEngine(self.tmp)
        engine.remove_doc("not_there")  # 不应抛
        self.assertNotIn("not_there", engine.docs)


if __name__ == "__main__":
    unittest.main()
