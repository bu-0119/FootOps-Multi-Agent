# FootOps 按开发顺序学习手册

> 文档状态：持续更新
> 建立日期：2026-07-31
> 当前学习进度：Phase 2A 已完成，下一章进入 Phase 2B 单 Agent MVP
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

MindBridge 使用通用 `AgentArtifact(kind, payload)` 在黑板上传递产物，适合承载不同心理
支持任务；FootOps 当前优先使用足球领域的强类型 Artifact，因为指标字段、单位、来源和
比赛范围必须被程序校验。未来多 Agent 可以在黑板上传递这些 Artifact，但不会退化为
只有模型才能理解的自由文本。

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

## 7. Phase 2A Spike：AgentScope 2.0.5

### 7.1 一句话理解

AgentScope 当前为 FootOps 提供模型 Agent、有限 ReAct 循环和结构化输出能力，但不负责
FootOps 的业务数据、指标真实性和最终证据审核。

### 7.2 为什么接入 AgentScope

直接调用模型 API 只能得到一次文本补全。后续单 Agent 需要在有限预算内理解问题、选择
Skill、调用只读工具并根据工具结果生成结构化产物。AgentScope 提供统一 `Agent`、
`ReActConfig`、`reply()`/`reply_stream()`、结构化 Schema 和 Toolkit 接口，可以减少重复
实现模型循环的工作。

当前 Spike 只验证：

```text
AnalysisPlanner
  -> AgentScope Agent
  -> DeepSeekChatModel
  -> structured_schema=AnalysisPlan
  -> Pydantic 校验
```

### 7.3 与 MindBridge 同类能力的共同点

- 都把 Agent 角色、模型调用和业务 Harness 分层；
- 都限制 Agent 循环和运行预算；
- 都要求模型输出经过业务规则或 Schema 校验；
- 都不会让模型直接替代数据库事务和外部副作用管理。

### 7.4 与 MindBridge 的关键差异

MindBridge 没有使用 AgentScope 作为核心 Runtime。它使用自研的
`AgentProfile + Registry + decide/act + EventDrivenCoordinator + Blackboard` 完成多 Agent
认领和调度，并通过自己的 `AiClient` 调用模型。

FootOps 的设计是：

- 使用 AgentScope 处理单个 Agent 内部的模型推理、结构化输出和未来工具调用；
- 使用 FootOps 自己的 Harness、路由、Artifact 和未来 Blackboard 管理足球业务；
- 不让 AgentScope 类型泄露到 HTTP 或前端；
- 不照搬 MindBridge 的自研模型循环，也不把 AgentScope 当成完整业务系统。

因此，“接入 AgentScope”不等于“已经完成多 Agent”，也不等于“已经完成真实分析”。

### 7.5 阅读代码与验证

- `services/agent/src/footops_agent/runtime/model_adapter.py`；
- `services/agent/src/footops_agent/agents/planner.py`；
- `services/agent/tests/test_deepseek_adapter.py`。

```bash
.venv/bin/pytest services/agent/tests/test_deepseek_adapter.py
```

### 7.6 当前边界与下一步

目前 AgentScope Agent 只生成计划，尚未注册足球数据 Tool、指标 Tool 或 Skill。必须先
完成 Phase 2A 的确定性数据链，再在 Phase 2B 让 Agent 选择这些只读能力。

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

当前 100% 支持率只表示三条描述性 Finding 的引用全部通过，不表示战术角色变化已经
被证明。战术推断只有事件指标时会被标记为 `needs_more_evidence`。

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

## 14. 当前完整认识

目前已经存在两条入口、一条确定性审核链和一个完整的 Phase 2A 工作区生命周期：

```text
LLM 规划链：问题 -> Planner -> AnalysisPlan
真实数据链：范围 -> Provider -> Snapshot -> MetricArtifact
审核链：MetricArtifact -> FindingSet -> EvidenceSet -> EvidenceReview
战术板链：受支持 Finding -> TacticsBoardArtifact
工作区链：Request + 审核产物 + 战术板 -> AnalysisWorkspace -> SSE/Repository
```

前者会调用模型但不取比赛数据；后者会读取真实比赛数据但不调用模型。真实 Metric
Artifact 已经驱动图表、描述性 Finding、证据面板和可编辑战术板。Phase 2A 已完成；
当前仍只有一个用于规划 Spike 的 `FootOpsPlanner`，目录中的 collaboration、tools、skills
等包不代表多 Agent 已实现。Phase 2B 才会把只读数据与指标能力注册为 Agent Tools。

## 15. 后续学习目录

以下章节只列学习顺序，不代表已经实现。完成对应切片后，必须按第 2 节模板补写正文。

1. 将数据与指标服务注册为 AgentScope 只读 Tools；
2. 建立球员角色分析 Skill；
3. 完成单 Agent 黄金任务；
4. 建立直接 LLM 与单 Agent 评测基线；
5. 仅在评测证明需要时提取 Coordinator、Data、Tactical、Evidence 角色；
6. 实现 AnalysisBlackboard 和有限协作循环；
7. 实现 Checkpoint、取消、局部重算、数据库持久化和队列；
8. 建立完整 Engineering Harness；
9. 根据实测结果决定是否保留多 Agent；
10. 业务价值成立后再评估 Java 平台。

## 16. 维护规则

1. 严格按照实际开发顺序追加，不为了文档完整提前宣称能力；
2. 每节必须同时写 FootOps 作用和 MindBridge 对照；
3. 对照必须区分“共同原则”“实现差异”和“FootOps 为什么这样选择”；
4. 每节必须提供代码入口和至少一种可重复验证方式；
5. 每节必须写当前边界，避免学习者把局部切片理解成完整系统；
6. 代码、契约或开发顺序改变时，同步修订对应学习章节；
7. 每完成一个可运行切片，同时更新本手册、当前进度和开发顺序清单。
