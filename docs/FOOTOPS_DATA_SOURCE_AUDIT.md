# FootOps 公开数据覆盖审计

> 审计日期：2026-07-31
> 数据源：StatsBomb Open Data
> 当前用途：Phase 2A 黄金样例，不代表当前赛季数据

## 1. 数据源结论

第一条真实数据链路使用
[StatsBomb Open Data](https://github.com/hudl/open-data)。该仓库公开提供比赛、
阵容和事件 JSON，并要求发布或分享分析时注明 StatsBomb 数据来源并使用其品牌
素材。FootOps 在每个快照中记录具体原始文件 URL、获取时间、来源名称和
[许可证链接](https://github.com/hudl/open-data/blob/master/LICENSE.pdf)。

当前适配器只读访问以下资源：

```text
competitions.json
matches/<competition_id>/<season_id>.json
lineups/<match_id>.json
events/<match_id>.json
```

下载内容缓存在 `data/cache/statsbomb-open/`，该目录已被 Git 忽略。缓存原始 JSON
不被模型修改，标准化快照保留事件 ID 和比赛 ID。

## 2. 黄金样例

审计命令：

```bash
.venv/bin/footops-data-audit \
  --competition-id 11 \
  --season-id 90 \
  --player Pedri \
  --window 5 \
  --metrics \
  --output target/data-audit/pedri-la-liga-2020-21.json
```

审计结果：

| 项目 | 结果 |
| --- | --- |
| 赛事 | Spain / La Liga |
| 赛季 | 2020/2021 |
| competition_id | `11` |
| season_id | `90` |
| 球员 | Pedro González López（Pedri，player_id `30486`） |
| 比赛目录 | 35 场 |
| 有出场位置记录 | 35 场 |
| 已下载并计算事件数据 | 建议窗口中的连续 5 场 |

建议窗口按比赛日期升序：

| 日期 | match_id | 比赛 | 阵容位置记录 |
| --- | --- | --- | --- |
| 2021-04-29 | `3773586` | Barcelona 1-2 Granada | Left Center Midfield |
| 2021-05-02 | `3773695` | Valencia 2-3 Barcelona | Left Center Midfield |
| 2021-05-08 | `3773372` | Barcelona 0-0 Atlético Madrid | Left Center Midfield |
| 2021-05-11 | `3773387` | Levante UD 3-3 Barcelona | Left Center Midfield |
| 2021-05-16 | `3773457` | Barcelona 1-2 Celta Vigo | Left Center Midfield |

这五场满足黄金任务的 3 至 10 场事件数据要求，可以用于开发数据、指标、证据、
图表和战术板的完整链路。

## 3. 已验证能力

- 比赛和赛季目录可下载；
- `Pedri` 昵称可解析为完整球员实体；
- 只保留存在实际位置区间的出场；
- 五场事件文件可下载并标准化；
- 每个数值可以关联事件文件 URL、match_id 和算法版本；
- 同一命令使用本地缓存可以重复运行；
- 整条数据计算链不调用 AgentScope、DeepSeek 或其他模型。

## 4. 限制

1. 这是 2020/2021 历史公开样例，不能回答“今年”或“最近五场”的实时问题；
2. 当前公开覆盖不代表西甲所有赛季或所有球队都可用；
3. 事件数据没有完整无球跑动和连续追踪坐标；
4. 阵容位置名称不能单独证明战术角色变化；
5. 当前 `touch_event_count` 是 FootOps 的事件代理指标，不是商业数据的官方 touches；
6. Finding 和战术解释必须在后续 Evidence Gate 完成后才能对用户展示；
7. 正式发布基于该数据的内容时必须保留 StatsBomb attribution。

## 5. 当前结论边界

本审计只证明“该样例有足够数据并且指标可以计算”，不证明 Pedri 在这五场发生了
任何战术角色变化。页面不会用 Mock 角色结论代替缺失能力；必须等真实 Finding 和
Evidence 链路完成后才能生成结论。
