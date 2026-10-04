# FootOps 当前开发进度

> 文档状态：持续更新
> 最后更新：2026-10-04
> 当前里程碑：Redis Vector RAG（确定性字符向量）与两场球员报告首切片
> 用途：新会话接手项目时的第一份状态文档

## 1. 三十秒了解当前状态

FootOps 已完成第一版前端交互原型、Phase 2A 真实数据黄金纵向链路、自然语言单 Agent
执行链和第二批三模式评测。页面首次打开保持空白，不会自动出现“分析 Pedri 最近五场”的预置
问答；用户主动提交问题后，前端才通过 SSE 创建分析工作区。
问题会先经过入口意图路由：问候和普通足球交流由 `ConversationAgent` 直接回复，不启动
数据检索和多 Agent；分析请求才进入受控分析链。具体指标问题只保留相关 Finding，当前
指标范围未覆盖的问题返回明确边界错误，不会复用固定观察。赛事、赛季、球员和 2 至
10 场窗口已经改为动态请求，不再绑定 Pedri。

当前同时完成了“分析前规划”和第一条不依赖模型的真实数据/指标切片：系统能够
审计 StatsBomb Open Data 覆盖，按所选赛事读取轻量球员目录，并只下载、缓存目标
球员所选 2 至 10 场的比赛事件文件，再过滤出该球员事件，
再用确定性代码生成 `PlayerRoleMetricArtifact`。当前数据链是**单球员、多场描述性分析**，
不是单场比赛或球队级战术复盘。原始事件中包含 `Shot`，指标层支持射门次数、射门参与，
并在来源数据完整时汇总球员 xG；尚未实现射正、射门方式或整队机会质量分析。前端已经通过 TypeScript 业务类型和
真实审核 API 驱动逐场数据表、位置/推进趋势图、最多十条描述性 Finding 和证据面板。
逐场表展示日期、对手比分、射门、xG、射门参与、关键传球、向前传球、推进带球和触球位置；宽泛角色
问题默认选择六条代表性 Finding；具体问题只返回相关指标。Evidence Gate 会核对指标
字段、数值、比赛范围和来源 URL。`AnalysisWorkspace` 继续包含确定性生成的
`TacticsBoardArtifact`：位置、区域和移动箭头只能引用已通过审核的 Finding，前端据此
确定性渲染并允许本地编辑。该战术板只描述样本位置变化，不声称阵型、传球线路或战术
因果。两场及以上的对比现可将审核过的数值观察、Redis 检索到的战术概念和解释边界组成
用户可读报告；案例化战术解释仍需授权案例 RAG、更多比赛级指标和完整联合 Evidence Gate。
普通分析 Agent 现可收到逐场日期、对手、射门、xG、射门参与、关键传球及推进等事实，
回答“哪场 xG/射门最高”等比较问题；“发挥最好”不会编造综合评分。省略追问
（如“哪场射门最多”）沿用上一分析工作区的比赛范围。当前 Repository 仅在 API 进程内保存，尚未接数据库。

项目已完成对本机 `mindbridge-py` 的代码级结构走读，并形成
[FOOTOPS_PROJECT_STRUCTURE_STANDARD.md](./FOOTOPS_PROJECT_STRUCTURE_STANDARD.md)。
后续文件必须按该标准落位，不再只依据概念目录猜测职责。

项目也已完成本地 `agentscope==2.0.5` 的多 Agent 能力审计。结论是 AgentScope 本身是
多 Agent 框架；FootOps 当前生产问答链接入单 `Agent`，Phase 3A 则先实现了用于学习
MindBridge 协作语义的最小领域 Board。AgentScope 包内还提供 App/Team、
`SubAgentTemplate`、任务工具、团队通信、MessageBus、Session、Storage 和
WorkspaceManager，但当前项目
尚未安装 `service` extra，实际导入 `agentscope.app` 会缺少 `apscheduler`。因此这些能力
仍只能写成“已审计、未接入”。Phase 3B 将把已经可测的 Task/Artifact/Claim 语义映射到
App/Team；Phase 3A Board 不扩展为通用 MessageBus、Storage 或 Scheduler。

