#!/usr/bin/env python3
"""
「我是学霸」练习题生成引擎

功能：
- 按学习进度（progress模式）为各学科出题
- 数学：从 question-bank 题库选取（100%准确）
- 其他学科：AI 实时生成（标记需核对）
- 输出：自包含 HTML 文件，支持 A4/A3 打印
- 内置答案切换 + 导出 PDF 按钮

使用方法：
    python exercise_engine.py                     # 为所有学科各生成一份练习题
    python exercise_engine.py --subject math      # 只生成数学
    python exercise_engine.py --count 10          # 每题10道（默认8道）
    python exercise_engine.py --paper A3          # A3 纸张（默认 A4）
"""

import base64
import json
import random
import re
import sys
from datetime import datetime
from pathlib import Path

# ============================================================
# 配置
# ============================================================

# 自动检测项目根目录：优先 __file__ 所在目录，若找不到 records/ 则向上查找
_initial_dir = Path(__file__).resolve().parent
BASE_DIR = _initial_dir
for _d in [_initial_dir] + list(_initial_dir.parents):
    if (_d / "records").exists() and (_d / "question-bank").exists():
        BASE_DIR = _d
        break
RECORDS_DIR = BASE_DIR / "records"
QUESTION_BANK_DIR = BASE_DIR / "question-bank"
OUTPUT_DIR = BASE_DIR / "artifacts" / "exercises"

SUBJECTS = ["math", "chinese", "english", "science", "geography", "physics"]
SUBJECT_NAMES = {
    "math": "数学",
    "chinese": "语文",
    "english": "英语",
    "science": "科学",
    "geography": "地理",
    "physics": "物理",
}

DEFAULT_COUNT = 8
DEFAULT_PAPER = "A4"


# ============================================================
# 图片加载（base64 编码用于自包含 HTML）
# ============================================================

def render_math(text) -> str:
    """
    将题目文本中的常见数学表达式转换为 KaTeX LaTeX 格式。
    输入可能是 int（题库 answer 字段），需先转 str。
    """
    if text is None:
        return ""
    text = str(text)

    # 已有的 LaTeX 不动
    result = text

    # 1) 带分数：数字又数字/数字 → 混合数
    # 例：3又3/5、37cm=（ ）dm 中的 3又3/5
    def replace_mixed(m):
        whole = m.group(1)
        num = m.group(2)
        den = m.group(3)
        return "$" + whole + "\\frac{" + num + "}{" + den + "}$"
    result = re.sub(r'(\d+)又(\d+)/(\d+)', replace_mixed, result)

    # 2) 简单分数：不含"又"的 数字/数字，但排除：
    #   - 已经在 $$ 内的
    #   - URL/路径中的 /
    #   - 大于等于100的分子分母（可能是页码等）
    def replace_frac(m):
        num = m.group(1)
        den = m.group(2)
        # 排除明显非分数的情况
        if int(num) >= 100 or int(den) >= 100:
            return m.group(0)
        return "$\\frac{" + num + "}{" + den + "}$"

    # 保护已有的 $$...$$ 块
    protected = []
    def protect_latex(m):
        protected.append(m.group(0))
        return f"\x00PROTECTED{len(protected)-1}\x00"

    result = re.sub(r'\$\$[^$]+\$\$', protect_latex, result)

    # 应用分数转换
    result = re.sub(r'(?<![0-9a-zA-Z\u4e00-\u9fff又/])'  # 前面不能有这些
                     r'(\d+)/(\d+)'
                     r'(?![0-9/])', replace_frac, result)

    # 恢复保护的块
    for i, block in enumerate(protected):
        result = result.replace(f"\x00PROTECTED{i}\x00", block)

    return result


def load_image_base64(question: dict) -> str:
    """
    从题目的 image 字段加载图片并返回 base64 编码字符串。
    image 字段可能是：
    - 相对于项目根目录的路径（如 'question-bank/math/grade-5/textbook/images/xxx.png'）
    - 相对于题库目录的路径（如 'images/xxx.png'）
    返回空字符串如果没有图片或文件不存在。
    """
    image_path = question.get("image", "")
    if not image_path:
        return ""

    # 优先：image_path 是相对于项目根目录的路径
    full_path = BASE_DIR / image_path
    if not full_path.exists():
        # 回退：用 _bank_dir 拼接
        bank_dir = question.get("_bank_dir", "")
        if bank_dir:
            full_path = Path(bank_dir) / image_path
        else:
            full_path = QUESTION_BANK_DIR / "math" / "grade-1" / "textbook" / image_path

    if not full_path.exists():
        return ""

    try:
        img_bytes = full_path.read_bytes()
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        # PNG 格式
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"  ⚠ 图片加载失败: {full_path} ({e})")
        return ""


# ============================================================
# 1. 进度解析（读 mastered.md + todo.md）
# ============================================================

def parse_mastered(subject):
    """解析 mastered.md，返回已掌握知识点列表。"""
    path = RECORDS_DIR / subject / "mastered.md"
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    # 匹配 ✅ 开头的行
    items = []
    for line in content.split("\n"):
        if line.strip().startswith("- ✅"):
            item = line.strip().replace("- ✅", "").strip()
            # 去掉日期备注
            item = re.sub(r"\（[^）]*\）", "", item).strip()
            if item:
                items.append(item)
    return items


def parse_todo(subject):
    """解析 todo.md，返回待学知识点列表（保持顺序）。"""
    path = RECORDS_DIR / subject / "todo.md"
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    items = []
    for line in content.split("\n"):
        if line.strip().startswith("- ⬜"):
            item = line.strip().replace("- ⬜", "").strip()
            if item:
                items.append(item)
    return items


def find_next_knowledge_point(subject):
    """
    根据 mastered.md 和 todo.md 确定下一个待学知识点。

    规则：从 todo 中找到第一个不在 mastered 中的知识点。
    如果 todo 全部已掌握或没有 todo，退化为巩固最后一个已掌握知识点。
    """
    return find_next_knowledge_points(subject, max_count=1)[0]


def find_next_knowledge_points(subject, max_count=3):
    """
    返回多个待学知识点（跨维度出题，避免全卷只考一个窄话题）。
    从 todo 中取前 max_count 个未掌握的，至少返回 1 个。
    """
    mastered = parse_mastered(subject)
    todo = parse_todo(subject)

    results = []
    for item in todo:
        if not _is_mastered(item, mastered):
            results.append(item)
            if len(results) >= max_count:
                break

    if results:
        return results

    # 全部学完 → 巩固已掌握的
    return [_last_mastered_or_default(subject, mastered)]


def _is_mastered(todo_item, mastered_list):
    """判断 todo 项是否已在 mastered 中。支持中文模糊匹配。"""
    todo_clean = todo_item.replace("（", "").replace("）", "").replace("、", "").replace("，", "").replace(" ", "")
    for m in mastered_list:
        m_clean = m.replace("（", "").replace("）", "").replace("、", "").replace("，", "").replace(" ", "")
        # 直接子串包含
        if todo_clean in m_clean or m_clean in todo_clean:
            return True
        # 公共子串至少占较短字符串的40%
        lcs = _common_substring_len(todo_clean, m_clean)
        threshold = min(len(todo_clean), len(m_clean)) * 0.4
        if lcs >= max(3, threshold):
            return True
    return False


