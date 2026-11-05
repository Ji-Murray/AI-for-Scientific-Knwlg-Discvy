"""推理方法实现：Direct / CoT / Self-Consistency / PoT / Adaptive / SelfCheck。

每种方法统一签名:
    method(client, item, cfg) -> dict  # {"pred": str|None, "raw": str, "tokens": int, ...}
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from . import prompts
from .grading import extract_answer, grade
from .llm import LLMClient


def run_direct(client: LLMClient, item: dict, cfg: dict) -> dict:
    r = client.complete(prompts.format_prompt(prompts.DIRECT, item["question"]),
                        system=prompts.SYSTEM)
    return _pack(r, item, answer_type=item["answer_type"])


def run_cot(client: LLMClient, item: dict, cfg: dict) -> dict:
    r = client.complete(prompts.format_prompt(prompts.COT, item["question"]),
                        system=prompts.SYSTEM)
    return _pack(r, item, answer_type=item["answer_type"])


def run_pot(client: LLMClient, item: dict, cfg: dict) -> dict:
    """Program-of-Thought：先让模型写代码并本地执行，失败再退回文本答案。"""
    r = client.complete(prompts.format_prompt(prompts.POT, item["question"]),
                        system=prompts.SYSTEM)
    exec_result = _exec_python(r.text)
    if exec_result is not None:
        pred = str(exec_result).strip()
        raw = r.text + f"\n[EXEC RESULT] {pred}"
    else:
        pred = extract_answer(r.text, item["answer_type"])
        raw = r.text + "\n[EXEC FAILED, fallback to boxed]"
    return {"pred": pred, "raw": raw, "tokens": r.tokens, "latency_s": r.latency_s,
            "exec_ok": exec_result is not None}


def run_selfcons(client: LLMClient, item: dict, cfg: dict) -> dict:
    """Self-Consistency：同一 CoT 提示采样 k 次，对抽取出的答案投票。"""
    k = int(cfg.get("k", 5))
    temp = float(cfg.get("temperature", 0.7))
    preds: list[str | None] = []
    total_tokens = 0
    raws = []
    for j in range(k):
        r = client.complete(prompts.format_prompt(prompts.COT, item["question"]),
                            system=prompts.SYSTEM, temperature=temp, seed=1000 + j)
        preds.append(extract_answer(r.text, item["answer_type"]))
        raws.append(r.text)
        total_tokens += r.tokens
    # 归一化后投票：数值答案按容差归簇
    pred = _vote(preds, item)
    return {"pred": pred, "raw": "\n---\n".join(raws), "tokens": total_tokens,
            "latency_s": 0.0, "k": k}


def run_selfcheck(client: LLMClient, item: dict, cfg: dict) -> dict:
    """Solver–Verifier：先 CoT 求解，再让模型自检一次。"""
    first = run_cot(client, item, cfg)
    r = client.complete(prompts.format_prompt(
        prompts.SELF_CHECK, item["question"], answer=first["pred"] or "N/A"),
        system=prompts.SYSTEM)
    pred = extract_answer(r.text, item["answer_type"]) or first["pred"]
    return {"pred": pred, "raw": first["raw"] + "\n[VERIFY]\n" + r.text,
            "tokens": first["tokens"] + r.tokens, "latency_s": 0.0}


def run_adaptive(client: LLMClient, item: dict, cfg: dict) -> dict:
    """自适应路由：先判断题目的推理需求，再派给 cheapest-enough 方法。"""
    mode = str(cfg.get("rules", "heuristic"))
    if mode == "heuristic":
        route = _heuristic_route(item)
        routed_by = "rule"
    else:
        r = client.complete(prompts.format_prompt(prompts.ADAPTIVE_ROUTE, item["question"]),
                            temperature=0.0)
        route = (r.text.strip().lower() or "cot").split()[0]
        routed_by = "llm"
        if route not in ("direct", "cot", "pot"):
            route = "cot"
    fn = {"direct": run_direct, "cot": run_cot, "pot": run_pot}[route]
    out = fn(client, item, cfg)
    out["route"] = route
    out["routed_by"] = routed_by
    return out


def _heuristic_route(item: dict) -> str:
    """规则路由：题面短且无计算词 → direct；含精确计算/符号 → pot；否则 cot。"""
    q = item["question"].lower()
    calc_words = ("calculate", "compute", "how many", "求", "计算", "value of", "evaluate")
    symbol_words = ("derive", "express", "integral", "derivative", "equation in terms")
    if item["answer_type"] == "numeric" and any(w in q for w in calc_words):
        return "pot"
    if any(w in q for w in symbol_words) or item["answer_type"] == "expression":
        return "pot"
    if len(item["question"]) < 120 and not any(w in q for w in calc_words):
        return "direct"
    return "cot"


METHODS = {
    "direct": run_direct,
    "cot": run_cot,
    "pot": run_pot,
    "selfcons": run_selfcons,
    "selfcheck": run_selfcheck,
    "adaptive": run_adaptive,
}


# ---- 工具 ----

def _pack(r, item: dict, answer_type: str) -> dict:
    truncated = r.finish_reason == "length"
    pred = None if truncated else extract_answer(r.text, answer_type)
    return {
        "pred": pred, "raw": r.text, "tokens": r.tokens,
        "latency_s": r.latency_s, "finish_reason": r.finish_reason,
        "truncated": truncated,
    }


def _vote(preds: list[str | None], item: dict) -> str | None:
    """数值答案按容差聚簇取最大簇代表；其他按字符串众数。"""
    valid = [p for p in preds if p is not None]
    if not valid:
        return None
    if item["answer_type"] in ("numeric", "number"):
        clusters: list[tuple[str, int]] = []
        for p in valid:
            placed = False
            for rep, cnt in clusters:
                if grade(p, rep, "numeric", 1e-4):
                    clusters.remove((rep, cnt))
                    clusters.append((rep, cnt + 1))
                    placed = True
                    break
            if not placed:
                clusters.append((p, 1))
        clusters.sort(key=lambda x: -x[1])
        return clusters[0][0]
    return Counter(valid).most_common(1)[0][0]


_CODE_BLOCK_RE = re.compile(r"```python\s*(.*?)```", re.DOTALL)
_POT_EXEC_TIMEOUT_S = 15.0


def _exec_python(text: str, timeout_s: float = _POT_EXEC_TIMEOUT_S) -> str | None:
    """在子进程中执行模型输出的 python 代码块，超时则放弃。

    必须带超时：模型偶发写出死循环/超重数值积分，会把整次评测卡死。
    """
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    m = _CODE_BLOCK_RE.search(text)
    if not m:
        return None
    code = m.group(1)
    if not re.search(r"print\s*\(", code):
        return None

    with tempfile.TemporaryDirectory(prefix="pot_exec_") as tmp:
        script = Path(tmp) / "snippet.py"
        script.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(  # noqa: S603 — 评测场景，代码由模型生成
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None
        except Exception:  # noqa: BLE001
            return None
    if proc.returncode != 0:
        return None
    lines = [line.strip() for line in proc.stdout.strip().splitlines() if line.strip()]
    return lines[-1] if lines else None
