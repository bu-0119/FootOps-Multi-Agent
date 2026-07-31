# FootOps Codex 工作会话

> 建立日期：2026-07-31
> 工作目录：`/Users/buxy/python/FootOps`

为降低长会话断线带来的上下文损失，FootOps 使用一个主协调会话和四个专职
会话。每个专职会话都保存了固定职责和写入边界。

| 会话 | Thread ID | 负责范围 | 唯一写入边界 |
| --- | --- | --- | --- |
| FootOps · 需求文档 | `019fb79d-6c1c-79e2-b2dd-c9a9fc8e31de` | 产品范围、用户场景、V1 功能和验收标准 | `docs/FOOTOPS_REQUIREMENTS.md` |
| FootOps · Agent架构 | `019fb79d-7358-7c81-af39-a5450c9bef50` | MindBridge 对照、AgentScope、Harness、Artifact 与 Evidence Gate | `docs/FOOTOPS_MINDBRIDGE_ARCHITECTURE.md` |
| FootOps · 开发顺序 | `019fb79d-7ac7-7df3-8bec-77ce6f682141` | 阶段依赖、完成标准、测试门槛与变更纪律 | `docs/FOOTOPS_DEVELOPMENT_ORDER.md` |
| FootOps · 实现检查 | `019fb79d-819b-7a81-847f-14710a6693a0` | 前后端实现、契约、测试和文档一致性检查 | `apps/`、`services/`、`contracts/`、`infra/` 和测试 |

## 协作规则

1. 主协调会话负责分派任务、合并结论和处理跨文件冲突。
2. 专职会话修改前必须先读取 `FOOTOPS_CURRENT_PROGRESS.md`，再读取其职责相关的基线文档。
3. 同一时间一份文档只能由对应负责人修改。
4. 实现检查会话只读开发文档，不可自行改写产品或架构基线。
5. 跨边界问题由专职会话记录，再交给主协调会话处理。

## 打开会话

这些是 Codex App 的持久化线程，可在会话列表中按名称打开。也可以从命令行
使用 `codex resume <thread-id>` 恢复，例如：

```bash
codex resume 019fb79d-6c1c-79e2-b2dd-c9a9fc8e31de
```
