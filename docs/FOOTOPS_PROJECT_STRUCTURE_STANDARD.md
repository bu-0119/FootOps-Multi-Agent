# FootOps 项目结构与文件放置标准

> 文档状态：有效
> 基线日期：2026-07-31
> 学习样本：`/Users/buxy/python/mindbridge-py` 本机代码
> 适用范围：FootOps Web、Python Agent Service、契约、测试与部署文件

## 1. 文档目的

本文档回答四个工程问题：

1. MindBridge 的真实项目结构是什么；
2. 一次请求从 HTTP 到 Agent、工具和持久化分别经过哪些文件；
3. FootOps 新增代码时应该放在哪个目录、由哪个文件定义；
4. 哪些 MindBridge 做法应学习，哪些只能视为现有实现而不能照搬。

本文档只规定代码组织和依赖边界。产品范围以
[FOOTOPS_REQUIREMENTS.md](./FOOTOPS_REQUIREMENTS.md) 为准，Agent 目标架构以
[FOOTOPS_MINDBRIDGE_ARCHITECTURE.md](./FOOTOPS_MINDBRIDGE_ARCHITECTURE.md)
为准，实际完成情况以
[FOOTOPS_CURRENT_PROGRESS.md](./FOOTOPS_CURRENT_PROGRESS.md) 为准。

## 2. MindBridge 真实结构

忽略 `__pycache__`、`.idea`、运行数据、模型权重和带 `(1)` 的重复副本后，
MindBridge 的有效结构如下：

```text
mindbridge-py/
├── app/
│   ├── main.py                   # FastAPI 组装、启动/关闭、静态页面挂载
│   ├── api/
│   │   └── routes.py             # HTTP/SSE 路由和认证依赖
│   ├── core/
│   │   ├── config.py             # Settings 与环境变量映射
│   │   ├── database.py           # SQLAlchemy Base、Engine、Session
│   │   ├── bootstrap.py          # 建表、种子用户、内置知识初始化
│   │   ├── security.py           # Basic Auth 与角色校验
│   │   └── enums.py              # 跨模块业务枚举
│   ├── agents/
│   │   ├── harness.py            # 线上单轮 Runtime Harness
│   │   ├── factory.py            # Runtime 组装入口
│   │   ├── event_driven_runtime.py # 创建黑板、Agent 并执行协作
│   │   ├── events.py             # Task/Event/Artifact/Blackboard 协议
│   │   ├── registry.py           # 能力、Profile、Claim 和 Agent 注册
│   │   ├── coordinator.py        # 有限轮次调度与最终采纳策略
│   │   ├── autonomous.py         # 各角色 Agent 的 decide/act 实现
│   │   └── result.py             # Runtime 对外稳定结果
│   ├── services/
│   │   ├── chat.py               # 调用 Harness 并输出 SSE
│   │   ├── ai.py                 # 模型客户端和 PromptTemplates
│   │   ├── agent_models.py       # 每个 Agent 的模型配置选择
│   │   ├── assessment.py         # 风险评估业务能力
│   │   ├── knowledge.py          # 检索、融合和 rerank
│   │   ├── vector_store.py       # Chroma 适配
│   │   ├── memory.py             # Redis 短期记忆与压缩
│   │   ├── skills.py             # SKILL.md 加载、校验和选择
│   │   ├── tools.py              # 工具的业务实现
│   │   ├── tool_governance.py    # 工具策略和审计定义
│   │   ├── tool_queue.py         # 异步任务、重试、限流、死信
│   │   ├── mcp_client.py         # MCP stdio Client
│   │   ├── trace.py              # Agent run trace 落库
│   │   ├── report.py             # 后台查询和 DTO 转换
│   │   └── privacy.py            # 输入和记忆脱敏
│   ├── models/
│   │   └── entities.py           # SQLAlchemy 持久化实体
│   ├── schemas/
│   │   └── dtos.py               # HTTP 输入输出 Pydantic DTO
│   ├── mcp_tools/
│   │   └── server.py             # MCP Server 和 @mcp.tool 暴露
│   ├── harness/
│   │   └── runner.py             # 离线 Engineering Harness
│   ├── rag_eval/
│   │   ├── runner.py             # RAG 评测入口
│   │   └── mindbridge-rag-eval.json
│   ├── knowledge/                 # 内置领域知识 Markdown
│   └── static/                    # 原生 Web 页面
├── skills/
│   └── <skill_name>/SKILL.md      # 可版本化业务 Skill 内容
├── tests/                         # unittest 回归测试
├── scripts/                       # 开发、模型和打包脚本
├── data/                          # 本地运行数据和输出
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 3. MindBridge 请求链与文件职责

MindBridge 的学生聊天请求真实经过以下链路：

```text
app/main.py
  -> app/api/routes.py
  -> app/services/chat.py
  -> app/agents/harness.py
  -> app/agents/factory.py
  -> app/agents/event_driven_runtime.py
  -> app/agents/coordinator.py
  -> app/agents/registry.py + app/agents/autonomous.py
  -> app/agents/events.py 中的 Blackboard/Task/Artifact/Event
  -> app/agents/result.py
  -> app/agents/harness.py 做落库、trace 和工具计划
  -> app/services/chat.py 负责 SSE 模型输出
  -> app/services/tool_queue.py 或 app/services/mcp_client.py
