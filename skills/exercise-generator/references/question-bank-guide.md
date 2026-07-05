# 题库结构与使用说明

> 本文件是 exercise-generator skill 的题库参考指南。

---

## 题库目录结构

```
question-bank/
├── README.md                    # 题库说明（本文件）
├── math/
│   ├── grade-1/
│   │   ├── generated/           # 程序化生成的习题
│   │   │   ├── L1.jsonl        # L1难度 ~100题
│   │   │   ├── L2.jsonl        # L2难度 ~100题
│   │   │   ├── L3.jsonl        # L3难度 ~100题
│   │   │   └── L4.jsonl        # L4难度 ~100题
│   │   └── textbook/           # 教材配套习题（预留）
│   ├── grade-2/                # 扩展目录
│   └── _generator/
│       └── gen_math_g1.py      # 数学一年级生成器（exercise_engine.py调用）
├── chinese/
│   ├── grade-1/
│   │   ├── poetry/             # 古诗填空题库
│   │   └── characters/         # 生字练习题库
│   └── grade-2/
└── english/
    └── grade-1/
        ├── vocabulary/         # 单词练习
        └── sentences/          # 句子练习
```

---

## JSONL 文件格式

每行一个 JSON 对象，字段说明：

```jsonl
{"question": "28 + 47 = ?", "answer": "75", "difficulty": "L3", "topic": "两位数加法_进位", "type": "calc", "grade": "1", "semester": "upper"}
{"question": "下列哪个是哺乳动物？A.金鱼 B.熊猫 C.青蛙 D.燕子", "answer": "B", "difficulty": "L2", "topic": "动物分类", "type": "choice", "grade": "1", "semester": "lower"}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| question | string | 题目文本 |
| answer | string | 标准答案 |
| difficulty | string | L1-L5 |
| topic | string | 所属知识点 |
| type | string | 题型：choice/fill/calc/open/judge |
| grade | string | 适用年级 |
| semester | string | 上/下册 |

---

## exercise_engine.py 调用方式

```bash
# 基础调用
python exercise_engine.py --subject math --count 5

# 指定年级和难度
python exercise_engine.py --subject math --count 3 --difficulty L3 --grade 1 --semester upper

# 输出JSON格式（供AI读取）
python exercise_engine.py --subject math --count 5 --output json

# 查看支持的知识点列表
python exercise_engine.py --subject math --list-topics
```

当前支持：
- 数学一年级上册（L1-L4）
- 数学一年级下册（L1-L4）

---

## 题库与教材的对应关系

| 知识点 | 教材位置 | 题库文件 | 生成器覆盖 |
|--------|---------|---------|-----------|
| 10以内加减法 | 1上第1单元 | L1 | ✅ |
| 20以内进位加法 | 1上第3单元 | L2-L3 | ✅ |
| 20以内退位减法 | 1下第2单元 | L2-L3 | ✅ |
| 认识图形 | 1上第4单元 | L1-L2 | ✅ |
| 100以内数 | 1下第4单元 | L1 | ✅ |
| 认识人民币 | 1下第5单元 | L1-L2 | ✅ |

---

## 题库扩展指南

### 添加新知识点
1. 在 `question-bank/<subject>/grade-X/generated/` 创建新的 JSONL 文件（命名：知识点.jsonl 或归入对应难度）
2. 每行格式严格按上述 JSONL 格式
3. 更新 README.md 的对应关系表

### 添加新年级
1. 创建 `question-bank/<subject>/grade-Y/` 目录
2. 运行 `question-bank/<subject>/_generator/gen_math_gY.py` 生成 JSONL（如果支持程序生成）
3. 手动补充 AI 生成的题目到对应难度 JSONL 文件

### 题库为空时的处理

当题库文件不存在或记录数为0时，按以下顺序降级：
1. 调用 `python exercise_engine.py --subject <subj> --count N`
2. 如 exercise_engine.py 不支持该学科/年级 → AI 实时生成（标注⚠️）

---

## 质量检查

题库维护时，执行以下检查：
- [ ] 每道题有且仅有一个正确答案
- [ ] 答案无歧义
- [ ] 难度标签与实际难度一致
- [ ] 题目语言适合目标年级理解力
- [ ] 不存在超纲内容
