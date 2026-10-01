# FootOps Agent 开发基准索引

> 文档状态：有效
> 基线日期：2026-07-31
> 当前里程碑：Phase 3A ExecutionPlan 已完成，下一切片为 Knowledge RAG

## 1. 文档说明

FootOps 的开发基准已拆分为职责单一的文档。本文档只保留阅读索引、
冲突处理规则和不可随意改变的核心决策。

## 2. 必读文档

按以下顺序阅读：

1. [FOOTOPS_CURRENT_PROGRESS.md](./FOOTOPS_CURRENT_PROGRESS.md)
   说明当前真正已经实现、仅用于测试的 Mock、尚未开发的能力，以及下一步任务。

2. [FOOTOPS_REQUIREMENTS.md](./FOOTOPS_REQUIREMENTS.md)
   说明为谁开发、解决什么问题、第一版提供什么功能以及如何验收。

3. [FOOTOPS_MINDBRIDGE_ARCHITECTURE.md](./FOOTOPS_MINDBRIDGE_ARCHITECTURE.md)
   说明如何借鉴 MindBridge，并用 AgentScope App/Team、Task、MessageBus 与 FootOps
   Workspace/Artifact 组合 Agent、Harness、Evidence Gate、Skills、Tools、记忆和评测。

4. [FOOTOPS_PROJECT_STRUCTURE_STANDARD.md](./FOOTOPS_PROJECT_STRUCTURE_STANDARD.md)
   说明从真实 MindBridge 代码学习到的目录职责、定义位置、依赖方向和文件放置标准。

5. [FOOTOPS_DEVELOPMENT_ORDER.md](./FOOTOPS_DEVELOPMENT_ORDER.md)
   说明当前进度、下一步任务、阶段顺序、阶段闸门和 Definition of Done。

6. [FOOTOPS_DEVELOPMENT_LEARNING.md](./FOOTOPS_DEVELOPMENT_LEARNING.md)
   按实际开发顺序讲解每个切片的作用、调用链位置、MindBridge 对照、代码入口、
   验证方法、当前边界和后续连接，供持续学习与复盘。

7. [FOOTOPS_MULTI_AGENT_LEARNING.md](./FOOTOPS_MULTI_AGENT_LEARNING.md)
   说明 MindBridge 协作协议如何映射到 FootOps、当前四角色运行链和下一步 AgentScope
   App/Team 对照路线。

## 3. 当前项目定位

FootOps Analyst 是面向足球战术爱好者、足球内容创作者和战术分析学习者的
可验证战术分析 Agent。

第一版黄金任务：

> 分析一名球员在连续 3 至 10 场比赛中的战术角色变化，并交付数据证据、
> 战术结论、趋势图、可编辑战术板和可继续修订的分析工作区。

FootOps 不对标职业俱乐部，不提供训练、医疗、实时指挥或博彩建议。

## 4. 当前真实进度

- 前端静态交互原型已完成；
- 侧边栏和战术板交互已完成；
- 第一张历史五场趋势图已由真实 `PlayerRoleMetricArtifact` 驱动；
- 前端假比赛、假球员、假证据覆盖率、假报告和预设战术图层已删除；
- 十个描述性 Finding 和确定性 Evidence Gate 已接入真实数据与前端；综合问题默认展示
  六个代表性指标，并可切换位置与推进进攻趋势；
- `TacticsBoardArtifact` 已把审核后的位置变化映射到可编辑战术板；阵型和传球线路不编造；
- 页面首次打开为空白，用户提交问题后才通过 SSE 创建真实 Workspace；
- 尚未生成的战术因果结论和报告显示为空状态；
- Python Agent Service 已完成首个可运行切片；
- 追问已接入 FastAPI、Harness、AgentScope 和 DeepSeek 结构化规划链路；
- 当前 Harness 已实现 `run_id`、输入限制、超时和统一错误映射；
- StatsBomb Open Data 覆盖审计、历史五场快照和 v1 确定性指标已经跑通；
- AnalysisWorkspace 创建/查询/SSE、状态机和进程内 Repository 基线已经实现；数据库
  落库和前端跨刷新恢复尚未实现；
