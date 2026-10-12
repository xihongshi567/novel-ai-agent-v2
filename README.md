# 小说AI —— 基于 LLM 的中文长篇小说写作 Agent V3

一个开源、全流程的中文小说写作助手。从「一句话简介」出发，自动完成 **设定集 → 世界观 → 故事线 → 大纲 → 分章正文 → 节奏分析 → 审校修订** 的完整闭环，并提供 **CLI / Web UI / 飞书 Bot** 三种使用方式。

V3 是工程的固化版本：v1 打通全流程，v2 扩展功能与评测基线，v3 把全部能力纳入 7 模块契约框架（M1 记忆 / M2 上下文 / M3 生成与幻觉防控 / M4 数据流转 / M5 编排 / M6 外部通信 / M7 评测），以评测指标驱动修复，最终 **M7 离线评测 18 pass / 0 fail**。

## 特性

### 写作流程
- **设定 & 世界观**：自动生成人物（含动态状态追踪）、地点、势力、规则体系（含硬性约束）、历史、术语表
- **大纲 & 故事线**：卷→章层次大纲，主线/支线/人物线/悬念线的串联与 idea 自动安插；支持动态调整章节数（扩展承接当前大纲续写、缩短仅删待写章）
- **智能写作**：分章生成正文，每章前自动注入设定集、连续性约束、故事线脉络、相关 idea
- **上下文压缩**：长篇不崩的核心——用最近 N 章摘要代替全文，配合上章末尾衔接

### 质量控制
- **审校 & 偏离检测**：写完自动检查逻辑一致性、与大纲的偏离度、连续性违反；审校返回**逐处 diff**（UI 直接红绿对比），问题严重自动修订重写
- **节奏曲线分析**：每章张力/情绪/信息密度打分，自动检测平淡谷、高潮过载、情绪单调、钩子缺失
- **文风一致性**：LLM 自动提取全书文风指纹 + 人物语言指纹，检测后续章节漂移
- **时间线校核**：检测时序矛盾、人物分身、因果关系倒置
- **全局检查（audit）**：一键扫出设定缺失/游离内容/可提高点/主旨违反
- **多版本章节**：重写自动归档历史版本（上限 20），支持回滚、diff 对比

### 知识管理
- **灵感库**：暂存的点子（场景/情节点/对话/反转），写作时按本章人物自动检索注入；idea 与大纲实时连接，拆解出的新设定自动入库
- **主旨库**：作品核心思考与全局约束，`补充`/`拆解` 操作受主旨约束
- **情节消化（digest）**：把自然语言情节描述忠实拆解为 idea + 大纲节拍建议（不自行扩展、不动既有大纲）
- **连续性追踪**：自动记录伏笔（含回收状态）、持有物、承诺、既定事实——全部写成强制约束；硬约束解析 + 冲突检测/确认/治理状态持久化
- **全文 & 语义搜索**：跨章节关键词搜索 + 硅基流动 bge-m3 语义向量检索 + 伏笔反查；索引支持增量更新与一致性校验
- **统一知识库**：bible / continuity / world / ideas / threads / manifesto / pacing / style / constraints / conflicts 全部持久化为 JSON

### 使用界面
- **CLI**：24+ 命令覆盖全流程，支持批量连写、管道脚本
- **Gradio Web UI**：可视化操作，多标签页管理，含 Context Diagnostic 只读诊断页
- **飞书 Bot**：长连接模式（无需公网 IP），`#命令` 操作 + 无前缀自由对话（LLM 以写作教练身份应答）；消息用卡片渲染 Markdown

### 成本 & 安全
- **Token 成本统计**：每次 LLM 调用自动记账，按操作/章节/天汇总费用
- **自动备份**：写完每章 zip 快照，保留最近 10 个
- **原子写入**：全部落盘走 tempfile + os.replace，崩溃不产生半写文件
- **LLM 双后端**：OpenAI 兼容 API (DeepSeek / 硅基流动 / OpenAI) + Ollama 本地

## 版本演进

### v1（全流程打通）
从一句话简介到分章正文的完整写作闭环 + CLI/WebUI 双入口。

### v2（功能扩展 + 评测基线）
- 飞书 Bot 上线：长连接、消息去重、长文本分段、自由对话模式（写作教练）
- 主旨库（manifesto）+ 补充（enrich）+ 检查（audit）三大功能
- 情节消化（digest）：情节 → idea + 大纲节拍，忠实拆解不扩展
- 建立 M7 离线评测（9 缺口 + 3 遗留套件，A0 基线落盘）与模块边界契约

