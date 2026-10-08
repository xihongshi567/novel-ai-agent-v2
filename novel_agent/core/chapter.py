"""章节正文与存储。

每章存成 chapters/<chapter_id>.md（正文）+ chapters/summaries.json（摘要表）。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ._atomic import atomic_write_json, atomic_write_text

from .outline import ChapterPlan


class Chapter(BaseModel):
    chapter_id: str
    title: str = ""
    content: str = ""
    word_count: int = 0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    review_note: str = ""  # 审校意见

    @property
    def filename(self) -> str:
        return f"{self.chapter_id}.md"

    def render_markdown(self) -> str:
        head = f"# {self.title}\n\n" if self.title else ""
        return f"{head}{self.content}\n"


class ChapterSummary(BaseModel):
    chapter_id: str
    title: str = ""
    summary: str = ""  # 这一章发生了什么（供后续章节参考）
    word_count: int = 0


class ChapterStore(BaseModel):
    """所有章节摘要的索引表。"""

    summaries: dict[str, ChapterSummary] = Field(default_factory=dict)
    # 审校意见（独立于 summary，避免污染前情提要；M5 修复对称操作）
    review_notes: dict[str, str] = Field(default_factory=dict)
    # 单章节最多保留的历史版本数；超过则归档时删最旧。防止长篇项目
    # versions 目录无限膨胀拖累 load()。
    max_versions_per_chapter: int = 20

    # ---- 路径 ----
    @staticmethod
    def chapters_dir(project_dir: Path) -> Path:
        return project_dir / "chapters"

    @staticmethod
    def summaries_path(project_dir: Path) -> Path:
        return ChapterStore.chapters_dir(project_dir) / "summaries.json"

    @staticmethod
    def chapter_path(project_dir: Path, chapter_id: str) -> Path:
        return ChapterStore.chapters_dir(project_dir) / f"{chapter_id}.md"

    # ---- 加载/保存 ----
    @classmethod
    def load(cls, project_dir: Path) -> "ChapterStore":
        p = cls.summaries_path(project_dir)
        if not p.exists():
            return cls()
        with open(p, "r", encoding="utf-8") as f:
            data = __import__("json").load(f)
        # data: dict[str, dict]
        return cls(
            summaries={
                k: ChapterSummary(**v) for k, v in data.get("summaries", {}).items()
            },
            review_notes=dict(data.get("review_notes", {})),
        )

    def save(self, project_dir: Path) -> None:
        self.chapters_dir(project_dir).mkdir(parents=True, exist_ok=True)
        data = {
            "summaries": {k: v.model_dump() for k, v in self.summaries.items()},
            "review_notes": dict(self.review_notes),
        }
        atomic_write_json(self.summaries_path(project_dir), data, ensure_ascii=False, indent=2)

    # ---- 操作 ----
    def write_chapter(
        self,
        project_dir: Path,
        plan: ChapterPlan,
        content: str,
        summary: str = "",
        *,
        source: str = "ai",
        review_note: str | None = None,
    ) -> Chapter:
        """写入章节正文。

        若该章已存在，会自动把旧版归档到 versions/<cid>.v{n}.md。
        source: 'ai' | 'human' | 'revise'，记录版本来源。
        review_note: 非 None 时写入 ChapterStore.review_notes（与 summary 分开存储，
        避免审校意见污染前情提要；M5 对称操作）。
        """
        self.chapters_dir(project_dir).mkdir(parents=True, exist_ok=True)
        cid = plan.chapter_id
        # 归档旧版（若存在）；记录本次归档的 v 编号以保证元信息与磁盘一致
        cur_path = self.chapter_path(project_dir, cid)
        v_num = 0
        if cur_path.exists():
            v_num = self._archive_version(
                project_dir, cid, cur_path.read_text(encoding="utf-8")
            )
        wc = len([c for c in content if c.strip()])
        ch = Chapter(
            chapter_id=cid,
            title=plan.title,
            content=content,
            word_count=wc,
        )
        atomic_write_text(cur_path, ch.render_markdown())
        # 头尾采样兜底：n 随长度收缩，避免短章节头尾重叠
        n = min(100, max(1, len(content) // 3))
        fallback_summary = content[:n] + content[-n:]
        self.summaries[cid] = ChapterSummary(
            chapter_id=cid,
            title=plan.title,
            summary=summary or fallback_summary,
            word_count=wc,
        )
        if review_note is not None:
            self.review_notes[cid] = review_note
        self.save(project_dir)
        self._log_version_meta(project_dir, cid, wc, source, v_num)
        # 归档 + 元信息追加后裁剪：先看是否超 max_versions_per_chapter
        self._prune_old_versions(project_dir, cid)
        return ch

    # ============ 多版本管理 ============
    @staticmethod
    def versions_dir(project_dir: Path) -> Path:
        return ChapterStore.chapters_dir(project_dir) / "versions"

    @staticmethod
    def versions_meta_path(project_dir: Path) -> Path:
        return ChapterStore.versions_dir(project_dir) / "versions.json"

    def _archive_version(self, project_dir: Path, cid: str, text: str) -> int:
        """把旧内容归档为 v{n}.md，返回本次归档的 v 文件编号。版本裁剪由
        write_chapter 末尾统一调用 _prune_old_versions 触发，避免在归档
        与元信息追加之间出现时序竞态。

        n 取元信息中所有 version 字段的最大值 + 1（不是 len+1），保证
        即便有占位 v_num=0 也不会推高编号。
        """
        vdir = self.versions_dir(project_dir)
        vdir.mkdir(parents=True, exist_ok=True)
        existing = self.list_versions(project_dir, cid)
        max_n = max((v["version"] for v in existing if isinstance(v.get("version"), int)), default=0)
        n = max_n + 1
        atomic_write_text(vdir / f"{cid}.v{n}.md", text)
        return n

    def _prune_old_versions(self, project_dir: Path, cid: str) -> None:
        """单章版本数超过 max_versions_per_chapter 时，删除最旧的版本文件 + 元信息条目。"""
        cap = self.max_versions_per_chapter
        if cap <= 0:
            return  # cap<=0 表示不限
        versions = self.list_versions(project_dir, cid)
        if len(versions) <= cap:
            return
        excess = len(versions) - cap
        vdir = self.versions_dir(project_dir)
        for entry in versions[:excess]:
            v_file = vdir / f"{cid}.v{entry['version']}.md"
            if v_file.exists():
                v_file.unlink()
        # 从 versions.json 同步裁剪（重写元信息）
        import json
        meta_path = self.versions_meta_path(project_dir)
        if not meta_path.exists():
            return
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        cid_versions = meta.get("versions", {}).get(cid, [])
        meta["versions"][cid] = cid_versions[excess:]
        atomic_write_json(meta_path, meta, ensure_ascii=False, indent=2)

    def _log_version_meta(
        self, project_dir: Path, cid: str, word_count: int, source: str,
        v_num: int,
    ) -> None:
        """记录版本元信息。v_num 是本次归档写入的 v 文件编号（与磁盘一致）。"""
        import json
        import time as _t

        vdir = self.versions_dir(project_dir)
        vdir.mkdir(parents=True, exist_ok=True)
        meta_path = self.versions_meta_path(project_dir)
        meta: dict[str, Any] = {"versions": {}}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        versions = meta.setdefault("versions", {}).setdefault(cid, [])
        versions.append(
            {
                "version": v_num,
                "ts": _t.time(),
                "word_count": word_count,
                "source": source,
                "is_current": False,
            }
        )
        atomic_write_json(meta_path, meta, ensure_ascii=False, indent=2)

    def list_versions(self, project_dir: Path, cid: str) -> list[dict]:
        """返回某章的版本历史（不含当前版）。"""
        import json

        meta_path = self.versions_meta_path(project_dir)
        if not meta_path.exists():
            return []
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return meta.get("versions", {}).get(cid, [])

    def get_version(self, project_dir: Path, cid: str, version: int) -> Chapter | None:
        """读取某历史版本。version=0 表示当前版。"""
        if version == 0:
            return self.read_chapter(project_dir, cid)
        p = self.versions_dir(project_dir) / f"{cid}.v{version}.md"
        if not p.exists():
            return None
        text = p.read_text(encoding="utf-8")
        lines = text.split("\n")
        title = ""
        content = text
        if lines and lines[0].startswith("# "):
            title = lines[0][2:].strip()
            content = "\n".join(lines[1:]).lstrip("\n")
        return Chapter(
            chapter_id=cid,
            title=title,
            content=content,
            word_count=len([c for c in content if c.strip()]),
        )

    def rollback(self, project_dir: Path, cid: str, version: int) -> Chapter | None:
        """回滚到某历史版本：把当前版也归档，再用历史版覆盖当前。"""
        target = self.get_version(project_dir, cid, version)
        if target is None:
            return None
        # 当前版归档（作为新版本）
        cur_path = self.chapter_path(project_dir, cid)
        v_num = 0
        if cur_path.exists():
            v_num = self._archive_version(
                project_dir, cid, cur_path.read_text(encoding="utf-8")
            )
        atomic_write_text(cur_path, target.render_markdown())
        self._log_version_meta(project_dir, cid, target.word_count, "rollback", v_num)
        if cid in self.summaries:
            self.summaries[cid].word_count = target.word_count
            self.save(project_dir)
        # rollback 后裁剪
        self._prune_old_versions(project_dir, cid)
        return target

    def diff(
        self, project_dir: Path, cid: str, v1: int = 0, v2: int = 1
    ) -> dict[str, list[str]]:
        """简单行级 diff（v1 vs v2，0=当前）。返回 {'added':[], 'removed':[]}。"""
        import difflib

        c1 = self.get_version(project_dir, cid, v1)
        c2 = self.get_version(project_dir, cid, v2)
        if c1 is None or c2 is None:
            return {"added": [], "removed": []}
        lines1 = c1.content.splitlines()
        lines2 = c2.content.splitlines()
        sm = difflib.SequenceMatcher(None, lines2, lines1)
        added: list[str] = []
        removed: list[str] = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("insert", "replace"):
                added.extend(lines1[j1:j2])
            if tag in ("delete", "replace"):
                removed.extend(lines2[i1:i2])
        return {"added": added, "removed": removed}

    def read_chapter(self, project_dir: Path, chapter_id: str) -> Chapter | None:
        p = self.chapter_path(project_dir, chapter_id)
        if not p.exists():
            return None
        text = p.read_text(encoding="utf-8")
        # 去掉 markdown 标题行
        lines = text.split("\n")
        title = ""
        content = text
        if lines and lines[0].startswith("# "):
            title = lines[0][2:].strip()
            content = "\n".join(lines[1:]).lstrip("\n")
        s = self.summaries.get(chapter_id)
        return Chapter(
            chapter_id=chapter_id,
            title=title,
            content=content,
            word_count=s.word_count if s else len(content),
            review_note=self.review_notes.get(chapter_id, ""),
        )

    def tail(self, project_dir: Path, chapter_id: str, chars: int) -> str:
        """取某章末尾 chars 个字符，作为"上一章结尾"上下文。"""
        ch = self.read_chapter(project_dir, chapter_id)
        if not ch or not ch.content:
            return ""
        return ch.content[-chars:] if len(ch.content) > chars else ch.content

    def has(self, chapter_id: str) -> bool:
        return chapter_id in self.summaries

    def ordered_ids(self) -> list[str]:
        return sorted(self.summaries.keys())
