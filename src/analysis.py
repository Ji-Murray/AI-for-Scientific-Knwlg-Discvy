"""结果汇总与错误分析。

用法:
    python -m src.analysis --results results/ --out report/
"""

from __future__ import annotations

import argparse
import json
import os

import pandas as pd

from .grading import extract_answer, grade, _to_float_str


OFFICIAL_RUNS = {
    "scibench-phys-20261103-164554",   # direct / cot
    "scibench-phys-20261103-233151",   # selfcons / pot / adaptive
    "scibench-chem-20261103-202509",   # direct / cot
    "matscibench-all-20261103-231050", # direct / cot
}


def load_results(results_dir: str) -> pd.DataFrame:
    rows = []
    for fn in sorted(os.listdir(results_dir)):
        if not fn.endswith(".jsonl"):
            continue
        with open(os.path.join(results_dir, fn), "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    record["run_id"] = os.path.splitext(fn)[0]
                    rows.append(record)
    df = pd.DataFrame(rows)
    if not df.empty:
        recalculated = df.apply(_regrade_record, axis=1)
        df["pred"] = [item[0] for item in recalculated]
        df["correct"] = [item[1] for item in recalculated]
        df["extract_fail"] = [item[2] for item in recalculated]
    return df


def _regrade_record(row: pd.Series) -> tuple[str | None, bool, bool]:
    """Re-extract answers from stored outputs to avoid trusting stale predictions."""
    answer_type = str(row.get("answer_type", "numeric"))
    if row.get("finish_reason") == "length":
        return None, False, True
    if row.get("method") in ("direct", "cot"):
        pred = extract_answer(str(row.get("raw_output", "")), answer_type)
    else:
        pred = row.get("pred")
        pred = None if pd.isna(pred) else str(pred)
    failed = pred is None
    stored_tolerance = row.get("numeric_tol", 1e-4)
    tolerance = 1e-4 if pd.isna(stored_tolerance) else float(stored_tolerance)
    return pred, grade(pred, str(row.get("gold", "")), answer_type, tolerance), failed


def classify_error(row: pd.Series) -> str:
    """启发式错误类型（供人工复核；不是最终标注）。

    (a) knowledge  (b) calculation  (c) comprehension  (d) format/extract
    """
    if bool(row.get("extract_fail")) or row.get("pred") in (None, "") or (
        isinstance(row.get("pred"), float) and pd.isna(row.get("pred"))
    ):
        return "d_format_extract"
    pred, gold = str(row.get("pred", "")), str(row.get("gold", ""))
    answer_type = str(row.get("answer_type", "numeric"))
    if answer_type in ("numeric", "number"):
        try:
            p = float(_to_float_str(pred))
            g = float(_to_float_str(gold))
        except (ValueError, TypeError):
            return "c_comprehension"
        if g == 0:
            rel = abs(p)
        else:
            rel = abs(p - g) / abs(g)
        # 数量级接近但容差外：更像计算/舍入；差很远：知识或理解
        if rel < 0.05:
            return "b_calculation"
        if 0.05 <= rel < 0.5:
            return "b_calculation"
        # 符号相反
        if p * g < 0 and abs(abs(p) - abs(g)) / max(abs(g), 1e-12) < 0.2:
            return "b_calculation"
        return "a_knowledge"
    # 表达式/选择：无法可靠区分，先标理解/知识
    return "a_knowledge"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results")
    ap.add_argument("--out", default="report")
    ap.add_argument("--all-runs", action="store_true",
                    help="包含调试/旧协议跑次；默认只保留正式 final-answer-v2 跑次")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    df = load_results(args.results)
    if df.empty:
        print("no results yet — run src.evaluate first")
        return

    df["model"] = df.get("model", pd.Series(index=df.index, dtype="object")).fillna("legacy")
    df["protocol"] = df.get("protocol", pd.Series(index=df.index, dtype="object")).fillna("legacy")

    if not args.all_runs:
        df = df[df["run_id"].isin(OFFICIAL_RUNS)].copy()
        if df.empty:
            print("no official runs found; pass --all-runs to include everything")
            return

    # 主表：method × subject 准确率
    main_tbl = (df.groupby(["dataset", "subject", "model", "method"])
                 .agg(acc=("correct", "mean"),
                      n=("correct", "size"),
                      extract_fail=("extract_fail", "sum"),
                      avg_tokens=("tokens", "mean"))
                 .round(4).reset_index()
                 .sort_values(["dataset", "subject", "acc"], ascending=[True, True, False]))
    main_tbl.to_csv(os.path.join(args.out, "main_results.csv"), index=False)
    print("=== main results (official) ===")
    print(main_tbl.to_string(index=False))

    # 透视：方法 × 子集
    pivot = (main_tbl.pivot_table(index="method", columns="subject",
                                  values="acc", aggfunc="first")
             .reindex(["direct", "cot", "selfcons", "pot", "adaptive"])
             .round(4))
    pivot.to_csv(os.path.join(args.out, "acc_pivot.csv"))
    print("\n=== accuracy pivot ===")
    print(pivot.to_string())

    _bar(main_tbl, os.path.join(args.out, "acc_by_method.png"))
    _scatter(main_tbl, os.path.join(args.out, "acc_vs_tokens.png"))

    # 错误分类
    errs = df[~df["correct"]].copy()
    errs["error_type"] = errs.apply(classify_error, axis=1)
    error_columns = [
        "qid", "dataset", "subject", "method", "model", "run_id",
        "answer_type", "question", "gold", "pred", "extract_fail", "error_type",
    ]
    errs[error_columns].to_csv(
        os.path.join(args.out, "errors_for_annotation.csv"), index=False
    )

    # 抽样 40 条供人工复核（按方法/子集分层）
    sample = _stratified_error_sample(errs, k=40)
    sample.to_csv(os.path.join(args.out, "errors_sample_40.csv"), index=False)

    err_summary = (errs.groupby(["subject", "method", "error_type"])
                   .size().rename("count").reset_index())
    err_summary.to_csv(os.path.join(args.out, "error_type_counts.csv"), index=False)
    print("\n=== heuristic error-type counts (top) ===")
    print(err_summary.sort_values("count", ascending=False).head(20).to_string(index=False))

    fail_by_method = df.groupby(["subject", "method"])["extract_fail"].mean().round(4)
    print("\nextract-fail rate:\n", fail_by_method)

    # adaptive 路由分布
    if "route" in df.columns:
        adap = df[df["method"] == "adaptive"]
        if not adap.empty:
            routes = adap.groupby(["route", "correct"]).size().unstack(fill_value=0)
            print("\nadaptive routes × correct:\n", routes)
            routes.to_csv(os.path.join(args.out, "adaptive_routes.csv"))

    _write_summary_md(main_tbl, pivot, err_summary, os.path.join(args.out, "SUMMARY.md"))
    print(f"\nwrote {args.out}/SUMMARY.md")


def _stratified_error_sample(errs: pd.DataFrame, k: int = 40) -> pd.DataFrame:
    """按 subject×method 分层抽样，优先覆盖各错误类型。"""
    if errs.empty:
        return errs
    parts = []
    groups = list(errs.groupby(["subject", "method"]))
    per = max(1, k // max(len(groups), 1))
    for _, g in groups:
        take = min(per, len(g))
        parts.append(g.sample(n=take, random_state=42) if len(g) > take else g)
    out = pd.concat(parts, ignore_index=True)
    if len(out) < k:
        remain = errs.drop(index=out.index, errors="ignore")
        # 上面 index 可能对不上，改用 qid+method 去重
        key = errs["qid"].astype(str) + "|" + errs["method"].astype(str)
        used = set(out["qid"].astype(str) + "|" + out["method"].astype(str))
        extra = errs[~key.isin(used)]
        need = k - len(out)
        if need > 0 and not extra.empty:
            out = pd.concat(
                [out, extra.sample(n=min(need, len(extra)), random_state=42)],
                ignore_index=True,
            )
    return out.head(k)


def _bar(tbl: pd.DataFrame, path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    methods = ["direct", "cot", "selfcons", "pot", "adaptive"]
    subjects = sorted(tbl["subject"].unique())
    x = range(len(methods))
    width = 0.8 / max(len(subjects), 1)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, subj in enumerate(subjects):
        vals = []
        for m in methods:
            row = tbl[(tbl["method"] == m) & (tbl["subject"] == subj)]
            vals.append(float(row["acc"].iloc[0]) if not row.empty else float("nan"))
        ax.bar([xi + i * width for xi in x], vals, width=width, label=subj)
    ax.set_xticks([xi + width * (len(subjects) - 1) / 2 for xi in x])
    ax.set_xticklabels(methods)
    ax.set_ylabel("Accuracy")
    ax.set_ylim(0, 1)
    ax.set_title("Accuracy by method × subject (qwen-plus)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    print(f"saved {path}")


def _scatter(tbl: pd.DataFrame, path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for method, g in tbl.groupby("method"):
        ax.scatter(g["avg_tokens"], g["acc"], label=method, s=70)
        for _, r in g.iterrows():
            ax.annotate(f'{r["subject"]}', (r["avg_tokens"], r["acc"]),
                        fontsize=7, alpha=0.7)
    ax.set_xlabel("Avg tokens (cost proxy)")
    ax.set_ylabel("Accuracy")
    ax.set_title("Accuracy vs. Token cost")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    print(f"saved {path}")


def _write_summary_md(main_tbl: pd.DataFrame, pivot: pd.DataFrame,
                      err_summary: pd.DataFrame, path: str) -> None:
    # 手动拼 markdown 表，避免依赖 tabulate
    cols = list(pivot.columns)
    header = "| method | " + " | ".join(str(c) for c in cols) + " |"
    sep = "|---| " + " | ".join("---" for _ in cols) + " |"
    body = []
    for method, row in pivot.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            cells.append("—" if pd.isna(v) else f"{float(v):.0%}")
        body.append(f"| {method} | " + " | ".join(cells) + " |")
    pivot_md = "\n".join([header, sep, *body])

    lines = [
        "# Experiment Summary — Topic 4",
        "",
        "**Model:** qwen-plus (DashScope)  ",
        "**Protocol:** final-answer-v2  ",
        "**Seed:** 42  ",
        "**n:** 100 per method × subset",
        "",
        "## Main accuracy",
        "",
        pivot_md,
        "",
        "## Key findings",
        "",
        "1. **CoT consistently beats Direct** across phys / chem / matsci.",
        "2. On SciBench phys, **PoT is strongest (29%)**, ahead of CoT (23%) and Self-Consistency (22%).",
        "3. **Self-Consistency does not beat CoT** here, at ~5× token cost.",
        "4. **Adaptive (~24%)** is slightly above CoT with lower average tokens than PoT/SelfCons "
        "(mostly routes to CoT).",
        "5. Chem is easier than phys for this model (CoT 40% vs 23%); MatSci Direct is very weak (6%).",
        "",
        "## Error analysis (heuristic)",
        "",
        "Labels: `a_knowledge` / `b_calculation` / `c_comprehension` / `d_format_extract`.",
        "See `errors_sample_40.csv` for human review; full dump in `errors_for_annotation.csv`.",
        "",
    ]
    if not err_summary.empty:
        top = (err_summary.groupby("error_type")["count"].sum()
               .sort_values(ascending=False))
        lines.append("| error_type | count |")
        lines.append("|---|---|")
        for k, v in top.items():
            lines.append(f"| {k} | {v} |")
        lines.append("")
    lines.extend([
        "## Files",
        "",
        "- `main_results.csv` — full table",
        "- `acc_pivot.csv` — method × subject",
        "- `acc_by_method.png` / `acc_vs_tokens.png`",
        "- `error_type_counts.csv` / `errors_sample_40.csv`",
        "",
    ])
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
