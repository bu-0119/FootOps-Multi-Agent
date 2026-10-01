# FootOps 开发顺序规范

> 文档类型：实施顺序与阶段闸门
> 基线日期：2026-07-31
> 当前阶段：Redis Vector RAG 确定性首切片；两场及以上球员报告已打通，进入检索评测与案例语料阶段

## 1. 文档目的

本文档规定：

- 当前项目真实进度；
- 下一步先做什么；
- 哪些能力必须后做；
- 每个阶段的完成标准；
- 进入下一阶段前必须通过的闸门。

需求以 [FOOTOPS_REQUIREMENTS.md](./FOOTOPS_REQUIREMENTS.md) 为准，技术设计以
[FOOTOPS_MINDBRIDGE_ARCHITECTURE.md](./FOOTOPS_MINDBRIDGE_ARCHITECTURE.md)
为准。

## 2. 开发原则

1. 先打通黄金任务的纵向链路，再扩展场景；
2. 先实现真实数据和确定性工具，再接入模型；
3. 先建立单 Agent 基线，再用同一黄金任务学习和评测多 Agent；
4. 先定义业务契约，再让前端依赖后端；
5. 先建立评测基线，再宣称技术收益；
6. 简单任务使用确定性服务，不强制 Agent；
7. 每一阶段必须有可以独立运行和验证的产物；
8. 每个可运行切片完成后，必须按开发顺序更新
   [FOOTOPS_DEVELOPMENT_LEARNING.md](./FOOTOPS_DEVELOPMENT_LEARNING.md)，记录作用、
   MindBridge 对照、代码入口、验证方式、当前边界和后续连接；
9. Phase 3A 允许实现一层最小领域协作协议，以代码级学习 MindBridge 的 Task Claim、
   Artifact、Evidence Review 和 Final Accept；不得扩展成通用 MessageBus、Scheduler 或
   Storage 框架。Phase 3B 再与 AgentScope App/Team 做映射和对照；
10. 官网其他版本的类名不得替代本地 2.0.5 API，框架升级必须单独评测。
11. 比赛事实进入 Data Provider，规则、战术案例和模板进入 Knowledge RAG；两类证据不得混存；
12. TacticalAgent 必须形成可审核的战术假设，不能只把确定性指标改写成自然语言。

## 3. 当前进度

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| 产品需求 | 已完成 | 已形成独立需求基线 |
| MindBridge 对照架构 | 已修订 | 已形成 AgentScope-first 目标架构和版本能力边界 |
| React 静态原型 | 已完成 | 页面和主要交互可用 |
| 可折叠侧边栏 | 已完成 | 桌面和移动端已设计 |
| 可编辑战术板 | Phase 2A 完成 | `TacticsBoardArtifact` 驱动审核后的位置、区域和移动箭头，支持本地编辑 |
| 分析、证据和图表 | Phase 2B 扩展完成 | 10 个确定性 Finding（含基础射门次数/射门参与）、2 至 10 场同一球员对比报告、位置/推进趋势图、Evidence Gate 和描述性战术板消费真实历史数据；整场比赛分析、球队级分析和战术因果结论未实现 |
| 前后端业务契约 | Phase 2A 完成 | Workspace 创建/查询、分析 SSE、OpenAPI、Artifact/Event JSON Schema 和 TypeScript 类型已生成 |
| Python Agent Service | 部分完成 | LLM 规划切片和确定性数据/指标切片可独立运行 |
| 真实足球数据 | 部分完成 | StatsBomb Open Data 覆盖审计、缓存、标准化和五场黄金样例已验证 |
| 单 Agent | Phase 3A KnowledgeAgent 首切片完成 | AgentScope 2.0.5 + DeepSeek 已接 Conversation、Scope、Analysis、Knowledge 四类角色，ReAct、Toolkit、FunctionTool、Skill、结构化输出、澄清和短期上下文 |
| Workspace | 进程内基线完成 | 状态机、Repository Protocol、创建/查询/SSE 已完成；数据库持久化和前端跨刷新恢复待补 |
| 事件驱动多 Agent | Phase 3A Scope 完成 | ScopeAgent 前置解析，Coordinator/Data/Tactical/Evidence 执行 Task Claim、Artifact、独立审核和最终采纳；自然语言 API 与 9/9 评测通过 |
| Knowledge RAG | Redis 外部知识库首切片完成 | 规则、战术概念和指标定义正文/来源元数据及确定性字符哈希向量进入 Redis 8；ExecutionPlan 路由至 KnowledgeAgent，经只读工具检索并带证据引用；Redis 故障时不使用本地语料或模型记忆兜底 |
| AgentScope App/Team | Phase 3B Storage/App Spike 完成 | Redis/MySQL-backed App、四类 `SubAgentTemplate` 和服务路由已启动；待验证 Team 行为、Task Tools 和业务 Artifact 投影 |

