"""缺口9 chunk 硬切：固定 900 字符硬切，切点大多落在句子中间。

走真实代码路径 SearchEngine.index_project（core/search.py:209-223 的 chunk_text），
通过临时项目的一章长正文重建索引后，检查各非末 chunk 的末字符是否落在句读处。

注意：chunk 滑动窗口带 140 字 overlap，实体即使横跨切点也会完整出现在下一
chunk 中，所以"实体被劈开"在现有参数下不会发生；真实缺陷是切点与句子边界
无关（语义断裂、片段句首残缺），以 boundary_quality 度量。
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from novel_agent.core import Bible, ChapterPlan, ChapterStore, Continuity, IdeaBank, World
from novel_agent.core.search import SearchEngine

CASE_PATH = Path(__file__).resolve().parent.parent / "datasets" / "chunk_cases.json"

SENTENCE_END = "。！？…\"”』"


def _build_long_chapter(entity: str) -> str:
    """构造长正文（>3000 字），每个句子都以句号结尾，实体置于 900 字切点附近。"""
    unit = "青云山深处云雾缭绕，古木参天，林尘沿着山径缓缓前行。"
    pre = "石壁之上，隐约刻着一行古老的铭文，铭文所载正是"
    post = "，据说只有有缘人才能领悟其中的奥妙。此后数日，林尘日日参悟，终于有所明悟。"
    head = unit * 40  # 40*27=1080 > 900，首切点在句中
    return head + pre + entity + post + unit * 60


def run() -> list[dict]:
    entities = [c["entity"] for c in json.loads(CASE_PATH.read_text(encoding="utf-8"))]
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        content = _build_long_chapter(entities[0])
        store = ChapterStore(summaries={})
        store.write_chapter(root, ChapterPlan(
            chapter_id="c001", title="古洞传承", beat="林尘在崖底古洞发现传承",
        ), content, summary="林尘坠崖获得传承。")

        engine = SearchEngine(root)
        engine.index_project(
            bible=Bible(project="p"), continuity=Continuity(),
            world=World(), ideas=IdeaBank(), store=store,
            project_dir=root, embedder=None,
        )

        chunks = sorted(
            (doc for doc in engine.docs.values()
             if doc.kind == "chapter_chunk" and doc.meta.get("chunk_index")),
            key=lambda d: d.meta["chunk_index"],
        )
        non_final = [c for c in chunks if c.meta["chunk_index"] < c.meta["chunk_count"]]
        good = sum(1 for c in non_final if c.text and c.text[-1] in SENTENCE_END)
        quality = good / len(non_final) if non_final else 1.0

        detail = [{
            "chunk_count": len(chunks),
            "boundary_count": len(non_final),
            "sentence_end_boundaries": good,
            "boundary_chars": [c.text[-1] if c.text else "" for c in non_final[:10]],
        }]
        return [{
            "gap": "chunk_boundary",
            "metric": "boundary_quality",
            "cases": len(non_final),
            "value": quality,
            "target": 0.9,
            "detail": detail,
        }]
