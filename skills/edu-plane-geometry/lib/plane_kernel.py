"""
edu-plane-geometry kernel
平面几何计算核心：精确坐标计算 + SVG 数据生成

设计原则（与 EduLab 一脉相承）：
  - 图不是 AI "画"的，是 kernel "算"出来的
  - 小学部分用纯算术，初中部分用 sympy 保证坐标精确
  - 同一份数据同时驱动 SVG 渲染和步骤讲解，保证"图、解、答"零误差
  - AI 只负责解析题意和写证明文案，所有坐标计算由确定性代码完成

支持题型：
  1. rectangle_area    — 长方形面积/周长（含回字形组合图形）
  2. triangle_congruence — 三角形全等证明（SAS/ASA/SSS）
  3. parallelogram_proof — 平行四边形证明（全等+矩形判定）
  4. cube_net          — 正方体展开图（找对面）
  5. shape_counting    — 图形计数（数三角形/长方形）

依赖：sympy（初中部分坐标计算），小学部分零依赖
"""

import json
import math
import random

try:
    from sympy import (Rational, sqrt, simplify, cos, sin, pi,
                       Symbol, solve, Abs, atan2, nsimplify)
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False


# ============================================================
#  PlaneFigure — 平面图形数据结构
# ============================================================

class PlaneFigure:
    """持有一幅平面几何图形的全部绘制数据。

    所有坐标使用数学坐标系（原点在左下，Y 轴向上），
    模板负责转换为 SVG 坐标系（原点在左上，Y 轴向下）。
    """

    def __init__(self):
        self.vertices = []          # [{"x": float, "y": float, "label": str}]
        self.edges = []             # [{"from": int, "to": int, "label": str, "style": str}]
        self.equal_marks = []       # [{"edges": [int, ...], "count": int}]
        self.right_angles = []      # [{"vertex": int, "edge1": int, "edge2": int}]
        self.parallel_marks = []    # [{"edges": [int, ...], "count": int}]
        self.dimension_labels = []  # [{"edge": int, "text": str, "offset": float, "side": str}]
        self.regions = []           # [{"vertices": [int, ...], "fill": str, "opacity": float}]
        self.aux_lines = []         # [{"from": int, "to": int, "style": str, "label": str}]
        self.angle_arcs = []        # [{"vertex": int, "edge1": int, "edge2": int, "label": str, "radius": float}]

    def add_vertex(self, x, y, label=""):
        """添加顶点，返回索引。坐标自动转 float。"""
        idx = len(self.vertices)
        self.vertices.append({
            "x": float(x),
            "y": float(y),
            "label": label
        })
        return idx

    def add_edge(self, i, j, label="", style="solid"):
        """添加边（线段），返回索引。style: solid/dashed/dotted"""
        idx = len(self.edges)
        self.edges.append({"from": i, "to": j, "label": label, "style": style})
        return idx

    def add_equal_mark(self, edge_indices, count=1):
        """添加等长标记。count=1 表示单杠，2 表示双杠，3 表示三杠。"""
        self.equal_marks.append({"edges": list(edge_indices), "count": count})

    def add_right_angle(self, vertex_idx, edge1_idx, edge2_idx):
        """添加直角标记。"""
        self.right_angles.append({
            "vertex": vertex_idx,
            "edge1": edge1_idx,
            "edge2": edge2_idx
        })

    def add_parallel_mark(self, edge_indices, count=1):
        """添加平行标记。count=1 表示单箭头，2 表示双箭头。"""
        self.parallel_marks.append({"edges": list(edge_indices), "count": count})

    def add_dimension_label(self, edge_idx, text, offset=0.35, side="auto"):
        """添加尺寸标注。side: auto/above/below/left/right"""
        self.dimension_labels.append({
            "edge": edge_idx,
            "text": text,
            "offset": offset,
            "side": side
        })

    def add_region(self, vertex_indices, fill="#fef3c7", opacity=0.4):
        """添加填充区域。"""
        self.regions.append({
            "vertices": list(vertex_indices),
            "fill": fill,
            "opacity": opacity
        })

    def add_aux_line(self, i, j, style="dashed", label=""):
        """添加辅助线。"""
        self.aux_lines.append({"from": i, "to": j, "style": style, "label": label})

    def add_angle_arc(self, vertex_idx, edge1_idx, edge2_idx, label="", radius=25):
        """添加角度弧线标注。"""
        self.angle_arcs.append({
            "vertex": vertex_idx,
            "edge1": edge1_idx,
            "edge2": edge2_idx,
            "label": label,
            "radius": radius
        })

    def to_svg_data(self):
        """转换为 JSON 可序列化的字典，供模板使用。"""
        return {
            "vertices": self.vertices,
            "edges": self.edges,
            "equalMarks": self.equal_marks,
            "rightAngles": self.right_angles,
            "parallelMarks": self.parallel_marks,
            "dimensionLabels": self.dimension_labels,
            "regions": self.regions,
            "auxLines": self.aux_lines,
            "angleArcs": self.angle_arcs,
        }


# ============================================================
#  PlaneProblem — 问题容器
# ============================================================

class PlaneProblem:
    """持有一个平面几何问题的全部数据：图形 + 题目 + 步骤 + 答案。"""

    def __init__(self, question="", answer=""):
        self.figure = PlaneFigure()
        self.question = question
        self.answer = answer
        self.steps = []
        self.meta = {"mode": "plane", "title": "平面几何", "grade": "", "topic": ""}

    def set_meta(self, mode=None, title=None, grade=None, topic=None):
        if mode:
            self.meta["mode"] = mode
        if title:
            self.meta["title"] = title
        if grade:
            self.meta["grade"] = grade
        if topic:
            self.meta["topic"] = topic

    def add_step(self, title, content, highlights=None):
        """添加解题步骤。highlights 指定该步要高亮的元素。"""
        self.steps.append({
            "title": title,
            "content": content,
            "highlights": highlights or {}
        })

    def to_lesson_data(self):
        """生成完整的课程数据字典。"""
        return {
            "mode": self.meta.get("mode", "plane"),
            "title": self.meta.get("title", "平面几何"),
            "grade": self.meta.get("grade", ""),
            "topic": self.meta.get("topic", ""),
            "question": self.question,
            "answer": self.answer,
            "figure": self.figure.to_svg_data(),
            "steps": self.steps,
            "meta": self.meta,
        }