def _common_substring_len(a, b):
    """计算 a 和 b 的最长公共子串长度。"""
    max_len = 0
    for i in range(len(a)):
        for j in range(len(b)):
            k = 0
            while i + k < len(a) and j + k < len(b) and a[i + k] == b[j + k]:
                k += 1
            max_len = max(max_len, k)
    return max_len


def _last_mastered_or_default(subject, mastered):
    """获取最后一个已掌握知识点，或返回默认起点。"""
    if mastered:
        # 过滤掉过于细节的子项（通常更短、更具体）
        broad_items = [m for m in mastered if len(m) >= 4]
        if broad_items:
            return broad_items[-1]
        return mastered[-1]

    defaults = {
        "math": "100以内数的认识",
        "chinese": "基本笔画（横、竖、撇、捺）",
        "english": "26个字母认读",
        "science": "静电探索",
        "geography": "认识地图",
        "physics": "长度和时间的测量",
    }
    return defaults.get(subject, "基础知识")


# ============================================================
# 2. 题库选题（数学）
# ============================================================

# todo 知识点 → 题库知识点 映射表
# 因为 todo.md 里的知识点描述比较细，而题库的知识点比较粗，
# 需要显式映射才能准确选题。
KNOWLEDGE_POINT_MAP = {
    # 100以内数的认识
    "数数—数的组成": "100以内数的认识",
    "读数—写数（100以内）": "100以内数的认识",
    "数的顺序—比较大小": "数的顺序比较",
    "100以内数的认识": "100以内数的认识",
    # 100以内加减法
    "两位数加一位数、整十数（不进位）": "100以内的加法和减法",
    "两位数加一位数（进位）": "100以内的加法和减法",
    "两位数减一位数、整十数（不退位）": "100以内的加法和减法",
    "两位数减一位数（退位）": "100以内的加法和减法",
    "两位数加两位数（进位）": "100以内的加法和减法",
    "两位数减两位数（退位）": "100以内的加法和减法",
    "整十数加、减整十数": "100以内的加法和减法",
    # 解决问题
    "解决问题（求比一个数多/少几）": "比较应用",
    "连加连减、加减混合": "连加连减",
    # 人民币
    "认识人民币（元角分）": "认识人民币",
}

def _map_knowledge_point(todo_kp):
    """将 todo 知识点映射到题库知识点（支持精确映射和模糊回退）。"""
    if todo_kp in KNOWLEDGE_POINT_MAP:
        return KNOWLEDGE_POINT_MAP[todo_kp]
    return todo_kp


