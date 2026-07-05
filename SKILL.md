---
name: wo-shi-xue-ba
version: 2.0.0
description: 基于 AI 和艾宾浩斯遗忘曲线的小学低年级辅助学习系统（开源版）
agent_created: true
triggers:
  - "初始化"
  - "我是学霸"
  - "学习系统"
  - "学习看板"
  - "打开看板"
  - "复习提醒"
  - "切换成XX老师"
---

# 我是学霸 — AI 辅助学习系统 Skill

## 系统概述

「我是学霸」是一个完整的 AI 辅助学习框架，面向小学低年级儿童（1-3年级），由家长操作。系统包含 6 科 AI 老师提示词、艾宾浩斯复习引擎、可视化看板、练习题生成引擎和视频制作流水线。

## 一键初始化（核心入口）

当用户说 **"初始化"** 时，执行完整的系统初始化流程（首次使用和重新配置都走这个入口）：

### Step 1: 环境检查
1. 检查 Python 版本（需 3.10+）：`python --version`
2. 检查 pip 依赖是否已安装：尝试 `import flask, edge_tts, PIL, numpy, scipy`
3. 检查 FFmpeg：`ffmpeg -version`
4. 如果有缺失：
   - pip 依赖缺失 → 运行 `pip install -r requirements.txt`
   - FFmpeg 缺失 → 提示安装方式（Windows: `winget install ffmpeg` / macOS: `brew install ffmpeg`）
   - 等用户完成安装后再继续

### Step 2: 初始化产物目录
```bash
python artifacts_init.py --init
```
如果 `artifacts_init.py` 不存在则跳过。

### Step 3: 学科初始化（核心步骤）

分三步完成，先确定年级和科目，再逐科配置：

#### 3a: 选择年级

弹出选项卡，让用户选择孩子的年级。分两步选择：

**第一步 — 学段**（AskUserQuestion 单选）：
```
选项: 学前 / 小学 / 初中 / 高中
```

**第二步 — 具体年级**（根据学段动态调整选项）：
- 学前 → 学前班
- 小学 → 一年级 / 二年级 / 三年级 / 四年级 / 五年级 / 六年级（分两次：低年级1-3 / 高年级4-6）
- 初中 → 初一 / 初二 / 初三
- 高中 → 高一 / 高二 / 高三

> student_grade = 用户最终选择的年级

#### 3b: 选择科目

弹出选项卡（**多选**），让用户勾选需要初始化的科目（AskUserQuestion, multiSelect: true）：
```
选项: 数学 / 语文 / 英语 / 科学 / 地理 / 物理
```

> selected_subjects = 用户勾选的科目列表

#### 3c: 逐科配置

加载 `skills/teacher-prompt-creator` skill，执行 **Complete Initialization Mode**：
- 年级（3a）和科目列表（3b）已确定，每科只需弹出选项卡配置 4 项：定位类型 / 教材版本 / 当前水平 / 教学风格
- 每科自动生成：`teachers/<学科>.md` 提示词 + `records/<学科>/todo.md`（从 knowledge-base 读取）+ 看板卡片 + 复习配置 + FAQ
- 详见 `skills/teacher-prompt-creator/SKILL.md` 的 Phase 1-4

> 用户也可以只说"初始化数学老师"单独配置一科（此时会额外询问年级）。

#### 3d: 清理未选学科

用户选了哪些科目就只保留哪些，**未选的学科模板全部删除**，保持系统干净。

**预定义6科 ID**：`math, chinese, english, science, geography, physics`

**未选学科 = 6科全集 - selected_subjects**

对每个未选的学科，删除以下文件/目录：

| 删除目标 | 路径 |
|---------|------|
| 教师提示词 | `teachers/<subject>.md` |
| FAQ 文件 | `teachers/<subject>-faq.md`（如存在） |
| 学习记录目录 | `records/<subject>/`（整个目录） |

同时更新以下配置文件：

1. **`review/next-review.json`**：从 `subjects` 数组中移除未选学科 ID
2. **`dashboard.html`**：从 JavaScript `SUBJECTS` 数组中移除未选学科的卡片对象
3. **`data_api.py`**：从 `subjects` 列表和 `subject_labels` 字典中移除未选学科

> ⚠️ 删除前先列出待删除清单，确认后再执行。兴趣驱动型学科（科学/地理）如果知识库中没有对应教材，`records/<subject>/` 可能不存在，跳过即可。

### Step 4: 启动看板
```bash
nohup python data_api.py > /tmp/data_api.log 2>&1 &
```
然后用 `present_files(["http://localhost:5177/"])` 打开看板。

### Step 5: 设置每日自动化任务

弹出选项卡，让用户配置两个每日自动化任务的时间：

#### 5a: 每日复习提醒时间

