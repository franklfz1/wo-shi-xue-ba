#!/usr/bin/env python3
"""
人教版数学一年级习题生成器

生成规则：
- 所有答案由 Python 算术运算得出，100% 准确
- 按知识点和难度分级（L1-L5）
- 输出 JSONL 格式，一行一题

使用方法：
    python gen_math_g1.py

输出文件：
    question-bank/math/grade-1/generated/L1-basic.jsonl
    question-bank/math/grade-1/generated/L2-standard.jsonl
    question-bank/math/grade-1/generated/L3-application.jsonl
    question-bank/math/grade-1/generated/L4-L5-challenge.jsonl
"""

import json
import random
from pathlib import Path

# 固定随机种子，保证可复现
random.seed(42)

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "grade-1" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 计数器
counters = {"L1": 0, "L2": 0, "L3": 0, "L4": 0, "L5": 0}

# 难度文件句柄
files = {}


def get_file(difficulty):
    """获取对应难度的文件句柄"""
    if difficulty not in files:
        fname = {
            "L1": "L1-basic.jsonl",
            "L2": "L2-standard.jsonl",
            "L3": "L3-application.jsonl",
            "L4": "L4-L5-challenge.jsonl",
            "L5": "L4-L5-challenge.jsonl",
        }[difficulty]
        files[difficulty] = open(OUTPUT_DIR / fname, "w", encoding="utf-8")
    return files[difficulty]


def make_id(difficulty):
    """生成唯一题号"""
    counters[difficulty] += 1
    return f"math-g1-{difficulty}-{counters[difficulty]:04d}"


def write_question(difficulty, **kwargs):
    """写入一道题"""
    q = {
        "id": make_id(difficulty),
        "difficulty": difficulty,
        "source": "program-generated",
        "created": "2026-06-25",
    }
    q.update(kwargs)
    # 生成错误选项（distractors）
    if "distractors" not in q and "answer" in q:
        q["distractors"] = generate_distractors(q["answer"], q.get("type", ""))
    f = get_file(difficulty)
    f.write(json.dumps(q, ensure_ascii=False) + "\n")


def generate_distractors(answer, qtype):
    """根据答案生成3个错误选项"""
    if not isinstance(answer, int):
        return []
    distractors = set()
    # 策略1：±1
    if answer + 1 not in distractors and answer + 1 >= 0:
        distractors.add(answer + 1)
    if answer - 1 not in distractors and answer - 1 >= 0:
        distractors.add(answer - 1)
    # 策略2：±2
    if len(distractors) < 3 and answer + 2 not in distractors:
        distractors.add(answer + 2)
    if len(distractors) < 3 and answer - 2 not in distractors and answer - 2 >= 0:
        distractors.add(answer - 2)
    # 策略3：±10
    if len(distractors) < 3 and answer + 10 not in distractors:
        distractors.add(answer + 10)
    if len(distractors) < 3 and answer - 10 not in distractors and answer - 10 >= 0:
        distractors.add(answer - 10)
    # 策略4：数字颠倒（适用于两位数）
    if len(distractors) < 3 and answer >= 10:
        tens = answer // 10
        ones = answer % 10
        swapped = ones * 10 + tens
        if swapped != answer and swapped >= 0:
            distractors.add(swapped)
    # 策略5：×2 或 ÷2
    if len(distractors) < 3:
        distractors.add(answer * 2)

    result = list(distractors)[:3]
    # 如果还不够3个，随机补充
    while len(result) < 3:
        fake = answer + random.randint(-5, 5)
        if fake >= 0 and fake != answer and fake not in result:
            result.append(fake)
    return result[:3]


# ============================================================
# L1 基础计算（5以内/10以内/11-20认识/整十数）
# ============================================================

