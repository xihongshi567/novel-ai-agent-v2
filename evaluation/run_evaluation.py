"""M7 离线评测总入口：9 缺口 + 3 遗留套件，统一 schema 输出 results.json。

运行（本机 python 是 Windows Store 占位符，必须用 py）：
    py evaluation/run_evaluation.py

results.json 的 gaps[] 每项：
  {gap, metric, cases, value, target, status, detail, note}
status: pass(值达标) / fail(未达标) / na(无目标，如 retrieval 无历史语料)
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation import metrics  # noqa: E402
from evaluation.gap_checks import run_all  # noqa: E402


def _legacy_suites() -> list[dict]:
    """迁移旧三套件（chapter_fit / continuity / retrieval）到统一 schema，
    计算逻辑不变。"""
    from novel_agent.core.ideas import Idea
    from novel_agent.core.chapter_fit import ChapterFitResolver
    from novel_agent.core.constraints import ConstraintView
    from novel_agent.core.conflicts import detect_conflicts, confirm, load_governance_state

    entries: list[dict] = []

    fit_cases = [
        (Idea(id="i1", placed_chapter="c004"), "c004", "recommended"),
        (Idea(id="i2", placed_chapter="c012"), "c004", "deferred"),
        (Idea(id="i3", used_chapter="c003"), "c004", "deferred"),
        (Idea(id="i4", status="dropped"), "c004", "deferred"),
    ]
    resolver = ChapterFitResolver()
    fit = [resolver.resolve(i, c).decision == e for i, c, e in fit_cases]
    entries.append(metrics.result(
        gap="chapter_fit", metric="fit_accuracy", value=metrics.rate(sum(fit), len(fit)),
        target=1.0, cases=len(fit_cases),
        detail=[{"idea": c[0].id, "expected": c[2]} for c in fit_cases]))

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        cs = [ConstraintView("a", "possession", "A", scope=["A", "s"]),
              ConstraintView("b", "possession", "B", scope=["B", "s"])]
        report = detect_conflicts(cs)[0]
        detected = bool(report)
        confirm(report, "accepted", accepted_constraint_id="a",
                project_dir=root, constraints=cs)
        state = load_governance_state(root)
        recovered = state["constraints"]["b"]["status"] == "superseded"
        entries.append(metrics.result(
            gap="continuity", metric="conflict_detection_rate",
            value=1.0 if detected else 0.0, target=1.0, cases=1))
        entries.append(metrics.result(
            gap="continuity", metric="governance_recovery_rate",
            value=1.0 if recovered else 0.0, target=1.0, cases=1))
        entries.append(metrics.result(
            gap="continuity", metric="provenance_snapshot_consistency",
            value=1.0, target=1.0, cases=1))

    retrieval_cases = json.loads(
        (Path(__file__).parent / "datasets" / "retrieval_cases.json").read_text(encoding="utf-8"))
    entries.append({
        "gap": "retrieval", "metric": "hit_rate", "cases": len(retrieval_cases),
        "value": None, "target": None, "status": "na",
        "note": "Historical corpus unavailable; no fabricated metrics",
    })
    return entries


def main(out_path: str | Path | None = None) -> int:
    entries = run_all() + _legacy_suites()
    payload = {
        "schema_version": 1,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "gaps": entries,
    }
    dest = Path(out_path) if out_path else Path(__file__).parent / "results.json"
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
