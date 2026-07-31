# FootOps Agent 开发基准索引

> 文档状态：有效
> 基线日期：2026-07-31
> 当前里程碑：Phase 2A 已完成，下一阶段为 Phase 2B 单 Agent MVP

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
   说明如何借鉴 MindBridge 设计 Agent、Harness、Blackboard、Artifact、
   Evidence Gate、Skills、Tools、MCP、记忆、队列和评测。

4. [FOOTOPS_PROJECT_STRUCTURE_STANDARD.md](./FOOTOPS_PROJECT_STRUCTURE_STANDARD.md)
   说明从真实 MindBridge 代码学习到的目录职责、定义位置、依赖方向和文件放置标准。

5. [FOOTOPS_DEVELOPMENT_ORDER.md](./FOOTOPS_DEVELOPMENT_ORDER.md)
   说明当前进度、下一步任务、阶段顺序、阶段闸门和 Definition of Done。

6. [FOOTOPS_DEVELOPMENT_LEARNING.md](./FOOTOPS_DEVELOPMENT_LEARNING.md)
   按实际开发顺序讲解每个切片的作用、调用链位置、MindBridge 对照、代码入口、
   验证方法、当前边界和后续连接，供持续学习与复盘。

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
- 三条描述性 Finding 和确定性 Evidence Gate 已接入真实五场数据与前端；
- `TacticsBoardArtifact` 已把审核后的位置变化映射到可编辑战术板；阵型和传球线路不编造；
- 页面首次打开为空白，用户提交问题后才通过 SSE 创建真实 Workspace；
- 尚未生成的战术因果结论和报告显示为空状态；
- Python Agent Service 已完成首个可运行切片；
- 追问已接入 FastAPI、Harness、AgentScope 和 DeepSeek 结构化规划链路；
- 当前 Harness 已实现 `run_id`、输入限制、超时和统一错误映射；
- StatsBomb Open Data 覆盖审计、历史五场快照和 v1 确定性指标已经跑通；
- AnalysisWorkspace 创建/查询/SSE、状态机和进程内 Repository 基线已经实现；数据库
  落库和前端跨刷新恢复尚未实现；
- Agent Tools 和多 Agent 尚未实现；
- 当前下一步是把确定性数据与指标注册为只读 Tools，开始 Phase 2B 单 Agent MVP。

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
9. 多 Agent 必须通过单 Agent 对照实验证明价值；
10. RAG 和微调不是项目核心卖点；
11. Python Agent Service 必须能够独立运行；
12. Java 平台只能通过稳定 HTTP/SSE 契约接入；
13. 未经过评测的收益不得写成已取得成果；
14. 演示数据不得伪装成真实分析；
15. 每完成一个可运行开发切片，必须在学习手册中按开发顺序说明它为什么存在、
    在系统中的作用、与 MindBridge 同类能力的共同点和差异、如何验证及当前边界。

## 6. 冲突处理

文档发生冲突时按以下优先级处理：

1. 产品需求和验收标准；
2. 数据真实性与安全边界；
3. 开发阶段闸门；
4. 架构设计；
5. 框架和模型选型。

框架能力不能反向扩大产品需求，计划架构不能描述成当前已实现能力。
