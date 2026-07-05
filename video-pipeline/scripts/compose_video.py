"""
compose_video.py — 使用 ffmpeg 合成最终竖屏 MP4 视频（增强版）。

流程:
  1. 把静态画面 frames/ 目录下的 PNG 合成基础无声视频
  2. 把配音 voice.mp3 合并进去
  3. 在指定时间点叠加音效 (SFX)
  4. 输出竖屏 1080x1920 H.264 MP4

用法:
  python compose_video.py <frames_dir> <audio_file> [--subtitle <srt_file>] \
                          [--sfx <sfx_events_json>] [--output <out.mp4>]

SFX events JSON 格式:
  [
    {"time": 0.0, "file": "assets/sfx/whoosh.mp3", "volume": 0.5},
    {"time": 5.2, "file": "assets/sfx/pop.mp3", "volume": 0.7},
    ...
  ]
"""

import json
import subprocess
import sys
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

FFMPEG    = CONFIG["ffmpeg"]["path"]
W         = CONFIG["video"]["width"]    # 1080
H         = CONFIG["video"]["height"]   # 1920
FPS       = CONFIG["video"]["fps"]       # 30
CODEC     = CONFIG["video"]["codec"]     # libx264
PIX_FMT   = CONFIG["video"]["pix_fmt"]  # yuv420p
BITRATE   = CONFIG["video"]["bitrate"]  # 2M
A_CODEC   = CONFIG["video"]["audio_codec"]
A_BITRATE = CONFIG["video"]["audio_bitrate"]

BASE_DIR = Path(__file__).parent.parent


