"""
我是学霸 — 数据管理 API
=========================
所有学习数据统一读写入口。
前端 dashboard.html 通过 fetch() 调用本服务，避免跨域限制。

启动方式：python data_api.py
默认监听 http://localhost:5177
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

# ============ 路径配置（支持自定义） ============
# 优先使用环境变量，否则自动检测脚本同级目录
_BASE_DIR_ENV = os.environ.get("STUDYBUDDY_DIR")
if _BASE_DIR_ENV:
    BASE_DIR = Path(_BASE_DIR_ENV)
else:
    # 自动指向脚本所在目录
    BASE_DIR = Path(__file__).parent.resolve()
NEXT_REVIEW_PATH = BASE_DIR / "review" / "next-review.json"
ERRORS_REVIEW_PATH = BASE_DIR / "review" / "errors-review.json"
RECORDS_DIR = BASE_DIR / "records"

# ============ 艾宾浩斯配置 ============
REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30]  # 6轮复习间隔
ERROR_REVIEW_INTERVALS = [1, 2, 3, 5, 7]   # 错题复习：5轮

# ============ Flask App ============
app = Flask(__name__)
CORS(app)

# ============ 辅助函数 ============

def load_json(path):
    """安全加载 JSON 文件"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] 读取 {path} 失败: {e}")
        return None


def append_review_log(subject, topic, round_completed, next_date, source="review"):
    """追加复习日志到 review-log.md"""
    log_path = RECORDS_DIR / subject / "review-log.md"
    label = "知识点复习" if source == "review" else "错题复习"
    line = f"| {today_str()} | {topic}（{label}·第{round_completed}轮） | 好 | {next_date or '（已完成全部轮次）'} |\n"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
        return True
    except Exception as e:
        print(f"[WARN] 写入复习日志失败: {e}")
        return False


def save_json(path, data):
    """安全写入 JSON 文件"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] 写入 {path} 失败: {e}")
        return False


def parse_mastered_from_md(filepath):
    """从 mastered.md 提取所有 ✅ 已掌握的知识点"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        # 匹配 ✅ 开头的行，去掉标记后提取知识点名称
        items = []
        for line in content.split("\n"):
            stripped = line.strip()
            # 匹配列表项行（- ✅ 开头），提取已掌握知识点
            if stripped.startswith("- ✅"):
                # 去掉列表标记和 emoji，保留知识点名称
                topic = stripped[2:].strip()          # 去掉 "-"
                topic = re.sub(r"^[^\u4e00-\u9fa5a-zA-Z0-9]+", "", topic).strip()
                if topic:
                    items.append(topic)
        return items
    except FileNotFoundError:
        return []


