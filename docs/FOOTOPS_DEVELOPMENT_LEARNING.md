# FootOps 按开发顺序学习手册

> 文档状态：持续更新
> 建立日期：2026-07-31
> 当前学习进度：本机 Redis Vector RAG 与两场球员报告首切片已接入
> 用途：把每个已完成开发切片转化为可复习的工程知识

## 1. 这份文档解决什么问题

开发进度文档回答“现在完成了什么”，架构文档回答“最终准备怎么做”，本手册回答：

1. 这一项技术为什么要接入；
2. 它在 FootOps 调用链中承担什么职责；
3. 它与 MindBridge 中同类能力有什么共同点和差异；
4. 应该阅读哪些代码；
5. 如何亲自验证；
6. 当前实现还不能做什么；
7. 它会怎样连接到后续开发。

本手册按 [FOOTOPS_DEVELOPMENT_ORDER.md](./FOOTOPS_DEVELOPMENT_ORDER.md) 的阶段
顺序编写。只有已经实现和验证的能力可以写入“已完成”章节；规划中的能力只能进入
“后续学习目录”。

## 2. 每次开发完成后的记录模板

每完成一个可以独立运行的切片，在本手册追加一节，并填写：

```text
开发阶段：
完成状态：
一句话理解：
为什么开发：
在调用链中的位置：
核心实现：
MindBridge 同类能力：
共同点：
关键差异：
阅读代码：
动手验证：
当前边界：
与下一步的关系：
```

记录不是提交日志。不要只写“新增了某文件”，而要解释设计原因、依赖方向和取舍。

## 3. Phase 1：React 静态工作台

### 3.1 一句话理解

Phase 1 先用 Mock 数据验证用户是否能在一个工作区里完成提问、查看证据、观察趋势和
编辑战术板，再决定后端需要交付哪些稳定业务数据。Phase 2A 接入真实数据后已删除这些
业务 Mock。

### 3.2 为什么先开发前端原型

FootOps 不是一个只输出文字的聊天机器人。它需要同时展示分析结论、比赛样本、指标、
证据、趋势图和战术板。先建立静态原型，可以提前确认页面布局和交互需求，并反推后端
Artifact Schema。

### 3.3 在系统中的位置

```text
用户
  -> React 工作台
  -> Phase 1 原型 Mock（现已删除）
  -> 聊天区 / 趋势图 / 证据面板 / 战术板
```

### 3.4 与 MindBridge 的对比

MindBridge 的前端核心是学生聊天和后台报告；FootOps 的前端核心是分析工作区。两者都
需要展示对话和运行结果，但 FootOps 还必须确定性渲染图表与可编辑战术板，因此前端不能
只消费一段模型文本。

### 3.5 阅读代码

- `apps/web/src/App.tsx`：工作台入口；
- `apps/web/src/components/ChatView.tsx`：问答与当前规划接口；
- `apps/web/src/components/TrendChart.tsx`：趋势图原型；
- `apps/web/src/components/EvidencePanel.tsx`：证据面板；
- `apps/web/src/components/TacticsBoard.tsx`：战术板交互；
- `apps/web/src/api/data.ts`：Phase 2A 真实数据契约与请求入口。

### 3.6 动手验证

```bash
npm install
npm run dev
npm run build
```

### 3.7 当前边界与下一步

当前趋势图、比赛、球员和来源已经消费后端真实 Artifact；战术结论、证据审核、自动
战术图层和报告尚未实现，页面显示为空状态，不再使用演示结果替代。

## 4. Phase 2A：业务契约和 Artifact

### 4.1 一句话理解

Artifact 是系统各层共同使用的、可校验和可追溯的业务产物，不是一段随意组织的 JSON。

### 4.2 为什么先定义 Schema

如果前端、数据服务和 Agent 各自发明字段，后续无法稳定渲染、恢复或审核结果。因此
FootOps 使用 Pydantic 定义严格模型，并导出 JSON Schema 与 OpenAPI，让前端和后端
围绕相同契约开发。

已经定义的主要产物包括：

- `AnalysisPlan`：尚未执行的分析计划；
- `CoverageAuditArtifact`：数据覆盖审计；
- `MatchDataSnapshot`：标准化比赛事件快照；
- `PlayerRoleMetricArtifact`：确定性球员角色指标；
- `EvidenceReference`：来源或指标引用；
- `AnalysisWorkspace`：可恢复分析工作区的初始契约。

### 4.3 与 MindBridge 的对比

MindBridge 使用通用 `AgentArtifact(kind, payload)` 在自研黑板上传递产物，适合承载不同
心理支持任务；FootOps 当前优先使用足球领域的强类型 Artifact，因为指标字段、单位、
来源和比赛范围必须被程序校验。未来多 Agent 的通信和任务状态由 AgentScope App/Team
负责，消息中只传 Artifact ID 或摘要；完整 Artifact 仍保存在 FootOps Workspace/
Repository，不退化为只有模型才能理解的自由文本。

### 4.4 阅读代码与验证

- `services/agent/src/footops_agent/artifacts/`：Pydantic 业务模型；
- `contracts/artifacts/`：生成的 JSON Schema；
- `contracts/openapi/footops-agent.openapi.json`：HTTP 契约。

```bash
.venv/bin/pytest services/agent/tests/test_api.py
```

### 4.5 当前边界与下一步

Finding、EvidenceReview、TacticsBoard 和最终报告 Artifact 尚未实现。现有 Schema 证明了
契约方向，但还没有完成完整分析工作区的持久化。

## 5. Phase 2A：FastAPI 服务边界

### 5.1 一句话理解

FastAPI 是 Web 与 Python 分析能力之间的稳定传输边界，不负责代替 Agent、数据服务或
指标引擎进行业务推理。

### 5.2 当前调用链位置

```text
React
  -> Vite /api 代理
  -> FastAPI Request Schema
  -> Harness 或确定性 Service
  -> Response Schema
```

当前接口包括健康检查、LLM 状态、结构化计划、数据覆盖和球员角色指标等切片。API 层
负责输入校验、依赖组装、错误映射和响应契约。

### 5.3 与 MindBridge 的对比

MindBridge 同样使用 FastAPI，但已经包含认证、聊天 SSE、数据库会话和后台报告。FootOps
目前只实现 MVP 所需的薄接口；没有提前复制认证、Redis、数据库和复杂 SSE 链路。

### 5.4 阅读代码与验证

- `services/agent/src/footops_agent/api/main.py`：应用和路由组装；
- `services/agent/src/footops_agent/api/schemas.py`：HTTP DTO；
- `services/agent/tests/test_api.py`：接口契约测试。

```bash
.venv/bin/uvicorn footops_agent.api.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/health
```

## 6. Phase 2A Spike：FootOpsAgentHarness

### 6.1 一句话理解

Harness 位于 API 与 Agent 之间，管理一次模型运行的工程边界，而不是替模型思考。

### 6.2 当前作用

当前 Harness 已负责：

- 为每次运行生成 `run_id`；
- 限制输入长度；
- 检查模型配置；
- 限制调用超时；
- 将内部异常转换为稳定 API 错误；
- 明确标记是否调用模型、是否取数、是否生成真实结论。

### 6.3 与 MindBridge 的对比

MindBridge 的 Runtime Harness 已经负责隐私脱敏、会话消息、Redis 记忆、数据库、运行
Trace、工具计划和报告落库。FootOps 当前 Harness 只是最小安全外壳。两者的共同原则是
把生命周期和副作用放在 Agent 外层；差异在于 FootOps 尚未进入持久化、工具治理和恢复
阶段。

