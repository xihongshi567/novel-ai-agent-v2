"""缺口5 设定过滤双问题：本章相关条目的过滤是否生效。

走真实代码路径 Memory.build_context_bundle（core/memory.py:103-115 的 related 匹配
+ core/bible.py:108-112 的 include_ids 渲染）。两个问题：
  A. 变体名匹配失败 → related 为空 → 兜底渲染全量设定集（过滤失效）
  B. 子串匹配过宽（短名如"林"会命中所有含该字条目）
度量：对每个用例检查"故事设定"渲染文本里是否包含/排除了预期条目。
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from novel_agent.core import (
    Bible, Character, ChapterPlan, ChapterStore, Continuity, IdeaBank,
    Location, Memory, Outline, ThreadNetwork, Volume, World,
)
from novel_agent.core.manifesto import Manifesto

CASE_PATH = Path(__file__).resolve().parent.parent / "datasets" / "setting_filter_cases.json"

BIBLE = {
    "characters": [
        Character(id="char_linchen", name="林尘", role="主角", summary="废柴少年"),
        Character(id="char_linba", name="林霸", role="反派", summary="堂兄"),
        Character(id="char_suqing", name="苏沐晴", role="配角", summary="青梅竹马"),
    ],
    "locations": [
        Location(id="loc_qingyun", name="青云村", summary="主角故乡"),
        Location(id="loc_huangcheng", name="皇城", summary="帝都"),
    ],
}

ENTRY_NAMES = {c.name for c in BIBLE["characters"]} | {l.name for l in BIBLE["locations"]}


def _extract_setting_section(text: str) -> str:
    m = re.search(r"===== 故事设定 =====\n(.*?)(?:===== 世界观硬约束|===== 连续性约束|===== ACTIVE|===== 故事大纲)", text, re.S)
    return m.group(1) if m else text


def _run_case(case: dict) -> dict:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        bible = Bible(project="p", **BIBLE)
        plan_data = case["plan"]
        plan = ChapterPlan(
            chapter_id="c002", title="废柴少年",
            characters=plan_data["characters"], pov=plan_data["pov"],
            setting=plan_data["setting"],
            beat="林尘在村中被欺辱", goal="建立困境", conflict="弱 vs 强",
            ending="获得传承",
        )
        outline = Outline(project="p", volumes=[Volume(
            volume_id="v1", title="觉醒之卷", chapters=[
                ChapterPlan(chapter_id="c001", title="开端", beat="出生"),
                plan,
            ],
        )])
        store = ChapterStore(summaries={})
        store.write_chapter(root, outline.volumes[0].chapters[0],
                            "林尘出生在青云村。", summary="林尘出生。")

        memory = Memory(
            root, outline, bible, store, Continuity(), world=World(),
            ideas=IdeaBank(), threads=ThreadNetwork(), manifesto=Manifesto(),
            embedding_config={}, rag_top_k=2, rag_max_chars=300,
            recent_summary_count=1, recent_text_chars=100,
        )
        bundle = memory.build_context_bundle("c002")
        section = _extract_setting_section(bundle.text)

        present = [n for n in ENTRY_NAMES if n in section]
        expected = set(case["expected_names"])
        included_expected = set(present) & expected
        precision = len(included_expected) / len(present) if present else 1.0
        recall = len(included_expected) / len(expected) if expected else 1.0
        return {
            "case": case["id"], "expected": case["expected_names"],
            "unrelated": case["unrelated_names"], "present": present,
            "precision": precision, "recall": recall, "note": case["note"],
        }


def run() -> list[dict]:
    cases = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    details = [_run_case(c) for c in cases]
    agg_precision = sum(d["precision"] for d in details) / len(details)
    agg_recall = sum(d["recall"] for d in details) / len(details)
    return [
        {
            "gap": "setting_filter",
            "metric": "filter_precision",
            "cases": len(cases),
            "value": agg_precision,
            "target": 0.9,
            "detail": details,
        },
        {
            "gap": "setting_filter",
            "metric": "filter_recall",
            "cases": len(cases),
            "value": agg_recall,
            "target": 1.0,
            "detail": details,
        },
    ]