```

这条链路体现了三个重要边界：

1. HTTP 层不编排 Agent，只负责认证、参数和传输；
2. Runtime 只负责 Agent 协作，外部业务副作用由 Harness 统一承接；
3. Agent 之间不直接改写彼此状态，而是通过 Task、Artifact、Event 和共享黑板协作。

MindBridge 中两个名称相近但用途不同的 Harness 必须区分：

| 类型 | MindBridge 位置 | 职责 |
| --- | --- | --- |
| Runtime Harness | `app/agents/harness.py` | 每个线上请求都会经过，负责脱敏、Runtime 调用、消息/报告/trace 落库和工具计划 |
| Engineering Harness | `app/harness/runner.py` | 离线验证环境，使用 Mock AI、SQLite 和内存记忆跑核心链路测试并生成报告 |

## 4. MindBridge 定义位置索引

| 概念 | 定义位置 | 备注 |
| --- | --- | --- |
| 应用入口 | `app/main.py` | 只组装应用和生命周期资源 |
| HTTP/SSE DTO | `app/schemas/dtos.py` | 面向外部接口，不等同于 Agent Artifact |
| ORM 实体 | `app/models/entities.py` | 只描述持久化结构 |
| 配置 | `app/core/config.py` | 从环境变量读取；敏感值不应有真实默认值 |
| Agent Profile/Capability | `app/agents/registry.py` | 声明能力、模型、记忆和工具权限 |
| 协作协议 | `app/agents/events.py` | Task、Claim、Message、Artifact、Event、Blackboard |
| 调度循环 | `app/agents/coordinator.py` | 轮次、预算、任务派生、Claim、审查和最终采纳 |
| Agent 行为 | `app/agents/autonomous.py` | `decide` 决定是否认领，`act` 发布产物 |
| Runtime 组装 | `app/agents/event_driven_runtime.py` | 创建服务、Agent、Blackboard，转换稳定结果 |
| Runtime 返回契约 | `app/agents/result.py` | 隔离 Runtime 内部结构和上层 Harness |
| Runtime Harness | `app/agents/harness.py` | 业务外围编排和副作用边界 |
| 模型供应商 | `app/services/ai.py` | OpenAI-compatible/Ollama/Mock |
| 每 Agent 模型选择 | `app/services/agent_models.py` | Role 到模型 Profile 的映射 |
| Skill 内容 | `skills/<name>/SKILL.md` | YAML frontmatter + `## Workflow` |
| Skill 运行时 | `app/services/skills.py` | 加载、校验、选择和模板渲染 |
| 工具业务实现 | `app/services/tools.py` | 可被队列和 MCP 共同复用 |
| 工具权限 | `app/services/tool_governance.py` | 白名单、风险边界和审计结构 |
| 队列执行 | `app/services/tool_queue.py` | 幂等、依赖、重试、限流和死信 |
| MCP 暴露 | `app/mcp_tools/server.py` | 薄协议层，不重复业务逻辑 |
| MCP 调用 | `app/services/mcp_client.py` | stdio 会话和结果归一化 |
| Run trace | `app/services/trace.py` | 将步骤、任务、事件和产物序列化落库 |
| 工程验证 | `app/harness/runner.py` | 独立于线上 Runtime Harness |