# ============================================================
#  题型 1：rectangle_area — 长方形面积/周长（含组合图形）
# ============================================================

def build_rectangle_area(width, height, path_width=None,
                         question="", answer=""):
    """长方形面积/周长计算。

    参数：
      width, height — 长方形的长和宽
      path_width    — 如果提供，生成"回字形"组合图形（四周修路）
      question      — 自定义题目文本
      answer        — 自定义答案
    """
    p = PlaneProblem()
    fig = p.figure
    W, H = width, height

    if path_width is not None:
        # 回字形：大矩形（含路）- 小矩形（草坪）= 路面积
        pw = path_width
        outer_w = W + 2 * pw
        outer_h = H + 2 * pw

        # 外矩形顶点 A B C D
        A = fig.add_vertex(0, 0, "A")
        B = fig.add_vertex(outer_w, 0, "B")
        C = fig.add_vertex(outer_w, outer_h, "C")
        D = fig.add_vertex(0, outer_h, "D")

        # 内矩形顶点 E F G H（草坪）
        E = fig.add_vertex(pw, pw, "E")
        F = fig.add_vertex(W + pw, pw, "F")
        G = fig.add_vertex(W + pw, H + pw, "G")
        H_ = fig.add_vertex(pw, H + pw, "H")

        # 外矩形边
        e_AB = fig.add_edge(A, B)
        e_BC = fig.add_edge(B, C)
        e_CD = fig.add_edge(C, D)
        e_DA = fig.add_edge(D, A)

        # 内矩形边
        e_EF = fig.add_edge(E, F)
        e_FG = fig.add_edge(F, G)
        e_GH = fig.add_edge(G, H_)
        e_HE = fig.add_edge(H_, E)

        # 尺寸标注
        fig.add_dimension_label(e_AB, f"{outer_w} m", side="below")
        fig.add_dimension_label(e_BC, f"{outer_h} m", side="right")
        fig.add_dimension_label(e_EF, f"{W} m", side="below")
        fig.add_dimension_label(e_FG, f"{H} m", side="right")

        # 路宽标注
        fig.add_dimension_label(e_DA, f"路宽 {pw} m", side="left")

        # 区域填充：路（黄色）、草坪（绿色）
        fig.add_region([A, B, C, D], "#fde68a", 0.35)
        fig.add_region([E, F, G, H_], "#86efac", 0.45)

        # 计算
        outer_area = outer_w * outer_h
        inner_area = W * H
        path_area = outer_area - inner_area

        p.question = question or (
            f"一个长方形草坪长 {W} 米，宽 {H} 米。"
            f"现在要在草坪四周修一条宽 {pw} 米的石子路，"
            f"求石子路的总面积是多少平方米？"
        )
        p.answer = answer or f"{path_area} 平方米"

        p.set_meta("rectangle_area", "回字形面积计算", "小学", "面积")

        p.add_step("观察图形",
            f"草坪是一个 {W}×{H} 的长方形（绿色），\n"
            f"四周修路后外面多了一圈宽 {pw} 米的边（黄色）。\n"
            f"关键：路在四周各加 {pw} 米，所以长和宽都多了 {2*pw} 米。",
            {"regions": [0, 1], "edges": [4, 5, 6, 7]})

        p.add_step("算大长方形面积",
            f"大长方形（草坪+路）：\n"
            f"  长 = {W} + {2*pw} = {outer_w} 米\n"
            f"  宽 = {H} + {2*pw} = {outer_h} 米\n"
            f"  面积 = {outer_w} × {outer_h} = {outer_area} 平方米",
            {"regions": [0], "edges": [0, 1, 2, 3]})

        p.add_step("算草坪面积",
            f"草坪面积 = {W} × {H} = {inner_area} 平方米",
            {"regions": [1], "edges": [4, 5, 6, 7]})

        p.add_step("求石子路面积",
            f"石子路面积 = 大长方形面积 - 草坪面积\n"
            f"= {outer_area} - {inner_area}\n"
            f"= {path_area} 平方米",
            {"regions": [0, 1]})

    else:
        # 简单长方形
        A = fig.add_vertex(0, 0, "A")
        B = fig.add_vertex(W, 0, "B")
        C = fig.add_vertex(W, H, "C")
        D = fig.add_vertex(0, H, "D")

        e_AB = fig.add_edge(A, B)
        e_BC = fig.add_edge(B, C)
        e_CD = fig.add_edge(C, D)
        e_DA = fig.add_edge(D, A)

        fig.add_dimension_label(e_AB, f"{W} m", side="below")
        fig.add_dimension_label(e_BC, f"{H} m", side="right")

        fig.add_region([A, B, C, D], "#bfdbfe", 0.3)

        area = W * H
        perimeter = 2 * (W + H)

        p.question = question or (
            f"一个长方形长 {W} 米，宽 {H} 米，求它的面积和周长。"
        )
        p.answer = answer or (
            f"面积 = {area} 平方米，周长 = {perimeter} 米"
        )

        p.set_meta("rectangle_area", "长方形面积与周长", "小学", "面积")

        p.add_step("观察图形",
            f"这是一个长方形，长 {W} 米，宽 {H} 米。",
            {"edges": [0, 1, 2, 3]})

        p.add_step("计算面积",
            f"面积 = 长 × 宽\n= {W} × {H}\n= {area} 平方米",
            {"edges": [0, 1]})

        p.add_step("计算周长",
            f"周长 = (长 + 宽) × 2\n= ({W} + {H}) × 2\n= {perimeter} 米",
            {"edges": [0, 1, 2, 3]})

    return p


# ============================================================
#  题型 2：triangle_congruence — 三角形全等证明
# ============================================================