### 6.4 阅读代码与验证

- `services/agent/src/footops_agent/harness/service.py`；
- `services/agent/src/footops_agent/harness/errors.py`；
- `services/agent/tests/test_harness.py`。

```bash
.venv/bin/pytest services/agent/tests/test_harness.py
```

### 6.5 当前边界与下一步

当前 Harness 还没有预算统计、取消、Checkpoint、重试、工具后处理和 Trace 持久化。
这些能力必须在实际业务链需要时按开发顺序补充。

## 7. Phase 2A Spike 与架构审计：AgentScope 2.0.5

### 7.1 一句话理解

AgentScope 是 FootOps 选择的 Agent Runtime，不是只负责单 Agent 的模型包装器；只是
FootOps 当前仅接入了它的单 `Agent` 切片，多 Agent App/Team 能力还没有进入运行链路。

### 7.2 为什么接入 AgentScope

直接调用模型 API 只能得到一次文本补全。Agent 系统还需要有限 ReAct 循环、工具调用、
结构化输出、上下文状态、任务拆分、SubAgent 生命周期、团队通信和会话存储。AgentScope
2.0.5 已提供这些通用能力，FootOps 应把开发时间用于足球数据、指标、Artifact 和证据
门禁，而不是重写一套通用多 Agent 框架。

当前已经运行的 Spike 只有：

```text
AnalysisPlanner
  -> AgentScope Agent + ReActConfig
  -> DeepSeekChatModel
  -> structured_schema=AnalysisPlan
  -> Pydantic 校验
```

已从本地 2.0.5 包源码审计、但尚未接入的能力包括：

| 能力 | AgentScope 2.0.5 入口 | FootOps 计划用途 |
| --- | --- | --- |
| 工具和 Skill | `Toolkit`、`FunctionTool`、MCP、Skill | Phase 2B 注入数据与指标只读工具 |
| 上下文状态 | `ContextConfig`、`AgentState` | 压缩长上下文并保存 Agent 运行状态 |
| 任务状态 | `TaskContext`、`TaskCreate/Get/List/Update` | 代替自研通用任务板 |
| App/Team | `create_app`、`SubAgentTemplate` | Team Leader 按角色模板创建 SubAgent |
| 团队协作 | App 注入的 Agent 创建/邀请/通信工具 | 代替自研 Agent 生命周期和群聊协议 |
| 实时传输 | `InMemoryMessageBus`、`RedisMessageBus` | 跨 Session 消息与唤醒 |
| 框架持久化 | `RedisStorage`、`AsyncSQLAlchemyStorage` | Agent、Session、Team 等框架状态 |
| 文件工作区 | `LocalWorkspaceManager` 等 | Agent 工作目录和隔离；不同于 AnalysisWorkspace |

### 7.3 与 MindBridge 同类能力的共同点

- 都把角色、模型调用、任务、协作和业务 Harness 分层；
- 都限制 Agent 循环和运行预算；
- 都要求业务产物经过规则或 Schema 校验；
- 都不会让模型直接替代数据库事务和外部副作用管理。

### 7.4 与 MindBridge 的关键差异

MindBridge 没有 AgentScope 依赖，所以它自研了
`AgentProfile + Registry + decide/act + EventDrivenCoordinator + Blackboard`。FootOps 最初
计划直接跳到 AgentScope App/Team；用户明确项目以学习 Agent 原理为优先后，Phase 3A
改为先实现一个最小领域协议，亲自验证 Task Claim、Artifact、独立审核和 Final Accept。
该协议不包含通用 MessageBus、Scheduler 或 Storage，Phase 3B 仍要映射到 AgentScope。

对应关系是：

```text
MindBridge EventDrivenMultiAgent
  ~= AgentScope App/Team + Session + MessageBus + Task Tools
     + FootOps Workspace/Artifact/Evidence Gate

MindBridge AgentProfile/Registry
  ~= AgentScope Agent 配置 + SubAgentTemplate + Tool/Permission 配置

MindBridge CollaborationBlackboard
  ~= AgentScope TaskContext/团队消息
     + FootOps AnalysisWorkspace 的领域状态投影
```

AgentScope 负责通用运行时；FootOps 仍负责足球业务路由、强类型 Artifact、
`AnalysisWorkspace`、确定性指标、Evidence Gate 和 HTTP/SSE 契约。AgentScope 类型不会
泄露给前端，但这不意味着 FootOps 要在框架外重写消息总线和调度器。

### 7.5 版本陷阱

FootOps 锁定的是 `agentscope==2.0.5`。本地验证显示该版本没有
`agentscope.pipeline`，因此官网其他版本出现的 `Pipeline`/`MsgHub` 不能写进当前实现。

同时，包内虽有公开 `agentscope.app`，当前 `pyproject.toml` 只安装基础
`agentscope==2.0.5`，未安装 `service` extra；现在导入 App 会因缺少 `apscheduler`
失败。AgentScope App/Team 的准确状态仍是“包内能力已审计、项目尚未具备运行依赖”；
Phase 3A 领域协作层已运行不等于 App/Team 已完成。Phase 3B 先补齐并锁定 extras，再做
App 挂载集成测试。

### 7.6 阅读代码与验证

FootOps 当前实现：

- `services/agent/src/footops_agent/runtime/model_adapter.py`；
- `services/agent/src/footops_agent/agents/planner.py`；
- `services/agent/src/footops_agent/collaboration/`；
- `services/agent/src/footops_agent/agents/collaborative.py`；
- `services/agent/src/footops_agent/runtime/multi_agent.py`；
- `services/agent/tests/test_multi_agent.py`；
- `services/agent/tests/test_deepseek_adapter.py`。

本地 AgentScope 2.0.5 能力来源：

- `.venv/lib/python3.12/site-packages/agentscope/app/__init__.py`；
- `.venv/lib/python3.12/site-packages/agentscope/app/_types.py`；
- `.venv/lib/python3.12/site-packages/agentscope/app/_app.py`；
- `.venv/lib/python3.12/site-packages/agentscope/app/_service/_toolkit.py`；
- `.venv/lib/python3.12/site-packages/agentscope/app/message_bus/`；
- `.venv/lib/python3.12/site-packages/agentscope/app/storage/`；
- `.venv/lib/python3.12/site-packages/agentscope/state/` 和 `agentscope/tool/`。

```bash
.venv/bin/pytest services/agent/tests/test_deepseek_adapter.py
.venv/bin/python -c "import agentscope; print(agentscope.__version__)"
```

### 7.7 当前边界与下一步

Phase 2B 已让一个 Agent 使用 `Toolkit`/`FunctionTool`、Skill 和 `ContextConfig` 完成黄金
任务。Phase 3A 为学习目的增加最小 Registry/Board/Coordinator，但只表达 FootOps 领域
协作语义；不实现通用 MessageBus、Scheduler 或 Storage。Phase 3B 再接 App/Team、
`SubAgentTemplate`、任务工具和框架 Storage，并与 Phase 3A 做可重复对照。

## 8. Phase 2A Spike：ModelAdapter 与 DeepSeek

### 8.1 一句话理解

ModelAdapter 把“FootOps 要生成一个计划”与“具体使用 DeepSeek 还是 Mock”分开。

### 8.2 为什么需要适配层