### v3（工程固化：7 模块框架 + 指标驱动修复）

v3 不新增用户功能，而是把 v1/v2 的全部能力按 **M1-M7 七模块契约**归位（归属与依赖方向由 `CLAUDE.md` 硬约束、AST 边界测试强制），并以 M7 评测缺口为驱动逐模块修复。修复前 A0 基线 14 项指标 fail，修复后全部翻 pass。

按模块的增强与修复：

| 模块 | 修复/增强内容 | 对应指标翻 pass |
|---|---|---|
| **M1 记忆管理** | 分层角色名解析（精确名/带注名/昵称/称呼）；伏笔回收保序匹配；ID 冲突感知——fs/pos/pm/fact 找空位复用，不再撞 ID | name_resolution_rate、resolution_accuracy/precision/recall |
| **M2 上下文管理** | 上下文截断显式化（不再静默丢失）；设定过滤复用同一解析；切点对齐句读；RAG 增量索引 `add_doc/remove_doc` + 索引一致性校验；`ContextBundle.section_stats` 各 section 注入量可观测 | truncation_visibility、rag_coverage、filter_precision/recall、boundary_quality |
| **M3 生成与幻觉防控** | 审校无效表面化（review_selfcheck）；摘要兜底改头尾采样（不再整体 fallback 丢实体）；审校返回逐处 diff | summary_fidelity、summary_purity、fallback_rate、review_invalid_surface |
| **M4 数据流转与持久化** | 15 处 save() 改原子写入（tempfile+os.replace 兜底崩溃半写）；章节版本上限 20，防 versions 目录膨胀 | —（可靠性基建） |
| **M5 编排与错误处理** | 吞错改显式降级（异常对调用方可见，红线可执行化）；返回契约统一（digest_plot/enrich/audit_project 顶层带 warnings）；`write_chapter` 注入 cancel_event 可取消，触发即回退 plan 状态 | silent_swallow_rate |
| **M6 外部通信** | 飞书消息改用 interactive 卡片 + markdown 元素渲染（text 类型不解析 Markdown）；`#想法列表` 等长文本自动分段不硬截断 | —（用户体验） |
| **M7 评测与可观测性** | 9 缺口回归基线 + 3 遗留套件统一 schema；`kb doctor` 跨 5 子表校验 id/必填字段/状态一致性 | 全部指标（见下） |

**当前 M7 状态**（`evaluation/results.json`，2026-10-08）：

| 套件 | 状态 |
|---|---|
| 9 缺口 × 19 项指标 | **18 pass / 0 fail**（1 项无目标 na） |
| 3 遗留套件（chapter_fit / continuity / retrieval） | 在册，schema 合法 |

总体结论：v3 相比 v2 不是功能扩张，而是围绕评测指标完成了 7 模块的系统性加固——

1. 名字匹配与伏笔回收（M1）；
2. 上下文截断/过滤/检索的可靠性与可观测性（M2）；
3. 审校与摘要的幻觉防控（M3）；
4. 持久化的原子性与容量控制（M4）；
5. 错误处理与返回契约的显式化（M5）；
6. 飞书消息渲染与交互体验（M6）；
7. 离线评测基线把"修复必须附带 M7 证明"固化为流程（M7）。

## 快速开始

> 注：本机（Windows）的 `python` 是 Store 占位符，请用 `py` 替代下文所有 `python`。

### 安装

```bash
pip install -r requirements.txt
```

### 配置

```bash
copy .env.example .env      # 填入 API key
copy config.example.yaml config.yaml
```

`.env`：
```
NOVEL_API_KEY=sk-你的DeepSeekKey
SILICONFLOW_API_KEY=sk-你的硅基流动Key    # 语义搜索用
FEISHU_APP_ID=cli_xxx                     # 飞书 Bot（可选）
FEISHU_APP_SECRET=xxx
```

`config.yaml` 常用服务商：

| 服务 | base_url | model |
|------|----------|-------|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 硅基流动 | `https://api.siliconflow.cn/v1` | `Qwen/Qwen2.5-72B-Instruct` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| Ollama 本地 | (改 `backend: ollama`) | `qwen2.5:7b-instruct` |

### 测试连通

```bash
python cli.py test
```

### 三步写第一章