## 5. FootOps 学习与修正规则

FootOps 学习 MindBridge 的职责分离，不机械复制其文件数量和历史问题。

### 5.1 必须学习

1. API、Harness、Runtime、Agent、工具和持久化分层；
2. Runtime Harness 与 Engineering Harness 分开；
3. Blackboard、Task、Artifact、Event 使用明确数据结构；
4. Agent Runtime 对上层返回稳定结果，不泄露框架内部对象；
5. Skill 内容与 Skill 加载代码分开；
6. MCP Server 只做协议暴露，实际业务实现由普通 Service/Tool 复用；
7. 工具调用经过白名单、审计、队列和失败处理；
8. Mock、临时数据库和内存依赖能够构造可重复验证环境。

### 5.2 不得照搬

1. 不复制带 `(1)` 的重复文件；
2. 不在 `Settings`、源码或测试中写真实 API Key；
3. 不把所有 Agent 长期堆在一个超大 `autonomous.py` 中；
4. 不把 API DTO、Agent Artifact 和 ORM Entity 混成同一个模型；
5. 不让 Agent 直接操作 FastAPI Request、SQLAlchemy Session 或前端结构；
6. 不让工具治理只停留在定义或测试中，正式执行链必须实际调用授权与审计；
7. 不把 `Base.metadata.create_all` 当作长期数据库迁移方案；
8. 不提交 Chroma 数据、Excel、数据库、模型权重或其他运行产物。

## 6. FootOps 标准目标结构

FootOps 是 Monorepo，保留现有 `src` 包布局。后续新增文件必须遵守以下结构：

