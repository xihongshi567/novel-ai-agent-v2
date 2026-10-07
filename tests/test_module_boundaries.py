"""模块边界约束：AST 扫描 novel_agent/ 的 import 依赖方向，防止修复越界破坏结构。

规则（与根目录 CLAUDE.md 模块契约一致）：
  R1 core/    不依赖 agents/prompts/feishu/kb/config（可依赖 llm.embedding 与同级）
  R2 llm/     不依赖 core/agents/prompts/feishu/kb（可依赖 config）
  R3 prompts/ 不依赖 novel_agent 任何其他模块（只允许同级）
  R4 agents/  除 novel.py（M5 编排者）与 __init__.py 外，只允许 import 同级 llm_helpers
  R5 任何 novel_agent/* 不依赖 evaluation/tests/cli/webui/feishu_bot（外部入口/评测）

运行：py -m unittest tests.test_module_boundaries 或 py -m unittest discover tests
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PKG = ROOT / "novel_agent"

TOP_LEVEL_ENTRIES = {"cli", "webui", "feishu_bot", "evaluation", "tests"}

FORBIDDEN = {
    "novel_agent.core": {
        "novel_agent.agents", "novel_agent.prompts", "novel_agent.feishu",
        "novel_agent.kb", "novel_agent.config",
    },
    "novel_agent.llm": {
        "novel_agent.core", "novel_agent.agents", "novel_agent.prompts",
        "novel_agent.feishu", "novel_agent.kb",
    },
    "novel_agent.prompts": {
        "novel_agent.core", "novel_agent.agents", "novel_agent.llm",
        "novel_agent.feishu", "novel_agent.kb", "novel_agent.config",
    },
}

ORCHESTRATOR = {"novel.py", "__init__.py", "llm_helpers.py"}


def _source_pkg(path: Path) -> str:
    parts = list(path.relative_to(PKG).parts)
    if len(parts) == 1:
        return "novel_agent.root"
    return "novel_agent." + parts[0]


def _resolve(level: int, module: str | None, path: Path) -> str:
    if level == 0:
        return module or ""
    pkg = list(path.relative_to(PKG).parts[:-1])
    for _ in range(max(0, level - 1)):
        if pkg:
            pkg.pop()
    parts = ["novel_agent", *pkg]
    if module:
        parts += module.split(".")
    return ".".join(parts)


def _target_pkg(full: str) -> str:
    parts = full.split(".")
    if parts[0] != "novel_agent":
        return parts[0]
    if len(parts) == 1:
        return "novel_agent.root"
    return ".".join(parts[:2])


def _violations(path: Path) -> list[str]:
    src = _source_pkg(path)
    violations: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                top = name.name.split(".")[0]
                if top in TOP_LEVEL_ENTRIES:
                    violations.append(
                        f"{path.name}:{node.lineno} import {name.name}（入口/评测反向依赖）")
                full = _resolve(0, name.name, path)
                pkg = _target_pkg(full)
                if src in FORBIDDEN and pkg in FORBIDDEN[src]:
                    violations.append(
                        f"{path.name}:{node.lineno} import {name.name}（{src} 禁依赖 {pkg}）")
        elif isinstance(node, ast.ImportFrom):
            full = _resolve(node.level, node.module, path)
            pkg = _target_pkg(full)
            if pkg in TOP_LEVEL_ENTRIES or pkg in {"novel_agent.evaluation", "novel_agent.tests"}:
                violations.append(
                    f"{path.name}:{node.lineno} from {node.module}（入口/评测反向依赖）")
            if src in FORBIDDEN and pkg in FORBIDDEN[src]:
                violations.append(
                    f"{path.name}:{node.lineno} from {node.module}（{src} 禁依赖 {pkg}）")
            if src == "novel_agent.agents" and path.name not in ORCHESTRATOR:
                if full.startswith("novel_agent.agents.") and not full.endswith("llm_helpers"):
                    violations.append(
                        f"{path.name}:{node.lineno} from {node.module}（agents 间直接依赖）")
    return violations


class ModuleBoundaryTests(unittest.TestCase):
    def test_dependency_directions(self):
        problems: list[str] = []
        for py in sorted(PKG.rglob("*.py")):
            if "__pycache__" in str(py):
                continue
            try:
                problems.extend(_violations(py))
            except Exception as e:  # noqa: BLE001
                problems.append(f"{py.name}: 解析失败 {e}")
        self.assertEqual([], problems, "模块边界违规:\n" + "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