弹出选项卡（AskUserQuestion 单选）：
```
问题：每天几点提醒今日复习内容？
选项：
  - 早上 9:00（推荐）
  - 早上 8:00
  - 上午 10:00
  - 其他时间（用户自定义）
```

> 默认 09:00。用户可输入自定义时间（如 14:30）。

#### 5b: 每日学习总结时间

弹出选项卡（AskUserQuestion 单选）：
```
问题：每天几点总结当日学习内容？
选项：
  - 晚上 10:00（推荐）
  - 晚上 9:00
  - 晚上 11:00
  - 其他时间（用户自定义）
```

> 默认 22:00。用户可输入自定义时间。

#### 5c: 创建自动化任务

使用 `automation_update` 工具创建两个定时任务：

**任务 1 — 每日复习提醒**

```
automation_update({
  mode: "create",
  name: "我是学霸-每日复习提醒",
  scheduleType: "recurring",
  rrule: "FREQ=DAILY;BYHOUR={复习提醒小时};BYMINUTE={复习提醒分钟}",
  status: "ACTIVE",
  cwds: "{项目根目录路径}",
  prompt: "你是「我是学霸」学习系统的复习提醒助手。请执行以下操作：

1. 读取 review/next-review.json，检查今天有哪些到期的知识点复习和错题复习
2. 读取 review/errors-review.json，检查今天到期的错题复习
3. 如果有到期复习内容，输出「📚 今日复习清单」：
   - 按学科分组列出：学科 → 知识点名称 → 复习轮次（第N轮/共6轮）
   - 标注哪些是错题复习（加红色标记）
   - 提示用户：「请完成以上复习内容，完成后在看板上勾选，或告诉老师已复习完」
4. 如果今天没有到期复习内容，输出「✅ 今天没有到期的复习任务，可以学习新内容或休息一天！」"
})
```

**任务 2 — 每日学习总结**

```
automation_update({
  mode: "create",
  name: "我是学霸-每日学习总结",
  scheduleType: "recurring",
  rrule: "FREQ=DAILY;BYHOUR={总结小时};BYMINUTE={总结分钟}",
  status: "ACTIVE",
  cwds: "{项目根目录路径}",
  prompt: "你是「我是学霸」学习系统的每日总结助手。请执行以下操作：

1. 回顾今天的「我是学霸」学习系统对话内容，总结今日学习情况：
   - 哪些学科、学了哪些知识点、做了哪些练习
   - 学生表现如何（答对/答错/哪些地方卡住）

2. 核实并更新已掌握知识点：
   - 检查各科 records/<subject>/mastered.md
   - 今天新掌握的知识点 → 添加到 mastered.md（标记 ✅）
   - 今天出错的已掌握知识点 → 更新标记为 🔴（易错）

3. 更新易错点记录：
   - 检查各科 records/<subject>/errors.md
   - 今天产生的错题 → 追加到 errors.md（含日期、题目、错误原因）

4. 更新复习计划：
   - 检查 review/next-review.json
   - 今天标记掌握的新知识点 → 添加第1轮复习计划（明天到期）
   - 今天完成复习的项目 → 推进到下一轮，更新 nextReviewDate
   - 确保数据格式正确

5. 输出「📋 今日学习总结报告」：
   ```
   📋 今日学习总结 {YYYY-MM-DD}

   📖 学习内容：
   - {学科}：{知识点} — {掌握情况}

   ✅ 新掌握知识点：
   - {学科}：{知识点列表}

   🔴 今日易错点：
   - {学科}：{错题简述}

   📅 明日复习任务：
   - {学科}：{知识点}（第N轮）

   💡 建议：{针对性建议}
   ```
})
```

> ⚠️ 注意：自动化任务的 cwds 必须设置为当前项目根目录的绝对路径。rrule 中的小时和分钟根据用户选择的时间填入。

### Step 6: 输出总结
```
🎉 系统初始化完成！

✅ 环境检查通过
✅ 产物目录已初始化
✅ {N}科教师提示词已生成（{科目列表}）
✅ 待学知识点已填充
✅ 未选学科已清理（{已删除的学科列表}，或"无"）
✅ 看板已启动：http://localhost:5177/
✅ 每日复习提醒已设置（每天 {复习时间}）
✅ 每日学习总结已设置（每天 {总结时间}）

💡 现在可以说"切换成XX老师"开始学习
```

### 已初始化时的处理
如果检测到系统已初始化（存在 `teachers/*.md` 非模板内容且有对应的 `records/*/todo.md`），提示用户：
> 系统已完成初始化（已配置：{科目列表}）。如需重新配置某科，说"重新初始化数学老师"；如需追加新科目，说"初始化XX老师"；如需调整自动化时间，说"修改复习提醒时间"或"修改学习总结时间"；如需直接学习，说"切换成XX老师"。

## 快速启动指令