- AgentScope 单 Agent、球员角色 Skill、三个受控 Tools、结构化 Decision、自然语言补问、
  短期历史、显式 AgentState/ContextConfig 和版本化 Agent SSE 已实现；
- Phase 3A 已实现 Coordinator/Data/Tactical/Evidence 四角色事件驱动协作、Task Claim、
  Artifact、轮次预算、独立 Evidence Review 和 Final Accept；
- 入口已实现 `RequestIntentRouter` 与无工具 `ConversationAgent`；普通问候不会启动数据
  检索或多 Agent，分析请求才进入受控执行链；
- 独立 ScopeAgent 已使用赛事/球员目录工具解析自然语言范围，模型 ID 必须被 hint 或工具
  唯一候选覆盖；自然语言多 Agent 九任务达到 9/9；
- AgentScope 2.0.5 的 App/Team、`SubAgentTemplate`、任务工具、MessageBus/Storage 已完成
  包源码审计，但项目尚未安装 `service`/Storage extras，也未完成集成；
- 原四模式九任务评测为确定性 7/9、直接 LLM 3/9、单 Agent 9/9、多 Agent 8/9；
  ScopeAgent 接入后多 Agent 达到 9/9。ExecutionPlan 已完成；当前下一步是 Knowledge
  RAG 和联合推理，再进入 AgentScope App/Team 映射。

逐层状态和验证记录以
[FOOTOPS_CURRENT_PROGRESS.md](./FOOTOPS_CURRENT_PROGRESS.md) 为准。

## 5. 核心固定决策

1. 第一版主线是职业比赛的赛后战术分析；
2. 目标用户是战术爱好者和内容创作者；
3. 第一版黄金任务是球员多场角色变化；
4. 正式指标由确定性代码计算；
5. 用户主界面不展示内部 Agent 和 Harness 术语；
6. 复杂结论必须可追溯到指标和来源；
7. 战术板由结构化 Artifact 驱动；
8. 先真实数据，再单 Agent，最后多 Agent；
9. 多 Agent 学习实现必须保留单 Agent 对照；未证明收益时不能替代默认业务路径；
10. RAG 不是比赛事实数据库；它只承载版本化规则、战术概念、案例、指标口径和分析模板；
11. Python Agent Service 必须能够独立运行；
12. Java 平台只能通过稳定 HTTP/SSE 契约接入；
13. 未经过评测的收益不得写成已取得成果；
14. 演示数据不得伪装成真实分析；
15. 每完成一个可运行开发切片，必须在学习手册中按开发顺序说明它为什么存在、
    在系统中的作用、与 MindBridge 同类能力的共同点和差异、如何验证及当前边界。
16. Phase 3A 可用最小领域 Board 学习 MindBridge 的协作语义；通用团队通信、Session、
    MessageBus 和 Storage 仍优先映射到本地锁定的 AgentScope 版本；
17. FootOps 自研边界是足球领域路由、Artifact、AnalysisWorkspace、Evidence Gate、
    数据指标和稳定 HTTP/SSE，而不是另一套通用多 Agent 框架；
18. 本地 `agentscope==2.0.5` API 与集成测试优先于官网其他版本示例，当前不得使用
    本地不存在的 `agentscope.pipeline`/`MsgHub` 设计。
19. 目标路由必须区分普通对话、知识检索、数据分析和数据 + 知识联合分析；
20. 复杂战术结论必须区分数据事实、知识引用和推断，并经过 Evidence critique/revision；
21. 当前十项确定性指标和两类趋势图只是黄金链路基线，不是 FootOps 最终分析能力上限。
22. ScopeAgent 只解析范围；它不能读取比赛事件、计算指标或生成战术结论。

## 6. 冲突处理

文档发生冲突时按以下优先级处理：

1. 产品需求和验收标准；
2. 数据真实性与安全边界；
3. 开发阶段闸门；
4. 架构设计；
5. 框架和模型选型。

框架能力不能反向扩大产品需求，计划架构不能描述成当前已实现能力。
