"""答案抽取与判分。

数值题：相对误差 < tol 视为正确；
表达式题：sympy 化简后比较；
抽取失败单独标记（extract_fail），不算模型答错。
"""

from __future__ import annotations

import re
from typing import Any

BOXED_RE = re.compile(r"\\boxed\{([^{}]+)\}")
# 处理嵌套大括号的 \\boxed{...}：逐层扫描
_LAST_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE]-?\d+)?")


def extract_answer(raw_output: str, answer_type: str = "numeric") -> str | None:
    """从模型输出中抽取最终答案。

    优先取 \\boxed{...}；否则仅从明确标记的最终答案行抽取数值题答案。
    返回 None 表示抽取失败，避免误取推理过程中的数字。
    """
    m = _find_boxed(raw_output)
    if m:
        return m.strip()
    if answer_type == "numeric":
        final_markers = list(re.finditer(
            r"(?i)(?:final\s+answer|answer)\s*[:：=]", raw_output
        ))
        if final_markers:
            final_text = raw_output[final_markers[-1].end():]
            nums = _LAST_NUM_RE.findall(final_text)
            if nums:
                return nums[-1]
    return None


def _find_boxed(text: str) -> str | None:
    """处理 \\boxed{...} 中可能嵌套大括号的情况。"""
    idx = text.rfind("\\boxed{")
    if idx == -1:
        return None
    depth, start = 0, idx + len("\\boxed{")
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            if depth == 0:
                return text[start:i]
            depth -= 1
    return None


def grade(pred: str | None, gold: str, answer_type: str = "numeric",
          tol: float = 1e-4) -> bool:
    """判定预测是否正确。pred 为 None 直接返回 False（抽取失败）。"""
    if pred is None:
        return False
    pred, gold = pred.strip(), str(gold).strip()
    if pred == gold:
        return True
    if answer_type in ("numeric", "number"):
        return _num_close(pred, gold, tol)
    if answer_type in ("expression", "symbolic"):
        try:  # sympy 惰性导入：数值判分不依赖它
            from sympy import simplify, sympify
            from sympy.parsing.latex import parse_latex
            p = parse_latex(pred) if "\\" in pred else sympify(pred)
            g = parse_latex(gold) if "\\" in gold else sympify(gold)
            diff = simplify(p - g)
            return diff == 0
        except Exception:  # noqa: BLE001
            return _num_close(pred, gold, tol)
    # multiple-choice / open-ended：去空格后子串匹配（保守）
    return pred.lower().replace(" ", "") == gold.lower().replace(" ", "")


def _num_close(pred: str, gold: str, tol: float) -> bool:
    try:
        p, g = float(_to_float_str(pred)), float(_to_float_str(gold))
    except (ValueError, TypeError):
        return False
    if g == 0:
        return abs(p) <= tol
    return abs(p - g) / abs(g) < tol


def _to_float_str(s: str) -> str:
    """去掉逗号、百分号、单位与 latex 残留，得到可 float 的串。"""
    s = s.replace(",", "").replace("%", "").replace("$", "").strip()
    s = re.sub(r"\\(mathrm|text)\{[^}]*\}", "", s)
    m = _LAST_NUM_RE.search(s)
    return m.group(0) if m else s
