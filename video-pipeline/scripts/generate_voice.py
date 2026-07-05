"""
generate_voice.py — 使用 edge-tts 生成配音 MP3，并使用 ffprobe 获取精确时长时间戳。

用法:
  python generate_voice.py script.json

输出:
  output/temp/voice.mp3          — 拼接后的完整音频
  output/temp/voice_timeline.json  — 每句开始/结束时间戳（毫秒精度）
"""

import json
import asyncio
import subprocess
import os
import sys
from pathlib import Path

# 从 config.json 读取配置
CONFIG_PATH = Path(__file__).parent.parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

VOICE     = CONFIG["voice"]["voice"]
RATE      = CONFIG["voice"]["rate"]
VOLUME    = CONFIG["voice"]["volume"]
FFPROBE   = CONFIG["ffmpeg"]["ffprobe_path"]
OUTPUT_DIR = Path(CONFIG["output"]["temp_dir"])
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_audio_duration(mp3_path: str) -> float:
    """用 ffprobe 获取 mp3 精确时长（秒，含小数）"""
    cmd = [
        FFPROBE, "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(mp3_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    # 优先取 streams[0].duration，其次 format.duration
    streams = data.get("streams", [])
    if streams and "duration" in streams[0]:
        return float(streams[0]["duration"])
    return float(data["format"]["duration"])


async def generate_one_mp3(text: str, out_path: Path) -> float:
    """生成单句 MP3，返回时长（秒）"""
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, volume=VOLUME)
    await communicate.save(str(out_path))
    duration = get_audio_duration(str(out_path))
    return duration


async def run(script_path: str):
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    scenes      = script["scenes"]
    timeline    = []
    current_ms  = 0.0          # 当前累计时间（秒）
    temp_files  = []              # 每句 mp3 路径，最后拼接

    for i, scene in enumerate(scenes):
        text = scene.get("voice_text", "").strip()
        if not text:
            continue

        out_mp3 = OUTPUT_DIR / f"voice_{scene['id']}.mp3"
        print(f"  [{i+1}/{len(scenes)}] '{text[:30]}...' ", end="", flush=True)

        duration = await generate_one_mp3(text, out_mp3)
        temp_files.append(str(out_mp3))

        start_s = current_ms
        end_s   = current_ms + duration
        timeline.append({
            "scene_id":  scene["id"],
            "start":     round(start_s, 3),
            "end":       round(end_s, 3),
            "text":      text,
            "audio_file": str(out_mp3)
        })
        print(f"{duration:.2f}s  ✓")

        current_ms = end_s + 0.4   # 句间停顿 0.4s

    # 拼接所有 mp3 成一个文件（ffmpeg concat demuxer）
    concat_file = OUTPUT_DIR / "concat_list.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for mp3 in temp_files:
            # 使用绝对路径避免 ffmpeg 相对路径解析问题
            abs_path = Path(mp3).resolve().as_posix()
            f.write(f"file '{abs_path}'\n")

    final_mp3 = OUTPUT_DIR / "voice.mp3"
    cmd = [
        CONFIG["ffmpeg"]["path"], "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy", str(final_mp3)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WARN] ffmpeg concat 失败，改用逐文件复制: {result.stderr[-500:]}")
        # fallback: 直接 copy 第一个文件（通常只有1句=1文件）
        import shutil
        shutil.copy(temp_files[0], str(final_mp3))
    print(f"\n✓ 配音合成完成: {final_mp3}  (总时长 {current_ms:.1f}s)")

    # 保存 timeline
    tl_path = OUTPUT_DIR / "voice_timeline.json"
    with open(tl_path, "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)
    print(f"✓ 时间戳已保存: {tl_path}")

    return str(final_mp3), str(tl_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python generate_voice.py <script.json>")
        sys.exit(1)
    asyncio.run(run(sys.argv[1]))
