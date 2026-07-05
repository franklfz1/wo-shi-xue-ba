#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate.py — 生成方块三视图交互教学页面。

支持四种模式：
  demo    — 演示模式：3D + 三视图 + 分步讲解（默认）
  draw    — 画图模式：展示 3D，学生在方格纸上画三视图，与标准答案比对
  reverse — 逆向还原：展示三视图，学生在 3D 网格上还原方块摆放
  choice  — 识图选择题：展示一个3D模型，给出四个方向的视图选项，问哪个是指定方向

用法：
  # 演示模式（默认）
  python generate.py --random --width 3 --depth 3
  python generate.py --blocks '[[2,1],[1,2]]'

  # 画图模式
  python generate.py --mode draw --random --seed 42

  # 逆向还原
  python generate.py --mode reverse --random --seed 42

  # 选择题
  python generate.py --mode choice --direction front --seed 42
  python generate.py --mode choice --direction top --seed 88
"""

import json
import os
import sys
import argparse

# 添加 lib 到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(SKILL_DIR, "lib"))

from block_kernel import BlockArrangement

TEMPLATE_PATH = os.path.join(SKILL_DIR, "template", "lesson.html")


def generate_demo(arrangement, question="", output_path=None):
    """生成演示模式页面。"""
    data = arrangement.to_lesson_data(question=question)
    return _inject_and_write(data, output_path)


def generate_draw(arrangement, question="", output_path=None):
    """生成画图模式页面。"""
    if not question:
        question = ('下面的立体图形由若干个小正方体组成。'
                    '请你在右侧的方格纸上分别画出从正面、左面、上面看到的形状。'
                    '点击方格可以填涂或取消，画完后点「检查答案」。')
    data = arrangement.to_draw_mode_data(question=question)
    return _inject_and_write(data, output_path)


def generate_reverse(arrangement, question="", output_path=None):
    """生成逆向还原模式页面。"""
    if not question:
        count = arrangement.cube_count()
        question = ("上面给出了一个立体图形的三视图。"
                    "请你在下方的 3D 网格上还原出这个立体图形。"
                    "左键点击放置方块，右键点击移除方块。"
                    f"（提示：一共用了 {count} 个小正方体）")
    data = arrangement.to_reverse_mode_data(question=question)
    return _inject_and_write(data, output_path)


def generate_choice(direction="front", width=3, depth=3, max_height=3,
                    seed=None, output_path=None):
    """生成识图选择题模式页面：一个3D模型 + 四个方向视图选项。"""
    data = BlockArrangement.generate_view_identification(
        direction=direction, width=width, depth=depth,
        max_height=max_height, seed=seed
    )
    return _inject_and_write(data, output_path)


def _inject_and_write(data, output_path):
    """注入数据到模板并写入文件。"""
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    html = template.replace("__LESSON_DATA__", json_str)

    if output_path is None:
        mode = data.get("mode", "demo")
        output_path = os.path.join(os.getcwd(), f"block-views-{mode}.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path, data


def parse_blocks(blocks_json):
    """从 2D JSON 数组解析方块摆放。"""
    matrix = json.loads(blocks_json)
    width = len(matrix)
    depth = len(matrix[0]) if width > 0 else 0
    arr = BlockArrangement(width, depth)
    for x in range(width):
        for y in range(depth):
            arr.place(x, y, matrix[x][y])
    return arr


def main():
    parser = argparse.ArgumentParser(description="生成方块三视图交互教学页面")
    parser.add_argument("--mode", type=str, default="demo",
                        choices=["demo", "draw", "reverse", "choice"],
                        help="模式：demo(演示) / draw(画图) / reverse(逆向还原) / choice(选择题)")
    parser.add_argument("--direction", type=str, default="front",
                        choices=["front", "left", "top", "back", "right"],
                        help="选择题模式：问哪个方向的视图")
    parser.add_argument("--random", action="store_true", help="随机生成")
    parser.add_argument("--blocks", type=str, help="指定摆放(JSON 2D数组)")
    parser.add_argument("--width", type=int, default=3, help="网格宽度(列数)")
    parser.add_argument("--depth", type=int, default=3, help="网格深度(行数)")
    parser.add_argument("--max-height", type=int, default=3, help="最大堆叠高度")
    parser.add_argument("--min-cubes", type=int, default=4, help="最少方块数")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument("--question", type=str, default="", help="自定义题目文字")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径")
    args = parser.parse_args()

    # 选择题模式
    if args.mode == "choice":
        output_path, data = generate_choice(
            direction=args.direction,
            width=args.width, depth=args.depth,
            max_height=args.max_height,
            seed=args.seed,
            output_path=args.output
        )
        print("生成完成! [识图选择题模式]")
        print(f"  方向: {data['directionLabel']}")
        print(f"  正确答案: {data['correctLabel']}")
        for opt in data["options"]:
            v = opt["view"]
            print(f"  {opt['label']}: {v.get('heights', v.get('cells'))} ({v['label']})")
        print(f"  文件: {output_path}")
        return

    # 其他模式：需要创建 BlockArrangement
    if args.blocks:
        arr = parse_blocks(args.blocks)
    elif args.random:
        arr = BlockArrangement.random(
            width=args.width, depth=args.depth,
            max_height=args.max_height, min_cubes=args.min_cubes,
            seed=args.seed
        )
    else:
        # 默认 demo
        arr = BlockArrangement(3, 2)
        arr.place(0, 0, 2).place(1, 0, 1).place(2, 0, 3)
        arr.place(0, 1, 1).place(1, 1, 2).place(2, 1, 1)

    if args.mode == "demo":
        output_path, _ = generate_demo(arr, question=args.question, output_path=args.output)
    elif args.mode == "draw":
        output_path, _ = generate_draw(arr, question=args.question, output_path=args.output)
    elif args.mode == "reverse":
        output_path, _ = generate_reverse(arr, question=args.question, output_path=args.output)
    else:
        output_path, _ = generate_demo(arr, question=args.question, output_path=args.output)

    print(f"生成完成! [{args.mode}模式]")
    print(f"  方块数: {arr.cube_count()}")
    print(f"  网格: {arr.width}x{arr.depth}, 最高{arr.max_height()}层")
    print(f"  正面视图: {arr.front_view()}")
    print(f"  左面视图: {arr.side_view()}")
    print(f"  俯视图: {arr.top_view()}")
    print(f"  文件: {output_path}")


if __name__ == "__main__":
    main()