```bash
# 1. 新建项目（自动生成设定 + 大纲）
python cli.py new mybook --title "书名" --genre 玄幻 --synopsis "故事简介..." --init --chapters 20

# 2. 搭建世界观（规则/历史/地理/术语，含硬性约束）
python cli.py kb mybook world --build

# 3. 写第一章（自动审校 + 状态追踪 + 备份）
python cli.py write mybook c001 --full
```

## CLI 命令全览

### 项目管理
| 命令 | 说明 |
|------|------|
| `new <name> --synopsis "..." --init` | 新建项目并生成大纲设定 |
| `list` | 列出所有项目 |
| `init <project>` | 为已有项目重新生成大纲/设定 |
| `chapters <project> <数量>` | 调整总章节数；扩展时承接当前大纲生成后续章节，缩短时仅删除待写章节 |
| `outline <project>` | 查看大纲 |
| `bible <project>` | 查看设定集 |
| `export <project>` | 导出全文 markdown |

### 写作执行
| 命令 | 说明 |
|------|------|
| `write <project> [cid]` | 写指定章节或下一章（含审校+追踪+备份），可 Ctrl-C 取消 |
| `batch <project> <n>` | 连写 n 章 |
| `rewrite <project> <cid> --passage "原文" --to "指令"` | 局部重写（自动归档旧版） |
| `version <project> <cid> --list/--rollback/--diff` | 章节版本管理 |

### 知识库
| 命令 | 说明 |
|------|------|
| `kb <project> view` | 查看完整知识库 |
| `kb <project> idea --add "..."` | 记录灵感 |
| `kb <project> world --build` | 搭建/补全世界观 |
| `kb <project> threads --weave` | 串联故事线 |
| `kb <project> timeline` | 时间线校核 |
| `kb <project> place` | idea 安插建议 |
| `kb <project> doctor` | 诊断：跨 5 子表校验 id/必填字段/状态一致性 |

### 分析与质量
| 命令 | 说明 |
|------|------|
| `pacing <project> --analyze` | 节奏曲线分析 |
| `style <project> --analyze` | 提取文风指纹 |
| `style <project> --check c001` | 检测某章文风漂移 |
| `track <project> --all` | 补跑状态追踪 |
| `search <project> <关键词> [--semantic]` | 全文/语义搜索 |
| `digest <project> <情节描述>` | 忠实拆解情节为 idea + 大纲节拍建议 |
| `manifesto <project>` | 主旨管理（核心思考/全局约束） |
| `enrich <project>` | 在主旨约束下补充内容 + 串联 idea |
| `audit <project>` | 全面检查：缺失/游离/可提高/主旨违反 |

### 进度与成本
| 命令 | 说明 |
|------|------|
| `stats <project>` | 写作进度仪表盘 |
| `cost <project>` | Token 用量与成本统计 |
| `backup <project>` | 手动备份 |
| `test` | 测试 LLM 后端连通性 |

## 飞书 Bot

飞书 Bot 是小说AI的移动端入口，非常适合随时记录灵感、查看进度、拆解情节。

### 启动

```bash
python feishu_bot.py
```

Bot 使用飞书**长连接模式**（无需公网 IP / 域名），收到消息自动去重（防飞书重试重复回复），长任务异步执行完成后主动推送。

### 前置配置（飞书开放平台后台，一次性）

1. 创建「企业自建应用」，记下 App ID / App Secret
2. 权限管理 → 开通：`im:message`、`im:message:send_as_bot`、`im:chat`、`contact:user`
3. 事件与回调 → 切换为**长连接模式**
4. 添加事件：`接收消息 v2.0` (im.message.receive_v1) 和 `消息已读` (im.message.message_read_v1)
5. 版本管理 → 创建版本并发布
6. 将 App ID/Secret 写入 `.env` 的 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`

### 可用命令（飞书聊天里发送）

| 命令 | 功能 |
|------|------|
| `#帮助` | 显示命令列表 |
| `#项目 [名字]` | 查看/切换当前项目 |
| `#想法 <内容> #标签 @人物` | 记录灵感 |
| `#想法列表` | 查看所有灵感 |
| `#进度` | 查看写作进度仪表盘 |
| `#下一章` | 写下一章（异步，完成后推送） |
| `#预览 [章节id]` | 预览章节（默认最新章节） |
| `#预览 下一章` | 预览下一个待写章节计划 |
| `#大纲` | 查看大纲 |
| `#设定` | 查看设定集 |
| `#连续性` | 查看连续性追踪表 |
| `#节奏` | 查看节奏曲线 |
| `#文风` | 查看文风指纹 |
| `#搜索 <关键词>` | 全文搜索 |
| `#知识库` | 查看完整知识库 |
| `#成本` | 查看成本统计 |
| `#备份` | 手动备份 |
| `#拆解 <情节描述>` | 情节消化为 idea + 大纲节拍建议 |
| `#主旨` | 查看作品主旨与全局约束 |
| `#补充` | 在主旨约束下补充内容 |
| `#检查` | 全面检查项目 |