```text
FootOps/
├── apps/
│   └── web/                           # React 用户工作台
│       └── src/
│           ├── api/                   # HTTP/SSE Client，不包含业务推理
│           ├── components/            # 视图组件
│           ├── features/              # 按业务功能聚合的 UI 状态与交互
│           ├── fixtures/              # 仅测试/Story fixture，不进入正式业务数据流
│           └── types/                 # 前端本地类型或契约生成类型
├── services/
│   └── agent/
│       ├── pyproject.toml
│       ├── README.md
│       ├── skills/
│       │   └── <skill_name>/SKILL.md  # 声明式业务 Skill
│       ├── knowledge/                 # 稳定战术概念知识，不放实时比赛事实
│       ├── src/footops_agent/
│       │   ├── api/
│       │   │   ├── main.py            # App factory、middleware、lifespan
│       │   │   ├── dependencies.py    # FastAPI Depends
│       │   │   ├── routes/            # 按资源拆分的薄路由
│       │   │   └── schemas/           # HTTP Request/Response DTO
│       │   ├── core/
│       │   │   ├── config.py          # Settings
│       │   │   ├── database.py        # Engine/Session/Base
│       │   │   ├── bootstrap.py       # 启动初始化
│       │   │   ├── security.py        # 认证和权限
│       │   │   └── enums.py           # 跨模块稳定枚举
│       │   ├── cli/
│       │   │   └── data_audit.py       # 数据覆盖审计命令入口
│       │   ├── agents/
│       │   │   ├── factory.py         # Agent/Runtime 依赖组装
│       │   │   ├── registry.py        # Profile/Capability/Claim
│       │   │   ├── result.py          # Runtime 稳定返回类型
│       │   │   ├── planner.py         # 当前规划 Agent
│       │   │   ├── coordinator.py     # CoordinatorAgent 行为
│       │   │   ├── data_agent.py      # DataAgent 行为
│       │   │   ├── tactical_agent.py  # TacticalAgent 行为
│       │   │   └── evidence_agent.py  # EvidenceAgent 行为
│       │   ├── collaboration/
│       │   │   ├── events.py          # Task/Claim/Event/Message 协议
│       │   │   ├── blackboard.py      # AnalysisBlackboard 纯状态操作
│       │   │   └── scheduler.py       # 有限循环、预算、调度和采纳
│       │   ├── runtime/
│       │   │   ├── service.py         # 创建一次 Agent run
│       │   │   ├── model_adapter.py   # AgentScope/模型供应商隔离层
│       │   │   └── result_mapper.py   # Blackboard 到稳定结果转换
│       │   ├── harness/
│       │   │   ├── service.py         # 线上 FootOpsAgentHarness
│       │   │   ├── outcomes.py        # Harness 输入/输出和工具计划
│       │   │   └── errors.py          # 对外稳定错误
│       │   ├── artifacts/
│       │   │   ├── base.py            # ID、版本、来源、时间等公共字段
│       │   │   ├── planning.py        # AnalysisPlan
│       │   │   ├── match_data.py      # 标准化比赛数据快照
│       │   │   ├── metrics.py         # 确定性指标结果
│       │   │   ├── evidence.py        # Claim/Evidence/Citation
│       │   │   ├── tactics.py         # 战术板节点和连线
│       │   │   └── report.py          # 最终分析报告
│       │   ├── services/
│       │   │   ├── analysis.py        # 业务用例服务
│       │   │   ├── data_catalog.py    # 比赛范围和数据覆盖判断
│       │   │   ├── metric_engine.py   # 确定性指标计算
│       │   │   ├── evidence_gate.py   # 结论证据审核
│       │   │   ├── skill_library.py   # Skill 选择和渲染
│       │   │   └── trace.py           # Run trace 组装
│       │   ├── providers/
│       │   │   ├── base.py            # 数据 Provider Protocol
│       │   │   └── <provider>.py      # 具体数据源适配
│       │   ├── repositories/
│       │   │   ├── models.py          # ORM Entity
│       │   │   ├── analysis_workspace.py # 当前 Workspace Protocol/内存实现
│       │   │   ├── analysis.py        # 后续 SQL Analysis/Artifact Repository
│       │   │   └── session.py         # DB Session 管理
│       │   ├── memory/
│       │   │   ├── store.py           # Redis/内存 Store
│       │   │   └── compaction.py      # 上下文裁剪和摘要
│       │   ├── skills/
│       │   │   ├── registry.py        # SKILL.md 加载和校验
│       │   │   └── selector.py        # Skill 触发规则
│       │   ├── tools/
│       │   │   ├── definitions.py     # AgentScope Tool Schema/FunctionTool
│       │   │   ├── implementations.py # 普通 Python 业务实现
│       │   │   └── governance.py      # 白名单、参数与副作用策略
│       │   ├── mcp/
│       │   │   ├── server.py          # MCP Server 薄适配
│       │   │   └── client.py          # 外部 MCP Client
│       │   ├── workers/
│       │   │   ├── queue.py           # Job 入队和幂等
│       │   │   └── runner.py          # 重试、限流和死信执行
│       │   ├── observability/
│       │   │   ├── tracing.py         # Trace 事件与序列化
│       │   │   └── metrics.py         # 延迟、Token、成本、成功率
│       │   └── prompts/
│       │       ├── common.py           # FootOps 公共边界
│       │       └── planner.py          # 角色 Prompt 与版本号
│       └── tests/
│           ├── unit/                   # 纯函数、Artifact、Agent 决策
│           ├── integration/            # API、DB、Provider、队列
│           ├── contract/               # Schema/OpenAPI 兼容性
│           └── engineering_harness/
│               ├── runner.py           # 一键验证入口
│               └── suites/             # data/metrics/evidence/api/agent/tools
├── contracts/
│   ├── openapi/                         # 冻结或生成的 HTTP 契约
│   ├── artifacts/                       # 跨服务 Artifact JSON Schema
│   └── events/                          # SSE/队列事件 Schema
├── infra/
│   ├── docker/
│   ├── compose/
│   └── migrations/                      # Alembic 迁移
├── scripts/                              # 仓库级开发/检查/打包命令
├── docs/
└── README.md
```

目录只在真实功能开始实现时创建。不得为了让目录树“看起来完整”而长期保留大量
无代码、无测试、无近期任务的空包。

## 7. 文件放置判定标准