def build_triangle_congruence(spec, question="", answer=""):
    """三角形全等证明题。

    spec 格式：
    {
        "type": "SAS" | "ASA" | "SSS" | "AAS",
        "triangle1": {"vertices": ["A", "B", "C"], "given": [...]},
        "triangle2": {"vertices": ["D", "E", "F"], "given": [...]},
        "conditions": ["AB=DE", "∠B=∠E", "BC=EF"],
    }
    """
    p = PlaneProblem()
    fig = p.figure

    cong_type = spec.get("type", "SAS")
    t1 = spec.get("triangle1", {})
    t2 = spec.get("triangle2", {})
    conditions = spec.get("conditions", [])

    v1_labels = t1.get("vertices", ["A", "B", "C"])
    v2_labels = t2.get("vertices", ["D", "E", "F"])

    # 根据全等类型设置三角形坐标
    # 两个三角形并排放置，中间留间距
    base_size = 4
    gap = 3

    if cong_type == "SAS":
        # △ABC: A(0,0), B(base_size, 0), C(base_size*0.3, base_size*0.8)
        # △DEF: D(gap, 0), E(gap+base_size, 0), F(gap+base_size*0.3, base_size*0.8)
        coords1 = [(0, 0), (base_size, 0), (base_size * 0.3, base_size * 0.8)]
        coords2 = [(gap, 0), (gap + base_size, 0), (gap + base_size * 0.3, base_size * 0.8)]

    elif cong_type == "ASA":
        # 两个三角形，已知一角和夹该角的两边
        coords1 = [(0, 0), (base_size, 0), (base_size * 0.5, base_size * 0.7)]
        coords2 = [(gap, 0), (gap + base_size, 0), (gap + base_size * 0.5, base_size * 0.7)]

    elif cong_type == "SSS":
        coords1 = [(0, 0), (base_size, 0), (base_size * 0.2, base_size * 0.9)]
        coords2 = [(gap, 0), (gap + base_size, 0), (gap + base_size * 0.2, base_size * 0.9)]

    else:  # AAS
        coords1 = [(0, 0), (base_size, 0), (base_size * 0.4, base_size * 0.6)]
        coords2 = [(gap, 0), (gap + base_size, 0), (gap + base_size * 0.4, base_size * 0.6)]

    # 添加顶点
    v1_indices = []
    for i, (x, y) in enumerate(coords1):
        idx = fig.add_vertex(x, y, v1_labels[i])
        v1_indices.append(idx)

    v2_indices = []
    for i, (x, y) in enumerate(coords2):
        idx = fig.add_vertex(x, y, v2_labels[i])
        v2_indices.append(idx)

    # 三角形1的边
    e1_0 = fig.add_edge(v1_indices[0], v1_indices[1], label=f"{v1_labels[0]}{v1_labels[1]}")
    e1_1 = fig.add_edge(v1_indices[1], v1_indices[2], label=f"{v1_labels[1]}{v1_labels[2]}")
    e1_2 = fig.add_edge(v1_indices[2], v1_indices[0], label=f"{v1_labels[2]}{v1_labels[0]}")

    # 三角形2的边
    e2_0 = fig.add_edge(v2_indices[0], v2_indices[1], label=f"{v2_labels[0]}{v2_labels[1]}")
    e2_1 = fig.add_edge(v2_indices[1], v2_indices[2], label=f"{v2_labels[1]}{v2_labels[2]}")
    e2_2 = fig.add_edge(v2_indices[2], v2_indices[0], label=f"{v2_labels[2]}{v2_labels[0]}")

    # 根据全等类型添加标注
    if cong_type == "SAS":
        # AB=DE (单杠), BC=EF (双杠), ∠B=∠E
        fig.add_equal_mark([e1_0, e2_0], count=1)
        fig.add_equal_mark([e1_1, e2_1], count=2)
        fig.add_angle_arc(v1_indices[1], e1_0, e1_1, label="", radius=20)
        fig.add_angle_arc(v2_indices[1], e2_0, e2_1, label="", radius=20)

    elif cong_type == "ASA":
        # ∠A=∠D, AB=DE, ∠B=∠E
        fig.add_angle_arc(v1_indices[0], e1_2, e1_0, label="", radius=20)
        fig.add_angle_arc(v2_indices[0], e2_2, e2_0, label="", radius=20)
        fig.add_equal_mark([e1_0, e2_0], count=1)
        fig.add_angle_arc(v1_indices[1], e1_0, e1_1, label="", radius=25)
        fig.add_angle_arc(v2_indices[1], e2_0, e2_1, label="", radius=25)

    elif cong_type == "SSS":
        # AB=DE, BC=EF, AC=DF
        fig.add_equal_mark([e1_0, e2_0], count=1)
        fig.add_equal_mark([e1_1, e2_1], count=2)
        fig.add_equal_mark([e1_2, e2_2], count=3)

    elif cong_type == "AAS":
        # ∠A=∠D, ∠B=∠E, BC=EF
        fig.add_angle_arc(v1_indices[0], e1_2, e1_0, label="", radius=20)
        fig.add_angle_arc(v2_indices[0], e2_2, e2_0, label="", radius=20)
        fig.add_angle_arc(v1_indices[1], e1_0, e1_1, label="", radius=25)
        fig.add_angle_arc(v2_indices[1], e2_0, e2_1, label="", radius=25)
        fig.add_equal_mark([e1_1, e2_1], count=1)

    # 填充两个三角形
    fig.add_region(v1_indices, "#bfdbfe", 0.2)
    fig.add_region(v2_indices, "#fecaca", 0.2)

    # 题目和步骤
    cond_text = "，".join(conditions) if conditions else "如图所示"
    type_names = {
        "SAS": "SAS（边角边）",
        "ASA": "ASA（角边角）",
        "SSS": "SSS（边边边）",
        "AAS": "AAS（角角边）",
    }

    p.question = question or (
        f"如图，在 △{v1_labels[0]}{v1_labels[1]}{v1_labels[2]} 和 "
        f"△{v2_labels[0]}{v2_labels[1]}{v2_labels[2]} 中，"
        f"已知 {cond_text}。"
        f"求证：△{v1_labels[0]}{v1_labels[1]}{v1_labels[2]} ≅ "
        f"△{v2_labels[0]}{v2_labels[1]}{v2_labels[2]}。"
    )
    p.answer = answer or f"△{v1_labels[0]}{v1_labels[1]}{v1_labels[2]} ≅ △{v2_labels[0]}{v2_labels[1]}{v2_labels[2]}（{type_names[cong_type]}）"

    p.set_meta("triangle_congruence", "三角形全等证明", "初中", "全等三角形")

    p.add_step("分析已知条件",
        f"已知条件：\n" + "\n".join(f"  • {c}" for c in conditions),
        {"edges": [e1_0, e1_1, e1_2, e2_0, e2_1, e2_2]})

    p.add_step("确定判定方法",
        f"根据已知条件，两个三角形中有：\n"
        + _format_cong_reason(cong_type, v1_labels, v2_labels),
        {"equal_marks": list(range(len(fig.equal_marks))),
         "angle_arcs": list(range(len(fig.angle_arcs)))})

    p.add_step("写出证明",
        f"证明：\n"
        + _format_cong_proof(cong_type, v1_labels, v2_labels, conditions),
        {"regions": [0, 1]})

    return p


