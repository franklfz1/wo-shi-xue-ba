"""
generate_sfx.py — 用 Python (numpy + scipy) 生成音效文件。

生成以下音效:
  - whoosh.mp3   : 快速划过（片头入场）
  - pop.mp3      : 弹出提示（答案揭晓/关键点）
  - chime.mp3    : 清脆提示音（答对/总结）
  - thud.mp3     : 沉重低音（重点强调）
  - tick.mp3     : 倒计时滴答（思考/quiz）
  - swoosh.mp3   : 快速切换（场景过渡）

用法:
  python generate_sfx.py [--output assets/sfx/]
"""

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter
import subprocess
import sys
import os
from pathlib import Path


# ── 配置 ──────────────────────────────────────────────
SAMPLE_RATE = 44100
OUTPUT_DIR  = Path(__file__).parent.parent / "assets" / "sfx"
FFMPEG_PATH = "ffmpeg"


def _to_mp3(wav_path: str, mp3_path: str):
    """WAV 转 MP3 (高音质)"""
    subprocess.run([
        FFMPEG_PATH, "-y", "-i", wav_path,
        "-codec:a", "libmp3lame", "-b:a", "192k",
        "-ar", "44100", mp3_path
    ], capture_output=True, text=True)
    os.remove(wav_path)


def gen_whoosh(duration: float = 0.4) -> np.ndarray:
    """快速划过音效 — 白噪声 + 下行频率扫描"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # 白噪声
    noise = np.random.randn(len(t)) * 0.5
    # 包络 (快速起 -> 快速落)
    envelope = np.exp(-t * 8) * (1 - np.exp(-t * 60))
    # 带通滤波 (中高频)
    nyq = SAMPLE_RATE / 2
    b, a = butter(2, [2000 / nyq, 6000 / nyq], btype='band')
    filtered = lfilter(b, a, noise)
    return (filtered * envelope * 32767).astype(np.int16)


def gen_pop(duration: float = 0.15) -> np.ndarray:
    """弹出提示音 — 短促正弦波 + 快速衰减"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freq_sweep = 800 * np.exp(-t * 15)  # 频率快速下降
    phase = 2 * np.pi * np.cumsum(freq_sweep) / SAMPLE_RATE
    signal = np.sin(phase)
    envelope = np.exp(-t * 30)
    return (signal * envelope * 32767 * 0.8).astype(np.int16)


def gen_chime(duration: float = 0.6) -> np.ndarray:
    """清脆提示音 — 双音叠加 + 延迟回响"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # 主音 C5 = 523 Hz + E5 = 659 Hz (大三和弦)
    sig = 0.4 * np.sin(2 * np.pi * 523 * t) + 0.3 * np.sin(2 * np.pi * 659 * t)
    # 加一点泛音
    sig += 0.15 * np.sin(2 * np.pi * 1046 * t)
    # 包络
    envelope = np.exp(-t * 4) * (1 - np.exp(-t * 100))
    # 简单回响 (延迟 + 衰减)
    delay_samples = int(SAMPLE_RATE * 0.12)
    reverb = np.zeros_like(sig)
    reverb[delay_samples:] = sig[:-delay_samples] * 0.3
    sig = sig + reverb
    return (sig * envelope * 32767 * 0.7).astype(np.int16)


def gen_thud(duration: float = 0.3) -> np.ndarray:
    """沉重低音 — 低频正弦 + 快速衰减"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freq = 80 * np.exp(-t * 5)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    sig = np.sin(phase)
    envelope = np.exp(-t * 10) * (1 - np.exp(-t * 80))
    # 加一点失真感
    sig = np.tanh(sig * 3) * 0.5
    return (sig * envelope * 32767 * 0.9).astype(np.int16)


def gen_tick(duration: float = 0.08) -> np.ndarray:
    """倒计时滴答 — 高频短脉冲"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    sig = np.sin(2 * np.pi * 2000 * t)
    envelope = np.exp(-t * 50)
    return (sig * envelope * 32767 * 0.5).astype(np.int16)


def gen_swoosh(duration: float = 0.25) -> np.ndarray:
    """快速切换 — 噪声 + 高频共振"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    noise = np.random.randn(len(t)) * 0.3
    freq_mod = 4000 * np.exp(-t * 10)
    phase = 2 * np.pi * np.cumsum(freq_mod) / SAMPLE_RATE
    carrier = np.sin(phase)
    sig = noise * 0.5 + carrier * 0.5
    envelope = np.exp(-t * 15) * (1 - np.exp(-t * 80))
    return (sig * envelope * 32767 * 0.6).astype(np.int16)


def gen_success(duration: float = 0.8) -> np.ndarray:
    """成功音效 — 上升琶音 C-E-G-C"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    notes = [523, 659, 784, 1046]  # C5, E5, G5, C6
    sig = np.zeros_like(t)
    for i, note in enumerate(notes):
        onset = i * 0.12
        dur = duration - onset
        if dur <= 0:
            continue
        mask = t >= onset
        local_t = t[mask] - onset
        note_env = np.exp(-local_t * 5) * (1 - np.exp(-local_t * 100))
        sig[mask] += 0.3 * np.sin(2 * np.pi * note * local_t) * note_env
    return (sig * 32767 * 0.6).astype(np.int16)


def gen_wrong(duration: float = 0.5) -> np.ndarray:
    """错误音效 — 下行两个音 (降调)"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    sig = np.zeros_like(t)
    notes = [400, 300]  # 下行
    for i, note in enumerate(notes):
        onset = i * 0.2
        mask = t >= onset
        local_t = t[mask] - onset
        note_env = np.exp(-local_t * 6) * (1 - np.exp(-local_t * 80))
        sig[mask] += 0.4 * np.sin(2 * np.pi * note * local_t) * note_env
    return (sig * 32767 * 0.6).astype(np.int16)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 检查 scipy 是否可用
    try:
        import scipy
    except ImportError:
        print("[ERROR] 需要 scipy: pip install scipy numpy")
        sys.exit(1)

    effects = {
        "whoosh": gen_whoosh,
        "pop": gen_pop,
        "chime": gen_chime,
        "thud": gen_thud,
        "tick": gen_tick,
        "swoosh": gen_swoosh,
        "success": gen_success,
        "wrong": gen_wrong,
    }

    print("=== 生成音效 ===")
    for name, gen_fn in effects.items():
        wav_path = str(OUTPUT_DIR / f"{name}.wav")
        mp3_path = str(OUTPUT_DIR / f"{name}.mp3")
        data = gen_fn()
        wavfile.write(wav_path, SAMPLE_RATE, data)
        _to_mp3(wav_path, mp3_path)
        size = os.path.getsize(mp3_path) / 1024
        print(f"  ✓ {name}.mp3  ({size:.1f} KB)")

    print(f"\n✓ 音效生成完成: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