| 要新增的内容 | 必须放置位置 | 不允许放置位置 |
| --- | --- | --- |
| HTTP 路由 | `api/routes/` | Agent、Harness、Repository |
| HTTP 请求/响应 DTO | `api/schemas/` | `artifacts/`、ORM models |
| Agent 协作产物 | `artifacts/` | API DTO、数据库 Entity |
| Agent 的 `decide/act/reply` 行为 | `agents/<role>.py` | routes、services、prompts |
| 任务、Claim、事件协议 | `collaboration/events.py` | 某个具体 Agent 文件 |
| Blackboard 状态操作 | `collaboration/blackboard.py` | Agent 或 Harness |
| Loop、轮次、预算、最终采纳 | `collaboration/scheduler.py` | API、AgentScope adapter |
| AgentScope 和模型 SDK 调用 | `runtime/model_adapter.py` | API、Artifact、Repository |
| 单次 run 的 Runtime 组装 | `runtime/service.py` | HTTP route |
| 输入限制、超时、trace、落库、工具计划 | `harness/service.py` | Agent 内部 |
| 确定性指标算法 | `services/metric_engine.py` | Prompt、Agent、前端 |
| 数据源 HTTP/SDK 适配 | `providers/<provider>.py` | Agent、Repository |
| 数据库 Entity/Repository | `repositories/` | API Schema、Artifact |
| Prompt 文本和版本 | `prompts/` | `model_adapter.py`、route |
| Skill 内容 | `services/agent/skills/<name>/SKILL.md` | Prompt 常量、数据库 |
| Skill 加载和选择代码 | `src/footops_agent/skills/` | Skill Markdown |
| Agent 可调用工具 Schema | `tools/definitions.py` | MCP Server 内重复定义 |
| 工具业务实现 | `tools/implementations.py` 或领域 Service | Agent、MCP 协议层 |
| 工具授权和副作用规则 | `tools/governance.py` | Prompt |
| MCP 暴露/调用 | `mcp/server.py`、`mcp/client.py` | Agent 业务实现 |
| 异步 Job | `workers/` | 请求内直接执行的 SSE 链路 |
| 线上 trace | `observability/` + Repository | Engineering Harness 报告 |
| 一键工程验证 | `tests/engineering_harness/` | 线上 `harness/` |
| 实时比赛事实 | Provider 快照/数据库 | `knowledge/`、Skill、Prompt |

## 8. 三类模型必须分开

FootOps 不允许一个 Pydantic 类同时承担所有层的职责。

| 模型类型 | 用途 | 示例 |
| --- | --- | --- |
| API DTO | 外部传输、兼容性和输入校验 | `AnalysisRequest`、`AnalysisResponse` |
| Artifact | Agent 间协作、证据链和版本化产物 | `MetricArtifact`、`EvidenceArtifact` |
| ORM Entity | 数据库存储结构和索引 | `AnalysisRunEntity`、`ArtifactEntity` |

允许显式转换：`API DTO -> Harness Input -> Artifact -> ORM Entity`。不允许把 ORM
对象直接交给模型，也不允许让前端依赖 AgentScope 内部类型。

## 9. 依赖方向

允许的主要依赖方向：

```text
api -> services/harness
harness -> runtime + repositories + workers + observability
runtime -> agents + collaboration + artifacts + tools
agents -> artifacts + collaboration + service/tool Protocol
services -> artifacts + providers + repositories
tools -> services/providers + artifacts
mcp -> tools/services
workers -> tools + repositories
repositories -> core.database
```

禁止反向依赖：

1. `artifacts` 不得导入 FastAPI、SQLAlchemy、AgentScope；
2. `agents` 不得导入 `api`；
3. `providers` 不得调用 Agent；
4. `repositories` 不得调用模型；
5. `apps/web` 不得依赖 Python 内部包；
6. `runtime/model_adapter.py` 之外的业务代码不得直接依赖具体模型供应商；
7. `mcp/server.py` 不得复制工具业务逻辑。

## 10. 新功能落位示例

新增“分析佩德里最近五场角色变化”时，文件分工应是：

