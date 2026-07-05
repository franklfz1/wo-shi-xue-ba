---
name: wo-shi-xue-ba
version: 2.0.0
description: 适合 K12 全年级的 AI 辅助自主学习基座系统，配合 AI Agent 使用
agent_created: true
---

# 我是学霸 — AI 辅助学习系统

> 一个适合 K12 全年级的 AI 辅助自主学习基座系统，配合 AI Agent 使用，基于艾宾浩斯遗忘曲线自动管理复习节奏。

## 系统概览

**我是学霸**是一套面向 K12（学前~高三）全年级的 AI 辅助学习基座系统。它本身不含 AI 能力，而是通过结构化的提示词、知识库、复习引擎和看板，为任意 AI Agent 提供完整的教学框架支撑。

**支持的 AI Agent**（不限于以下）：

| AI Agent | 支持程度 | 说明 |
|----------|---------|------|
| [WorkBuddy](https://www.codebuddy.cn/download) | ⭐ 完整支持 | 自动加载内置 Skill，初始化/出题/复习全自动化 |
| [TRAE](https://www.trae.ai/) | ⭐ 完整支持 | 同 WorkBuddy，支持 Skill 自动加载 |
| [Codex](https://openai.com/index/openai-codex/) | ✅ 基本支持 | 需手动指定 Skill 文件，核心功能可用 |
| Claude / ChatGPT 等 | ⚠️ 手动模式 | 手动复制提示词到对话，看板和复习引擎仍可用 |

核心特点：

- **6科AI老师**：语文、数学、英语、科学、地理、物理——每个都有完整的提示词、知识体系和出题规则
- **艾宾浩斯复习引擎**：自动推进 6 轮复习（1-2-4-7-15-30天），到期自动提醒
- **学习进度看板**：可视化六科进度、今日复习任务、掌握状态，Flask API 驱动
- **练习题生成引擎**：按学习进度自动出题，数学题库 100% 准确，支持 A4/A3 打印
- **视频制作流水线**：完整的教学短视频自动化工具链（配音→画面→字幕→合成）
- **教材知识库**：按年级/单元结构化的教学地图，与事实锚点库交叉校验

## 快速开始

### 0. 选择并安装 AI Agent（前提条件）

本系统是一个**基座框架**，需要配合 AI Agent 才能运行 AI 老师功能。推荐以下任一：

- **[WorkBuddy](https://www.codebuddy.cn/download)**：完整支持，自动加载内置 Skill
- **[TRAE](https://www.trae.ai/)**：完整支持，自动加载内置 Skill
- **[Codex](https://openai.com/index/openai-codex/)** 及其他支持 Skill/MCP 的 AI Agent：基本支持

安装后，将项目目录设为工作目录即可。本系统的内置 Skill 会被 Agent 自动识别。

### 1. 下载项目

```bash
git clone https://github.com/franklfz1/wo-shi-xue-ba.git
cd wo-shi-xue-ba
```

> 也可以在 GitHub 页面点击 "Code → Download ZIP" 下载压缩包，解压即可。

### 2. 安装依赖

**方式 A — 一键安装（推荐）**：

```bash
# Windows
install.bat

# macOS / Linux
chmod +x install.sh && ./install.sh
```

**方式 B — 手动安装**：

```bash
pip install -r requirements.txt

# 视频制作还需要 FFmpeg：
# Windows:  winget install ffmpeg
# macOS:    brew install ffmpeg
# Linux:    sudo apt install ffmpeg
```

### 3. 一键初始化（⭐ 新用户必读）

安装完依赖后，在 AI Agent 对话中说一个字：

> **初始化**

系统会自动完成以下全部流程：

1. ✅ 环境检查（Python / 依赖包 / FFmpeg）
2. ✅ 初始化产物目录（`artifacts_init.py --init`）
3. ✅ **选择年级** — 弹出选项卡，先选学段（学前/小学/初中/高中），再选具体年级
4. ✅ **选择科目** — 弹出选项卡（多选），勾选需要初始化的科目（数学/语文/英语/科学/地理/物理）
5. ✅ **逐科配置** — 对每个选中的科目弹出选项卡问答：

| 配置项 | 选项示例 |
|--------|---------|
| 定位类型 | 跳级衔接型 / 拓展提升型 / 书面内容导向型 / 兴趣驱动型 |
| 教材版本 | 人教版/统编版 + 年级上下册 |
| 当前水平 | 零基础 / 略有了解 / 基础扎实 / 超前学习 |
| 教学风格 | 活泼探险型 / 温暖陪伴型 / 严谨教练型 / 幽默启发型 |

6. ✅ 每科自动生成：定制版提示词 + `todo.md`（从知识库读取）+ 看板卡片 + 复习配置
7. ✅ 启动看板并打开浏览器

整个流程约 5-15 分钟（取决于选了几科），完成后直接说"切换成数学老师"开始学习。

> 💡 只想配置单科？说"初始化数学老师"即可（会额外询问年级）。不想用 Skill？见下方折叠区。

<details>
<summary>不想用 Skill？手动初始化也行</summary>

1. 运行 `python artifacts_init.py --init`
2. 编辑 `teachers/*.md`，将"当前学生水平"部分改为孩子实际情况
3. 参考 `knowledge-base/` 中的教材目录，将知识点填入 `records/<学科>/todo.md`
4. 确认 `review/next-review.json` 的 `subjects` 数组包含所有需要的学科
5. 运行 `python data_api.py` 启动看板

</details>

### 4. 开始学习

初始化完成后，看板已自动启动。在 AI Agent 对话中告诉 AI 老师你要学什么：

- "切换成数学老师" → 加载 `teachers/math.md` 提示词
- "切换成语文老师" → 加载 `teachers/chinese.md` 提示词
- 其他学科同理：英语、科学、地理、物理

### 5. 生成练习题

```bash
python exercise_engine.py                # 全科各一份
python exercise_engine.py -s math -c 10  # 数学10道
python exercise_engine.py -t "古诗词|生字书写"  # 指定知识点
```

## 目录结构

```
├── dashboard.html          # 学习进度看板（前端）
├── data_api.py             # Flask API 服务（后端，端口 5177）
├── exercise_engine.py      # 练习题生成引擎
├── artifacts_init.py       # 教学产物目录初始化工具
├── 启动看板.bat             # Windows 一键启动
│
├── teachers/               # 6科AI老师提示词
│   ├── math.md             # 数学（跳级衔接型）
│   ├── chinese.md          # 语文（拓展提升型·认写分离）
│   ├── english.md          # 英语（书面内容导向型）
│   ├── science.md          # 科学（兴趣拓展型）
│   ├── geography.md        # 地理（兴趣拓展型）
│   └── physics.md          # 物理（跳级衔接型·初中框架）
│
├── system/                 # 系统规则与模板
│   ├── teacher-prompt-rules.md    # 提示词编写规则（十一大模块）
│   ├── teacher-prompt-template.md # 空白模板，可新增任意学科
│   └── knowledge-anchors/         # 事实锚点库（对不对）
│       ├── math.md                # 数学法则、乘法口诀等
│       └── chinese-poetry.md      # 古诗原文、释义
│
├── knowledge-base/         # 教材知识库（教什么）
│   ├── _meta/textbook-index.md    # 教材版本索引
│   ├── math/                      # 人教版数学一年级上下册
│   └── chinese/                   # 统编版语文一年级上下册+识字表
│
├── question-bank/          # 习题库（练什么）
│   ├── README.md                  # 格式与五级难度标准
│   └── math/grade-1/generated/    # 数学一年级 JSONL 题库
│       ├── L1-basic.jsonl
│       ├── L2-standard.jsonl
│       ├── L3-application.jsonl
│       └── L4-L5-challenge.jsonl
│   └── math/_generator/gen_math_g1.py  # 程序生成器
│
├── records/                # 学习记录（每科4文件）
│   └── {subject}/
│       ├── mastered.md     # ✅已掌握 / 🔴易错 / 🟡待巩固
│       ├── todo.md         # ⬜待学知识点（按阶段排序）
│       ├── errors.md       # 错题记录
│       └── review-log.md   # 复习打卡表
│
├── review/                 # 艾宾浩斯复习中枢
│   ├── next-review.json    # 知识点复习队列（6轮）
│   ├── errors-review.json  # 错题复习队列（5轮）
│   └── schedule.md         # 复习计划总表
│
├── artifacts/              # 教学产物（运行时生成）
│   └── {学科}/{类型}/      # images/videos/audio/html
│
├── video-pipeline/         # 视频制作流水线
│   ├── config.json         # 参数配置（竖屏1080×1920）
│   └── scripts/            # 自动化脚本
│       ├── main_pipeline.py
│       ├── generate_voice.py
│       ├── render_frames.py
│       ├── compose_video.py
│       └── generate_sfx.py
│   └── assets/             # SVG动画/背景/音效
│   └── output/             # 输出产物
│   └── templates/          # 视频模板
│
├── 系统搭建指南.md          # 完整搭建与使用说明
├── README.md               # 项目说明（本文件）
├── LICENSE                 # MIT 开源协议
└── .gitignore              # Git忽略规则
```

## 内置 Skills（AI 老师技能系统）

系统内置三类子 skill，覆盖 AI 教学的核心场景。加载这些 skill 后，AI 老师系统具备完整的自动化能力。

### 一、系统管理类

#### skills/teacher-prompt-creator — 教师提示词生成
- **触发**：说"初始化"、"新增学科"、"创建XX老师"、"写老师提示词"
- **功能**：选项卡问答 → 严格遵循 rules 规范生成提示词 → 自动学科初始化（records + 看板 + 复习配置）
- **文件**：`skills/teacher-prompt-creator/SKILL.md` + `references/`

#### skills/exercise-generator — 练习题组卷引擎
- **触发**：说"出题"、"生成N道XX题"、"做一张XX卷子"、"打印练习题"
- **功能**：三级题源（题库JSONL→exercise_engine.py程序生成→AI标注⚠️）→ 出题前自检 → 批改三步 → 错题追加errors.md → 可打印A4/A3试卷HTML
- **文件**：`skills/exercise-generator/SKILL.md` + `scripts/exercise_engine.py` + `references/`

#### skills/qa-assistant — 问题解答助手
- **触发**：问"为什么XX"、"XX是什么"、"查一下XX"、"告诉我XX对不对"
- **功能**：防幻觉三步法（锚点库→知识库→推理），不确定时诚实拒绝绝不编造
- **文件**：`skills/qa-assistant/SKILL.md` + `references/`

### 二、EduLab 交互教学类

这类技能的**共同设计理念**是：**图不是 AI "画"的，是 kernel "算"出来的**。每个技能都有一个 Python 计算核心（kernel），精确算出坐标/数值后驱动前端渲染，保证"图、解、答"零误差。产出物都是**自包含的单页 HTML**，浏览器直接打开即可交互。

#### skills/edu-block-views — 方块三视图（小学数学·观察物体）
- **功能**：3D可拖拽方块 + 三视图同步 + 4种教学模式（演示/画图/逆向还原/选择题）
- **计算核心**：`lib/block_kernel.py`（纯整数运算，无依赖）
- **来源**：原创，借鉴 edulab 架构思路

#### skills/edu-plane-geometry — 平面几何（小学~初中）
- **功能**：SVG精确几何图 + 分步解析（长方形面积/全等证明/平行四边形/展开图/图形计数）
- **计算核心**：`lib/plane_kernel.py`（小学算术 + 初中sympy）
- **来源**：原创

#### skills/edu-solid-geometry — 立体几何（高中数学）
- **功能**：3D模型 + MathJax解析（线面角/二面角/异面直线/点到面距离）
- **计算核心**：`lib/geometry_kernel.py`（sympy）
- **来源**：[edulab](https://github.com/wy51ai/edulab) (Apache-2.0)

#### skills/edu-analytic-geometry — 解析几何（高中数学）
- **功能**：三栏交互页（题面+滑块控制台+KaTeX解析+2D Canvas动态画板），椭圆/双曲线/抛物线
- **计算核心**：`lib/analytic_kernel.py` + `lib/conics.py`（sympy）
- **来源**：[edulab](https://github.com/wy51ai/edulab) (Apache-2.0)

#### skills/edu-chem-reaction — 化学反应微观演示（高中化学）
- **功能**：3D分子动画 + KaTeX方程 + 原子守恒计数（燃烧/氧化还原/酯化等）
- **计算核心**：`lib/reaction_kernel.py`（sympy配平）
- **来源**：[edulab](https://github.com/wy51ai/edulab) (Apache-2.0)

## 新增学科

系统支持任意扩展新学科，只需三步：

1. 在 `teachers/` 下创建新学科提示词，遵循 `system/teacher-prompt-rules.md` 的十一大模块规范，使用 `system/teacher-prompt-template.md` 空白模板
2. 在 `records/` 下创建对应目录（`mastered.md` + `todo.md` + `errors.md` + `review-log.md`）
3. 在 `data_api.py` 的 `subjects` 和 `subject_labels` 中添加新学科

### 学科定位类型参考

| 类型 | 适合场景 | 示例 |
|------|----------|------|
| 跳级衔接型 | 孩子已掌握部分内容，需要跳到更高起点 | 数学（一年级上已掌握）、物理（初中框架） |
| 拓展提升型 | 孩子有基础但某维度薄弱，需要专项强化 | 语文（识字1000+但写字零基础） |
| 书面内容导向型 | AI 不适合教的部分由家长补充，AI 只教书面 | 英语（不教发音/听力/口语） |
| 兴趣拓展型 | 无固定大纲，主题探索为主 | 科学、地理 |

## 全局约束

### 语文
- **不教笔顺/田字格占位**：只展示规范楷体字形，用系统楷体字体渲染
- 汉字展示禁止 SVG 自绘字形

### 英语
- **不教发音/听力/口语**：AI 合成发音不准确，只教字母书写、单词认读、句子阅读
- **不教书写顺序/笔顺/占格**：只展示字母规范字形

### 物理
- 跳级衔接型起点为人教版初中物理八年级上册，从"长度和时间的测量"开始
- 约 65 个知识点，19 个教学阶段

## Flask 后台注意事项

- `data_api.py` 使用 Flask，**必须用 `nohup python data_api.py > /tmp/data_api.log 2>&1 &` 方式启动**（不能用 WorkBuddy 的 `run_in_background=true`，后者会永久卡住）
- 服务运行在 `localhost:5177`，浏览器直接访问即可

## 教学产物存放规范

教学过程中生成的所有文件归入 `artifacts/` 对应子目录，不再散落根目录：

- 路径：`artifacts/{学科}/{类型}/`
- 学科：math/chinese/english/science/geography/other
- 类型：images/videos/audio/html/other
- 命名：`{YYYY-MM-DD}_{描述}.{ext}`（日期前缀必须）
- 初始化：`python artifacts_init.py --init`

## 复习机制

系统基于艾宾浩斯遗忘曲线自动管理复习节奏：

- **知识点复习**：6轮，间隔 1-2-4-7-15-30 天
- **错题复习**：5轮，间隔 1-2-3-5-7 天
- 标记一个知识点为"已掌握"时，自动建立复习计划
- 每日可通过 AI Agent 的自动化功能触发复习提醒
- 看板页面可交互勾选完成复习，自动推进下一轮

## 数据全本地化

所有数据以 Markdown + JSON 文件存储在项目根目录下，零外部依赖，完全可移植。`data_api.py` 是数据读写唯一入口，前端通过 fetch() 调用。
