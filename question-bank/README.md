# 习题库 (question-bank/)

## 是什么

按学科、年级、难度分级的结构化习题库，是 AI 老师出题时的"弹药库"。

与 `system/knowledge-anchors/` 和 `knowledge-base/` 的关系：
- **锚点库**管"对不对"——标准答案
- **知识库**管"教什么"——教材结构
- **习题库**管"练什么"——按难度分级的练习题

## 目录结构

```
question-bank/
├── math/
│   ├── grade-1/
│   │   ├── generated/          ← 程序生成的习题
│   │   │   ├── L1-basic.jsonl
│   │   │   ├── L2-standard.jsonl
│   │   │   ├── L3-application.jsonl
│   │   │   └── L4-L5-challenge.jsonl
│   │   └── textbook/
│   │       └── after-class.jsonl  ← 教材课后题
│   └── _generator/
│       └── gen_math_g1.py    ← 数学习题生成脚本
├── chinese/
│   └── grade-1/
│       ├── character-recognition.jsonl
│       ├── poetry-fill.jsonl
│       └── after-class.jsonl
└── _meta/
    └── question-index.md
```

## 文件格式 (JSONL)

每道题是一行 JSON：

```json
{
  "id": "math-g1-L1-0001",
  "type": "计算",
  "subtype": "5以内加法",
  "difficulty": "L1",
  "knowledge_point": "1~5的加法",
  "textbook_unit": "一 5以内数的认识和加、减法",
  "question": "2 + 3 = ?",
  "answer": "5",
  "explanation": "2和3合起来是5",
  "distractors": ["4", "6", "3"],
  "source": "program-generated",
  "created": "2026-06-25"
}
```

## 字段说明

| 字段 | 说明 |
|------|------|
| `id` | 唯一编号，格式：`学科-g年级-难度-序号` |
| `type` | 大题型：计算/应用/规律/填空/选择 |
| `subtype` | 子题型：5以内加法/进位加法/求和应用题 |
| `difficulty` | L1-L5，对应五级难度标准 |
| `knowledge_point` | 所属知识点名称 |
| `textbook_unit` | 教材单元名称 |
| `question` | 题目内容 |
| `answer` | 正确答案 |
| `explanation` | 解析/步骤说明 |
| `distractors` | 错误选项（选择题使用） |
| `source` | 来源：program-generated / textbook |
| `created` | 生成日期 |

## 出题优先级

1. **教材课后题** (`textbook/` 目录) — 最贴合教材
2. **程序生成题** (`generated/` 目录) — 量大、答案100%准确
3. **AI 实时生成** — 以上覆盖不足时使用，需符合五级难度标准

## 当前覆盖

| 学科 | 年级 | 习题数量 | 来源 |
|------|------|----------|------|
| 数学 | 一年级 | ~500题 | 程序生成 |
| 语文 | 一年级 | 待补充 | 教材课后题+AI生成 |
