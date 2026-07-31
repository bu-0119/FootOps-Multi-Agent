# FootOps 架构图

本目录保存 FootOps 架构图的可维护 SVG 源文件和 1920 x 1080 PNG 展示文件。

## 文件

- `footops-system-architecture.svg`：目标系统架构；
- `footops-system-architecture.png`：目标系统架构高清图；
- `footops-agent-collaboration.svg`：Agent 协作与补证回环；
- `footops-agent-collaboration.png`：Agent 协作高清图。

## 状态说明

两张图描述的是目标架构，不代表全部能力已经实现。当前真实进度以
`../FOOTOPS_DEVELOPMENT_ORDER.md` 为准，目前处于 Phase 2A 真实数据纵向链路。

## macOS 渲染

修改 SVG 后执行：

```bash
sips -s format png footops-system-architecture.svg \
  --out footops-system-architecture.png
sips -s format png footops-agent-collaboration.svg \
  --out footops-agent-collaboration.png
```
