# 数据格式参考（problem-schema）

## 1. 方块摆放表示

核心数据结构是 `heights[x][y]`：在 (x, y) 位置堆放的正方体个数。

```
网格 3×2:
  heights[0][0]=2  heights[1][0]=1  heights[2][0]=3
  heights[0][1]=1  heights[1][1]=2  heights[2][1]=1

正面看（x方向最大）: [2, 2, 3]
左面看（y方向最大）: [3, 2]
上面看（有方块=1）: [[1,1],[1,1],[1,1]]
```

## 2. lesson data（注入模板 `__LESSON_DATA__` 的 JSON）

```jsonc
{
  "lesson": {
    "title": "方块三视图",
    "meta": "交互练习 · 观察物体",
    "question": "下面的立体图形由若干个小正方体组成...",
    "cubeCount": 10
  },
  "model": {
    "blocks": [
      {"x": 0, "y": 0, "z": 0, "color": "#FF6B6B"},
      {"x": 0, "y": 0, "z": 1, "color": "#4ECDC4"},
      ...
    ],
    "gridSize": {"width": 3, "depth": 2, "maxHeight": 3}
  },
  "views": {
    "front": {
      "heights": [2, 2, 3],        // 每列最大高度
      "grid": [[0,0,1],[0,0,1],[1,1,1]],  // 2D布尔网格(row=从上到下)
      "label": "从正面看"
    },
    "side": {
      "heights": [3, 2],
      "grid": [[0,1],[1,1],[1,1]],
      "label": "从左面看"
    },
    "top": {
      "cells": [[1,1],[1,1],[1,1]],
      "grid": [[1,1],[1,1],[1,1]],
      "label": "从上面看"
    }
  },
  "steps": [
    {
      "title": "观察立体图形",
      "content": "<p>...</p>",
      "highlight": "scene"  // scene | front | side | top
    },
    ...
  ]
}
```

## 3. 坐标映射

| 坐标 | 含义 | 范围 |
|------|------|------|
| x | 列方向（从左到右） | 0 ~ width-1 |
| y | 行方向（从近到远） | 0 ~ depth-1 |
| z | 高度方向（从下到上） | 0 ~ heights[x][y]-1 |

Three.js 映射：kernel (x, y, z) → three (x+offsetX, z+0.5, y+offsetZ)

## 4. 视图计算规则

- **正面视图**：`front[x] = max(heights[x][y] for all y)`，取每列最高
- **左面视图**：`side[y] = max(heights[x][y] for all x)`，取每行最高
- **俯视图**：`top[x][y] = 1 if heights[x][y] > 0 else 0`，有方块即填

## 5. 层颜色

```python
LAYER_COLORS = [
    "#FF6B6B",  # 第1层
    "#4ECDC4",  # 第2层
    "#FFE66D",  # 第3层
    "#95E1D3",  # 第4层
    "#C7B6E5",  # 第5层
    "#FFA07A",  # 第6层
]
```

方块按 z 坐标（层）着色，不同层不同颜色，便于观察堆叠关系。
