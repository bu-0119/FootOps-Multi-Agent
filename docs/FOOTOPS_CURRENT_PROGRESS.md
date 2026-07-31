# FootOps 当前开发进度

> 文档状态：持续更新
> 最后更新：2026-07-31
> 当前里程碑：Phase 2A 已完成，下一阶段为 Phase 2B 单 Agent MVP
> 用途：新会话接手项目时的第一份状态文档

## 1. 三十秒了解当前状态

FootOps 已完成第一版前端交互原型、Phase 2A 真实数据纵向链路，以及一条独立的
LLM 规划 Spike。页面首次打开保持空白，不会自动出现“分析 Pedri 最近五场”的预置
问答；用户主动提交问题后，前端才通过 SSE 创建分析工作区。

当前同时完成了“分析前规划”和第一条不依赖模型的真实数据/指标切片：系统能够
审计 StatsBomb Open Data 覆盖，下载并缓存 Pedri 西甲 2020/21 的连续五场事件，
再用确定性代码生成 `PlayerRoleMetricArtifact`。前端已经通过 TypeScript 业务类型和
真实审核 API 驱动趋势图、三条描述性 Finding 和证据面板。Evidence Gate 会核对指标
字段、数值、比赛范围和来源 URL。`AnalysisWorkspace` 继续包含确定性生成的
`TacticsBoardArtifact`：位置、区域和移动箭头只能引用已通过审核的 Finding，前端据此
确定性渲染并允许本地编辑。该战术板只描述样本位置变化，不声称阵型、传球线路或战术
因果。当前 Repository 仅在 API 进程内保存，尚未接数据库。

项目已完成对本机 `mindbridge-py` 的代码级结构走读，并形成
[FOOTOPS_PROJECT_STRUCTURE_STANDARD.md](./FOOTOPS_PROJECT_STRUCTURE_STANDARD.md)。
后续文件必须按该标准落位，不再只依据概念目录猜测职责。

项目同时建立
[FOOTOPS_DEVELOPMENT_LEARNING.md](./FOOTOPS_DEVELOPMENT_LEARNING.md)，按实际开发
顺序解释每个切片的作用、MindBridge 对照、代码入口、验证方式和当前边界；以后每完成
一个可运行切片必须同步追加。

## 2. 按项目架构查看进度

