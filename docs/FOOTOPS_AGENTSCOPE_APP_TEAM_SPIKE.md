# FootOps AgentScope App/Team Spike

> 状态：Phase 3B 预研，未接入默认运行链
> 更新：2026-08-07

## 1. 目的

FootOps 当前已经有一套面向业务的事件驱动协作层：`Coordinator` 维护
`CollaborationBoard`，领域 Agent 通过 capability claim 发布 Artifact，
`EvidenceAgent` 审核后由 Coordinator Final Accept。它负责的是 FootOps 的业务边界、
证据门禁和可复算性。

AgentScope App/Team 负责的是可复用的服务运行时：会话、团队成员、跨会话消息、
SubAgent 模板、Workspace、Storage 和 HTTP 路由。本 Spike 的目标不是把两套模型
强行合并，而是验证 AgentScope 能否作为上层运行容器承载 FootOps 现有业务编排。

## 2. 本地审计结果

| 项目 | 结果 | 说明 |
| --- | --- | --- |
| AgentScope | `2.0.5` | 已安装，现有 ReAct/Toolkit/结构化输出链路正在使用 |
| `agentscope.app.create_app` | 可从源码确认 | 可创建独立 FastAPI App，也可 mount 到现有 FastAPI |
| `SubAgentTemplate` | 可用 | 通过 `custom_subagent_templates` 注册角色模板 |
| Team 工具 | 已存在 | `TeamCreate`、`AgentCreate`、`TeamSay`、`TeamDelete` |
| service extra | 已安装 | `apscheduler`、`ag-ui-protocol` 已安装，最小 App 可启动 |
| Storage | Redis/MySQL 均已验证 | Redis Storage 已连通；独立 MySQL `footops_agentscope` 已初始化 8 张 AgentScope 表 |
| Workspace | 有 Local/Docker 等 Manager | 当前 FootOps `AnalysisWorkspace` 仍是业务 Artifact，不等同于文件沙箱 |

当前 Spike 已安装 `agentscope[service,storage-redis,storage-sql]==2.0.5` 和 `aiomysql`，
默认使用 Redis 的 15 号逻辑库作为本地隔离环境；MySQL 对照库为独立的
`footops_agentscope`。默认 FootOps API 仍使用自己的进程内 Workspace Repository，不会被
这条实验链改写。

### 2.1 已确认的 App 入口

AgentScope 2.0.5 的 App 工厂接口为：

```python
agentscope.app.create_app(
    storage=...,                         # 会话、Agent、Team 等持久化
    message_bus=...,                     # 跨会话/成员消息
    workspace_manager=...,               # 运行工作区
    custom_subagent_templates=[...],     # 角色化 SubAgent 模板
)
```

它既可以独立运行，也可以挂载到 FootOps 的 FastAPI 根应用。App 层内置的 Team 工具
由 Leader Agent 决定何时创建团队、何时创建成员、何时发送 `TeamSay`；这与 FootOps
当前由业务 `Coordinator` 按 Artifact 缺口推进的编排策略不同。

## 3. FootOps 映射方案

| FootOps 业务概念 | AgentScope App/Team 对应物 | 责任边界 |
| --- | --- | --- |
| `CoordinatorAgent` | App 中的 Leader Agent / Team Leader | 保留 FootOps 的最终采纳和预算规则，不把最终裁决交给自由聊天 |
| `DataAgent` | `SubAgentTemplate(type="data")` | 读取赛事工具，发布 `MatchDataSnapshot` |
| `TacticalAgent` | `SubAgentTemplate(type="tactical")` | 读取数据与知识，发布 Finding/Hypothesis |
| `KnowledgeAgent` | `SubAgentTemplate(type="knowledge")` | 调用只读 `search_knowledge`，发布 Knowledge Artifact |
| `EvidenceAgent` | `SubAgentTemplate(type="evidence")` | 独立审核 Evidence Gate，不能直接改写原始数据 |
| `CollaborationBoard` | Team Task/Message 的运行投影 | Board 仍是业务事实源，Team 消息只是调度和通知 |
| FootOps Artifact | Session/Task Context 中的业务载荷引用 | 传递 `artifact_id` 和版本，不把完整 Artifact 塞进自然语言消息 |
| `AnalysisWorkspace` | 业务 Workspace | 不与 AgentScope 文件沙箱混用；前者面向战术分析，后者面向运行资源隔离 |
| 现有 FastAPI `/api/v1/agent/runs` | App mount 或外部业务 API | 保持现有前端契约和 SSE，不要求用户理解 AgentScope 内部协议 |

### 3.1 计划中的团队拓扑

