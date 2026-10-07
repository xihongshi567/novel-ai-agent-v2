"""M7 gap checks：9 个缺口的离线度量。每个模块 run() 返回 result dict 列表。

result dict 统一 schema：
  {gap, metric, cases, value, target, status, detail}
"""

from . import name_matching
from . import foreshadow_recovery
from . import summary_fidelity
from . import rag_truncation
from . import setting_filter
from . import review_selfcheck
from . import silent_failures
from . import chunk_boundary

MODULES = [
    name_matching,
    foreshadow_recovery,
    summary_fidelity,
    rag_truncation,
    setting_filter,
    review_selfcheck,
    silent_failures,
    chunk_boundary,
]

GAP_NAMES = ["name_matching", "foreshadow_recovery", "summary_fidelity",
             "rag_truncation", "setting_filter", "review_selfcheck",
             "silent_failures", "chunk_boundary"]


def _status(r: dict) -> str:
    direction = r.get("direction", "max")
    if direction == "min":
        return "pass" if r["value"] <= r["target"] else "fail"
    return "pass" if r["value"] >= r["target"] else "fail"


def run_all() -> list[dict]:
    results: list[dict] = []
    for m in MODULES:
        for r in m.run():
            r.setdefault("direction", "max")
            r["status"] = _status(r)
            results.append(r)
    return results