**自由对话**：不带 `#` 前缀直接发消息，LLM 以写作教练身份结合项目上下文回答（适合理清思路、聊情节）。

**消息渲染**：回复以飞书卡片（interactive + markdown 元素）发送，粗体/列表/行内代码正常渲染；`#` 标题、代码块、表格受平台限制不会渲染。

长任务（写章节）约 1-3 分钟，完成后自动推送结果。

## 🧠 知识库架构

| 模块 | 文件 | 功能 |
|------|------|------|
| 设定集 | `bible.json` | 人物（含动态状态时间线）/地点/势力/物品/设定 |
| 连续性追踪 | `continuity.json` | 时间线/伏笔/持有物/承诺/既定事实 |
| 世界观 | `world.json` | 规则/历史/地理/文化/组织/术语，含硬约束 |
| 灵感库 | `ideas.json` | 场景/情节/对话/反转，按优先级标签管理 |
| 故事线 | `threads.json` | 主线/支线/人物线/悬念线节点串联 |
| 主旨库 | `manifesto.json` | 作品核心思考 + 全局约束 |
| 硬约束与冲突 | `constraints.json` / `conflicts.json` | 约束解析、冲突检测/确认/治理状态 |
| 节奏曲线 | `pacing.json` | 每章张力/情绪/信息密度/节奏/钩子评分 |
| 文风指纹 | `style.json` | 全文文风特征 + 人物语言指纹 |
| 搜索索引 | `embeddings/` | 文本索引 + bge-m3 向量库（numpy），支持增量更新 |
| 上下文溯源 | `chapters/provenance/` | 每章生成时实际使用的上下文来源记录 |

**写每章时，这些知识自动注入上下文**（设定 → 世界观约束 → 连续性约束 → 故事线 → 主旨约束 → 大纲 → 前情 → 灵感 idea），全部标注"务必遵守，不得违反"。

## 写作闭环

```
写章前： 世界观硬约束 + 连续性约束 + 故事线脉络 + 主旨约束 + 相关idea
         ↓
写章：   LLM 生成正文
         ↓
写完：   生成摘要 → 状态追踪回写bible → 更新continuity → 审校(偏离检测 + diff)
         ↓                                   [严重问题自动修订重写]
         └→ 自动备份 → 记录进度 → 记账token成本
```

## 项目结构