如果 Planner 直接依赖 DeepSeek SDK，更换模型、编写离线测试或处理供应商故障时，业务
代码也必须跟着修改。现在 Planner 只依赖 `ModelAdapter` Protocol：

```text
AnalysisPlanner -> ModelAdapter
                    |- MockModelAdapter
                    `- DeepSeekModelAdapter -> AgentScope -> DeepSeek
```

### 8.3 与 MindBridge 的对比

MindBridge 的 `AiClient` 在 Ollama、OpenAI-compatible 和 Mock 之间切换，并通过
`AgentModelRegistry` 为不同角色选择模型配置。FootOps 当前 ModelAdapter 的范围更小，
只隔离结构化计划调用；未来有多个稳定角色后，才有理由增加按角色选择模型的注册表。

### 8.4 阅读代码与验证

- `services/agent/src/footops_agent/runtime/model_adapter.py`；
- `services/agent/src/footops_agent/config/settings.py`；
- `.env.example`。

验证时默认使用 Mock。真实 DeepSeek 测试必须显式配置环境变量，不能把密钥写入代码、
测试或本文档。

## 9. Phase 2A Spike：Planner 中文角色 Prompt

### 9.1 一句话理解

Prompt 定义当前 Agent 的角色和边界；Schema 定义它必须交付的结构，两者不能互相替代。

### 9.2 当前角色

当前只有 `FootOpsPlanner`，负责理解足球分析问题并生成未执行计划。Prompt 要求它：

- 使用简体中文；
- 区分用户条件、待核验事实和规划假设；
- 不编造比赛、比分、指标、来源或结论；
- 将指标写成待计算项；
- 包含数据来源、确定性计算和证据审核步骤；
- 只输出 `AnalysisPlan` Schema。

### 9.3 与 MindBridge 的对比

MindBridge 为 Understanding、Safety、Context、Response 和 Coordinator 分别设置
`AgentProfile.system_prompt`，因为这些角色已经存在并承担不同任务。FootOps 当前还没有
实现四 Agent，所以只给正在运行的 Planner 定义 Prompt。未来应在角色真正落地时分别
定义 Prompt、能力、工具白名单和 Artifact 权限，而不是提前写一批没有运行路径的文本。

### 9.4 为什么“你好”也会生成计划

当前前端调用的是显式 `/analyses/plan` 接口，Planner 又必须返回 `AnalysisPlan`，所以任何
输入都会被包装成计划。这是当前 Spike 的接口边界，不是最终聊天体验。真正解决它需要
后续消息路由；单纯改 Prompt 或隐藏字段不能产生一个不存在的直接回复。

### 9.5 阅读代码与验证

- `services/agent/src/footops_agent/prompts.py`；
- `services/agent/tests/test_prompts.py`。

```bash
.venv/bin/pytest services/agent/tests/test_prompts.py
```

## 10. Phase 2A：StatsBomb Open Data Provider

### 10.1 一句话理解

Provider 把外部数据源的原始 JSON 转换为 FootOps 自己的标准比赛数据契约。

### 10.2 为什么先做覆盖审计

黄金任务要求连续 3 至 10 场比赛。如果先选球员再假设数据存在，系统很可能在开发后期
才发现样本不完整。因此先列出赛事和比赛，再读取阵容确认球员出场，最后选择满足窗口的
真实比赛。

当前已验证 StatsBomb Open Data 中 Pedri 的历史西甲样例，并建立：

- 只读 HTTP 获取；
- 本地 Git 忽略缓存；
- URL、署名、许可和获取时间记录；
- 球员全名/昵称匹配；
- 比赛、阵容、位置和事件标准化；
- 覆盖不足和资源不存在错误。

### 10.3 与 MindBridge 的对比

MindBridge 的 ContextAgent 主要获取会话记忆、心理知识 RAG 和 Skill 上下文；FootOps 的
核心上下文首先是比赛事件数据。两者都需要把外部内容转换为内部结构并记录来源，但
FootOps 不能把比赛数据当作普通 RAG 文本，必须保留比赛 ID、事件坐标和计算口径。

### 10.4 阅读代码与验证

- `services/agent/src/footops_agent/providers/base.py`：Provider Protocol；
- `services/agent/src/footops_agent/providers/statsbomb_open.py`：数据源适配；
- `services/agent/src/footops_agent/services/data_catalog.py`：覆盖审计；
- `services/agent/src/footops_agent/cli/data_audit.py`：命令入口；
- [FOOTOPS_DATA_SOURCE_AUDIT.md](./FOOTOPS_DATA_SOURCE_AUDIT.md)：覆盖结论。

### 10.5 当前边界与下一步

当前验证的是公开历史样例，不代表拥有实时西甲或全部赛事数据。后续增加 Provider 时仍须
先做许可、覆盖和字段审计，不能让 Agent 临时抓取网页并把结果当作正式比赛数据。

## 11. Phase 2A：确定性球员角色指标

### 11.1 一句话理解

模型负责解释“这些变化可能意味着什么”，代码负责计算“数值到底是多少”。

### 11.2 当前计算链

```text
CoverageAuditArtifact
  -> MatchDataSnapshot（3 至 10 场）
  -> PlayerRoleMetricEngine
  -> MatchRoleMetrics
  -> PlayerRoleMetricArtifact