def gen_L1():
    """生成 L1 难度习题（约200题）"""
    # 1. 5以内加法（30题）
    for _ in range(30):
        a = random.randint(1, 4)
        b = random.randint(1, 5 - a)
        ans = a + b
        write_question(
            "L1",
            type="计算",
            subtype="5以内加法",
            knowledge_point="1~5的加法",
            textbook_unit="一 5以内数的认识和加、减法",
            question=f"{a} + {b} = ?",
            answer=ans,
            explanation=f"{a}和{b}合起来是{ans}",
        )

    # 2. 5以内减法（30题）
    for _ in range(30):
        a = random.randint(2, 5)
        b = random.randint(1, a - 1)
        ans = a - b
        write_question(
            "L1",
            type="计算",
            subtype="5以内减法",
            knowledge_point="1~5的减法",
            textbook_unit="一 5以内数的认识和加、减法",
            question=f"{a} - {b} = ?",
            answer=ans,
            explanation=f"{a}去掉{b}还剩{ans}",
        )

    # 3. 含0的加减法（10题）
    for _ in range(5):
        a = random.randint(1, 5)
        write_question(
            "L1",
            type="计算",
            subtype="含0加法",
            knowledge_point="0的认识和加减法",
            textbook_unit="一 5以内数的认识和加、减法",
            question=f"0 + {a} = ?",
            answer=a,
            explanation=f"0加任何数等于那个数本身",
        )
    for _ in range(5):
        a = random.randint(1, 5)
        write_question(
            "L1",
            type="计算",
            subtype="含0减法",
            knowledge_point="0的认识和加减法",
            textbook_unit="一 5以内数的认识和加、减法",
            question=f"{a} - 0 = ?",
            answer=a,
            explanation=f"任何数减0等于它本身",
        )

    # 4. 10以内加法（30题）
    for _ in range(30):
        a = random.randint(1, 9)
        b = random.randint(1, 10 - a)
        ans = a + b
        write_question(
            "L1",
            type="计算",
            subtype="10以内加法",
            knowledge_point="6~10的加法",
            textbook_unit="二 6~10的认识和加、减法",
            question=f"{a} + {b} = ?",
            answer=ans,
            explanation=f"{a}加{b}等于{ans}",
        )

    # 5. 10以内减法（30题）
    for _ in range(30):
        a = random.randint(2, 10)
        b = random.randint(1, a - 1)
        ans = a - b
        write_question(
            "L1",
            type="计算",
            subtype="10以内减法",
            knowledge_point="6~10的减法",
            textbook_unit="二 6~10的认识和加、减法",
            question=f"{a} - {b} = ?",
            answer=ans,
            explanation=f"{a}减{b}等于{ans}",
        )

    # 6. 10的加减法（10题）
    for _ in range(5):
        a = random.randint(1, 9)
        write_question(
            "L1",
            type="计算",
            subtype="10的加法",
            knowledge_point="10的认识和加减法",
            textbook_unit="二 6~10的认识和加、减法",
            question=f"{a} + {10 - a} = ?",
            answer=10,
            explanation=f"{a}和{10-a}组成10",
        )
    for _ in range(5):
        a = random.randint(1, 9)
        write_question(
            "L1",
            type="计算",
            subtype="10的减法",
            knowledge_point="10的认识和加减法",
            textbook_unit="二 6~10的认识和加、减法",
            question=f"10 - {a} = ?",
            answer=10 - a,
            explanation=f"10可以分成{a}和{10-a}",
        )

    # 7. 11-20的认识——10加几（20题）
    for _ in range(20):
        a = random.randint(1, 9)
        ans = 10 + a
        write_question(
            "L1",
            type="计算",
            subtype="10加几",
            knowledge_point="11~20的认识",
            textbook_unit="四 11~20的认识",
            question=f"10 + {a} = ?",
            answer=ans,
            explanation=f"1个十和{a}个一组成{ans}",
        )

    # 8. 十几加减（不进位不退位）（20题）
    for _ in range(10):
        a = random.randint(11, 19)
        b = random.randint(1, 9 - (a % 10))  # 保证不进位
        ans = a + b
        write_question(
            "L1",
            type="计算",
            subtype="十几加几（不进位）",
            knowledge_point="11~20的简单加减法",
            textbook_unit="四 11~20的认识",
            question=f"{a} + {b} = ?",
            answer=ans,
            explanation=f"个位{a%10}加{b}等于{a%10+b}，所以是{ans}",
        )
    for _ in range(10):
        a = random.randint(11, 19)
        b = random.randint(1, a % 10)  # 保证不退位
        ans = a - b
        write_question(
            "L1",
            type="计算",
            subtype="十几减几（不退位）",
            knowledge_point="11~20的简单加减法",
            textbook_unit="四 11~20的认识",
            question=f"{a} - {b} = ?",
            answer=ans,
            explanation=f"个位{a%10}减{b}等于{a%10-b}，所以是{ans}",
        )

    # 9. 整十数加减（10题）
    for _ in range(5):
        a = random.randint(1, 9) * 10
        b = random.randint(1, 9) * 10
        if a + b <= 100:
            write_question(
                "L1",
                type="计算",
                subtype="整十数加法",
                knowledge_point="100以内数的认识",
                textbook_unit="四 100以内数的认识",
                question=f"{a} + {b} = ?",
                answer=a + b,
                explanation=f"{a//10}个十加{b//10}个十等于{(a+b)//10}个十，是{a+b}",
            )
    for _ in range(5):
        a = random.randint(2, 9) * 10
        b = random.randint(1, (a // 10) - 1) * 10
        write_question(
            "L1",
            type="计算",
            subtype="整十数减法",
            knowledge_point="100以内数的认识",
            textbook_unit="四 100以内数的认识",
            question=f"{a} - {b} = ?",
            answer=a - b,
            explanation=f"{a//10}个十减{b//10}个十等于{(a-b)//10}个十，是{a-b}",
        )

    # 10. 100以内数的组成（10题）
    for _ in range(10):
        tens = random.randint(1, 9)
        ones = random.randint(0, 9)
        num = tens * 10 + ones
        write_question(
            "L1",
            type="填空",
            subtype="数的组成",
            knowledge_point="100以内数的认识",
            textbook_unit="四 100以内数的认识",
            question=f"{num}里面有（ ）个十和（ ）个一",
            answer=f"{tens},{ones}",
            explanation=f"{num}的十位是{tens}，个位是{ones}",
        )

    print(f"L1 生成完成：{counters['L1']} 题")


# ============================================================
# L2 标准计算（进位加法/退位减法/连加连减/人民币）
# ============================================================

def gen_L2():
    """生成 L2 难度习题（约150题）"""
    # 1. 连加（20题）
    for _ in range(20):
        a = random.randint(1, 8)
        b = random.randint(1, 9 - a)
        c = random.randint(1, 10 - a - b)
        ans = a + b + c
        write_question(
            "L2",
            type="计算",
            subtype="连加",
            knowledge_point="连加连减",
            textbook_unit="二 6~10的认识和加、减法",
            question=f"{a} + {b} + {c} = ?",
            answer=ans,
            explanation=f"先算{a}+{b}={a+b}，再算{a+b}+{c}={ans}",
        )

    # 2. 连减（20题）
    for _ in range(20):
        a = random.randint(5, 10)
        b = random.randint(1, a - 2)
        c = random.randint(1, a - b - 1)
        ans = a - b - c
        write_question(
            "L2",
            type="计算",
            subtype="连减",
            knowledge_point="连加连减",
            textbook_unit="二 6~10的认识和加、减法",
            question=f"{a} - {b} - {c} = ?",
            answer=ans,
            explanation=f"先算{a}-{b}={a-b}，再算{a-b}-{c}={ans}",
        )

    # 3. 加减混合（20题）
    for _ in range(20):
        a = random.randint(5, 10)
        b = random.randint(1, a - 1)
        c = random.randint(1, 10 - (a - b))
        ans = a - b + c
        write_question(
            "L2",
            type="计算",
            subtype="加减混合",
            knowledge_point="加减混合",
            textbook_unit="二 6~10的认识和加、减法",
            question=f"{a} - {b} + {c} = ?",
            answer=ans,
            explanation=f"先算{a}-{b}={a-b}，再算{a-b}+{c}={ans}",
        )

    # 4. 9加几（凑十法）（15题）
    for _ in range(15):
        b = random.randint(2, 9)
        ans = 9 + b
        write_question(
            "L2",
            type="计算",
            subtype="9加几（凑十法）",
            knowledge_point="20以内的进位加法",
            textbook_unit="五 20以内的进位加法",
            question=f"9 + {b} = ?",
            answer=ans,
            explanation=f"拆{b}为1和{b-1}，9+1=10，10+{b-1}={ans}",
        )

    # 5. 8/7/6加几（凑十法）（15题）
    for _ in range(5):
        a, b = 8, random.randint(2, 9)
        ans = a + b
        write_question(
            "L2",
            type="计算",
            subtype="8加几（凑十法）",
            knowledge_point="20以内的进位加法",
            textbook_unit="五 20以内的进位加法",
            question=f"8 + {b} = ?",
            answer=ans,
            explanation=f"拆{b}为2和{b-2}，8+2=10，10+{b-2}={ans}",
        )
    for _ in range(5):
        a, b = 7, random.randint(3, 9)
        ans = a + b
        write_question(
            "L2",
            type="计算",
            subtype="7加几（凑十法）",
            knowledge_point="20以内的进位加法",
            textbook_unit="五 20以内的进位加法",
            question=f"7 + {b} = ?",
            answer=ans,
            explanation=f"拆{b}为3和{b-3}，7+3=10，10+{b-3}={ans}",
        )
    for _ in range(5):
        a, b = 6, random.randint(4, 9)
        ans = a + b
        write_question(
            "L2",
            type="计算",
            subtype="6加几（凑十法）",
            knowledge_point="20以内的进位加法",
            textbook_unit="五 20以内的进位加法",
            question=f"6 + {b} = ?",
            answer=ans,
            explanation=f"拆{b}为4和{b-4}，6+4=10，10+{b-4}={ans}",
        )

    # 6. 十几减9（破十法）（15题）
    for _ in range(15):
        a = random.randint(11, 18)
        ans = a - 9
        write_question(
            "L2",
            type="计算",
            subtype="十几减9（破十法）",
            knowledge_point="20以内的退位减法",
            textbook_unit="二 20以内的退位减法",
            question=f"{a} - 9 = ?",
            answer=ans,
            explanation=f"拆{a}为10和{a-10}，10-9=1，1+{a-10}={ans}",
        )

    # 7. 十几减8/7/6（破十法）（15题）
    for _ in range(5):
        a = random.randint(11, 17)
        ans = a - 8
        write_question(
            "L2",
            type="计算",
            subtype="十几减8",
            knowledge_point="20以内的退位减法",
            textbook_unit="二 20以内的退位减法",
            question=f"{a} - 8 = ?",
            answer=ans,
            explanation=f"拆{a}为10和{a-10}，10-8=2，2+{a-10}={ans}",
        )
    for _ in range(5):
        a = random.randint(11, 16)
        ans = a - 7
        write_question(
            "L2",
            type="计算",
            subtype="十几减7",
            knowledge_point="20以内的退位减法",
            textbook_unit="二 20以内的退位减法",
            question=f"{a} - 7 = ?",
            answer=ans,
            explanation=f"拆{a}为10和{a-10}，10-7=3，3+{a-10}={ans}",
        )
    for _ in range(5):
        a = random.randint(11, 15)
        ans = a - 6
        write_question(
            "L2",
            type="计算",
            subtype="十几减6",
            knowledge_point="20以内的退位减法",
            textbook_unit="二 20以内的退位减法",
            question=f"{a} - 6 = ?",
            answer=ans,
            explanation=f"拆{a}为10和{a-10}，10-6=4，4+{a-10}={ans}",
        )

    # 8. 整十数加减（10题）
    for _ in range(5):
        a = random.randint(2, 9) * 10
        b = random.randint(1, (a // 10) - 1) * 10
        write_question(
            "L2",
            type="计算",
            subtype="整十数加减",
            knowledge_point="100以内的加法和减法",
            textbook_unit="六 100以内的加法和减法(一)",
            question=f"{a} + {b} = ?",
            answer=a + b,
            explanation=f"{a//10}个十加{b//10}个十等于{(a+b)//10}个十",
        )
    for _ in range(5):
        a = random.randint(2, 9) * 10
        b = random.randint(1, (a // 10) - 1) * 10
        write_question(
            "L2",
            type="计算",
            subtype="整十数减法",
            knowledge_point="100以内的加法和减法",
            textbook_unit="六 100以内的加法和减法(一)",
            question=f"{a} - {b} = ?",
            answer=a - b,
            explanation=f"{a//10}个十减{b//10}个十等于{(a-b)//10}个十",
        )

    # 9. 人民币简单换算（10题）
    for _ in range(5):
        a = random.randint(1, 9)
        write_question(
            "L2",
            type="填空",
            subtype="人民币换算",
            knowledge_point="认识人民币",
            textbook_unit="五 认识人民币",
            question=f"{a}元 = （ ）角",
            answer=a * 10,
            explanation=f"1元=10角，{a}元={a}×10={a*10}角",
        )
    for _ in range(5):
        a = random.randint(10, 90)
        if a % 10 == 0:
            write_question(
                "L2",
                type="填空",
                subtype="人民币换算",
                knowledge_point="认识人民币",
                textbook_unit="五 认识人民币",
                question=f"{a}角 = （ ）元",
                answer=a // 10,
                explanation=f"10角=1元，{a}角={a//10}元",
            )

    print(f"L2 生成完成：{counters['L2']} 题")


# ============================================================
# L3 应用题与进阶计算
# ============================================================

def gen_L3():
    """生成 L3 难度习题（约100题）"""
    # 1. 5/4/3/2加几（凑十法）（10题）
    for _ in range(10):
        a = random.randint(2, 5)
        b = random.randint(5, 9)
        ans = a + b
        write_question(
            "L3",
            type="计算",
            subtype="小数凑大数",
            knowledge_point="20以内的进位加法",
            textbook_unit="五 20以内的进位加法",
            question=f"{a} + {b} = ?",
            answer=ans,
            explanation=f"可以想{b}+{a}={ans}，因为加法交换位置结果不变",
        )

    # 2. 十几减5/4/3/2（10题）
    for _ in range(10):
        a = random.randint(11, 14)
        b = random.randint(2, 5)
        ans = a - b
        write_question(
            "L3",
            type="计算",
            subtype="十几减小数",
            knowledge_point="20以内的退位减法",
            textbook_unit="二 20以内的退位减法",
            question=f"{a} - {b} = ?",
            answer=ans,
            explanation=f"{a}-{b}={ans}",
        )

    # 3. 两位数加一位数（进位）（10题）
    for _ in range(10):
        a = random.randint(11, 89)
        b = random.randint(10 - (a % 10), 9)  # 保证进位
        ans = a + b
        write_question(
            "L3",
            type="计算",
            subtype="两位数加一位数（进位）",
            knowledge_point="100以内的加法和减法",
            textbook_unit="六 100以内的加法和减法(一)",
            question=f"{a} + {b} = ?",
            answer=ans,
            explanation=f"个位{a%10}+{b}={a%10+b}，写{(a%10+b)%10}进1，十位{a//10}+1={ans//10}，所以是{ans}",
        )

    # 4. 两位数减一位数（退位）（10题）
    for _ in range(10):
        a = random.randint(11, 99)
        while a % 10 >= 9:  # 确保个位小于9，否则无法构造退位
            a = random.randint(11, 99)
        b = random.randint((a % 10) + 1, 9)  # 保证退位
        ans = a - b
        write_question(
            "L3",
            type="计算",
            subtype="两位数减一位数（退位）",
            knowledge_point="100以内的加法和减法",
            textbook_unit="六 100以内的加法和减法(一)",
            question=f"{a} - {b} = ?",
            answer=ans,
            explanation=f"个位{a%10}不够减{b}，拆{a}为{a-10}和10，10-{b}={10-b}，{a-10}+{10-b}={ans}",
        )

    # 5. 应用题——求和（10题）
    templates = [
        ("小明有{0}个苹果，小红有{1}个苹果，他们一共有多少个苹果？", "求一共用加法"),
        ("树上有{0}只鸟，又飞来了{1}只，现在树上一共有多少只鸟？", "求一共用加法"),
        ("妈妈买了{0}个橘子，爸爸又买了{1}个，家里一共有多少个橘子？", "求一共用加法"),
    ]
    for _ in range(10):
        a = random.randint(1, 9)
        b = random.randint(1, 9)
        template, explanation = random.choice(templates)
        question = template.format(a, b)
        ans = a + b
        write_question(
            "L3",
            type="应用题",
            subtype="求和",
            knowledge_point="加法应用",
            textbook_unit="应用题",
            question=question,
            answer=ans,
            explanation=f"{explanation}：{a}+{b}={ans}",
        )

    # 6. 应用题——求差（10题）
    templates = [
        ("小明有{0}个糖果，给了小红{1}个，还剩多少个？", "求还剩用减法"),
        ("树上有{0}只鸟，飞走了{1}只，还剩多少只？", "求还剩用减法"),
        ("停车场有{0}辆车，开走了{1}辆，还剩多少辆？", "求还剩用减法"),
    ]
    for _ in range(10):
        a = random.randint(5, 15)
        b = random.randint(1, a - 1)
        template, explanation = random.choice(templates)
        question = template.format(a, b)
        ans = a - b
        write_question(
            "L3",
            type="应用题",
            subtype="求差",
            knowledge_point="减法应用",
            textbook_unit="应用题",
            question=question,
            answer=ans,
            explanation=f"{explanation}：{a}-{b}={ans}",
        )

    # 7. 应用题——比多少（10题）
    templates = [
        ("小明有{0}支铅笔，小红有{1}支铅笔，小明比小红多几支？", "求谁比谁多用减法"),
        ("树上有{0}个苹果，地上有{1}个苹果，树上比地上多几个？", "求谁比谁多用减法"),
    ]
    for _ in range(10):
        a = random.randint(5, 15)
        b = random.randint(1, a - 1)
        template, explanation = random.choice(templates)
        question = template.format(a, b)
        ans = a - b
        write_question(
            "L3",
            type="应用题",
            subtype="比多少",
            knowledge_point="比较应用",
            textbook_unit="应用题",
            question=question,
            answer=ans,
            explanation=f"{explanation}：{a}-{b}={ans}",
        )

    # 8. 比较大小（10题）
    for _ in range(10):
        a = random.randint(11, 99)
        b = random.randint(11, 99)
        if a != b:
            symbol = ">" if a > b else "<"
            write_question(
                "L3",
                type="填空",
                subtype="比较大小",
                knowledge_point="数的顺序比较",
                textbook_unit="四 100以内数的认识",
                question=f"{a} （ ） {b}",
                answer=symbol,
                explanation=f"先比十位，{a//10} {'>' if a//10 > b//10 else '<'} {b//10}，所以{a} {symbol} {b}",
            )

    # 9. 人民币计算（10题）
    for _ in range(10):
        a = random.randint(1, 5)
        b = random.randint(1, 5)
        write_question(
            "L3",
            type="应用题",
            subtype="人民币计算",
            knowledge_point="认识人民币",
            textbook_unit="五 认识人民币",
            question=f"一个文具盒{a}元，一支铅笔{b}角，一共要付多少钱？（用'几元几角'回答）",
            answer=f"{a}元{b}角",
            explanation=f"{a}元+{b}角={a}元{b}角，单位不同不能直接加数字",
        )

    # 10. 带括号计算（10题）
    for _ in range(10):
        a = random.randint(10, 20)
        b = random.randint(1, a - 5)
        c = random.randint(1, a - b - 1)
        ans = a - (b + c)
        write_question(
            "L3",
            type="计算",
            subtype="带括号计算",
            knowledge_point="带括号运算",
            textbook_unit="六 100以内的加法和减法(一)",
            question=f"{a} - ({b} + {c}) = ?",
            answer=ans,
            explanation=f"先算括号里{b}+{c}={b+c}，再算{a}-{b+c}={ans}",
        )

    print(f"L3 生成完成：{counters['L3']} 题")


# ============================================================
# L4-L5 拓展挑战（两步应用题/找规律/综合）
# ============================================================

def gen_L4_L5():
    """生成 L4-L5 难度习题（约50题）"""
    # 1. 两步应用题（15题）
    templates = [
        ("商店有{0}个球，上午卖出{1}个，下午又进了{2}个，现在有多少个球？", "先减后加"),
        ("小明有{0}颗糖，吃掉了{1}颗，妈妈又给了他{2}颗，现在有多少颗糖？", "先减后加"),
        ("停车场有{0}辆车，开来了{1}辆，又开走了{2}辆，现在有多少辆？", "先加后减"),
    ]
    for _ in range(15):
        a = random.randint(15, 30)
        b = random.randint(3, 10)
        c = random.randint(3, 10)
        # 确保题目有意义（结果为正）
        if a - b + c > 0:
            template, explanation = random.choice(templates)
            question = template.format(a, b, c)
            ans = a - b + c
            write_question(
                "L4",
                type="应用题",
                subtype="两步计算",
                knowledge_point="综合应用",
                textbook_unit="应用题",
                question=question,
                answer=ans,
                explanation=f"{explanation}：{a}-{b}={a-b}，{a-b}+{c}={ans}",
            )

    # 2. 找规律——数字（10题）
    for _ in range(10):
        # 等差数列
        start = random.randint(1, 5)
        step = random.randint(2, 4)
        seq = [start + step * i for i in range(4)]
        ans = start + step * 4
        write_question(
            "L4",
            type="填空",
            subtype="数字规律",
            knowledge_point="找规律",
            textbook_unit="七 找规律",
            question=f"找规律填数：{seq[0]}，{seq[1]}，{seq[2]}，{seq[3]}，（ ）",
            answer=ans,
            explanation=f"每次加{step}，{seq[3]}+{step}={ans}",
        )

    # 3. 找规律——图形（5题）
    patterns = [
        ("○ △ ○ △ ○ △ （ ）", "△", "圆形和三角形交替"),
        ("□ □ ○ □ □ ○ □ □ （ ）", "○", "两个方块一个圆形循环"),
        ("▲ ▲ ▲ ▲ ▲ ▲ （ ）", "▲", "全是三角形"),
    ]
    for pat, ans, explanation in patterns:
        write_question(
            "L4",
            type="填空",
            subtype="图形规律",
            knowledge_point="找规律",
            textbook_unit="七 找规律",
            question=f"找规律：{pat}",
            answer=ans,
            explanation=explanation,
        )
    # 再生成2题随机颜色规律
    for _ in range(2):
        colors = ["红", "黄", "蓝"]
        pat = random.sample(colors, 3)
        seq = (pat * 3)[:5]  # 取前5个
        ans = pat[2]  # 第6个应该是第3个颜色
        write_question(
            "L4",
            type="填空",
            subtype="颜色规律",
            knowledge_point="找规律",
            textbook_unit="七 找规律",
            question=f"找规律：{' '.join(seq)} （ ）",
            answer=ans,
            explanation=f"{'、'.join(pat)}循环，第6个是{ans}",
        )

    # 4. 综合计算（10题）
    for _ in range(10):
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        c = random.randint(1, 10)
        d = random.randint(1, 10)
        # 设计有意义的综合算式
        if random.choice([True, False]):
            # a + b - c + d
            ans = a + b - c + d
            if ans > 0:
                write_question(
                    "L5",
                    type="计算",
                    subtype="四步混合",
                    knowledge_point="综合运算",
                    textbook_unit="总复习",
                    question=f"{a} + {b} - {c} + {d} = ?",
                    answer=ans,
                    explanation=f"从左到右依次算：{a}+{b}={a+b}，{a+b}-{c}={a+b-c}，{a+b-c}+{d}={ans}",
                )
        else:
            # a + (b + c) - d
            ans = a + (b + c) - d
            if ans > 0:
                write_question(
                    "L5",
                    type="计算",
                    subtype="带括号综合",
                    knowledge_point="综合运算",
                    textbook_unit="总复习",
                    question=f"{a} + ({b} + {c}) - {d} = ?",
                    answer=ans,
                    explanation=f"先算括号：{b}+{c}={b+c}，再算{a}+{b+c}={a+b+c}，最后{a+b+c}-{d}={ans}",
                )

    # 5. 开放性问题（10题）
    for _ in range(10):
        a = random.randint(5, 15)
        b = random.randint(1, a - 1)
        ans = a - b
        write_question(
            "L5",
            type="应用题",
            subtype="开放问题",
            knowledge_point="综合应用",
            textbook_unit="总复习",
            question=f"小明有{a}颗糖，他给了小红一些后还剩{ans}颗。小明给了小红几颗糖？",
            answer=b,
            explanation=f"原来有{a}颗，还剩{ans}颗，给了{a}-{ans}={b}颗",
        )

    print(f"L4-L5 生成完成：{counters['L4']} 题（L4）+ {counters['L5']} 题（L5）")


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 60)
    print("人教版数学一年级习题生成器")
    print("=" * 60)
    print()

    gen_L1()
    gen_L2()
    gen_L3()
    gen_L4_L5()

    # 关闭所有文件
    for f in files.values():
        f.close()

    total = sum(counters.values())
    print()
    print("=" * 60)
    print("生成统计：")
    print(f"  L1 基础计算：{counters['L1']} 题")
    print(f"  L2 标准计算：{counters['L2']} 题")
    print(f"  L3 应用进阶：{counters['L3']} 题")
    print(f"  L4 拓展挑战：{counters['L4']} 题")
    print(f"  L5 综合挑战：{counters['L5']} 题")
    print(f"  总计：{total} 题")
    print("=" * 60)
    print()
    print("输出文件：")
    for fname in ["L1-basic.jsonl", "L2-standard.jsonl", "L3-application.jsonl", "L4-L5-challenge.jsonl"]:
        fpath = OUTPUT_DIR / fname
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                count = sum(1 for _ in f)
            print(f"  {fname}: {count} 题")
    print()


if __name__ == "__main__":
    main()