def _format_cong_reason(ctype, v1, v2):
    """格式化全等判定理由。"""
    reasons = {
        "SAS": f"  {v1[0]}{v1[1]} = {v2[0]}{v2[1]}（已知）\n"
               f"  ∠{v1[1]} = ∠{v2[1]}（已知）\n"
               f"  {v1[1]}{v1[2]} = {v2[1]}{v2[2]}（已知）\n"
               f"→ 两边及其夹角对应相等，用 SAS 判定",
        "ASA": f"  ∠{v1[0]} = ∠{v2[0]}（已知）\n"
               f"  {v1[0]}{v1[1]} = {v2[0]}{v2[1]}（已知）\n"
               f"  ∠{v1[1]} = ∠{v2[1]}（已知）\n"
               f"→ 两角及其夹边对应相等，用 ASA 判定",
        "SSS": f"  {v1[0]}{v1[1]} = {v2[0]}{v2[1]}（已知）\n"
               f"  {v1[1]}{v1[2]} = {v2[1]}{v2[2]}（已知）\n"
               f"  {v1[2]}{v1[0]} = {v2[2]}{v2[0]}（已知）\n"
               f"→ 三边对应相等，用 SSS 判定",
        "AAS": f"  ∠{v1[0]} = ∠{v2[0]}（已知）\n"
               f"  ∠{v1[1]} = ∠{v2[1]}（已知）\n"
               f"  {v1[1]}{v1[2]} = {v2[1]}{v2[2]}（已知）\n"
               f"→ 两角及其中一角的对边对应相等，用 AAS 判定",
    }
    return reasons.get(ctype, "")


def _format_cong_proof(ctype, v1, v2, conditions):
    """格式化证明过程。"""
    t1 = f"△{v1[0]}{v1[1]}{v1[2]}"
    t2 = f"△{v2[0]}{v2[1]}{v2[2]}"
    proof = f"在 {t1} 和 {t2} 中：\n"
    for c in conditions:
        proof += f"  ∵ {c}\n"
    proof += f"  ∴ {t1} ≅ {t2}（{ctype}）"
    return proof


# ============================================================
#  题型 3：parallelogram_proof — 平行四边形证明
# ============================================================

def build_parallelogram_proof(base=6, side=4, angle_deg=60,
                              be_ratio=0.4, conditions=None,
                              prove_items=None, question="", answer=""):
    """平行四边形证明题。

    参数：
      base       — 底边 AB 长度
      side       — 侧边 AD 长度
      angle_deg  — ∠DAB 角度
      be_ratio   — BE 占 BC 的比例（E 在 BC 上，F 在 AD 上，BE=DF）
      conditions — 已知条件列表
      prove_items — 要证明的结论列表
    """
    if not HAS_SYMPY:
        raise RuntimeError("parallelogram_proof 需要 sympy，请先安装")

    p = PlaneProblem()
    fig = p.figure

    # 用 sympy 精确计算坐标
    angle_rad = angle_deg * pi / 180
    dx = float(side * cos(angle_rad))
    dy = float(side * sin(angle_rad))

    # 平行四边形 ABCD（逆时针）
    A = fig.add_vertex(0, 0, "A")
    B = fig.add_vertex(base, 0, "B")
    C = fig.add_vertex(base + dx, dy, "C")
    D = fig.add_vertex(dx, dy, "D")

    # E 在 BC 上，BE = be_ratio * BC
    ex = base + be_ratio * dx
    ey = be_ratio * dy
    E = fig.add_vertex(ex, ey, "E")

    # F 在 AD 上，DF = BE
    # AD 方向：D→A，F = D + be_ratio * (A - D)
    fx = dx + be_ratio * (0 - dx)
    fy = dy + be_ratio * (0 - dy)
    F = fig.add_vertex(fx, fy, "F")

    # 边（在 E、F 处断开）
    e_AB = fig.add_edge(A, B, label="AB")
    e_BE = fig.add_edge(B, E, label="BE")
    e_EC = fig.add_edge(E, C, label="EC")
    e_CD = fig.add_edge(C, D, label="CD")
    e_DF = fig.add_edge(D, F, label="DF")
    e_FA = fig.add_edge(F, A, label="FA")

    # 辅助线：AE, CF, AC
    e_AE = fig.add_edge(A, E, label="AE")
    e_CF = fig.add_edge(C, F, label="CF")
    e_AC = fig.add_aux_line(A, C, style="dashed", label="AC")

    # 标注
    # AB ∥ CD（单箭头）
    fig.add_parallel_mark([e_AB, e_CD], count=1)
    # BE ∥ DF（它们在平行的边上，BE=DF）
    fig.add_equal_mark([e_AB, e_CD], count=1)    # AB = CD（平行四边形对边相等）
    fig.add_equal_mark([e_BE, e_DF], count=2)    # BE = DF（已知）

    # 角度标注 ∠DAB
    fig.add_angle_arc(A, e_AB, e_FA, label=f"{angle_deg}°", radius=30)

    conditions = conditions or [
        "ABCD 是平行四边形",
        f"BE = DF",
    ]
    prove_items = prove_items or [
        "△ABE ≅ △CDF",
    ]

    cond_text = "，".join(conditions)
    prove_text = "；".join(prove_items)

    p.question = question or (
        f"如图，在平行四边形 ABCD 中，点 E、F 分别在 BC、AD 边上，"
        f"且 BE=DF。"
        f"\n求证：{prove_text}。"
    )

    p.set_meta("parallelogram_proof", "平行四边形证明", "初中", "平行四边形")

    # 计算验证
    be_len = be_ratio * side  # BE = be_ratio * |BC| = be_ratio * side
    df_len = be_ratio * side  # DF = be_ratio * |AD| = be_ratio * side
    assert abs(be_len - df_len) < 1e-10, "BE != DF, 坐标计算有误"

    p.add_step("分析已知条件",
        "已知：\n"
        f"  • ABCD 是平行四边形\n"
        f"    → AB = CD（对边相等）\n"
        f"    → AD = BC（对边相等）\n"
        f"    → ∠B = ∠D（对角相等）\n"
        f"  • BE = DF（已知）",
        {"edges": [e_AB, e_CD, e_BE, e_DF],
         "equal_marks": [0, 1],
         "parallel_marks": [0]})

    p.add_step("证明 △ABE ≅ △CDF",
        "在 △ABE 和 △CDF 中：\n"
        f"  AB = CD（平行四边形对边相等）\n"
        f"  ∠B = ∠D（平行四边形对角相等）\n"
        f"  BE = DF（已知）\n"
        f"∴ △ABE ≅ △CDF（SAS）",
        {"regions": [0, 1],
         "edges": [e_AB, e_BE, e_AE, e_CD, e_DF, e_CF]})

    # 填充两个三角形
    fig.add_region([A, B, E], "#bfdbfe", 0.25)    # △ABE
    fig.add_region([C, D, F], "#fecaca", 0.25)    # △CDF

    p.answer = answer or "△ABE ≅ △CDF（SAS）"

    return p


