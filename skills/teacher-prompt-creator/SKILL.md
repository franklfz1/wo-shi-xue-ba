---
name: teacher-prompt-creator
description: |
  「我是学霸」系统的教师提示词生成技能。当用户说"初始化"、"新增学科"、"创建XX老师"、"写老师提示词"时触发。
  严格遵循 teacher-prompt-rules.md 的十一大模块规范，通过选项卡问答收集学科定位信息，
  生成完整的AI老师提示词文件，并自动完成学科初始化（records目录/看板卡片/复习配置）。
agent_created: true
version: 1.0.0
---

# Teacher Prompt Creator

## Overview

为「我是学霸」系统生成或更新学科AI老师提示词。严格遵循 `references/teacher-prompt-rules.md` 的十一大模块规范，不得省略或跳过任何模块。

## When to Use

- 用户说"初始化"（由主 skill 的"一键初始化"流程调用，执行 Complete Initialization Mode）
- 用户说"新增学科"、"创建XX老师"、"写老师提示词"
- 用户说"初始化XX老师"（单独配置一科）
- 用户需要为新学科建立完整的老师提示词体系

## Workflow

### Phase 1: Collect Configuration via AskUserQuestion

> **调用方式说明**：
> - **单独配置一科**（"初始化XX老师"）：依次弹出全部 6 项问答（Q1-Q6）。
> - **由主 skill 调用**（Complete Initialization Mode）：年级和科目已由主 skill 通过 3a/3b 收集，Q1（学科名称）和 Q4（学生年级）已预填，只需弹出 Q2/Q3/Q5/Q6 四项问答。

依次弹出选项卡，收集6项配置：

**Q1 - 学科名称**
```
选项: 数学 / 语文 / 英语 / 科学 / 地理 / 物理 / 其他（需填写ID）
```
→ subject_id = 用户选择（小写英文，如 math）

**Q2 - 定位类型**
```
选项:
- 跳级衔接型（低年级已掌握，直接教高年级内容，如数学、物理）
- 拓展提升型（有基础，需要深化扩展，如语文读写）
- 书面内容导向型（只教读写，不教听说，如英语）
- 兴趣驱动型（无固定大纲，兴趣探索，如科学、地理）
```
→ positioning_type = 用户选择

**Q3 - 教材版本**
```
选项: 人教版 / 统编版 + X年级上册 / X年级下册（学前/一年级~九年级）
```
→ textbook = 组合结果（如"人教版一年级上册"）

**Q4 - 学生年级**
```
选项: 学前 / 一年级 / 二年级 / 三年级 / 四年级 / 五年级 / 六年级 / 初一 / 初二 / 初三 / 高一 / 高二 / 高三
```
→ student_grade = 用户选择

**Q5 - 当前学生水平**
```
选项:
- 零基础（从未接触过该学科）
- 略有了解（接触过少量概念，但不系统）
- 基础扎实（教材同步内容基本掌握）
- 超前学习（已掌握当前年级，正在学更高年级内容）
```
→ student_level = 用户选择

**Q6 - 教学风格**
```
选项:
- 活泼探险型（适合低龄/兴趣驱动型学科，如科学、地理）
- 温暖陪伴型（适合拓展提升型，如语文、英语）
- 严谨教练型（适合跳级衔接型，如数学、物理）
- 幽默启发型（适合中高年级自主学习）
```
→ teaching_style = 用户选择

### Phase 2: Generate Teacher Prompt

1. 读取 `references/teacher-prompt-rules.md`（必须严格遵循十一大模块）
2. 读取 `references/teacher-prompt-template.md` 作为填充框架
3. 根据6项配置，填充模板生成完整提示词
4. 写入 `teachers/<subject_id>.md`

**十一大模块（不得省略）**：
1. 角色定位
2. 教学风格
3. 图文交互教学规则
4. 知识体系（按教材单元分阶段）
5. 常见易错点
6. 掌握判断标准
7. 练习出题模式（五级难度 L1-L5）
8. 学习记录格式
9. 知识边界与防幻觉规则
10. 教学摘要记录规则
11. 切换提示
+ 学科禁忌清单

### Phase 3: Subject Initialization（自动执行）

生成提示词后，**必须**执行以下初始化步骤：

#### 3.1 创建 records 目录和文件
```bash
# 创建目录
mkdir -p records/<subject_id>/

# 创建5个空模板文件
# mastered.md — 已掌握知识点
# todo.md — 待学知识点
# errors.md — 错题/易错点记录
# review-log.md — 复习打卡表
# teaching-log.md — 教学日志
```

#### 3.2 更新 review 配置
读取 `review/next-review.json`，将新学科追加到 `subjects` 数组：
```json
{
  "subjects": ["chinese", "math", "english", "science", "geography", "physics"]
  // ↑ 新学科追加到数组末尾
}
```

#### 3.3 更新 dashboard.html 科目卡片

找到 `dashboard.html` 中的 `SUBJECTS` 配置（JavaScript 常量），追加新卡片：

**预设颜色对照**：

| 学科ID | 颜色 | 学科ID | 颜色 |
|--------|------|--------|------|
| math | #3B82F6（蓝） | science | #F97316（橙） |
| chinese | #EF4444（红） | geography | #8B5CF6（紫） |
| english | #22C55E（绿） | physics | #06B6D4（青） |
| 其他 | #6B7280（灰） | 初始积分 | 0 |

