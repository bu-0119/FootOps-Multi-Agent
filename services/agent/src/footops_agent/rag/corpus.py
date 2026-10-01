"""Small, versioned corpus used by the first Knowledge RAG learning slice."""

from dataclasses import dataclass
from datetime import date
from typing import Literal

KnowledgeDomain = Literal["rule", "tactics", "case", "metric_definition"]

IFAB_CORPUS_VERSION = "ifab-laws-2026-27.v1"
FOOTOPS_KNOWLEDGE_CORPUS_VERSION = "footops-knowledge-2026-08.v1"
IFAB_EFFECTIVE_FROM = date(2026, 7, 1)


@dataclass(frozen=True)
class KnowledgeDocument:
    """Curated source passage; summaries are FootOps-authored paraphrases."""

    document_id: str
    domain: KnowledgeDomain
    title: str
    section: str
    summary: str
    search_text: str
    keywords: tuple[str, ...]
    source_url: str
    source_authority: str = "The International Football Association Board (IFAB)"
    source_version: str = "Laws of the Game 2026/27"
    effective_from: date = IFAB_EFFECTIVE_FROM
    language: str = "zh-CN"


IFAB_2026_27_DOCUMENTS: tuple[KnowledgeDocument, ...] = (
    KnowledgeDocument(
        document_id="ifab-2026-27-law11-position",
        domain="rule",
        title="IFAB Law 11: Offside position",
        section="11.1 Offside position",
        summary=(
            "处于越位位置本身不构成犯规。判断位置时看队友触球的时刻：球员位于对方"
            "半场，且头、躯干或脚比球和倒数第二名防守队员更接近球门线，才属于越位"
            "位置；手和手臂不参与位置判断。"
        ),
        search_text=(
            "越位位置 判断时点 队友传球 触球 瞬间 对方半场 倒数第二名防守球员 "
            "头 躯干 脚 手臂 offside position second-last opponent"
        ),
        keywords=("越位位置", "判断时点", "倒数第二名防守球员"),
        source_url="https://www.theifab.com/laws/latest/offside/#offside-position",
    ),
    KnowledgeDocument(
        document_id="ifab-2026-27-law11-active-play",
        domain="rule",
        title="IFAB Law 11: Offside offence",
        section="11.2 Becoming involved in active play",
        summary=(
            "越位位置的球员只有随后参与实际比赛才会被判罚，包括触及队友传来的球、"
            "干扰对手处理球，或在反弹、折射和对手扑救后获得利益。单纯站在越位位置"
            "而没有产生这些影响，不应直接判罚。"
        ),
        search_text=(
            "越位犯规 参与实际比赛 干扰比赛 干扰对手 获得利益 触球 视线 挑战球 "
            "active play interfering opponent gaining advantage"
        ),
        keywords=("参与实际比赛", "干扰对手", "获得利益"),
        source_url="https://www.theifab.com/laws/latest/offside/#offside-offence",
    ),
    KnowledgeDocument(
        document_id="ifab-2026-27-law11-deliberate-play",
        domain="rule",
        title="IFAB Law 11: Deliberate play by an opponent",
        section="11.2 Deliberate play indicators",
        summary=(
            "判断防守方是否属于主动处理球，核心是球员当时是否控制了球并有可能传球、"
            "取得控球或解围。可参考来球距离、视野、球速和方向是否可预期、是否有时间"
            "协调身体，以及地滚球或空中球的处理难度。动作结果失误并不会自动否定其"
            "主动性；本能伸腿、跳起后只有有限接触则更接近折射。主动扑救仍是例外。"
        ),
        search_text=(
            "主动触球 主动处理球 故意触球 deliberate play 控制球 传球 控球 解围 "
            "来球距离 清晰视野 球速 方向 时间协调身体 本能伸腿 折射 deflection "
            "失误 unsuccessful save 扑救"
        ),
        keywords=("主动触球", "主动处理球", "deliberate play", "控制球"),
        source_url="https://www.theifab.com/laws/latest/offside/#offside-offence",
    ),
    KnowledgeDocument(
        document_id="ifab-2026-27-law11-deflection-save",
        domain="rule",
        title="IFAB Law 11: Deflection and deliberate save",
        section="11.2 Gaining an advantage",
        summary=(
            "球从门柱、横梁、比赛官员或对手身上反弹、折射，或者来自对手的主动扑救，"
            "通常不会为原先处于越位位置的进攻球员重置越位阶段。扑救指阻止或试图阻止"
            "正飞向球门或非常接近球门的球。"
        ),
        search_text=(
            "越位 折射 反弹 主动扑救 重置越位阶段 deliberate save rebound "
            "deflection 门柱 横梁"
        ),
        keywords=("折射", "反弹", "主动扑救"),
        source_url="https://www.theifab.com/laws/latest/offside/#offside-offence",
    ),
    KnowledgeDocument(
        document_id="ifab-2026-27-law11-no-offence",
        domain="rule",
        title="IFAB Law 11: No offence from specified restarts",
        section="11.3 No offence",
        summary=(
            "球员直接接到球门球、界外球或角球时，不构成越位犯规。该例外不包括任意球；"
            "任意球仍按通常的越位条件判断。"
        ),
        search_text=(
            "不越位 例外 球门球 界外球 角球 直接接球 任意球 goal kick throw-in "
            "corner kick no offence"
        ),
        keywords=("球门球", "界外球", "角球", "越位例外"),
        source_url="https://www.theifab.com/laws/latest/offside/#no-offence",
    ),
    KnowledgeDocument(
        document_id="ifab-2026-27-law12-handball",
        domain="rule",
        title="IFAB Law 12: Handling the ball",
        section="12.1 Direct free kick: handling the ball",
        summary=(
            "手球判罚需要结合动作是否故意、手臂是否让身体不自然地扩大，以及进攻球员"
            "是否在手臂触球后立即进球等条件判断。手臂位置本身不是唯一标准，裁判还要"
            "考虑该位置是否由当时具体身体动作造成或能够合理解释。"
        ),
        search_text=(
            "手球 故意手球 手臂 身体不自然扩大 立即进球 handball deliberate "
            "unnaturally bigger body law 12"
        ),
        keywords=("手球", "故意", "身体不自然扩大"),
        source_url="https://www.theifab.com/laws/latest/fouls-and-misconduct/#direct-free-kick",
    ),
)