项目同时建立
[FOOTOPS_DEVELOPMENT_LEARNING.md](./FOOTOPS_DEVELOPMENT_LEARNING.md)，按实际开发
顺序解释每个切片的作用、MindBridge 对照、代码入口、验证方式和当前边界；以后每完成
一个可运行切片必须同步追加。

## 2. 按项目架构查看进度

| 架构层 | 当前状态 | 已开发内容 | 尚未开发内容 |
| --- | --- | --- | --- |
| Web 前端 | Phase 2B 扩展中 | React/Vite 工作台、自然语言优先输入、2 至 10 场范围约束、Agent SSE 工具进度、真实趋势图/证据和 Artifact 驱动战术板 | 中文别名消歧、日期范围、工作区列表、跨刷新恢复、球队级报告 |
| API 契约 | Phase 2B 扩展中 | 健康检查、目录、指标、Finding、Workspace、确定性分析 SSE 与 Agent started/tool/final/error SSE；OpenAPI、Artifact/Event Schema 可生成 | 数据库持久化、服务端会话、取消/恢复事件 |
| Agent Runtime Harness | 已完成首个切片 | 为每次运行生成 `run_id`，执行输入长度限制、超时控制、配置检查和错误映射 | run trace 持久化、预算控制、取消/恢复、工具后处理、完整生命周期状态机 |
| AgentScope / Planner | Phase 3A KnowledgeAgent 首切片完成 | 可组合 ExecutionPlan、`ConversationAgent`、`FootOpsScopeAgent`、`FootOpsAnalysisAgent`、`FootOpsKnowledgeAgent`、AgentScope 2.0.5 ReAct、DeepSeek、结构化输出和受控工具 | 案例知识联合解释与 Phase 3B App/Team |
| ModelAdapter | 已完成首个切片 | `MockModelAdapter`、`DeepSeekModelAdapter` 与无工具直接 LLM 对照运行时；记录供应商 Token，支持按配置单价估算成本 | 模型降级、速率限制、跨供应商回归测试 |
| Artifact | Phase 3A 联合知识首个切片完成 | Planning、CoverageAudit、MatchDataSnapshot、PlayerRoleMetric、FindingSet、EvidenceSet、EvidenceReview、TacticsBoard、AnalysisWorkspace、ExecutionPlan、ScopeResolution、KnowledgeEvidence、KnowledgeAnswer 和 TacticalHypothesis Schema | 独立 AnalysisReport、Hypothesis revision 及版本化落库 |
| 数据与 Tools | Phase 2B 工具基线完成 | StatsBomb Provider 与确定性服务已通过 AgentScope `Toolkit`/`FunctionTool` 暴露为赛事检索、球员解析和分析执行工具；工具结果由 Harness 校验并通过 SSE 发布 | 中文别名、更多 Provider、跨赛事自动查找 |
| Evidence Gate | 描述性链路完成 | `footops-evidence-gate-v1` 校验指标字段、数值、比赛集合、起止日期和来源 URL；伪造数值被拒绝，战术推断进入需补证；前端显示真实支持率 | 数据冲突检测、补证循环、知识来源与战术推断审核 |
| Skills / MCP | Skill 首个切片完成 | AgentScope 已注册并加载 `footops-player-role-analysis/SKILL.md` | 导出/发布类 MCP 工具和更多业务 Skill |
| Knowledge RAG | Redis 外部知识库首切片 | 规则、战术概念和指标定义的向量及完整知识正文/来源元数据均同步到 Redis 8；ExecutionPlan 将对应请求路由给 KnowledgeAgent，Agent 通过只读工具检索 Redis 并引用证据；Redis 不可用时拒绝基于模型记忆回答 | 语义 Embedding、授权比赛案例、战术模板、知识更新管理、向量检索评测、矛盾与多样性选择、联合 Evidence Gate |
| AgentScope App/Team 多 Agent | Phase 3B Storage/App Spike 已通过，Team 行为待最后运行 | 已安装 `service`、`storage-redis`、`storage-sql` 与 `aiomysql`；Redis/MySQL Storage、Redis MessageBus、APScheduler、LocalWorkspaceManager 和四类 SubAgentTemplate 均已能随 App 生命周期启动；已新增 TeamCreate/AgentCreate 验证脚本 | Team 行为回归、事件投影、FootOps Board/Artifact 接入、取消恢复和生产 Storage 选型 |
| 事件驱动多 Agent 学习层 | Phase 3A critique/revision 首个切片完成 | ScopeAgent 前置解析；Coordinator/Data/Tactical/Evidence/Knowledge 五角色、不可变 Board、capability claim、Artifact、轮次预算、独立审核、Final Accept；KnowledgeAgent 已发布知识与假设 Artifact；审核未通过时会生成 critique、触发一次 Finding revision 并重新审核；协作事件已有用户态 SSE | Checkpoint、AgentScope Team 映射；当前 Board KnowledgeAgent 使用同一版本化检索器，尚未把案例化战术解释完整接入当前聊天主链 |
| 记忆与持久化 | 基线完成 | `AnalysisWorkspaceRepository` Protocol、线程安全进程内实现、生命周期状态机；同一 API 进程内可按 ID 恢复 | SQLAlchemy/MySQL、Redis、历史列表、跨进程恢复和迁移 |
| 可观测与评测 | Phase 3A Scope 对照完成 | 原四模式 9 任务对照保留；接入 ScopeAgent 后多 Agent 9/9，记录范围工具、Token、延迟和脱敏 collaboration trace | ExecutionPlan/RAG 黄金任务、多 Agent SSE、trace 持久化、故障/恢复任务 |

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