| 架构层 | 当前状态 | 已开发内容 | 尚未开发内容 |
| --- | --- | --- | --- |
| Web 前端 | Phase 2A 完成 | React/Vite 工作台、可收起侧边栏、空白首屏、用户主动提问、SSE 分析、真实趋势图/证据和 Artifact 驱动的可编辑战术板；原型 Mock 业务数据已删除 | 工作区列表、跨刷新恢复、战术因果结论和报告 |
| API 契约 | Phase 2A 完成 | 健康检查、LLM 状态、结构化计划、覆盖审计、指标、Finding 审核、Workspace 创建/查询、分析 SSE；OpenAPI、10 份 Artifact Schema 和事件 Schema 可生成 | 数据库持久化、会话、Agent 工具过程事件 |
| Agent Runtime Harness | 已完成首个切片 | 为每次运行生成 `run_id`，执行输入长度限制、超时控制、配置检查和错误映射 | run trace 持久化、预算控制、取消/恢复、工具后处理、完整生命周期状态机 |
| AgentScope / Planner | 已完成首个切片 | AgentScope 2.0.5 `Agent`、内置 ReAct 有限循环、DeepSeek 模型接入、中文 FootOps/Planner 分层角色 Prompt、结构化计划输出 | 足球数据工具、证据验证、可执行分析循环和基于失败反馈的修订循环 |
| ModelAdapter | 已完成首个切片 | `MockModelAdapter` 与 `DeepSeekModelAdapter`，上层 Planner 不依赖供应商实现 | 模型降级、成本统计、速率限制、跨供应商回归测试 |
| Artifact | Phase 2A 完成 | Planning、CoverageAudit、MatchDataSnapshot、PlayerRoleMetric、FindingSet、EvidenceSet、EvidenceReview、TacticsBoard 和 AnalysisWorkspace Schema | AnalysisReport 及版本化落库 |
| 数据与 Tools | 部分完成 | StatsBomb Open Data Provider、本地只读缓存、Pedri 五场黄金样例、v1 确定性指标、覆盖审计 CLI/API、前端指标消费 | AgentScope ToolKit/FunctionTool、更多 Provider 和数据缺失降级 |
| Evidence Gate | 描述性链路完成 | `footops-evidence-gate-v1` 校验指标字段、数值、比赛集合、起止日期和来源 URL；伪造数值被拒绝，战术推断进入需补证；前端显示真实支持率 | 数据冲突检测、补证循环、知识来源与战术推断审核 |
| Skills / MCP | 未开始 | 仅保留目录和架构边界 | `SKILL.md` 注册加载、分析技能、导出/发布类 MCP 工具 |
| Blackboard / 多 Agent | 未开始 | 仅保留目录和架构设计 | Coordinator、Data、Tactical、Evidence 等角色及 Artifact 协作；须先证明优于单 Agent |
| 记忆与持久化 | 基线完成 | `AnalysisWorkspaceRepository` Protocol、线程安全进程内实现、生命周期状态机；同一 API 进程内可按 ID 恢复 | SQLAlchemy/MySQL、Redis、历史列表、跨进程恢复和迁移 |
| 可观测与评测 | 部分完成 | 接口可返回 `run_id`/SSE `request_id`；已有单元测试、契约测试和 Mock 端到端验证 | trace 详情、延迟/Token/成本、黄金任务集、直接 LLM/单 Agent/多 Agent 对照评测 |

## 3. 当前已经跑通的调用链

```text
独立 API 调试或自动化测试
  -> FastAPI POST /api/v1/analyses/plan
  -> FootOpsAgentHarness
  -> AnalysisPlanner
  -> ModelAdapter
  -> AgentScope Agent + DeepSeek
  -> AnalysisPlan 结构化校验
  -> AnalysisPlanResponse 返回前端
```

这条链路只负责理解问题和生成后续分析计划。它不会读取比赛数据，也不会生成
可对外发布的战术结论。该边界由 API 响应中的以下字段显式表达：

```json
{
  "model_called": true,
  "data_retrieved": false,
  "real_conclusions_generated": false
}
```

确定性数据链路：

```text
CLI 或 POST /api/v1/metrics/player-role
  -> DataCatalogService
  -> StatsBombOpenDataProvider
  -> CoverageAuditArtifact + MatchDataSnapshot
  -> PlayerRoleMetricEngine
  -> PlayerRoleMetricArtifact
```

该链路真实读取公开比赛数据，但不调用模型，也不生成 Finding 或战术结论。

确定性 Finding 审核链路：

```text
POST /api/v1/findings/player-role/review
  -> PlayerRoleAnalysisService
  -> DeterministicFindingBuilder
  -> FindingSetArtifact + EvidenceSetArtifact
  -> EvidenceGate
  -> EvidenceReviewArtifact
```

该链路生成可复算的描述性观察并完成引用核验，不调用模型，也不把统计变化解释为
战术因果。API 因此保持 `real_conclusions_generated=false`。

工作区链路：

```text
POST /api/v1/analyses 或 POST /api/v1/analyses/stream
  -> AnalysisWorkspaceService
  -> PlayerRoleFindingReviewService
  -> created -> data_ready -> metrics_ready -> findings_ready
  -> evidence_reviewed -> tactics_ready
  -> DeterministicTacticsBoardBuilder
  -> AnalysisWorkspaceRepository

GET /api/v1/analyses/{workspace_id}
  -> AnalysisWorkspaceRepository
  -> 恢复同一 Workspace
```

