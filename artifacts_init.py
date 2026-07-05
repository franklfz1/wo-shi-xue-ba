#!/usr/bin/env python3
"""
教学产物目录初始化工具
用法：
  python artifacts_init.py                          # 初始化全部四科
  python artifacts_init.py --subject 历史            # 新增学科
  python artifacts_init.py --subject 数学 --date 2025-01-15  # 查看某科某日的产物路径
"""

import argparse
import os
import sys
from datetime import date
from pathlib import Path

# 修复 Windows GBK 终端编码问题
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 项目根目录（脚本所在目录的上级）
PROJECT_ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

# 默认学科（含 other 用于跨学科/未归类产物）
DEFAULT_SUBJECTS = ["math", "chinese", "english", "science", "other"]

# 学科中英文映射
SUBJECT_NAMES = {
    "math": "数学",
    "chinese": "语文",
    "english": "英语",
    "science": "科学",
    "other": "其他/跨学科",
}

# 产物类型
ARTIFACT_TYPES = ["images", "videos", "audio", "html", "other"]


def init_subject(subject_key: str) -> None:
    """为指定学科创建产物目录结构"""
    subject_dir = ARTIFACTS_DIR / subject_key
    for atype in ARTIFACT_TYPES:
        (subject_dir / atype).mkdir(parents=True, exist_ok=True)
    cn_name = SUBJECT_NAMES.get(subject_key, subject_key)
    print(f"  ✅ {subject_key}（{cn_name}）目录就绪")


def init_all() -> None:
    """初始化全部默认学科"""
    print("🚀 初始化教学产物目录...")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    for subj in DEFAULT_SUBJECTS:
        init_subject(subj)
    print(f"\n📂 产物根目录：{ARTIFACTS_DIR}")


def get_artifact_path(subject: str, artifact_type: str, filename: str,
                      date_str: str = None) -> Path:
    """
    生成标准化的产物路径

    Args:
        subject: 学科键名（math/chinese/english/science）
        artifact_type: 产物类型（images/videos/audio/html/other）
        filename: 文件描述（不含日期前缀和扩展名也可以）
        date_str: 日期字符串，默认今天

    Returns:
        完整的产物文件路径

    示例：
        >>> get_artifact_path("chinese", "images", "登鹳雀楼水墨画.png")
        artifacts/chinese/images/2025-01-15_登鹳雀楼水墨画.png
    """
    if date_str is None:
        date_str = date.today().isoformat()

    # 如果文件名已有日期前缀则不重复添加
    if not filename.startswith(date_str):
        filename = f"{date_str}_{filename}"

    return ARTIFACTS_DIR / subject / artifact_type / filename


def list_artifacts(subject: str = None, date_str: str = None) -> None:
    """列出已有的教学产物"""
    if subject:
        subjects = [subject]
    else:
        subjects = DEFAULT_SUBJECTS

    for subj in subjects:
        subj_dir = ARTIFACTS_DIR / subj
        if not subj_dir.exists():
            continue
        cn_name = SUBJECT_NAMES.get(subj, subj)
        print(f"\n📚 {subj}（{cn_name}）：")
        for atype in ARTIFACT_TYPES:
            type_dir = subj_dir / atype
            if not type_dir.exists():
                continue
            files = sorted(type_dir.iterdir()) if type_dir.exists() else []
            # 按日期过滤
            if date_str:
                files = [f for f in files if f.name.startswith(date_str)]
            if files:
                print(f"  {atype}/")
                for f in files:
                    size_kb = f.stat().st_size / 1024
                    print(f"    {f.name}  ({size_kb:.0f} KB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="教学产物目录初始化工具")
    parser.add_argument("--subject", "-s", help="指定学科（英文键名或中文名）")
    parser.add_argument("--date", "-d", help="指定日期（YYYY-MM-DD格式）")
    parser.add_argument("--list", "-l", action="store_true", help="列出已有产物")
    parser.add_argument("--init", action="store_true", help="初始化目录结构")

    args = parser.parse_args()

    # 中文→英文映射
    cn_to_en = {v: k for k, v in SUBJECT_NAMES.items()}
    subject = args.subject
    if subject in cn_to_en:
        subject = cn_to_en[subject]

    if args.init or (not args.list and not args.subject):
        init_all()

    if args.subject and not args.list:
        init_subject(args.subject)
        # 更新中文映射
        SUBJECT_NAMES[args.subject] = args.subject

    if args.list:
        list_artifacts(subject, args.date)
