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

## AI 行为准则（代码质量 + 最小改动）

### 最小改动原则（不做多余的事）

- 只改任务要求的文件；重构/重命名/格式化/顺手修复等超范围改动，必须先说明并等确认
- 不新建文件（含测试/文档），除非任务明确要求
- 不引入新依赖（pip 包）；确需引入必须显式说明理由
- 不添加无调用方的函数/类/参数/import（死代码禁令）；确定无用即删除，不留注释掉的代码
- 不做假设性抽象：三行相似代码好过一个过早的抽象；不为未来需求设计

### 代码质量标准

- 风格跟随现状：pydantic/dataclass 模型、类型注解、`from __future__ import annotations`、中文 docstring
- 错误处理红线（`tests/test_code_quality.py` 强制）：禁止新增裸 `except: pass` 吞错；
  异常必须让调用方可见（抛出/结果带 errors|warnings 标记），或显式降级（except 内有 return/赋值/raise）。
  存量 24 处吞错在各模块修复时逐步清理
- 不破坏调用方：core 公共函数签名（参数/返回）不改；确需修改标注 `[API-CHANGE]` 并同步全部调用方
- 不改评测资产：`datasets/`、`gap_checks/`、`run_evaluation.py` 冻结，修复只能改业务代码
- 注释只在 WHY 非显然时写；不写流水账注释
