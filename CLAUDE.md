# novel-ai-agent-v2 模块契约

长篇小说 AI 写作 agent。修复工作按 7 模块框架归位执行（详见用户 memory 的
project-module-framework）。本文件是模块归属与依赖方向的**硬约束**，
与 `tests/test_module_boundaries.py` 对应，边界测试强制依赖方向。

## 运行命令

- 本机 `python` 是 Windows Store 占位符，**必须用 `py`**
- M7 评测：`py evaluation/run_evaluation.py`（输出 `evaluation/results.json`）
- 全量测试：`py -m unittest discover tests`
- 边界测试：`py -m unittest tests.test_module_boundaries`

## 7 模块归属（文件清单）

| 模块 | 职责 | 文件 |
|---|---|---|
| M1 记忆管理 | 知识库建模/写入/更新 | `core/bible.py` `core/continuity.py` `core/world.py` `core/ideas.py` `core/threads.py` `core/manifesto.py` `core/links.py` `core/constraints.py` `core/conflicts.py` `agents/tracker.py`（写入侧）`agents/kb_agent.py` `kb.py` |
| M2 上下文管理 | 挑选/组装/注入/预算/召回 | `core/memory.py` `core/idea_retrieval.py` `core/search.py`（召回侧）`core/outline.py` |
| M3 生成与幻觉防控 | 写作/审校/修订/质量 | `agents/writer.py` `agents/reviewer.py` `agents/rewrite_agent.py` `agents/style_agent.py` `agents/pacing_agent.py` `agents/planner.py` `core/pacing.py` `core/style.py` `prompts/` |
| M4 数据流转与持久化 | 落盘/一致性/备份/溯源 | `core/project.py` `core/chapter.py` `core/backup.py` `core/progress.py` `core/usage.py` `core/chapter_fit.py` |
| M5 编排与错误处理 | 流程/状态机/失败策略 | `agents/novel.py` |
| M6 外部通信 | LLM 后端/三入口/成本 | `cli.py` `webui.py` `feishu_bot.py` `novel_agent/feishu/` `novel_agent/llm/` `agents/llm_helpers.py` `config.py` |
| M7 评测与可观测性 | 指标/回归/验证 | `evaluation/` `tests/` |

## 依赖方向（`tests/test_module_boundaries.py` 强制执行）

- `core/` 不依赖 agents/prompts/feishu/kb/config（可依赖 `llm.embedding` 与同级）
- `llm/` 不依赖 core/agents/prompts/feishu/kb（可依赖 config）
- `prompts/` 不依赖 novel_agent 任何其他模块（只允许同级）
- `agents/` 除 `novel.py`（M5 编排者）与 `__init__.py` 外，只允许 import 同级 `llm_helpers`，
  不允许 agent 间直接互相依赖
- 任何 novel_agent 模块不依赖 evaluation/tests/cli/webui/feishu_bot

## 修复流程约束

1. **先归位**：动手前说明改动属于哪个模块、触及哪些文件（对照归属表）
2. **只碰本模块文件**；确需跨模块改动时，commit message 标注 `[CROSS-MODULE]` 并写明理由
   （跨模块根因传导是合法场景：summary_fidelity 横跨 M5/M3、review_selfcheck 横跨 M3/M5）
3. **验收 = 全量回归**：`py evaluation/run_evaluation.py`（本模块指标 pass + 其他模块无回归）
   + `py -m unittest discover tests` 全绿（含边界测试）
4. **每模块一个本地 git commit**，commit message 说明修复了哪个缺口、指标变化
