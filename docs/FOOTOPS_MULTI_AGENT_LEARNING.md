# FootOps 多 Agent 学习实现

> 当前阶段：Phase 3A ScopeAgent 与事件驱动协作协议已运行
> 参考代码：`/Users/buxy/python/mindbridge-py/app/agents/`
> 目标：学习真正的 Agent 协作机制，而不是用多个类包装固定函数链

## 1. 为什么现在进入多 Agent

FootOps 是 Agent 架构学习项目。足球分析是可验证的业务载体，不是项目最终要追求的
专业数据深度。Phase 2B 已建立单 Agent、Tool、Skill、Harness 和黄金任务基线；继续
增加指标的学习收益开始低于实现协作协议。因此当前主线改为多 Agent 编排，现有单 Agent
保留为对照组。

## 2. 从 MindBridge 学到的核心

MindBridge 的多 Agent 不等于依次调用四个函数。它包含：

1. `CollaborationBlackboard` 保存不可覆盖的 Task、Artifact 和 Event；
2. Coordinator 根据缺失 Artifact 创建任务，不写死 Agent 调用链；
3. Agent 根据 capability、当前状态和置信度 claim 任务；
4. 生成者不能采纳自己的结果，独立审核通过后 Coordinator 才能接受最终 Artifact；
5. 轮次和 claim 数受预算约束，未满足停止条件时不能伪装成完成。

## 3. MindBridge 与 FootOps 文件映射

| MindBridge | FootOps | 作用 |
| --- | --- | --- |
| `app/agents/events.py` | `collaboration/events.py` | Task、Artifact、Event、不可变 Board |
| `app/agents/registry.py` | `collaboration/registry.py` | capability、claim decision、候选排序 |
| `app/agents/coordinator.py` | `collaboration/coordinator.py` | 缺失工作推导、轮次预算、最终采纳 |
| `app/agents/autonomous.py` | `agents/collaborative.py` | 领域 Agent 的 decide/act 和工具权限 |
| `app/agents/event_driven_runtime.py` | `runtime/multi_agent.py` | 组装 Agent、Board、Repository 与 Workspace |
| `tests/test_event_driven_multi_agent.py` | `tests/test_multi_agent.py` | 不可变性、claim 顺序、预算与采纳测试 |

## 4. 当前角色

| 角色 | 能力 | 可访问工具 | 产物 |
| --- | --- | --- | --- |
| `CoordinatorAgent` | 协调与采纳 | task board、final accept | Workspace 最终采纳事件 |
| `ScopeAgent` | 前置范围解析 | 赛事目录、球员目录 | `ScopeResolutionArtifact` |
| `DataAgent` | 数据与指标 | Provider 读取、Metric Engine | `data_bundle` |
| `TacticalAgent` | 候选分析与战术投影 | Finding Builder、Tactics Builder | `finding_bundle`、`tactics_bundle` |
| `EvidenceAgent` | 独立审核 | Evidence Gate | `review_bundle` |

综合角色问题的真实 claim 顺序为：

```text
DataAgent
  -> TacticalAgent(findings)
  -> EvidenceAgent(review)
  -> TacticalAgent(tactics)
  -> CoordinatorAgent(final accept)
```

向前传球等不需要位置战术板的问题不会创建 tactics 任务，说明 Coordinator 是根据缺失
Artifact 推导工作，不是固定四步流水线。

## 5. 当前运行入口

```http
POST /api/v1/multi-agent/analyses
POST /api/v1/multi-agent/runs
```

`analyses` 保留显式范围的确定性调试入口；`runs` 接收自然语言和可选范围 hint，先由
ScopeAgent 使用只读目录工具生成强类型 Scope，再启动协作 Board。Trace 只包含工具摘要、
任务、Agent、Artifact ID 和事件，不包含模型思维过程或原始 Artifact payload。

四模式黄金任务结果保存在：

```text
data/evaluation/reports/phase3-latest.json
```

当前九任务结果：确定性直调 `7/9`、直接 LLM `3/9`、单 Agent `9/9`、多 Agent `8/9`。
新增的普通问候任务会先被入口 Router 识别并交给 `ConversationAgent`，不创建协作 Board、
不访问数据工具。多 Agent 唯一失败是无 scope hint 的自然语言范围解析，这证明下一步需要
`ScopeAgent`，而不是继续增加足球指标。

ScopeAgent 后续切片已补齐该失败：多 Agent 九任务 `9/9`，平均 `3361.8 ms`，Token 共
`25716`。自然语言任务的真实顺序为 search_competitions -> search_players -> Data ->
Tactical -> Evidence -> Tactical；报告位于
`data/evaluation/reports/phase3-scope-agent-latest.json`。

## 6. 入口路由与正常回复

MindBridge 的入口不是所有消息都启动多 Agent。FootOps 现在采用相同原则：

```text
用户消息
  -> RequestIntentRouter
     -> chat: ConversationAgent -> 普通回复
     -> analysis: AnalysisAgent 或 MultiAgentRuntime -> 数据与证据链
```

`ConversationAgent` 使用 AgentScope 和 DeepSeek，但不注册数据工具；响应显式标记
`status=chat`、`data_retrieved=false`、`workspace=null`。这样普通问候不会生成假的分析
结果，也不会为了展示编排而浪费多 Agent 成本。当前 Router 先用可测试的确定性规则完成
入口粗分；已实现的 `ScopeAgent` 负责分析分支内的赛事、赛季、球员和窗口解析，两者职责
不同。

## 7. 当前边界

Phase 3A 的 Worker 先使用确定性领域服务，以隔离“编排是否正确”和“模型是否聪明”两个
变量。它已经是可运行的多角色 claim/Artifact/审核/采纳协议，但尚不是 AgentScope App/Team，
也不能宣称多 Agent 优于单 Agent。

当前没有复制 MindBridge 的私有记忆、Agent Message、revision/critique 循环、并发 claim、
Checkpoint 或 MessageBus；这些能力必须按学习顺序逐项实现并评测。

## 8. 接下来的学习顺序

1. [x] 实现 `ScopeAgent`，用 AgentScope + 受控目录工具解析自然语言赛事、赛季和球员；
2. [x] 将入口路由升级为结构化 ExecutionPlan，区分规则、战术知识、比赛数据和联合分析；
3. 建立 Knowledge RAG 和 `KnowledgeEvidenceArtifact`，新增 KnowledgeAgent；
4. 为 TacticalAgent 增加 `TacticalHypothesisArtifact`，同时引用数据与知识证据；
5. 实现 EvidenceAgent 的 critique/revision 事件和有限返工循环；
6. 将多 Agent 加入 SSE，让前端只显示用户可理解的阶段，不暴露内部术语；
7. 安装并验证 AgentScope `service`/Storage extras，把当前领域协议映射到 App/Team；
8. 比较“当前薄协作层”和“AgentScope Team”在正确率、延迟、Token、恢复能力上的差异；
9. 再决定保留哪套运行方式，不能因为框架更新而直接删除已经可测的基线。