TACTICAL_LEARNING_DOCUMENTS: tuple[KnowledgeDocument, ...] = (
    KnowledgeDocument(
        document_id="footops-tactics-half-space",
        domain="tactics",
        title="战术概念：半空间接应",
        section="进攻结构 / 半空间",
        summary=(
            "半空间是边路与中路之间的纵向通道。球员在这里接应，通常可以同时获得"
            "向外连接边路、向内连接中路和攻击肋部的传球角度；它不是固定站位，是否有"
            "效还要结合队友宽度、对手防线和接球后的下一动作判断。"
        ),
        search_text=(
            "半空间 肋部 half space 进攻结构 边路 中路 接应 宽度 传球角度"
            " 内外连接 positional play"
        ),
        keywords=("半空间", "肋部", "接应", "进攻结构"),
        source_url="https://www.fifatrainingcentre.com/en/",
        source_authority="FootOps curated tactical learning corpus",
        source_version="FootOps Tactical Concepts 2026.v1",
        effective_from=date(2026, 8, 1),
    ),
    KnowledgeDocument(
        document_id="footops-tactics-third-man",
        domain="tactics",
        title="战术概念：第三人配合",
        section="进攻配合 / 第三人",
        summary=(
            "第三人配合是指第一名球员把球传给第二名球员，同时利用第二名球员的回做或"
            "牵制，让第三名球员进入下一条传球线路。它的核心不是固定三角站位，而是通过"
            "接应、墙式传球和无球跑动绕过第一道防守压力。"
        ),
        search_text=(
            "第三人 三人出球 third man third player combination 墙式传球 回做"
            " 无球跑动 绕过压迫 出球"
        ),
        keywords=("第三人", "三人出球", "墙式传球", "无球跑动"),
        source_url="https://www.fifatrainingcentre.com/en/",
        source_authority="FootOps curated tactical learning corpus",
        source_version="FootOps Tactical Concepts 2026.v1",
        effective_from=date(2026, 8, 1),
    ),
    KnowledgeDocument(
        document_id="footops-tactics-pressing-triggers",
        domain="tactics",
        title="战术概念：高位压迫触发点",
        section="无球阶段 / 压迫触发",
        summary=(
            "压迫触发点是球队决定从控制空间转为主动逼抢的可识别信号，例如回传门将、"
            "接球者背身、停球质量差或边线限制了出球方向。触发点必须与队友的封堵角度、"
            "身后保护和压迫距离配套，否则单人上抢不等于形成高位压迫。"
        ),
        search_text=(
            "高位压迫 压迫触发 trigger 回传 背身 停球失误 边线 封堵角度 身后保护"
            " press trigger pressing trap"
        ),
        keywords=("高位压迫", "压迫触发", "回传", "背身", "身后保护"),
        source_url="https://www.fifatrainingcentre.com/en/",
        source_authority="FootOps curated tactical learning corpus",
        source_version="FootOps Tactical Concepts 2026.v1",
        effective_from=date(2026, 8, 1),
    ),
    KnowledgeDocument(
        document_id="footops-tactics-rest-defence",
        domain="tactics",
        title="战术概念：Rest defence 进攻时的身后保护",
        section="攻守转换 / Rest defence",
        summary=(
            "Rest defence 指球队进攻时仍保留的身后保护结构，用来应对丢球后的"
            "第一波反击。"
            "分析时应观察留守人数、横向距离、对手前锋位置和中路保护，而不能仅凭控球率"
            "推断球队是否具备稳定的攻守转换保护。"
        ),
        search_text=(
            "rest defence 身后保护 攻守转换 丢球 反击 留守人数 横向距离 中路保护"
            " counterpress transition"
        ),
        keywords=("rest defence", "身后保护", "攻守转换", "反击"),
        source_url="https://www.fifatrainingcentre.com/en/",
        source_authority="FootOps curated tactical learning corpus",
        source_version="FootOps Tactical Concepts 2026.v1",
        effective_from=date(2026, 8, 1),
    ),
)


