"""AI 行为准则可执行检查：错误处理红线（禁止新增裸 except: pass 吞错）。

基线 = 修复前实测的裸吞错数（AST 扫描 24 处：novel.py 11 处 + 各 agent 的
log 防御 + core 3 处），断言不增长；各模块修复时逐步清理，数量只会下降。
显式降级（except 内有 return/赋值/raise）是合法模式，不计入。

运行：py -m unittest tests.test_code_quality 或 py -m unittest discover tests
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PKG = ROOT / "novel_agent"

SWALLOW_BASELINE = 24


def _find_swallows(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        meaningful = [s for s in node.body if not isinstance(s, ast.Pass)]
        if any(isinstance(s, ast.Pass) for s in node.body) and not meaningful:
            found.append(f"{path.name}:{node.lineno}")
    return found


class CodeQualityTests(unittest.TestCase):
    def test_no_new_bare_except_swallow(self):
        swallows: list[str] = []
        for py in sorted(PKG.rglob("*.py")):
            if "__pycache__" in str(py):
                continue
            swallows.extend(_find_swallows(py))
        self.assertLessEqual(
            len(swallows), SWALLOW_BASELINE,
            f"裸 except 吞错超过基线 {SWALLOW_BASELINE}（禁止新增，应显式降级）:\n"
            + "\n".join(swallows))


if __name__ == "__main__":
    unittest.main()