def select_from_bank(subject, knowledge_point, count=8, grade=1):
    """
    从指定学科的题库中按知识点选题（通用科目，不限于数学）。
    先尝试精确映射，再尝试模糊匹配。
    同时从 generated/ 和 textbook/ 目录读取题库。
    返回题目列表，每道题为 dict。
    """
    bank_dir = QUESTION_BANK_DIR / subject / f"grade-{grade}"
    if not bank_dir.exists():
        return []

    all_questions = []
    # 同时读取 generated/ 和 textbook/ 目录
    for sub_dir in ["generated", "textbook"]:
        sub_path = bank_dir / sub_dir
        if not sub_path.exists():
            continue
        for jsonl_file in sorted(sub_path.glob("*.jsonl")):
            try:
                for line in jsonl_file.read_text(encoding="utf-8").strip().split("\n"):
                    if not line.strip():
                        continue
                    q = json.loads(line)
                    # 记录题库文件路径，用于定位图片
                    q["_bank_dir"] = str(sub_path)
                    all_questions.append(q)
            except Exception:
                continue

    if not all_questions:
        return []

    # 映射 todo 知识点 → 题库知识点
    target = _map_knowledge_point(knowledge_point)

    # 优先精确匹配：知识点名完全一致
    exact_matches = [q for q in all_questions if q.get("knowledge_point", "") == target]

    if exact_matches:
        matched = exact_matches
    else:
        # 退化为子串匹配
        matched = [q for q in all_questions if target in q.get("knowledge_point", "") or q.get("knowledge_point", "") in target]

    if not matched:
        return []

    # 按难度分组
    l1 = [q for q in matched if q.get("difficulty") == "L1"]
    l2 = [q for q in matched if q.get("difficulty") == "L2"]
    l3 = [q for q in matched if q.get("difficulty") == "L3"]

    # 去重
    def dedup(qlist):
        seen = set()
        result = []
        for q in qlist:
            qtext = q.get("question", "")
            if qtext not in seen:
                seen.add(qtext)
                result.append(q)
        return result

    l1 = dedup(l1)
    l2 = dedup(l2)
    l3 = dedup(l3)

    random.shuffle(l1)
    random.shuffle(l2)
    random.shuffle(l3)

    # 选题策略：L1 占一半，L2 和 L3 各占 1/4
    selected = []
    n_l1 = max(2, count // 2)
    n_l2 = max(1, count // 4)
    n_l3 = count - n_l1 - n_l2

    selected.extend(l1[:n_l1])
    selected.extend(l2[:n_l2])
    selected.extend(l3[:n_l3])

    # 不够就补 L1
    while len(selected) < count and len(l1) > len(selected):
        for q in l1:
            if q not in selected:
                selected.append(q)
                break
        else:
            break

    random.shuffle(selected)
    return selected[:count]


def select_from_bank_broad(subject, count=20, grade=1):
    """
    跨知识点/跨单元抽样——用于"出一套卷子"的场景。
    从题库所有题目中，按单元均衡抽样，覆盖不同难度和题型。
    """
    bank_dir = QUESTION_BANK_DIR / subject / f"grade-{grade}"
    if not bank_dir.exists():
        return []

    all_questions = []
    for sub_dir in ["generated", "textbook"]:
        sub_path = bank_dir / sub_dir
        if not sub_path.exists():
            continue
        for jsonl_file in sorted(sub_path.glob("*.jsonl")):
            try:
                for line in jsonl_file.read_text(encoding="utf-8").strip().split("\n"):
                    if not line.strip():
                        continue
                    q = json.loads(line)
                    q["_bank_dir"] = str(sub_path)
                    all_questions.append(q)
            except Exception:
                continue

    if not all_questions:
        return []

    # 按单元分组
    by_unit = {}
    for q in all_questions:
        unit = q.get("textbook_unit", "其他")
        # 取单元名前缀（去掉"·第X课时"等后缀）
        unit_key = unit.split("·")[0].strip()
        by_unit.setdefault(unit_key, []).append(q)

    units = list(by_unit.keys())
    if not units:
        return []

    # 按单元数均衡分配题量
    per_unit = max(2, count // len(units))
    remaining = count - per_unit * len(units)

    selected = []
    for i, unit in enumerate(units):
        qs = by_unit[unit][:]
        random.shuffle(qs)
        n = per_unit + (1 if i < remaining else 0)
        selected.extend(qs[:n])

    # 按难度排序（L1→L5），确保试卷从易到难
    diff_order = {"L1": 0, "L2": 1, "L3": 2, "L4": 3, "L5": 4}
    selected.sort(key=lambda q: diff_order.get(q.get("difficulty", "L2"), 99))

    return selected[:count]


def select_from_bank_all_subtypes(subject, knowledge_point, count=8, grade=1):
    """选题时尽量覆盖不同子题型（通用科目）。"""
    questions = select_from_bank(subject, knowledge_point, count * 3, grade=grade)
    if len(questions) <= count:
        return questions

    # 按 subtype 分组
    by_subtype = {}
    for q in questions:
        st = q.get("subtype", "其他")
        by_subtype.setdefault(st, []).append(q)

    # 轮流从每个 subtype 取题
    selected = []
    subtypes = list(by_subtype.keys())
    idx = 0
    while len(selected) < count and subtypes:
        st = subtypes[idx % len(subtypes)]
        if by_subtype[st]:
            selected.append(by_subtype[st].pop(0))
        else:
            subtypes.remove(st)
            if not subtypes:
                break
            idx = -1
        idx += 1

    return selected[:count]


# ============================================================
# 3. AI 生成题目（非数学科兜底）
# ============================================================

def generate_questions_ai(subject, knowledge_point, count=8):
    """
    对非数学科，AI 实时生成题目。
    返回与题库相同格式的题目列表。
    标记 source: "ai-generated"。
    """
    # 根据学科和知识点构造生成 prompt
    subject_name = SUBJECT_NAMES.get(subject, subject)

    templates = {
        "chinese": _gen_chinese_questions,
        "english": _gen_english_questions,
        "science": _gen_science_questions,
        "geography": _gen_geography_questions,
        "physics": _gen_physics_questions,
    }

    gen_func = templates.get(subject)
    if gen_func:
        return gen_func(knowledge_point, count)

    # 兜底：通用格式
    return _gen_generic_questions(subject_name, knowledge_point, count)


def _gen_chinese_questions(knowledge_point, count):
    """语文题目生成。根据知识点类型分别处理。"""
    qs = []
    qid = 0
    kp_clean = knowledge_point.replace("（", "(").replace("）", ")")

    # 1) 写字/书写/生字 → 实际练字题
    if any(kw in kp_clean for kw in ("写字", "书写", "生字", "笔画", "结构")):
        # 尝试从括号中提取汉字列表
        chars = _extract_chars_from_kp(knowledge_point)
        if not chars:
            # 结构类关键词匹配
            struct_map = {
                "独体": ["人", "大", "天", "口", "日", "月", "山", "水", "火", "木"],
                "左右": ["明", "林", "好", "们", "叶", "红", "江", "河", "把", "打"],
                "上下": ["花", "草", "星", "是", "爸", "爷", "早", "香"],
                "包围": ["国", "回", "园", "问", "同", "风", "区"],
            }
            for key, vals in struct_map.items():
                if key in kp_clean:
                    chars = vals
                    break
        if not chars:
            # 一年级常用字兜底
            chars = ["一", "二", "三", "十", "人", "大", "小", "口", "日", "月"]
        for i, ch in enumerate(chars[:count]):
            qid += 1
            qs.append({
                "id": f"chinese-g1-ai-{qid:04d}",
                "type": "写字",
                "subtype": knowledge_point,
                "difficulty": "L1",
                "knowledge_point": knowledge_point,
                "question": f"请照着写这个字：{ch}",
                "answer": ch,
                "explanation": f"规范书写「{ch}」",
                "distractors": [],
                "source": "ai-generated",
                "created": datetime.now().strftime("%Y-%m-%d"),
            })

    # 2) 握笔姿势和坐姿 → 选择题/判断题
    elif "握笔" in kp_clean or "坐姿" in kp_clean or "姿势" in kp_clean:
        posture_qs = [
            ("写字时身体应该离桌子多远？", "一拳的距离", ["一个拳头远", "两个拳头远", "贴紧桌子"]),
            ("握笔时，笔杆应靠在哪个手指上？", "虎口位置（拇指和食指之间）", ["食指指尖", "中指侧面", "无名指"]),
            ("正确的坐姿：眼睛离书本应该多远？", "大约一尺（33厘米）", ["越近越好", "50厘米", "一臂长"]),
            ("写字时书本应该放在什么位置？", "正前方，略微偏右", ["左侧", "随意放", "正前方偏左"]),
            ("握笔的手指离笔尖应该多远？", "约一寸（3厘米）", ["紧贴笔尖", "5厘米以上", "握住笔杆中间"]),
            ("写字时双脚应该怎样放？", "平放在地面上", ["交叉放", "悬空", "踩在椅子腿上"]),
        ]
        random.shuffle(posture_qs)
        for i, (q, ans, _) in enumerate(posture_qs[:count]):
            qid += 1
            qs.append({
                "id": f"chinese-g1-ai-{qid:04d}",
                "type": "填空",
                "subtype": "写字习惯",
                "difficulty": "L1",
                "knowledge_point": knowledge_point,
                "question": q,
                "answer": ans,
                "explanation": "",
                "distractors": [],
                "source": "ai-generated",
                "created": datetime.now().strftime("%Y-%m-%d"),
            })

    # 3) 古诗
    elif "古诗" in kp_clean:
        poems = [
            ("《登鹳雀楼》", "王之涣", "白日依山尽，黄河入海流。欲穷千里目，更上一层楼。", "站得高才能看得远"),
            ("《静夜思》", "李白", "床前明月光，疑是地上霜。举头望明月，低头思故乡。", "看到月亮想起了家乡"),
            ("《春晓》", "孟浩然", "春眠不觉晓，处处闻啼鸟。夜来风雨声，花落知多少。", "春天早晨醒来，听到鸟叫，想起昨夜风雨"),
            ("《悯农》", "李绅", "锄禾日当午，汗滴禾下土。谁知盘中餐，粒粒皆辛苦。", "农民种地很辛苦，要珍惜粮食"),
            ("《咏鹅》", "骆宾王", "鹅鹅鹅，曲项向天歌。白毛浮绿水，红掌拨清波。", "描写大白鹅在水中游动的样子"),
            ("《画》", "王维", "远看山有色，近听水无声。春去花还在，人来鸟不惊。", "这是一幅画，画里的山和水都是静止的"),
        ]

        # 分配题型：背诵填空 + 理解问答 + 作者配对
        q_types = []
        n_fill = max(2, count * 2 // 3)       # 2/3 补全诗句
        n_understand = count - n_fill - 1    # 1 道理解题
        n_author = 1                          # 1 道作者题
        q_types = ["fill"] * n_fill + ["understand"] * n_understand + ["author"] * n_author
        random.shuffle(q_types)

        used_poems_fill = []
        used_poems_understand = []
        used_poems_author = []

        for qt in q_types:
            qid += 1

            if qt == "fill":
                # 选一首没用过的诗，补全其中一句
                avail = [p for p in poems if p[0] not in used_poems_fill]
                if not avail:
                    avail = poems
                title, author, text, meaning = random.choice(avail)
                used_poems_fill.append(title)
                lines = [l.strip("。，. ") for l in text.replace("。", "，").split("，") if l.strip()]
                # 随机选一句让学生补全
                idx = random.randint(0, len(lines) - 1)
                blank_line = lines[idx]

                # 构建简洁的上下文提示
                before = lines[:idx]
                after = lines[idx+1:]
                context_parts = []
                if before:
                    context_parts.append("「" + "，".join(before) + "」")
                context_parts.append("（ ？ ）")
                if after:
                    context_parts.append("「" + "，".join(after) + "」")
                context_str = "  ".join(context_parts)

                qs.append({
                    "id": f"chinese-g1-ai-{qid:04d}",
                    "type": "填空",
                    "subtype": "古诗背诵",
                    "difficulty": "L2",
                    "knowledge_point": knowledge_point,
                    "question": f"请补全古诗《{title[1:-1]}》中缺少的一句：{context_str}",
                    "answer": blank_line,
                    "explanation": f"{title} — {author}：{text}\n诗意：{meaning}",
                    "distractors": [],
                    "source": "ai-generated",
                    "created": datetime.now().strftime("%Y-%m-%d"),
                })

            elif qt == "understand":
                # 理解诗意题
                avail = [p for p in poems if p[0] not in used_poems_understand]
                if not avail:
                    avail = poems
                title, author, text, meaning = random.choice(avail)
                used_poems_understand.append(title)
                question = f"古诗《{title[1:-1]}》说的是什么意思？（用自己的话说一说）"
                qs.append({
                    "id": f"chinese-g1-ai-{qid:04d}",
                    "type": "简答",
                    "subtype": "古诗理解",
                    "difficulty": "L2",
                    "knowledge_point": knowledge_point,
                    "question": question,
                    "answer": meaning,
                    "explanation": f"{title} 作者 {author}，全文：{text}",
                    "distractors": [],
                    "source": "ai-generated",
                    "created": datetime.now().strftime("%Y-%m-%d"),
                })

            elif qt == "author":
                # 作者配对题
                avail = [p for p in poems if p[0] not in used_poems_author]
                if not avail:
                    avail = poems
                title, author, text, meaning = random.choice(avail)
                used_poems_author.append(title)
                qs.append({
                    "id": f"chinese-g1-ai-{qid:04d}",
                    "type": "填空",
                    "subtype": "作者知识",
                    "difficulty": "L1",
                    "knowledge_point": knowledge_point,
                    "question": f"《{title[1:-1]}》的作者是谁？",
                    "answer": author,
                    "explanation": f"{author} 是唐代诗人，代表作 {title}。",
                    "distractors": [],
                    "source": "ai-generated",
                    "created": datetime.now().strftime("%Y-%m-%d"),
                })

    # 4) 阅读/表达/复述
    elif any(kw in kp_clean for kw in ("阅读", "复述", "看图说话", "表达")):
        reading_qs = [
            ("阅读短文后，用一句话说出主要意思，这叫____。", "概括大意", []),
            ("「看图说话」需要观察哪三要素？", "时间、地点、人物", []),
            ("复述故事时，应该按什么顺序说？", "事情发生的先后顺序", []),
            ("读完后，试着自己讲一遍故事的主要情节。", "（口头练习，无标准答案）", []),
        ]
        for i, (q, ans, _) in enumerate(reading_qs[:count]):
            qid += 1
            qs.append({
                "id": f"chinese-g1-ai-{qid:04d}",
                "type": "简答",
                "subtype": "阅读理解",
                "difficulty": "L2",
                "knowledge_point": knowledge_point,
                "question": q,
                "answer": ans,
                "explanation": "",
                "distractors": [],
                "source": "ai-generated",
                "created": datetime.now().strftime("%Y-%m-%d"),
            })

    else:
        qs = _gen_generic_questions("语文", knowledge_point, count)

    return qs


def _extract_chars_from_kp(kp):
    """从知识点描述中提取汉字列表，如 '简单汉字书写（一、二、三、十、人、大、小、口、日、月）'。"""
    import re
    # 匹配括号内的顿号分隔内容
    m = re.search(r'[（(]([^）)]+)[）)]', kp)
    if not m:
        return []
    inner = m.group(1)
    # 找单个汉字（排除标点、数字、字母）
    chars = re.findall(r'[\u4e00-\u9fff]', inner)
    return chars


def _gen_english_questions(knowledge_point, count):
    """英语题目生成（纯书面，无发音）。"""
    qs = []

    word_banks = {
        "字母": ["A", "B", "C", "D", "E", "F", "G", "H"],
        "颜色": ["red", "blue", "yellow", "green", "black", "white", "orange", "purple"],
        "动物": ["cat", "dog", "bird", "fish", "rabbit", "duck", "pig", "cow"],
        "数字": ["one", "two", "three", "four", "five", "six", "seven", "eight"],
        "水果": ["apple", "banana", "orange", "grape", "pear", "peach"],
        "身体": ["head", "eyes", "nose", "mouth", "ears", "hands", "feet"],
    }

    words = None
    for key, vals in word_banks.items():
        if key in knowledge_point:
            words = vals
            break
    if not words:
        words = word_banks.get("字母", ["A", "B", "C", "D", "E", "F", "G", "H"])

    for i, w in enumerate(words[:count]):
        qs.append({
            "id": f"english-g1-ai-{i+1:04d}",
            "type": "抄写",
            "subtype": knowledge_point,
            "difficulty": "L1",
            "knowledge_point": knowledge_point,
            "question": f"请抄写这个单词/字母：{w}",
            "answer": w,
            "explanation": f"规范书写「{w}」",
            "distractors": [],
            "source": "ai-generated",
            "created": datetime.now().strftime("%Y-%m-%d"),
        })

    return qs


def _gen_science_questions(knowledge_point, count):
    """科学题目生成（探索型）。"""
    topics = {
        "动物": [
            ("请写出 3 种你认识的哺乳动物", "猫、狗、大象（答案不唯一）"),
            ("鱼用什么呼吸？", "鳃"),
            ("鸟儿为什么能飞？", "有翅膀、身体轻、有羽毛（合理即可）"),
        ],
        "植物": [
            ("植物生长需要什么？（写 2 样）", "水、阳光（答案不唯一）"),
            ("树叶为什么是绿色的？", "因为有叶绿素"),
        ],
        "地球": [
            ("地球有几个大洲？", "七个"),
            ("为什么会有白天和黑夜？", "地球自转"),
        ],
        "静电": [
            ("摩擦气球后能吸起纸片，这是什么现象？", "静电（摩擦起电）"),
            ("冬天脱毛衣会有噼啪声，为什么？", "静电放电"),
            ("为什么冬天静电多，夏天静电少？", "冬天空气干燥，夏天潮湿，水汽能带走电荷"),
            ("两种物体摩擦后，电子怎么跑？", "从一个物体跑到另一个物体上"),
            ("同种电荷靠近会怎样？异种电荷呢？", "同种相斥，异种相吸"),
            ("静电放电会产生什么？（写出2种）", "噼啪声、小火花"),
            ("塑料、毛皮容易起静电吗？为什么？", "容易，它们是绝缘体，电子不容易跑掉"),
            ("闪电和静电有什么关系？", "闪电是大规模的静电放电"),
        ],
        "磁铁": [
            ("磁铁能吸住什么东西？（写 2 样）", "铁钉、回形针（铁磁性材料）"),
            ("两个 N 极的磁铁靠近会怎样？", "互相推开（排斥）"),
        ],
    }

    matched = None
    for key, vals in topics.items():
        if key in knowledge_point:
            matched = vals
            break
    if not matched:
        # 模糊匹配：检查 knowledge_point 中的字符和 topic key 的重叠
        for key, vals in topics.items():
            if any(c in knowledge_point for c in key):
                matched = vals
                break
    if not matched:
        matched = topics.get("动物", topics["动物"])

    qs = []
    for i, (q_text, ans) in enumerate(matched[:count]):
        qs.append({
            "id": f"science-g1-ai-{i+1:04d}",
            "type": "简答",
            "subtype": knowledge_point,
            "difficulty": "L1",
            "knowledge_point": knowledge_point,
            "question": q_text,
            "answer": ans,
            "explanation": "",
            "distractors": [],
            "source": "ai-generated",
            "created": datetime.now().strftime("%Y-%m-%d"),
        })

    return qs


def _gen_geography_questions(knowledge_point, count):
    """地理题目生成。"""
    qs = [
        {"q": "中国在地球上的哪个大洲？", "a": "亚洲"},
        {"q": "世界上有几个大洋？", "a": "四个（太平洋、大西洋、印度洋、北冰洋）"},
        {"q": "世界上最长的河是什么河？", "a": "尼罗河（在非洲）"},
        {"q": "沙漠里会有生命吗？", "a": "有，比如仙人掌、骆驼"},
        {"q": "南极和北极，哪个更冷？", "a": "南极更冷"},
        {"q": "地球表面最多的是什么？", "a": "海洋（约71%）"},
        {"q": "中国最高的山是什么山？", "a": "珠穆朗玛峰"},
        {"q": "说出 3 种地形（如：山）", "a": "山、平原、高原、盆地、丘陵（任选3）"},
    ]
    result = []
    for i, item in enumerate(qs[:count]):
        result.append({
            "id": f"geography-g1-ai-{i+1:04d}",
            "type": "简答",
            "subtype": knowledge_point,
            "difficulty": "L1",
            "knowledge_point": knowledge_point,
            "question": item["q"],
            "answer": item["a"],
            "explanation": "",
            "distractors": [],
            "source": "ai-generated",
            "created": datetime.now().strftime("%Y-%m-%d"),
        })
    return result


def _gen_physics_questions(knowledge_point, count):
    """物理题目生成。"""
    qs = [
        {"q": "测量一个本子的长度，用什么工具？", "a": "尺子（刻度尺）"},
        {"q": "1 厘米等于多少毫米？", "a": "10 毫米"},
        {"q": "小明用尺子量铅笔，一端对着 0 刻度，另一端对着 12 厘米，铅笔多长？", "a": "12 厘米"},
        {"q": "尺子上的最小刻度是 1 毫米，这个尺子的分度值是多少？", "a": "1 毫米"},
        {"q": "测量物体长度时，视线应该怎么看？", "a": "与刻度垂直（正视）"},
        {"q": "1 米等于多少厘米？", "a": "100 厘米"},
        {"q": "什么是误差？", "a": "测量值与真实值之间的差异"},
        {"q": "多次测量取平均值可以减小什么？", "a": "误差"},
    ]
    result = []
    for i, item in enumerate(qs[:count]):
        result.append({
            "id": f"physics-g1-ai-{i+1:04d}",
            "type": "简答",
            "subtype": knowledge_point,
            "difficulty": "L1",
            "knowledge_point": knowledge_point,
            "question": item["q"],
            "answer": item["a"],
            "explanation": "",
            "distractors": [],
            "source": "ai-generated",
            "created": datetime.now().strftime("%Y-%m-%d"),
        })
    return result


def _gen_generic_questions(subject_name, knowledge_point, count):
    """通用题目生成兜底。"""
    qs = []
    for i in range(count):
        qs.append({
            "id": f"{subject_name}-g1-ai-{i+1:04d}",
            "type": "简答",
            "subtype": knowledge_point,
            "difficulty": "L1",
            "knowledge_point": knowledge_point,
            "question": f"关于「{knowledge_point}」，请回答以下问题：______",
            "answer": "（请家长核对）",
            "explanation": "",
            "distractors": [],
            "source": "ai-generated",
            "created": datetime.now().strftime("%Y-%m-%d"),
        })
    return qs


# ============================================================
# 4. HTML 渲染
# ============================================================

def render_html(subject, knowledge_point, questions, paper_size="A4"):
    """将题目列表渲染为自包含 HTML 文件。"""
    subject_name = SUBJECT_NAMES.get(subject, subject)
    today = datetime.now().strftime("%Y-%m-%d")

    page_size_css = _page_size_css(paper_size)

    # 按难度排序后渲染（确保题目和答案使用同一顺序）
    diff_order = {"L1": 0, "L2": 1, "L3": 2, "L4": 3, "L5": 4}
    sorted_questions = sorted(questions, key=lambda q: diff_order.get(q.get("difficulty", "L1"), 99))

    # 统计有哪些难度组（用于得分表）
    diff_names = {"L1": "基础题", "L2": "巩固题", "L3": "提高题", "L4": "拓展题", "L5": "挑战题"}
    section_diffs = []
    for d in ["L1", "L2", "L3", "L4", "L5"]:
        if any(q.get("difficulty") == d for q in sorted_questions):
            section_diffs.append(d)

    score_header = "".join(f"<th>{diff_names.get(d, d)}</th>" for d in section_diffs)
    score_body = "".join("<td> </td>" for _ in section_diffs)

    # 构建题目 HTML
    question_html = _render_questions_html(subject, sorted_questions)

    # 构建答案 HTML
    answer_html = _render_answers_html(sorted_questions)

    # 统计 AI 生成题目数
    ai_count = sum(1 for q in questions if q.get("source") == "ai-generated")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{subject_name}练习题 — {today}</title>
<!-- KaTeX 数学公式渲染 -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: "宋体", "SimSun", "Noto Serif CJK SC", serif;
    font-size: 15px;
    line-height: 1.7;
    color: #000;
    width: 100%;
    padding: 6mm 10mm;
    background: #fff;
}}

/* ===== 整体外框（密封线 + 全部题目） ===== */
.exam-frame {{
    display: flex;
    border: 1.5px solid #000;
    padding: 0;
    margin-bottom: 16px;
    min-height: 100%;
}}
.exam-frame .seal-left {{
    width: 38px;
    flex-shrink: 0;
    border-right: 1.5px dashed #000;
    display: flex;
    align-items: center;
    justify-content: center;
    writing-mode: vertical-rl;
    font-size: 12px;
    letter-spacing: 4px;
    color: #555;
    padding: 8px 4px;
}}
.exam-frame .exam-body {{
    flex: 1;
    padding: 10px 14px;
    min-width: 0;
}}
.exam-body h1 {{
    font-size: 20px;
    text-align: center;
    font-weight: bold;
    margin-bottom: 4px;
    letter-spacing: 4px;
}}
.exam-body .info-row {{
    display: flex;
    justify-content: space-between;
    font-size: 14px;
    gap: 20px;
}}
.exam-body .info-row span {{
    white-space: nowrap;
}}
.exam-body .info-row .blank {{
    display: inline-block;
    min-width: 80px;
    border-bottom: 1px solid #000;
    text-align: center;
}}

/* ===== 得分表 ===== */
.score-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
    font-size: 14px;
}}
.score-table th {{
    border: 1.5px solid #000;
    padding: 10px 6px;
    text-align: center;
    font-weight: bold;
    background: #fafafa;
}}
.score-table td {{
    border: 1px solid #000;
    padding: 12px 6px;
    text-align: center;
}}

