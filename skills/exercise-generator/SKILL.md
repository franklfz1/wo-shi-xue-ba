---
name: exercise-generator
description: |
  「我是学霸」练习题组卷引擎。根据学习进度自动出题，生成可打印的 A4/A3 试卷 HTML。
  支持六学科（数学/语文/英语/科学/地理/物理），数学从题库选题，其他学科 AI 模板生成。
  触发词：出题、组卷、练习题、试卷、出练习题、生成考题、printable exercise。
agent_created: true
---

# 练习题组卷引擎

## 概述

根据孩子当前学习进度（`records/{学科}/mastered.md` + `todo.md`），自动确定待学知识点，从题库选题或 AI 模板生成题目，输出自包含的试卷 HTML 文件，支持 A4/A3 打印、答案切换、一键导出 PDF。

## 何时使用

- 用户说「出题」「出练习题」「组卷」「出一套卷子」「出数学题」等
- 用户要求按学习进度出针对性练习
- 用户要求生成可打印的试卷/练习题

## 三级题源优先级

1. **题库 JSONL**（零幻觉）— 从 `question-bank/` 读取已有题目
2. **exercise_engine.py 程序生成** — 题库不足时调用引擎程序化生成
3. **AI 实时生成**（必须标注 ⚠️）— 引擎也无法覆盖时，AI 生成但必须标注来源

## 核心脚本

**`scripts/exercise_engine.py`** — 组卷引擎，可直接执行：

```bash
# 生成全部学科（各8题，A4）
python scripts/exercise_engine.py

# 只生成数学，10题
python scripts/exercise_engine.py --subject math --count 10

# 指定知识点出题（可多个用 | 分隔）
python scripts/exercise_engine.py --subject chinese --topic "古诗词" --count 6
python scripts/exercise_engine.py --subject math --topic "两位数加一位数、整十数（不进位）|100以内数的认识"

# A3 纸张
python scripts/exercise_engine.py --subject math --paper A3

# 组卷模式：跨单元抽样（忽略学习进度，覆盖全部已学知识点）
python scripts/exercise_engine.py --subject math --broad --count 20

# 指定年级（非1年级时自动跨单元抽样）
python scripts/exercise_engine.py --subject math --grade 5 --count 20
```

**运行前提：** 当前工作目录必须为项目根目录（即 `wo-shi-xue-ba/` 所在位置）。

**Windows 注意**：如遇编码错误，设置环境变量 `PYTHONIOENCODING=utf-8`。

## 命令行参数

| 参数 | 简写 | 默认 | 说明 |
|------|------|------|------|
| `--subject` | `-s` | 全部 | 学科：math/chinese/english/science/geography/physics |
| `--count` | `-c` | 8 | 每份试卷题目数量 |
| `--paper` | `-p` | A4 | 纸张大小：A4 或 A3 |
| `--topic` | `-t` | 自动 | 手动指定知识点，多个用 `\|` 分隔 |
| `--grade` | `-g` | 1 | 年级（1-6），非1时自动跨单元抽样 |
| `--broad` | `-B` | false | 组卷模式：跨单元抽样 |

## 出题模式

### 模式一：学习进度驱动（默认）

1. 读取 `records/{学科}/todo.md` 获取待学知识点列表
2. 取前 3 个未掌握知识点，按比例分摊题量
3. 数学 → 从题库 JSONL 选取（精确映射 + 模糊匹配兜底）
4. 其他学科 → AI 模板生成（标记 `source: ai-generated`）
5. 生成 HTML 到 `artifacts/exercises/`

### 模式二：手动指定知识点（`--topic`）

直接用指定知识点出题，跳过进度检测。适合用户说「出一道古诗词的题」这类需求。

### 模式三：跨单元组卷（`--broad` 或 `--grade > 1`）

从题库所有题目中按单元均衡抽样，覆盖不同难度和题型，适合期末复习或综合测试。

## 出题前自检（强制）

出题前必须先算出正确答案，标注难度级别。具体难度标准见 `references/difficulty-standards.md`。

## 批改流程