当前不能宣称已经完成整场/球队级比赛分析、案例化战术因果分析、FootOps 业务数据库持久化或
AgentScope Team 已接入默认主链；可以准确宣称 Phase 3A 事件驱动多 Agent 协作切片和 Phase 3B
Redis-backed App 启动 Spike 已运行。

## 4. Phase 1：前端静态原型

状态：**黄金样例已完成，通用化扩展进行中**

已实现：

- 问答主界面；
- 可折叠侧边栏；
- 证据引用与证据面板；
- 可编辑战术板；
- 本地 Mock 数据（仅 Phase 1 原型，已在真实数据接入后删除）；
- 桌面和移动端响应式适配。

保留规则：

- 模型 Mock 只保留为自动化测试 Fixture，不进入正式业务界面；
- 正式模式接入后，删除组件内部写死的结论、证据覆盖率和指标数值；
- 交互组件保留，数据来源改为统一业务 Schema。

## 5. Phase 2A：真实数据纵向链路

状态：**已完成**

这一阶段不实现多 Agent，也不以 RAG 为重点。真实数据纵向链路仍是唯一交付
主线；本阶段允许进行 5.3 所定义的受限 LLM 接入基础设施 Spike，但不得挤占、
替代或延后数据链路工作。

### 5.1 执行顺序

1. 编写公开数据覆盖审计脚本；
2. 列出可用赛事、赛季、比赛和球员；
3. 选择确实拥有连续 3 至 10 场事件数据的黄金样例；
4. 定义 AnalysisRequest、AnalysisWorkspace 和核心 Artifacts；
5. 在 `contracts/` 固化 OpenAPI 和 SSE Schema；
6. 将前端改为消费统一 AnalysisResponse；
7. 建立 FastAPI 应用和健康检查；
8. 实现创建分析、查询分析和 SSE 接口；
9. 实现数据下载、缓存、标准化和快照；
10. 实现第一组确定性球员指标；
11. 用真实 MetricArtifact 驱动图表；
12. 用 Finding 和 Evidence 数据驱动证据面板；
13. 用 TacticsBoardArtifact 驱动战术板；
14. 增加数据适配器和指标工具单元测试。

### 5.2 第一组指标范围

只实现黄金任务必要指标：

- 触球位置和区域分布；
- 进攻三区和禁区触球占比；
- 接球区域变化；
- 向前传球；
- 持球推进；
- 关键传球；
- 射门次数和射门参与；
- 跨比赛趋势。

指标定义必须写明输入字段、公式、空值规则、单位和适用范围。

### 5.3 LLM 接入基础设施 Spike

该 Spike 只验证 LLM 接入所需的最小基础设施，不扩展为单 Agent MVP。范围严格
限于：

- 建立 FastAPI 中的最小接入边界；
- 建立模型、凭据和超时配置，凭据仅从环境变量读取；
- 固定使用 AgentScope 2.0.5，并验证 Agent 内置 ReAct loop 的最小调用链；
- 实现 DeepSeek ModelAdapter 的最小接线；
- 定义并校验结构化分析计划 Schema，只表达问题拆解、所需数据、候选工具、
  证据需求、缺失信息和停止条件；
- 在 Harness 边界实现明确的模型调用超时，并将超时转换为可测试的失败状态；
- 建立 mock 和 live 两类测试：mock 测试默认运行，live 测试必须显式启用并依赖
  外部凭据。

该 Spike 不得调用真实分析链路生成指标、Finding 或战术建议，不得产生或展示
任何真实战术结论。它只证明接线、Schema、超时和测试边界可用；完成该 Spike
不代表 Phase 2A 数据链路完成，也不计为 Phase 2B 完成或部分完成。

### 5.4 Phase 2A 完成标准

- 前端不依赖写死的正式分析结果；
- 一个黄金问题使用真实比赛数据完成指标计算；
- 图表、证据和战术板来自后端 Artifact；
- 每个数值可追溯到数据快照和计算口径；
- 数据覆盖不足有明确降级状态；
- 不需要模型也能跑通数据到界面的完整链路；
- 单元测试和集成测试通过。

### 5.5 Phase 2A 通用球员数据扩展

在进入 Phase 2B 前完成，且不通过 RAG 保存比赛事件：

