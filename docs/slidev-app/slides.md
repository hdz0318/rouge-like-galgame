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

课程：AIGC 课程  
小组成员：`请替换`  
汇报人：`请替换`  
日期：`请替换`

</div>

---

# 项目目标

<div class="page-kicker">Project Goals</div>

<div class="grid grid-cols-3 gap-4 mt-5 text-sm leading-relaxed">

<div class="metric-card p-4">

**目标一：内容进入流程**

本项目希望将 AIGC 生成内容从“静态展示结果”推进到“可被游戏系统实际消费”的层面，使模型输出能够参与剧情推进、场景切换与交互反馈。

</div>

<div class="metric-card p-4">

**目标二：形成交互闭环**

系统需要同时协调文本生成、图像生成与玩家选择，使三者之间形成稳定联动，而不是彼此割裂的独立模块。

</div>

<div class="metric-card p-4">

**目标三：保证系统可用**

在模型输出存在波动、失败或不稳定的情况下，仍通过工程机制维持原型系统的可运行性与可演示性。

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

在实际流程中，主文本模型主要承担规划、评审与最终整合任务；草稿模型负责中间候选内容生成，以平衡生成质量、速度与调用成本。

</div>

<div class="section-card p-5">

**图像生成模型**

- 常规图像模型：`google/gemini-3.1-flash-image-preview`
- CG / 宣传图模型：`google/gemini-3-pro-image-preview`
- 按不同任务类型进行资源分配

其中，常规图像生成主要服务于背景与流程内画面，高质量图像模型则用于 CG 或展示型画面，以提升汇报与演示效果。

</div>

<div class="accent-note p-4 col-span-2 text-sm leading-relaxed">

**设计说明**

在同一轮生成任务中，规划、草稿、审核与出图所要求的能力并不相同。因此，本项目并未采用单模型包揽全部任务的方式，而是按子任务分配模型能力，从而提高整体稳定性与效率。

</div>

</div>

---

# 为什么采用多 Agent

<div class="page-kicker">Motivation</div>

如果仅依赖单模型一次性完成场景生成，通常会出现以下问题：

- 规划与写作耦合，导致内容容易偏离当前剧情目标
- 难以同时兼顾角色一致性、分支设计与连续性约束
- 输出质量波动时，缺少显式检查与纠错机制

基于上述问题，我们将内容生成流程拆分为多个阶段，由不同 Agent 分别承担规划、生成、检查与收敛任务。这样做的核心目的，是将“内容生产”与“质量控制”分离，从而提高复杂叙事任务的可控性。

---

# 多 Agent 协同设计

<div class="page-kicker">Architecture</div>

<div class="grid grid-cols-[0.96fr_1.04fr] gap-6 items-center text-sm leading-relaxed mt-3">

<div>

我们将场景生成过程抽象为四类 Agent：

- `Planner`：负责剧情目标、节拍安排与连续性约束
- `Writer`：负责生成场景草稿、对话与候选选项
- `Critic`：负责质量检查、逻辑核对与问题识别
- `Reviewer`：负责整合修改意见并输出最终结果

**核心流程**：规划 → 生成 → 检查 → 交付

这一流程的意义在于，使系统能够在每一轮生成中形成“先规划、后写作、再校验”的稳定链路，而不是依赖单次调用直接获得最终答案。

</div>

<div>
  <img src="/figures/agent-workflow.svg" alt="multi-agent workflow" class="w-full max-h-[18rem] object-contain rounded-2xl border border-gray-200 shadow-sm bg-white/70" />
</div>

</div>

---

# 稳定性机制

<div class="page-kicker">Stability</div>

<div class="grid grid-cols-[0.96fr_1.04fr] gap-6 items-center text-sm leading-relaxed mt-3">

<div>

项目虽然没有直接依赖 `LangChain`，但在设计上参考了同类框架的若干核心思想：

- 结构化输出：降低解析不确定性
- 状态化工作流：保证流程具有阶段性与顺序性
- 进度回调：便于前端展示生成进度
- 运行 Trace：便于开发、调试与演示说明
- 质量门控：在输出进入系统前进行校验

这些机制的重点不在于复刻某一框架，而在于提升多阶段生成流程的稳定性、可观测性与可控性，使系统更适合工程化实现与课堂答辩展示。

</div>

<div>
  <img src="/figures/langchain-mechanisms.svg" alt="workflow mechanisms" class="w-full max-h-[18rem] object-contain rounded-2xl border border-gray-200 shadow-sm bg-white/70" />
</div>

</div>

---

# 共享状态与记忆

<div class="page-kicker">Shared Context</div>

<div class="grid grid-cols-[0.96fr_1.04fr] gap-6 items-center text-sm leading-relaxed mt-3">

<div>

多阶段生成要实现稳定运行，核心在于共享上下文状态，而不是让每一轮生成都从零开始。

系统在运行中持续维护以下信息：

- 角色档案与人物设定
- 当前路线阶段与好感度状态
- 历史摘要与关键记忆片段
- 连续性备注与尚未回收的伏笔

这些信息会在各阶段之间持续传递，从而使后续生成能够继承前文语境，维持叙事连贯性与状态一致性。

</div>

<div>
  <img src="/figures/shared-memory.svg" alt="shared memory blackboard" class="w-full max-h-[18rem] object-contain rounded-2xl border border-gray-200 shadow-sm bg-white/70" />
</div>

</div>

---

# 结构化协议

<div class="page-kicker">Structured Protocol</div>

<div class="grid grid-cols-[0.92fr_1.08fr] gap-6 items-center text-sm leading-relaxed mt-3">

<div>