在 `SUBJECTS` 数组末尾追加对象：
```javascript
{
  id: '<subject_id>',
  name: '<中文名>',
  color: '<颜色>',
  icon: '📚',  // 或其他合适图标
  score: 0,
  mastered: 0
}
```

#### 3.4 创建 FAQ 引导问题文件

创建 `teachers/<subject_id>-faq.md`，基于该学科的定位类型和常见易错点，生成10-15个引导性问题模板。

#### 3.5 初始化 artifacts 目录
如果 `artifacts_init.py` 存在，运行：
```bash
python artifacts_init.py --subject <subject_id>
```

#### 3.6 自动生成 todo.md（从教材知识库读取）

根据 Phase 1 收集的 Q3（教材版本）和 Q4（学生年级），从 `knowledge-base/` 读取对应教材的知识点，自动填充 `records/<subject_id>/todo.md`。

**读取逻辑**：

1. 根据学科 + 教材版本 + 年级，定位知识库文件：
   - 数学+人教版+一年级上 → `knowledge-base/math/grade-1-upper.md`
   - 数学+人教版+一年级下 → `knowledge-base/math/grade-1-lower.md`
   - 语文+统编版+一年级上 → `knowledge-base/chinese/grade-1-upper.md`
   - 其他组合：检查 `knowledge-base/_meta/textbook-index.md` 获取文件路径
   - 如果知识库中没有对应文件：跳过此步骤，输出提示"未找到 <教材> 对应的知识库文件，请手动填写 todo.md"

2. 解析知识库文件，提取单元标题和知识点条目

3. 根据 Q5（学生水平）过滤：
   - 零基础 / 略有了解 → 全部知识点写入 todo.md
   - 基础扎实 → 当前年级知识点标记为已掌握（写入 mastered.md），下一年级写入 todo.md
   - 超前学习 → 跳过当前年级，下一年级知识点写入 todo.md

4. 生成 todo.md 格式：
```markdown
## 待学知识点

> 来源：<教材版本+年级> | 生成时间：<YYYY-MM-DD>

### 第X单元 <单元标题>
- ⬜ 知识点1
- ⬜ 知识点2

### 第X+1单元 <单元标题>
- ⬜ 知识点3
- ⬜ 知识点4
```

5. 如果 Q5 为"基础扎实"或"超前学习"，同时生成 mastered.md：
```markdown
## 已掌握知识点

> 根据"<学生水平>"定位自动标记，请核实后调整

### <年级/单元>
- ✅ 知识点1
- ✅ 知识点2
```

**兴趣驱动型学科特殊处理**：
如果 Q2 为"兴趣驱动型"（如科学、地理），知识库中可能没有固定教材。此时：
- 检查 `teachers/<subject_id>.md` 中的知识体系部分，提取主题列表
- 将主题列表写入 todo.md 作为探索方向

### Phase 4: Output Summary

初始化完成后，输出清单：
```
✅ 教师提示词已生成: teachers/<subject_id>.md
✅ records 目录已创建: records/<subject_id>/
✅ 待学知识点已填充: records/<subject_id>/todo.md（从 knowledge-base/ 读取 N 个知识点）
✅ 看板已注册: dashboard.html
✅ 复习配置已更新: review/next-review.json
✅ FAQ 引导问题: teachers/<subject_id>-faq.md

💡 建议：切换成 <中文名>老师 测试提示词效果
```

## Complete Initialization Mode（全部科目初始化）

当用户说"初始化"（由主 skill 调用）时，主 skill 已通过 Step 3a/3b 收集了年级和科目列表。本 skill 接收以下预填参数：

- `student_grade`：用户在 3a 选择的年级
- `selected_subjects`：用户在 3b 多选的科目列表（如 ["math", "chinese", "english"]）

对 `selected_subjects` 中的每个科目依次执行 Phase 2 + Phase 3，每科**跳过 Q1（学科名称）和 Q4（学生年级）**，只弹出 4 项选项卡问答：

| 配置项 | 选项 |
|--------|------|
| 定位类型（Q2） | 跳级衔接型 / 拓展提升型 / 书面内容导向型 / 兴趣驱动型 |
| 教材版本（Q3） | 人教版/统编版 + student_grade 上下册 |
| 当前水平（Q5） | 零基础 / 略有了解 / 基础扎实 / 超前学习 |
| 教学风格（Q6） | 活泼探险型 / 温暖陪伴型 / 严谨教练型 / 幽默启发型 |

**科目 ID 与中文名对照**（用于颜色分配和文件命名）：

| 学科ID | 中文名 | 颜色 |
|--------|--------|------|
| math | 数学 | #3B82F6（蓝） |
| chinese | 语文 | #EF4444（红） |
| english | 英语 | #22C55E（绿） |
| science | 科学 | #F97316（橙） |
| geography | 地理 | #8B5CF6（紫） |
| physics | 物理 | #06B6D4（青） |

每次只处理一科，输出清单后再继续下一科。全部完成后由主 skill 执行 Step 4（启动看板）和 Step 5（输出总结）。

## Global Constraints

所有生成的提示词必须遵守系统级禁忌：

| 学科 | 禁止教学内容 |
|------|------------|
| 语文 | 笔顺、书写顺序、田字格占位 |
| 英语 | 发音、音标、听力、口语、字母书写顺序、四线三格占位 |
| 数学 | 教材未涉及的公式/定理 |
| 科学 | 死记硬背定义、标准答案 |
| 物理 | 超纲的公式和概念 |
| 地理 | 死记硬背地名和定义 |
