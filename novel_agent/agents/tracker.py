"""StateTracker —— 连续性追踪引擎。

每写完一章后调用 `track_chapter()`：
  1. 用 LLM 从正文提取状态变化/伏笔/持有物/承诺/既定事实
  2. 回写人物 status_history 到 bible
  3. 更新 continuity 表（含伏笔回收、持有物变更、承诺兑现的自动匹配）

这是防止长篇小说「写着写着就崩」的核心模块。
"""

from __future__ import annotations

from typing import Any

from ..core import Bible, Continuity, ForeshadowStatus
from ..llm import LLMBackend
from .llm_helpers import call_json_with_usage


class StateTracker:
    def __init__(self, backend: LLMBackend, *, log=None) -> None:
        self.backend = backend
        self._log = log

    def extract(
        self, chapter_id: str, content: str, known_characters: list[str]
    ) -> dict[str, Any] | None:
        """从一章正文提取所有状态/连续性变化。"""
        from ..prompts import TRACK_SYSTEM, extract_state_prompt

        turns = extract_state_prompt(chapter_id, content, known_characters)
        content_out, usage = call_json_with_usage(
            self.backend, TRACK_SYSTEM, turns, temperature=0.2, max_tokens=2000
        )
        if self._log:
            try:
                self._log(op="track", model="", usage=usage, chapter_id=chapter_id)
            except Exception:  # noqa: BLE001
                pass
        return content_out

    def apply_to_bible(
        self, bible: Bible, chapter_id: str, data: dict[str, Any]
    ) -> int:
        """把人物状态变化回写到 bible.characters[].status_history。返回更新条数。"""
        updated = 0
        for cs in data.get("character_status", []) or []:
            name = cs.get("name", "").strip()
            status = cs.get("status", "").strip()
            if not name or not status:
                continue
            target = bible.resolve_character(name)
            if target is None:
                continue
            # 避免重复记录同一章
            if (
                target.status_history
                and target.status_history[-1].get("chapter") == chapter_id
            ):
                target.status_history[-1]["text"] = status
            else:
                target.status_history.append({"chapter": chapter_id, "text": status})
            updated += 1
        return updated

    def apply_to_continuity(
        self, continuity: Continuity, chapter_id: str, data: dict[str, Any]
    ) -> dict[str, int]:
        """更新连续性表。返回各类新增/变更计数。"""
        counts = {
            "timeline": 0,
            "foreshadows": 0,
            "possessions": 0,
            "promises": 0,
            "facts": 0,
        }

        # 时间线
        for t in data.get("timeline", []) or []:
            event = t.get("event", "").strip()
            if not event:
                continue
            continuity.timeline.append(_mk_timeline(chapter_id, t))
            counts["timeline"] += 1

        # 伏笔：新埋 + 回收
        all_fs = continuity.foreshadows
        for f in data.get("foreshadows", []) or []:
            desc = f.get("description", "").strip()
            if not desc:
                continue
            fid = _next_id("fs", all_fs)
            all_fs.append(_mk_foreshadow(fid, chapter_id, desc))
            counts["foreshadows"] += 1
        # 回收：从已存在的未回收伏笔中选匹配度最高的一个（非先到先得）
        for fr in data.get("foreshadows_resolved", []) or []:
            desc = fr.get("description", "").strip()
            if not desc:
                continue
            candidates = [
                (f, score) for f in all_fs
                if f.status == ForeshadowStatus.planted
                and (score := _foreshadow_score(desc, f.description)) is not None
                and score >= 0.6
            ]
            if not candidates:
                continue
            best = max(candidates, key=lambda pair: pair[1])[0]
            best.status = ForeshadowStatus.resolved
            best.resolved_at = chapter_id
            counts["foreshadows"] += 1

        # 持有物
        for p in data.get("possessions", []) or []:
            owner = p.get("owner", "").strip()
            item = p.get("item", "").strip()
            if not owner or not item:
                continue
            acquired = p.get("acquired", True)
            if acquired:
                pid = _next_id("pos", continuity.possessions)
                continuity.possessions.append(
                    _mk_possession(pid, chapter_id, owner, item, p.get("detail", ""))
                )
                counts["possessions"] += 1
            else:
                # 失去：匹配同名持有物
                for existing in continuity.possessions:
                    if (
                        not existing.lost
                        and existing.owner in owner
                        and existing.item in item
                    ):
                        existing.lost = True
                        existing.lost_at = chapter_id
                        counts["possessions"] += 1
                        break

        # 承诺
        for pm in data.get("promises", []) or []:
            maker = pm.get("maker", "").strip()
            content = pm.get("content", "").strip()
            if not maker or not content:
                continue
            made = pm.get("made", True)
            if made:
                pmid = _next_id("pm", continuity.promises)
                continuity.promises.append(
                    _mk_promise(
                        pmid, chapter_id, maker, pm.get("receiver", ""), content
                    )
                )
                counts["promises"] += 1
            else:
                for existing in continuity.promises:
                    if (
                        not existing.fulfilled
                        and existing.maker in maker
                        and _similar(content, existing.content)
                    ):
                        existing.fulfilled = True
                        existing.fulfilled_at = chapter_id
                        counts["promises"] += 1
                        break

        # 既定事实
        for f in data.get("facts", []) or []:
            c = f.get("content", "").strip()
            if not c:
                continue
            # 去重：避免重复记录相同事实
            if any(_similar(c, x.content) for x in continuity.facts):
                continue
            fid = _next_id("fact", continuity.facts)
            continuity.facts.append(_mk_fact(fid, chapter_id, c, f.get("category", "")))
            counts["facts"] += 1

        return counts

    def track_chapter(
        self,
        chapter_id: str,
        content: str,
        bible: Bible,
        continuity: Continuity,
        known_characters: list[str] | None = None,
    ) -> dict[str, Any]:
        """一站式：提取 + 回写 bible + 更新 continuity。返回报告。"""
        if known_characters is None:
            known_characters = [c.name for c in bible.characters]
        data = self.extract(chapter_id, content, known_characters)
        if not data:
            return {"extracted": False}
        bible_updated = self.apply_to_bible(bible, chapter_id, data)
        cont_counts = self.apply_to_continuity(continuity, chapter_id, data)
        return {
            "extracted": True,
            "bible_characters_updated": bible_updated,
            "continuity": cont_counts,
            "raw": data,
        }


