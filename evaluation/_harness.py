"""M7 评测共享 harness：在真实 projects/ 下建临时项目跑真实 NovelAgent 流程。

沿用 tests/test_offline.py 的构造模式（test_offline 也在 PROJECTS_ROOT 下建
_test_mock 项目），但项目名带随机后缀、结束即清理，避免并发/残留冲突。
"""

from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from novel_agent import Config
from novel_agent.core import Project
from novel_agent.core.project import PROJECTS_ROOT

from .mock_backend import MockBackend

PINNED_WRITING = {
    "chapter_words": 2500,
    "recent_summary_count": 3,
    "recent_text_chars": 600,
    "max_retries": 2,
    "auto_review": False,
    "auto_track": True,
    "rag_top_k": 6,
    "rag_max_chars": 5000,
}


class EvalProject:
    """管理一个临时项目目录 + MockBackend + NovelAgent。"""

    def __init__(self, *, rag_max_chars: int = 5000) -> None:
        self.name = f"_eval_m7_{uuid.uuid4().hex[:8]}"
        self.dir = PROJECTS_ROOT / self.name
        self.backend = MockBackend()
        cfg = Config()
        cfg.raw["writing"] = {**PINNED_WRITING, "rag_max_chars": rag_max_chars}
        proj = Project(
            name=self.name,
            title="青云传",
            genre="玄幻",
            style="热血",
            logline="废柴少年偶得传承，踏上修仙路。",
            synopsis="孤儿林尘在青云村受尽欺凌，坠崖后获得上古传承，从此踏上修仙之路。",
            worldview="九州大陆，境界分炼气、筑基、金丹等。",
        )
        proj.save()
        from novel_agent.agents import NovelAgent

        self.agent = NovelAgent(proj, cfg, backend=self.backend)

    def init(self, chapter_count: int = 2) -> None:
        """跑一遍 主线/大纲/设定 + 丰富第一章计划（全部走 mock）。"""
        self.agent.init_from_synopsis(chapter_count=chapter_count, auto_bible=True)
        self.plan = self.agent.enrich_next_chapter_plan()

    def cleanup(self) -> None:
        if self.dir.exists():
            shutil.rmtree(self.dir)


def with_project(fn):
    """装饰器：确保 EvalProject 用完即清理。"""

    def wrapper(*args, **kwargs):
        p = EvalProject()
        try:
            return fn(p, *args, **kwargs)
        finally:
            p.cleanup()

    return wrapper