1. **先说对的** — 肯定用户做对的部分
2. **指出可更好的** — 哪里可以改进
3. **完整演示** — 给出完整解题过程
4. **记录错误** — 错题追加到 `records/{学科}/errors.md`

## 输出文件

- **路径：** `artifacts/exercises/{YYYY-MM-DD}_{学科}_{知识点}.html`
- **自包含：** 所有 CSS/JS 内联，图片 base64 嵌入，可离线打开
- **HTML 功能：**
  - 「显示答案」按钮切换答案显示
  - 「导出PDF」按钮调用浏览器打印（选「另存为 PDF」）
  - A4/A3 下拉切换纸张尺寸
  - 打印时自动隐藏按钮，答案默认不打印
  - 密封线 + 得分表 + 按难度分大题（基础/巩固/提高）

## 数据依赖

### 题库目录结构

详见 `references/question-bank-guide.md`。

### 题目 JSONL 格式

每行一个 JSON 对象，字段如下：

```json
{
  "id": "math-g1-L1-0001",
  "difficulty": "L1",
  "type": "计算",
  "subtype": "5以内加法",
  "knowledge_point": "1~5的加法",
  "textbook_unit": "一 5以内数的认识和加、减法",
  "question": "1 + 1 = ?",
  "answer": 2,
  "explanation": "1和1合起来是2",
  "distractors": [1, 3, 4],
  "options": [],
  "image": "images/xxx.png",
  "page_ref": "全优卷一下 p.4",
  "source": "program-generated"
}
```

- `difficulty`: L1(基础) ~ L5(挑战)
- `type`: 计算 / 填空 / 选择 / 应用题 / 简答 / 写字 / 抄写
- `image`: 相对路径，指向 `textbook/images/` 下的图片
- `source`: `program-generated` / `textbook-xxx` / `ai-generated`

### 学习进度文件

- `records/{学科}/mastered.md` — 已掌握知识点（`- ✅` 开头）
- `records/{学科}/todo.md` — 待学知识点（`- ⬜` 开头，按优先级排序）
- `records/{学科}/errors.md` — 错题记录

### 知识点映射

`todo.md` 中的知识点描述较细，题库中的较粗，引擎内置映射表 `KNOWLEDGE_POINT_MAP` 进行转换。详见 `references/knowledge_point_map.md`。

若用户反馈「选题不相关」，检查映射表是否覆盖了该知识点，缺失则在 `exercise_engine.py` 的 `KNOWLEDGE_POINT_MAP` 中添加映射。

## AI 生成题目说明

非数学科（语文/英语/科学/地理/物理）的题目由引擎内置模板生成，HTML 中标记 `[AI]`。生成后应审核题目摘要输出，确认题目质量后再给孩子使用。

各科生成器支持的题型：
- **语文：** 写字（提取括号内汉字）、握笔姿势、古诗词（背诵填空 + 诗意理解 + 作者配对）、阅读理解
- **英语：** 字母/颜色/动物/数字/水果/身体单词抄写
- **科学：** 动物/植物/地球/静电/磁铁主题简答
- **地理：** 大洲/大洋/河流/沙漠/极地等常识简答
- **物理：** 长度测量/单位换算/误差等简答

## 常见问题

### 选题不相关
知识点名称与题库不匹配 → 检查 `KNOWLEDGE_POINT_MAP`，添加映射。

### 题目全挤在一个窄知识点
默认取 3 个知识点分摊题量。若 `todo.md` 只有一个待学项，可用 `--topic` 手动指定多个。

### Windows 控制台乱码
引擎已内置 `sys.stdout.reconfigure(encoding="utf-8")`，若仍有问题，确保终端编码为 UTF-8。

### 打印排版问题
- 默认 A4 竖向，8mm 页边距
- 计算题双栏排列，其他题型单栏
- 打印时得分表、按钮、AI 提示自动隐藏
- 答案区默认不打印，需先点「显示答案」再打印

## references 文件

- `references/difficulty-standards.md` — L1-L5 六科详细难度定义（30 例）
- `references/question-bank-guide.md` — 题库结构与使用说明
- `references/knowledge_point_map.md` — 知识点映射表与匹配策略