# ---- 工厂函数（避免直接 import 子类，减少耦合）----
def _mk_timeline(chapter_id: str, t: dict[str, Any]):
    from ..core import TimelineEvent

    return TimelineEvent(
        chapter_id=chapter_id,
        time_label=t.get("time_label", ""),
        event=t.get("event", ""),
    )


def _mk_foreshadow(fid: str, chapter_id: str, desc: str):
    from ..core import Foreshadow

    return Foreshadow(id=fid, chapter_id=chapter_id, description=desc)


def _mk_possession(pid: str, chapter_id: str, owner: str, item: str, detail: str):
    from ..core import Possession

    return Possession(
        id=pid, chapter_id=chapter_id, owner=owner, item=item, detail=detail
    )


def _mk_promise(pmid: str, chapter_id: str, maker: str, receiver: str, content: str):
    from ..core import Promise

    return Promise(
        id=pmid, chapter_id=chapter_id, maker=maker, receiver=receiver, content=content
    )


def _mk_fact(fid: str, chapter_id: str, content: str, category: str):
    from ..core import Fact

    return Fact(id=fid, chapter_id=chapter_id, content=content, category=category)


def _next_id(prefix: str, existing: list, width: int = 3) -> str:
    """生成与 existing 中 id 不冲突的新 id：保留 fs_001 格式向后兼容评测数据集，
    同时删除条目后再生成会找空位而不是复用旧 id（避免历史数据重导入时的引用错乱）。

    格式固定为 <prefix>_<3 位零填充序号>：fs_001, pos_001, pm_001, fact_001。
    """
    taken = {getattr(x, "id", "") for x in existing}
    n = 1
    while True:
        cand = f"{prefix}_{n:0{width}d}"
        if cand not in taken:
            return cand
        n += 1


# ---- 伏笔回收匹配（与 _similar 独立，只用于 foreshadows_resolved）----
_FS_STOP = frozenset("的得了在把被从将着与于为和一枚中会向往进手里外个是有这那之也都")


def _fs_core(s: str) -> str:
    return "".join(ch for ch in s if ch not in _FS_STOP)


def _lcs_len(a: str, b: str) -> int:
    """最长公共子序列长度（保序）。事件要素顺序一致才构成同一事件。"""
    n, m = len(a), len(b)
    if not n or not m:
        return 0
    prev = [0] * (m + 1)
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        for j in range(1, m + 1):
            cur[j] = prev[j - 1] + 1 if a[i - 1] == b[j - 1] else max(prev[j], cur[j - 1])
        prev = cur
    return prev[m]


def _foreshadow_score(a: str, b: str) -> float | None:
    """伏笔回收匹配度，不达标返回 None。

    组合评分：0.5*保序重叠（LCS 比例）+ 0.5*非保序重叠（bigram 比例）
    + 主语前缀对齐加分（0.2）。换词表述靠非保序部分召回（夺回 vs 抢走），
    要素顺序颠倒的相似句靠保序部分降权（对付 vs 对峙）。长度比约束：
    回收句核心长度 >= 伏笔句核心的 75%，挡"上古玉简被毁坏"类简略句。
    """
    ac, bc = _fs_core(a), _fs_core(b)
    if not ac or not bc or len(bc) / len(ac) < 0.75:
        return None
    a_set = {ac[i : i + 2] for i in range(len(ac) - 1)}
    b_set = {bc[i : i + 2] for i in range(len(bc) - 1)}
    if not a_set or not b_set:
        return None
    overlap = len(a_set & b_set) / max(len(a_set), len(b_set))
    seq = _lcs_len(ac, bc) / max(len(ac), len(bc))
    score = 0.5 * seq + 0.5 * overlap
    bonus = 0.2 if ac[:2] == bc[:2] else 0.0
    return score + bonus


def _similar(a: str, b: str) -> bool:
    """宽松的中文相似度：共享的关键词多就算相似。"""
    if not a or not b:
        return False
    # 取 2 字以上的共有子串作为简单衡量
    a_set = {a[i : i + 2] for i in range(len(a) - 1)}
    b_set = {b[i : i + 2] for i in range(len(b) - 1)}
    if not a_set or not b_set:
        return False
    overlap = len(a_set & b_set) / max(len(a_set), len(b_set))
    return overlap >= 0.4
