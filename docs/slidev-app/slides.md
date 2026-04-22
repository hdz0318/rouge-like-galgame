---
theme: unicorn
title: Phantom Seed
info: AIGC课程小组答辩
class: text-left
drawings:
  persist: false
transition: slide-left
mdc: true
layout: cover
---

# Phantom Seed
## 基于多 Agent 协同的互动叙事游戏生成系统

<div class="mt-10 text-sm leading-relaxed text-slate-600">

小组成员：022330225 黄耘青 / 202330218 何东泽 / 162340124 吴承骏
汇报人：022330225 黄耘青  
日期：4月23日

</div>

---

# 功能展示

<div class="page-kicker">What The System Can Do</div>

<div class="grid grid-cols-3 gap-4 mt-5 text-sm leading-relaxed">

<div class="metric-card p-4">

**生成可玩的剧情场景**

不是只生成一段文本，而是直接输出可进入游戏流程的场景内容，包括对白、选项、状态变化与下一步推进线索。

</div>

<div class="metric-card p-4">

**联动文本、图像与交互**

系统会同时生成剧情文本、背景/立绘描述与舞台调度信息，并将其交给前端界面直接渲染和响应。

</div>

<div class="metric-card p-4">

**支持持续多轮运行**

玩家每一次选择都会反馈到状态机与记忆模块，从而影响后续剧情和图像生成方向，而不是一次性静态出图。

</div>

</div>

<div class="accent-note p-4 mt-5 text-sm leading-relaxed">

**一句话概括**

我们做的不是“生成内容演示”，而是一个能够把 AIGC 内容真正接入互动叙事流程的可运行原型。

</div>

---

# Demo：运行效果

<div class="page-kicker">Live Screens</div>

<div class="grid grid-cols-2 gap-4 mt-3">

<div class="section-card p-4">

**单角色剧情场景**

<img src="/screenshots/1.png" alt="单角色场景" class="w-full max-h-[15rem] object-contain rounded-lg shadow mt-3" />

<div class="text-xs leading-snug mt-3">

- 背景、立绘、对白与选项同时进入游戏界面
- 玩家点击选项后，系统继续生成下一幕内容
- 说明 AI 输出已被程序稳定消费，而非停留在文本结果

</div>

</div>

<div class="section-card p-4">

**多角色舞台调度**

<img src="/screenshots/image.png" alt="多角色舞台" class="w-full max-h-[15rem] object-contain rounded-lg shadow mt-3" />

<div class="text-xs leading-snug mt-3">

- 输出不仅有对白，还包含角色站位、出入场等舞台指令
- 程序依据 `stage_commands` 控制视觉呈现
- 说明结构化结果能够同时驱动叙事与界面渲染

</div>

</div>

</div>

---

# 项目目标

<div class="page-kicker">Project Goals</div>

<div class="grid grid-cols-3 gap-4 mt-5 text-sm leading-relaxed">

<div class="metric-card p-4">

**让生成内容进入系统**

让模型输出不再只是展示结果，而是能够参与剧情推进、场景切换与交互反馈。

</div>

<div class="metric-card p-4">

**形成稳定交互闭环**

把文本生成、图像生成、界面渲染与玩家选择连接起来，形成完整的可运行链路。

</div>

<div class="metric-card p-4">

**保证原型可用可演示**

即使模型输出波动，也通过工程兜底、缓存和状态管理保证系统能够持续运行。

</div>

</div>

---

# 核心创新点

<div class="page-kicker">Highlights</div>

<div class="grid grid-cols-2 gap-4 mt-4 text-sm leading-relaxed">

<div class="section-card p-5">

**创新点一：多 Agent 分阶段生成**

将“规划、写作、检查、收敛”拆开，避免单模型一次性生成时出现跑题、失控和质量波动。

</div>

<div class="section-card p-5">

**创新点二：结构化协议驱动游戏**

定义 `SceneData` 作为中间层，使模型输出能被前端、状态机和场景续写模块稳定解析与消费。

</div>

<div class="section-card p-5">

**创新点三：共享状态与记忆机制**

引入分层记忆架构，将当前场景上下文与长期角色知识分开管理，保证多轮叙事的连续性与可扩展性。

</div>

<div class="section-card p-5">

**创新点四：多模态闭环落地**

把文本、图像、交互和状态更新放进同一运行链路中，让玩家选择真正影响后续生成。

</div>

</div>

---

# 系统总体方案

<div class="page-kicker">Architecture</div>

<div class="grid grid-cols-[0.96fr_1.04fr] gap-6 items-center text-sm leading-relaxed mt-3">

<div>

我们将场景生成流程抽象为四类 Agent：

- `Planner`：负责剧情目标、节拍安排与连续性约束
- `Writer`：负责生成场景草稿、对白与候选选项
- `Critic`：负责质量检查、逻辑核对与问题识别
- `Reviewer`：负责整合修改意见并输出最终结果

