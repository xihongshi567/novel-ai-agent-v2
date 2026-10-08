"""M5 修复回归：digest_plot / enrich / audit_project 返回契约。

M5 之前三个 LLM 编排方法的 LLM 解析失败 fallback 路径返回裸
{"parsed": False}，调用方无法判断"为什么没解析成功"。本 commit 把
成功/失败两条路径都补成顶层 warnings 字段，让 UI/CLI 能一致地展示
降级原因。

运行：py -m unittest tests.test_result_contract 或 py -m unittest discover tests
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation._harness import EvalProject  # noqa: E402


def _patch_llm_parse_fail():
    """patch call_json_with_usage 返回 (None, {}) 触发 JSON 解析失败路径。"""
    return mock.patch(
        "novel_agent.agents.llm_helpers.call_json_with_usage",
        return_value=(None, {}),
    )


class ResultContractTests(unittest.TestCase):
    def setUp(self):
        self.p = EvalProject()
        self.p.init(chapter_count=1)

    def tearDown(self):
        self.p.cleanup()

    def test_digest_plot_llm_fail_has_warnings(self):
        with _patch_llm_parse_fail():
            r = self.p.agent.digest_plot("主角在悬崖下醒来获得传承")
        self.assertIn("warnings", r, f"digest_plot fallback 缺 warnings: {r}")
        self.assertIsInstance(r["warnings"], list)
        self.assertGreater(len(r["warnings"]), 0)

    def test_digest_plot_success_has_empty_warnings(self):
        # MockBackend 默认能 parse,这里走成功路径
        r = self.p.agent.digest_plot("主角在悬崖下醒来获得传承")
        self.assertIn("warnings", r, f"digest_plot 成功路径缺 warnings: {r}")
        self.assertIsInstance(r["warnings"], list)

    def test_enrich_llm_fail_has_warnings(self):
        with _patch_llm_parse_fail():
            r = self.p.agent.enrich("characters:林尘", instruction="")
        self.assertIn("warnings", r, f"enrich fallback 缺 warnings: {r}")
        self.assertIsInstance(r["warnings"], list)
        self.assertGreater(len(r["warnings"]), 0)

    def test_enrich_success_has_empty_warnings(self):
        r = self.p.agent.enrich("characters:林尘", instruction="")
        self.assertIn("warnings", r, f"enrich 成功路径缺 warnings: {r}")
        self.assertIsInstance(r["warnings"], list)

    def test_audit_project_llm_fail_has_warnings(self):
        with _patch_llm_parse_fail():
            r = self.p.agent.audit_project()
        self.assertIn("warnings", r, f"audit_project fallback 缺 warnings: {r}")
        self.assertIsInstance(r["warnings"], list)
        self.assertGreater(len(r["warnings"]), 0)

    def test_audit_project_success_has_warnings(self):
        r = self.p.agent.audit_project()
        self.assertIn("warnings", r, f"audit_project 成功路径缺 warnings: {r}")
        self.assertIsInstance(r["warnings"], list)


if __name__ == "__main__":
    unittest.main()
