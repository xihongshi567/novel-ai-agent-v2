"""缺口2 伏笔回收误判：回收判定是否命中正确目标。

走真实代码路径 StateTracker.apply_to_continuity（agents/tracker.py:100-112），
当前逻辑是 _similar() 二元组重叠 >=0.4 且先到先得。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from novel_agent.agents.tracker import StateTracker
from novel_agent.core import Continuity, Foreshadow, ForeshadowStatus

CASE_PATH = Path(__file__).resolve().parent.parent / "datasets" / "foreshadow_cases.json"


def run() -> list[dict]:
    cases = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    detail = []
    ok = 0
    total_flips = 0
    correct_flips = 0
    total_expect = 0
    recovered_expect = 0
    for case in cases:
        continuity = Continuity(project="p", foreshadows=[
            Foreshadow(id=f"fs_{i + 1:03d}", chapter_id="c006", description=d)
            for i, d in enumerate(case["planted"])
        ])
        tracker = StateTracker(backend=None)
        counts = tracker.apply_to_continuity(
            continuity, "c010", {"foreshadows_resolved": [{"description": case["resolved"]}]}
        )
        flipped = [f.id for f in continuity.foreshadows
                   if f.status == ForeshadowStatus.resolved]
        expected = case["expected_resolved"]
        correct = sorted(flipped) == sorted(expected)
        ok += correct
        total_flips += len(flipped)
        correct_flips += len(set(flipped) & set(expected))
        total_expect += len(expected)
        recovered_expect += len(set(flipped) & set(expected))
        detail.append({
            "case": case["id"], "planted": case["planted"], "resolved": case["resolved"],
            "expected": expected, "flipped": flipped, "correct": correct,
            "note": case["note"],
        })
    n = len(cases)
    precision = correct_flips / total_flips if total_flips else 1.0
    recall = recovered_expect / total_expect if total_expect else 1.0
    return [
        {
            "gap": "foreshadow_recovery",
            "metric": "resolution_accuracy",
            "cases": n,
            "value": ok / n,
            "target": 1.0,
            "detail": detail,
        },
        {
            "gap": "foreshadow_recovery",
            "metric": "resolution_precision",
            "cases": n,
            "value": precision,
            "target": 1.0,
            "detail": detail,
        },
        {
            "gap": "foreshadow_recovery",
            "metric": "resolution_recall",
            "cases": n,
            "value": recall,
            "target": 1.0,
            "detail": detail,
        },
    ]