自然语言执行入口
  -> POST /api/v1/agent/runs/stream
  -> FootOpsAnalysisHarness
  -> RequestIntentRouter
     -> chat: ConversationAgent -> 普通回复，不创建 Workspace
     -> analysis: AgentScope ReAct + AgentState + ContextConfig
        -> player-role Skill -> competition/player/analysis Tools
        -> AgentRunStreamEvent -> Workspace 或安全补问

多 Agent 学习入口
  -> POST /api/v1/multi-agent/analyses
  -> EventDrivenCoordinator + CollaborationBoard
  -> DataAgent claim -> data_bundle
  -> TacticalAgent claim -> finding_bundle
  -> EvidenceAgent claim -> review_bundle
  -> TacticalAgent 可选 claim -> tactics_bundle
  -> CoordinatorAgent final accept -> Workspace
```

确定性 SSE 使用 `analysis.*` 事件；自然语言 Agent SSE 使用 `agent.started`、
`agent.chat_completed`、`agent.tool.completed` 和最终完成、补问、超范围或错误事件。前端当前不做跨刷新恢复；
Workspace 查询接口和 Repository 仍作为持久化前的服务端边界保留。

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
| 黄金问题范围路由 | `services/agent/src/footops_agent/services/question_scope.py` |
| 战术板 Artifact 与确定性 Builder | `services/agent/src/footops_agent/artifacts/tactics.py`、`services/agent/src/footops_agent/services/tactics_board.py` |
| Workspace 生命周期服务 | `services/agent/src/footops_agent/services/workspace.py` |
| Workspace Repository | `services/agent/src/footops_agent/repositories/analysis_workspace.py` |
| 多 Agent 协作协议 | `services/agent/src/footops_agent/collaboration/` |
| 多 Agent 领域角色 | `services/agent/src/footops_agent/agents/collaborative.py` |
| 多 Agent Runtime | `services/agent/src/footops_agent/runtime/multi_agent.py` |
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
`FOOTOPS_DEEPSEEK_INPUT_COST_PER_MILLION_USD`、
`FOOTOPS_DEEPSEEK_OUTPUT_COST_PER_MILLION_USD`、
`FOOTOPS_REQUEST_TIMEOUT_SECONDS`、`STATSBOMB_OPEN_DATA_BASE_URL`、
`FOOTOPS_DATA_CACHE_DIR`、`FOOTOPS_DATA_TIMEOUT_SECONDS`。

## 6. 已完成验证

- Redis Vector RAG：Redis 8 `VADD`/`VSIM` 检查通过；当前使用确定性字符哈希向量，
  不依赖本地模型服务；先前的模型向量索引已清除。Ruff、Python 编译和前端生产构建通过；
  本次未重跑全量回归测试；
- Python 单元/API/Prompt/数据管线/Workspace/SSE/Agent/RAG/评测回归测试：84 项通过；
- Ruff：通过；
- 前端生产构建：通过；
- Mock 端到端链路：浏览器提交问题并收到结构化计划；
- 浏览器控制台：无错误；
- 真实 DeepSeek 调用：通过。AgentScope 2.0.5 使用 `deepseek-v4-flash`
  返回通过 Pydantic 校验的 `AnalysisPlan`；响应保持
  `data_retrieved=false`、`real_conclusions_generated=false`。
- 真实单 Agent 调用：通过。自然语言缺少范围时返回澄清；范围完整时按
  Skill -> 赛事工具 -> 球员工具 -> 确定性分析工具执行，并生成通过证据门禁的 Workspace；
- 入口意图路由：通过。`你好` 等普通对话进入无工具 `ConversationAgent`，返回
  `status=chat`、`data_retrieved=false`、空 collaboration trace，不创建 Workspace；
- ScopeAgent：真实 DeepSeek 自然语言范围解析通过，只调用 `search_competitions` 和
  `search_players`，规范解析 La Liga `11/90`、Pedri `30486` 和 3 场窗口；
- ExecutionPlan：已区分 chat、rule_qa、tactical_knowledge、data_analysis 和
  hybrid_tactical_analysis，并独立声明数据、规则 RAG、战术 RAG、多 Agent 和范围需求；
- 规则 Knowledge RAG：IFAB 2026/27 规则问题进入 KnowledgeAgent，只调用
  `search_knowledge`，返回版本、章节、有效日期、官方 URL 和可解析 citation ID；不调用
  ScopeAgent 或比赛数据工具；
- 外部知识库：目前所有规则、战术概念和指标定义的检索正文、向量与来源元数据均持久化于
  Redis Stack；KnowledgeAgent 仅通过受限域的只读检索工具访问。问候等普通聊天不触发检索，
  Redis 检索故障时不回退到 Python 本地语料作答；
- RAG 能力边界：本机 Redis 8 Vector Sets 已接入规则、战术概念和指标定义，以确定性字符
  哈希向量和 BM25/字符特征混合排序；它不具备语义 Embedding 的跨表达召回能力。授权案例、
  战术模板和知识更新流水线仍待补充；
- 自然语言多 Agent API：`POST /api/v1/multi-agent/runs` 通过。ScopeAgent 完成后才创建
  Board，随后 Data -> Tactical -> Evidence -> Tactical -> Final Accept；
- 数据 + 战术知识联合入口：当前 `/api/v1/agent/runs` 的 `hybrid_tactical_analysis` 在范围
  完整时会进入多 Agent Board，并把 `TacticalHypothesisArtifact` 回流为用户可见的受限文字
  假设；缺少范围时先澄清，不启动比赛数据链；
- 前端普通对话：通过。页面显示“普通对话 · 未启动比赛分析”，不会渲染 0 条 Finding、
  证据面板或战术板；真实 DeepSeek 调用和浏览器控制台均通过；
- 自然语言入口：`POST /api/v1/agent/runs` 已接入，固定赛事、球员和窗口改为可选提示；
- 短期上下文：前端随请求携带最近六轮问答，可接续 Agent 的范围补问；
- 前端代理真实链路：通过。`127.0.0.1:4173/api` 已成功代理到 Agent API。
- StatsBomb Open Data 真实覆盖审计：35 场 Pedri 出场记录，连续五场事件快照通过；
- 通用球员目录真实验收：西甲 2020/21 解析 383 名有出场记录的球员；Lionel Messi
  最近三场完整数据链路通过，证明事件数据按球员和窗口读取；
- `footops-player-role-v1` 指标：真实五场快照计算通过；位置、传球、推进、进攻参与及来源
  可用时的球员 xG 已接入确定性 Finding，宽泛角色问题仍选择 6 个代表性指标；
- 真实趋势图：桌面端和 390 px 移动端通过视觉检查，无横向页面溢出和控制台错误；
- 原型 Mock 清理：假比赛、假球员、假证据覆盖率、假报告和预设战术图层已删除；
- Finding/Evidence Gate 反例：正常引用通过、篡改指标数值被拒绝、战术推断要求补证；
- Critique/revision：审核未通过时生成 `CRITIQUE_CREATED`，由 TacticalAgent 在预算内修订，
  EvidenceAgent 重新审核，并记录 `REVISION_PUBLISHED`；
- Workspace：创建后按 ID 查询、非法状态跳转拒绝、Repository 防御性拷贝通过；
- TacticsBoard：只消费已审核 Finding，真实 Workspace 生成 2 个区域、1 个位置标记和
  1 条位置变化箭头；阵型未指定、传球线路为空；
- SSE：状态事件先于完成事件，前端成功消费最终 Workspace；
- 多 Agent 用户态 SSE：`POST /api/v1/multi-agent/runs/stream` 已推送 started、协作
  trace、completed/clarification/unsupported 和 error 事件；不暴露 Artifact payload 或模型思维链；
- 问题范围：位置、禁区触球、向前传球、推进带球、关键传球、射门和射门参与问题只返回
  相关 Finding；“最近表现”“踢得怎么样”等综合问法返回 6 项代表性观察；进球、助攻、
  射正、防守和评分等未接入指标被明确拒绝；球员 xG 仅在 StatsBomb 对该样本完整提供时支持；
- 前端范围优先级：赛事和窗口默认不发送约束，由 Agent 解析用户自然语言；只有用户主动
  选择筛选项时才发送 hint，避免“最近三场”被默认五场覆盖；
- Phase 2B 真实黄金任务对照：确定性直调 7/8、无工具直接 LLM 2/8、单 Agent 8/8；
  单 Agent 工具序列正确率 100%，已生成结论的证据支持率 100%，无无依据完成状态；
- 单 Agent 八任务平均耗时 7544.4 ms，供应商报告 Token 共 77107；未配置动态单价，
  因此费用字段如实保留为 `null`，不伪造成本；
- Phase 3A 多 Agent：九任务 8/9，平均 70.2 ms，Claim Support 100%；综合问题的 claim
  顺序为 Data -> Tactical -> Evidence -> Tactical，Evidence 审核前 Coordinator 不采纳；
- 四模式九任务最新对照保存于 `data/evaluation/reports/phase3-latest.json`：确定性
  7/9、直接 LLM 3/9、单 Agent 9/9、多 Agent 8/9。多 Agent 唯一失败是无 scope hint
  的自然语言范围解析；该缺口已由 ScopeAgent 后续切片补齐；
- ScopeAgent 后的多 Agent 九任务结果保存于
  `data/evaluation/reports/phase3-scope-agent-latest.json`：9/9，平均 3361.8 ms，Token
  共 25716，Claim Support 100%；
- OpenAPI、17 份 Artifact JSON Schema 与 2 份 SSE Event Schema：已生成。

## 7. 当前明确不是已完成功能

1. 两场及以上的同一球员数据可生成带逐场指标、描述性变化和战术知识参照的受限报告；
   尚未生成经 LLM 推理并由独立门禁验证的战术因果结论；
2. 当前真实数据只验证了 StatsBomb Open Data 的历史黄金样例，不支持实时西甲；
3. Finding/Evidence Gate 目前只覆盖确定性描述和首个战术假设切片，尚未覆盖完整的 Agent
   生成战术报告验证；
4. `rag/` 已接入 Redis Vector Sets 与确定性字符哈希向量，检索 IFAB 2026/27 规则、
   半空间/第三人/压迫触发/Rest defence 概念和 FootOps v1 指标口径；语义 Embedding、
   授权比赛案例、战术模板、向量检索评测与知识更新流水线尚未接入；
5. 当前数据分析以单球员、两场及以上窗口为主；尚未实现完整单场比赛、两队对比和球队级战术分析；
6. 当前支持射门次数、射门参与及来源可用时的球员 xG；射正、射门方式和整队机会质量尚未实现；
7. 当前支持率表示结构化引用通过率，不是模型置信度或战术结论正确率；
8. 当前 Workspace 只保存在 API 进程内，尚未实现数据库、跨进程恢复和历史列表；
9. 已实现首个 Agent 工具调用和球员角色 Skill；尚未实现 MCP 和异步队列；
10. 已实现 Phase 3A 事件驱动领域协作和前置 ScopeAgent；AgentScope App/Team 已完成最小 App
   启动 Spike，但尚未接入默认业务主链或把 Team 事件投影到 FootOps Board；
11. ScopeAgent 接入后当前多 Agent 9/9，与单 Agent 9/9 持平；它仍是学习和对照路径，
   尚未证明质量收益，因此不替代默认分析链；
12. 普通足球交流已经可由 ConversationAgent 回答，但它不检索实时数据；可执行分析仍只覆盖
   位置/触球、向前传球、推进带球、关键传球、射门与射门参与等已声明的描述性意图。
13. StatsBomb Open Data 不提供中文球员别名和全局球员搜索 API；当前需在所选赛事中
    使用数据源姓名或候选项，尚不能仅凭任意中文译名跨赛事定位球员。

## 8. 下一步开发顺序

1. [已完成首个切片] 已加入半空间、第三人、压迫触发、Rest defence 战术概念和 FootOps v1
   指标口径，并完成
   KnowledgeAgent -> CollaborationBoard -> `TacticalHypothesisArtifact` 首个联合切片及聊天
   入口回流；继续补充授权比赛案例和战术模板，并建立语义 Embedding 对照评测；
2. [已完成首个切片] KnowledgeAgent 已接入 CollaborationBoard，支持数据 + 知识联合分析；
3. [已完成首个切片] 实现 Evidence critique -> Tactical revision 的一次有限返工循环，
   由 `revision_budget` 防止无限循环；
4. [已完成首个切片] 为检索、Task Claim、Artifact、审核、修订和 Final Accept 增加用户态 SSE；
5. [已完成 Storage/App Spike] 启动 Redis-backed 和 MySQL-backed App，注册四类
   SubAgentTemplate，并在独立 `footops_agentscope` 库生成 AgentScope 表；TeamCreate/AgentCreate
   脚本已完成，待一次真实凭据运行后继续把事件无破坏投影到 FootOps Board/Artifact。

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

## 10. 2026-08-01 Phase 2B 会话交接

本次已完成：

- 新增 `POST /api/v1/agent/runs` 自然语言入口，赛事、赛季、球员和窗口均为可选提示；
- 新增 `FootOpsAnalysisAgent`，使用 AgentScope 2.0.5 ReAct、DeepSeek、结构化
  `AgentDecision` 和请求级 Toolkit；
- 新增赛事检索、球员检索、确定性球员角色分析三个 FunctionTool；
- 新增 `footops-player-role-analysis` Skill；
- 新增 `FootOpsAnalysisHarness`，负责输入上限、120 秒运行超时、模型可用性、完成状态
  与真实 Workspace 一致性校验；
- 前端允许只输入自然语言，固定选择项改为可选范围约束；
- 前端随请求携带最近六轮问答，支持后续接续 Agent 补问；
- Mock/API 回归、Ruff 和前端构建通过；该阶段结束时测试数为 52。

真实联调结果：

1. 缺少赛事赛季时，Agent 能调用赛事工具并返回 `clarification_required`；
2. 提供完整规范 ID 时，Agent 能按赛事检索 -> 球员检索 -> 确定性分析执行，生成
   6 条代表性 Finding 和通过证据门禁的 Workspace；
3. 已修复“2020/21 赛季”标准化导致赛事目录误判的问题；
4. 中文球员名首次检索未命中后，已加入“转换拉丁字母简称并只重试一次”的工具规则；
5. 该次 502 已定位为 ReAct 在 6 次迭代内完成工具调用、但未生成结构化 Decision；
   初步调整为 8 次。黄金任务进一步证明中文姓名重试需要额外预算，最终上限调整为
   10 次，并增加“真实 Workspace 已存在时构造可信 Decision”的兜底；
6. 中文完整问题和两轮补问历史均已真实通过；模型补问中的未核验赛季示例已由
   `_safe_clarification` 替换为工具事实驱动文本；
7. Agent SSE、显式 `AgentState`、`ContextConfig`、上下文压缩 Prompt 和工具结果上限
   已接入，桌面与 390 px 移动端浏览器验收通过。

本次追加完成 Phase 2B 第二批黄金任务：`footops-player-role-v1` 含 8 个任务，在原有
完整范围、自然语言解析、缺失范围、越界指标和未知球员之外，新增向前传球、推进带球和
射门参与。真实结果保存于 `data/evaluation/reports/phase2b-latest.json`：确定性直调
7/8、直接 LLM 2/8、单 Agent 8/8。确定性直调唯一失败是没有范围 hint 时无法自行解析
自然语言，恰好是 Agent 补足的能力。前端已新增位置/推进进攻趋势切换，并修复默认五场
覆盖用户“最近三场”的问题。该阶段原计划先补球员解析；第 11 节记录了用户确认学习
优先后进入 Phase 3A 的最新顺序，后文状态优先。

当前本地服务：前端仍可使用 `http://127.0.0.1:4173/`；后端运行于
`http://127.0.0.1:8000/`。工作区有未提交修改，禁止回退本会话之前已有的并行改动。

