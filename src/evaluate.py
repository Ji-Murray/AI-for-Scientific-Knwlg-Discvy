"""评测主流程 CLI。

用法:
    python -m src.evaluate --dataset scibench --subset phys --methods direct cot --n 100
    python -m src.evaluate --dataset matscibench --methods direct cot selfcons pot adaptive
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os

from .data_loaders import load_dataset
from .grading import grade
from .llm import LLMClient, load_config, record_result
from .methods import METHODS


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=["scibench", "matscibench"])
    ap.add_argument("--subset", default=None, help="scibench: phys/chem/math/qm")
    ap.add_argument("--methods", nargs="+", required=True,
                    default=["direct", "cot"], choices=list(METHODS))
    ap.add_argument("--n", type=int, default=100, help="每方法评多少题（最低要求 100）")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--tol", type=float, default=1e-4)
    ap.add_argument("--offset", type=int, default=0, help="跳过前 offset 题（扩展实验用）")
    ap.add_argument("--out", default=None,
                    help="指定结果 JSONL 路径（用于断点续跑追加；默认新建带时间戳文件）")
    args = ap.parse_args()

    cfg = load_config(args.config)
    client = LLMClient(cfg, config_path=args.config)

    if args.n < 1:
        raise ValueError("--n must be at least 1")
    items = load_dataset(args.dataset, args.data_dir, args.subset,
                         n=args.offset + args.n)[args.offset: args.offset + args.n]
    if not items:
        raise ValueError("No evaluation items found; check --data-dir and --subset")
    if len(items) < args.n:
        print(f"[eval] warning: requested {args.n} items but found {len(items)}")
    print(f"[eval] dataset={args.dataset} subset={args.subset} "
          f"items={len(items)} methods={args.methods} model={client.model}")

    if args.out:
        out_path = args.out
    else:
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        tag = f"{args.dataset}-{args.subset or 'all'}"
        out_path = os.path.join(args.results_dir, f"{tag}-{stamp}.jsonl")

    for method in args.methods:
        m_cfg = dict(cfg.get("methods", {}).get(method, {}))
        n_ok = n_extract_fail = 0
        for it in items:
            out = METHODS[method](client, it, m_cfg)
            correct = grade(out.get("pred"), it["gold"], it["answer_type"], args.tol)
            extract_fail = out.get("pred") is None
            rec = {
                "qid": it["id"], "dataset": args.dataset, "subject": it["subject"],
                "method": method, "seed": cfg.get("seed", 42),
                "model": client.model, "protocol": "final-answer-v2",
                "question": it["question"], "gold": it["gold"],
                "answer_type": it["answer_type"], "numeric_tol": args.tol,
                "source": it.get("source", ""),
                "raw_output": out.get("raw", ""), "pred": out.get("pred"),
                "correct": correct, "extract_fail": extract_fail,
                "finish_reason": out.get("finish_reason"),
                "truncated": out.get("truncated", False),
                "tokens": out.get("tokens", 0), "latency_s": out.get("latency_s", 0.0),
            }
            rec.update({k: v for k, v in out.items()
                        if k not in rec and k != "raw"})
            record_result(out_path, rec)
            n_ok += int(correct)
            n_extract_fail += int(extract_fail)
        print(f"[eval] {method:10s} acc={n_ok / len(items):.1%} "
              f"({n_ok}/{len(items)})  extract_fail={n_extract_fail}  -> {out_path}")

    print(f"[eval] done. results: {out_path}")


if __name__ == "__main__":
    main()
