# FootOps 球员多场描述性指标定义 v1

> 算法版本：`footops-player-role-v1`
> 坐标口径：StatsBomb 标准化 120 x 80 事件坐标
> 实现位置：`services/agent/src/footops_agent/services/metric_engine.py`

## 1. 输入约束

本版本是**单球员、多场事件指标**，不是整场比赛或球队级分析。Provider 原始事件中
可以包含 `Shot`，当前指标层支持基础射门次数、射门参与和 StatsBomb 提供时的球员 xG
（不代表已经支持完整射门质量分析）。

指标输入只能是经过 Provider 标准化的 `MatchDataSnapshot`：

- 所有快照必须属于同一球员；
- 每个事件保留 `event_id`、`match_id`、事件类型和坐标；
- 数值只由确定性 Python 代码计算；
- Prompt、模型输出和自然语言结论不能作为数值输入；
- 单个 Artifact 最多包含 10 场比赛。

## 2. 触球代理事件

`touch_event_count` 使用以下带 `location` 的球员事件作为可复算代理：

```text
Ball Receipt*
Ball Recovery
Carry
Clearance
Dispossessed
Dribble
Interception
Miscontrol
Pass
Shot
```

它不等同于其他数据商定义的官方 touches，因此 UI 和报告必须显示具体口径。

## 3. 指标公式

| 字段 | 输入 | 公式 | 单位 | 空值规则 |
| --- | --- | --- | --- | --- |
| `event_count` | 目标球员全部事件 | 事件条数 | 次 | 无事件为 0 |
| `touch_event_count` | 触球代理事件 | 带坐标事件条数 | 次 | 无事件为 0 |
| `average_touch_x` | 触球代理事件 x | `sum(x) / n` | 0-120 坐标 | `n=0` 返回 `null` |
| `average_touch_y` | 触球代理事件 y | `sum(y) / n` | 0-80 坐标 | `n=0` 返回 `null` |
| `attacking_third_touch_count` | 触球代理事件 | `x >= 80` 的条数 | 次 | 无事件为 0 |
| `attacking_third_touch_ratio` | 上述两项 | `进攻三区条数 / 触球代理条数` | 0-1 | 分母为 0 返回 `null` |
| `penalty_area_touch_count` | 触球代理事件 | `x >= 102 and 18 <= y <= 62` | 次 | 无事件为 0 |
| `penalty_area_touch_ratio` | 上述两项 | `禁区条数 / 触球代理条数` | 0-1 | 分母为 0 返回 `null` |
| `receipt_count` | `Ball Receipt*` | 带坐标接球事件条数 | 次 | 无事件为 0 |
| `average_receipt_x` | 接球事件 x | `sum(x) / n` | 0-120 坐标 | `n=0` 返回 `null` |
| `forward_pass_count` | Pass 起终点 | `end_x > start_x` 的传球条数 | 次 | 缺任一坐标则排除 |
| `completed_forward_pass_count` | 向前传球 outcome | outcome 缺失或为 `Complete` | 次 | 无向前传球为 0 |
| `progressive_carry_count` | Carry 起终点 | `end_x - start_x >= 10` | 次 | 缺任一坐标则排除 |
| `key_pass_count` | Pass 属性 | 有 `assisted_shot_id`、`shot_assist` 或 `goal_assist` | 次 | 无为 0 |
| `shot_count` | Shot | Shot 事件条数 | 次 | 无为 0 |
| `expected_goals` | Shot 的 `statsbomb_xg` | 该球员单场射门 xG 求和 | xG | 无射门为 0；任一射门缺 xG 时该场为 `null` |
| `shot_involvement_count` | key pass + shot | 两者之和 | 次 | 无为 0 |

平均值保留三位小数，比率保留四位小数。图表显示可以格式化，但不得覆盖 Artifact
中的原始计算值。

### 3.1 Finding 覆盖

当前 `DeterministicFindingBuilder` 最多为以下 11 个指标生成可审核的跨比赛描述性 Finding；
仅当所有样本比赛都有 xG 值时才生成 xG Finding：

`average_touch_x`、`attacking_third_touch_ratio`、`penalty_area_touch_ratio`、
`average_receipt_x`、`forward_pass_count`、`completed_forward_pass_count`、
`progressive_carry_count`、`key_pass_count`、`shot_count`、`expected_goals`、
`shot_involvement_count`。

宽泛的角色/近期表现问题不会一次堆满全部指标，而是选择触球位置、进攻三区、接球位置、
成功向前传球、推进带球和射门参与 6 个代表性 Finding；明确问题只选择相关指标。
次数类 Finding 当前是所选比赛的场均次数，尚未按出场分钟或球队控球时间归一化，必须在
limitations 中披露。`shot_involvement_count` 只是射门与关键传球之和，不代表进球或完整进攻贡献。
公开数据不保证每场每次射门都有 xG；缺值时不得补零或由模型估算。

## 4. 适用范围

v1 指标可以支持：

- 单个球员在连续多场比赛中的描述性趋势；
- 比较多场比赛的持球活动高度；
- 比较进攻三区和禁区参与比例；
- 比较接球区域变化；
- 比较向前传球、持球推进、关键传球和射门参与。

v1 指标不能单独支持：

- 无球跑位、压迫覆盖和完整跑动距离；
- 教练指令或球员主观战术职责；
- 跨数据源直接对比；
- 因果判断；
- 整场比赛的两队战术结构和比赛阶段复盘；
- 射正、射门方式、整队机会质量等高级射门分析；球员 xG 只在来源数据提供时支持；
- 职业训练、临场决策或博彩判断。

## 5. 变更规则

修改事件集合、区域边界、阈值、完成规则或空值规则时，必须：

1. 新增算法版本，不能悄悄覆盖 `footops-player-role-v1`；
2. 更新 Fixture 和确定性期望值；
3. 重新运行黄金样例；
4. 更新 JSON Schema、本文档和当前进度；
5. 旧 Workspace 保留原算法版本，不能自动改写历史数值。