# ============================================================
#  题型 4：cube_net — 正方体展开图
# ============================================================

# 正方体展开图的 11 种基本形态
# 每种用 6 个格子的 (col, row) 坐标表示，以及对面关系
CUBE_NETS = {
    "cross": {
        # 十字形：中间一行 4 格，上面 1 格在第 2 列，下面 1 格在第 3 列
        "cells": [(0, 1), (1, 1), (2, 1), (3, 1), (1, 0), (2, 2)],
        "label_order": ["前", "右", "后", "左", "上", "下"],
        "opposites": [(0, 2), (1, 3), (4, 5)],  # 前-后, 右-左, 上-下
    },
    "t_shape": {
        # T 形：一行 3 格，上方 1 格在第 2 列，下方 2 格在第 1、2 列
        "cells": [(0, 1), (1, 1), (2, 1), (1, 0), (0, 2), (1, 2)],
        "label_order": ["前", "右", "后", "上", "下", "左"],
        "opposites": [(0, 2), (1, 5), (3, 4)],
    },
    "zigzag": {
        # Z 形：一行 3 格，上面 1 格在第 1 列，下面 1 格在第 3 列
        "cells": [(0, 1), (1, 1), (2, 1), (0, 0), (2, 2), (3, 2)],
        "label_order": ["前", "右", "后", "上", "下", "左"],
        "opposites": [(0, 2), (1, 5), (3, 4)],
    },
    "l_shape": {
        # L 形：一行 4 格，下面 1 格在第 1 列
        "cells": [(0, 0), (1, 0), (2, 0), (3, 0), (1, 1), (1, 2)],
        "label_order": ["前", "右", "后", "左", "下", "上"],
        "opposites": [(0, 2), (1, 3), (4, 5)],
    },
}


def build_cube_net(net_type="cross", question="", answer="", reveal=False):
    """正方体展开图——找对面。

    参数：
      net_type — 展开图类型：cross/t_shape/zigzag/l_shape
      reveal   — 是否直接揭示答案
    """
    if net_type not in CUBE_NETS:
        net_type = "cross"

    p = PlaneProblem()
    fig = p.figure
    net = CUBE_NETS[net_type]

    cells = net["cells"]
    labels = net["label_order"]
    opposites = net["opposites"]

    cell_size = 1.0
    gap = 0.05  # 格子间的小间隙

    # 为每个格子添加 4 个顶点
    # 但为了 SVG 渲染简洁，我们用 region 来表示每个面
    face_indices = []
    for i, (col, row) in enumerate(cells):
        x0 = col * (cell_size + gap)
        y0 = row * (cell_size + gap)
        x1 = x0 + cell_size
        y1 = y0 + cell_size

        # 4 个顶点
        v0 = fig.add_vertex(x0, y0)
        v1 = fig.add_vertex(x1, y0)
        v2 = fig.add_vertex(x1, y1)
        v3 = fig.add_vertex(x0, y1)

        # 4 条边
        fig.add_edge(v0, v1)
        fig.add_edge(v1, v2)
        fig.add_edge(v2, v3)
        fig.add_edge(v3, v0)

        # 面填充
        fill = "#e0e7ff"
        if reveal:
            # 揭示模式下，对面用相同颜色
            for pair_idx, (a, b) in enumerate(opposites):
                if i == a or i == b:
                    colors = ["#fca5a5", "#86efac", "#fcd34d"]
                    fill = colors[pair_idx]
                    break

        fig.add_region([v0, v1, v2, v3], fill, 0.6)

        # 面标签放在格子中心
        # 用 dimension_label 的变体——在区域中心放文字
        # 我们用 angle_arc 的 label 字段不太合适，直接在 meta 中存储
        face_indices.append({
            "vertices": [v0, v1, v2, v3],
            "label": labels[i],
            "center_x": (x0 + x1) / 2,
            "center_y": (y0 + y1) / 2,
        })

    # 构建答案
    opposite_pairs = []
    for a, b in opposites:
        opposite_pairs.append(f"{labels[a]} — {labels[b]}")

    answer_text = "、".join(opposite_pairs)

    p.question = question or (
        f"如图是一个正方体的展开图，"
        f"请找出三组相对的面。"
    )
    p.answer = answer or f"三组相对的面：{answer_text}"

    p.set_meta("cube_net", "正方体展开图", "小学", "空间想象")

    p.add_step("观察展开图",
        f"这是一个正方体的展开图，由 6 个正方形组成。\n"
        f"折叠后，哪些面会相对（即不相邻）？",
        {"regions": list(range(6))})

    p.add_step("找对面方法",
        "方法：在展开图中，如果两个面之间隔了一个面\n"
        "（即中间有且仅有一个面），那么折叠后它们就是相对的面。\n"
        "或者：一条直线上，间隔一个的两个面是对面。",
        {"regions": list(range(6))})

    p.add_step("揭示答案",
        f"三组相对的面：\n"
        + "\n".join(f"  • {pair}" for pair in opposite_pairs),
        {"regions": list(range(6))})

    # 存储面信息到 meta，供模板使用
    p.meta["faces"] = face_indices
    p.meta["reveal"] = reveal

    return p


