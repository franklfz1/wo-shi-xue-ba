---
name: edu-block-views
description: >-
  把一道"方块三视图"题解成自包含的交互教学网页，支持四种教学模式：
  (1) demo 演示模式——3D 可拖拽方块 + 三视图同步 + 分步讲解 + 答案隐藏/揭示；
  (2) draw 画图模式——展示 3D 模型，学生在方格纸上点击填涂三视图，与标准答案比对（绿色正确/红色多画/橙色漏画）；
  (3) reverse 逆向还原——展示三视图，学生在 3D 网格上左键放置/右键移除方块，实时预览比对；
  (4) choice 选择题——四个立体图形（2D 等轴测渲染），辨析哪个的指定方向视图与其他不同。
  覆盖小学数学"观察物体"单元：立方体堆放三视图、正方体计数、从不同方向看立体图形等题型。
  所有视图由 block_kernel.py 精确计算（纯整数运算，无浮点误差），3D 渲染坐标与视图数据同源一致，
  保证"图、解、答"零误差。选择题模式自动生成四组摆放并保证同组视图严格相同、不同项严格不同。
  触发词：方块三视图, 从正面看, 从上面看, 从左面看, 从侧面看, 立方体堆放, 正方体堆放,
  观察物体, 空间视图, 三视图, 从不同方向看, 画三视图, 还原方块, 视图辨析, 哪个不同;
  block views, front view, top view, side view, cube stacking, observe objects from different directions,
  draw views, reconstruct blocks, which is different.
agent_created: true
source: 我是学霸 EduLab 系列（原创，借鉴 edu-solid-geometry 的架构思路，简化为小学整数运算）
---

# edu-block-views — 方块三视图交互教学

## 概述

把一道"观察物体"题（立方体堆放三视图）变成自包含的交互教学网页。
3D 可拖拽旋转 + 2D 三视图同步 + 分步讲解 + 答案揭示/隐藏。

**核心原则**：图不是 AI "画"的，是 kernel "算"出来的。同一套方块数据同时驱动
3D 渲染和 2D 投影，保证"图、解、答"严格一致。

## 架构

```
题目/随机 → block_kernel.py (整数运算) → lesson data (JSON)
                                          ↓                    ↓
                                     3D 渲染 (Three.js)    2D 投影 (Canvas)
                                          ↓                    ↓
                                     generate.py 注入 template/lesson.html
                                          ↓
                                     自包含 HTML 页面
```

### 与 edu-solid-geometry 的区别

| 维度 | edu-solid-geometry | edu-block-views |
|------|-------------------|-----------------|
| 年级 | 高中 | 小学 1-6 年级 |
| 计算核心 | sympy 符号运算 | 纯 Python 整数运算 |
| 坐标精度 | 精确根式 | 精确整数 |
| 3D 渲染 | Three.js（连续坐标） | Three.js（整数网格） |
| 2D 投影 | 无 | Canvas 三视图（核心输出） |
| 依赖 | sympy | 无（标准库即可） |

## 依赖

无外部依赖。Python 3.8+ 标准库即可运行。

**Windows 注意**：如遇编码错误，设置环境变量 `PYTHONIOENCODING=utf-8`。

## 使用方式

### 方式一：随机出题

```bash
cd .workbuddy/skills/edu-block-views
PYTHONIOENCODING=utf-8 python scripts/generate.py --random --width 3 --depth 3 --max-height 3 --seed 42
```

### 方式二：指定摆放

```bash
python scripts/generate.py --blocks '[[2,1,3],[1,2,1]]'
```

blocks 是 2D JSON 数组，`heights[x][y]` = 该位置堆放的方块数。

### 方式三：在对话中触发

直接描述题目即可，AI 会自动解析为方块摆放并生成页面。例如：
- "3×3 的网格上，(0,0) 放 2 个，(1,1) 放 3 个，(2,0) 放 1 个，画出三视图"
- "随机出一道方块视图题"
- "从正面看是 [2,1,3]，从左面看是 [3,1]，从上面看是 2×3 的满网格，还原能摆多少方块？"

## 文件结构

```
edu-block-views/
├── SKILL.md                  ← 本文件
├── lib/
│   └── block_kernel.py       ← 计算核心（纯整数运算，自检）
├── template/
│   └── lesson.html           ← HTML 模板（Three.js + Canvas + 步骤导航）
├── scripts/
│   └── generate.py           ← 生成脚本（注入 lesson data 到模板）
└── references/
    └── problem-schema.md     ← 数据格式参考
```

## 四种教学模式

### demo — 演示模式（默认）

3D 可拖拽模型 + 三视图同步 + 分步讲解 + 答案隐藏/揭示。

```bash
python scripts/generate.py --random --width 3 --depth 3
python scripts/generate.py --blocks '[[2,1],[1,2]]'
```

### draw — 画图模式

展示 3D 模型，学生在方格纸上点击填涂三视图，与标准答案比对。
绿色=正确，红色×=多画，橙色虚线=漏画。

```bash
python scripts/generate.py --mode draw --random --seed 42
```

### reverse — 逆向还原模式

展示三视图，学生在 3D 网格上还原方块摆放。
左键点击放置方块，右键点击移除方块，实时预览三视图比对。

```bash
python scripts/generate.py --mode reverse --random --seed 33
```

### choice — 识图选择题模式

展示一个 3D 模型（可旋转观察），给出四个不同方向的视图选项（正面/背面/左面/上面），
问"哪个是从正面看的？"。学生选择后确认，正确显示绿色，错误显示红色+揭示正确答案。
支持 front/left/top/back/right 五个方向。

```bash
python scripts/generate.py --mode choice --direction front --seed 55
python scripts/generate.py --mode choice --direction top --seed 88
python scripts/generate.py --mode choice --direction left --seed 42
```

## 正确性自检

- `block_kernel.py` 内置 `self_test()`，运行 `python lib/block_kernel.py` 即可执行
- 14 项自检覆盖：已知题目验证、边界情况、随机生成一致性、序列化正确性、
  画图模式数据、逆向模式数据、选择题视图一致性（front/top 双方向）、
  back_view/right_view 正确性、识图模式四选项互不相同验证
- 视图一致性：正面视图列数 = 网格宽度，侧面视图列数 = 网格深度，俯视图尺寸 = 网格尺寸
- 识图选择题保证：四个选项视图互不相同，正确选项确实是指定方向的视图

## 扩展方向

1. **难度分级**：L1(2×2) / L2(3×3) / L3(4×3) / L4(不规则形状)
2. **计时模式**：画图/逆向模式增加计时，记录完成时间
3. **多解讨论**：逆向模式中标注"此题有多个解，你找到的是其中之一"