```text
用户请求
  -> FootOps ScopeAgent / IntentRouter
  -> App Leader / Coordinator
      -> DataTemplate       -> MatchDataSnapshot
      -> KnowledgeTemplate  -> KnowledgeAnswer / Evidence
      -> TacticalTemplate   -> Finding / Hypothesis
      -> EvidenceTemplate   -> EvidenceReview
  -> Coordinator Final Accept
  -> AnalysisWorkspace + SSE
```

其中 `KnowledgeAgent` 是否参与、`DataAgent` 是否参与，仍由 ExecutionPlan 和
Artifact 缺口决定；不会为了展示“多 Agent”而固定调用全部成员。

## 4. 迁移策略

### 阶段 A：无破坏映射 Spike

1. 安装并锁定 AgentScope `service` extra 的依赖版本；
2. 用内存 Storage、内存 MessageBus、LocalWorkspaceManager 启动最小 App；
3. 注册 `data/knowledge/tactical/evidence` 四个 `SubAgentTemplate`；
4. 用一个测试 Team 验证 Leader 创建成员、成员回报和会话结束；
5. 将 Team 事件投影为 FootOps collaboration event，但不改变现有 Board 写入逻辑。

### 阶段 B：业务适配

1. 让 Leader 只负责调度，所有业务结论仍经过 FootOps Artifact Schema；
2. 将 `TeamSay` 的自由文本收敛为 `task_id`、`artifact_id`、`artifact_version` 和状态；
3. 复用现有 Evidence Gate、revision budget 和 Final Accept；
4. 对比领域 Coordinator 与 App/Team Leader 的耗时、失败恢复、可审计性和测试成本。

### 阶段 C：持久化与生产化

1. 再决定是否接 `AsyncSQLAlchemyStorage` 或 Redis；
2. 将会话、Team、Artifact、trace 分别定义生命周期和迁移；
3. 保留当前 FastAPI 业务入口，App 作为内部运行时或挂载子应用；
4. 只有通过回归和故障注入后，才考虑替换默认协作实现。

## 5. 验收标准

- 普通对话不创建 Team，不触发比赛数据工具；
- 规则/指标口径问题只创建 Knowledge 任务，不创建 Data 任务；
- 综合战术问题能按 ExecutionPlan 缺口调度成员，而不是固定顺序跑完所有 Agent；
- 每个成员只能发布声明过的 Artifact，EvidenceAgent 能拒绝无来源或越权结论；
- Leader/Team 消息断线后可以从任务状态和 Artifact 版本恢复，而不是依赖聊天文本；
- 现有 `/api/v1/agent/runs`、SSE、前端 Workspace 和 84 项回归测试不回归；
- App/Team 运行耗时、Token、失败和重试进入现有 trace/评测体系。

Team 行为验证脚本为 [agentscope_team_spike.py](../scripts/agentscope_team_spike.py)，
它会创建 Leader Session，调用 `TeamCreate` 和 `AgentCreate(data)`，检查 `TeamMember`
落库后再清理临时团队。建议使用独立 MySQL 库运行：

```bash
FOOTOPS_AGENT_SCOPE_DATABASE_URL='mysql+aiomysql://root:<password>@127.0.0.1:3306/footops_agentscope?charset=utf8mb4' \
  .venv/bin/python scripts/agentscope_team_spike.py
```

当前脚本已经通过 Ruff 和 Python 语法检查；由于本轮本地执行审批通道中断，Team 行为
脚本尚未完成最后一次带凭据运行，不能把它标记为已通过。

## 6. 当前结论

AgentScope 已经参与 FootOps 的 Agent、Toolkit、ReAct 和结构化输出，但 **AgentScope
App/Team 尚未接入 FootOps 默认业务链**。当前最合理的架构是：FootOps
Harness/Board/Artifact 继续作为业务控制面，AgentScope App/Team 作为已经可启动、但仍
可选的会话与团队运行容器。下一步要验证 Team 行为和 Artifact 投影，再决定是否接入默认链路。

最小 Spike 可重复运行：

```bash
.venv/bin/python scripts/agentscope_app_spike.py
FOOTOPS_AGENT_SCOPE_DATABASE_URL='mysql+aiomysql://root:<password>@127.0.0.1:3306/footops_agentscope?charset=utf8mb4' \
  .venv/bin/python scripts/agentscope_app_spike.py --storage mysql
```

通过条件是输出 `status=ready`、四个模板类型（`data`、`knowledge`、`tactical`、
`evidence`）以及服务路由存在。MySQL 只用于本地持久化对照，待 Team 行为和业务
Artifact 投影通过后，再决定是否让它承载正式会话；密码只能通过环境变量提供。