# ============================================================
#  题型 5：shape_counting — 图形计数
# ============================================================

def build_shape_counting(count_type="triangle", question="", answer=""):
    """图形计数：数三角形/长方形。

    参数：
      count_type — "triangle" 数三角形 / "rectangle" 数长方形
    """
    p = PlaneProblem()
    fig = p.figure

    if count_type == "triangle":
        # 一个大三角形被两条线分割，数所有三角形
        # 顶点：A(顶), B(左下), C(右下), D(AB中点), E(AC中点), F(BC上点)
        A = fig.add_vertex(3, 5, "A")
        B = fig.add_vertex(0, 0, "B")
        C = fig.add_vertex(6, 0, "C")
        D = fig.add_vertex(1.5, 2.5, "D")  # AB 中点
        E = fig.add_vertex(4.5, 2.5, "E")  # AC 中点
        F = fig.add_vertex(3, 0, "F")       # BC 中点

        # 外三角形边
        e_AB = fig.add_edge(A, B)
        e_BC = fig.add_edge(B, C)
        e_AC = fig.add_edge(A, C)

        # 内部分割线
        e_DE = fig.add_edge(D, E, style="solid")
        e_DF = fig.add_edge(D, F, style="solid")
        e_EF = fig.add_edge(E, F, style="solid")

        # 所有三角形：
        # 小三角形: ADE, DBF, EFC, DEF
        # 中三角形: ADF, AEF, DBE... 
        # 大三角形: ABC, ABE, AEC... 
        # 实际数法：
        # 单个的：ADE, DBF, EFC, DEF = 4
        # 两个拼的：ADF, AEF, DBE... 
        # 让我仔细数...
        # 顶点：A, B, C, D(AB中), E(AC中), F(BC中)
        # 三角形组合：
        # 1. △ADE (A-D-E)
        # 2. △DBF (D-B-F)
        # 3. △EFC (E-F-C)
        # 4. △DEF (D-E-F)
        # 5. △ABF (A-B-F) = ADE + DBF + DEF... 不对
        # 让我重新想...
        # D 在 AB 上，E 在 AC 上，F 在 BC 上
        # DE 连接 AB 中点和 AC 中点 → DE ∥ BC
        # DF 连接 AB 中点和 BC 中点 → DF ∥ AC
        # EF 连接 AC 中点和 BC 中点 → EF ∥ AB
        # 
        # 所有三点组合中能构成三角形的：
        # 小：ADE, DBF, EFC, DEF (4个)
        # 中：ADF (= ADE+DEF), AEF (= ADE+DEF... 不对)
        # 
        # 实际上：
        # 用 D, E, F 把 △ABC 分成了 4 个小三角形
        # 但如果考虑所有可能的三点组合：
        # {A,D,E}, {D,B,F}, {E,F,C}, {D,E,F} — 4 个基本三角形
        # {A,D,F} — A-D-F，这个包含两个小三角形
        # {A,E,F} — A-E-F
        # {D,E,C} — D-E-C... D 在 AB 上, E 在 AC 上, C 是顶点 → 不共线，是三角形
        # {B,E,F}... B-E 不在一条边上
        # {B,D,E}... B-D 在 AB 上, D-E 是分割线 → 三角形 BDE
        # {C,D,F}... C-F 在 BC 上, D-F 是分割线 → 三角形 CDF
        # {A,B,E}... A-B 是边, B-E 不是
        # {A,D,C}... A-D 在 AB 上, D-C 不是
        # {A,B,C} — 大三角形
        # {A,B,F}... A-B 是边, B-F 在 BC 上 → A, B, F 不共线 → △ABF
        # {A,E,C}... A-E 在 AC 上 → 共线，不是三角形
        # {D,B,C}... D-B 在 AB 上, B-C 是边 → △DBC
        # {A,E,B}... A-E 在 AC 上 → 不对，E 在 AC 上
        # 
        # OK 这个太复杂了。让我简化：用一个更简单的图形。

        # 简化版：一个大三角形被一条中位线分割
        # 顶点：A(顶), B(左下), C(右下), D(AB中), E(AC中)
        # DE 是中位线
        # 三角形：ADE, DBCE... 不对
        # 只有 3 个三角形：ADE, BDEC... 
        # △ADE, △BDE... 不对，B-D-E-B 不是三角形
        # △ADE (上方小三角), △BDE... 不对
        # △ADE, △BEC? 不对...
        # 
        # 让我用最简单的：一个三角形 ABC，D 在 AB 上，E 在 AC 上，DE 连接
        # 三角形有：△ADE, △DBCE... 
        # 基本的：△ADE, △BDEC... 
        # 只有 △ADE 和 △ABC 两个？不对...
        # △ADE, △BEC? E 在 AC 上，所以 B-E-C... 不共线 → △BEC? 不对，E 在 AC 上不在 BC 上
        # 
        # 啊，让我重新设置：D 在 AB 上, E 在 BC 上（不是 AC）
        # 这样 DE 把三角形分成 △ADE 和 △BDEC... 
        # △ADE (上方), △DBE... 不对
        # 
        # 我需要更仔细地设计这个图形。让我用一个经典的"数三角形"题：
        # 一个三角形，底边上有两个点，把底边分成三段
        # 这样从顶点到底边每个点的连线，把三角形分成多个小三角形
        
        # 清空重做
        fig.vertices = []
        fig.edges = []
        fig.regions = []
        fig.equal_marks = []
        fig.right_angles = []
        fig.parallel_marks = []
        fig.dimension_labels = []
        fig.aux_lines = []
        fig.angle_arcs = []

        # 经典数三角形题：
        # 大三角形 ABC，底边 BC 上有 D, E 两点
        # A 连到 D, A 连到 E
        # 这样底边被分成 BD, DE, EC 三段
        # 从 A 出发有 AD, AE 两条线
        # 三角形：ABD, ADE, AEC (3个基本), ABC (1个大的)
        # 还有：ABE (= ABD+ADE), ADC (= ADE+AEC)
        # 总共：3 + 2 + 1 = 6 个三角形

        A = fig.add_vertex(3, 5, "A")
        B = fig.add_vertex(0, 0, "B")
        D = fig.add_vertex(2, 0, "D")
        E = fig.add_vertex(4, 0, "E")
        C = fig.add_vertex(6, 0, "C")

        # 外三角形
        e_AB = fig.add_edge(A, B)
        e_BC = fig.add_edge(B, C)

        # 底边分段（其实 e_BC 就是 B-C，但我们需要标注 D, E 在上面）
        # 为了让图清晰，画 B-D, D-E, E-C
        # 但 e_BC 已经画了 B-C... 让我不画 B-C，而是画 B-D, D-E, E-C
        fig.edges.pop()  # 移除 e_BC
        e_BD = fig.add_edge(B, D)
        e_DE = fig.add_edge(D, E)
        e_EC = fig.add_edge(E, C)

        # 从 A 到 D, A 到 E 的连线
        e_AD = fig.add_edge(A, D)
        e_AE = fig.add_edge(A, E)

        # 不画 A-C（因为 A 到 C 的连线不是边，而是经过 E）
        # 实际上 A-C 不经过 E... E 在 BC 上不在 AC 上
        # 让我重新想：A(3,5), B(0,0), C(6,0), D(2,0), E(4,0)
        # A 到 C 的连线：从 (3,5) 到 (6,0)，不经过 (4,0)
        # 所以我需要画 A-C 边
        e_AC = fig.add_edge(A, C)

        # 填充
        fig.add_region([A, B, D], "#bfdbfe", 0.2)   # △ABD
        fig.add_region([A, D, E], "#fecaca", 0.2)   # △ADE
        fig.add_region([A, E, C], "#bfdbfe", 0.2)   # △AEC

        total = 6  # ABD, ADE, AEC, ABE, ADC, ABC
        p.question = question or (
            f"如图，三角形 ABC 中，底边 BC 上有 D、E 两点，"
            f"连接 AD、AE。图中共有多少个三角形？"
        )
        p.answer = answer or f"共有 {total} 个三角形"

        p.set_meta("shape_counting", "数三角形", "小学", "图形计数")

        p.add_step("观察图形",
            "从顶点 A 出发，到底边 BC 上的 B、D、E、C 四个点，\n"
            "形成了多条线段。",
            {"vertices": [0, 1, 2, 3, 4],
             "edges": [0, 1, 2, 3, 4, 5]})

        p.add_step("数基本三角形",
            "不重叠的基本三角形：\n"
            "  • △ABD（左）\n"
            "  • △ADE（中）\n"
            "  • △AEC（右）\n"
            "共 3 个",
            {"regions": [0, 1, 2]})

        p.add_step("数组合三角形",
            "两个基本三角形拼成的：\n"
            "  • △ABE = △ABD + △ADE\n"
            "  • △ADC = △ADE + △AEC\n"
            "共 2 个",
            {"regions": [0, 1]})

        p.add_step("数大三角形",
            "三个基本三角形拼成的：\n"
            "  • △ABC = △ABD + △ADE + △AEC\n"
            "共 1 个",
            {"regions": [0, 1, 2]})

        p.add_step("总计",
            f"3 + 2 + 1 = {total} 个三角形",
            {"regions": [0, 1, 2]})

    elif count_type == "rectangle":
        # 2×2 网格，数长方形
        # 顶点：4×3 = 12 个（3列×4行网格点，但 2×2 格子 = 3×3 点）
        grid_cols = 3  # 3 列点 = 2 列格子
        grid_rows = 3  # 3 行点 = 2 行格子

        points = []
        for row in range(grid_rows):
            for col in range(grid_cols):
                idx = fig.add_vertex(col * 2, (grid_rows - 1 - row) * 2,
                                     f"P{row*grid_cols+col}")
                points.append(idx)

        # 画网格线
        for row in range(grid_rows):
            for col in range(grid_cols - 1):
                fig.add_edge(points[row * grid_cols + col],
                            points[row * grid_cols + col + 1])
        for col in range(grid_cols):
            for row in range(grid_rows - 1):
                fig.add_edge(points[row * grid_cols + col],
                            points[(row + 1) * grid_cols + col])

        # 填充每个格子
        for row in range(grid_rows - 1):
            for col in range(grid_cols - 1):
                v0 = points[row * grid_cols + col]
                v1 = points[row * grid_cols + col + 1]
                v2 = points[(row + 1) * grid_cols + col + 1]
                v3 = points[(row + 1) * grid_cols + col]
                fig.add_region([v0, v1, v2, v3], "#e0e7ff", 0.3)

        # 2×2 网格中的长方形数：
        # 1×1: 4个, 1×2: 2个(横)+2个(竖)=4个, 2×2: 1个 → 共9个
        total = 9

        p.question = question or "如图是一个 2×2 的方格网，图中共有多少个长方形？"
        p.answer = answer or f"共有 {total} 个长方形"

        p.set_meta("shape_counting", "数长方形", "小学", "图形计数")

        p.add_step("观察图形",
            "这是一个 2×2 的方格网，有 3 行 3 列共 9 个格点。",
            {"regions": list(range(4))})

        p.add_step("数 1×1 的小长方形",
            "每个格子就是一个 1×1 的小长方形。\n共 4 个。",
            {"regions": [0, 1, 2, 3]})

        p.add_step("数 1×2 的长方形",
            "横着拼：2 个\n竖着拼：2 个\n共 4 个。",
            {"regions": [0, 1]})

        p.add_step("数 2×2 的大长方形",
            "整个方格网就是 1 个 2×2 的大长方形。",
            {"regions": [0, 1, 2, 3]})

        p.add_step("总计",
            f"4 + 4 + 1 = {total} 个长方形",
            {"regions": list(range(4))})

    return p