为了避免使用自由文本直接驱动程序，我们定义了结构化协议 `SceneData`，用于统一描述场景生成结果。

核心字段包括：

- `script`
- `stage_commands`
- `choices`
- `background`
- `game_state_update`
- `continuity_notes` 等

该协议一方面保证程序能够稳定解析模型输出，另一方面为 UI 渲染、状态更新与后续场景续写提供统一的数据接口，是连接生成模块与游戏逻辑的重要中间层。

</div>

<div>
  <img src="/figures/scene-protocol.svg" alt="structured scene protocol" class="w-full max-h-[18rem] object-contain rounded-2xl border border-gray-200 shadow-sm bg-white/70" />
</div>

</div>

---

# 多模态协同

<div class="page-kicker">Multimodal Loop</div>

<div class="grid grid-cols-[0.96fr_1.04fr] gap-6 items-center text-sm leading-relaxed mt-3">

<div>

本系统并非只生成文本，而是同时协调文本、图像与交互三类模块：

- 文本模块负责生成剧情目标、对话与视觉描述
- 图像模块负责生成立绘、背景与 CG 画面
- UI 层依据结构化结果完成呈现与交互
- 玩家选择再进一步反馈至状态机

因此，系统形成的是一个持续迭代的多模态闭环，而非一次性生成。玩家的选择会影响状态机，而状态机又会进一步影响后续文本与图像内容的生成方向。

</div>

<div>
  <img src="/figures/multimodal-loop.svg" alt="multimodal generation loop" class="w-full max-h-[18rem] object-contain rounded-2xl border border-gray-200 shadow-sm bg-white/70" />
</div>

</div>

---

# 渐进式披露

<div class="page-kicker">Presentation Layer</div>

<div class="grid grid-cols-[0.96fr_1.04fr] gap-6 items-center text-sm leading-relaxed mt-3">

<div>

由于系统内部包含较多生成状态、诊断信息与中间过程，我们在展示层采用了渐进式披露策略：

- 默认界面仅展示剧情、角色与选项等核心信息
- 在生成过程中展示必要的进度反馈
- 将 Trace、记忆与诊断信息设计为按需展开

该设计既保证了玩家界面的简洁性，也便于在开发、调试和答辩演示过程中逐步解释系统内部流程，避免一次性暴露过多技术细节而影响展示效果。

</div>

<div>
  <img src="/figures/progressive-disclosure.svg" alt="progressive disclosure UI" class="w-full max-h-[18rem] object-contain rounded-2xl border border-gray-200 shadow-sm bg-white/70" />
</div>

</div>

---

# 工程实现

<div class="page-kicker">Engineering</div>

为了让整套流程具备可运行性，我们补充了以下工程机制：

- 并行生成多位角色人设与立绘
- 异步预取下一场景
- 背景缓存与去重
- `fallback scene` 兜底
- 存档、读档与 backlog 支持

这些机制的意义在于，将模型调用从单次实验扩展为连续可运行的应用流程。因此，本项目并非停留在 Prompt 设计层面，而是实现了一个可实际运行的互动叙事原型系统。

---

# Demo：运行截图

<div class="page-kicker">Demo</div>

<div class="grid grid-cols-2 gap-4 mt-3">

<div class="section-card p-4">

**单角色场景**

<img src="/screenshots/1.png" alt="单角色场景" class="w-full max-h-[15rem] object-contain rounded-lg shadow mt-3" />

<div class="text-xs leading-snug mt-3">

- 展示 AI 内容进入真实游戏界面后的效果
- 背景、立绘、对话与状态能够联动
- 玩家选择会影响下一幕场景的生成

该截图说明，生成结果并不是独立文本，而是能够被界面系统直接消费并参与游戏运行。

</div>

</div>

<div class="section-card p-4">

**多角色舞台调度**

<img src="/screenshots/image.png" alt="多角色舞台" class="w-full max-h-[15rem] object-contain rounded-lg shadow mt-3" />

<div class="text-xs leading-snug mt-3">

- 输出结果不仅包含文本，也包含舞台调度信息
- 程序依据 `stage_commands` 控制角色站位与出入场
- 同一结构化协议同时服务叙事生成与界面渲染

这说明结构化协议不仅服务于文本表达，也直接参与了视觉呈现与交互控制。

</div>

</div>

</div>

---

# 项目意义

<div class="page-kicker">Significance</div>

本项目的意义主要体现在以下三个层面：

- **应用层面**：AIGC 不仅可以用于静态内容生成，也能够进入交互式系统并参与真实应用流程
- **方法层面**：多 Agent 协同更适合处理持续、受约束、带状态的复杂生成任务
- **工程层面**：结构化协议、状态管理与兜底机制对于系统能否稳定运行同样关键

换言之，本项目希望说明，互动叙事场景中的 AIGC 研究，不应只关注“模型生成了什么”，还需要关注“生成结果如何被系统稳定使用”。

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

总体而言，当前系统已经验证了方案的可行性，但在长期叙事稳定性、风格统一性与自动评测方面仍有进一步完善空间。

---

# 总结

<div class="page-kicker">Conclusion</div>

本项目验证了一个核心判断：

> 对互动叙事任务而言，多 Agent 协同比单次生成更适合处理持续、多约束、带状态的内容生成问题。

对于互动叙事系统来说，关键并不只是模型生成得是否足够“华丽”，而在于：

- 输出能否被程序稳定消费
- 系统能否在多轮生成下持续运行
- 玩家选择能否真正影响后续内容

因此，我们认为，互动叙事系统的重点不仅是生成能力本身，更在于如何把生成结果组织为一个可执行、可维护、可扩展的完整流程。

---
layout: center
class: text-center
---

# 谢谢老师
## 欢迎提问
