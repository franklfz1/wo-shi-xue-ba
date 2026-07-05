---
name: edu-plane-geometry
description: >-
  把一道平面几何题解成一个自包含的交互教学网页：左侧 SVG 精确几何图形
  （自动缩放 · 顶点标注 · 等长标记 · 直角标记 · 平行标记 · 尺寸标注 · 区域填充），
  右侧分步解析导航 + 答案揭示。覆盖小学到初中平面几何五大题型：
  长方形面积/周长（含回字形组合图形）、三角形全等证明（SAS/ASA/SSS/AAS）、
  平行四边形证明（全等+矩形判定）、正方体展开图（找对面）、图形计数（数三角形/长方形）。
  小学部分用纯算术，初中部分用 sympy 精确坐标计算，保证图形比例精确、图解一致。
  证明题的推理文案由 AI 写，但图由 kernel 保证精确——图不会画错，证明逻辑由 AI 负责。
  触发词：平面几何, 面积计算, 周长计算, 回字形, 石子路, 三角形全等, SAS, ASA, SSS, AAS,
  平行四边形证明, 正方体展开图, 找对面, 数三角形, 数长方形, 图形计数,
  解这道几何题, 画几何图; plane geometry, area, perimeter, triangle congruence,
  parallelogram proof, cube net, shape counting.
agent_created: true
---

# edu-plane-geometry

平面几何交互式教学技能：把平面几何题解成自包含的 SVG 交互教学网页。

## 设计原则

与 EduLab 系列一脉相承——**图不是 AI "画"的，是 kernel "算"出来的**：

| 环节 | 谁负责 | 方式 |
|------|--------|------|
| 图形精确绘制 | kernel | 坐标计算 → SVG，保证比例正确 |
| 已知条件标注 | kernel | 等长标记、直角标记、平行标记自动标注 |
| 计算答案 | kernel | 小学用纯算术，初中用 sympy |
| 证明步骤文案 | AI | AI 写推理过程，kernel 负责格式化和高亮 |

## 支持题型

### 1. rectangle — 长方形面积/周长（含组合图形）

小学数学。支持简单长方形和"回字形"组合图形（大减小）。

```bash
# 简单长方形
python scripts/generate.py --type rectangle --width 5 --height 3

# 回字形（石子路）
python scripts/generate.py --type rectangle --width 15 --height 8 --path-width 1
```

### 2. congruence — 三角形全等证明

初中数学。支持 SAS / ASA / SSS / AAS 四种判定。

```bash
python scripts/generate.py --type congruence --cong-type SAS
python scripts/generate.py --type congruence --cong-type SSS
```

### 3. parallelogram — 平行四边形证明

初中数学。平行四边形 ABCD + E/F 点 + 全等证明。

```bash
python scripts/generate.py --type parallelogram --base 6 --side 4 --angle 60 --be-ratio 0.4
```

### 4. cube-net — 正方体展开图

小学数学/空间想象。11 种展开图形态，找三组对面。

```bash
python scripts/generate.py --type cube-net --net-type cross
python scripts/generate.py --type cube-net --net-type t_shape --reveal
```

### 5. counting — 图形计数

小学数学。数三角形/数长方形。

```bash
python scripts/generate.py --type counting --count-type triangle
python scripts/generate.py --type counting --count-type rectangle
```

## 目录结构

```
edu-plane-geometry/
├── lib/
│   └── plane_kernel.py      # 计算核心 + SVG 数据生成
├── template/
│   └── lesson.html          # SVG 交互式模板
├── scripts/
│   └── generate.py          # CLI 生成脚本
├── references/
│   └── problem-schema.md    # 题目格式参考
└── SKILL.md
```

## 依赖

- Python 3（已就绪）
- sympy（已安装，初中题型需要；小学题型零依赖）
- Windows 运行需设置 `PYTHONIOENCODING=utf-8`

## 正确性自检

- `plane_kernel.py` 内置 `self_test()`，运行 `python lib/plane_kernel.py` 即可执行
- 11 项自检覆盖：长方形面积、回字形面积、三角形全等(SAS/SSS)、
  平行四边形证明(BE=DF验证)、正方体展开图(4种类型)、图形计数(三角形/长方形)、
  序列化正确性、不同参数验证

## SVG 渲染特性

- **自动缩放**：根据顶点坐标自动计算 bounding box，缩放到 600×480 视口
- **坐标系翻转**：数学坐标(Y向上) → SVG坐标(Y向下)
- **标注系统**：
  - 等长标记：单杠/双杠/三杠（相同杠数 = 等长）
  - 直角标记：小正方形
  - 平行标记：箭头（单/双）
  - 尺寸标注：沿边方向旋转的文字
  - 角度弧线：带标签的圆弧
- **分步高亮**：每步可高亮指定的顶点、边、区域、标记
- **答案揭示**：点击按钮显示/隐藏答案

## 扩展方向

1. **更多题型**：梯形面积、圆面积/周长、扇形、相似三角形
2. **动态参数**：滑块控制图形参数，实时更新
3. **交互画图**：学生在 SVG 上画图，与标准答案比对
4. **随机出题**：kernel 随机生成题目参数
5. **难度分级**：L1(基础) / L2(进阶) / L3(挑战)
