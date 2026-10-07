"""缺口3 摘要永久有损 + 缺口8 摘要污染。

走真实代码路径：
  - novel.py:426-429  summarize 抛错 → content[:200] 兜底（头部截断，尾部信息永久丢失）
  - chapter.py:118  `summary or content[:200]` 同一兜底
  - novel.py:511  审校注记 [审校] 被追加进摘要（污染后续章节看到的前情提要）

度量：
  - summary_entity_recall：正文关键实体在摘要中的存活率（direction=max，目标≥0.9）
  - fallback_rate：走 content[:200] 兜底的比例（direction=min，目标 0）
  - summary_purity：摘要是否混入审校注记等非剧情内容（direction=max，目标 1）
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

HEAD_UNIT = "林尘在青云村外的石坪上练剑，剑光霍霍，尘土飞扬。"
TAIL_ENTITY = "赤焰剑"
TAIL_SENTENCE = "突然，一把赤焰剑从天而降，插在林尘面前。"


def _custom_novel_text() -> str:
    head = HEAD_UNIT * 25  # 25*24=600 字，全部是 林尘
    return head + TAIL_SENTENCE


def _run() -> dict:
    from novel_agent.agents.writer import WriterAgent

    from .._harness import EvalProject

    p = EvalProject()
    try:
        p.backend.novel_text = _custom_novel_text()
        p.init(chapter_count=2)
        cid = p.plan.chapter_id

        # summarize 抛错 → novel.py:428 兜底 content[:200]
        with mock.patch.object(WriterAgent, "summarize",
                               side_effect=RuntimeError("injected fault")):
            r = p.agent.write_chapter(cid, review=False)
        summary = p.agent.store.summaries[cid].summary
        fallback = summary == r["content"][:200]

        survived = [e for e in (HEAD_UNIT[:2], TAIL_ENTITY) if e in summary]
        entity_recall = len(survived) / 2

        # 缺口8：审校注记污染摘要
        p.agent.review_chapter(cid)
        polluted = "[审校]" in p.agent.store.summaries[cid].summary
        return {
            "fallback": fallback,
            "survived_entities": survived,
            "entity_recall": entity_recall,
            "summary_len": len(summary),
            "polluted_by_review_note": polluted,
            "summary_tail": summary[-60:],
        }
    finally:
        p.cleanup()


def run() -> list[dict]:
    s = _run()
    detail = [s]
    return [
        {
            "gap": "summary_fidelity",
            "metric": "summary_entity_recall",
            "cases": 2,
            "value": s["entity_recall"],
            "target": 0.9,
            "detail": detail,
        },
        {
            "gap": "summary_fidelity",
            "metric": "fallback_rate",
            "direction": "min",
            "cases": 1,
            "value": 1.0 if s["fallback"] else 0.0,
            "target": 0.0,
            "detail": detail,
        },
        {
            "gap": "summary_purity",
            "metric": "summary_purity",
            "cases": 1,
            "value": 0.0 if s["polluted_by_review_note"] else 1.0,
            "target": 1.0,
            "detail": detail,
        },
    ]
