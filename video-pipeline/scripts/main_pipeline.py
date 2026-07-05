"""
main_pipeline.py — 数学短视频制作流水线主入口（增强版 v2）。

增强功能:
  - 支持音效混合 (SFX)
  - 支持预渲染 SVG 动画帧
  - 支持趣味解说脚本

用法:
  python main_pipeline.py <script.json> [--output output/ep1.mp4] [--sfx-dir assets/sfx/] [--svg-dir assets/svg_animations/]
"""

import json
import subprocess
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

BASE_DIR    = Path(__file__).parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
CONFIG_PATH = BASE_DIR / "config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)


def step1_read_script(script_path: str) -> dict:
    print("=== Step 1: 读取脚本 ===")
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)
    print(f"  主题: {script['topic']}")
    print(f"  场景数: {len(script['scenes'])}")
    sfx_count = len(script.get("sfx_events", []))
    print(f"  音效数: {sfx_count}")
    return script


def step2_generate_voice(script_path: str) -> tuple:
    print("\n=== Step 2: 生成配音 ===")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "generate_voice.py"), script_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[ERROR] 配音生成失败:\n{result.stderr}")
        sys.exit(1)
    temp_dir = Path(CONFIG["output"]["temp_dir"])
    return str(temp_dir / "voice.mp3"), str(temp_dir / "voice_timeline.json")


def step3_render_frames(script: dict, timeline: list, svg_dir: str = None) -> str:
    print("\n=== Step 3: 渲染画面帧 ===")
    temp_dir = Path(CONFIG["output"]["temp_dir"])
    frames_dir = temp_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    tl_file = temp_dir / "render_timeline.json"
    with open(tl_file, "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)

    cmd = [
        sys.executable, str(SCRIPTS_DIR / "render_frames.py"),
        "--script", json.dumps(script),
        "--timeline", str(tl_file),
        "--output", str(frames_dir),
    ]
    if svg_dir:
        cmd += ["--svg-dir", svg_dir]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] 帧渲染失败:\n{result.stderr}")
        sys.exit(1)
    print(f"  -> {frames_dir}")
    return str(frames_dir)


def step4_generate_srt(timeline: list, output_path: str):
    print("\n=== Step 4: 生成 SRT 字幕 ===")
    subtitles = []
    for i, item in enumerate(timeline, 1):
        start_s = item["start"]
        end_s   = item["end"]
        text    = item["text"]
        def fmt(s):
            h = int(s // 3600)
            m = int((s % 3600) // 60)
            sec = int(s % 60)
            ms = int((s - int(s)) * 1000)
            return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
        subtitles.append(f"{i}\n{fmt(start_s)} --> {fmt(end_s)}\n{text}\n")

    srt_path = Path(output_path)
    with open(srt_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(subtitles))
    print(f"  -> {srt_path}  ({len(subtitles)} 条)")
    return str(srt_path)


def step5_prepare_sfx(script: dict, output_path: str) -> str:
    """从脚本中提取音效事件，写入临时 JSON 文件"""
    sfx_events = script.get("sfx_events", [])
    if not sfx_events:
        return None

    print(f"\n=== Step 4.5: 准备音效 ({len(sfx_events)} 个) ===")

    # 确保音效文件都存在，不存在则跳过
    valid_events = []
    for evt in sfx_events:
        sfx_file = evt.get("file", "")
        if sfx_file and not Path(sfx_file).is_absolute():
            sfx_file = str(BASE_DIR / sfx_file)
        if Path(sfx_file).exists():
            evt_copy = dict(evt)
            evt_copy["file"] = sfx_file
            valid_events.append(evt_copy)
        else:
            print(f"  [WARN] 音效不存在: {sfx_file}")

    if not valid_events:
        print("  无有效音效，跳过")
        return None

    sfx_json = Path(output_path).with_suffix(".sfx.json")
    with open(sfx_json, "w", encoding="utf-8") as f:
        json.dump(valid_events, f, ensure_ascii=False, indent=2)
    print(f"  -> {sfx_json}")
    return str(sfx_json)


def step6_compose_video(frames_dir: str, audio_file: str, srt_file: str,
                        output_file: str, sfx_file: str = None):
    print("\n=== Step 6: 合成最终视频 ===")
    cmd = [
        sys.executable, str(SCRIPTS_DIR / "compose_video.py"),
        frames_dir, audio_file,
        "--subtitle", srt_file,
        "--output", output_file,
    ]
    if sfx_file:
        cmd += ["--sfx", sfx_file]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] 视频合成失败:\n{result.stderr}")
        sys.exit(1)

    size_mb = Path(output_file).stat().st_size / 1024 / 1024
    print(f"\n=== 视频制作完成! ===")
    print(f"  文件: {output_file}")
    print(f"  大小: {size_mb:.1f} MB")
    return output_file


def run(script_path: str, output_path: str = None,
        svg_dir: str = None, sfx_dir: str = None):
    script = step1_read_script(script_path)

    if output_path is None:
        date_str  = datetime.now().strftime("%Y%m%d")
        topic_str = script["topic"].replace(" ", "_")
        output_path = f"output/{date_str}_{topic_str}.mp4"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Step 2: 配音
    audio_file, timeline_file = step2_generate_voice(script_path)

    with open(timeline_file, "r", encoding="utf-8") as f:
        timeline = json.load(f)

    # Step 3: 渲染帧
    frames_dir = step3_render_frames(script, timeline, svg_dir)

    # Step 4: 生成 SRT
    srt_file = step4_generate_srt(timeline, str(Path(output_path).with_suffix(".srt")))

    # Step 4.5: 准备音效
    sfx_file = step5_prepare_sfx(script, output_path)

    # Step 6: 合成视频
    final_video = step6_compose_video(frames_dir, audio_file, srt_file, output_path, sfx_file)

    print(f"\n  用播放器打开: {final_video}")
    return final_video


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python main_pipeline.py <script.json> [--output output/ep1.mp4] [--svg-dir assets/svg_animations/]")
        sys.exit(1)

    script_path = sys.argv[1]
    output_path = None
    svg_dir = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]; i += 2
        elif sys.argv[i] == "--svg-dir" and i + 1 < len(sys.argv):
            svg_dir = sys.argv[i + 1]; i += 2
        else:
            i += 1

    run(script_path, output_path, svg_dir)