```text
api/routes/analyses.py              接收请求、返回 run_id/SSE
api/schemas/analysis.py             AnalysisRequest/Response
harness/service.py                  创建 run、限时、落 trace、安排后处理
runtime/service.py                  启动本轮 Agent Runtime
agents/planner.py                   理解问题并发布 AnalysisPlan
providers/<provider>.py             获取可追溯比赛数据
services/metric_engine.py           计算位置、触球、推进等确定性指标
artifacts/match_data.py             保存标准化比赛数据快照
artifacts/metrics.py                保存指标结果和算法版本
agents/tactical_agent.py            基于指标提出战术解释
agents/evidence_agent.py            审核 Claim 与 Evidence
services/evidence_gate.py           执行确定性证据门禁
artifacts/tactics.py                生成战术板结构
artifacts/report.py                 生成最终报告结构
repositories/analysis.py            持久化 run 和 Artifact
observability/tracing.py            记录步骤、工具和采纳结果
```

## 11. 当前 FootOps 与标准的差异

| 当前内容 | 判断 | 后续处理 |
| --- | --- | --- |
| `api/main.py` 同时包含全部路由 | 首个 Spike 可接受 | 接口增加时拆为 `api/routes/` 与 `api/schemas/` |
| `api/schemas.py` 单文件 | 首个 Spike 可接受 | Schema 超过一个业务资源后按领域拆分 |
| `agents/planner.py` | 位置正确 | 保持只负责 Agent 行为 |
| `artifacts/planning.py` | 位置正确 | 后续增加公共 Artifact 元数据与版本 |
| `runtime/model_adapter.py` | 位置正确 | AgentScope/DeepSeek 继续只在 Runtime 层出现 |
| `harness/service.py` | 位置正确 | 后续增加 outcome、trace、持久化和工具计划 |
| 根包 `prompts.py` | 过渡结构 | Prompt 增多时迁移为 `prompts/common.py`、`prompts/planner.py` |
| 多个空目录包 | 目标占位 | 对近期不用的空包删除或在功能落地时再创建 |
| 已建立 `services/`、`providers/`、`artifacts/` 数据链路 | Phase 2A 边界已落地 | 保持 Provider、确定性服务和 Agent 行为分离；需要共享领域逻辑时再引入 `core/` |
| Finding Builder 与 Evidence Gate 已位于 `services/` | 符合确定性业务服务边界 | Agent 后续只能提交 Finding，不得绕过 Gate 直接发布结论 |
| Workspace Service 与进程内 Repository 已落地 | 符合 Service 依赖 Repository Protocol 的方向 | 接 SQLAlchemy 时替换 Repository 实现，不改 API 和业务服务 |
| `artifacts/tactics.py` 与 `services/tactics_board.py` 已落地 | Artifact 与确定性映射职责分开 | 后续 Tactical Agent 只能提交 Finding，不得直接拼前端坐标 |
| 基础分析 SSE 已落地 | API 只传输版本化业务事件 | Phase 2B 扩展工具、门禁和停止原因事件，不在路由中编排 Agent |
| 尚无 Engineering Harness | 未完成 | 数据、指标、证据链出现后建立独立 runner/suites |

当前已有代码不因本标准立即进行无收益搬迁。只有当下一项真实功能需要相应边界时，
才按标准渐进拆分，并由测试保证行为不变。

## 12. 结构验收清单

每次新增模块或完成阶段前检查：

- 是否能用一句话说明该文件的唯一职责；
- HTTP DTO、Artifact 和 ORM Entity 是否分开；
- 模型 SDK 是否仍被限制在 Runtime Adapter；
- 数值是否由确定性 Service/Tool 计算，而不是 Prompt 生成；
- Agent 是否只通过 Artifact/Task/Event 协作；
- Harness 是否统一负责运行边界和副作用；
- Tool 是否经过实际执行的治理与审计；
- MCP 是否只是普通工具实现的协议适配；
- Runtime Harness 和 Engineering Harness 是否没有混用；
- 新目录是否有真实代码、测试或明确的当前阶段任务；
- 密钥和运行产物是否被排除在版本控制之外；
- `FOOTOPS_CURRENT_PROGRESS.md` 是否同步更新。

违反本标准时，应先修正归属和依赖，再继续叠加功能。框架便利性不能成为打破
业务边界的理由。
