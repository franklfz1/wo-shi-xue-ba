# Problem Schema — edu-plane-geometry

## 数据格式

所有题目最终生成一个 JSON 对象，注入模板的 `__LESSON_DATA__` 占位符。

### 顶层结构

```json
{
  "mode": "rectangle_area",
  "title": "回字形面积计算",
  "grade": "小学",
  "topic": "面积",
  "question": "一个长方形草坪长 15 米...",
  "answer": "50 平方米",
  "figure": { ... },
  "steps": [ ... ],
  "meta": { ... }
}
```

### figure 结构

```json
{
  "vertices": [
    {"x": 0, "y": 0, "label": "A"},
    {"x": 17, "y": 0, "label": "B"}
  ],
  "edges": [
    {"from": 0, "to": 1, "label": "AB", "style": "solid"}
  ],
  "equalMarks": [
    {"edges": [0, 2], "count": 1}
  ],
  "rightAngles": [
    {"vertex": 0, "edge1": 0, "edge2": 3}
  ],
  "parallelMarks": [
    {"edges": [0, 2], "count": 1}
  ],
  "dimensionLabels": [
    {"edge": 0, "text": "17 m", "offset": 0.35, "side": "below"}
  ],
  "regions": [
    {"vertices": [0, 1, 2, 3], "fill": "#fde68a", "opacity": 0.35}
  ],
  "auxLines": [
    {"from": 0, "to": 2, "style": "dashed", "label": "AC"}
  ],
  "angleArcs": [
    {"vertex": 0, "edge1": 0, "edge2": 1, "label": "60°", "radius": 25}
  ]
}
```

### steps 结构

```json
[
  {
    "title": "观察图形",
    "content": "草坪是一个 15×8 的长方形...",
    "highlights": {
      "vertices": [0, 1],
      "edges": [0, 1],
      "regions": [0, 1],
      "equalMarks": [0],
      "parallelMarks": [0],
      "angleArcs": [0]
    }
  }
]
```

`highlights` 中的数组元素是对应列表的索引。被高亮的元素会以不同颜色/透明度渲染。

### meta 结构

```json
{
  "mode": "rectangle_area",
  "title": "回字形面积计算",
  "grade": "小学",
  "topic": "面积",
  "faces": null
}
```

`faces` 仅用于 cube-net 模式，存储每个面的中心和标签信息。

## 坐标系

- 所有顶点坐标使用**数学坐标系**（原点在左下，Y 轴向上）
- 模板负责转换为 SVG 坐标系（原点在左上，Y 轴向下）
- 自动缩放：根据所有顶点的 bounding box 计算缩放比例

## 标注系统

| 标注类型 | 数据字段 | 渲染方式 |
|----------|----------|----------|
| 等长标记 | `equalMarks` | 垂直于边的短杠，count 控制杠数 |
| 直角标记 | `rightAngles` | 顶点处的小正方形 |
| 平行标记 | `parallelMarks` | 边中点处的箭头 |
| 尺寸标注 | `dimensionLabels` | 沿边方向旋转的文字 |
| 角度弧线 | `angleArcs` | 顶点处的圆弧 + 标签 |
| 辅助线 | `auxLines` | 虚线 + 标签 |
| 区域填充 | `regions` | 多边形填充 |

## 题型 mode 值

| mode | 题型 | 年级 | 依赖 |
|------|------|------|------|
| `rectangle_area` | 长方形面积/周长 | 小学 | 无 |
| `triangle_congruence` | 三角形全等证明 | 初中 | 无 |
| `parallelogram_proof` | 平行四边形证明 | 初中 | sympy |
| `cube_net` | 正方体展开图 | 小学 | 无 |
| `shape_counting` | 图形计数 | 小学 | 无 |
