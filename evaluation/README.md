# M7 离线评测与回归基线

`run_evaluation.py` 输出 `results.json`，覆盖 9 个已知缺口 + 3 个遗留套件，
全部离线运行（不调 LLM/网络，LLM 路径用 `mock_backend.py` 注入）。

运行（本机 `python` 是 Windows Store 占位符，必须用 `py`）：

    py evaluation/run_evaluation.py

`results.json` 的 `gaps[]` 每项：`{gap, metric, cases, value, target, status, direction, detail}`。
`status`：pass（达标）/ fail（未达标）/ na（无目标）。`direction`：max（越高越好）/ min（越低越好）。

## A0 基线（2026-10-07，修复前实测）

| 缺口 | 指标 | 基线 | 目标 | 状态 |
|---|---|---|---|---|
| name_matching | name_resolution_rate | 0.5 | 1.0 | fail |
| foreshadow_recovery | resolution_accuracy | 0.5 | 1.0 | fail |
| foreshadow_recovery | resolution_precision | 0.5 | 1.0 | fail |
| foreshadow_recovery | resolution_recall | 0.33 | 1.0 | fail |
| summary_fidelity | summary_entity_recall | 0.5 | ≥0.9 | fail |
| summary_fidelity | fallback_rate | 1.0 | 0.0 | fail |
| summary_purity | summary_purity | 0.0 | 1.0 | fail |
| rag_truncation | truncation_visibility | 0.0 | 1.0 | fail |
| rag_truncation | rag_coverage | 0.6 | 1.0 | fail |
| setting_filter | filter_precision | 0.8 | ≥0.9 | fail |
| setting_filter | filter_recall | 0.875 | 1.0 | fail |
| review_selfcheck | review_invalid_surface | 0.0 | 1.0 | fail |
| silent_failures | silent_swallow_rate | 1.0 | 0.0 | fail |
| chunk_boundary | boundary_quality | 0.0 | ≥0.9 | fail |

修复流程：每个模块（M1/M2/M3/M5）修复落地后重跑，对应指标 status 翻转 pass，
同时在修复模块的测试中把该指标断言为达标——这就是框架"修复必须附带 M7 证明"的执行方式。

## 目录

- `gap_checks/` — 每个缺口一个模块，`run()` 返回 result dict 列表；只调纯函数，
  真实流程类缺口（summary/review/silent）用 `_harness.py` 的临时项目 + MockBackend 走完整 NovelAgent 路径
- `datasets/` — 用例 JSON（name/foreshadow/setting/rag/chunk/summary/review）
- `metrics.py` — 指标工具（rate / result 构造）
- 遗留套件（chapter_fit / continuity / retrieval）计算逻辑不变，迁移到统一 schema

回归测试：`py tests/test_m7_regression.py`（断言 runner 完整性、12 套件在册、schema 合法；
不断言 value 达标——未修复前指标是 fail 的）。