METRIC_DEFINITION_DOCUMENTS: tuple[KnowledgeDocument, ...] = (
    KnowledgeDocument(
        document_id="footops-metric-touch-proxy-v1",
        domain="metric_definition",
        title="FootOps v1：触球代理指标",
        section="输入与限制 / touch_event_count",
        summary=(
            "FootOps v1 的触球数是带坐标的 Ball Receipt、Carry、Pass、Shot 等球员事件的"
            "可复算代理，不等同于数据商的官方 touches。它适合比较同一数据源内的"
            "样本趋势，"
            "不能直接代表完整控球次数或无球活动。"
        ),
        search_text=(
            "触球 触球代理 touch_event_count touches Ball Receipt Carry Pass Shot 坐标"
            " 数据口径 官方触球 无球活动"
        ),
        keywords=("触球代理", "touch_event_count", "触球口径", "官方 touches"),
        source_url="https://github.com/bu-0119/FootOps/blob/main/docs/FOOTOPS_METRIC_DEFINITIONS.md",
        source_authority="FootOps metric definitions",
        source_version="footops-player-role-v1",
        effective_from=date(2026, 8, 7),
    ),
    KnowledgeDocument(
        document_id="footops-metric-shot-involvement-v1",
        domain="metric_definition",
        title="FootOps v1：射门参与指标",
        section="进攻参与 / shot_involvement_count",
        summary=(
            "射门参与等于球员本人 Shot 事件数与关键传球数之和。它描述球员直接射门或制造"
            "射门机会的事件参与，不等同于 xG、射正、进球、助攻或完整进攻贡献。"
        ),
        search_text=(
            "射门参与 shot involvement shot_involvement_count 射门次数 关键传球 xG 射正"
            " 进球 助攻 进攻贡献"
        ),
        keywords=("射门参与", "shot involvement", "shot_involvement_count", "xG"),
        source_url="https://github.com/bu-0119/FootOps/blob/main/docs/FOOTOPS_METRIC_DEFINITIONS.md",
        source_authority="FootOps metric definitions",
        source_version="footops-player-role-v1",
        effective_from=date(2026, 8, 7),
    ),
    KnowledgeDocument(
        document_id="footops-metric-forward-pass-v1",
        domain="metric_definition",
        title="FootOps v1：向前传球与推进带球",
        section="推进指标 / forward_pass_count",
        summary=(
            "向前传球按 Pass 起点和终点的纵向坐标判断 end_x 大于 start_x；"
            "推进带球按 Carry 纵向前进至少 10 米判断。两者是事件次数，尚未按出场分钟、"
            "球队控球时间或比赛节奏"
            "归一化。"
        ),
        search_text=(
            "向前传球 forward pass completed_forward_pass_count 推进带球"
            " progressive carry"
            " end_x start_x 十米 归一化 出场分钟 控球时间"
        ),
        keywords=("向前传球", "推进带球", "progressive carry", "十米"),
        source_url="https://github.com/bu-0119/FootOps/blob/main/docs/FOOTOPS_METRIC_DEFINITIONS.md",
        source_authority="FootOps metric definitions",
        source_version="footops-player-role-v1",
        effective_from=date(2026, 8, 7),
    ),
)


FOOTOPS_KNOWLEDGE_DOCUMENTS: tuple[KnowledgeDocument, ...] = (
    *IFAB_2026_27_DOCUMENTS,
    *TACTICAL_LEARNING_DOCUMENTS,
    *METRIC_DEFINITION_DOCUMENTS,
)
