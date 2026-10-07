"""缺口6 审校自举盲区：审校返回无效内容时被当作"干净通过"。

走真实代码路径：
  - reviewer.py:74  _run_json → extract_json_block 失败返 None（llm_helpers.py:55）
  - novel.py:505  review_chapter `result = self.reviewer.review(...) or {}`
    → 无效审校被静默当成空结果，章节仍标记 reviewed（无 issues 无偏离）

度量 review_invalid_surface：无效审校是否被表面化（重试/抛错/标记 invalid），
当前静默通过 → 0。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from .._harness import EvalProject


def _run() -> dict:
    p = EvalProject()
    try:
        p.backend.invalid_review = True
        p.init(chapter_count=2)
        cid = p.plan.chapter_id
        p.agent.write_chapter(cid, review=False)

        try:
            result = p.agent.review_chapter(cid)
            raised = False
        except Exception as e:  # noqa: BLE001
            raised = True
            result = {"exception": str(e)}

        review = result.get("review") or {}
        surfaced = (
            raised
            or bool(review.get("invalid"))
            or bool(review.get("parse_failed"))
            or "errors" in result
            or "warnings" in result
        )
        plan = p.agent.outline.find(cid)
        return {
            "invalid_review_returned_none": review == {},
            "surfaced": bool(surfaced),
            "plan_status": plan.status.value if plan else None,
            "review_result_keys": list(review.keys()),
        }
    finally:
        p.cleanup()


def run() -> list[dict]:
    s = _run()
    detail = [s]
    return [{
        "gap": "review_selfcheck",
        "metric": "review_invalid_surface",
        "cases": 1,
        "value": 1.0 if s["surfaced"] else 0.0,
        "target": 1.0,
        "detail": detail,
    }]