/* ===== 题目区 ===== */
.section-title {{
    font-size: 16px;
    font-weight: bold;
    margin: 14px 0 6px;
    padding-bottom: 2px;
    border-bottom: 1px solid #000;
    letter-spacing: 2px;
}}

/* 计算题：双栏网格 */
.calc-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 3px 30px;
}}
.calc-grid .q-item {{
    display: flex;
    align-items: baseline;
    gap: 4px;
    padding: 4px 0;
}}
.calc-grid .q-num {{
    font-weight: bold;
    font-size: 14px;
    min-width: 30px;
    white-space: nowrap;
}}
.calc-grid .q-expr {{
    font-size: 16px;
    font-family: "Times New Roman", "宋体", serif;
    letter-spacing: 1px;
}}
.calc-grid .q-blank {{
    display: inline-block;
    min-width: 50px;
    border-bottom: 1px solid #000;
    text-align: center;
    padding: 0 4px;
    margin: 0 3px;
}}

/* 非计算题：单栏 */
.q-single {{
    padding: 5px 0;
    border-bottom: 1px dotted #ddd;
}}
.q-single .q-num {{
    font-weight: bold;
    font-size: 14px;
    margin-right: 6px;
}}
.q-single .q-text {{
    display: inline;
    font-size: 15px;
}}
.q-single .q-blank {{
    display: inline-block;
    min-width: 80px;
    border-bottom: 1px solid #000;
    text-align: center;
    padding: 0 6px;
    margin: 0 4px;
}}

