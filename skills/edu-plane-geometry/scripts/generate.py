#!/usr/bin/env python3
"""
edu-plane-geometry 生成脚本
用法：
  python scripts/generate.py --type rectangle --width 15 --height 8 --path-width 1
  python scripts/generate.py --type congruence --cong-type SAS
  python scripts/generate.py --type parallelogram --base 6 --side 4 --angle 60
  python scripts/generate.py --type cube-net --net-type cross --reveal
  python scripts/generate.py --type counting --count-type triangle
  python scripts/generate.py --type counting --count-type rectangle

  --output PATH  指定输出文件路径
"""

import sys
import os
import json
import argparse

# 将 lib 目录加入路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(SKILL_DIR, "lib"))

from plane_kernel import (
    build_rectangle_area,
    build_triangle_congruence,
    build_parallelogram_proof,
    build_cube_net,
    build_shape_counting,
    to_json,
)


TEMPLATE_PATH = os.path.join(SKILL_DIR, "template", "lesson.html")


def load_template():
    """读取 HTML 模板。"""
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def inject_and_write(problem, output_path=None):
    """将 problem 数据注入模板并写入文件。"""
    template = load_template()
    json_str = to_json(problem)
    html = template.replace("__LESSON_DATA__", json_str)

    if output_path is None:
        output_path = os.path.join(os.getcwd(), "plane-geometry-lesson.html")

    # 确保输出目录存在
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"生成完成!")
    print(f"  题型: {problem.meta.get('mode', 'unknown')}")
    print(f"  标题: {problem.meta.get('title', '')}")
    print(f"  年级: {problem.meta.get('grade', '')}")
    print(f"  题目: {problem.question[:60]}...")
    print(f"  答案: {problem.answer}")
    print(f"  步骤数: {len(problem.steps)}")
    print(f"  文件: {output_path}")
    return output_path


def generate_rectangle(width=5, height=3, path_width=None,
                       question="", answer="", output_path=None):
    """生成长方形面积题。"""
    p = build_rectangle_area(width, height, path_width, question, answer)
    return inject_and_write(p, output_path)


def generate_congruence(cong_type="SAS", question="", answer="",
                        output_path=None):
    """生成三角形全等证明题。"""
    v1 = ["A", "B", "C"]
    v2 = ["D", "E", "F"]

    specs = {
        "SAS": {
            "type": "SAS",
            "triangle1": {"vertices": v1},
            "triangle2": {"vertices": v2},
            "conditions": ["AB=DE", "angle_B=angle_E", "BC=EF"],
        },
        "ASA": {
            "type": "ASA",
            "triangle1": {"vertices": v1},
            "triangle2": {"vertices": v2},
            "conditions": ["angle_A=angle_D", "AB=DE", "angle_B=angle_E"],
        },
        "SSS": {
            "type": "SSS",
            "triangle1": {"vertices": v1},
            "triangle2": {"vertices": v2},
            "conditions": ["AB=DE", "BC=EF", "AC=DF"],
        },
        "AAS": {
            "type": "AAS",
            "triangle1": {"vertices": v1},
            "triangle2": {"vertices": v2},
            "conditions": ["angle_A=angle_D", "angle_B=angle_E", "BC=EF"],
        },
    }

    spec = specs.get(cong_type, specs["SAS"])
    p = build_triangle_congruence(spec, question, answer)
    return inject_and_write(p, output_path)


def generate_parallelogram(base=6, side=4, angle=60, be_ratio=0.4,
                           question="", answer="", output_path=None):
    """生成平行四边形证明题。"""
    p = build_parallelogram_proof(base, side, angle, be_ratio,
                                  question=question, answer=answer)
    return inject_and_write(p, output_path)


def generate_cube_net(net_type="cross", reveal=False,
                      question="", answer="", output_path=None):
    """生成正方体展开图题。"""
    p = build_cube_net(net_type, question, answer, reveal)
    return inject_and_write(p, output_path)


def generate_counting(count_type="triangle",
                      question="", answer="", output_path=None):
    """生成图形计数题。"""
    p = build_shape_counting(count_type, question, answer)
    return inject_and_write(p, output_path)


def main():
    parser = argparse.ArgumentParser(
        description="edu-plane-geometry 生成脚本"
    )
    parser.add_argument("--type", type=str, default="rectangle",
                        choices=["rectangle", "congruence", "parallelogram",
                                 "cube-net", "counting"],
                        help="题型")

    # 长方形参数
    parser.add_argument("--width", type=float, default=5, help="长方形宽")
    parser.add_argument("--height", type=float, default=3, help="长方形高")
    parser.add_argument("--path-width", type=float, default=None,
                        help="回字形路宽（不设则为简单长方形）")

    # 全等参数
    parser.add_argument("--cong-type", type=str, default="SAS",
                        choices=["SAS", "ASA", "SSS", "AAS"],
                        help="全等判定类型")

    # 平行四边形参数
    parser.add_argument("--base", type=float, default=6, help="底边长")
    parser.add_argument("--side", type=float, default=4, help="侧边长")
    parser.add_argument("--angle", type=float, default=60, help="底角度数")
    parser.add_argument("--be-ratio", type=float, default=0.4,
                        help="BE占BC的比例")

    # 展开图参数
    parser.add_argument("--net-type", type=str, default="cross",
                        choices=["cross", "t_shape", "zigzag", "l_shape"],
                        help="展开图类型")
    parser.add_argument("--reveal", action="store_true",
                        help="直接揭示答案（展开图）")

    # 计数参数
    parser.add_argument("--count-type", type=str, default="triangle",
                        choices=["triangle", "rectangle"],
                        help="计数类型")

    # 输出
    parser.add_argument("--output", type=str, default=None,
                        help="输出文件路径")

    args = parser.parse_args()

    if args.type == "rectangle":
        generate_rectangle(args.width, args.height, args.path_width,
                           output_path=args.output)
    elif args.type == "congruence":
        generate_congruence(args.cong_type, output_path=args.output)
    elif args.type == "parallelogram":
        generate_parallelogram(args.base, args.side, args.angle,
                               args.be_ratio, output_path=args.output)
    elif args.type == "cube-net":
        generate_cube_net(args.net_type, args.reveal,
                          output_path=args.output)
    elif args.type == "counting":
        generate_counting(args.count_type, output_path=args.output)


if __name__ == "__main__":
    main()
