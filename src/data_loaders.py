"""数据加载器：把各基准统一成中间格式。

统一条目格式:
    {
      "id": str,            # 唯一 ID，如 "phys-0007"
      "question": str,      # 题面
      "gold": str,          # 标准答案（数值/表达式/选项）
      "answer_type": str,   # numeric | expression | choice | open
      "subject": str,       # phys / chem / math / matsci ...
      "meta": dict,         # 原始字段备份
    }

SciBench 仓库结构（mandyyyyii/scibench）:
    data/{subfolder}/size-{N}.json  （如 phys/size-300.json）
    每条: {"problem": ..., "answer": ..., ...} — 下载后先跑一次
    inspect 脚本核对字段名，必要时在此调整。

MatSciBench（Jun-Kai-Zhang/MatSciBench）:
    JSON/JSONL，字段含 question / answer / type；同样先 inspect。
"""

from __future__ import annotations

import json
import os
from typing import Any, Iterator


def _iter_json(path: str) -> Iterator[dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_scibench(data_dir: str, subset: str = "phys", n: int | None = None) -> list[dict]:
    """加载 SciBench，兼容官方仓库的 ``dataset/original`` 布局。

    官方仓库按教材章节命名文件，而不是按 ``phys``/``chem`` 建目录，
    因此这里把课程中的主题名映射到对应章节，并合并后再截取样本。
    """
    repo = os.path.join(data_dir, "scibench")
    subset_aliases = {
        "phys": ("class", "diff", "fund", "matter"),
        "chem": ("atkins", "chemmc", "thermo"),
        "math": ("calculus", "stat"),
        "qm": ("quan",),
    }
    candidates: list[str] = []
    for base in (os.path.join(repo, "data", subset), os.path.join(repo, subset)):
        if os.path.isdir(base):
            candidates.extend(
                os.path.join(base, name)
                for name in sorted(os.listdir(base))
                if name.endswith(".json")
            )
    original = os.path.join(repo, "dataset", "original")
    names = subset_aliases.get(subset, (subset,))
    if os.path.isdir(original):
        candidates.extend(os.path.join(original, f"{name}.json") for name in names)
    candidates = [path for path in candidates if os.path.isfile(path)]
    if not candidates:
        raise FileNotFoundError(
            f"SciBench data for subset {subset!r} not found under {repo}; "
            "run scripts/download_data.sh"
        )

    out: list[dict] = []
    for path in candidates:
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)
        if isinstance(items, dict):
            items = items.get("questions", next(iter(items.values()), []))
        for item in items:
            answer = item.get("answer_number") or item.get("answer") or item.get("answer_latex", "")
            question = item.get("problem_text") or item.get("problem") or item.get("question", "")
            out.append({
                "id": f"{subset}-{len(out):04d}",
                "source": os.path.basename(path),
                "question": str(question).strip(),
                "gold": str(answer).strip(),
                "answer_type": "numeric" if item.get("answer_number") else (
                    "expression" if _looks_symbolic(answer) else "numeric"
                ),
                "subject": subset,
                "meta": item,
            })
            if n is not None and len(out) >= n:
                return out
    return out


def load_matscibench(data_dir: str, n: int | None = None) -> list[dict]:
    """加载 MatSciBench 数据（本地 json/jsonl；字段对齐 HuggingFace JunkaiZ/MatSciBench）。"""
    directory = os.path.join(data_dir, "matscibench")
    path = os.path.join(directory, "matscibench.json")
    if not os.path.exists(path):
        files = sorted(
            name for name in os.listdir(directory) if name.endswith((".json", ".jsonl"))
        ) if os.path.isdir(directory) else []
        if files:
            path = os.path.join(directory, files[0])
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"MatSciBench data not found under {directory}; run scripts/download_data.sh"
        )

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    try:
        rows = list(_iter_json(path)) if path.endswith(".jsonl") else json.loads(content)
    except json.JSONDecodeError:
        rows = list(_iter_json(path))
    if isinstance(rows, dict):
        rows = rows.get("data", rows.get("questions", []))

    out = []
    for i, it in enumerate(rows):
        # 默认跳过多模态与多答案题，保证与文本判分流水线兼容
        if it.get("image"):
            continue
        if str(it.get("number_of_answers", "single")).lower() == "multiple":
            continue
        gold = it.get("answer", it.get("final_answer", ""))
        qid = it.get("qid") or f"{i:04d}"
        out.append({
            "id": f"matsci-{qid}" if not str(qid).startswith("matsci-") else str(qid),
            "question": it.get("question") or it.get("problem", ""),
            "gold": str(gold).strip(),
            "answer_type": _classify_matsci(it),
            "subject": "matsci",
            "source": str(it.get("source", "")),
            "meta": it,
        })
        if n is not None and len(out) >= n:
            break
    return out


def _looks_symbolic(ans: Any) -> bool:
    """启发式：含字母变量（非纯数字/单位）视为符号表达式。"""
    s = str(ans)
    return bool(s) and not _is_number(s) and any(c.isalpha() for c in s)


def _is_number(s: str) -> bool:
    try:
        float(s.replace(",", "").strip())
        return True
    except ValueError:
        return False


def _classify_matsci(item: dict) -> str:
    t = str(item.get("type", "")).lower()
    if t in ("num", "numeric", "number") or "numer" in t or "calc" in t:
        return "numeric"
    if t in ("formula", "expression", "symbolic") or "symbol" in t or "formula" in t:
        return "expression"
    if "choice" in t or "concept" in t:
        return "choice"
    return "numeric" if _is_number(str(item.get("answer", ""))) else "expression"


def load_dataset(name: str, data_dir: str = "data", subset: str | None = None,
                 n: int | None = None) -> list[dict]:
    """统一入口。"""
    if name == "scibench":
        return load_scibench(data_dir, subset or "phys", n)
    if name == "matscibench":
        return load_matscibench(data_dir, n)
    raise ValueError(f"Unknown dataset: {name}")
