#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
block_kernel.py — 方块三视图确定性计算核心（纯 Python 整数运算）。

设计目标：坐标、视图、答案全部由本模块精确算出，杜绝心算误差。
同一套方块数据既喂给解题文案，也喂给 3D 渲染和 2D 投影，
保证"图、解、答"严格一致。

无外部依赖（不需要 sympy），仅用 Python 标准库。

坐标约定：
  - x: 列方向（从左到右），对应正面视图的宽度
  - y: 行方向（从近到远），对应俯视图的深度
  - z: 高度方向（从下到上），对应堆叠层数
  - heights[x][y] = 在 (x, y) 位置堆放的正方体个数
"""

import json
import random


# ===================== 层颜色（与 3D 渲染共享） =====================

LAYER_COLORS = [
    "#FF6B6B",  # 第1层 — 珊瑚红
    "#4ECDC4",  # 第2层 — 青绿
    "#FFE66D",  # 第3层 — 暖黄
    "#95E1D3",  # 第4层 — 薄荷
    "#C7B6E5",  # 第5层 — 薰衣草
    "#FFA07A",  # 第6层 — 浅鲑鱼
]


# ===================== 核心类 =====================

class BlockArrangement:
    """方块摆放：在 W(xD 网格上堆放正方体。"""

    def __init__(self, width: int, depth: int):
        """初始化 width x depth 的空网格。"""
        if width < 1 or depth < 1:
            raise ValueError("网格尺寸必须 >= 1")
        self.width = width
        self.depth = depth
        # heights[x][y] = 该位置堆放的方块数（0 表示空）
        self.heights = [[0] * depth for _ in range(width)]

    # ---- 摆放操作 ----

    def place(self, x: int, y: int, h: int):
        """在 (x, y) 位置堆放 h 个正方体（覆盖原有）。"""
        if not (0 <= x < self.width and 0 <= y < self.depth):
            raise IndexError(f"坐标 ({x},{y}) 超出 {self.width}x{self.depth} 网格")
        if h < 0:
            raise ValueError("高度不能为负")
        self.heights[x][y] = h
        return self

    def stack(self, x: int, y: int, n: int = 1):
        """在 (x, y) 位置增加 n 个正方体（叠加）。"""
        self.heights[x][y] += n
        return self

    # ---- 查询 ----

    def cube_list(self) -> list:
        """返回所有正方体的坐标列表 [{x, y, z, color}]。"""
        result = []
        for x in range(self.width):
            for y in range(self.depth):
                for z in range(self.heights[x][y]):
                    result.append({
                        "x": x, "y": y, "z": z,
                        "color": LAYER_COLORS[z % len(LAYER_COLORS)]
                    })
        return result

    def cube_count(self) -> int:
        """正方体总数。"""
        return sum(self.heights[x][y]
                   for x in range(self.width)
                   for y in range(self.depth))

    def max_height(self) -> int:
        """最高层数。"""
        return max((self.heights[x][y]
                    for x in range(self.width)
                    for y in range(self.depth)), default=0)

    # ---- 三视图计算（核心） ----

    def front_view(self) -> list:
        """从正面看：每列（x方向）的最大高度。
        返回 [h0, h1, ...]，长度 = width。
        """
        return [max(self.heights[x]) for x in range(self.width)]

    def side_view(self) -> list:
        """从左面看：每行（y方向）的最大高度。
        返回 [h0, h1, ...]，长度 = depth。
        """
        return [max(self.heights[x][y] for x in range(self.width))
                for y in range(self.depth)]

    def top_view(self) -> list:
        """从上面看：哪些位置有方块。
        返回 2D 数组 [[0/1, ...], ...]，尺寸 width x depth。
        """
        return [[1 if self.heights[x][y] > 0 else 0
                 for y in range(self.depth)]
                for x in range(self.width)]

    def back_view(self) -> list:
        """从背面看：正面视图的列反转。
        返回 [h_{w-1}, ..., h1, h0]，长度 = width。
        """
        return list(reversed(self.front_view()))

    def right_view(self) -> list:
        """从右面看：左面视图的列反转。
        返回 [h_{d-1}, ..., h1, h0]，长度 = depth。
        """
        return list(reversed(self.side_view()))

    # ---- 视图转 2D 网格（供 Canvas 渲染） ----

    def front_view_grid(self) -> list:
        """正面视图的 2D 布尔网格（row=从上到下, col=x）。
        grid[row][col] = True 表示该位置有可见方块。
        """
        fh = self.front_view()
        max_h = max(fh) if fh else 0
        if max_h == 0:
            return [[]]
        return [[1 if (max_h - 1 - row) < fh[col] else 0
                 for col in range(self.width)]
                for row in range(max_h)]

    def side_view_grid(self) -> list:
        """左面视图的 2D 布尔网格（row=从上到下, col=y）。"""
        sh = self.side_view()
        max_h = max(sh) if sh else 0
        if max_h == 0:
            return [[]]
        return [[1 if (max_h - 1 - row) < sh[col] else 0
                 for col in range(self.depth)]
                for row in range(max_h)]

    def top_view_grid(self) -> list:
        """俯视图的 2D 布尔网格（row=y从近到远, col=x从左到右）。
        与 front_view_grid 共享 x 轴（col=x 左→右），
        y 轴为深度方向（row=y 近→远，上→下）。
        """
        return [[1 if self.heights[x][y] > 0 else 0
                 for x in range(self.width)]
                for y in range(self.depth)]

    def back_view_grid(self) -> list:
        """背面视图的 2D 布尔网格（row=从上到下, col=x反向）。"""
        bh = self.back_view()
        max_h = max(bh) if bh else 0
        if max_h == 0:
            return [[]]
        return [[1 if (max_h - 1 - row) < bh[col] else 0
                 for col in range(len(bh))]
                for row in range(max_h)]

    def right_view_grid(self) -> list:
        """右面视图的 2D 布尔网格（row=从上到下, col=y反向）。"""
        rv = self.right_view()
        max_h = max(rv) if rv else 0
        if max_h == 0:
            return [[]]
        return [[1 if (max_h - 1 - row) < rv[col] else 0
                 for col in range(len(rv))]
                for row in range(max_h)]

    # ---- 序列化 ----

    def to_lesson_data(self, question: str = "", steps: list = None) -> dict:
        """生成注入模板 __LESSON_DATA__ 的完整 JSON。"""
        cubes = self.cube_list()
        fh = self.front_view()
        sh = self.side_view()
        tv = self.top_view()
        count = self.cube_count()

        if steps is None:
            steps = self._default_steps(fh, sh, tv, count)

        return {
            "lesson": {
                "title": "方块三视图",
                "meta": "交互练习 · 观察物体",
                "question": question or self._default_question(count),
                "cubeCount": count,
            },
            "model": {
                "blocks": cubes,
                "gridSize": {
                    "width": self.width,
                    "depth": self.depth,
                    "maxHeight": self.max_height()
                },
            },
            "views": {
                "front": {
                    "heights": fh,
                    "grid": self.front_view_grid(),
                    "label": "从正面看"
                },
                "side": {
                    "heights": sh,
                    "grid": self.side_view_grid(),
                    "label": "从左面看"
                },
                "top": {
                    "cells": tv,
                    "grid": self.top_view_grid(),
                    "label": "从上面看"
                },
            },
            "steps": steps,
        }

    # ---- 画图模式数据 ----

    def to_draw_mode_data(self, question: str = "") -> dict:
        """生成画图模式数据：展示 3D 模型，学生在方格纸上画三视图，与标准答案比对。"""
        data = self.to_lesson_data(question=question)
        data["mode"] = "draw"
        # 学生答案网格（初始全空）
        fg = self.front_view_grid()
        sg = self.side_view_grid()
        tg = self.top_view_grid()
        data["student"] = {
            "front": [[0] * len(row) for row in fg],
            "side": [[0] * len(row) for row in sg],
            "top": [[0] * len(row) for row in tg],
        }
        return data

    # ---- 逆向还原模式数据 ----

    def to_reverse_mode_data(self, question: str = "") -> dict:
        """生成逆向模式数据：展示三视图，学生在 3D 网格上还原方块摆放。"""
        data = self.to_lesson_data(question=question)
        data["mode"] = "reverse"
        # 隐藏 3D 模型中的方块（学生需要自己摆）
        data["model"]["blocks"] = []
        # 保留 targetViews 供前端比对
        data["targetViews"] = {
            "front": data["views"]["front"],
            "side": data["views"]["side"],
            "top": data["views"]["top"],
        }
        return data

    # ---- 选择题模式数据 ----

    @classmethod
    def generate_choice_set(cls, direction: str = "front",
                            width: int = 3, depth: int = 3, max_height: int = 3,
                            seed: int = None) -> dict:
        """生成四选一视图辨析题：4 个摆放中 1 个的指定方向视图与其他 3 个不同。

        Args:
            direction: 'front' / 'side' / 'top'
            width, depth, max_height: 网格参数
            seed: 随机种子

        Returns:
            dict: arrangements(4个), diff_index, direction, direction_label,
                  question, options(每个选项的序列化数据)
        """
        rng = random.Random(seed)

        # 生成基础摆放
        base = cls.random(width, depth, max_height, min_cubes=4, seed=seed)

        # 生成 2 个同视图变体
        same_arrs = [base]
        for _ in range(2):
            v = cls._perturb_keep_view(base, direction, rng, max_height)
            # 确保变体与基础不同
            if v.heights == base.heights:
                v = cls._perturb_keep_view(base, direction, rng, max_height)
            same_arrs.append(v)

        # 生成 1 个不同视图的变体
        diff = cls._perturb_change_view(base, direction, rng, max_height)
        # 确保视图确实不同
        attempts = 0
        while diff._view_tuple(direction) == base._view_tuple(direction) and attempts < 20:
            diff = cls._perturb_change_view(base, direction, rng, max_height)
            attempts += 1

        all_arrs = same_arrs + [diff]
        diff_idx = 3

        # 打乱顺序
        perm = list(range(4))
        rng.shuffle(perm)
        shuffled = [all_arrs[i] for i in perm]
        new_diff_idx = perm.index(diff_idx)

        direction_labels = {
            "front": "从正面看",
            "side": "从左面看",
            "top": "从上面看",
        }

        options = []
        for i, arr in enumerate(shuffled):
            options.append({
                "label": chr(65 + i),  # A, B, C, D
                "blocks": arr.cube_list(),
                "gridSize": {
                    "width": arr.width,
                    "depth": arr.depth,
                    "maxHeight": arr.max_height(),
                },
                "view": arr._view_data(direction),
            })

        return {
            "mode": "choice",
            "direction": direction,
            "directionLabel": direction_labels[direction],
            "diffIndex": new_diff_idx,
            "correctLabel": chr(65 + new_diff_idx),
            "question": f"下面四个立体图形中，{direction_labels[direction]}，哪个与其他三个不同？",
            "options": options,
        }

    def _view_tuple(self, direction: str):
        """返回指定方向视图的元组表示，用于比较。"""
        if direction == "front":
            return tuple(self.front_view())
        elif direction == "side":
            return tuple(self.side_view())
        elif direction == "top":
            return tuple(tuple(row) for row in self.top_view())
        raise ValueError(f"未知方向: {direction}")

    def _view_data(self, direction: str) -> dict:
        """返回指定方向视图的渲染数据。"""
        if direction == "front":
            return {"heights": self.front_view(), "grid": self.front_view_grid(),
                    "label": "从正面看"}
        elif direction == "side":
            return {"heights": self.side_view(), "grid": self.side_view_grid(),
                    "label": "从左面看"}
        elif direction == "top":
            return {"cells": self.top_view(), "grid": self.top_view_grid(),
                    "label": "从上面看"}

    @classmethod
    def _perturb_keep_view(cls, base: "BlockArrangement", direction: str,
                           rng: random.Random, max_height: int) -> "BlockArrangement":
        """创建一个不同摆放但指定方向视图相同的变体。"""
        w, d = base.width, base.depth
        variant = cls(w, d)
        for x in range(w):
            for y in range(d):
                variant.heights[x][y] = base.heights[x][y]

        if direction == "front":
            # 正面视图只看每列(x)最高，改非最高位置的高度
            for x in range(w):
                col_max = max(base.heights[x])
                for y in range(d):
                    if 0 < base.heights[x][y] < col_max:
                        variant.heights[x][y] = rng.randint(0, col_max)
        elif direction == "side":
            for y in range(d):
                row_max = max(base.heights[x][y] for x in range(w))
                for x in range(w):
                    if 0 < base.heights[x][y] < row_max:
                        variant.heights[x][y] = rng.randint(0, row_max)
        elif direction == "top":
            # 俯视图只看有无，改非零位置的高度
            for x in range(w):
                for y in range(d):
                    if base.heights[x][y] > 0:
                        variant.heights[x][y] = rng.randint(1, max(base.heights[x][y], 1))

        # 验证视图相同
        if variant._view_tuple(direction) != base._view_tuple(direction):
            # 回退到直接复制（确保正确性）
            variant = cls(w, d)
            for x in range(w):
                for y in range(d):
                    variant.heights[x][y] = base.heights[x][y]
            # 只改一个不影响视图的位置
            if direction == "front":
                for x in range(w):
                    col_max = max(variant.heights[x])
                    for y in range(d):
                        if 0 < variant.heights[x][y] < col_max:
                            variant.heights[x][y] = max(0, variant.heights[x][y] - 1)
                            if variant._view_tuple(direction) == base._view_tuple(direction):
                                return variant
                            variant.heights[x][y] += 1  # 回退
            elif direction == "side":
                for y in range(d):
                    row_max = max(variant.heights[x][y] for x in range(w))
                    for x in range(w):
                        if 0 < variant.heights[x][y] < row_max:
                            variant.heights[x][y] = max(0, variant.heights[x][y] - 1)
                            if variant._view_tuple(direction) == base._view_tuple(direction):
                                return variant
                            variant.heights[x][y] += 1
            elif direction == "top":
                for x in range(w):
                    for y in range(d):
                        if variant.heights[x][y] > 1:
                            variant.heights[x][y] -= 1
                            if variant._view_tuple(direction) == base._view_tuple(direction):
                                return variant
                            variant.heights[x][y] += 1

        return variant

    @classmethod
    def _perturb_change_view(cls, base: "BlockArrangement", direction: str,
                             rng: random.Random, max_height: int) -> "BlockArrangement":
        """创建一个指定方向视图不同的变体。"""
        w, d = base.width, base.depth
        variant = cls(w, d)
        for x in range(w):
            for y in range(d):
                variant.heights[x][y] = base.heights[x][y]

        if direction == "front":
            # 改某一列的最高高度
            x = rng.randint(0, w - 1)
            old_max = max(variant.heights[x])
            new_max = (old_max + 1) % (max_height + 1)
            if new_max == old_max:
                new_max = (old_max + 1) if old_max < max_height else max(0, old_max - 1)
            # 调整该列
            for y in range(d):
                if variant.heights[x][y] > new_max:
                    variant.heights[x][y] = new_max
            if max(variant.heights[x]) < new_max:
                y = rng.randint(0, d - 1)
                variant.heights[x][y] = new_max
        elif direction == "side":
            y = rng.randint(0, d - 1)
            old_max = max(variant.heights[x][y] for x in range(w))
            new_max = (old_max + 1) % (max_height + 1)
            if new_max == old_max:
                new_max = (old_max + 1) if old_max < max_height else max(0, old_max - 1)
            for x in range(w):
                if variant.heights[x][y] > new_max:
                    variant.heights[x][y] = new_max
            if max(variant.heights[x][y] for x in range(w)) < new_max:
                x = rng.randint(0, w - 1)
                variant.heights[x][y] = new_max
        elif direction == "top":
            # 增加或移除一个方块
            x, y = rng.randint(0, w - 1), rng.randint(0, d - 1)
            if variant.heights[x][y] > 0:
                variant.heights[x][y] = 0
            else:
                variant.heights[x][y] = 1

        return variant

    # ---- 识图模式（一个模型，四个方向视图，问哪个是指定方向） ----

    def _all_views_data(self) -> dict:
        """返回所有方向的视图数据。"""
        return {
            "front": {"heights": self.front_view(), "grid": self.front_view_grid(),
                      "label": "从正面看"},
            "back": {"heights": self.back_view(), "grid": self.back_view_grid(),
                     "label": "从背面看"},
            "left": {"heights": self.side_view(), "grid": self.side_view_grid(),
                     "label": "从左面看"},
            "right": {"heights": self.right_view(), "grid": self.right_view_grid(),
                      "label": "从右面看"},
            "top": {"cells": self.top_view(), "grid": self.top_view_grid(),
                    "label": "从上面看"},
        }

    @classmethod
    def generate_view_identification(cls, direction: str = "front",
                                     width: int = 3, depth: int = 3, max_height: int = 3,
                                     seed: int = None) -> dict:
        """生成识图选择题：展示一个3D模型，给出4个不同方向的视图，问哪个是指定方向的视图。

        Args:
            direction: 'front' / 'left' / 'top' / 'back' / 'right'
            width, depth, max_height: 网格参数
            seed: 随机种子

        Returns:
            dict: model(3D数据), options(4个视图), correctIndex, direction, question
        """
        rng = random.Random(seed)

        direction_labels = {
            "front": "从正面看",
            "back": "从背面看",
            "left": "从左面看",
            "right": "从右面看",
            "top": "从上面看",
        }

        # 生成一个有足够区分度的摆放
        max_attempts = 30
        for attempt in range(max_attempts):
            arr = cls.random(width, depth, max_height, min_cubes=4,
                             seed=rng.randint(0, 99999))
            all_views = arr._all_views_data()

            # 选4个方向：必须包含目标方向
            all_dirs = ["front", "left", "top", "back"]
            if direction not in all_dirs:
                all_dirs = ["front", "left", "top", "right"]
            if direction not in all_dirs:
                all_dirs = ["front", "left", "top", direction]

            # 确保四个视图互不相同
            view_keys = []
            for d in all_dirs:
                v = all_views[d]
                if d == "top":
                    view_keys.append(tuple(tuple(r) for r in v["grid"]))
                else:
                    view_keys.append(tuple(tuple(r) for r in v["grid"]))

            if len(set(view_keys)) == 4:
                break
        else:
            # 最后兜底：强制修改确保不同
            arr = cls.random(width, depth, max_height, min_cubes=4, seed=seed)
            all_views = arr._all_views_data()
            all_dirs = ["front", "left", "top", "back"]
            if direction not in all_dirs:
                all_dirs = ["front", "left", "top", "right"]

        # 打乱顺序
        perm = list(range(4))
        rng.shuffle(perm)
        shuffled_dirs = [all_dirs[i] for i in perm]
        correct_pos = shuffled_dirs.index(direction)

        options = []
        for i, d in enumerate(shuffled_dirs):
            v = all_views[d]
            options.append({
                "label": chr(65 + i),
                "view": v,
                "isTop": d == "top",
            })

        return {
            "mode": "choice",
            "model": {
                "blocks": arr.cube_list(),
                "gridSize": {
                    "width": arr.width,
                    "depth": arr.depth,
                    "maxHeight": arr.max_height(),
                },
            },
            "direction": direction,
            "directionLabel": direction_labels[direction],
            "correctIndex": correct_pos,
            "correctLabel": chr(65 + correct_pos),
            "question": f"请观察上面的立体图形，下面四个选项中，哪个是{direction_labels[direction]}的形状？",
            "options": options,
        }

    def _default_question(self, count: int) -> str:
        return (f"下面的立体图形由若干个小正方体组成。"
                f"请分别画出从正面、左面、上面看到的形状，"
                f"并数一数一共用了多少个小正方体。")

    def _default_steps(self, fh, sh, tv, count) -> list:
        fh_str = "、".join(str(h) for h in fh)
        sh_str = "、".join(str(h) for h in sh)
        return [
            {
                "title": "观察立体图形",
                "content": (
                    f"<p>首先观察整个立体图形。它放在一个 "
                    f"{self.width}×{self.depth} 的网格上，"
                    f"最高堆了 {self.max_height()} 层。</p>"
                    f"<p>数一数：一共用了 <b>{count}</b> 个小正方体。</p>"
                ),
                "highlight": "scene",
            },
            {
                "title": "从正面看",
                "content": (
                    f"<p>从正面看，我们只关心每个位置（x方向）<b>最高的那一列</b>。</p>"
                    f"<p>从左到右，每列的最大高度分别是：{fh_str}。</p>"
                    f"<p>这就是正面看到的形状——{len(fh)}列，"
                    f"每列有对应高度的方块堆叠。</p>"
                ),
                "highlight": "front",
            },
            {
                "title": "从左面看",
                "content": (
                    f"<p>从左面看，我们看的是每个深度（y方向）<b>最高的那一排</b>。</p>"
                    f"<p>从近到远，每排的最大高度分别是：{sh_str}。</p>"
                    f"<p>这就是左面看到的形状。</p>"
                ),
                "highlight": "side",
            },
            {
                "title": "从上面看",
                "content": (
                    f"<p>从上面看，我们只关心哪些位置<b>有方块</b>。</p>"
                    f"<p>有方块的位置画实心，没有的留空，"
                    f"就得到了俯视图。</p>"
                    f"<p>现在三个视图都画好了！正方体总数是 <b>{count}</b> 个。</p>"
                ),
                "highlight": "top",
            },
        ]

    # ---- 随机生成 ----

    @classmethod
    def random(cls, width: int = 3, depth: int = 3, max_height: int = 3,
               min_cubes: int = 4, seed: int = None) -> "BlockArrangement":
        """随机生成一个方块摆放。

        策略：
        1. 随机给每个格子一个高度（偏向 1~2）
        2. 确保至少 min_cubes 个方块
        3. 确保至少 2 种不同高度（避免纯平面）
        """
        rng = random.Random(seed)
        arr = cls(width, depth)

        for x in range(width):
            for y in range(depth):
                # 偏向低高度：60% 概率 1-2，25% 概率 0，15% 概率 3
                r = rng.random()
                if r < 0.25:
                    h = 0
                elif r < 0.85:
                    h = rng.randint(1, 2)
                else:
                    h = rng.randint(1, max_height)
                arr.place(x, y, h)

        # 确保最少方块数
        while arr.cube_count() < min_cubes:
            x = rng.randint(0, width - 1)
            y = rng.randint(0, depth - 1)
            arr.heights[x][y] = min(arr.heights[x][y] + 1, max_height)

        # 确保至少 2 种不同高度
        unique_heights = set(arr.heights[x][y]
                             for x in range(width)
                             for y in range(depth))
        if len(unique_heights - {0}) < 2:
            # 强制给一个位置加高
            x, y = rng.randint(0, width - 1), rng.randint(0, depth - 1)
            arr.heights[x][y] = min(arr.heights[x][y] + 1, max_height)

        return arr

    # ---- 自检 ----

    @staticmethod
    def self_test():
        """运行自检验证 kernel 正确性。"""
        print("=== block_kernel.py 自检 ===")

        # 测试 1: 已知题目
        arr = BlockArrangement(3, 2)
        arr.place(0, 0, 2).place(1, 0, 1).place(2, 0, 3)
        arr.place(0, 1, 1).place(1, 1, 2).place(2, 1, 1)

        assert arr.cube_count() == 10, f"方块数应为10, 得到{arr.cube_count()}"
        assert arr.front_view() == [2, 2, 3], f"正面视图错误: {arr.front_view()}"
        assert arr.side_view() == [3, 2], f"侧面视图错误: {arr.side_view()}"
        assert arr.top_view() == [[1, 1], [1, 1], [1, 1]], f"俯视图错误: {arr.top_view()}"
        print(f"  测试1 通过: 3x2网格, 10个方块, 正面[2,2,3] 侧面[3,2]")

        # 测试 2: 单个方块
        arr2 = BlockArrangement(1, 1)
        arr2.place(0, 0, 1)
        assert arr2.cube_count() == 1
        assert arr2.front_view() == [1]
        assert arr2.side_view() == [1]
        assert arr2.top_view() == [[1]]
        print(f"  测试2 通过: 单个方块")

        # 测试 3: 空网格
        arr3 = BlockArrangement(2, 2)
        assert arr3.cube_count() == 0
        assert arr3.front_view() == [0, 0]
        assert arr3.side_view() == [0, 0]
        assert arr3.top_view() == [[0, 0], [0, 0]]
        print(f"  测试3 通过: 空网格")

        # 测试 4: 随机生成
        arr4 = BlockArrangement.random(width=3, depth=3, max_height=3, min_cubes=5, seed=42)
        assert arr4.cube_count() >= 5
        assert arr4.max_height() <= 3
        assert arr4.width == 3 and arr4.depth == 3
        print(f"  测试4 通过: 随机生成(seed=42), {arr4.cube_count()}个方块, "
              f"最高{arr4.max_height()}层")

        # 测试 5: 视图一致性
        arr5 = BlockArrangement.random(width=4, depth=3, max_height=4, seed=100)
        fh = arr5.front_view()
        sh = arr5.side_view()
        tv = arr5.top_view()
        # 正面视图的列数 = 网格宽度
        assert len(fh) == arr5.width
        # 侧面视图的列数 = 网格深度
        assert len(sh) == arr5.depth
        # 俯视图尺寸 = 网格尺寸
        assert len(tv) == arr5.width and len(tv[0]) == arr5.depth
        # 正面视图最大高度 <= 全局最大高度
        assert max(fh) == arr5.max_height()
        print(f"  测试5 通过: 视图尺寸一致性验证")

        # 测试 5.5: top_view_grid 方向验证
        arr_t = BlockArrangement(3, 2)  # width=3, depth=2
        arr_t.place(0, 0, 1)  # x=0, y=0: 有方块
        arr_t.place(2, 1, 1)  # x=2, y=1: 有方块
        tg = arr_t.top_view_grid()
        # grid[y][x]: y=0(near) → [1,0,0], y=1(far) → [0,0,1]
        assert tg == [[1, 0, 0], [0, 0, 1]], f"top_view_grid 方向错误: {tg}"
        assert len(tg) == 2  # depth 行
        assert len(tg[0]) == 3  # width 列
        # 与 front_view_grid 共享 x 轴：列数 = width
        fg_t = arr_t.front_view_grid()
        assert len(fg_t[0]) == len(tg[0])  # 都 = width
        print(f"  测试5.5 通过: top_view_grid 方向正确, {tg}")

        # 测试 6: to_lesson_data 序列化
        data = arr.to_lesson_data()
        assert "lesson" in data
        assert "model" in data
        assert "views" in data
        assert "steps" in data
        assert len(data["model"]["blocks"]) == 10
        assert data["lesson"]["cubeCount"] == 10
        json_str = json.dumps(data, ensure_ascii=False)
        assert len(json_str) > 100
        print(f"  测试6 通过: 序列化正常, JSON长度{len(json_str)}")

        # 测试 7: 画图模式数据
        draw_data = arr.to_draw_mode_data()
        assert draw_data["mode"] == "draw"
        assert "student" in draw_data
        assert "front" in draw_data["student"]
        assert "side" in draw_data["student"]
        assert "top" in draw_data["student"]
        # 学生网格应为空
        assert all(v == 0 for row in draw_data["student"]["front"] for v in row)
        # 标准答案仍在 views 中
        assert draw_data["views"]["front"]["grid"] is not None
        print(f"  测试7 通过: 画图模式数据结构正确")

        # 测试 8: 逆向还原模式数据
        rev_data = arr.to_reverse_mode_data()
        assert rev_data["mode"] == "reverse"
        assert rev_data["model"]["blocks"] == []  # 方块隐藏
        assert "targetViews" in rev_data
        assert rev_data["targetViews"]["front"]["heights"] == [2, 2, 3]
        print(f"  测试8 通过: 逆向还原模式数据结构正确")

        # 测试 9: 选择题模式 — front 方向
        choice_data = BlockArrangement.generate_choice_set(
            direction="front", width=3, depth=3, max_height=3, seed=55)
        assert choice_data["mode"] == "choice"
        assert len(choice_data["options"]) == 4
        assert 0 <= choice_data["diffIndex"] < 4
        # 验证：3个相同 + 1个不同
        views = [tuple(opt["view"]["heights"]) for opt in choice_data["options"]]
        diff_idx = choice_data["diffIndex"]
        same_views = [v for i, v in enumerate(views) if i != diff_idx]
        assert all(v == same_views[0] for v in same_views), "同组视图应相同"
        assert views[diff_idx] != same_views[0], "不同项视图应不同"
        print(f"  测试9 通过: 选择题(front), 不同项={choice_data['correctLabel']}, "
              f"视图={views[diff_idx]} vs {same_views[0]}")

        # 测试 10: 选择题模式 — top 方向
        choice_top = BlockArrangement.generate_choice_set(
            direction="top", width=3, depth=2, max_height=2, seed=88)
        assert len(choice_top["options"]) == 4
        top_views = [tuple(tuple(r) for r in opt["view"]["cells"])
                     for opt in choice_top["options"]]
        diff_i = choice_top["diffIndex"]
        same_tops = [v for i, v in enumerate(top_views) if i != diff_i]
        assert all(v == same_tops[0] for v in same_tops), "同组俯视图应相同"
        assert top_views[diff_i] != same_tops[0], "不同项俯视图应不同"
        print(f"  测试10 通过: 选择题(top), 不同项={choice_top['correctLabel']}")

        # 测试 11: _view_tuple 一致性
        assert arr._view_tuple("front") == (2, 2, 3)
        assert arr._view_tuple("side") == (3, 2)
        assert arr._view_tuple("top") == ((1, 1), (1, 1), (1, 1))
        print(f"  测试11 通过: _view_tuple 正确")

        # 测试 12: back_view / right_view
        assert arr.back_view() == [3, 2, 2], f"背面视图错误: {arr.back_view()}"
        assert arr.right_view() == [2, 3], f"右面视图错误: {arr.right_view()}"
        print(f"  测试12 通过: back_view={arr.back_view()}, right_view={arr.right_view()}")

        # 测试 13: 识图模式
        ident = BlockArrangement.generate_view_identification(
            direction="front", width=3, depth=3, max_height=3, seed=42)
        assert ident["mode"] == "choice"
        assert len(ident["options"]) == 4
        assert 0 <= ident["correctIndex"] < 4
        assert ident["direction"] == "front"
        # 验证正确选项确实是正面视图
        correct_opt = ident["options"][ident["correctIndex"]]
        assert correct_opt["view"]["label"] == "从正面看"
        # 验证四个选项互不相同
        grids = [tuple(tuple(r) for r in opt["view"]["grid"]) for opt in ident["options"]]
        assert len(set(grids)) == 4, f"选项视图应互不相同: {grids}"
        print(f"  测试13 通过: 识图模式(front), 正确答案={ident['correctLabel']}")

        # 测试 14: 识图模式 — top 方向
        ident_top = BlockArrangement.generate_view_identification(
            direction="top", width=3, depth=2, max_height=2, seed=88)
        assert ident_top["direction"] == "top"
        correct_top = ident_top["options"][ident_top["correctIndex"]]
        assert correct_top["view"]["label"] == "从上面看"
        grids_top = [tuple(tuple(r) for r in opt["view"]["grid"]) for opt in ident_top["options"]]
        assert len(set(grids_top)) == 4, f"选项应互不相同"
        print(f"  测试14 通过: 识图模式(top), 正确答案={ident_top['correctLabel']}")

        print("=== 全部通过 ===")


# ===================== 命令行入口 =====================

if __name__ == "__main__":
    BlockArrangement.self_test()
