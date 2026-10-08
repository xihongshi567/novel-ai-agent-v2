"""KnowledgeBase —— 统一知识库接口。

聚合一个项目的所有长期记忆：
  - bible       : 人物/地点/势力/物品设定集
  - continuity  : 连续性追踪表（时间线/伏笔/持有物/承诺/既定事实）
  - world       : 世界观（规则/历史/地理/文化/组织/术语）
  - ideas       : 灵感库
  - threads     : 故事线网络

所有数据【严格持久化为 JSON】，是长篇小说的「长期记忆与知识库」。
NovelAgent 通过本类统一访问；写作时通过 Memory 注入上下文。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .core import (
    Bible,
    Continuity,
    IdeaBank,
    Outline,
    Project,
    ThreadNetwork,
    World,
)
from .agents.kb_agent import KBAgent
from .llm import LLMBackend


class KnowledgeBase:
    """一个项目的全部知识聚合。"""

    def __init__(
        self,
        project_dir: Path,
        project_name: str,
        *,
        bible: Bible | None = None,
        continuity: Continuity | None = None,
        world: World | None = None,
        ideas: IdeaBank | None = None,
        threads: ThreadNetwork | None = None,
    ) -> None:
        self.dir = project_dir
        self.project_name = project_name
        self.bible = bible or Bible.load(project_dir, project_name)
        self.continuity = continuity or Continuity.load(project_dir, project_name)
        self.world = world or World.load(project_dir, project_name)
        self.ideas = ideas or IdeaBank.load(project_dir, project_name)
        self.threads = threads or ThreadNetwork.load(project_dir, project_name)

    @classmethod
    def load(cls, project: Project) -> "KnowledgeBase":
        return cls(project.dir, project.name)

    def save_all(self) -> None:
        """严格持久化全部知识库到磁盘（JSON）。"""
        self.bible.save(self.dir)
        self.continuity.save(self.dir)
        self.world.save(self.dir)
        self.ideas.save(self.dir)
        self.threads.save(self.dir)

    # ============ 健康诊断（doctor）============
    def doctor(self) -> dict[str, Any]:
        """轻量诊断:跨 5 个核心子表校验 id 唯一/必填字段/交叉一致性。

        返回：
          healthy: bool —— 没有任何 error 即 true
          issues: list[dict] —— 每条 {severity, module, path, message}
          summary: dict —— 各表条目数与关键计数
        """
        issues: list[dict[str, Any]] = []

        def _issue(severity: str, module: str, path: str, message: str) -> None:
            issues.append({
                "severity": severity, "module": module,
                "path": path, "message": message,
            })

        # ---- bible ----
        bible_counts = {"characters": 0, "locations": 0, "factions": 0,
                        "items": 0, "lore": 0}
        bible_seen: dict[str, list[str]] = {}  # id -> [kind,...]
        for kind, attr, count_key in (
            ("character", self.bible.characters, "characters"),
            ("location", self.bible.locations, "locations"),
            ("faction", self.bible.factions, "factions"),
            ("item", self.bible.items, "items"),
            ("lore", self.bible.lore, "lore"),
        ):
            for i, e in enumerate(attr):
                bible_counts[count_key] += 1
                p = f"{kind}s[{i}]"
                if not e.id:
                    _issue("error", "bible", f"{p}.id", f"{kind} 缺 id")
                else:
                    bible_seen.setdefault(e.id, []).append(kind)
                if not e.name:
                    _issue("error", "bible", f"{p}.name", f"{kind} 缺 name")
        for cid, kinds in bible_seen.items():
            if len(kinds) > 1:
                _issue("error", "bible", cid,
                       f"id 跨 kind 冲突:{'/'.join(sorted(set(kinds)))}")

        # ---- continuity ----
        cont_counts = {"timeline": len(self.continuity.timeline),
                       "foreshadows": len(self.continuity.foreshadows),
                       "open_foreshadows": 0,
                       "possessions": len(self.continuity.possessions),
                       "promises": len(self.continuity.promises),
                       "facts": len(self.continuity.facts)}
        cont_seen: set[str] = set()
        for i, f in enumerate(self.continuity.foreshadows):
            p = f"foreshadows[{i}]"
            if f.id in cont_seen:
                _issue("error", "continuity", f.id, "foreshadow id 重复")
            cont_seen.add(f.id)
            if not f.id:
                _issue("error", "continuity", p, "foreshadow 缺 id")
            if f.status == "planted" and not f.chapter_id:
                _issue("error", "continuity", p,
                       "planted 状态缺 chapter_id(无法定位回收章节)")
            if f.status == "planted":
                cont_counts["open_foreshadows"] += 1
        for i, e in enumerate(self.continuity.timeline):
            p = f"timeline[{i}]"
            if not e.chapter_id:
                _issue("error", "continuity", p, "timeline 事件缺 chapter_id")
            if not e.event:
                _issue("warning", "continuity", p, "timeline 事件描述为空")
        for i, fa in enumerate(self.continuity.facts):
            p = f"facts[{i}]"
            if not fa.content:
                _issue("warning", "continuity", p, "fact 内容为空")
        pos_seen: set[str] = set()
        for i, ps in enumerate(self.continuity.possessions):
            p = f"possessions[{i}]"
            if ps.id in pos_seen:
                _issue("error", "continuity", ps.id, "possession id 重复")
            pos_seen.add(ps.id)
            if not ps.id:
                _issue("error", "continuity", p, "possession 缺 id")
        pm_seen: set[str] = set()
        for i, pm in enumerate(self.continuity.promises):
            p = f"promises[{i}]"
            if pm.id in pm_seen:
                _issue("error", "continuity", pm.id, "promise id 重复")
            pm_seen.add(pm.id)
            if not pm.id:
                _issue("error", "continuity", p, "promise 缺 id")
        fact_seen: set[str] = set()
        for i, fa in enumerate(self.continuity.facts):
            p = f"facts[{i}]"
            if fa.id in fact_seen:
                _issue("error", "continuity", fa.id, "fact id 重复")
            fact_seen.add(fa.id)
            if not fa.id:
                _issue("error", "continuity", p, "fact 缺 id")

        # ---- world ----
        world_counts = {"elements": len(self.world.elements),
                        "with_constraints": 0}
        for i, el in enumerate(self.world.elements):
            p = f"elements[{i}]"
            if not el.name:
                _issue("error", "world", p, "world element 缺 name")
            if el.constraints:
                world_counts["with_constraints"] += 1

        # ---- ideas ----
        idea_counts = {"total": len(self.ideas.ideas),
                       "available": len(self.ideas.available()),
                       "used": 0, "dropped": 0}
        idea_seen: set[str] = set()
        for i, idea in enumerate(self.ideas.ideas):
            p = f"ideas[{i}]"
            if idea.id in idea_seen:
                _issue("error", "ideas", idea.id, "idea id 重复")
            idea_seen.add(idea.id)
            if not idea.id:
                _issue("error", "ideas", p, "idea 缺 id")
            if not idea.content:
                _issue("warning", "ideas", p, f"idea {idea.id} 内容为空")
            if idea.status == "used":
                idea_counts["used"] += 1
            elif idea.status == "dropped":
                idea_counts["dropped"] += 1

        # ---- threads ----
        thread_counts = {"total": len(self.threads.threads), "active": 0,
                         "open_nodes": 0}
        thread_seen: set[str] = set()
        for i, t in enumerate(self.threads.threads):
            p = f"threads[{i}]"
            if t.id in thread_seen:
                _issue("error", "threads", t.id, "thread id 重复")
            thread_seen.add(t.id)
            if not t.id:
                _issue("error", "threads", p, "thread 缺 id")
            if t.status == "active":
                thread_counts["active"] += 1
            for j, n in enumerate(t.nodes):
                np_ = f"{p}.nodes[{j}]"
                if not n.chapter_id:
                    _issue("warning", "threads", np_, "thread node 缺 chapter_id")
                if t.status == "active" and not n.closed:
                    thread_counts["open_nodes"] += 1

        errors = sum(1 for x in issues if x["severity"] == "error")
        return {
            "healthy": errors == 0,
            "errors": errors,
            "warnings": sum(1 for x in issues if x["severity"] == "warning"),
            "issues": issues,
            "summary": {
                "bible": bible_counts,
                "continuity": cont_counts,
                "world": world_counts,
                "ideas": idea_counts,
                "threads": thread_counts,
            },
        }

    # ============ 智能操作（需 LLM）============
    def with_agent(self, backend: LLMBackend) -> "_KBOps":
        """绑定一个 LLM 后端，返回可执行智能操作的对象。"""
        return _KBOps(self, KBAgent(backend))

    # ============ idea 管理 ============
    def add_idea(self, content: str, **kwargs: Any) -> Any:
        idea = self.ideas.add(content, **kwargs)
        self.save_all()
        return idea

    def query_ideas(self, **kwargs: Any) -> list[Any]:
        return self.ideas.query(**kwargs)

    def mark_idea_used(self, idea_id: str, chapter_id: str) -> bool:
        ok = self.ideas.mark_used(idea_id, chapter_id)
        if ok:
            self.save_all()
        return ok

    # ============ 世界观管理 ============
    def add_world_element(self, **kwargs: Any) -> Any:
        elem = self.world.add(**kwargs)
        self.save_all()
        return elem

    def world_constraints(self) -> list[str]:
        """所有硬性约束（写作强制注入）。"""
        return self.world.all_constraints()

    # ============ 故事线管理 ============
    def add_thread(self, **kwargs: Any) -> Any:
        t = self.threads.add_thread(**kwargs)
        self.save_all()
        return t

    def add_thread_node(self, thread_id: str, **kwargs: Any) -> Any:
        n = self.threads.add_node_to(thread_id, **kwargs)
        if n:
            self.save_all()
        return n

    # ============ 时间线 ============
    def timeline_events(self) -> list[Any]:
        return list(self.continuity.timeline)

    # ============ 统一渲染（给写作/查看用）============
    def render_full(self) -> str:
        """渲染整个知识库（人读）。"""
        parts = ["========== 知识库总览 =========="]
        if self.world.elements or self.world.premise:
            parts.append("\n--- 世界观 ---")
            parts.append(self.world.render_for_prompt() or "(空)")
        if self.bible.all_entries():
            parts.append("\n--- 设定集 ---")
            parts.append(self.bible.render_for_prompt())
        cont = self.continuity.render_for_prompt()
        if cont:
            parts.append("\n--- 连续性追踪 ---")
            parts.append(cont)
        if self.threads.threads:
            parts.append("\n--- 故事线 ---")
            parts.append(self.threads.render_for_prompt())
        if self.ideas.ideas:
            st = self.ideas.stats()
            parts.append(
                f"\n--- 灵感库（共{st['total']}：待用{st['pending']} 规划{st['planned']} "
                f"已用{st['used']} 放弃{st['dropped']}）---"
            )
            parts.append(self.ideas.render_for_prompt())
        return "\n".join(parts)

    def render_for_writing(
        self,
        *,
        chapter_chars: list[str] | None = None,
        chapter_keywords: str = "",
        include_ideas: bool = True,
    ) -> str:
        """渲染写作时要注入的知识库子集（精简，控制 token）。

        - 世界观：只注入硬性约束 + 与本章相关的元素
        - 设定集：与本章人物/地点相关的
        - 连续性：全部（伏笔/持有物/承诺/事实）
        - 故事线：未收束的
        - idea：与本章相关的高优先级
        """
        parts: list[str] = []

        # 世界观硬约束（始终注入，最关键）
        wc = self.world.render_for_prompt(with_constraints_only=True)
        if wc:
            parts.append(wc)

        # 故事线脉络
        tp = self.threads.render_for_prompt(only_active=True)
        if tp:
            parts.append(tp)

        # 相关 idea（按本章人物/关键词检索）
        if include_ideas and self.ideas.available():
            pool = self.ideas.available()
            if chapter_chars:
                pool = [
                    i
                    for i in pool
                    if any(
                        any(c in ch or ch in c for c in i.related_chars)
                        for ch in chapter_chars
                    )
                ] or pool
            if chapter_keywords:
                kw = chapter_keywords.lower()
                pool = [
                    i for i in pool if kw in i.content.lower() or kw in i.title.lower()
                ] or pool
            pool = sorted(pool, key=lambda i: -i.priority)[:5]  # 最多 5 个
            ip = self.ideas.render_for_prompt(pool)
            if ip:
                parts.append("【可用的灵感 idea（可酌情融入本章）】\n" + ip)

        return "\n\n".join(p for p in parts if p)


class _KBOps:
    """绑定 LLM 后的知识库智能操作（桥接 KBAgent + 数据落盘）。"""

    def __init__(self, kb: KnowledgeBase, agent: KBAgent) -> None:
        self.kb = kb
        self.agent = agent

    # ---- 世界观搭建（落盘到 world.json）----
    def build_world(self, project_meta: str, focus: str = "") -> dict[str, Any]:
        data = self.agent.build_world(project_meta, focus) or {}
        if data.get("premise"):
            self.kb.world.premise = data["premise"]
        added = 0
        for e in data.get("elements", []) or []:
            cat = e.get("category", "rule")
            try:
                self.kb.world.add(
                    category=cat,
                    name=e.get("name", ""),
                    summary=e.get("summary", ""),
                    detail=e.get("detail", ""),
                    constraints=e.get("constraints", []) or [],
                    parent=e.get("parent", ""),
                )
                added += 1
            except Exception:  # noqa: BLE001
                pass
        self.kb.save_all()
        return {"premise": data.get("premise", ""), "elements_added": added}

    # ---- 故事线串联（落盘到 threads.json）----
    def weave_threads(
        self,
        outline: Outline,
        summaries_text: str = "",
        target_chapters: int = 5,
    ) -> dict[str, Any]:
        data = (
            self.agent.weave_threads(
                outline.render_for_prompt(),
                summaries_text,
                self.kb.ideas.render_for_prompt(),
                self.kb.threads.render_for_prompt(),
                target_chapters,
            )
            or {}
        )
        added_threads = 0
        added_nodes = 0
        # 把规划写入 threads.json（合并：已有的线更新节点，新线新增）
        for td in data.get("threads", []) or []:
            name = td.get("name", "").strip()
            if not name:
                continue
            existing = next(
                (t for t in self.kb.threads.threads if t.name == name), None
            )
            if existing is None:
                existing = self.kb.threads.add_thread(
                    type=td.get("type", "subplot"),
                    name=name,
                    summary=td.get("summary", ""),
                    importance=td.get("importance", 3),
                )
                added_threads += 1
            else:
                if td.get("summary"):
                    existing.summary = td["summary"]
            for nd in td.get("nodes", []) or []:
                self.kb.threads.add_node_to(
                    existing.id,
                    chapter_id=nd.get("chapter_id", ""),
                    from_idea=nd.get("from_idea", ""),
                    title=nd.get("title", ""),
                    description=nd.get("description", ""),
                )
                added_nodes += 1
                # 如果节点来自 idea，标记 idea 为已规划
                if nd.get("from_idea") and nd.get("chapter_id"):
                    self.kb.ideas.mark_planned(nd["from_idea"], nd["chapter_id"])
        self.kb.save_all()
        return {
            "threads_added": added_threads,
            "nodes_added": added_nodes,
            "notes": data.get("weaving_notes", ""),
        }

    # ---- 时间线校核（只读分析，不落盘；返回冲突报告）----
    def audit_timeline(self) -> dict[str, Any]:
        tl = self.kb.continuity
        timeline_text = "\n".join(
            f"• {t.chapter_id} [{t.time_label}] {t.event}" for t in tl.timeline
        )
        facts_text = "\n".join(f"• [{f.category}] {f.content}" for f in tl.facts)
        if not timeline_text:
            return {"consistent": True, "conflicts": [], "overall": "暂无时间线事件"}
        return self.agent.audit_timeline(timeline_text, facts_text) or {
            "consistent": True,
            "conflicts": [],
            "overall": "校核未返回结果",
        }

    # ---- idea 安插建议（只读分析）----
    def place_ideas(self, outline: Outline) -> dict[str, Any]:
        available = self.kb.ideas.available()
        if not available:
            return {"placements": [], "unsuitable": [], "note": "没有可用的 idea"}
        return self.agent.place_ideas(
            self.kb.ideas.render_for_prompt(available),
            outline.render_for_prompt(),
        ) or {"placements": [], "unsuitable": []}