1. 赛事和赛季来自 Provider 目录，不在前端写死；
2. 球员目录只保存姓名、规范 ID、球队和覆盖场次等轻量元数据；
3. 触球、传球和接球事件只在提交分析后读取所选 3 至 10 场比赛事件文件，再按规范
   球员 ID 过滤和计算；不预下载整个赛季事件；
4. 请求和 Workspace 保存规范球员 ID，避免同名球员混淆；
5. 数据源没有该球员时返回明确边界，不让模型补造；
6. 至少使用黄金球员之外的一名真实球员完成端到端回归；
7. 后续补充中文别名、跨赛事定位、日期范围和第二 Provider 评估。

当前已完成 1 至 6；第 7 项继续作为进入 Phase 2B 前的数据产品完善主线。

## 6. Phase 2B：单 Agent MVP

状态：**第二批黄金任务基线完成，作为 Phase 3 对照组继续保留**

已完成：自然语言范围解析与补问、AgentScope ReAct、请求级 Toolkit、球员角色 Skill、
三个受控工具、结构化 Decision、可信 Workspace 兜底、短期历史、显式 AgentState、
ContextConfig、版本化 Agent SSE，以及确定性直调/直接 LLM/单 Agent 八任务评测。
位置、传球、推进、关键传球和基础射门参与的描述性 Finding 已完成；当前仍是单球员多场
指标链路，不是整场比赛或球队级分析。尚未完成受控案例化战术解释，因此暂不把模型输出
描述为战术因果。

### 6.1 实施内容

- 复用已完成的 DeepSeek ModelAdapter Spike，接入可执行的单 Agent 链；
- 使用 AgentScope 2.0.5 Agent 内置 ReAct loop；
- 实现问题范围识别和澄清；
- 注册球员角色分析 Skill；
- 允许 Agent 选择只读数据和指标 Tools；
- 使用 AgentScope `Toolkit`/`FunctionTool` 适配现有领域服务，不自建工具调用循环；
- 生成结构化 FindingArtifact；
- 验证并使用 AgentScope `ContextConfig`/`AgentState` 的基础上下文压缩和运行状态；
- 扩展现有 SSE，返回 Agent 工具选择、门禁和停止原因等业务事件；
- 建立直接 LLM 与单 Agent 基线。

### 6.2 单 Agent 边界

单 Agent 可以：

- 理解问题；
- 选择 Skill；
- 选择只读工具；
- 组织受控的战术解释候选；完整案例化解释仍待战术案例 RAG 和联合 Evidence Gate；
- 生成结构化 Finding。

单 Agent 不可以：

- 直接编造指标；
- 修改原始数据；
- 执行任意 Shell；
- 绕过 Schema 校验；
- 在数据不足时生成确定性结论。

### 6.3 Phase 2B 完成标准

- Agent 能为黄金任务选择正确工具；
- 模型不生成未经计算的数值；
- Finding 引用 MetricArtifact；
- 工具失败返回明确降级状态；
- 黄金任务可重复运行；
- 直接 LLM 和单 Agent 评测结果已保存。

第二批结果已保存于 `data/evaluation/reports/phase2b-latest.json`：确定性直调 7/8、
直接 LLM 2/8、单 Agent 8/8。任务覆盖自然语言范围解析、位置/触球、向前传球、推进带球、
射门参与、缺失范围、越界指标和未知球员；单 Agent 工具序列与结论证据支持率均为 100%。

## 7. Phase 3：MindBridge 协作学习、AgentScope 映射与 Harness

状态：**Phase 3A 多 Agent 首切片与本机 Redis Vector RAG 已完成，进入案例语料和检索评测**

### 7.1 实施顺序

1. 代码级学习 MindBridge 的 Event、Task、Claim、Artifact、Coordinator 和测试；
2. 建立最小领域协作层，实现 Coordinator、Data、Tactical、Evidence 四个角色；
3. 将协作层接入 Workspace、API 和黄金任务评测，保留单 Agent 对照；
4. [x] 在 Harness 前增加入口意图判断；普通聊天交给无工具 ConversationAgent，不启动
   多 Agent 和数据检索；
5. [x] 根据九任务多 Agent `8/9` 结果实现 `ScopeAgent`，使用目录限定工具补齐自然语言
   范围解析；接入后多 Agent 九任务达到 `9/9`；
6. [x] 将二分类入口扩展为结构化 `ExecutionPlan`，分别表达比赛数据、规则 RAG、战术
   RAG、多 Agent 和范围完整性需求；RAG 未接入时阻断知识类请求；
7. [已完成首个切片] 建立 Redis 外部知识库：规则、战术概念和指标定义的正文、向量、
   版本来源元数据持久化到 Redis 8 Vector Sets；`ExecutionPlan -> KnowledgeAgent ->
   search_knowledge -> KnowledgeEvidenceArtifact` 已贯通。当前用确定性字符哈希向量，不是
   语义 Embedding；授权案例、模板和检索评测待补；Redis 故障不回退本地语料；
