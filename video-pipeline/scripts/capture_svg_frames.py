"""
capture_svg_frames.py — 从 HTML 文件捕获 SVG 组装动画帧为 PNG 序列。

流程:
  1. 读取 SVG 组装动画 HTML 文件
  2. 用 Playwright 打开页面，逐帧捕获
  3. 输出 PNG 序列帧到指定目录

用法:
  python capture_svg_frames.py --html animation.html --output frames/ --duration 3.5 --fps 30

依赖: pip install playwright && python -m playwright install chromium
"""

import json
import sys
import argparse
from pathlib import Path
import subprocess


def capture_frames(html_path: str, output_dir: str, duration: float, fps: int,
                    width: int = 1080, height: int = 1920, capture_after: float = 0.0):
    """
    用 Playwright 捕获 HTML 动画帧。

    Args:
        html_path: HTML 文件路径
        output_dir: 输出 PNG 目录
        duration: 动画总时长（秒）
        fps: 帧率
        width: 捕获宽度
        height: 捕获高度
        capture_after: 页面加载后等待时间（秒），用于预加载动画
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    total_frames = int(duration * fps)
    interval_ms = 1000 / fps

    # 用绝对路径避免路径问题
    abs_html = str(Path(html_path).resolve())

    # 生成 Playwright 捕获脚本
    js_code = f"""
const fs = require('fs');
const path = require('path');

(async () => {{
    const {{ chromium }} = require('playwright');

    const browser = await chromium.launch({{ headless: true }});
    const page = await browser.newPage({{
        viewport: {{ width: {width}, height: {height} }}
    }});

    await page.goto('file:///{abs_html.replace(/\\\\/g, "/")}');

    // 等待页面完全加载
    await page.waitForTimeout({int(capture_after * 1000)});

    // 如果页面有 GSAP 动画，先触发播放
    try {{
        await page.evaluate(() => {{
            // 查找并点击重播按钮（如果有的话）
            const replayBtn = document.querySelector('[data-action="replay"]') ||
                              document.querySelector('.replay-btn');
            if (replayBtn) replayBtn.click();
        }});
        await page.waitForTimeout(100);
    }} catch(e) {{ console.log('No replay button found, animation may auto-play'); }}

    const totalFrames = {total_frames};
    const intervalMs = {interval_ms};
    const outputDir = '{str(output_path).replace(/\\\\/g, "/")}';

    for (let i = 0; i < totalFrames; i++) {{
        // 等待到指定时间点
        await page.waitForTimeout(intervalMs);

        // 捕获截图
        const padded = String(i).padStart(4, '0');
        const screenshotPath = path.join(outputDir, `svg_frame_${{padded}}.png`);
        await page.screenshot({{
            path: screenshotPath,
            type: 'png'
        }});

        if (i % 30 === 0) {{
            console.log(`  ...captured ${{i + 1}}/${{totalFrames}} frames`);
        }}
    }}

    console.log(`  ✓ Total ${{totalFrames}} frames captured`);
    await browser.close();
}})();
"""

    # 写入临时 JS 文件并执行
    tmp_js = Path(output_dir) / "_capture.js"
    with open(tmp_js, "w", encoding="utf-8") as f:
        f.write(js_code)

    result = subprocess.run(
        ["node", str(tmp_js)],
        capture_output=True, text=True,
        timeout=max(300, total_frames * 0.05)  # 超时保护
    )

    # 清理临时 JS
    try:
        tmp_js.unlink()
    except:
        pass

    if result.returncode != 0:
        print(f"[ERROR] Playwright 捕获失败:")
        print(result.stderr[-2000:])
        sys.exit(1)

    print(result.stdout)

    # 验证帧文件
    frames = sorted(output_path.glob("svg_frame_*.png"))
    print(f"  ✓ 捕获完成: {len(frames)} 帧 → {output_dir}")
    return output_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", required=True, help="SVG 动画 HTML 文件")
    parser.add_argument("--output", required=True, help="输出帧目录")
    parser.add_argument("--duration", type=float, default=3.5, help="动画时长（秒）")
    parser.add_argument("--fps", type=int, default=30, help="帧率")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--wait", type=float, default=0.5, help="页面加载后等待时间")
    args = parser.parse_args()

    capture_frames(args.html, args.output, args.duration, args.fps,
                   args.width, args.height, args.wait)