当用户说"打开看板"时：
1. 检查 `data_api.py` 是否在运行（`curl http://localhost:5177/api/status`）
2. 如未运行，用 `nohup python data_api.py > /tmp/data_api.log 2>&1 &` 启动
3. `present_files(["http://localhost:5177/"])`

## 目录结构

```
├── teachers/          6科AI老师提示词
├── system/            规则+模板+锚点库
├── knowledge-base/    教材知识库
├── question-bank/     习题库 JSONL
├── records/           学习记录（每科4文件）
├── review/            艾宾浩斯复习队列
├── artifacts/         教学产物（运行时生成）
├── video-pipeline/    视频制作流水线
├── dashboard.html     学习进度看板
├── data_api.py        Flask API 服务
├── exercise_engine.py 练习题生成引擎
├── 系统搭建指南.md     完整搭建说明
└── README.md          项目说明
```

## 学科切换

当用户说"切换成XX老师"时，读取并加载对应的提示词文件：
- 数学 → `teachers/math.md`
- 语文 → `teachers/chinese.md`
- 英语 → `teachers/english.md`
- 科学 → `teachers/science.md`
- 地理 → `teachers/geography.md`
- 物理 → `teachers/physics.md`

## 全局约束

### 语文
- **不教笔顺/田字格占位**：只展示规范楷体字形
- 汉字展示必须用系统楷体字体渲染，禁止 SVG 自绘字形

### 英语
- **不教发音/听力/口语**：只教书面认读+写作
- **不教书写顺序/笔顺/占格**：只展示字母规范字形

### 物理
- 跳级衔接型起点：人教版初中物理八上，从"长度和时间的测量"开始

## Flask 后台注意事项

- `data_api.py` 使用 Flask，**必须用 `nohup python data_api.py > /tmp/data_api.log 2>&1 &` 启动**
- 不能用 WorkBuddy 的 `run_in_background=true`（会永久卡住）
- 服务运行在 localhost:5177

## 教学产物存放

教学过程中生成的所有文件归入 `artifacts/` 对应子目录：
- 路径：`artifacts/{学科}/{类型}/`
- 命名：`{YYYY-MM-DD}_{描述}.{ext}`
- 初始化：`python artifacts_init.py --init`

## 复习机制

- 知识点复习：6轮间隔（1-2-4-7-15-30天）
- 错题复习：5轮间隔（1-2-3-5-7天）
- 标记掌握 → 自动建立复习计划 → 到期提醒 → 完成推进轮次

## 新增学科

**推荐方式**：在对话中说"新增XX老师"或"创建XX老师"，自动加载 `skills/teacher-prompt-creator` skill，通过选项卡问答完成提示词生成 + 学科初始化。

**手动方式**：
1. 复制 `system/teacher-prompt-template.md` 为 `teachers/{新学科}.md`
2. 按 `system/teacher-prompt-rules.md` 的十一大模块规范填写
3. 创建 `records/{新学科}/` 目录（mastered/todo/errors/review-log/teaching-log）
4. 更新 `data_api.py` 和 `dashboard.html` 配置
5. `python artifacts_init.py --subject {新学科}`

## Troubleshooting

- 看板打不开 → 检查 `data_api.py` 是否运行在 5177 端口
- 连接API按钮 → 服务已在 localhost:5177，直接访问即可，无需手动点按钮

## 内置 Sub-Skills

系统内置 8 个子 skill，分系统管理和交互教学两类。AI agent 加载这些 skill 后具备完整的自动化能力。

**系统管理类：**

| Skill | 触发词 | 核心功能 |
|-------|--------|---------|
| `skills/teacher-prompt-creator/` | 初始化、新增学科、创建老师、写提示词 | 半自动生成提示词 + 学科初始化 |
| `skills/exercise-generator/` | 出题、生成练习题、做卷子、打印练习题 | 三级题源 + 批改流程 + A4/A3试卷HTML |
| `skills/qa-assistant/` | 为什么XX、查一下XX、XX是什么 | 防幻觉三步法问答 |

**EduLab 交互教学类**（kernel 精确计算驱动，产出自包含 HTML）：

| Skill | 学科/年级 | 核心功能 |
|-------|----------|---------|
| `skills/edu-block-views/` | 小学数学·观察物体 | 3D方块+三视图同步，4种教学模式 |
| `skills/edu-plane-geometry/` | 小学~初中·平面几何 | SVG精确几何图+分步解析 |
| `skills/edu-solid-geometry/` | 高中数学·立体几何 | 3D模型+MathJax解析（线面角/二面角等） |
| `skills/edu-analytic-geometry/` | 高中数学·解析几何 | 滑块控制台+KaTeX+2D动态画板 |
| `skills/edu-chem-reaction/` | 高中化学·反应微观演示 | 3D分子动画+方程配平+原子守恒 |

**使用方法**：在 WorkBuddy 对话中，AI 会根据用户意图自动加载对应 skill。
