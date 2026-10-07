"""缺口4 RAG 截断无感知：命中超出 rag_max_chars 预算被静默丢弃。

走真实代码路径 Memory.build_context_bundle（core/memory.py:172-188），
构造 8 章已写章节（8 个不同 ref 的 chapter_chunk，hybrid_search 的 ref 去重
每章只保留一个 chunk），预算 3500 字 → 只装得下 3 个 block，其余静默丢弃。

度量：
  - truncation_visibility：ContextBundle 是否暴露"被丢弃的 hits"信息（契约：
    bundle.rag_stats 且 dropped>0，或 bundle.truncation 为真）。当前无 → 0。
  - rag_coverage：实际纳入的 block 数 / 命中总数（当前因静默 break < 1）。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from novel_agent.core import (
    Bible, ChapterPlan, ChapterStore, Continuity, IdeaBank,
    Memory, Outline, ThreadNetwork, Volume, World,
)
from novel_agent.core.manifesto import Manifesto
from novel_agent.core.search import SearchEngine

UNIT = "林尘深入古洞寻找传承与机关之谜，古洞寻宝取得传承，机关重重，危机四伏。"
CH_COUNT = 8
RAG_MAX_CHARS = 3500


def _run_scenario() -> dict:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        store = ChapterStore(summaries={})
        chapters = []
        for i in range(1, CH_COUNT + 1):
            cid = f"c{i:03d}"
            plan = ChapterPlan(chapter_id=cid, title="古洞寻宝",
                               beat="林尘深入古洞寻找传承")
            store.write_chapter(root, plan, UNIT * 90,  # ≈2430 字 → 3 chunk
                                summary="林尘在古洞找到传承。")
            chapters.append(plan)

        current = ChapterPlan(
            chapter_id=f"c{CH_COUNT + 1:03d}", title="古洞寻宝", pov="林尘",
            setting="古洞", characters=["林尘"],
            beat="林尘深入古洞寻找传承与机关之谜",
            goal="取得传承", conflict="机关重重", ending="传承入体",
        )
        outline = Outline(project="p", volumes=[Volume(
            volume_id="v1", title="觉醒之卷", chapters=[*chapters, current],
        )])

        memory = Memory(
            root, outline, Bible(project="p"), store, Continuity(),
            world=World(), ideas=IdeaBank(), threads=ThreadNetwork(),
            manifesto=Manifesto(), embedding_config={},
            rag_top_k=6, rag_max_chars=RAG_MAX_CHARS,
            recent_summary_count=1, recent_text_chars=100,
        )
        bundle = memory.build_context_bundle(current.chapter_id)

        engine = SearchEngine(root)
        rag_query = " ".join(x for x in [
            current.title, current.beat, current.goal, current.conflict, current.ending
        ] if x)
        hits = engine.hybrid_search(
            rag_query, embedder=None,
            kinds=["chapter_chunk", "summary", "character", "location",
                   "faction", "item", "lore", "world", "foreshadow",
                   "fact", "promise"],
            top_k=6,
        )
        included = len(bundle.retrieved_sources)
        dropped = max(0, len(hits) - included)

        visible = False
        rag_stats = getattr(bundle, "rag_stats", None)
        if isinstance(rag_stats, dict):
            visible = rag_stats.get("dropped", 0) > 0
        if not visible and getattr(bundle, "truncation", None):
            visible = True
        return {
            "chapters": CH_COUNT, "rag_max_chars": RAG_MAX_CHARS,
            "hits": len(hits), "included": included, "dropped": dropped,
            "visible": visible,
            "coverage": included / len(hits) if hits else 1.0,
        }


def run() -> list[dict]:
    s = _run_scenario()
    detail = [s]
    return [
        {
            "gap": "rag_truncation",
            "metric": "truncation_visibility",
            "cases": 1,
            "value": 1.0 if s["visible"] else 0.0,
            "target": 1.0,
            "detail": detail,
        },
        {
            "gap": "rag_truncation",
            "metric": "rag_coverage",
            "cases": 1,
            "value": s["coverage"],
            "target": 1.0,
            "detail": detail,
        },
    ]