/* 应用题答案区 */
.q-app {{
    padding: 6px 0;
    border-bottom: 1px dotted #ddd;
}}
.q-app .q-num {{
    font-weight: bold;
    font-size: 14px;
    margin-right: 6px;
}}
.q-app .q-text {{
    font-size: 15px;
    display: block;
    margin-bottom: 3px;
}}
.q-app .q-answer {{
    font-size: 14px;
    color: #000;
    padding: 2px 0 2px 20px;
}}
.q-app .q-answer .blank {{
    display: inline-block;
    min-width: 120px;
    border-bottom: 1px solid #000;
    text-align: center;
}}

/* 写字/抄写题 */
.q-write {{
    padding: 6px 0;
    border-bottom: 1px dotted #ddd;
    display: flex;
    align-items: center;
    gap: 15px;
}}
.q-write .q-num {{
    font-weight: bold;
    font-size: 14px;
    min-width: 30px;
}}
.q-write .model-char {{
    font-size: 30px;
    color: #bbb;
    font-family: "楷体", "KaiTi", serif;
}}
.q-write .write-box {{
    display: inline-block;
    width: 120px;
    height: 44px;
    border: 1.5px dashed #999;
}}

/* 难度角标 */
.diff-mark {{
    font-size: 10px;
    color: #999;
    vertical-align: super;
    margin-left: 2px;
}}

