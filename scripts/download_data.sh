#!/usr/bin/env bash
# 下载 SciBench 与 MatSciBench 数据到 data/
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data

# --- SciBench ---
if [ ! -d data/scibench ]; then
  git clone --depth 1 https://github.com/mandyyyyii/scibench.git data/scibench
  echo "[ok] scibench cloned -> data/scibench"
else
  echo "[skip] data/scibench exists"
fi

# --- MatSciBench（官方数据在 HuggingFace；本仓库只有评测代码）---
mkdir -p data/matscibench
if [ ! -f data/matscibench/matscibench.json ]; then
  python - <<'PY'
"""Download text-only, single-answer MatSciBench items for our pipeline."""
from __future__ import annotations

import json
from pathlib import Path

from datasets import load_dataset

out_path = Path("data/matscibench/matscibench.json")
ds = load_dataset("JunkaiZ/MatSciBench", split="test")
rows = []
for row in ds:
    if row.get("image"):
        continue
    if str(row.get("number_of_answers", "single")).lower() == "multiple":
        continue
    rows.append({
        "qid": row.get("qid"),
        "type": row.get("type"),
        "question": row.get("question"),
        "answer": row.get("answer"),
        "unit": row.get("unit") or "",
        "number_of_answers": row.get("number_of_answers"),
        "difficulty_level": row.get("difficulty_level"),
        "primary_category": row.get("primary_category"),
        "solution": row.get("solution"),
        "source": row.get("source"),
    })
    if len(rows) >= 150:
        break
out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"[ok] wrote {out_path} n={len(rows)}")
PY
else
  echo "[skip] data/matscibench/matscibench.json exists"
fi

echo ""
echo "下一步检查："
echo "  python - <<'EOF'"
echo "  from src.data_loaders import load_dataset"
echo "  print('phys', len(load_dataset('scibench', subset='phys', n=5)))"
echo "  print('chem', len(load_dataset('scibench', subset='chem', n=5)))"
echo "  print('matsci', len(load_dataset('matscibench', n=5)))"
echo "  EOF"
