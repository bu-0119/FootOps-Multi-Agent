# FootOps 开发顺序规范

> 文档类型：实施顺序与阶段闸门
> 基线日期：2026-07-31
> 当前阶段：Phase 2A 已完成，进入 Phase 2B 单 Agent MVP

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
3. 先建立单 Agent 基线，再拆分多 Agent；
4. 先定义业务契约，再让前端依赖后端；
5. 先建立评测基线，再宣称技术收益；
6. 简单任务使用确定性服务，不强制 Agent；
7. 每一阶段必须有可以独立运行和验证的产物；
8. 每个可运行切片完成后，必须按开发顺序更新
   [FOOTOPS_DEVELOPMENT_LEARNING.md](./FOOTOPS_DEVELOPMENT_LEARNING.md)，记录作用、
   MindBridge 对照、代码入口、验证方式、当前边界和后续连接。

## 3. 当前进度

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| 产品需求 | 已完成 | 已形成独立需求基线 |
| MindBridge 对照架构 | 已完成 | 已形成目标架构 |
| React 静态原型 | 已完成 | 页面和主要交互可用 |
| 可折叠侧边栏 | 已完成 | 桌面和移动端已设计 |
| 可编辑战术板 | Phase 2A 完成 | `TacticsBoardArtifact` 驱动审核后的位置、区域和移动箭头，支持本地编辑 |
| 分析、证据和图表 | Phase 2A 完成 | 趋势图、描述性 Finding、Evidence Gate 和描述性战术板均消费真实历史数据；战术因果结论和报告未实现 |
| 前后端业务契约 | Phase 2A 完成 | Workspace 创建/查询、分析 SSE、OpenAPI、Artifact/Event JSON Schema 和 TypeScript 类型已生成 |
| Python Agent Service | 部分完成 | LLM 规划切片和确定性数据/指标切片可独立运行 |
| 真实足球数据 | 部分完成 | StatsBomb Open Data 覆盖审计、缓存、标准化和五场黄金样例已验证 |
| 单 Agent | 基础 Spike 完成 | AgentScope 2.0.5 + DeepSeek 只用于结构化规划，尚未接 Tools |
| Workspace | 进程内基线完成 | 状态机、Repository Protocol、创建/查询/SSE 已完成；数据库持久化和前端跨刷新恢复待补 |
| 多 Agent 与完整 Harness | 规划中 | Phase 3 实现 |

当前不能宣称已经完成战术因果分析、数据库持久化工作区或多 Agent 编排。

## 4. Phase 1：前端静态原型

状态：**已完成**

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
- 射门参与；
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

## 6. Phase 2B：单 Agent MVP

状态：**当前阶段**

### 6.1 实施内容

- 复用已完成的 DeepSeek ModelAdapter Spike，接入可执行的单 Agent 链；
- 使用 AgentScope 2.0.5 Agent 内置 ReAct loop；
- 实现问题范围识别和澄清；
- 注册球员角色分析 Skill；
- 允许 Agent 选择只读数据和指标 Tools；
- 生成结构化 FindingArtifact；
- 加入基础上下文压缩；
- 扩展现有 SSE，返回 Agent 工具选择、门禁和停止原因等业务事件；
- 建立直接 LLM 与单 Agent 基线。

### 6.2 单 Agent 边界

单 Agent 可以：

- 理解问题；
- 选择 Skill；
- 选择只读工具；
- 组织战术解释；
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

## 7. Phase 3：多 Agent 与 Harness

状态：**单 Agent 基线完成后开始**

### 7.1 实施顺序

1. 从单 Agent 中提取稳定职责；
2. 实现 CoordinatorAgent；
3. 实现 DataAgent；
4. 实现 TacticalAgent；
5. 实现 EvidenceAgent；
6. 实现 AnalysisBlackboard；
7. 实现 FootOpsAgentHarness；
8. 实现 Evidence Gate；
9. 实现 Checkpoint/Resume；
10. 实现用户取消；
11. 实现依赖分析和局部重算；
12. 接入 Redis 和关系数据库；
13. 实现异步报告和导出队列；
14. 与单 Agent 运行消融实验。

### 7.2 Phase 3 完成标准

- 复杂分析可在 Blackboard 上完成任务分发；
- 每个 Agent 只通过 Artifact 协作；
- Evidence Gate 能阻断无证据高置信结论；
- 工具超时后可以重试或降级；
- Run 可以取消和恢复；
- 用户修改范围只重算受影响 Artifact；
- 多 Agent 与单 Agent 的质量、延迟和费用对照完成。

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
| Phase 2B -> 3 | 单 Agent 黄金任务和评测基线稳定 |
| Phase 3 -> 4 | 多 Agent、Harness、恢复和证据审核可测试 |
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

Phase 2A 清单已经完成。现在进入 Phase 2B 单 Agent MVP；四 Agent 编排仍须等待单 Agent
黄金任务和对照评测通过。

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
9. 学习手册已新增或更新对应章节。