## 11. 2026-08-01 Phase 3A 多 Agent 交接

用户重新确认 FootOps 是 Agent 架构学习项目，足球业务只作为可验证载体，因此开发顺序
已调整：停止优先扩展足球指标，立即进入 MindBridge 多 Agent 协作学习。

本次完成：

- 代码级走读本机 `mindbridge-py/app/agents/` 的 events、registry、coordinator、
  autonomous、event-driven runtime 和测试；
- 新增最小不可变 CollaborationBoard、Task、Artifact、Event 和 capability Registry；
- 新增 CoordinatorAgent、DataAgent、TacticalAgent、EvidenceAgent；
- Coordinator 根据缺失 Artifact 创建任务，Worker 自主 claim，EvidenceAgent 审核后才
  允许 Final Accept；
- 新增轮次预算，预算耗尽不能返回伪成功；
- 新增 `POST /api/v1/multi-agent/analyses` 与脱敏协作 Trace；
- 新增 5 项多 Agent 协议/API 测试；加入意图路由后全套测试增至 62 项；
- 四模式评测扩展为 9 项，结果为确定性 7/9、直接 LLM 3/9、单 Agent 9/9、
  多 Agent 8/9。

当前多 Agent Worker 先复用确定性领域服务，目的是隔离编排与模型质量。ScopeAgent 已作为
Board 前置角色接入，KnowledgeAgent 已能在战术联合请求中发布版本化知识和
TacticalHypothesis；Evidence critique -> Tactical revision 首个有限循环已完成。系统尚未
已完成 AgentScope App/Team 的 Redis-backed 最小启动，但尚未接入默认业务主链，也尚未拥有
FootOps 侧的 Message 投影、私有记忆、Checkpoint 和持久化 Trace。入口已有 RequestIntentRouter
和 ConversationAgent；ExecutionPlan 与协作用户态 SSE 已完成，下一步是扩展黄金任务并进行
Team 行为和 Artifact 投影验证；详细路线见
[FOOTOPS_MULTI_AGENT_LEARNING.md](./FOOTOPS_MULTI_AGENT_LEARNING.md)。

## 12. 2026-08-02 Knowledge RAG 规则切片交接

本次完成：

- 新增 IFAB Laws of the Game 2026/27 最小版本化规则语料；
- 新增 `KnowledgeEvidenceArtifact` 与 `KnowledgeAnswerArtifact`；
- 新增 BM25 + 字符 n-gram 稀疏向量 + 确定性 rerank 检索基线；
- 新增 AgentScope `FootOpsKnowledgeAgent` 和只读 `search_knowledge` 工具；
- 规则问答已接入现有 ExecutionPlan、Harness、API 和 SSE；
- 规则问题不启动比赛数据链；战术概念首个切片已进入独立 KnowledgeAgent 和联合 Board；
- 新增 `TacticalHypothesisArtifact`，新增 critique/revision 事件、协作 SSE、混合入口回流、指标口径 RAG 和回归测试，全套测试增至 84 项，
  契约新增假设 Artifact Schema。

下一步是补充授权比赛案例和战术模板黄金集，评估语义 Embedding 相对当前可审计基线的收益，
并执行 [AgentScope App/Team Spike](./FOOTOPS_AGENTSCOPE_APP_TEAM_SPIKE.md) 的 Team 行为回归。
