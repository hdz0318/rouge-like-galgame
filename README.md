# Phantom Seed

一个结合了 `Roguelike` 结构与 `Galgame / Visual Novel` 演出的实验型项目。  
游戏会基于随机种子动态生成女主设定、剧情场景、对话分支与背景/立绘，并通过 `pygame-ce` 渲染为可游玩的视觉小说体验。

## 项目特点

- 基于种子生成每轮不同的角色阵容与叙事氛围
- 使用 OpenRouter 生成结构化剧情数据，而不是只返回自由文本
- 自动生成女主立绘、场景背景与高潮 CG
- 包含好感度、线路锁定、章节推进与结局阶段等状态系统
- 支持存档、读档、快速存档、对话回看与设置面板
- 带有图片缓存与失败兜底逻辑，方便反复调试

## 当前玩法流程

1. 启动游戏后进入主菜单
2. 开始新游戏时随机生成一个种子
3. 根据种子生成多位女主的人设与立绘
4. AI 生成首个场景、对话脚本、选项和主视觉
5. 玩家通过选项影响总好感与各角色分线状态
6. 随着轮次推进，剧情会进入锁线、高潮与结局阶段

## 技术栈

- Python `>=3.11`
- `pygame-ce`
- `pydantic`
- `Pillow`
- `rembg[cpu]`
- `onnxruntime`
- OpenRouter Chat / Image API

## 快速开始

### 1. 安装依赖

推荐使用 `uv`：

```powershell
uv sync
```

如果你想带上开发依赖：

```powershell
uv sync --extra dev
```

### 2. 配置环境变量

在项目根目录创建 `.env`：

```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_TEXT_MODEL=x-ai/grok-4.1-fast
OPENROUTER_DRAFT_TEXT_MODEL=google/gemini-3-flash-preview
OPENROUTER_IMAGE_MODEL=google/gemini-3.1-flash-image-preview
OPENROUTER_PROMO_IMAGE_MODEL=google/gemini-3-pro-image-preview
```

最少需要配置：

```env
OPENROUTER_API_KEY=your_key_here
```

### 3. 运行游戏

```powershell
uv run phantom-seed
```

也可以直接运行模块入口：

```powershell
uv run python -m phantom_seed.main
```

## 常用操作

- `左键` / `Space`：推进对话，或在打字中直接显示整句
- `F5`：快速存档
- `F9`：快速读档
- `S`：打开存档菜单
- `L`：打开读档菜单
- `B`：打开 backlog / 对话回看
- `右键`：打开上下文菜单

## 环境与配置说明

程序启动时会自动读取项目根目录下的 `.env`。  
运行时配置位于 `src/phantom_seed/config.py`，当前包含：

- 窗口大小：`1280 x 720`
- 帧率：`60 FPS`
- 标题：`Phantom Seed`
- 文本速度、自动播放间隔、全屏设置
- OpenRouter 文本模型与图像模型配置
- 图像缓存目录：`.cache/images`
- 存档目录：`.saves`

用户设置会持久化到根目录的 `settings.json`。

## 目录结构

```text
src/phantom_seed/
├─ ai/           # LLM 客户端、图像生成、Prompt、Chain、协议定义
├─ core/         # 游戏状态、种子逻辑、协调器、Roguelike 规则、存档系统
├─ pipeline/     # 异步生成流程
├─ ui/           # pygame UI、场景渲染、菜单、HUD、对话框、转场
└─ main.py       # 程序入口
```

## 核心模块

- `src/phantom_seed/main.py`
  - 启动入口，检查 `OPENROUTER_API_KEY` 后创建游戏引擎
- `src/phantom_seed/ui/engine.py`
  - 主循环、事件处理、场景切换、对话推进、菜单和存档交互
- `src/phantom_seed/core/coordinator.py`
  - 协调角色生成、剧情生成、图像生成、状态推进与背景缓存
- `src/phantom_seed/ai/protocol.py`
  - 定义 AI 返回的结构化协议，如 `SceneData`、`CharacterProfile`、`Choice`
- `src/phantom_seed/ai/imagen_client.py`
  - 封装图像生成、缓存、抠图和立绘标准化逻辑

## AI 生成流程

一次新游戏的大致流程如下：

1. 根据种子计算哈希和初始氛围
2. 为多位女主生成独立人设
3. 为每位女主生成立绘
4. 结合当前状态生成下一个结构化场景
5. 生成主背景或高潮 CG
6. 预取后续可能发生的转场背景

剧情生成失败时会回退到内置 `fallback scene`，避免游戏流程完全中断。

## 存档系统

存档文件保存在 `.saves/` 下，每个槽位对应一个 JSON 文件。  
当前支持的槽位：

- `QUICK`
- `1`
- `2`
- `3`

存档内容不仅保存数值状态，还包括：

- 当前线路与轮次
- 角色数据与立绘路径
- 背景缓存
- 当前场景数据
- 当前对话索引
- 全量 backlog
- 缩略图截图

## 适合继续扩展的方向

- 增加更多路线规则和结局分支
- 引入本地素材与 AI 素材混合渲染
- 为角色加入表情、动作和多套服装
- 补充测试与开发工具链
- 增加更完整的加载进度与错误提示

## 开发说明

安装开发依赖后可使用：

```powershell
uv run pytest
uv run ruff check .
```

是否存在完整测试覆盖，仍取决于仓库后续补充情况。