8. [已完成首个切片] 新增 `KnowledgeAgent`：纯规则问答只走知识链，复杂战术问题已经能
   在 Board 中合并数据证据与知识证据；
9. [已完成首个切片] 新增 `TacticalHypothesisArtifact`，让 KnowledgeAgent 发布事实、知识引用和推断；
10. [已完成首个切片] 实现 Evidence critique -> Tactical revision 一次有限循环，记录
    critique、revision 和重新审核事件；
11. [已完成首个切片] 为 claim、检索、审核、修订和 final accept 增加用户态 SSE；
12. [已完成首个切片] 扩充并接通数据 + 知识联合分析黄金任务；继续补齐规则问答、战术概念和纯数据对照；
13. [已完成首个切片] 为 AgentScope App 锁定 `service`、`storage-redis`、`storage-sql` 和
   `aiomysql`，修复 `agentscope.app` 缺少 `apscheduler` 的导入条件，并完成 Redis/MySQL-backed
   最小启动；
14. [进行中] 建立 AgentScope 2.0.5 App/Team 能力 Spike，验证 `create_app` 挂载现有 FastAPI、
   Session、Storage、WorkspaceManager、MessageBus、任务工具、团队通信、取消和错误传播；
15. 将 Coordinator 定义为 Team Leader，将 Scope、Data、Knowledge、Tactical、Evidence 定义为
   `SubAgentTemplate`，分别配置 Prompt、`ReActConfig`、权限和工具白名单；
16. 通过 `extra_agent_tools` 向框架注入 FootOps 只读 Tools，不直接导入 App 私有工具类；
17. 使用框架提供的 Agent 创建/邀请/团队通信和 Task Tools 完成有限协作循环；
18. 将 AgentScope Session/Task/Event 映射为 FootOps `AnalysisWorkspace`、Artifact 和 SSE；
19. 复用现有确定性 Evidence Gate，模型审核角色不能替代最终门禁；
20. 实现 Checkpoint/Resume、用户取消、依赖分析和局部重算；
21. 为 AgentScope 框架状态选择 Redis 或 SQL Storage，为实时传输选择 InMemory 或 Redis
    MessageBus；FootOps Artifact 仍通过 Repository Protocol 持久化；
22. 实现异步报告和导出队列；
23. 与单 Agent 运行消融实验；
24. 只有 Spike 证明 AgentScope 存在明确缺口时，才新增薄的领域状态投影或适配器，
    并记录 ADR；Phase 3A 领域 Board 不得膨胀成自研通用 MessageBus、Storage 或 Scheduler。

### 7.2 Phase 3 完成标准

- 复杂分析可由 AgentScope Team Leader、SubAgent、Task Tools 和 MessageBus 完成任务分发；
- AgentScope 负责通信和通用任务状态，业务结果只通过强类型 Artifact 引用交付；
- Evidence Gate 能阻断无证据高置信结论；
- 规则、战术知识和比赛数据能被正确路由，纯知识问题不下载比赛数据；
- 联合分析同时生成数据证据、知识证据和可区分的战术推断；
- Knowledge RAG 引用可回到版本化来源和原文位置；
- TacticalAgent 能根据 Evidence critique 完成有限修订或明确拒绝；
- 工具超时后可以重试或降级；
- Run 可以取消和恢复；
- 用户修改范围只重算受影响 Artifact；
- 多 Agent 与单 Agent 的质量、延迟和费用对照完成；
- 没有重复实现 AgentScope 已提供的通用编排能力；任何替代实现都有失败测试和 ADR。

若多 Agent 没有带来可测质量收益，对应请求继续使用单 Agent。

## 8. Phase 4：Engineering Harness

状态：**Phase 3 后系统化建设**

实施内容：

- 固定数据 Fixture；
- 黄金任务评测集；
- 人工、直接 LLM、单 Agent 和多 Agent 对照；
- 路由准确率评测；
- Metric Consistency；
- Claim Support Rate；
- Citation Correctness；
- Board Schema Validity；
- 超时、限流、数据缺失和工具失败注入；
- Checkpoint 恢复和局部重算测试；
- Trace、延迟、Token 和费用分析；
- 模型、Prompt 和 Skill 回归。

未通过 Engineering Harness 测量的收益不得写成已经取得的成果。

## 9. Phase 5：Java 业务平台

状态：**可选，不是 MVP 前置条件**

Java 负责：

