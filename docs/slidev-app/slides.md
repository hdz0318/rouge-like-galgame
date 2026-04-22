---
theme: default
background: https://cover.sli.dev
title: Phantom Seed
info: AIGC课程小组答辩
class: text-left
drawings:
  persist: false
transition: slide-left
mdc: true
---

# Phantom Seed
## 基于多 Agent 协同的互动叙事游戏生成系统

课程：AIGC 课程  
小组成员：`请替换`  
汇报人：`请替换`  
日期：`请替换`

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
layout: two-cols
---

# 多 Agent 协同设计

场景生成可抽象为四个角色：

- `Planner`：剧情目标、节拍、连续性约束
- `Writer`：生成完整场景
- `Critic`：质量检查
- `Reviewer`：输出最终结果

核心流程：

- 先规划
- 再生成
- 再检查
- 再交付

::right::

<div class="h-full flex items-center">
  <img src="/figures/agent-workflow.png" alt="multi-agent workflow" class="w-full rounded-lg border border-gray-200 shadow-sm" />
</div>

---
layout: two-cols
---

# 借鉴的 LangChain 类机制

项目没有直接依赖 `LangChain`，但设计上借鉴了这类框架的常见机制：

- 结构化输出
- 状态化工作流
- 回调与进度流
- Trace 记录
- 质量门控

这些机制帮助我们把多阶段生成组织成一个稳定流程。

::right::

<div class="h-full flex items-center">
  <img src="/figures/langchain-mechanisms.png" alt="langchain inspired mechanisms" class="w-full rounded-lg border border-gray-200 shadow-sm" />
</div>

---
layout: two-cols
---

# 共享状态与记忆

多阶段生成要稳定，关键是共享上下文。

系统维护：

- 角色档案
- 当前路线阶段和好感度
- 历史摘要和记忆片段
- 连续性备注和未回收伏笔

这些状态会在每一轮继续传给后续生成模块。

::right::

<div class="h-full flex items-center">
  <img src="/figures/shared-memory.png" alt="shared memory blackboard" class="w-full rounded-lg border border-gray-200 shadow-sm" />
</div>

---
layout: two-cols
---

# 结构化协议

我们不用自由文本直接驱动程序，而是定义结构化 `SceneData`：

- `script`
- `stage_commands`
- `choices`
- `background`
- `game_state_update`
- `continuity_notes`
- `open_threads`
- `next_hook`

作用：

- 稳定解析
- 统一渲染
- 支撑后续场景继续生成

::right::

<div class="h-full flex items-center">
  <img src="/figures/scene-protocol.png" alt="structured scene protocol" class="w-full rounded-lg border border-gray-200 shadow-sm" />
</div>

---
layout: two-cols
---

# 多模态协同

系统不只有文本，还要同时处理图像和交互：

- 文本模块决定场景目标和视觉描述
- 图像模块生成立绘、背景和 CG
- UI 根据结构化结果渲染
- 玩家选择再反馈回状态机

这形成了一个持续循环的系统。

::right::

<div class="h-full flex items-center">
  <img src="/figures/multimodal-loop.png" alt="multimodal generation loop" class="w-full rounded-lg border border-gray-200 shadow-sm" />
</div>

---
layout: two-cols
---

# 渐进式披露

系统信息量很大，所以展示层采用渐进式披露：

- 默认展示剧情、角色和选项
- 生成过程中展示必要进度
- trace、记忆和诊断信息按需展开

这样既保证普通玩家界面简洁，也方便开发和演示时查看系统细节。

::right::

<div class="h-full flex items-center">
  <img src="/figures/progressive-disclosure.png" alt="progressive disclosure UI" class="w-full rounded-lg border border-gray-200 shadow-sm" />
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

# Demo：单角色场景

这一页展示：

- 生成内容已经进入真实 UI
- 背景、立绘、对话和状态联动
- 当前选择会影响下一幕生成

![单角色场景](/screenshots/1.png)

---

# Demo：多角色舞台调度

这一页展示：

- 模型输出不仅有文本，还有舞台调度信息
- 程序根据 `stage_commands` 控制站位和出入场
- 同一套协议同时服务叙事和渲染

![多角色舞台](/screenshots/image.png)

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
