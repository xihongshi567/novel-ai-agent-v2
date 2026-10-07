"""指标工具：离线评测通用的计算与结果构造。"""

from __future__ import annotations


def hit_rates(rows):
    n = len(rows) or 1
    return {f"top{k}": sum(bool(set(r["expected"]) & set(r["retrieved"][:k])) for r in rows) / n for k in (1, 3, 5)}


def rate(ok: int, total: int, default: float = 1.0) -> float:
    return ok / total if total else default


def result(*, gap: str, metric: str, value: float, target: float,
           cases: int, detail: list | None = None, note: str = "",
           direction: str = "max") -> dict:
    r = {"gap": gap, "metric": metric, "cases": cases, "value": value,
         "target": target, "direction": direction}
    r["status"] = ("pass" if value <= target else "fail") if direction == "min" \
        else ("pass" if value >= target else "fail")
    if detail is not None:
        r["detail"] = detail
    if note:
        r["note"] = note
    return r