```
小说AI/
├── cli.py                        # 命令行入口（24+ 子命令）
├── webui.py                      # Gradio Web UI
├── feishu_bot.py                 # 飞书 Bot（长连接）
├── config.yaml                   # 你的配置文件
├── .env                          # API key
├── CLAUDE.md                     # 7 模块契约：归属 + 依赖方向（硬约束）
├── novel_agent/
│   ├── config.py                 # 配置加载
│   ├── kb.py                     # KnowledgeBase 统一接口
│   ├── llm/                      # LLM 后端
│   │   ├── openai_api.py         #   OpenAI 兼容 (DeepSeek/硅基/...)
│   │   ├── ollama.py             #   本地 Ollama
│   │   └── embedding.py          #   Embedding (硅基流动 bge-m3)
│   ├── core/                     # 数据模型（全部 JSON 持久化）
│   │   ├── project.py            #   项目元信息
│   │   ├── bible.py              #   设定集
│   │   ├── outline.py            #   大纲树
│   │   ├── chapter.py            #   章节 + 多版本管理
│   │   ├── continuity.py         #   连续性追踪
│   │   ├── world.py              #   世界观
│   │   ├── ideas.py              #   灵感库
│   │   ├── threads.py            #   故事线
│   │   ├── manifesto.py          #   主旨库
│   │   ├── constraints.py        #   硬约束解析
│   │   ├── conflicts.py          #   冲突检测/治理
│   │   ├── pacing.py             #   节奏数据
│   │   ├── style.py              #   文风指纹
│   │   ├── search.py             #   搜索引擎（关键词+向量）
│   │   ├── idea_retrieval.py     #   idea 多通道召回
│   │   ├── links.py              #   idea↔故事线↔章节 关联解析
│   │   ├── memory.py             #   记忆系统（上下文组装）
│   │   ├── chapter_fit.py        #   章节适配判断
│   │   ├── progress.py           #   写作进度
│   │   ├── usage.py              #   用量记账
│   │   ├── backup.py             #   自动备份
│   │   └── _atomic.py            #   原子写入（tempfile + os.replace）
│   ├── agents/                   # Agent 编排
│   │   ├── novel.py              #   NovelAgent 总管
│   │   ├── planner.py            #   规划
│   │   ├── writer.py             #   写作
│   │   ├── reviewer.py           #   审校+偏离检测
│   │   ├── tracker.py            #   状态追踪
│   │   ├── kb_agent.py           #   知识库操作
│   │   ├── pacing_agent.py       #   节奏分析
│   │   ├── rewrite_agent.py      #   局部重写
│   │   ├── style_agent.py        #   文风分析
│   │   └── llm_helpers.py        #   LLM 调用工具
│   ├── prompts/                  # 所有 Prompt 模板
│   │   ├── planner.py / writer.py / reviewer.py / tracker.py
│   │   ├── kb.py / pacing.py / rewrite.py / style.py
│   └── feishu/                   # 飞书 Bot 命令模块
│       └── commands.py           #   命令路由器 + 自由对话（可独立测试）
├── evaluation/                   # M7 离线评测
│   ├── run_evaluation.py         #   评测入口（输出 results.json）
│   ├── datasets/                 #   缺口用例 JSON
│   ├── gap_checks/               #   缺口检查模块
│   ├── metrics.py / mock_backend.py / _harness.py
├── projects/                     # 你的小说项目
│   └── mybook/                   #   一个项目
│       ├── project.json / bible.json / outline.json
│       ├── continuity.json / world.json / ideas.json / manifesto.json
│       ├── threads.json / pacing.json / style.json
│       ├── constraints.json / conflicts.json
│       ├── progress.json / usage_log.json
│       ├── chapters/             #     章节正文 + 摘要表
│       │   ├── versions/         #     历史版本（上限 20）
│       │   └── provenance/       #     章节上下文溯源
│       ├── backups/              #     自动备份 zip
│       └── embeddings/           #     向量库（可重建）
└── tests/                        # 22 个测试文件（94 用例）
    ├── test_offline.py           # 离线集成测试（mock LLM）
    ├── test_module_boundaries.py # AST 边界测试（强制依赖方向）
    └── test_m1_fix ~ test_m7_regression.py  # 各模块修复回归
```

## 测试与评测

```bash
py -m unittest discover tests    # 全量 94 用例（含边界测试）
py evaluation/run_evaluation.py  # M7 离线评测 → evaluation/results.json
```

- **全量测试**：22 个测试文件 94 用例，覆盖离线全数据流、阶段功能（phase1~6）、M1-M7 修复回归、代码质量红线（禁止裸 `except: pass`）、AST 模块边界契约
- **M7 离线评测**：不调 LLM/网络（mock 后端注入），覆盖 9 个已知缺口 + 3 个遗留套件，共 19 项指标；修复前 A0 基线 14 项 fail → 当前 **18 pass / 0 fail**（1 项无目标）
- **修复必须附带 M7 证明**：每个模块修复落地后重跑评测，对应指标翻 pass，并在该模块测试中断言达标——这是 v3 质量闭环的固定流程

## 使用建议

- **模型**：写长篇推荐 DeepSeek-V3（便宜 + 长文本好）；本地 7B 起步
- **省钱**：规划/摘要/审校用便宜模型，写作用强模型（writer_model 配置项）
- **人工把关**：自动生成后务必审阅大纲和设定；正文在 Web UI 里直接改后手动跑 `rewrite`
- **批量**：`batch` 适合无人值守，每 5-10 章用 `pacing --analyze` 检查一次节奏
- **飞书**：bot 适合碎片时间记录灵感、查看进度、拆解情节；大段写作建议用 CLI/WebUI
- **质量体检**：改完任何模块跑 `py evaluation/run_evaluation.py`，指标不允许回退