```

当前指标包括触球位置、进攻三区和禁区触球、接球位置、向前传球、推进、关键传球、
射门及射门参与等。计算只读取标准化事件，不调用模型。

### 11.3 与 MindBridge 的对比

MindBridge 的风险判断包含硬规则与模型评估，核心安全输出仍需要 SafetyAgent 审核；
FootOps 的足球数值更适合完全由确定性代码计算。未来 TacticalAgent 只能引用
`MetricArtifact`，不能重新心算或修改这些数值。

### 11.4 阅读代码与验证

- `services/agent/src/footops_agent/services/metric_engine.py`；
- `services/agent/src/footops_agent/services/player_role.py`；
- `services/agent/src/footops_agent/artifacts/metrics.py`；
- [FOOTOPS_METRIC_DEFINITIONS.md](./FOOTOPS_METRIC_DEFINITIONS.md)；
- `services/agent/tests/test_data_pipeline.py`。

```bash
.venv/bin/pytest services/agent/tests/test_data_pipeline.py
```

### 11.5 当前边界与下一步

指标已真实计算并驱动第一张前端趋势图，但尚未形成经过 Evidence Gate 的战术 Finding。
当前不能把指标存在或图表展示描述成完整战术分析已经完成。

## 12. Phase 2A：精简规划回复的前端呈现

### 12.1 一句话理解

后端保留完整结构化计划用于校验和后续处理，前端只展示适合用户阅读的模型内容。

### 12.2 为什么只修改呈现层

`AnalysisPlanResponse` 中的运行说明、结构标题、步骤编号和 `run_id` 用于表达接口状态或
工程追踪，不属于模型生成的用户内容。普通用户不需要在聊天区看到这些信息，但后端仍应
保留它们，供测试、日志和未来 Trace 使用。

当前前端按以下优先级展示：

- 有必要澄清的问题时，只展示这些面向用户的问题；
- 没有澄清问题时，只展示一句模型生成的分析意图。

前端不再追加“模型仅生成分析计划”“问题理解”“分析计划”“待确认”、步骤序号和运行
编号，也不展示 `AnalysisPlan.steps` 中供后续系统执行的内部计划。

### 12.3 与 MindBridge 的对比

MindBridge 同样区分内部 Agent Artifact、风险标签和最终学生回复，普通用户不会看到
任务板、Agent 名称或后台风险分数。FootOps 采用相同的内外分离原则，但当前仍只有
Planner；这次修改只是隐藏工程包装，没有实现 MindBridge 那样的意图路由和独立回复角色。

### 12.4 阅读代码与验证

- `apps/web/src/api/agent.ts` 中的 `formatAnalysisPlan()`；
- `apps/web/src/components/ChatView.tsx` 中的追问消息渲染。

```bash
npm run build
```

### 12.5 当前边界与下一步

当前模型仍生成 `AnalysisPlan`，不存在独立的自然对话答案字段。因此前端只能从必要澄清
问题或分析意图中选择用户可读内容；问候仍会进入 Planner。真正的直接回复需要后续消息
路由。

## 13. Phase 2A：真实 Metric Artifact 驱动前端趋势图

### 13.1 一句话理解

前端不再保存这张图的业务数值，只负责把后端返回的标准指标 Artifact 转换成可视图形。

### 13.2 当前实现

`apps/web/src/api/data.ts` 定义首批 TypeScript 业务类型并调用
`POST /api/v1/metrics/player-role`。`ChatView` 只展示样本范围和确定性数值，明确标记
“结论待审核”；`TrendChart` 从五场指标动态生成三条曲线，并对桌面和移动端使用不同
坐标布局。

### 13.3 与 MindBridge 的对比

MindBridge 把 Agent 产出的结构化结果交给 API 和前端呈现，而不是让页面复制业务判断。
FootOps 延续相同原则，但这一切片甚至不经过 Agent：确定性指标直接由 Service 生成
Artifact，避免模型或 UI 改写数值。只有后续经过 Evidence Gate 的 Finding 才能进入
战术结论区域。

### 13.4 阅读代码与验证

- `apps/web/src/api/data.ts`；
- `apps/web/src/components/ChatView.tsx`；
- `apps/web/src/components/TrendChart.tsx`；
- `apps/web/src/styles.css`。

```bash
npm run build
```

浏览器还需检查桌面与 390 px 移动端：图表完整、页面无横向溢出、控制台无错误。

### 13.5 当前边界与下一步

这一切片当时只替换了一张历史样例趋势图；随后第 13.7 至 13.10 节已经补齐 Finding、
Evidence Gate、TacticsBoardArtifact 和 SSE。这个顺序保留了“先指标、再结论、最后可视化”
的依赖关系，没有让模型直接填充证据或战术板。

### 13.6 移除原型业务 Mock

真实数据链路接通后，删除 `apps/web/src/data/mockData.ts`。比赛研究只展示黄金样例的
五场真实比赛；球员研究只展示实际完成指标计算的 Pedri；证据面板只展示后端来源与
范围；当时自动战术图层和报告显示空状态。第 13.9 节完成后，战术板改为消费真实
`TacticsBoardArtifact`，报告仍为空状态。`MockModelAdapter` 只作为离线测试替身保留，
不会向正式页面提供比赛、结论或证据数据。

### 13.7 描述性 Finding 与确定性 Evidence Gate

`DeterministicFindingBuilder` 将五场指标拆成前两场与后两场均值，只生成描述性观察，
不推断战术因果。每条 Finding 同时引用逐场 Metric Evidence 和逐场 Source Evidence。
`EvidenceGate` 再核对字段、数值、比赛集合、日期与来源 URL，输出 `supported`、
`needs_more_evidence` 或 `rejected`。

这对应 MindBridge 的 Safety 审核原则：生成者不能自行宣布输出可靠，审核必须拥有独立、
可测试的规则。区别是 FootOps 当前门禁完全由确定性代码完成；AgentScope 尚未参与
Finding 生成和证据判断。

阅读与验证：

- `artifacts/finding.py`、`artifacts/evidence.py`；
- `services/finding_builder.py`、`services/evidence_gate.py`；
- `POST /api/v1/findings/player-role/review`；
- `services/agent/tests/test_data_pipeline.py`。

100% 支持率只表示所选描述性 Finding 的引用全部通过，不表示战术角色变化已经被证明。
本切片最初覆盖三条位置 Finding，第 13.16 节扩展到十个指标；战术推断只有事件指标时
仍会被标记为 `needs_more_evidence`。

### 13.8 AnalysisWorkspace 生命周期与 Repository 基线

这一切片把原先分散返回的覆盖审计、指标、Finding、Evidence 和审核结果组合为一个
拥有稳定 `workspace_id` 的业务对象。`WorkspaceStateMachine` 只允许状态按
`created -> data_ready -> metrics_ready -> findings_ready -> evidence_reviewed -> tactics_ready`
推进，并在
每一阶段检查必需 Artifact；跨级跳转会失败。

`AnalysisWorkspaceService` 负责用现有确定性审核链创建 Workspace，
`AnalysisWorkspaceRepository` Protocol 定义保存和查询边界，当前
`InMemoryAnalysisWorkspaceRepository` 使用锁和防御性深拷贝，避免并发访问或调用方修改
返回对象时污染已保存状态。FastAPI 提供：

- `POST /api/v1/analyses` 创建工作区；
- `GET /api/v1/analyses/{workspace_id}` 查询工作区。

前端不再把 Finding Review 响应当成页面的长期状态，而是直接消费
`AnalysisWorkspace`。查询接口保留按 `workspace_id` 读取的服务端边界；当前前端每次打开
保持空白，不会自动恢复或创建 Pedri 问答，只有用户主动提交后才创建 Workspace。

这对应 MindBridge 用 Harness 统一管理报告、消息和 trace 落库的原则：聊天文本不是唯一
状态，业务产物必须能独立保存和恢复。当前差异是 FootOps 只建立进程内基线，尚未实现
SQLAlchemy/MySQL、Checkpoint、运行 trace 或跨进程恢复。

阅读与验证：

- `artifacts/workspace.py`；
- `services/workspace.py`；
- `repositories/analysis_workspace.py`；
- `api/main.py`、`api/schemas.py`；
- `services/agent/tests/test_workspace.py`；
- `apps/web/src/api/data.ts`、`apps/web/src/App.tsx`。

```bash
.venv/bin/pytest services/agent/tests/test_workspace.py
npm --prefix apps/web run build
```

这一步证明的是 Workspace 接口和生命周期边界，不代表数据库持久化已经完成。API 进程
重启后内存数据会消失，后续 SQL Repository 必须复用同一个 Protocol 和 HTTP 契约。

### 13.9 TacticsBoardArtifact 与证据约束

`DeterministicTacticsBoardBuilder` 把已审核 Finding 映射为版本化
`TacticsBoardArtifact`。当前黄金任务只绘制前段/后段平均触球区域、后段位置标记和位置
变化箭头；每一个图层都必须携带 `finding_refs`，整个 Artifact 同时保存
`evidence_refs`。若平均触球位置 Finding 未通过 Evidence Gate，Builder 会拒绝生成战术板。

这延续 MindBridge 的 Artifact 协作和 Safety 审核原则，但当前没有 TacticalAgent：战术板
由确定性 Service 生成，避免模型根据稀疏事件数据编造阵型、传球线路或因果解释。前端只
负责确定性渲染与本地编辑，重置操作会恢复审核后的原始图层。

阅读与验证：

- `artifacts/tactics.py`；
- `services/tactics_board.py`；
- `artifacts/workspace.py`、`services/workspace.py`；
- `apps/web/src/components/TacticsBoard.tsx`；
- `services/agent/tests/test_workspace.py`。

### 13.10 空白首屏与分析 SSE

产品首屏不再自动展示预置 Pedri 问答。用户输入问题后，前端调用
`POST /api/v1/analyses/stream`，依次消费版本化的 `analysis.status` 和
`analysis.completed`，失败时消费 `analysis.error`。事件 Schema 位于
`contracts/events/analysis-stream-event.schema.json`。

这类 SSE 是业务生命周期流，不是模型 token 流。Phase 2A 的分析仍由确定性 Service
执行；Phase 2B 才会在同一稳定事件边界内增加工具选择、Evidence Gate 和停止原因等
Agent 事件。这样未来 Java 后端或其他前端可以只依赖 HTTP/SSE 契约，不依赖 AgentScope
内部对象。

### 13.11 问题范围路由与相关 Finding 选择

最初的 Workspace Service 接收了 `question`，却没有让问题参与执行选择，因此任何输入
都会运行同一套固定黄金样例。`PlayerRoleQuestionRouter` 现在先验证球员和受支持意图，
再从位置/触球、向前传球、推进带球、关键传球和射门参与对应的 Finding 中选择相关结果。
Evidence、Review、趋势图和战术板随后只消费被选中的结果。

这不是 LLM 意图识别，而是 Phase 2A 的确定性产品边界：无法执行的问题返回
`unsupported_analysis_question`，不能为了维持聊天体验而套用固定答案。Phase 2B 可让
Agent 负责澄清和工具选择，但仍必须受这个可执行能力集合约束。

通用球员数据接入后又补充了正常用户问法回归：“分析最近几场表现”“最近踢得怎么样”
和“看看近期活动趋势”映射到六项代表性综合观察；明确询问进球、助攻、xG、射正、防守
和评分等尚未接入指标时仍拒绝执行。这个规则避免两种错误：路由过窄导致所有自然问法
失败，以及路由过宽导致所有问题都复用同一组结果。

阅读与验证：

- `services/question_scope.py`、`services/workspace.py`；
- `api/main.py` 的同步与 SSE 错误映射；
- `apps/web/src/components/ChatView.tsx`、`TrendChart.tsx`；
- `services/agent/tests/test_workspace.py`。

### 13.12 通用球员目录与按需事件读取

最初前端把赛事、赛季、Pedri 和五场窗口写在请求体中，Provider 虽然可以按姓名查找，
产品链路仍只能表现为固定样例。本切片新增赛事目录和球员目录接口：球员目录只聚合
lineup 中的规范球员 ID、姓名、球队、出场数和日期范围，不预下载所有球员事件。用户
提交分析后，Provider 才读取所选 3 至 10 场的比赛事件文件，再按规范球员 ID 过滤并
交给确定性指标引擎。StatsBomb Open Data 的文件粒度是整场比赛，不支持按球员单独下载，
但系统不会因此预下载整个赛季或所有球员事件。

这与 MindBridge 先解析业务实体、再按需检索领域数据的原则一致，但比赛事件不是 RAG：
它是结构化、可计算、随比赛增长的数据，应通过 Provider/API 精确查询；RAG 后续只保存
相对稳定的战术知识、指标定义和分析规范。

阅读与验证：

- `providers/base.py`、`providers/statsbomb_open.py`；
- `services/data_catalog.py`；
- `api/schemas.py`、`api/main.py`；
- `apps/web/src/api/data.ts`、`App.tsx`、`components/ChatView.tsx`；
- `services/agent/tests/test_data_pipeline.py`、`test_workspace.py`。

真实验收中，西甲 2020/21 目录解析出 383 名有出场记录的球员，并使用 Lionel Messi
最近三场完成事件读取、指标计算、Finding 和 Evidence Gate 链路。当前边界是 StatsBomb
Open Data 没有中文别名和全局球员搜索 API；输入任意中文译名或查询开放数据未覆盖的
球员仍会明确失败。

### 13.13 自然语言单 Agent、Toolkit 与 Skill

Phase 2B 的首个切片不再要求用户先填写赛事和球员。`FootOpsAnalysisAgent` 使用
AgentScope 2.0.5 内置 ReAct 有限循环，先读取 `footops-player-role-analysis` Skill，
再从请求级 Toolkit 中选择赛事检索、球员解析和确定性分析工具。赛事 ID、赛季 ID 和
球员 ID 必须来自用户可选约束或工具结果；候选不唯一时返回结构化补问，不能靠模型
记忆猜测。分析完成状态还必须由 Harness 核对真实 Workspace，模型单独声称完成无效。

这对应 MindBridge 的 Runtime Harness、业务 Skill 和工具后处理思想，但当前保持单
Agent：Agent 负责理解与调度，现有 Service 负责指标、Finding、Evidence Gate、战术板
和 Workspace。前端携带最近六轮短期历史，使用户可以直接回答 Agent 的范围补问；
数据库会话记忆仍未实现；请求级上下文预算与压缩配置见下一节。

阅读与验证：

- `runtime/analysis_agent.py`、`tools/analysis.py`；
- `skills/player_role_analysis/SKILL.md`；
- `harness/analysis.py`、`api/main.py` 的 `/api/v1/agent/runs`；
- `apps/web/src/App.tsx`、`api/data.ts`、`components/ChatView.tsx`；
- `services/agent/tests/test_workspace.py`。

### 13.14 Agent 业务事件、状态与上下文预算

自然语言入口新增 `/api/v1/agent/runs/stream`。它发送 `agent.started`、逐次
`agent.tool.completed`，以及 completed、clarification、unsupported 或 error 最终事件。
`AgentToolContext` 在记录业务 Trace 时同步通知 Harness 事件队列，因此前端可以展示真实
工具进度，而不消费 AgentScope 私有 Message 或模型思维过程。同步 POST 入口继续保留，
方便自动化调用和故障排查。

每次执行显式创建独立 `AgentState`，并配置 `ContextConfig`：75% 触发压缩、15% 保留、
工具结果上限 12000 token。压缩 Prompt 只保留用户范围、工具核验结果、Workspace ID 和
待解决问题，禁止补入模型记忆。前端目前携带最近六轮历史；服务端数据库 Session、跨
刷新恢复和压缩触发压力测试仍待实现。

本切片还修复了中文全自然语言请求的 502：中文姓名需要一次转写重试，6 次 ReAct 预算
不足以完成 Skill、四次工具动作和结构化输出，因此上限最终调整为 10。若工具已生成可信
Workspace 但模型只耗尽格式化预算，Runtime 从 Workspace 构造完成 Decision；无
Workspace 时仍失败，不能把不完整运行伪装成成功。

阅读与验证：

- `runtime/analysis_agent.py`、`harness/analysis.py`、`tools/analysis.py`；
- `api/schemas.py` 的 `AgentRunStreamEvent` 与 `api/main.py` 的流式入口；
- `contracts/events/agent-run-stream-event.schema.json`；
- `tests/test_deepseek_adapter.py`、`tests/test_workspace.py`。

### 13.15 黄金任务评测 Harness

新增 `footops-player-role-v1` 黄金任务评测集，第一批验证完整范围执行、自然语言范围解析、
缺少赛事补问、越界指标拒绝和未知球员补问。同一套期望行为依次交给确定性直调、无工具
直接 LLM 和当前 AgentScope 单 Agent，报告记录状态、Workspace、工具序列、证据支持率、
耗时、Token、停止原因和错误类型。费用只接受运维配置的每百万 Token 单价，不在代码中
固化可能变化的供应商价格。

首次评测暴露出 scope_hint 与 Skill 的规则冲突，以及中文姓名重试耗尽 8 次循环预算。
统一规则、增强赛事自然语言匹配并把有限上限调整为 10 后，真实结果为：确定性直调
4/5、直接 LLM 2/5、单 Agent 5/5。随后增加向前传球、推进带球和射门参与三个业务任务，
第二批真实结果为确定性直调 7/8、直接 LLM 2/8、单 Agent 8/8。单 Agent 工具序列正确率
和已生成结论的证据支持率均为 100%。这证明当前 Harness 对已声明任务有价值，但并不
证明多 Agent 会更好。

阅读与验证：

- `evaluation/models.py`、`evaluation/runners.py`、`evaluation/service.py`；
- `runtime/direct_llm.py`、`runtime/usage.py`；
- `data/evaluation/player-role-v1.json`；
- `python -m footops_agent.cli.evaluate`；
- `tests/test_evaluation.py`。

### 13.16 业务 Finding 扩展与用户范围优先级

指标引擎此前已经计算传球、推进和进攻参与数据，但 Finding Builder 只消费三个位置指标，
所以“指标存在”并不等于 Agent 能回答对应问题。本切片为禁区触球、向前传球、成功向前
传球、推进带球、关键传球、射门和射门参与补齐确定性 Finding、Evidence 与问题路由，
总覆盖达到 10 个指标。宽泛问题选择 6 个代表性观察，具体问题只保留相关 Finding，避免
回答既固定又冗长。前端趋势图使用“位置 / 推进进攻”分段模式，不把坐标、比例和次数混在
同一纵轴语义中。

浏览器联调还暴露了一个 Harness 外的产品边界错误：用户明确写“最近三场”，但前端默认
发送 `requested_window=5`，导致 Agent 合理地服从了错误 hint。修复后，赛事和窗口默认由
Agent 从自然语言解析，只有用户主动选择筛选项时才发送约束。这说明边界管理不仅在 Prompt
和 Tool 中，也包括 UI 产生的结构化输入；用户明确意图与默认控件冲突时，默认值不能静默
覆盖用户文本。

次数类 Finding 仍是场均次数，尚未按出场分钟或球队控球时间归一化；射门参与只是射门与
关键传球之和。它们可以支持样本内描述性比较，不能直接写成战术因果或完整贡献评价。

阅读与验证：

- `services/finding_builder.py`、`services/question_scope.py`；
- `skills/player_role_analysis/SKILL.md`、`prompts.py`；
- `apps/web/src/components/TrendChart.tsx`、`ChatView.tsx`、`App.tsx`；
- `data/evaluation/player-role-v1.json`；
- `tests/test_data_pipeline.py`、`tests/test_workspace.py`、`tests/test_evaluation.py`。

### 13.17 Phase 3A：MindBridge 风格事件驱动多 Agent

项目定位重新确认后，开发主线从继续增加足球指标切换为学习多 Agent 编排。代码级走读
MindBridge 的 `events.py`、`registry.py`、`coordinator.py`、`autonomous.py`、
`event_driven_runtime.py` 和对应测试后，FootOps 建立了最小协作协议：不可变 Board 保存
Task、Artifact 和 Event；Coordinator 根据缺失 Artifact 创建任务；Worker 按 capability
和当前 Board 状态 claim；EvidenceAgent 独立审核；Coordinator 只在审核通过且必要战术
投影完成后接受 Workspace。

当前角色是 CoordinatorAgent、DataAgent、TacticalAgent 和 EvidenceAgent。综合角色问题
的真实 claim 顺序为 Data -> Tactical(findings) -> Evidence(review) -> Tactical(tactics)；
只询问向前传球时不会创建 tactics 任务，因此它不是写死的四函数流水线。轮次不足会产生
`BUDGET_EXHAUSTED`，Runtime 不会返回伪成功。

第一版 Worker 故意先复用确定性领域服务，不让模型质量掩盖编排错误。独立 API
`POST /api/v1/multi-agent/analyses` 返回 Workspace 和脱敏协作 Trace。加入普通问候后的
四模式九任务结果为：确定性 7/9、直接 LLM 3/9、单 Agent 9/9、多 Agent 8/9；多 Agent
唯一失败是无结构化 scope hint 的自然语言问题，因此后续新增 ScopeAgent，而不是继续
堆指标；完成结果见 13.20 节。

与 MindBridge 相比，当前尚无 Agent Message、私有记忆、critique/revision、并发 claim、
Checkpoint 和持久化 Trace；也尚未接入 AgentScope App/Team。完整映射和学习路线见
[FOOTOPS_MULTI_AGENT_LEARNING.md](./FOOTOPS_MULTI_AGENT_LEARNING.md)。

阅读与验证：

- `collaboration/events.py`、`registry.py`、`coordinator.py`；
- `agents/collaborative.py`、`runtime/multi_agent.py`；
- `tests/test_multi_agent.py`；
- `data/evaluation/reports/phase3-latest.json`。

### 13.18 入口意图路由与 ConversationAgent

MindBridge 会先判断请求是否需要业务 Agent，普通交流不应启动整个协作 Runtime。FootOps
因此在 `FootOpsAnalysisHarness` 前加入 `RequestIntentRouter`：问候和普通足球交流进入
无工具 `ConversationAgent`，分析意图才进入原有单 Agent 数据链。多 Agent 评测入口复用
同一 Router，避免不同运行模式出现不一致的产品边界。

普通回复仍由 AgentScope `Agent` 和 DeepSeek 生成，但不给它注册数据工具，也不创建
Workspace。API 返回 `status=chat`、`data_retrieved=false` 和空 trace；前端显示普通对话
标签，不再渲染“0 条观察”或证据区域。入口 Router 与后续 ScopeAgent 不重复：前者回答
“要不要分析”，后者只在分析分支回答“分析谁、哪个赛事、哪个赛季、多少场”。

验证结果：真实 DeepSeek 问候调用通过，浏览器中输入“你好”得到普通回复；全套 62 项
测试、Ruff 和前端生产构建通过。九任务结果为确定性 7/9、直接 LLM 3/9、单 Agent 9/9、
多 Agent 8/9。

阅读与验证：

- `services/intent_routing.py`、`runtime/chat_agent.py`、`harness/analysis.py`；
- `api/main.py`、`api/schemas.py`；
- `apps/web/src/components/ChatView.tsx`；
- `tests/test_intent_routing.py`、`tests/test_workspace.py`。

### 13.19 战术知识与联合推理方向校准（仅设计，尚未实现）

当前十项指标和两类趋势图证明了 Provider -> Metric -> Finding -> Evidence -> Workspace
纵向链路，但 TacticalAgent 仍主要组合确定性 Finding，尚未形成“提出假设、检索战术知识、
检查反例、接受 critique、有限修订”的战术推理循环。项目需求因此明确：现有指标是可测试
基线，不是最终能力边界。

目标入口不再只有 chat/analysis 二分类，而是生成 ExecutionPlan，分别表达是否需要比赛
数据、IFAB/FIFA 规则、战术知识、案例模板和多 Agent。比赛事实继续由 Data Provider
获取；规则、战术概念、已授权案例、指标口径和分析模板进入 Knowledge RAG。复杂问题由
DataAgent 与规划中的 KnowledgeAgent 分别提供证据，TacticalAgent 发布结构化战术假设，
EvidenceAgent 检查数据引用、知识引用和推断边界后触发接受、修订、降级或拒绝。

这次只修改需求、架构和开发顺序，没有新增 RAG、KnowledgeAgent 或战术推理代码。后续
必须先用黄金任务验证检索正确性、引用正确性和联合分析收益，再宣称系统具备该能力。

### 13.20 ScopeAgent：先确认分析对象，再启动协作

原多 Agent Runtime 只能接收显式 competition_id、season_id、player_id 和窗口，因此自然
语言黄金任务失败。现在新增独立 `FootOpsScopeAgent`：它是 AgentScope ReAct 角色，但工具
权限只有 `search_competitions` 和 `search_players`，不能读取事件、计算指标或生成 Finding。
其 `ScopeResolutionArtifact` 在 `resolved` 状态下必须包含完整赛事、球员和窗口。

模型输出不能直接成为可信 ID。目录工具把唯一赛事和球员候选保存在请求级 Context，Runtime
会用候选覆盖模型输出；如果 ID 既不来自 scope hint，也不来自工具唯一候选，则降级为
clarification。解析完成后 `FootOpsMultiAgentHarness` 才构造 `MultiAgentAnalysisRequest`，
启动原有 CollaborationBoard。显式范围调试接口继续保留，自然语言入口新增为
`POST /api/v1/multi-agent/runs`。

真实 DeepSeek 黄金任务顺序为 search_competitions -> search_players -> DataAgent ->
TacticalAgent -> EvidenceAgent -> TacticalAgent，最终由 Coordinator 接受 Workspace。
ScopeAgent 后的多 Agent 九任务 `9/9`，平均 `3361.8 ms`，Token 共 `25716`；全套测试
`67 passed`。这也修正了旧基线中多 Agent `0 Token/约 70 ms` 的含义：旧数据只测了范围
已知后的协作协议，新数据包含真实范围解析成本。

阅读与验证：

- `artifacts/scope.py`、`runtime/scope_agent.py`、`harness/multi_agent.py`；
- `tools/analysis.py`、`api/main.py`、`api/schemas.py`；
- `tests/test_scope_agent.py`；
- `data/evaluation/reports/phase3-scope-agent-latest.json`。

### 13.21 ExecutionPlan：数据和知识需求不再互斥

旧 `RequestIntentRouter` 只输出 chat/analysis，无法表达规则问答不需要比赛数据、战术原因
分析同时需要比赛数据与战术知识。现在新增 `ExecutionPlanArtifact`，用独立布尔字段声明
`need_match_data`、`need_rule_rag`、`need_tactical_rag`、`need_multi_agent` 和
`scope_required`，并区分 chat、rule_qa、tactical_knowledge、data_analysis、
hybrid_tactical_analysis 五类意图。

Harness 已消费该计划。普通问候仍进入 ConversationAgent；纯数据问题进入现有分析链；
规则、战术知识和联合分析由于 Knowledge RAG 尚未实现，会直接返回 unsupported，不启动
ScopeAgent、比赛数据工具或模型回答。这样“主动触球”的规则含义不会因为包含“触球”二字
误触发球员指标链，也不会把模型常识伪装成已检索规则。

全套测试增至 `71 passed`。本切片只完成路由和能力门禁；Knowledge RAG、知识引用和
KnowledgeAgent 仍是下一阶段，不能把 unsupported 状态描述为已经具备规则问答能力。

阅读与验证：

- `artifacts/execution_plan.py`、`services/intent_routing.py`；
- `harness/analysis.py`、`harness/multi_agent.py`；
- `tests/test_intent_routing.py`、`tests/test_scope_agent.py`。

### 13.22 Knowledge RAG 规则纵向链与 KnowledgeAgent

ExecutionPlan 能识别规则问题后，项目新增第一条真实知识链。首批语料不是比赛事件，也不是
模型自行总结的实时内容，而是基于 IFAB Laws of the Game 2026/27 建立的版本化中文释义
条目。每条记录保存知识域、规则章节、发布机构、版本、生效日期、官方 URL 和内容形式；
当前释义明确标记为 `paraphrase`，不把二次整理冒充规则原文。

检索采用 `BM25 + 字符 n-gram 稀疏向量 + 确定性 rerank`。这让最小切片不依赖额外
Embedding 服务，组件分数和排序可重复测试；代价是跨语言语义召回有限。因此当前实现是
混合检索与 Artifact 契约的工程基线，不是生产级 dense semantic RAG。规则查询会发布
`KnowledgeEvidenceArtifact`，其中包含可解析的 evidence ID 和来源元数据。

`FootOpsKnowledgeAgent` 是 AgentScope ReAct 角色，只有只读 `search_knowledge` 工具。
Harness 控制允许检索的知识域，模型不能自行扩大范围。回答必须输出
`KnowledgeAnswerArtifact` 并引用工具返回的 ID；Runtime 会删除越界引用，无有效引用时
使用已检索证据生成受控降级答案。纯规则问题不会启动 ScopeAgent、比赛 Provider 或
CollaborationBoard。当前尚无战术知识语料，纯战术概念返回 insufficient；数据 + 知识联合
问题仍返回 unsupported，等待 KnowledgeAgent 接入 Board 和 TacticalHypothesis 修订循环。

验证结果：规则“主动触球”检索将 Law 11 deliberate play 排在首位；规则 API 返回
`status=completed`、`data_retrieved=false` 和可回溯引用；战术知识域缺失时拒绝使用模型
记忆补齐。全套测试增至 `77 passed`。

阅读与验证：

- `artifacts/knowledge.py`、`rag/corpus.py`、`rag/retrieval.py`；
- `tools/knowledge.py`、`runtime/knowledge_agent.py`、`harness/analysis.py`；
- `tests/test_knowledge_rag.py`；
- `contracts/artifacts/knowledge-evidence.schema.json`、
  `contracts/artifacts/knowledge-answer.schema.json`。

### 13.23 Redis Vector RAG 与两场球员报告

此前的知识检索只在 Python 进程内计算 BM25 与字符 n-gram 相似度，既没有真实语义
Embedding，也没有向量库。当前 RAG 仍只索引规则条目、战术概念和指标口径；StatsBomb
比赛事件及其确定性指标留在 Provider/Workspace 链，不写入知识向量库。

FootOps 使用确定性的字符 n-gram 哈希生成固定维度特征向量，通过 Redis 8 Vector Sets 的
`VADD`/`VSIM` 保存并召回语料；同一 Redis 中还持久化知识正文、关键词、版本和来源元数据。
`RedisVectorKnowledgeIndex` 按语料指纹惰性同步，检索时从 Redis 读回知识条目，再按知识域
过滤并用 BM25、向量分数和关键词加权重排，最终输出可追溯的 `KnowledgeEvidenceArtifact`。
该向量不是模型生成的语义 Embedding，跨表达、同义词和跨语言召回能力有限。Redis 不可用时
KnowledgeAgent 返回证据不足，不回退进程内语料，也禁止模型仅凭记忆回答。

入口遵循 MindBridge 的“先计划、按能力调用”方式：`ExecutionPlan` 判断是否需要规则、战术
或指标知识；纯知识问题由 `KnowledgeAgent` 调用受限域的只读 `search_knowledge` 工具；数据与
战术联合问题由 Board 中的 `KnowledgeAgent` 使用相同 Redis 知识库补充证据；普通问候不触发
知识检索。`rag/corpus.py` 是版本化的受控知识源/首次同步种子，不是运行时的本地检索后备。

边界：这里的“全部检索知识”指当前规则条目、战术概念和指标口径。StatsBomb 比赛事件是有结构
的事实数据，仍由 Provider/Workspace 获取与分析，不应伪装成 RAG 文档塞进向量库。当前语料
13 条，后续新增案例或模板时应走同一 Redis 同步和来源元数据契约。

数据链同时放宽为两场起：每场先单独算指标，FindingBuilder 对比第 1 场和第 2 场，并经过
原来的 Evidence Gate 校验数值、比赛 ID、时间范围和来源。联合分析报告展示审核通过的变化，
再附上检索到的战术概念作为看录像的参考；两场数据不支持单独断言战术角色改变或因果关系。

实现入口：

- `rag/redis_vector.py`、`rag/retrieval.py`、`config/settings.py`；
- `agents/collaborative.py`、`runtime/multi_agent.py`、`harness/analysis.py`；
- `services/finding_builder.py`、`services/data_catalog.py`、`services/workspace.py`；
- `api/main.py`、`api/schemas.py`、`skills/player_role_analysis/SKILL.md`。

验证：Redis `VADD`/`VSIM` 与知识 Hash 读写、检索路由测试、Ruff 和 Python 编译均通过；
当前 Redis 索引版本为 `char-ngram-v2`。尚未添加授权比赛案例、战术模板、离线检索评测集
或自动化的向量版本迁移工具。

### 13.24 逐场表现问答、xG 与追问范围

此前用户问“哪场发挥最好”时，普通分析链虽然运行 `FootOpsAnalysisAgent` 并生成 Workspace，
但 `run_player_role_analysis` 只把完成状态回给模型，没有提供每场日期、对手和可比较指标。
模型因此只能复述汇总 Finding，无法回答哪一场射门或参与最高。

现在分析工具把已解析 Workspace 的逐场事实作为结构化 `match_facts` 返回给 ReAct Agent，
包括日期、对手、球员视角比分、射门、xG、射门参与、关键传球、推进带球、来源 ID 和指标引用。
System Prompt 要求模型基于这些事实逐场比较，区分射门数、xG 和射门参与；“发挥最好”没有
唯一口径时不得编造综合评分。Mock Runtime 也提供确定性逐场比较回答，便于无密钥环境验证。
前端使用 `react-markdown` 和 GFM 插件渲染回答，不再把 Markdown 源文本塞进普通段落；标题、
列表、行内强调和表格分别排版。System Prompt 鼓励用小标题与列表，避免宽表格及长段落。
逐场事实另由前端从 Workspace 指标生成表格，包含日期、对手比分、射门、xG、射门参与、关键
传球、向前传球、推进带球和平均触球位置；现有趋势图接在表格之后，Agent 评论排在数据可视化之后。

StatsBomb Provider 从 Shot detail 解析 `statsbomb_xg`，MetricEngine 对球员每场射门 xG 求和，
FindingBuilder 和图表按需展示 xG。若一场比赛任一射门缺少 xG，该场 xG 为 `null`，而不是估算
或补零；只有完整样本可形成跨场 xG Finding。前端 xG 图单独使用 xG 轴，不与射门次数混用刻度。
宽泛问题仍只挑六项代表指标，xG 需用户明确询问。

前端对“哪场”“这几场”“xG”等省略追问复用上一个分析 Workspace 的赛事、赛季、球员和窗口；
界面当前显式选择仍优先。后端 Intent Router 结合近期对话识别追问为分析，而不是误判成普通聊天。
该记忆只在当前前端会话中传递最近对话和工作区范围，不是跨设备长期记忆。

实现入口：`providers/statsbomb_open.py`、`services/metric_engine.py`、
`services/finding_builder.py`、`tools/analysis.py`、`runtime/analysis_agent.py`、
`services/intent_routing.py`、`apps/web/src/App.tsx` 和 `TrendChart.tsx`。

验证：全套 Python 测试、Ruff 和 Web 生产构建通过；回归测试断言 xG 逐场最大值回答包含日期、
对手、数值和来源引用。当前仍是单球员、多场事件分析，不代表整场 xG、射正、进球、射门质量
或无球战术分析；真实 StatsBomb 样本的 xG 覆盖率仍需进一步抽样核验。

## 14. 当前完整认识

目前已经存在自然语言 Agent 入口、计划入口、一条确定性审核链和完整工作区生命周期：

```text
LLM 规划链：问题 -> Planner -> AnalysisPlan
Agent 执行链：问题/历史 -> AgentScope ReAct -> Skill -> Tools -> Workspace/补问
真实数据链：范围 -> Provider -> Snapshot -> MetricArtifact
审核链：MetricArtifact -> FindingSet -> EvidenceSet -> EvidenceReview
战术板链：受支持 Finding -> TacticsBoardArtifact
工作区链：Request + 审核产物 + 战术板 -> AnalysisWorkspace -> SSE/Repository
```

规划链只制定计划；Agent 执行链会在受控工具边界内读取比赛数据。真实 MetricArtifact
驱动图表、最多 11 个描述性 Finding、逐场问答、证据面板和战术板。当前有 `FootOpsPlanner`、
`ConversationAgent`、`FootOpsAnalysisAgent` 和 `FootOpsKnowledgeAgent` 等角色，并已实现
Phase 3A 四角色事件驱动协作；前置 ScopeAgent 已接入自然语言多 Agent Harness。
AgentScope App/Team 仍未接入默认业务链。Redis Vector RAG 支持规则、战术概念和指标定义；
下一步是加入授权案例与模板，并用可复现评测验证检索收益，再继续 App/Team 事件投影。

## 15. 后续学习目录

以下章节只列学习顺序，不代表已经实现。完成对应切片后，必须按第 2 节模板补写正文。

1. [x] 实现 ScopeAgent 与自然语言范围解析；
2. [x] 将入口升级为可组合的 ExecutionPlan；
3. [部分完成] 建立规则、战术知识、案例和指标口径 Knowledge RAG；规则切片已完成；
4. [部分完成] 增加 KnowledgeAgent、KnowledgeEvidenceArtifact 和
   TacticalHypothesisArtifact；前两项已完成，TacticalHypothesis 待补；
5. 增加 critique/revision 有限返工循环；
6. 增加多 Agent SSE 和前端用户态进度；
7. 安装 AgentScope `service`/Storage extras，完成 App/Team 集成 Spike；
8. 用 `SubAgentTemplate`、任务工具、团队消息和 MessageBus 实现有限协作循环；
9. 将框架 Session/Task/Event 映射为 Workspace/Artifact/SSE；
10. 增加故障、恢复和单/多 Agent 对照评测；
11. 实现 Checkpoint、取消、局部重算、数据库持久化和队列；
12. 建立完整 Engineering Harness；
13. 根据实测结果决定默认运行模式；
14. 业务价值成立后再评估 Java 平台。

## 16. 维护规则

1. 严格按照实际开发顺序追加，不为了文档完整提前宣称能力；
2. 每节必须同时写 FootOps 作用和 MindBridge 对照；
3. 对照必须区分“共同原则”“实现差异”和“FootOps 为什么这样选择”；
4. 每节必须提供代码入口和至少一种可重复验证方式；
5. 每节必须写当前边界，避免学习者把局部切片理解成完整系统；
6. 代码、契约或开发顺序改变时，同步修订对应学习章节；
7. 每完成一个可运行切片，同时更新本手册、当前进度和开发顺序清单。