**核心流程**：规划 → 生成 → 检查 → 交付

这样做的关键价值，是把“内容生产”和“质量控制”显式分离，使复杂叙事任务更可控、更稳定。

</div>

<div>
  <img src="/figures/agent-workflow.svg" alt="multi-agent workflow" class="w-full max-h-[18rem] object-contain rounded-2xl border border-gray-200 shadow-sm bg-white/70" />
</div>

</div>

---

# Agent 记忆机制

<div class="page-kicker">Memory Architecture</div>

<div class="grid grid-cols-2 gap-4 mt-4 text-sm leading-relaxed">

<div class="section-card p-5">

**短期记忆 Short-term Memory**

- 保存最近若干幕剧情、当前场景目标与玩家最新选择
- 记录本轮对话中的情绪、冲突、未完成动作与临时约束
- 以滑动窗口方式维护，保证生成时始终聚焦“眼前正在发生什么”

</div>

<div class="section-card p-5">

**长期记忆 Long-term Memory**

- 持久保存角色设定、世界观规则、关键事件和已埋伏笔
- 将高价值历史内容压缩为可复用的记忆条目，而非简单拼接全文
- 用于支撑跨章节一致性，避免角色性格、关系和设定漂移

</div>

<div class="accent-note p-4 col-span-2 text-sm leading-relaxed">

**设计思路**

短期记忆保证当前场景连贯，长期记忆保证跨场景稳定；两者结合，才能让互动叙事既“接得上当前剧情”，又“记得住过去发生过什么”。

</div>

</div>

---

# 记忆如何参与生成

<div class="page-kicker">Memory Loop</div>

<div class="grid grid-cols-[0.96fr_1.04fr] gap-6 items-center text-sm leading-relaxed mt-3">

<div>

我们将记忆机制设计为一个“写入 - 检索 - 回注”的循环：

- 场景结束后，系统抽取关键事实、人物关系变化与伏笔信息
- 高价值信息写入长期记忆库，近期过程保留在短期上下文中
- 新一轮生成前，`Planner` 和 `Writer` 先检索与当前路线最相关的记忆
- 检索结果以结构化摘要形式回注到 Prompt，供 `Critic` 检查连续性

这样做的目标，是避免把所有历史内容都塞进上下文窗口，同时仍然保留“该记住的内容”。

</div>

<div>
  <img src="/figures/shared-memory.svg" alt="shared memory blackboard" class="w-full max-h-[18rem] object-contain rounded-2xl border border-gray-200 shadow-sm bg-white/70" />
</div>

</div>

---

# 稳定性机制

<div class="page-kicker">Stability</div>

<div class="grid grid-cols-[0.96fr_1.04fr] gap-6 items-center text-sm leading-relaxed mt-3">

<div>

为了让多阶段生成真正可运行，我们补充了若干稳定性机制：

- 结构化输出：降低解析不确定性
- 状态化工作流：保证流程具有阶段性与顺序性
- 进度回调：便于前端展示生成进度
- 运行 Trace：便于开发、调试与答辩说明
- 质量门控：在输出进入系统前进行校验

这些机制的重点不在于复刻某一框架，而在于提升流程的稳定性、可观测性与可控性。

</div>

<div>
  <img src="/figures/langchain-mechanisms.svg" alt="workflow mechanisms" class="w-full max-h-[18rem] object-contain rounded-2xl border border-gray-200 shadow-sm bg-white/70" />
</div>

</div>

---

# 结构化协议

<div class="page-kicker">Structured Protocol</div>

<div class="grid grid-cols-[0.92fr_1.08fr] gap-6 items-center text-sm leading-relaxed mt-3">

<div>

为了避免自由文本直接驱动程序，我们定义了结构化协议 `SceneData`。

核心字段包括：

- `script`
- `stage_commands`
- `choices`
- `background`
- `game_state_update`
- `continuity_notes`

它一方面保证程序能够稳定解析模型输出，另一方面为 UI 渲染、状态更新与场景续写提供统一接口。

</div>

<div>
  <img src="/figures/scene-protocol.svg" alt="structured scene protocol" class="w-full max-h-[18rem] object-contain rounded-2xl border border-gray-200 shadow-sm bg-white/70" />
</div>

</div>

---

# 记忆 + 协议的意义

<div class="page-kicker">State & Protocol</div>

<div class="grid grid-cols-2 gap-4 mt-4 text-sm leading-relaxed">

<div class="section-card p-5">

**分层记忆**

- 短期记忆负责当前剧情推进
- 长期记忆负责角色与世界设定保持稳定
- 检索机制负责在新场景开始前提取相关历史信息

这样可以在有限上下文窗口内保留真正有用的历史内容。

</div>

<div class="section-card p-5">

**结构化协议 `SceneData`**

- `script`
- `stage_commands`
- `choices`
- `background`
- `game_state_update`
- `continuity_notes`

它把记忆检索结果、场景生成结果和游戏状态更新统一到同一数据接口中，保证流程可解析、可追踪、可续写。