SSE 接口先发送 `analysis.status`，再发送 `analysis.completed` 或 `analysis.error`。前端当前
不做跨刷新恢复；Workspace 查询接口和 Repository 仍作为持久化前的服务端边界保留。

## 4. 已实现代码位置

| 内容 | 位置 |
| --- | --- |
| 前端入口和工作台 | `apps/web/src/App.tsx`、`apps/web/src/components/` |
| 前端 Agent API 客户端 | `apps/web/src/api/agent.ts` |
| 前端数据类型与指标客户端 | `apps/web/src/api/data.ts` |
| FastAPI 应用和接口 | `services/agent/src/footops_agent/api/` |
| Harness | `services/agent/src/footops_agent/harness/` |
| Planner | `services/agent/src/footops_agent/agents/planner.py` |
| AI 角色 Prompt | `services/agent/src/footops_agent/prompts.py` |
| AgentScope/DeepSeek 适配 | `services/agent/src/footops_agent/runtime/model_adapter.py` |
| 结构化计划 Artifact | `services/agent/src/footops_agent/artifacts/planning.py` |
| 数据/指标 Artifact | `services/agent/src/footops_agent/artifacts/match_data.py`、`metrics.py` |
| Finding/证据 Artifact | `services/agent/src/footops_agent/artifacts/finding.py`、`evidence.py` |
| 公开数据 Provider | `services/agent/src/footops_agent/providers/statsbomb_open.py` |
| 覆盖审计和指标服务 | `services/agent/src/footops_agent/services/` |
| Finding Builder 与 Evidence Gate | `services/agent/src/footops_agent/services/finding_builder.py`、`evidence_gate.py` |
| 战术板 Artifact 与确定性 Builder | `services/agent/src/footops_agent/artifacts/tactics.py`、`services/agent/src/footops_agent/services/tactics_board.py` |
| Workspace 生命周期服务 | `services/agent/src/footops_agent/services/workspace.py` |
| Workspace Repository | `services/agent/src/footops_agent/repositories/analysis_workspace.py` |
| 数据审计 CLI | `services/agent/src/footops_agent/cli/data_audit.py` |
| 生成契约 | `contracts/artifacts/`、`contracts/events/`、`contracts/openapi/` |
| 配置 | `services/agent/src/footops_agent/config/settings.py`、`.env.example` |
| Python 测试 | `services/agent/tests/` |

## 5. 本地运行方式

项目使用 Python 3.12 虚拟环境 `.venv`。本地密钥只允许放在已被 Git 忽略的
根目录 `.env`，不得写入源码、文档、测试快照或日志。

启动 Agent API：

```bash
.venv/bin/uvicorn footops_agent.api.main:app --host 127.0.0.1 --port 8000
```

启动前端：

```bash
npm run dev
```

验证：

```bash
.venv/bin/pytest services/agent/tests
.venv/bin/ruff check services/agent/src services/agent/tests
npm run build
```

运行配置只记录变量名：`LLM_MODE`、`DEEPSEEK_API_KEY`、
`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`、`FOOTOPS_AGENT_MAX_ITERS`、
`FOOTOPS_REQUEST_TIMEOUT_SECONDS`、`STATSBOMB_OPEN_DATA_BASE_URL`、
`FOOTOPS_DATA_CACHE_DIR`、`FOOTOPS_DATA_TIMEOUT_SECONDS`。

## 6. 已完成验证

- Python 单元/API/Prompt/数据管线/Workspace/SSE 回归测试：23 项通过；
- Ruff：通过；
- 前端生产构建：通过；
- Mock 端到端链路：浏览器提交问题并收到结构化计划；
- 浏览器控制台：无错误；
- 真实 DeepSeek 调用：通过。AgentScope 2.0.5 使用 `deepseek-v4-flash`
  返回通过 Pydantic 校验的 `AnalysisPlan`；响应保持
  `data_retrieved=false`、`real_conclusions_generated=false`。
