"""缺口7 静默失败：write_chapter 流程里的异常被 except: pass 吞掉。

走真实代码路径 novel.py:406-481，注入三类故障：
  a. writer.summarize 抛错        → novel.py:428 吞掉，改用 content[:200]
  b. backup_project 抛错          → novel.py:460 吞掉
  c. track_chapter 抛错           → novel.py:479 吞掉（仅 verbose 时打印）

度量 silent_swallow_count：被吞掉且对调用方无任何可见痕迹（抛错/结果含
errors|warnings|failure 字段）的注入故障数。当前 3/3 → 目标 0/3。
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from .._harness import EvalProject


def _attempt(p: EvalProject, patcher) -> dict:
    p.init(chapter_count=2)
    cid = p.plan.chapter_id
    with patcher:
        try:
            result = p.agent.write_chapter(cid, review=False)
            raised = False
        except Exception as e:  # noqa: BLE001
            return {"raised": True, "surfaced": True, "exception": str(e)}
    surfaced = bool(
        result.get("errors") or result.get("warnings") or result.get("failure")
    )
    return {"raised": False, "surfaced": surfaced}


def _run() -> dict:
    outcomes: dict[str, dict] = {}

    from novel_agent.agents.writer import WriterAgent

    p = EvalProject()
    try:
        outcomes["summarize"] = _attempt(
            p, mock.patch.object(WriterAgent, "summarize",
                                 side_effect=RuntimeError("injected fault")))
    finally:
        p.cleanup()

    p = EvalProject()
    try:
        outcomes["backup"] = _attempt(
            p, mock.patch("novel_agent.core.backup.backup_project",
                          side_effect=RuntimeError("injected fault")))
    finally:
        p.cleanup()

    p = EvalProject()
    try:
        outcomes["track"] = _attempt(
            p, mock.patch.object(p.agent, "track_chapter",
                                 side_effect=RuntimeError("injected fault")))
    finally:
        p.cleanup()

    return outcomes


def run() -> list[dict]:
    s = _run()
    swallowed = [k for k, v in s.items() if not v["surfaced"]]
    detail = [s]
    return [{
        "gap": "silent_failures",
        "metric": "silent_swallow_rate",
        "direction": "min",
        "cases": len(s),
        "value": len(swallowed) / len(s) if s else 1.0,
        "target": 0.0,
        "detail": detail,
    }]