- 用户和组织；
- 登录、权限和审计；
- 订阅和运营后台；
- 内容发布；
- 业务高并发接口。

Python 负责：

- Agent Runtime；
- Harness；
- Skills 和 Tools；
- Artifacts；
- 战术分析；
- Evidence Gate。

Java 通过 HTTP/SSE 调用 Python Agent Service。Python 服务必须能够脱离 Java
独立运行。

## 10. 阶段闸门

| 阶段切换 | 必须满足 |
| --- | --- |
| Phase 1 -> 2A | 静态原型和需求基线完成 |
| Phase 2A -> 2B | 真实数据、指标、API 和动态前端链路稳定 |
| Phase 2B -> 3 | 单 Agent 黄金任务和评测基线稳定，并已冻结 AgentScope 2.0.5 能力清单 |
| Phase 3 -> 4 | AgentScope Team、Harness 映射、恢复和证据审核可测试 |
| Phase 4 -> 5 | 业务价值和技术收益已有实测结果 |

不得为了展示技术栈跳过阶段闸门。

## 11. 当前下一步清单

按顺序执行：

- [x] 创建数据覆盖审计命令；
- [x] 生成可用比赛和球员清单；
- [x] 确认黄金样例；
- [x] 创建核心 Pydantic Schema；
- [x] 创建对应 TypeScript 类型；
- [x] 编写 OpenAPI 初版；
- [x] 建立 FastAPI `/health`；
- [x] 建立分析创建和查询接口；
- [x] 删除前端硬编码业务结果，未实现区域改为空状态；
- [x] 实现第一个真实数据 Adapter；
- [x] 实现第一个确定性 Metric Service；
- [x] 用真实数据替换一张趋势图；
- [x] 定义 `FindingArtifact` 与 Claim/Evidence 引用；
- [x] 实现确定性 Evidence Gate；
- [x] 用真实描述性 Finding/Evidence 填充回答和证据面板；
- [x] 固化并消费版本化分析 SSE 事件；
- [x] 用 `TacticsBoardArtifact` 驱动战术板。

Phase 2A、Phase 2B、Phase 3A 协作首切片和入口意图路由已完成。普通聊天由
ConversationAgent 直接回复；ScopeAgent 通过目录工具解析自然语言范围并交给多 Agent。
Redis Vector RAG 已把 IFAB 规则、战术概念和指标定义接入本机 Redis 8 的确定性字符向量索引；
分析窗口现在支持同一球员 2 至 10 场，并能生成带审核数值、检索知识参照和限制说明的受限报告。
下一步为向量检索建立黄金评测，补授权比赛案例和战术模板，再继续 AgentScope App/Team
事件投影与行为验证。App/Team 目前仍是独立启动 Spike，未接入 FootOps 默认业务链。

## 12. 开发规范

### 12.1 契约优先

- 前端只依赖业务 Schema；
- AgentScope 类型不得暴露到 HTTP；
- API 和 SSE 变更先修改 `contracts/`；
- Mock 和真实后端必须返回相同结构。

### 12.2 数据优先

- 数据源先审计覆盖再开发功能；
- 原始数据只读保存；
- 标准化数据记录来源和版本；
- 指标代码必须拥有 Fixture 和期望结果。

### 12.3 Agent 克制

- 确定性任务不使用 Agent；
- 工具必须白名单；
- 循环必须有预算和终止条件；
- 多 Agent 必须有单 Agent 基线；
- RAG 只在知识解释需要时启用。

### 12.4 框架优先

- 本地锁定版本和集成测试是 AgentScope API 的事实来源；
- `agentscope.pipeline`/`MsgHub` 不属于本地 2.0.5，不得写入实现计划；
- 团队工具由 AgentScope App 注入，不直接依赖 `_tool` 等私有模块；
- FootOps 只扩展领域 Prompt、Tools、Artifact、Evidence Gate、Workspace 和业务路由；
- 发现框架缺口时先提交失败测试与 ADR，再决定适配、升级或最小自研。

### 12.4 状态诚实

- README 和文档区分已完成、Mock、待实现和规划中；
- 前端演示数据明确标记；
- 未运行的评测不得填写结果；
- 计划中的架构不得描述成现有实现。

## 13. Definition of Done

每个功能完成必须同时满足：

1. 代码已实现；
2. 正常路径可运行；
3. 失败和空数据路径可运行；
4. Schema 已更新；
5. 测试已通过；
6. 文档已更新；
7. 不含未标记的演示数据；
8. 结果可以从来源或 Trace 追溯；
9. 学习手册已新增或更新对应章节；
10. 若涉及 Agent 编排，已证明复用 AgentScope 能力，或附有可复现缺口与 ADR。