</div>

</div>

---

# 多模态闭环

<div class="page-kicker">Multimodal Loop</div>

<div class="grid grid-cols-[0.96fr_1.04fr] gap-6 items-center text-sm leading-relaxed mt-3">

<div>

本系统不是只生成文本，而是让多个模块协同工作：

- 文本模块生成剧情目标、对白与视觉描述
- 图像模块生成背景、立绘与 CG
- UI 层依据结构化结果完成呈现与交互
- 玩家选择反馈给状态机，影响下一轮生成

因此，系统形成的是一个持续迭代的多模态闭环，而不是一次性内容生成。

</div>

<div>
  <img src="/figures/multimodal-loop.svg" alt="multimodal generation loop" class="w-full max-h-[18rem] object-contain rounded-2xl border border-gray-200 shadow-sm bg-white/70" />
</div>

</div>

---

# 渐进式披露

<div class="page-kicker">Context Loading</div>

<div class="grid grid-cols-[0.96fr_1.04fr] gap-6 items-center text-sm leading-relaxed mt-3">

<div>

这里的“渐进式披露”并不是指界面展示，而是指 **对模型上下文按需装载**：

- 默认只注入当前场景目标、最近剧情和必要角色状态
- 当任务涉及连续性、伏笔或人物关系时，再检索相关长期记忆
- 诊断信息、历史细节和低相关内容不会一次性全部塞入 Prompt
- 不同 Agent 只拿自己当前阶段真正需要的那部分上下文

这样做的目的，是减少上下文噪声与 token 浪费，让模型把注意力集中在“当前这一步真正需要解决的问题”上。

</div>

<div>
  <img src="/figures/progressive-disclosure.svg" alt="progressive disclosure for context loading" class="w-full max-h-[18rem] object-contain rounded-2xl border border-gray-200 shadow-sm bg-white/70" />
</div>

</div>

---

# 工程亮点

<div class="page-kicker">Engineering</div>

<div class="grid grid-cols-2 gap-4 mt-4 text-sm leading-relaxed">

<div class="section-card p-5">

**稳定性与可观测性**

- 结构化输出降低解析不确定性
- 状态化工作流保证阶段顺序
- 进度回调与 Trace 便于展示和调试
- 质量门控避免异常结果直接进入系统

</div>

<div class="section-card p-5">

**可运行性的工程补充**

- 并行生成角色人设与立绘
- 异步预取下一场景
- 背景缓存与去重
- `fallback scene` 兜底
- 存档、读档与 backlog 支持

</div>

</div>

---

# 模型栈与任务分工

<div class="page-kicker">Model Stack</div>

<div class="grid grid-cols-2 gap-4 mt-4 text-sm leading-relaxed">

<div class="section-card p-5">

**文本生成模型**

- 主文本模型：`x-ai/grok-4.1-fast`
- 草稿生成模型：`google/gemini-3-flash-preview`
- 接入方式：通过 `OpenRouter` 统一调度

主文本模型负责规划、评审与整合；草稿模型负责候选内容生成，以平衡质量、速度与成本。

</div>

<div class="section-card p-5">

**图像生成模型**

- 常规图像模型：`google/gemini-3.1-flash-image-preview`
- CG / 宣传图模型：`google/gemini-3-pro-image-preview`
- 按任务类型分配不同模型资源

常规模型服务流程内背景与画面，高质量模型用于 CG 和展示型图像。

</div>

</div>

---

# 项目价值

<div class="page-kicker">Significance</div>

本项目说明了三件事：

- **AIGC 可以进入真实互动系统**：不是只生成静态内容，而是能参与可运行应用流程
- **多 Agent 更适合复杂叙事任务**：尤其适用于持续、多约束、带状态的生成场景
- **工程机制与模型能力同样重要**：结构化协议、状态管理和兜底设计决定系统是否可用

因此，我们关注的不只是“模型生成了什么”，更是“生成结果能否被系统稳定使用”。

---

# 当前不足与后续工作

<div class="page-kicker">Limitations & Future Work</div>

当前系统仍存在以下不足：

- 图像风格一致性仍然有限
- 长剧情连续性仍受上下文窗口限制
- 多阶段生成会带来额外延迟与成本
- 自动评测体系尚不完整

后续工作主要包括：

- 继续细化记忆管理与连续性管理模块
- 完善短期上下文与长期记忆机制
- 建立自动评测与质量分析方案
- 强化文本与图像之间的一致性约束

---

# 总结

<div class="page-kicker">Conclusion</div>

本项目验证了一个核心判断：

> 对互动叙事任务而言，多 Agent 协同比单次生成更适合处理持续、多约束、带状态的内容生成问题。

我们希望说明，互动叙事系统的重点不仅是生成能力本身，更在于如何把生成结果组织为一个可执行、可维护、可扩展的完整流程。

---
layout: center
class: text-center
---

# 谢谢老师
## 欢迎提问