/* 带图题目 */
.q-with-image {{
    padding: 5px 0;
    border-bottom: 1px dotted #ddd;
}}
.q-with-image .q-num {{
    font-weight: bold;
    font-size: 14px;
    margin-right: 6px;
}}
.q-with-image .q-text {{
    display: inline;
    font-size: 15px;
}}
.q-with-image .q-image {{
    max-width: 70%;
    max-height: 180px;
    margin: 6px auto 4px;
    border: 1px solid #ddd;
    border-radius: 4px;
    display: block;
    object-fit: contain;
}}

/* 看图列式题 */
.q-app-image {{
    padding: 6px 0;
    border-bottom: 1px dotted #ddd;
}}
.q-app-image .q-num {{
    font-weight: bold;
    font-size: 14px;
    margin-right: 6px;
}}
.q-app-image .q-image {{
    max-width: 70%;
    max-height: 180px;
    margin: 4px auto 6px;
    border: 1px solid #ddd;
    border-radius: 4px;
    display: block;
    object-fit: contain;
}}
.q-app-image .q-text {{
    font-size: 15px;
    display: block;
    margin-bottom: 3px;
}}
.q-app-image .q-answer {{
    font-size: 14px;
    color: #000;
    padding: 2px 0 2px 20px;
}}
.q-app-image .q-answer .blank {{
    display: inline-block;
    min-width: 120px;
    border-bottom: 1px solid #000;
    text-align: center;
}}