def parse_errors_from_md(filepath):
    """从 errors.md 提取错题记录"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        records = []
        # 按 ## YYYY-MM-DD 分割
        sections = re.split(r"(?=## \d{4}-\d{2}-\d{2})", content)
        for section in sections:
            if not section.strip() or "## " not in section:
                continue
            date_match = re.search(r"## (\d{4}-\d{2}-\d{2})", section)
            if not date_match:
                continue
            err_date = date_match.group(1)
            # 提取题目
            topic_match = re.search(r"\*\*题目：\*\*(.+)", section)
            my_ans_match = re.search(r"\*\*我的错误答案：\*\*(.+)", section)
            correct_match = re.search(r"\*\*正确答案：\*\*(.+)", section)
            reason_match = re.search(r"\*\*错误原因：\*\*(.+)", section)
            point_match = re.search(r"\*\*知识点：\*\*(.+)", section)
            notes_match = re.search(r"\*\*备注：\*\*(.+)", section)
            records.append({
                "date": err_date,
                "question": topic_match.group(1).strip() if topic_match else "",
                "myAnswer": my_ans_match.group(1).strip() if my_ans_match else "",
                "correctAnswer": correct_match.group(1).strip() if correct_match else "",
                "reason": reason_match.group(1).strip() if reason_match else "",
                "knowledgePoint": point_match.group(1).strip() if point_match else "",
                "notes": notes_match.group(1).strip() if notes_match else "",
            })
        return records
    except FileNotFoundError:
        return []


def today_str():
    return date.today().isoformat()


def get_subject_mastered(subject):
    """获取某科目所有已掌握知识点"""
    filepath = RECORDS_DIR / subject / "mastered.md"
    return parse_mastered_from_md(filepath)


def get_subject_errors(subject):
    """获取某科目所有错题"""
    filepath = RECORDS_DIR / subject / "errors.md"
    return parse_errors_from_md(filepath)


# ============ 路由 ============

@app.route("/")
def index():
    """返回 dashboard.html"""
    return send_from_directory(BASE_DIR, "dashboard.html")


@app.route("/api/status")
def api_status():
    """系统状态检查"""
    return jsonify({
        "ok": True,
        "baseDir": str(BASE_DIR),
        "today": today_str()
    })


@app.route("/api/dashboard")
def api_dashboard():
    """
    获取看板全量数据（供 dashboard.html 渲染用）
    合并 next-review.json + 各科 mastered.md + errors.md
    """
    next_review = load_json(NEXT_REVIEW_PATH) or {"reviewItems": []}
    errors_review = load_json(ERRORS_REVIEW_PATH) or {"reviewItems": []}

    today = today_str()

    # 各科已掌握数量
    subjects = ["chinese", "math", "english", "science", "geography", "physics"]
    subject_labels = {
        "chinese": "语文",
        "math": "数学",
        "english": "英语",
        "science": "科学",
        "geography": "地理",
        "physics": "物理",
    }

    subject_data = {}
    total_mastered = 0
    total_errors = 0
    total_mastered_by_subject = {}

    for subj in subjects:
        mastered = get_subject_mastered(subj)
        errors = get_subject_errors(subj)
        mastered_count = len(mastered)
        errors_count = len(errors)
        total_mastered += mastered_count
        total_errors += errors_count
        total_mastered_by_subject[subj] = mastered_count
        subject_data[subj] = {
            "label": subject_labels[subj],
            "mastered": mastered,
            "masteredCount": mastered_count,
            "errors": errors,
            "errorsCount": errors_count,
        }

    # 今日到期复习项（普通知识点）
    due_items = [
        item for item in next_review.get("reviewItems", [])
        if item.get("nextReviewDate", "") == today
    ]

    # 今日到期错题复习
    due_errors = [
        item for item in errors_review.get("reviewItems", [])
        if item.get("nextReviewDate", "") == today
    ]

    # 估算总知识点数（小学阶段：每科约30-40个知识点）
    estimated_total = {
        "chinese": 35,
        "math": 40,
        "english": 30,
        "science": 30,
        "geography": 25,
        "physics": 65,
    }

    return jsonify({
        "today": today,
        "overview": {
            "totalMastered": total_mastered,
            "totalErrors": total_errors,
            "totalDueToday": len(due_items) + len(due_errors),
        },
        "subjects": subject_data,
        "estimatedTotal": estimated_total,
        "dueReviews": due_items,
        "dueErrors": due_errors,
        "reviewItems": next_review.get("reviewItems", []),
        "errorsReviewItems": errors_review.get("reviewItems", []),
    })


@app.route("/api/complete-review", methods=["POST"])
def api_complete_review():
    """
    完成一次知识点复习
    Body: { "subject": "math", "topic": "...", "source": "review" | "error" }
    自动推进艾宾浩斯轮次
    """
    body = request.get_json()
    subject = body.get("subject")
    topic = body.get("topic")
    source = body.get("source", "review")  # "review" 或 "error"

    if source == "review":
        review_file = NEXT_REVIEW_PATH
        intervals = REVIEW_INTERVALS
    else:
        review_file = ERRORS_REVIEW_PATH
        intervals = ERROR_REVIEW_INTERVALS

    data = load_json(review_file)
    if data is None:
        return jsonify({"ok": False, "error": "文件加载失败"}), 500

    # 找到对应项
    found = False
    for item in data.get("reviewItems", []):
        if item.get("subject") == subject and item.get("topic") == topic:
            current_round = item.get("reviewRound", 0)
            max_round = len(intervals)

            if current_round >= max_round:
                # 已完成全部复习轮次，从列表移除（或标记为 done）
                item["status"] = "done"
                item["nextReviewDate"] = None
                item["completedAt"] = today_str()
            else:
                # 推进到下一轮
                next_interval = intervals[current_round]
                next_date = (date.today() + timedelta(days=next_interval)).isoformat()
                item["reviewRound"] = current_round + 1
                item["nextReviewDate"] = next_date
                item["lastReviewDate"] = today_str()
                item["status"] = "pending"

            found = True
            next_review = item.get("nextReviewDate")
            next_round = item.get("reviewRound")
            break

    if not found:
        return jsonify({"ok": False, "error": f"未找到：{subject} - {topic}"}), 404

    # 记录到复习日志
    append_review_log(subject, topic, item.get("reviewRound", 1), item.get("nextReviewDate"), source)
    next_review = item.get("nextReviewDate")
    next_round = item.get("reviewRound")

    if save_json(review_file, data):
        return jsonify({
            "ok": True,
            "subject": subject,
            "topic": topic,
            "newRound": next_round,
            "nextReviewDate": next_review,
            "completed": next_review is None,
        })
    else:
        return jsonify({"ok": False, "error": "保存失败"}), 500


@app.route("/api/add-error", methods=["POST"])
def api_add_error():
    """
    添加一条错题记录（同时建立独立复习计划）
    Body: { "subject": "math", "question": "...", "myAnswer": "...", "correctAnswer": "...", "reason": "...", "knowledgePoint": "...", "notes": "..." }
    """
    body = request.get_json()
    subject = body.get("subject")
    err_record = {
        "date": today_str(),
        "question": body.get("question", ""),
        "myAnswer": body.get("myAnswer", ""),
        "correctAnswer": body.get("correctAnswer", ""),
        "reason": body.get("reason", ""),
        "knowledgePoint": body.get("knowledgePoint", ""),
        "notes": body.get("notes", ""),
    }

    # 写入 errors.md
    err_md_path = RECORDS_DIR / subject / "errors.md"
    entry_lines = [
        "---",
        f"## {today_str()} {err_record['knowledgePoint']}",
        f"**题目：** {err_record['question']}",
        f"**我的错误答案：** {err_record['myAnswer']}",
        f"**正确答案：** {err_record['correctAnswer']}",
        f"**错误原因：** {err_record['reason']}",
        f"**知识点：** {err_record['knowledgePoint']}",
    ]
    if err_record["notes"]:
        entry_lines.append(f"**备注：** {err_record['notes']}")

    try:
        with open(err_md_path, "a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(entry_lines) + "\n")
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    # 建立错题复习计划（加入 errors-review.json）
    first_interval = ERROR_REVIEW_INTERVALS[0]
    errors_data = load_json(ERRORS_REVIEW_PATH) or {
        "reviewIntervals": ERROR_REVIEW_INTERVALS,
        "description": "错题本艾宾浩斯复习间隔",
        "reviewItems": []
    }

    new_review_item = {
        "subject": subject,
        "knowledgePoint": err_record["knowledgePoint"],
        "question": err_record["question"],
        "correctAnswer": err_record["correctAnswer"],
        "errorDate": today_str(),
        "nextReviewDate": (date.today() + timedelta(days=first_interval)).isoformat(),
        "reviewRound": 1,
        "status": "pending",
    }

    errors_data["reviewItems"].append(new_review_item)
    save_json(ERRORS_REVIEW_PATH, errors_data)

    return jsonify({
        "ok": True,
        "item": new_review_item,
    })


@app.route("/api/add-mastered", methods=["POST"])
def api_add_mastered():
    """
    标记一个知识点为已掌握（加入 mastered.md，同时建立复习计划）
    Body: { "subject": "math", "topic": "..." }
    """
    body = request.get_json()
    subject = body.get("subject")
    topic = body.get("topic")

    # 追加到 mastered.md
    mastered_path = RECORDS_DIR / subject / "mastered.md"
    line = f"- ✅ {topic}\n"

    try:
        with open(mastered_path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    # 加入 next-review.json 复习计划
    review_data = load_json(NEXT_REVIEW_PATH) or {
        "reviewIntervals": REVIEW_INTERVALS,
        "description": "艾宾浩斯复习间隔（单位：天）",
        "subjects": ["chinese", "math", "english", "science", "geography", "physics"],
        "reviewItems": []
    }

    first_interval = REVIEW_INTERVALS[0]
    new_item = {
        "subject": subject,
        "topic": topic,
        "learnedDate": today_str(),
        "nextReviewDate": (date.today() + timedelta(days=first_interval)).isoformat(),
        "reviewRound": 1,
        "status": "pending",
    }

    review_data["reviewItems"].append(new_item)
    save_json(NEXT_REVIEW_PATH, review_data)

    return jsonify({
        "ok": True,
        "item": new_item,
    })


@app.route("/api/next-review-json")
def api_next_review_json():
    """直接返回 next-review.json 内容"""
    data = load_json(NEXT_REVIEW_PATH)
    if data is None:
        return jsonify({"reviewItems": []})
    return jsonify(data)


@app.route("/api/errors-review-json")
def api_errors_review_json():
    """直接返回 errors-review.json 内容"""
    data = load_json(ERRORS_REVIEW_PATH)
    if data is None:
        return jsonify({"reviewItems": []})
    return jsonify(data)


# ============ 启动 ============
if __name__ == "__main__":
    print("=" * 50)
    print("我是学霸 - 数据管理 API")
    print(f"数据目录: {BASE_DIR}")
    print(f"今日日期: {today_str()}")
    print("=" * 50)
    print("服务已就绪...")
    print("   看板: http://localhost:5177/")
    print("   API:  http://localhost:5177/api/status")
    print("=" * 50)
    import webbrowser, threading
    def _open_browser():
        webbrowser.open("http://localhost:5177/")
    threading.Timer(1.2, _open_browser).start()
    app.run(host="127.0.0.1", port=5177, debug=True)