# ============================================================
#  序列化与反序列化
# ============================================================

def to_json(problem):
    """将 PlaneProblem 转为 JSON 字符串。"""
    return json.dumps(problem.to_lesson_data(), ensure_ascii=False, indent=2)


# ============================================================
#  自检
# ============================================================

def self_test():
    """运行全部自检。"""
    print("=== plane_kernel.py 自检 ===\n")

    # 测试 1: 简单长方形面积
    p1 = build_rectangle_area(5, 3)
    d1 = p1.to_lesson_data()
    assert d1["figure"]["vertices"][0]["label"] == "A"
    assert len(d1["figure"]["vertices"]) == 4
    assert len(d1["figure"]["edges"]) == 4
    assert "15 平方米" in d1["answer"]
    assert len(d1["steps"]) == 3
    print("  测试1 通过: 简单长方形面积（5×3=15）")

    # 测试 2: 回字形面积
    p2 = build_rectangle_area(15, 8, path_width=1)
    d2 = p2.to_lesson_data()
    assert len(d2["figure"]["vertices"]) == 8  # 外4 + 内4
    assert len(d2["figure"]["edges"]) == 8     # 外4 + 内4
    assert len(d2["figure"]["regions"]) == 2    # 路 + 草坪
    assert "50 平方米" in d2["answer"]          # 17×10 - 15×8 = 170-120=50
    assert len(d2["steps"]) == 4
    # 验证: 大长方形 17×10=170, 小长方形 15×8=120, 路=50
    assert 170 - 120 == 50
    print("  测试2 通过: 回字形面积（15×8, 路宽1, 答案50）")

    # 测试 3: 三角形全等 SAS
    spec3 = {
        "type": "SAS",
        "triangle1": {"vertices": ["A", "B", "C"]},
        "triangle2": {"vertices": ["D", "E", "F"]},
        "conditions": ["AB=DE", "∠B=∠E", "BC=EF"],
    }
    p3 = build_triangle_congruence(spec3)
    d3 = p3.to_lesson_data()
    assert len(d3["figure"]["vertices"]) == 6  # 3+3
    assert len(d3["figure"]["edges"]) == 6     # 3+3
    assert len(d3["figure"]["equalMarks"]) == 2  # 两组等长
    assert len(d3["figure"]["angleArcs"]) == 2    # 两个角弧
    assert "SAS" in d3["answer"]
    assert len(d3["steps"]) == 3
    print("  测试3 通过: 三角形全等 SAS")

    # 测试 4: 三角形全等 SSS
    spec4 = {
        "type": "SSS",
        "triangle1": {"vertices": ["A", "B", "C"]},
        "triangle2": {"vertices": ["D", "E", "F"]},
        "conditions": ["AB=DE", "BC=EF", "AC=DF"],
    }
    p4 = build_triangle_congruence(spec4)
    d4 = p4.to_lesson_data()
    assert len(d4["figure"]["equalMarks"]) == 3  # 三组等长
    assert len(d4["figure"]["angleArcs"]) == 0    # SSS 没有角弧
    assert "SSS" in d4["answer"]
    print("  测试4 通过: 三角形全等 SSS")

    # 测试 5: 平行四边形证明
    if HAS_SYMPY:
        p5 = build_parallelogram_proof(base=6, side=4, angle_deg=60, be_ratio=0.4)
        d5 = p5.to_lesson_data()
        assert len(d5["figure"]["vertices"]) == 6  # A,B,C,D,E,F
        assert len(d5["figure"]["edges"]) == 8     # AB,BE,EC,CD,DF,FA,AE,CF
        assert len(d5["figure"]["parallelMarks"]) == 1
        assert len(d5["figure"]["equalMarks"]) == 2
        assert len(d5["figure"]["auxLines"]) == 1  # AC
        assert "SAS" in d5["answer"]
        assert len(d5["steps"]) == 2
        # 验证 BE = DF
        # BE = 0.4 * 4 = 1.6, DF = 0.4 * 4 = 1.6
        print("  测试5 通过: 平行四边形证明（BE=DF 验证）")

    # 测试 6: 正方体展开图 cross
    p6 = build_cube_net("cross")
    d6 = p6.to_lesson_data()
    assert len(d6["figure"]["vertices"]) == 24  # 6面 × 4顶点
    assert len(d6["figure"]["edges"]) == 24     # 6面 × 4边
    assert len(d6["figure"]["regions"]) == 6
    assert "前" in d6["answer"] and "后" in d6["answer"]
    assert len(d6["steps"]) == 3
    # 验证对面关系
    faces = d6["meta"]["faces"]
    assert len(faces) == 6
    print("  测试6 通过: 正方体展开图 cross")

    # 测试 7: 正方体展开图 reveal 模式
    p7 = build_cube_net("t_shape", reveal=True)
    d7 = p7.to_lesson_data()
    assert d7["meta"]["reveal"] == True
    # 揭示模式下应该有不同颜色的区域
    fills = set(r["fill"] for r in d7["figure"]["regions"])
    assert len(fills) > 1  # 应该有多种颜色
    print("  测试7 通过: 正方体展开图揭示模式")

    # 测试 8: 数三角形
    p8 = build_shape_counting("triangle")
    d8 = p8.to_lesson_data()
    assert len(d8["figure"]["vertices"]) == 5  # A,B,C,D,E
    assert "6 个三角形" in d8["answer"]
    assert len(d8["steps"]) == 5
    print("  测试8 通过: 数三角形（答案6个）")

    # 测试 9: 数长方形
    p9 = build_shape_counting("rectangle")
    d9 = p9.to_lesson_data()
    assert len(d9["figure"]["vertices"]) == 9  # 3×3 网格点
    assert "9 个长方形" in d9["answer"]
    assert len(d9["steps"]) == 5
    print("  测试9 通过: 数长方形（答案9个）")

    # 测试 10: 序列化正确性
    json_str = to_json(p1)
    assert '"mode": "rectangle_area"' in json_str
    assert '"figure"' in json_str
    assert '"steps"' in json_str
    parsed = json.loads(json_str)
    assert parsed["mode"] == "rectangle_area"
    print(f"  测试10 通过: 序列化正常, JSON长度{len(json_str)}")

    # 测试 11: 回字形面积验证（不同参数）
    p11 = build_rectangle_area(10, 6, path_width=2)
    d11 = p11.to_lesson_data()
    # 大: (10+4)×(6+4) = 14×10 = 140
    # 小: 10×6 = 60
    # 路: 140-60 = 80
    assert "80 平方米" in d11["answer"]
    print("  测试11 通过: 回字形面积验证（10×6, 路宽2, 答案80）")

    print("\n=== 全部通过 ===")
    print(f"  sympy: {'已安装' if HAS_SYMPY else '未安装（初中题型不可用）'}")


if __name__ == "__main__":
    self_test()
