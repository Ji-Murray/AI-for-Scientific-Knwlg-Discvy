"""生成小组展示 PPT（DSC6020 Topic 4）。运行: python scripts/make_slides.py"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

# ----------------------------------------------------------------------------
# 主题
# ----------------------------------------------------------------------------
NAVY = RGBColor(0x0E, 0x17, 0x26)
INK = RGBColor(0x0F, 0x17, 0x2A)
MUTED = RGBColor(0x64, 0x74, 0x8B)
INDIGO = RGBColor(0x4F, 0x46, 0xE5)
TEAL = RGBColor(0x14, 0xB8, 0xA6)
AMBER = RGBColor(0xF5, 0x9E, 0x0B)
ROSE = RGBColor(0xF4, 0x3F, 0x5E)
SLATE = RGBColor(0x94, 0xA3, 0xB8)
LIGHT = RGBColor(0xF1, 0xF5, 0xF9)
BORDER = RGBColor(0xE2, 0xE8, 0xF0)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SOFT = RGBColor(0xF8, 0xFA, 0xFC)

FONT = "PingFang SC"
SW, SH = 13.333, 7.5

HEX = {"ink": "#0F172A", "muted": "#64748B", "indigo": "#4F46E5",
       "teal": "#14B8A6", "amber": "#F59E0B", "rose": "#F43F5E",
       "slate": "#94A3B8", "border": "#E2E8F0"}
METHOD_COLOR = {"direct": HEX["slate"], "cot": HEX["indigo"],
                "selfcons": HEX["teal"], "pot": HEX["amber"],
                "adaptive": HEX["rose"]}

OUT = os.path.join("report", "slides")
os.makedirs(OUT, exist_ok=True)

# 实验数据（src.analysis 重新判分，n=100 / 方法 / 子集，qwen-plus, seed=42）
ACC = {
    "phys":   {"direct": 0.13, "cot": 0.23, "selfcons": 0.22, "pot": 0.29, "adaptive": 0.24},
    "chem":   {"direct": 0.30, "cot": 0.40},
    "matsci": {"direct": 0.06, "cot": 0.26},
}
TOK_ACC = {"direct": (189, 0.13), "cot": (1129, 0.23), "selfcons": (5843, 0.22),
           "pot": (3194, 0.29), "adaptive": (1414, 0.24)}
ERRORS = {"Knowledge": 359, "Calculation / rounding": 310,
          "Format / extract": 16, "Comprehension": 2}
ROUTES = {"CoT": (18, 60), "PoT": (6, 15), "Direct": (0, 1)}

# ----------------------------------------------------------------------------
# matplotlib 图
# ----------------------------------------------------------------------------
def _style_axes(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(HEX["border"])
    ax.tick_params(colors=HEX["muted"], labelsize=11)
    ax.yaxis.grid(True, color=HEX["border"], linewidth=0.8)
    ax.set_axisbelow(True)


def chart_results(path):
    fig, (a, b) = plt.subplots(1, 2, figsize=(11.2, 4.0), dpi=200)
    fig.patch.set_facecolor("white")
    subs, labels = ["phys", "chem", "matsci"], ["Physics", "Chemistry", "MatSci"]
    x, w = range(len(subs)), 0.36
    for i, m in enumerate(["direct", "cot"]):
        vals = [ACC[s][m] for s in subs]
        bars = a.bar([xi + (i - 0.5) * w for xi in x], vals, width=w,
                     color=METHOD_COLOR[m], label=m.capitalize(), zorder=3)
        for r, v in zip(bars, vals):
            a.text(r.get_x() + r.get_width() / 2, v + 0.012, f"{v:.0%}",
                   ha="center", va="bottom", fontsize=10, color=HEX["ink"])
    a.set_xticks(list(x)); a.set_xticklabels(labels)
    a.set_ylim(0, 0.5); a.set_yticks([0, 0.1, 0.2, 0.3, 0.4, 0.5])
    a.set_yticklabels([f"{int(t*100)}%" for t in a.get_yticks()])
    a.set_title("Direct vs. CoT  (n=100 each)", fontsize=13, color=HEX["ink"],
                fontweight="bold", loc="left")
    a.legend(frameon=False, fontsize=10, loc="upper right")
    _style_axes(a)

    methods = ["direct", "cot", "selfcons", "pot", "adaptive"]
    vals = [ACC["phys"][m] for m in methods]
    bars = b.bar(range(len(methods)), vals, width=0.62,
                 color=[METHOD_COLOR[m] for m in methods], zorder=3)
    best = max(range(len(vals)), key=lambda i: vals[i])
    for i, (r, v) in enumerate(zip(bars, vals)):
        b.text(r.get_x() + r.get_width() / 2, v + 0.012, f"{v:.0%}",
               ha="center", va="bottom", fontsize=10, color=HEX["ink"],
               fontweight="bold" if i == best else "normal")
    b.set_xticks(range(len(methods)))
    b.set_xticklabels(["Direct", "CoT", "SelfCons", "PoT", "Adaptive"], fontsize=10.5)
    b.set_ylim(0, 0.5); b.set_yticks([0, 0.1, 0.2, 0.3, 0.4, 0.5])
    b.set_yticklabels([f"{int(t*100)}%" for t in b.get_yticks()])
    b.set_title("SciBench-Physics: all methods", fontsize=13,
                color=HEX["ink"], fontweight="bold", loc="left")
    _style_axes(b)
    fig.tight_layout(pad=1.4)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def chart_cost(path):
    fig, ax = plt.subplots(figsize=(7.6, 4.6), dpi=200)
    fig.patch.set_facecolor("white")
    for m, (tok, acc) in TOK_ACC.items():
        ax.scatter(tok, acc, s=260, color=METHOD_COLOR[m], zorder=3,
                   edgecolor="white", linewidth=1.5)
        ax.annotate(m, (tok, acc), ha="center", va="center",
                    fontsize=9.5, color="white", fontweight="bold", zorder=4)
        ax.annotate(f"{acc:.0%} · {tok:,} tok", (tok, acc + 0.012),
                    ha="center", va="bottom", fontsize=9.5, color=HEX["muted"])
    ax.set_xscale("log")
    ax.set_xlim(120, 8000); ax.set_ylim(0.08, 0.34)
    ax.set_yticks([0.10, 0.15, 0.20, 0.25, 0.30])
    ax.set_yticklabels([f"{int(t*100)}%" for t in ax.get_yticks()])
    ax.set_xlabel("Average tokens per question (cost proxy, log scale)",
                  fontsize=11, color=HEX["muted"])
    ax.set_ylabel("Accuracy (SciBench-Physics)", fontsize=11, color=HEX["muted"])
    ax.set_title("Accuracy vs. Token cost", fontsize=14, color=HEX["ink"],
                 fontweight="bold", loc="left")
    ax.xaxis.grid(True, color=HEX["border"], linewidth=0.8)
    _style_axes(ax)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def chart_errors(path):
    fig, ax = plt.subplots(figsize=(7.8, 3.8), dpi=200)
    fig.patch.set_facecolor("white")
    names, vals = list(ERRORS.keys()), list(ERRORS.values())
    colors = [HEX["indigo"], HEX["amber"], HEX["rose"], HEX["teal"]]
    bars = ax.barh(range(len(names)), vals, color=colors, zorder=3, height=0.6)
    for r, v in zip(bars, vals):
        ax.text(v + 6, r.get_y() + r.get_height() / 2, str(v), va="center",
                fontsize=11, color=HEX["ink"], fontweight="bold")
    ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=10.5)
    ax.invert_yaxis(); ax.set_xlim(0, 410)
    ax.set_xlabel("Number of errors (heuristic, to be reviewed)", fontsize=10.5,
                  color=HEX["muted"])
    ax.set_title("Error type distribution", fontsize=14, color=HEX["ink"],
                 fontweight="bold", loc="left")
    ax.xaxis.grid(True, color=HEX["border"], linewidth=0.8)
    _style_axes(ax)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def chart_routes(path):
    fig, ax = plt.subplots(figsize=(7.6, 3.6), dpi=200)
    fig.patch.set_facecolor("white")
    routes = list(ROUTES.keys())
    correct = [ROUTES[r][0] for r in routes]
    wrong = [ROUTES[r][1] for r in routes]
    y = range(len(routes))
    ax.barh(y, correct, color=HEX["teal"], zorder=3, height=0.55, label="Correct")
    ax.barh(y, wrong, left=correct, color=HEX["slate"], zorder=3, height=0.55, label="Wrong")
    for i, (c, wr) in enumerate(zip(correct, wrong)):
        tot = c + wr
        ax.text(tot + 1.2, i, f"{tot} q  ·  {c} correct ({c/tot:.0%})",
                va="center", fontsize=10.5, color=HEX["ink"])
    ax.set_yticks(list(y)); ax.set_yticklabels(routes, fontsize=11)
    ax.invert_yaxis(); ax.set_xlim(0, 100)
    ax.set_xlabel("Questions routed", fontsize=10.5, color=HEX["muted"])
    ax.set_title("Adaptive routing outcome", fontsize=14, color=HEX["ink"],
                 fontweight="bold", loc="left")
    ax.legend(frameon=False, fontsize=10, loc="lower right")
    ax.xaxis.grid(True, color=HEX["border"], linewidth=0.8)
    _style_axes(ax)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ----------------------------------------------------------------------------
# python-pptx 辅助
# ----------------------------------------------------------------------------
def _ea_font(run, font=FONT):
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", font)


def style_run(run, size, bold=False, color=INK, font=FONT):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font
    _ea_font(run, font)


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP,
         align=PP_ALIGN.LEFT, line=1.0):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = p.get("align", align)
        para.line_spacing = p.get("line", line)
        if p.get("space_after") is not None:
            para.space_after = Pt(p["space_after"])
        for (t, size, bold, color) in p["runs"]:
            r = para.add_run()
            r.text = t
            style_run(r, size, bold, color)
    return tb


def rect(slide, x, y, w, h, fill, line=None, radius=0.08):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                   Inches(x), Inches(y), Inches(w), Inches(h))
    shape.adjustments[0] = radius
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(1)
    shape.shadow.inherit = False
    return shape


def card(slide, x, y, w, h, title, body, accent, tsize=15, bsize=12):
    rect(slide, x, y, w, h, SOFT, line=BORDER, radius=0.06)
    rect(slide, x, y, 0.09, h, accent, radius=0.5)
    text(slide, x + 0.32, y + 0.22, w - 0.5, h - 0.34, [
        {"runs": [(title, tsize, True, INK)], "space_after": 6},
        {"runs": [(body, bsize, False, MUTED)], "line": 1.12},
    ])


def header(slide, kicker, title, idx):
    rect(slide, 0, 0, SW, 0.16, INDIGO, radius=0)
    text(slide, 0.75, 0.55, 9.0, 0.35, [{"runs": [(kicker, 12, True, INDIGO)]}])
    text(slide, 0.75, 0.9, 11.5, 0.9, [{"runs": [(title, 30, True, INK)]}])
    rect(slide, 0.78, 1.72, 1.1, 0.06, INDIGO, radius=0)
    text(slide, 0.75, 7.08, 9.0, 0.3, [{"runs": [
        ("DSC6020 · Topic 4 · LLM 科学推理推理时策略", 10, False, MUTED)]}])
    text(slide, 11.6, 7.08, 1.0, 0.3, [{"runs": [(f"{idx:02d}", 11, True, MUTED)],
                                          "align": PP_ALIGN.RIGHT}])


def new_slide(prs, bg=WHITE):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    rect(s, -0.1, -0.1, SW + 0.2, SH + 0.2, bg, radius=0)
    return s


def bullet_list(slide, x, y, w, items, size=13.5, gap=10, color=INK, dot=INDIGO):
    paras = []
    for it in items:
        paras.append({"runs": [("●  ", size - 3, True, dot), (it, size, False, color)],
                      "space_after": gap, "line": 1.15})
    return text(slide, x, y, w, 4.0, paras)


def add_table(slide, x, y, w, data, col_w, row_h=0.5, header_fill=NAVY,
              first_col_bold=True, fsize=13):
    rows, cols = len(data), len(data[0])
    gt = slide.shapes.add_table(rows, cols, Inches(x), Inches(y),
                                Inches(w), Inches(row_h * rows))
    tbl = gt.table
    tbl.first_row = True
    tbl.horz_banding = False
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i in range(rows):
        tbl.rows[i].height = Inches(row_h)
        for j in range(cols):
            cell = tbl.cell(i, j)
            cell.margin_left = Inches(0.12)
            cell.margin_right = Inches(0.1)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if i == 0:
                cell.fill.fore_color.rgb = header_fill
                col, bold = WHITE, True
            else:
                cell.fill.fore_color.rgb = WHITE if i % 2 else LIGHT
                col, bold = INK, (first_col_bold and j == 0)
            cell.text = ""
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
            r = p.add_run()
            r.text = str(data[i][j])
            style_run(r, fsize, bold, col)
    return tbl


# ----------------------------------------------------------------------------
# 构建幻灯片
# ----------------------------------------------------------------------------
def build():
    prs = Presentation()
    prs.slide_width = Inches(SW)
    prs.slide_height = Inches(SH)

    # ---------- 1. 标题 ----------
    s = new_slide(prs, NAVY)
    rect(s, 0, 0, 0.28, SH, INDIGO, radius=0)
    rect(s, 0.9, 1.55, 0.16, 0.5, TEAL, radius=0.5)
    text(s, 1.2, 1.5, 10.5, 0.4, [{"runs": [
        ("DSC6020 · AI for Scientific Knowledge Discovery · Topic 4", 14, True, TEAL)]}])
    text(s, 0.95, 2.15, 11.5, 2.0, [
        {"runs": [("LLM 科学推理的", 44, True, WHITE)], "space_after": 4},
        {"runs": [("推理时策略评测", 44, True, WHITE)]},
    ])
    text(s, 0.98, 4.15, 11.5, 0.9, [{"runs": [
        ("Direct · Chain-of-Thought · Self-Consistency · "
         "Program-of-Thought · 自适应路由", 17, False, SLATE)]}])
    rect(s, 0.98, 5.05, 6.2, 0.03, RGBColor(0x33, 0x41, 0x55), radius=0)
    text(s, 0.98, 5.25, 11.8, 1.2, [
        {"runs": [("基座模型  ", 13, False, SLATE), ("qwen-plus", 13, True, WHITE),
                  ("     基准  ", 13, False, SLATE),
                  ("SciBench (Physics / Chemistry) + MatSciBench", 13, True, WHITE)],
         "space_after": 8},
        {"runs": [("方法  ", 13, False, SLATE),
                  ("5 种推理时策略 · 每种 ≥100 题 · 零微调 · 全结果落盘可复现",
                   13, True, WHITE)]},
    ])
    text(s, 9.9, 6.6, 3.0, 0.4, [{"runs": [
        ("小组展示 · 2026.11.19", 12, True, TEAL)], "align": PP_ALIGN.RIGHT}])

    # ---------- 2. 一页看懂 ----------
    s = new_slide(prs)
    header(s, "TL;DR", "一页看懂：我们在问什么、得到了什么", 2)
    text(s, 0.8, 2.02, 12.0, 1.0, [{"runs": [
        ("研究问题：不训练、只靠推理时策略，能否显著提升 LLM 解大学科学题的能力？"
         "哪条路线性价比最高？", 15, False, INK)], "line": 1.15}])
    stats = [
        ("CoT 全面优于 Direct", "物理/化学各 +10pt", "材料科学 +20pt", "稳定基线的性价比最高", INDIGO),
        ("物理最强单方法：PoT", "29%", "比 CoT +6pt，但 token ≈ 3×", "重计算/符号题的利器", AMBER),
        ("Self-Consistency 未跑赢", "22%", "≈5× token 却 ≤ CoT", "多采样投票性价比偏低", TEAL),
    ]
    cw, gap = 3.75, 0.34
    for i, (t, big, sub, foot, col) in enumerate(stats):
        x = 0.8 + i * (cw + gap)
        rect(s, x, 3.15, cw, 2.35, SOFT, line=BORDER, radius=0.05)
        rect(s, x, 3.15, cw, 0.1, col, radius=0)
        text(s, x + 0.3, 3.45, cw - 0.5, 1.0, [
            {"runs": [(t, 15, True, INK)], "space_after": 6},
            {"runs": [(big, 30, True, col)], "space_after": 2},
            {"runs": [(sub, 12, False, MUTED)]},
        ])
        text(s, x + 0.3, 4.92, cw - 0.5, 0.5, [{"runs": [(foot, 11, True, col)]}])
    rect(s, 0.8, 5.85, 11.75, 0.85, RGBColor(0xEE, 0xF2, 0xFF), radius=0.05)
    text(s, 1.05, 5.95, 11.3, 0.7, [{"runs": [
        ("一句话结论：", 13.5, True, INDIGO),
        ("CoT 是稳健基线；PoT 在重计算题上更强但更贵；"
         "自适应路由是“精度–成本”的折中方向，但规则还偏保守。", 13.5, False, INK)],
        "line": 1.1}], anchor=MSO_ANCHOR.MIDDLE)

    # ---------- 3. 背景与动机 ----------
    s = new_slide(prs)
    header(s, "MOTIVATION", "背景与动机：为什么要研究推理时策略", 3)
    card(s, 0.8, 2.05, 5.75, 2.0, "LLM 做科学题的难点",
         "多步数值计算、符号推导、单位与精确最终答案；一步算错就全错，"
         "“看起来会”不代表“答得对”。", INDIGO)
    card(s, 6.75, 2.05, 5.8, 2.0, "两条提升路线",
         "训练时（微调 / RLHF）成本高、需数据；推理时（提示 / 采样 / 工具）"
         "零训练、可复现、按需付费。", TEAL)
    text(s, 0.8, 4.35, 11.75, 0.4, [{"runs": [
        ("本项目聚焦推理时策略，把问题拆成 3 个子问题：", 15, True, INK)]}])
    qs = [
        ("Q1  结构化推理值不值？", "Chain-of-Thought 相比直接作答，能提升多少准确率？"),
        ("Q2  额外算力值不值？", "多采样投票（Self-Consistency）与代码求解（PoT），精度增益能否覆盖成本？"),
        ("Q3  能否按需分配？", "用轻量路由在预算内自动选择策略，能否兼顾精度与成本？"),
    ]
    for i, (h, b) in enumerate(qs):
        x = 0.8 + i * 3.92
        rect(s, x, 4.95, 3.83, 1.75, WHITE, line=BORDER, radius=0.05)
        text(s, x + 0.28, 5.17, 3.3, 1.4, [
            {"runs": [(h, 14, True, INDIGO)], "space_after": 6},
            {"runs": [(b, 12, False, MUTED)], "line": 1.12},
        ])

    # ---------- 4. 任务与数据 ----------
    s = new_slide(prs)
    header(s, "TASK & DATA", "任务与数据：两个大学水平科学基准", 4)
    data = [
        ["基准", "子集", "题量", "主要题型", "难度定位"],
        ["SciBench", "Physics", "100", "数值 / 符号推导", "大学物理，多步计算"],
        ["SciBench", "Chemistry", "100", "数值 / 符号", "大学化学，定量为主"],
        ["MatSciBench", "Materials (all)", "100", "概念 / 数值 / 符号", "材料科学，覆盖广"],
    ]
    add_table(s, 0.8, 2.1, 11.75, data, [2.0, 2.1, 1.2, 3.0, 3.45], row_h=0.62, fsize=13)
    card(s, 0.8, 4.9, 5.75, 1.85, "统一中间格式",
         "全部加载为 {id, question, gold, answer_type, subject}；"
         "按 answer_type 分派数值 / 符号 / 选择判分。", INDIGO, bsize=12)
    card(s, 6.75, 4.9, 5.8, 1.85, "统一答题协议",
         "强制模型把最终答案放进 \\boxed{...} 或 FINAL ANSWER 行，"
         "使抽取与判分对 5 种方法完全一致。", TEAL, bsize=12)
    text(s, 0.8, 6.7, 11.75, 0.3, [{"runs": [
        ("每题 100 题 · 覆盖物理 / 化学 / 材料 三域 · 同一基座模型贯穿全部实验",
         11.5, False, MUTED)]}])

    # ---------- 5. 实验设置 ----------
    s = new_slide(prs)
    header(s, "SETUP", "实验设置与评测协议", 5)
    card(s, 0.8, 2.05, 3.75, 2.2, "基座模型",
         "qwen-plus（DashScope，OpenAI 兼容接口）\n"
         "temperature=0；SelfCons=0.7\nmax_tokens=8192；seed=42", INDIGO, bsize=11.5)
    card(s, 4.78, 2.05, 3.75, 2.2, "答题协议 final-answer-v2",
         "强制 \\boxed{...} / FINAL ANSWER 行\n"
         "截断时判为抽取失败，不算答错\n同一提示模板贯穿所有方法", TEAL, bsize=11.5)
    card(s, 8.76, 2.05, 3.8, 2.2, "判分 grading.py",
         "数值：相对误差 < 1e-4\n"
         "符号：sympy 化简后比较\n选择/开放：归一化匹配", AMBER, bsize=11.5)
    text(s, 0.8, 4.55, 11.75, 0.4, [{"runs": [
        ("三个核心指标（分开报告，避免混淆“答错”与“抽不出”）", 15, True, INK)]}])
    metrics = [
        ("Accuracy", "正确率", "正确题数 / 总题数，主指标", INDIGO),
        ("Extract-fail", "抽取失败率", "模型没给出可解析的最终答案", ROSE),
        ("Avg tokens", "平均 token", "作为成本代理，衡量推理开销", TEAL),
    ]
    for i, (en, zh, desc, col) in enumerate(metrics):
        x = 0.8 + i * 3.95
        rect(s, x, 5.1, 3.8, 1.55, SOFT, line=BORDER, radius=0.05)
        text(s, x + 0.28, 5.28, 3.3, 1.2, [
            {"runs": [(en, 17, True, col)], "space_after": 2},
            {"runs": [(zh, 12, True, INK)], "space_after": 4},
            {"runs": [(desc, 11.5, False, MUTED)], "line": 1.1},
        ])

    # ---------- 6. 方法总览 ----------
    s = new_slide(prs)
    header(s, "METHODS", "五种推理时策略", 6)
    methods = [
        ("Direct", "直接作答", "不展示过程，直接输出最终答案。最低成本基线。", SLATE),
        ("CoT", "思维链", "≤5 步简洁推理 → 最终答案。稳健的推理基线。", INDIGO),
        ("Self-Consistency", "多采样投票", "同一 CoT 采样 k=5，答案多数投票（数值按容差聚簇）。", TEAL),
        ("PoT", "程序化推理", "写 Python（sympy），子进程执行取结果；15s 超时，失败回退文本。", AMBER),
        ("Adaptive", "自适应路由", "短/概念→Direct；精确计算/符号→PoT；其余→CoT。", ROSE),
    ]
    positions = [(0.8, 2.05), (4.78, 2.05), (8.76, 2.05), (2.8, 4.55), (6.78, 4.55)]
    for (x, y), (en, zh, desc, col) in zip(positions, methods):
        w = 3.78
        rect(s, x, y, w, 2.05, SOFT, line=BORDER, radius=0.05)
        rect(s, x, y, w, 0.1, col, radius=0)
        text(s, x + 0.28, y + 0.3, w - 0.5, 1.6, [
            {"runs": [(en, 16, True, col)], "space_after": 1},
            {"runs": [(zh, 12.5, True, INK)], "space_after": 7},
            {"runs": [(desc, 11.5, False, MUTED)], "line": 1.12},
        ])
    text(s, 0.8, 6.75, 11.75, 0.3, [{"runs": [
        ("实现约束：所有调用统一走 src/llm.py；结果逐题追加写入 JSONL（含原始输出、tokens、耗时）。",
         11, False, MUTED)]}])

    # ---------- 7. 主结果 ----------
    s = new_slide(prs)
    header(s, "RESULTS", "主结果：CoT 稳定提升，PoT 在物理最强", 7)
    data = [
        ["方法", "Phys", "Chem", "MatSci"],
        ["Direct", "13%", "30%", "6%"],
        ["CoT", "23%", "40%", "26%"],
        ["SelfCons (k=5)", "22%", "—", "—"],
        ["PoT", "29%", "—", "—"],
        ["Adaptive", "24%", "—", "—"],
    ]
    add_table(s, 0.8, 2.15, 4.4, data, [2.1, 0.78, 0.78, 0.74], row_h=0.55, fsize=13)
    s.shapes.add_picture(os.path.join(OUT, "fig_results.png"),
                         Inches(5.35), Inches(2.05), width=Inches(7.3))
    text(s, 0.8, 5.6, 4.4, 1.4, [
        {"runs": [("看点", 12.5, True, INDIGO)], "space_after": 4},
        {"runs": [("CoT 三域全部优于 Direct；物理 PoT 最高 29%；自适应 ≈ CoT。",
                   11.5, False, MUTED)], "line": 1.12},
    ])

    # ---------- 8. 成本 vs 准确率 ----------
    s = new_slide(prs)
    header(s, "COST-ACCURACY", "成本 vs 准确率：谁才是性价比甜点", 8)
    s.shapes.add_picture(os.path.join(OUT, "fig_cost.png"),
                         Inches(0.7), Inches(2.05), width=Inches(7.1))
    insights = [
        ("CoT 是甜点位", "翻倍 token 换 +10~20pt，性价比最高。", INDIGO),
        ("PoT 更贵更强", "精度最高（29%），但 token ≈ 3× CoT。", AMBER),
        ("SelfCons 不划算", "≈5× token，却未超过 CoT（22%）。", TEAL),
        ("Adaptive 居中", "≈CoT 精度，成本介于 CoT 与 PoT 之间。", ROSE),
    ]
    for i, (h, b, col) in enumerate(insights):
        y = 2.1 + i * 1.16
        rect(s, 8.0, y, 4.5, 1.0, SOFT, line=BORDER, radius=0.06)
        rect(s, 8.0, y, 0.08, 1.0, col, radius=0.5)
        text(s, 8.3, y + 0.14, 4.0, 0.8, [
            {"runs": [(h, 13, True, INK)], "space_after": 3},
            {"runs": [(b, 11, False, MUTED)], "line": 1.08},
        ])

    # ---------- 9. 自适应路由 ----------
    s = new_slide(prs)
    header(s, "ADAPTIVE ROUTING", "自适应路由：分配是否合理", 9)
    s.shapes.add_picture(os.path.join(OUT, "fig_routes.png"),
                         Inches(0.7), Inches(2.1), width=Inches(7.0))
    card(s, 7.95, 2.1, 4.55, 1.45, "路由分布",
         "CoT 78 题 / PoT 21 题 / Direct 1 题 —— 规则较保守，多数落到 CoT。",
         ROSE, bsize=11.5)
    card(s, 7.95, 3.7, 4.55, 1.45, "分支表现",
         "CoT 分支 18/78=23%；PoT 分支 6/21=29% —— 重计算分支确有增益。",
         TEAL, bsize=11.5)
    card(s, 7.95, 5.3, 4.55, 1.25, "改进方向",
         "换学习型路由器 + 调阈值，让更多 PoT 适配题走 PoT。", INDIGO, bsize=11.5)
    text(s, 0.8, 6.55, 7.0, 0.5, [{"runs": [
        ("结论：", 12.5, True, INK),
        ("自适应≈CoT（24%），以更接近 CoT 的成本拿到略高精度；但路由偏保守。",
         12, False, MUTED)], "line": 1.12}])

    # ---------- 10. 错误分析 ----------
    s = new_slide(prs)
    header(s, "ERROR ANALYSIS", "错误分析：错在哪、怎么错", 10)
    s.shapes.add_picture(os.path.join(OUT, "fig_errors.png"),
                         Inches(0.7), Inches(2.1), width=Inches(7.0))
    ecards = [
        ("知识 vs 计算是主因", "知识错误 359、计算/舍入 310 占绝大多数；纯格式问题仅 16。", INDIGO),
        ("抽取失败集中在开放题", "MatSci Direct 抽取失败率最高 8%；SciBench 数值题 ≈1%。", ROSE),
        ("典型失败模式", "物理多步推导中途算错；符号题 latex 等价性判定难。", AMBER),
    ]
    for i, (h, b, col) in enumerate(ecards):
        y = 2.1 + i * 1.55
        rect(s, 7.95, y, 4.55, 1.4, SOFT, line=BORDER, radius=0.06)
        rect(s, 7.95, y, 0.08, 1.4, col, radius=0.5)
        text(s, 8.25, y + 0.2, 4.05, 1.05, [
            {"runs": [(h, 13, True, INK)], "space_after": 4},
            {"runs": [(b, 11, False, MUTED)], "line": 1.1},
        ])
    text(s, 0.8, 6.65, 11.5, 0.3, [{"runs": [
        ("注：错误类型为启发式初判，已抽样 40 条人工复核（report/errors_sample_40.csv）。",
         10.5, False, MUTED)]}])

    # ---------- 11. 结论 ----------
    s = new_slide(prs)
    header(s, "TAKEAWAYS", "结论与洞察", 11)
    findings = [
        ("1", "CoT 是稳健基线", "物理 +10 / 化学 +10 / 材料 +20 个百分点，全面优于 Direct。"),
        ("2", "PoT 在物理最强", "29% 为五法最高，但 token ≈ 3× CoT，适合重计算题。"),
        ("3", "SelfCons 不值", "k=5、≈5× token，精度 22% 仍 ≤ CoT，性价比低。"),
        ("4", "自适应是折中", "24% ≈ CoT，成本远低于 PoT/SelfCons；但路由偏保守。"),
        ("5", "题目领域差异大", "化学易（CoT 40%），材料 Direct 仅 6%，格式失败高。"),
    ]
    for i, (n, h, b) in enumerate(findings):
        y = 2.05 + i * 0.98
        rect(s, 0.8, y, 0.75, 0.82, INDIGO, radius=0.1)
        text(s, 0.8, y + 0.12, 0.75, 0.6,
             [{"runs": [(n, 26, True, WHITE)], "align": PP_ALIGN.CENTER}])
        text(s, 1.75, y + 0.02, 10.6, 0.8, [
            {"runs": [(h, 15.5, True, INK)], "space_after": 3},
            {"runs": [(b, 12, False, MUTED)], "line": 1.05},
        ])

    # ---------- 12. 局限与未来 ----------
    s = new_slide(prs)
    header(s, "LIMITATIONS & FUTURE WORK", "局限与未来工作", 12)
    text(s, 0.8, 2.05, 5.7, 0.4, [{"runs": [("局限", 18, True, ROSE)]}])
    bullet_list(s, 0.8, 2.6, 5.7, [
        "仅评测单一基座模型（qwen-plus），未做多模型对比。",
        "SciBench 只覆盖 physics / chemistry，math / qm 未评。",
        "自适应路由为规则而非学习，偏保守。",
        "错误类型为启发式，仍需更大规模人工标注。",
    ], size=13, gap=14, dot=ROSE)
    text(s, 6.75, 2.05, 5.8, 0.4, [{"runs": [("未来工作", 18, True, TEAL)]}])
    bullet_list(s, 6.75, 2.6, 5.8, [
        "学习型路由器：在 token 预算约束下最大化精度。",
        "加入 Solver-Verifier 自检，降低多步计算错误。",
        "扩展 math / qm 子集，并做多模型 / QLoRA 小模型对比。",
        "多种子 + 更大样本，给出置信区间。",
    ], size=13, gap=14, dot=TEAL)

    # ---------- 13. 团队分工 ----------
    s = new_slide(prs)
    header(s, "TEAM", "团队分工与工程实现", 13)
    roles = [
        ("A", "LLM 封装 + 评测流水线", "src/llm.py · src/evaluate.py\n统一调用、重试、并发与结果落盘", INDIGO),
        ("B", "数据 + 判分", "src/data_loaders.py · src/grading.py\n统一格式、数值容差、sympy 比较", TEAL),
        ("C", "Bonus 方法", "src/methods.py\nSelfCons · PoT(subprocess) · Adaptive 路由", AMBER),
        ("D", "分析 + 可视化 + Slides", "src/analysis.py · make_slides.py\n结果表、图、错误分析、展示", ROSE),
    ]
    for i, (k, h, b, col) in enumerate(roles):
        x = 0.8 + (i % 2) * 6.0
        y = 2.1 + (i // 2) * 2.3
        rect(s, x, y, 5.75, 2.0, SOFT, line=BORDER, radius=0.05)
        rect(s, x, y, 0.9, 2.0, col, radius=0.06)
        text(s, x, y + 0.55, 0.9, 0.9,
             [{"runs": [(k, 34, True, WHITE)], "align": PP_ALIGN.CENTER}])
        text(s, x + 1.15, y + 0.28, 4.4, 1.5, [
            {"runs": [(h, 15, True, INK)], "space_after": 8},
            {"runs": [(b, 11.5, False, MUTED)], "line": 1.15},
        ])

    # ---------- 14. 谢谢 ----------
    s = new_slide(prs, NAVY)
    rect(s, 0, 0, 0.28, SH, INDIGO, radius=0)
    rect(s, 0.95, 2.6, 0.16, 0.9, TEAL, radius=0.5)
    text(s, 1.25, 2.55, 10.0, 1.4, [{"runs": [("谢谢 & Q&A", 50, True, WHITE)]}])
    text(s, 1.28, 4.05, 11.0, 1.0, [{"runs": [
        ("代码与结果全部开源可复现 · 欢迎提问与交流", 17, False, SLATE)]}])
    text(s, 1.28, 5.5, 11.0, 1.0, [
        {"runs": [("github.com/Ji-Murray/AI-for-Scientific-Knwlg-Discvy", 13, False, TEAL)],
         "space_after": 6},
        {"runs": [("qwen-plus · final-answer-v2 · seed=42 · n=100/方法/子集", 12, False, SLATE)]},
    ])

    out = os.path.join(OUT, "Topic4_Scientific_Reasoning.pptx")
    prs.save(out)
    print("saved", out)


if __name__ == "__main__":
    chart_results(os.path.join(OUT, "fig_results.png"))
    chart_cost(os.path.join(OUT, "fig_cost.png"))
    chart_errors(os.path.join(OUT, "fig_errors.png"))
    chart_routes(os.path.join(OUT, "fig_routes.png"))
    build()
