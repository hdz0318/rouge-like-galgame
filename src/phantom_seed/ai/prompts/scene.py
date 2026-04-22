"""Scene generation prompt helpers."""

from phantom_seed.ai.prompts.system import SYSTEM_MESSAGE

SCENE_PLAN_PROMPT_TEMPLATE = """\
你现在扮演剧情总规划 agent。请先为下一幕生成一个“剧情执行大纲”，重点保证延续性、情绪推进和选项分支价值。

## 当前角色档案
{character_profile}

## 女主阵容摘要
{cast_summary}

## 当前游戏状态
- 当前焦点女主: {active_heroine}
- 好感度: {affection}/100
- 当前场景编号: 第 {round_number} 幕
- 章节节拍: {chapter_beat}
- 路线阶段: {route_phase}
- 锁定线路: {route_locked_to}

## 路线蓝图
{route_blueprint}

## 当前目标结局
{ending_target}

## 故事历史摘要
{history_summary}

## 剧情记忆
{story_memory}

## 上一次玩家的选择
{last_choice}

## 随机小插曲
{random_event}

## 规划要求
- 请按照商业 galgame 常见结构规划：共通线负责多女主铺垫，个人线负责集中推进单个女主的秘密、冲突、告白与结局
- 如果仍处于共通线，可以让多名女主出场，但必须明确本幕的“主焦点女主”
- 如果已经锁线，本幕必须围绕锁定女主推进，其他女主只做轻量陪衬或不出场
- 大纲必须明确本幕的目标、开场情境、情绪推进、冲突转折和结尾钩子
- continuity_must_use 必须写出本幕需要延续的既有事实、伏笔、关系变化，避免失忆式展开
- location_sequence 给出本幕的地点/时段推进，至少 3 个节点，便于后续生成自然转场
- choice_design 说明每个选项想引导的剧情方向，而不是只写数值变化
- 如果上一幕有钩子或未解决问题，优先纳入本幕
- 所有会进入 `background`、`scene_transition`、`climax_cg_prompt` 的视觉描述，都要默认服务于日本动漫风格的 galgame 背景与事件 CG 生成

请严格按 ScenePlan 的 JSON 输出，不要附加解释。"""

SCENE_WRITE_PROMPT_TEMPLATE = """\
## 当前角色档案
{character_profile}

## 女主阵容摘要
{cast_summary}

## 当前游戏状态
- 当前焦点女主: {active_heroine}
- 好感度 (Affection): {affection}/100
- 当前场景编号: 第 {round_number} 幕
- 章节节拍: {chapter_beat}
- 路线阶段: {route_phase}
- 锁定线路: {route_locked_to}

## 路线蓝图
{route_blueprint}

## 当前目标结局
{ending_target}

## 故事历史摘要
{history_summary}

## 剧情记忆
{story_memory}

## 上一次玩家的选择
{last_choice}

## 随机小插曲（可以融入剧情，也可以忽略）
{random_event}

## 本幕剧情规划
{scene_plan}

## 本次剧情生成要求
- 必须输出 **25-45 条对话**（严格执行，少于20条视为失败）
- 必须包含至少 **2次场景/地点切换**（使用 scene_transition 字段）
- **以对话为核心**：减少神态/动作/心理描写，台词本身要体现情绪和性格
- inner_monologue 仅在心动高潮处使用，全段不超过 3-4 条，其余留空字符串
- 剧情要体现本幕的章节节拍（{chapter_beat}）
- 必须显式承接 scene_plan 中的 continuity_must_use，避免角色失忆、情绪跳变、关系回退
- 对话要像真实剧本一样自然衔接，避免重复句式、反复解释同一件事
- 参考全价 galgame 写法：共通线里允许多名女主交错登场，但本幕必须有一个明确主焦点；锁线后必须以锁定女主为核心推进个人剧情
- stage_commands 中允许出现多名女主，但只能使用女主阵容摘要中已有的名字，不要发明新的可视化角色
- choices 需要具备“选线感”，在共通线阶段可通过 `heroine:角色名` 和 `affection` 体现偏向；锁线后则以锁定女主的情感推进为主
- 若路线阶段是 `lock_window`，2-3 个 choices 至少要有 2 个明确偏向不同女主
- 若路线阶段是 `climax` 或 `ending`，必须朝 {ending_target} 这种结局质感推进
- 基调是温馨浪漫的成人恋爱故事，允许有小冲突和误会，但整体基调积极向上
- 【强制约束】所有角色均为 18 岁以上大学生或成年人，不得出现任何涉及未成年人的浪漫或亲密内容
- `background` / `scene_transition` / `climax_cg_prompt` 的英文内容必须明显偏向 Japanese anime galgame aesthetics，不要使用 photo, realistic, cinematic live-action, 3D render 之类的导向
- 在最后提供 **2-3 个选择分支**，选项要对剧情走向有实质影响
- 除正常 SceneData 字段外，还要认真填写：
  - scene_goal：本幕完成了什么推进
  - emotional_shift：本幕情绪如何变化
  - continuity_notes：后续必须记住的事实，写 2-4 条
  - open_threads：本幕留下的未解决问题或伏笔，写 1-3 条
  - next_hook：下一幕最该承接的钩子

请生成下一段剧情场景，严格按 JSON 格式输出。"""

SCENE_REVIEW_PROMPT_TEMPLATE = """\
你现在扮演剧情审校 agent。请检查下面的剧本草稿是否存在以下问题，并直接输出修正后的最终 SceneData JSON：
- 和历史摘要、剧情记忆、scene_plan 冲突
- 角色说话方式不稳定，情绪变化过快，关系推进不自然
- 场景切换生硬，台词重复，信息密度失衡
- continuity_notes / open_threads / next_hook 填写空泛，无法服务后续连载

## 当前角色档案
{character_profile}

## 女主阵容摘要
{cast_summary}

## 当前游戏状态
- 当前焦点女主: {active_heroine}
- 好感度: {affection}/100
- 当前场景编号: 第 {round_number} 幕
- 章节节拍: {chapter_beat}
- 路线阶段: {route_phase}
- 锁定线路: {route_locked_to}

## 路线蓝图
{route_blueprint}

## 当前目标结局
{ending_target}

## 故事历史摘要
{history_summary}

## 剧情记忆
{story_memory}

## 本幕剧情规划
{scene_plan}

## 场景草稿
{scene_draft}

## 审校要求
- 保留草稿中有效的情绪亮点，但必须优先修正连贯性问题
- 不要缩短成骨架，仍需保持完整的 25-45 条对话和至少 2 次转场
- choice 的文案和影响方向要明显区分
- 不要生成阵容外的新可视化女主；若已锁线，不要把剧情重心切回其他女主
- lock_window 阶段要保留明确分支感；ending 阶段必须让结局落点清晰
- 任何视觉字段都要修正到日本动漫 galgame 语境，避免写实或非二次元风格漂移
- 只输出最终可用的 SceneData JSON
"""


def build_scene_plan_messages(**payload: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": SCENE_PLAN_PROMPT_TEMPLATE.format(**payload)},
    ]


def build_scene_write_messages(**payload: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": SCENE_WRITE_PROMPT_TEMPLATE.format(**payload)},
    ]


def build_scene_review_messages(**payload: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": SCENE_REVIEW_PROMPT_TEMPLATE.format(**payload)},
    ]