def mix_sfx_into_audio(audio_file: str, sfx_events: list, output_file: str):
    """
    把音效事件混合到配音音频中。

    方法:
      1. 对每个 sfx 事件，用 ffmpeg 的 adelay 滤镜在指定时间点插入
      2. 用 ffmpeg amix 滤镜把所有音轨混合在一起
    """
    if not sfx_events:
        # 没有音效，直接复制
        import shutil
        shutil.copy(audio_file, output_file)
        return output_file

    temp_dir = Path(output_file).parent / "_sfx_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 为每个 sfx 生成延迟后的音频文件
    delayed_files = []
    for i, evt in enumerate(sfx_events):
        time_s  = evt.get("time", 0)
        sfx_src = evt.get("file", "")
        volume  = evt.get("volume", 0.5)

        if not sfx_src or not Path(sfx_src).exists():
            print(f"  [WARN] 音效文件不存在: {sfx_src}")
            continue

        # 绝对路径
        sfx_abs = str(Path(sfx_src).resolve())
        delay_ms = int(time_s * 1000)

        delayed_file = temp_dir / f"delayed_{i:03d}.mp3"

        cmd = [
            FFMPEG, "-y",
            "-i", sfx_abs,
            "-filter_complex",
            f"[0:a]adelay={delay_ms}|{delay_ms},volume={volume}[a]",
            "-map", "[a]",
            "-c:a", "libmp3lame", "-b:a", "192k",
            str(delayed_file)
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  [WARN] 音效延迟失败 (t={time_s}s): {r.stderr[-200:]}")
            continue

        delayed_files.append(str(delayed_file))

    if not delayed_files:
        import shutil
        shutil.copy(audio_file, output_file)
        return output_file

    # 构建混合命令: voice + sfx1 + sfx2 + ...
    # 用 -filter_complex amix 滤镜
    inputs = ["-i", str(Path(audio_file).resolve())]
    for df in delayed_files:
        inputs += ["-i", df]

    n_inputs = len(delayed_files) + 1  # voice + sfx tracks
    input_labels = "".join(f"[{i}:a]" for i in range(n_inputs))

    # amix 滤镜: 所有音轨混合，配音优先
    filter_str = f"{input_labels}amix=inputs={n_inputs}:duration=longest:dropout_transition=0[aout]"

    cmd = [
        FFMPEG, "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[aout]",
        "-c:a", "aac", "-b:a", A_BITRATE,
        str(output_file)
    ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [WARN] 音效混合失败，使用原始音频: {r.stderr[-500:]}")
        import shutil
        shutil.copy(audio_file, output_file)
    else:
        print(f"  ✓ 已混合 {len(delayed_files)} 个音效")

    # 清理临时文件
    for df in delayed_files:
        try:
            os.remove(df)
        except:
            pass
    try:
        temp_dir.rmdir()
    except:
        pass

    return output_file


def compose(frames_dir: str, audio_file: str, output_file: str,
            subtitle_file: str = None, sfx_events: list = None):
    """合成视频（增强版：支持音效混合）"""
    frames_path = Path(frames_dir)
    audio_path  = Path(audio_file)
    out_path    = Path(output_file)

    # 检查帧文件
    frame_files = sorted(frames_path.glob("frame_*.png"))
    if not frame_files:
        # 也检查 svg_frame_*.png（SVG 动画帧）
        frame_files = sorted(frames_path.glob("svg_frame_*.png"))
        if not frame_files:
            print(f"[ERROR] 目录 {frames_dir} 中没有帧文件")
            sys.exit(1)
        frame_pattern = "svg_frame_%04d.png"
    else:
        frame_pattern = "frame_%04d.png"

    # ── Step 0: 混合音效到配音 ──
    mixed_audio = audio_file  # 默认使用原始配音
    if sfx_events:
        print(f"[0/3] 混合音效 ({len(sfx_events)} 个)...")
        mixed_audio_temp = str(out_path.with_suffix("")) + "_mixed.mp3"
        mixed_audio = mix_sfx_into_audio(audio_file, sfx_events, mixed_audio_temp)

    # ── Step 1: frames/*.png → 无声视频 ──
    print(f"[1/3] 合成无声视频... ({len(frame_files)} 帧)")
    silent_video = str(out_path.with_suffix("")) + "_novoice.mp4"

    cmd1 = [
        FFMPEG, "-y",
        "-framerate", str(FPS),
        "-i", str(frames_path / frame_pattern),
        "-c:v", CODEC,
        "-b:v", BITRATE,
        "-pix_fmt", PIX_FMT,
        str(silent_video)
    ]
    r1 = subprocess.run(cmd1, capture_output=True, text=True)
    if r1.returncode != 0:
        print(f"[ERROR] 合成失败:\n{r1.stderr[-2000:]}")
        sys.exit(1)
    print(f"  → {silent_video}")

    # ── Step 2: 加入音频 ──
    print(f"[2/3] 合并音频...")
    video_with_audio = str(out_path.with_suffix("")) + "_withaudio.mp4"

    cmd2 = [
        FFMPEG, "-y",
        "-i", silent_video,
        "-i", str(Path(mixed_audio).resolve()),
        "-c:v", "copy",
        "-c:a", A_CODEC,
        "-b:a", A_BITRATE,
        "-shortest",
        str(video_with_audio)
    ]
    r2 = subprocess.run(cmd2, capture_output=True, text=True)
    if r2.returncode != 0:
        print(f"[ERROR] 音频合并失败:\n{r2.stderr[-2000:]}")
        sys.exit(1)
    print(f"  → {video_with_audio}")

    # ── Step 3: 添加字幕 ──
    if subtitle_file and Path(subtitle_file).exists():
        print(f"[3/3] 添加字幕...")
        sub_style = CONFIG["subtitle"]
        force_style = (
            f"FontName={sub_style['font']},"
            f"FontSize={sub_style['size']},"
            f"PrimaryColour={sub_style['color']},"
            f"OutlineColour={sub_style['outline_color']},"
            f"Outline={sub_style['outline_width']},"
            f"Bold={sub_style['bold']},"
            f"Italic={sub_style['italic']},"
            f"Alignment={sub_style['alignment']}"
        )
        vf = f"subtitles={subtitle_file}:force_style='{force_style}'"
        cmd3 = [
            FFMPEG, "-y",
            "-i", video_with_audio,
            "-vf", vf,
            "-c:v", CODEC,
            "-c:a", "copy",
            str(out_path)
        ]
        r3 = subprocess.run(cmd3, capture_output=True, text=True)
        if r3.returncode != 0:
            print(f"[WARN] 字幕失败，保留无字幕版:\n{r3.stderr[-1000:]}")
            import shutil
            shutil.copy(video_with_audio, out_path)
        else:
            print(f"  → {out_path}")
    else:
        import shutil
        shutil.copy(video_with_audio, out_path)
        print(f"  → {out_path} (无字幕)")

    # 清理中间文件
    for f in [silent_video, video_with_audio]:
        try:
            os.remove(f)
        except:
            pass
    if mixed_audio != audio_file:
        try:
            os.remove(mixed_audio)
        except:
            pass

    print(f"\n✓ 最终视频: {out_path}")
    return str(out_path)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python compose_video.py <frames_dir> <audio_file> [--subtitle <srt>] [--sfx <events.json>] [--output <out.mp4>]")
        sys.exit(1)

    frames_dir  = sys.argv[1]
    audio_file = sys.argv[2]
    subtitle   = None
    sfx_file   = None
    output     = "output/final_video.mp4"

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--subtitle" and i + 1 < len(sys.argv):
            subtitle = sys.argv[i + 1]; i += 2
        elif sys.argv[i] == "--sfx" and i + 1 < len(sys.argv):
            sfx_file = sys.argv[i + 1]; i += 2
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            output = sys.argv[i + 1]; i += 2
        else:
            i += 1

    sfx_events = []
    if sfx_file and Path(sfx_file).exists():
        with open(sfx_file, "r", encoding="utf-8") as f:
            sfx_events = json.load(f)

    compose(frames_dir, audio_file, output, subtitle, sfx_events)
