---
theme: default
title: Phantom Seed
info: AIGC课程小组答辩
class: text-left
drawings:
  persist: false
transition: slide-left
mdc: true
layout: cover
background: '#f5f7fa'
---

<div class="absolute inset-0 -z-10 bg-gradient-to-br from-slate-50 via-sky-50 to-indigo-50"></div>

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

我们要解决三个问题：

- 让 AI 生成内容进入真实游戏流程
- 让文本、图像、玩家选择形成闭环
- 在模型不稳定时仍然保证系统可运行

---

# 为什么采用多 Agent

单模型一次性生成的问题：

- 规划和写作混在一起，容易跑偏
- 连续性、角色一致性和分支设计难兼顾
- 输出质量不好时缺少纠错环节

所以我们把任务拆成多个阶段，分别负责规划、生成、检查和收敛。

---

# 多 Agent 协同设计

<div class="grid grid-cols-[0.9fr_1.3fr] gap-6 items-center text-sm leading-snug mt-2">

<div>

场景生成可抽象为四个角色：

- `Planner`：剧情目标、节拍、连续性
- `Writer`：生成完整场景
- `Critic`：质量检查
- `Reviewer`：输出最终结果

**核心流程**：先规划 → 再生成 → 再检查 → 再交付

</div>

<div>
  <img src="/figures/agent-workflow.png" alt="multi-agent workflow" class="w-full max-h-[26rem] object-contain rounded-lg border border-gray-200 shadow-sm" />
</div>

</div>

---

# 借鉴的 LangChain 类机制

<div class="grid grid-cols-[0.9fr_1.3fr] gap-6 items-center text-sm leading-snug mt-2">

<div>

项目没有直接依赖 `LangChain`，但设计上借鉴了这类框架的常见机制：

- 结构化输出
- 状态化工作流
- 回调与进度流
- Trace 记录
- 质量门控

这些机制帮助我们把多阶段生成组织成一个稳定流程。

</div>

<div>
  <img src="/figures/langchain-mechanisms.png" alt="langchain inspired mechanisms" class="w-full max-h-[26rem] object-contain rounded-lg border border-gray-200 shadow-sm" />
</div>

</div>

---

# 共享状态与记忆

<div class="grid grid-cols-[0.9fr_1.3fr] gap-6 items-center text-sm leading-snug mt-2">

<div>

多阶段生成要稳定，关键是共享上下文。

系统维护：

- 角色档案
- 当前路线阶段和好感度
- 历史摘要和记忆片段
- 连续性备注和未回收伏笔

这些状态会在每一轮继续传给后续生成模块。

</div>

<div>
  <img src="/figures/shared-memory.png" alt="shared memory blackboard" class="w-full max-h-[26rem] object-contain rounded-lg border border-gray-200 shadow-sm" />
</div>

</div>

---

# 结构化协议

<div class="grid grid-cols-[0.9fr_1.3fr] gap-6 items-center text-sm leading-snug mt-2">

<div>

我们不用自由文本直接驱动程序，而是定义结构化 `SceneData`：

<div class="grid grid-cols-2 gap-x-4 gap-y-0 mt-2 mb-2">

- `script`
- `stage_commands`
- `choices`
- `background`
- `game_state_update`
- `continuity_notes`
- `open_threads`
- `next_hook`

</div>

**作用**：稳定解析 · 统一渲染 · 支撑后续场景继续生成

</div>

<div>
  <img src="/figures/scene-protocol.png" alt="structured scene protocol" class="w-full max-h-[26rem] object-contain rounded-lg border border-gray-200 shadow-sm" />
</div>

</div>

---

# 多模态协同

<div class="grid grid-cols-[0.9fr_1.3fr] gap-6 items-center text-sm leading-snug mt-2">

<div>

系统不只有文本，还要同时处理图像和交互：

- 文本模块决定场景目标和视觉描述
- 图像模块生成立绘、背景和 CG
- UI 根据结构化结果渲染
- 玩家选择再反馈回状态机

这形成了一个持续循环的系统。

</div>

<div>
  <img src="/figures/multimodal-loop.png" alt="multimodal generation loop" class="w-full max-h-[26rem] object-contain rounded-lg border border-gray-200 shadow-sm" />
</div>

</div>

---

# 渐进式披露

<div class="grid grid-cols-[0.9fr_1.3fr] gap-6 items-center text-sm leading-snug mt-2">

<div>

系统信息量很大，所以展示层采用渐进式披露：

- 默认展示剧情、角色和选项
- 生成过程中展示必要进度
- trace、记忆和诊断信息按需展开

这样既保证普通玩家界面简洁，也方便开发和演示时查看系统细节。

</div>

<div>
  <img src="/figures/progressive-disclosure.png" alt="progressive disclosure UI" class="w-full max-h-[26rem] object-contain rounded-lg border border-gray-200 shadow-sm" />
</div>

</div>

---

# 工程实现

为了让流程真正可运行，我们做了：

- 并行生成多位角色人设与立绘
- 异步预取下一场景
- 背景缓存与去重
- fallback scene 兜底
- 存档、读档、backlog

因此项目不是停留在 prompt 层面，而是一个可运行的原型系统。

---

# Demo：运行截图

<div class="grid grid-cols-2 gap-4 mt-2">

<div>

**单角色场景**

<img src="/screenshots/1.png" alt="单角色场景" class="w-full max-h-[18rem] object-contain rounded-lg shadow" />

<div class="text-xs leading-snug mt-2">

- 生成内容进入真实 UI
- 背景、立绘、对话与状态联动
- 当前选择会影响下一幕生成

</div>

</div>

<div>

**多角色舞台调度**

<img src="/screenshots/image.png" alt="多角色舞台" class="w-full max-h-[18rem] object-contain rounded-lg shadow" />

<div class="text-xs leading-snug mt-2">

- 输出不止文本，还包含舞台调度
- 程序按 `stage_commands` 控制站位与出入场
- 同一协议同时服务叙事与渲染

</div>

</div>

</div>

---

# 课程价值

这个项目最想说明三点：

- AIGC 可以进入交互式应用，而不只是静态生成
- 多 Agent 协同适合处理复杂生成任务
- 结构化协议、状态管理和工程兜底同样重要

---

# 当前不足与后续工作

当前不足：

- 图像风格一致性有限
- 长剧情连续性仍受上下文限制
- 多阶段生成有额外延迟和成本
- 自动评测体系还不完整

后续方向：

- 继续拆分记忆管理与连续性管理
- 完善短期上下文和长期记忆
- 建立自动评测方案
- 强化文本和图像之间的一致性约束

---

# 总结

本项目验证了一个核心判断：

> 对互动叙事任务来说，多 Agent 协同比单次生成更适合处理持续、多约束、带状态的内容生成问题。

关键不在于模型写得多华丽，而在于：

- 输出能否被程序稳定消费
- 系统能否持续运行
- 玩家选择能否真正影响后续内容

---
layout: center
class: text-center
---

# 谢谢老师
## 欢迎提问