- 前端代理真实链路：通过。`127.0.0.1:4173/api` 已成功代理到 Agent API。
- StatsBomb Open Data 真实覆盖审计：35 场 Pedri 出场记录，连续五场事件快照通过；
- `footops-player-role-v1` 指标：真实五场快照计算通过；
- 真实趋势图：桌面端和 390 px 移动端通过视觉检查，无横向页面溢出和控制台错误；
- 原型 Mock 清理：假比赛、假球员、假证据覆盖率、假报告和预设战术图层已删除；
- Finding/Evidence Gate 反例：正常引用通过、篡改指标数值被拒绝、战术推断要求补证；
- Workspace：创建后按 ID 查询、非法状态跳转拒绝、Repository 防御性拷贝通过；
- TacticsBoard：只消费已审核 Finding，真实 Workspace 生成 2 个区域、1 个位置标记和
  1 条位置变化箭头；阵型未指定、传球线路为空；
- SSE：状态事件先于完成事件，前端成功消费最终 Workspace；
- OpenAPI、10 份 Artifact JSON Schema 与 1 份 SSE Event Schema：已生成。

## 7. 当前明确不是已完成功能

1. 页面只生成经过审核的描述性观察和位置变化图层，尚未生成战术因果结论和报告；
2. 当前真实数据只验证了 StatsBomb Open Data 的历史黄金样例，不支持实时西甲；
3. Finding/Evidence Gate 目前只覆盖确定性描述，尚未处理 Agent 生成的战术推断；
4. 当前支持率表示结构化引用通过率，不是模型置信度或战术结论正确率；
5. 当前 Workspace 只保存在 API 进程内，尚未实现数据库、跨进程恢复和历史列表；
6. 尚未实现 Agent 工具调用、Skills、MCP 和队列；
7. 尚未实现多 Agent 协作，目录存在不代表能力已经落地；
8. 尚未用实验说明多 Agent 比单 Agent 更有价值。

## 8. 下一步开发顺序

1. 将现有只读数据、覆盖审计和指标能力注册为 AgentScope Tools；
2. 建立球员角色分析 `SKILL.md` 与加载/选择边界；
3. 让单个 FootOps Agent 在有限 loop 内完成范围识别、工具选择和结构化 Finding 草案；
4. 所有 Agent Finding 继续经过确定性 Evidence Gate，不允许绕过；
5. 建立直接 LLM 与单 Agent 黄金任务对照，再决定 Phase 3 是否拆分多 Agent。

详细阶段闸门以 [FOOTOPS_DEVELOPMENT_ORDER.md](./FOOTOPS_DEVELOPMENT_ORDER.md)
为准。

## 9. 新会话接手顺序

新 session 开始时按以下顺序阅读：

1. 本文档，确认实际开发状态；
2. [FOOTOPS_REQUIREMENTS.md](./FOOTOPS_REQUIREMENTS.md)，确认产品范围；
3. [FOOTOPS_MINDBRIDGE_ARCHITECTURE.md](./FOOTOPS_MINDBRIDGE_ARCHITECTURE.md)，确认目标架构；
4. [FOOTOPS_PROJECT_STRUCTURE_STANDARD.md](./FOOTOPS_PROJECT_STRUCTURE_STANDARD.md)，确认文件归属；
5. [FOOTOPS_DEVELOPMENT_ORDER.md](./FOOTOPS_DEVELOPMENT_ORDER.md)，确认阶段闸门；
6. [FOOTOPS_DEVELOPMENT_LEARNING.md](./FOOTOPS_DEVELOPMENT_LEARNING.md)，按顺序学习已实现切片；
7. [CODEX_WORK_SESSIONS.md](./CODEX_WORK_SESSIONS.md)，确认各会话职责。

每完成一个可运行切片，必须同步更新本文档中的架构状态、验证结果和下一步，
不得只更新计划文档。
