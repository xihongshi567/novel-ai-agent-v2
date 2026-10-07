"""缺口1 名字匹配断裂：LLM 返回的角色变体名能否解析到 bible 角色。

走真实代码路径 StateTracker.apply_to_bible（agents/tracker.py:42-69），
其匹配逻辑是 `name in c.name or c.name in name`（子串双向）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from novel_agent.agents.tracker import StateTracker
from novel_agent.core import Bible, Character

CASE_PATH = Path(__file__).resolve().parent.parent / "datasets" / "name_matching_cases.json"

def _fresh_bible() -> Bible:
    # 每个用例独立实例，避免 status_history 串扰
    return Bible(project="p", characters=[
        Character(id="char_linchen", name="林尘", role="主角", summary="废柴少年"),
        Character(id="char_linba", name="林霸", role="反派", summary="堂兄"),
        Character(id="char_suqing", name="苏沐晴", role="配角", summary="青梅竹马"),
        Character(id="char_laozu", name="青云老祖", role="配角", summary="隐居强者"),
    ])


def _resolve(bible: Bible, name: str, chapter_id: str) -> str | None:
    """用真实 apply_to_bible 解析，返回被更新的角色 id（更新数为 0 则 None）。"""
    tracker = StateTracker(backend=None)
    data = {"character_status": [{"name": name, "status": "本章出场"}]}
    updated = tracker.apply_to_bible(bible, chapter_id, data)
    if not updated:
        return None
    for c in bible.characters:
        if c.status_history and c.status_history[-1].get("chapter") == chapter_id:
            return c.id
    return None


def run() -> list[dict]:
    cases = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    detail = []
    ok = 0
    for i, case in enumerate(cases):
        bible = _fresh_bible()
        got = _resolve(bible, case["name"], f"c0{i + 5:02d}")
        correct = got == case["expected_char_id"]
        ok += correct
        detail.append({
            "name": case["name"], "expected": case["expected_char_id"],
            "resolved": got, "correct": correct, "note": case["note"],
        })
    return [{
        "gap": "name_matching",
        "metric": "name_resolution_rate",
        "cases": len(cases),
        "value": ok / len(cases),
        "target": 1.0,
        "detail": detail,
    }]