/* ===== 答案区（屏幕查看用） ===== */
.answer-section {{
    display: none;
    margin-top: 20px;
    padding: 0 10px;
    border-top: 2px solid #4a90d9;
}}
.answer-section.visible {{ display: block; }}
.answer-section h2 {{
    font-size: 17px;
    margin: 10px 0 8px;
    color: #4a90d9;
}}
.answer-section table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}}
.answer-section td {{
    padding: 3px 8px;
    border-bottom: 1px dashed #ddd;
}}
.answer-section .a-num {{ font-weight: bold; color: #4a90d9; white-space: nowrap; }}
.answer-section .a-val {{ color: #2e7d32; font-weight: bold; padding-right: 12px; }}
.answer-section .a-exp {{ color: #888; font-size: 13px; }}

/* ===== 按钮（屏幕专用，不打印） ===== */
.controls {{
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-bottom: 8px;
}}
.controls button {{
    padding: 5px 14px;
    font-size: 13px;
    border: 1px solid #999;
    background: #f8f8f8;
    color: #333;
    cursor: pointer;
    font-family: inherit;
}}
.controls button:hover {{ background: #eee; }}
.controls button.active {{ background: #4a90d9; color: #fff; border-color: #4a90d9; }}
.controls select {{
    padding: 5px 10px;
    font-size: 13px;
    border: 1px solid #999;
    font-family: inherit;
    cursor: pointer;
}}

.ai-note {{
    margin-top: 12px;
    font-size: 12px;
    color: #856404;
    padding: 4px 10px;
    background: #fff8e1;
    border-left: 3px solid #ffc107;
}}

/* ===== 打印 ===== */
@media print {{
    body {{
        font-size: 14px;
        line-height: 1.6;
        padding: 3mm 5mm;
    }}
{page_size_css}
    .no-print {{ display: none !important; }}
    .exam-frame {{ border: 1.5px solid #000; }}
    .exam-frame .seal-left {{ border-right-color: #000; }}
    .answer-section {{ display: none !important; }}
    .answer-section.visible {{ display: block !important; }}
    .ai-note {{ display: none !important; }}
    .q-image {{ max-height: 140px !important; max-width: 60% !important; }}
    body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
}}
</style>
</head>
<body>

<div class="controls no-print">
    <button id="btn-answer" onclick="toggleAnswers()">显示答案</button>
    <button id="btn-pdf" onclick="exportPDF()">导出PDF</button>
    <select id="paper-select" onchange="changePaper(this.value)">
        <option value="A4" {"selected" if paper_size == "A4" else ""}>A4</option>
        <option value="A3" {"selected" if paper_size == "A3" else ""}>A3</option>
    </select>
</div>

<div class="exam-frame">
    <div class="seal-left">← 密封线内不要答题 →</div>
    <div class="exam-body">
        <h1>{subject_name} 练习题</h1>
        <div class="info-row">
            <span>姓名：<span class="blank"></span></span>
            <span>日期：{today}</span>
            <span>用时：<span class="blank"></span> 分钟</span>
        </div>
        <div style="text-align:right;font-size:12px;color:#888;margin-top:2px;">{knowledge_point}</div>

        <table class="score-table no-print">
            <tr>
                {score_header}
                <th>总分</th>
            </tr>
            <tr>
                {score_body}
                <td> </td>
            </tr>
        </table>

        {question_html}
    </div>
</div>

<div class="answer-section" id="answer-section">
    <h2>参考答案</h2>
    <table>{answer_html}</table>
</div>

{"<div class='ai-note no-print'>[!] 本卷中有 " + str(ai_count) + " 道题为AI生成，建议家长先核对答案。</div>" if ai_count > 0 else ""}

<script>
function toggleAnswers() {{
    var s = document.getElementById('answer-section');
    var b = document.getElementById('btn-answer');
    s.classList.toggle('visible');
    if (s.classList.contains('visible')) {{
        b.textContent = '隐藏答案'; b.classList.add('active');
    }} else {{
        b.textContent = '显示答案'; b.classList.remove('active');
    }}
}}
function exportPDF() {{ window.print(); }}
function changePaper(size) {{
    var st = document.getElementById('page-size-style');
    if (!st) {{
        st = document.createElement('style'); st.id = 'page-size-style';
        document.head.appendChild(st);
    }}
    if (size === 'A3') {{
        st.textContent = '@media print {{ @page {{ size: A3 landscape; margin: 8mm; }} body {{ font-size: 15px; }} }}';
    }} else {{
        st.textContent = '@media print {{ @page {{ size: A4; margin: 8mm; }} body {{ font-size: 14px; }} }}';
    }}
}}
</script>
<!-- KaTeX 自动渲染 -->
<script>
document.addEventListener("DOMContentLoaded", function() {{
    renderMathInElement(document.body, {{
        delimiters: [
            {{left: "$$", right: "$$", display: true}},
            {{left: "$", right: "$", display: false}}
        ],
        throwOnError: false
    }});
}});
</script>
</body>
</html>"""
    return html


def _page_size_css(paper_size):
    """根据纸张尺寸返回 @page CSS。"""
    if paper_size == "A3":
        return """    @page {
        size: A3 landscape;
        margin: 8mm;
    }"""
    return """    @page {
        size: A4;
        margin: 8mm;
    }"""


def _render_questions_html(subject, questions):
    """将题目列表渲染为紧凑试卷风格 HTML。计算题双栏，其他单栏。"""
    if not questions:
        return "<p>暂无题目。</p>"

    # 按难度分组
    groups = {}
    for q in questions:
        diff = q.get("difficulty", "L1")
        groups.setdefault(diff, []).append(q)

    diff_names = {"L1": "一、基础题", "L2": "二、巩固题", "L3": "三、提高题", "L4": "四、拓展题", "L5": "五、挑战题"}
    diff_order = ["L1", "L2", "L3", "L4", "L5"]

    html_parts = []
    global_num = 0

    for diff in diff_order:
        if diff not in groups:
            continue
        qs = groups[diff]
        section_name = diff_names.get(diff, diff)
        html_parts.append(f'<div class="section-title">{section_name}</div>')

        # 判断是否全部为计算题 → 双栏布局
        all_calc = all(q.get("type") == "计算" for q in qs)
        if all_calc:
            html_parts.append('<div class="calc-grid">')
            for q in qs:
                global_num += 1
                html_parts.append(_render_calc_question(global_num, q, diff))
            html_parts.append('</div>')
        else:
            for q in qs:
                global_num += 1
                html_parts.append(_render_single_question(global_num, q))

    return "\n".join(html_parts)


def _render_calc_question(num, q, diff):
    """双栏计算题。"""
    question = q.get("question", "")
    # "30 + 10 = ?" → "30 + 10 ="
    expr = question.replace("= ?", "=").replace("=?", "=")
    return f"""<div class="q-item">
    <span class="q-num">{num}.</span>
    <span class="q-expr">{expr}</span>
    <span class="q-blank"></span>
</div>"""


def _render_single_question(num, q):
    """单栏题（填空/简答/写字/抄写等），支持带图题目。"""
    qtype = q.get("type", "简答")
    question = render_math(q.get("question", ""))
    source = q.get("source", "")
    source_note = ' <span class="diff-mark">[AI]</span>' if source == "ai-generated" else ""
    has_image = bool(q.get("image", ""))
    img_b64 = load_image_base64(q) if has_image else ""
    img_tag = f'<img class="q-image" src="{img_b64}" alt="题目图片">' if img_b64 else ""

    if qtype == "选择":
        # 多选题/单选题 — 渲染为字母选项列表
        opts = q.get("options", [])
        # 如果 question 里内嵌了选项文本，先剥离，只保留题干
        question_text = question
        if opts:
            # 找到 question 中选项部分的起始位置（"\nA "、"\nA."、或开头"A "）
            cut_positions = []
            for marker in ["\nA ", "\nA.", "\n① ", "\n①.", "\n1. ", "\n（1）"]:
                idx = question_text.find(marker)
                if idx > 0:
                    cut_positions.append(idx)
            if cut_positions:
                question_text = question_text[:min(cut_positions)].strip()
        opts_html = []
        letters = ["A", "B", "C", "D", "E", "F"]
        for i, o in enumerate(opts):
            letter = letters[i] if i < len(letters) else f"({i+1})"
            opts_html.append(f'<div style="padding:2px 0;"><span style="font-weight:700;margin-right:6px;">{letter}.</span> {render_math(o)}</div>')
        opts_block = "\n".join(opts_html)
        if img_tag:
            return f"""<div class="q-with-image">
    <span class="q-num">{num}.</span>
    <span class="q-text">{question_text}{source_note}</span>
    {img_tag}
    <div style="margin:6px 0 4px 30px;font-size:14px;">{opts_block}</div>
</div>"""
        return f"""<div class="q-single">
    <span class="q-num">{num}.</span>
    <span class="q-text">{question_text}{source_note}</span>
    <div style="margin:4px 0 4px 30px;font-size:14px;">{opts_block}</div>
</div>"""

    elif qtype in ("写字", "抄写"):
        ch = q.get("answer", "")
        return f"""<div class="q-write">
    <span class="q-num">{num}.</span>
    <span class="q-text">{question}</span>
    <span class="model-char">{ch}</span>
    <span class="write-box"></span>
    {source_note}
</div>"""

    elif qtype in ("应用题", "简答"):
        if img_tag:
            return f"""<div class="q-app-image">
    <span class="q-num">{num}.</span>
    {img_tag}
    <span class="q-text">{question}{source_note}</span>
    <div class="q-answer">答：<span class="blank"></span></div>
</div>"""
        return f"""<div class="q-app">
    <span class="q-num">{num}.</span>
    <span class="q-text">{question}{source_note}</span>
    <div class="q-answer">答：<span class="blank"></span></div>
</div>"""

    elif qtype in ("填空",):
        if img_tag:
            return f"""<div class="q-with-image">
    <span class="q-num">{num}.</span>
    <span class="q-text">{question}{source_note}</span>
    {img_tag}
</div>"""
        return f"""<div class="q-single">
    <span class="q-num">{num}.</span>
    <span class="q-text">{question}{source_note}</span>
    <span class="q-blank"></span>
</div>"""

    else:
        if img_tag:
            return f"""<div class="q-with-image">
    <span class="q-num">{num}.</span>
    <span class="q-text">{question}{source_note}</span>
    {img_tag}
</div>"""
        return f"""<div class="q-single">
    <span class="q-num">{num}.</span>
    <span class="q-text">{question}{source_note}</span>
    <span class="q-blank"></span>
</div>"""


def _render_answers_html(questions):
    """紧凑表格答案区。"""
    if not questions:
        return "<tr><td>暂无答案。</td></tr>"

    parts = []
    for i, q in enumerate(questions, 1):
        ans = q.get("answer", "")
        exp = q.get("explanation", "")
        source = q.get("source", "")
        sn = ' <span style="font-size:11px;color:#856404;">[AI]</span>' if source == "ai-generated" else ""

        parts.append(f"""<tr>
    <td class="a-num">{i}.</td>
    <td class="a-val">{render_math(ans)}{sn}</td>
    <td class="a-exp">{"<div>" + exp + "</div>" if exp else ""}</td>
</tr>""")

    return "\n".join(parts)


# ============================================================
# 5. 主入口
# ============================================================

def generate_exercise(subject, count=8, paper_size="A4", topic=None, grade=1, broad=False):
    """
    为一个学科生成练习题 HTML。

    参数：
        subject: 学科代码（math/chinese/english/science/geography/physics）
        count: 题目数量
        paper_size: 纸张大小（A4/A3）
        topic: 手动指定知识点（覆盖自动检测），多个用 | 分隔
        grade: 年级（1-6），默认1
        broad: True 时强制跨单元抽样（组卷模式）

    返回：
        生成的 HTML 文件路径
    """
    # 组卷模式（--broad）：强制跨单元抽样，忽略学习进度
    if broad:
        knowledge_points = []
        print(f"  [{SUBJECT_NAMES.get(subject, subject)}] 模式: 组卷（跨单元抽样）")
    # 手动指定知识点优先
    elif topic:
        knowledge_points = [t.strip() for t in topic.split("|") if t.strip()]
    elif grade != 1:
        # 非一年级且未指定知识点 → 跨单元抽样
        knowledge_points = []
    else:
        knowledge_points = find_next_knowledge_points(subject, max_count=3)

    # 跨单元抽样模式
    if broad or (not knowledge_points and grade != 1):
        kp_display = f"五年级综合" if grade == 5 else f"{grade}年级综合"
        print(f"  [{SUBJECT_NAMES.get(subject, subject)}] 模式: 跨单元抽样 (grade-{grade})")
        all_questions = select_from_bank_broad(subject, count=count, grade=grade)
        if not all_questions:
            print(f"    [X] 题库无数据，跳过")
            return None
        print(f"    题库抽样 {len(all_questions)} 道")

        # 统计单元覆盖
        units_covered = set()
        for q in all_questions:
            units_covered.add(q.get("textbook_unit", "").split("·")[0].strip())
        print(f"    覆盖单元: {len(units_covered)} 个")
    else:
        if len(knowledge_points) == 1:
            kp_display = knowledge_points[0]
        else:
            kp_display = " + ".join(knowledge_points)
        print(f"  [{SUBJECT_NAMES.get(subject, subject)}] 知识点: {kp_display}")

        # 按知识点分摊题目数
        all_questions = []
        per_kp = max(2, count // len(knowledge_points))
        remaining = count - per_kp * len(knowledge_points)

        for i, kp in enumerate(knowledge_points):
            n = per_kp + (1 if i < remaining else 0)
            print(f"    [{kp}] 生成 {n} 道题...")

            # 通用科目：优先从题库选取，题库无匹配再 AI 兜底
            qs = select_from_bank_all_subtypes(subject, kp, n, grade=grade)
            if qs:
                print(f"      题库选取 {len(qs)} 道")
            else:
                print(f"      题库无匹配，AI 生成")
                qs = generate_questions_ai(subject, kp, n)

            all_questions.extend(qs)

    if not all_questions:
        print(f"    [X] 无法生成题目，跳过")
        return None

    # 审核：打印题目摘要
    from_bank = sum(1 for q in all_questions if q.get("source") != "ai-generated")
    ai_count = len(all_questions) - from_bank
    print(f"    [审核] 共 {len(all_questions)} 题（题库 {from_bank} + AI {ai_count}）:")
    for i, q in enumerate(all_questions, 1):
        src = "[题库]" if q.get("source") != "ai-generated" else "[AI]"
        qtext = q.get("question", "")[:40]
        print(f"      {i}. {src} {qtext}")

    # 渲染 HTML
    html = render_html(subject, kp_display, all_questions, paper_size)

    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    subject_name = SUBJECT_NAMES.get(subject, subject)
    if knowledge_points:
        safe_kp = knowledge_points[0].replace("/", "-").replace("、", "-")[:20]
    else:
        safe_kp = f"grade{grade}综合"
    filename = f"{today}_{subject_name}_{safe_kp}.html"
    filepath = OUTPUT_DIR / filename
    filepath.write_text(html, encoding="utf-8")

    print(f"    -> 已保存: {filepath}")
    return str(filepath)


def main():
    import argparse

    # 修复 Windows 控制台编码问题
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="练习题生成引擎")
    parser.add_argument("--subject", "-s", type=str, default=None,
                        help="指定学科（math/chinese/english/science/geography/physics），不指定则生成全部")
    parser.add_argument("--count", "-c", type=int, default=DEFAULT_COUNT,
                        help=f"题目数量（默认 {DEFAULT_COUNT}）")
    parser.add_argument("--paper", "-p", type=str, default=DEFAULT_PAPER,
                        choices=["A4", "A3"],
                        help=f"纸张大小（默认 {DEFAULT_PAPER}）")
    parser.add_argument("--topic", "-t", type=str, default=None,
                        help="手动指定知识点（覆盖自动检测），多个用 | 分隔，如 '古诗词|生字书写'")
    parser.add_argument("--grade", "-g", type=int, default=1,
                        help="年级（1-6），默认1。非1年级时自动跨单元抽样")
    parser.add_argument("--broad", "-B", action="store_true",
                        help="组卷模式：跨单元抽样，覆盖全部已学知识点（忽略学习进度）")
    args = parser.parse_args()

    subjects_to_gen = [args.subject] if args.subject else SUBJECTS

    print("=" * 60)
    print("  [我是学霸] 练习题生成引擎")
    mode_str = "组卷（跨单元抽样）" if args.broad else ("跨单元抽样" if args.grade != 1 and not args.topic else "学习进度驱动")
    print(f"  模式: {mode_str} | 年级: {args.grade} | 纸张: {args.paper} | 每题{args.count}道")
    print("=" * 60)

    results = []
    for subj in subjects_to_gen:
        print(f"\n>> 正在生成 {SUBJECT_NAMES.get(subj, subj)} 练习题...")
        try:
            filepath = generate_exercise(subj, args.count, args.paper, args.topic, grade=args.grade, broad=args.broad)
            if filepath:
                results.append(filepath)
        except Exception as e:
            print(f"    X 出错: {e}")

    print("\n" + "=" * 60)
    print(f"  完成! 共生成 {len(results)} 份练习题")
    for fp in results:
        print(f"  -> {fp}")
    print("=" * 60)


if __name__ == "__main__":
    main()
