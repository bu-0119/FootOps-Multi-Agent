# FootOps 架构图

本目录保存 FootOps 架构图的可维护 SVG 源文件和 1920 x 1080 PNG 展示文件。

> 2026-07-31 审计：现有图片仍是自研 `AnalysisBlackboard` 版本，已被
> AgentScope-first 架构修订取代，暂仅用于历史对照。当前权威流程以
> [FOOTOPS_MINDBRIDGE_ARCHITECTURE.md](../FOOTOPS_MINDBRIDGE_ARCHITECTURE.md) 中的
> Mermaid 为准。

## 文件

- `footops-system-architecture.svg`：旧版目标系统架构，待重绘；
- `footops-system-architecture.png`：旧版目标系统架构高清图，待重绘；
- `footops-agent-collaboration.svg`：旧版自研 Blackboard 协作图，待重绘；
- `footops-agent-collaboration.png`：旧版自研 Blackboard 协作高清图，待重绘。

## 状态说明

重绘时必须使用 AgentScope App/Team、`SubAgentTemplate`、Task Tools、MessageBus 与
FootOps Workspace/Artifact 的两层结构。当前真实进度以
`../FOOTOPS_DEVELOPMENT_ORDER.md` 为准，目前处于 Phase 2B 单 Agent MVP。

## macOS 渲染

修改 SVG 后执行：

```bash
sips -s format png footops-system-architecture.svg \
  --out footops-system-architecture.png
sips -s format png footops-agent-collaboration.svg \
  --out footops-agent-collaboration.png
```
