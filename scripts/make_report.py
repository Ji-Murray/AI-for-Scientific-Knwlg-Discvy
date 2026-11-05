#!/usr/bin/env python
"""把 results/*.jsonl 汇总成报告（结果表 + 图），等价于 src.analysis 的脚本入口。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analysis import main  # noqa: E402

if __name__ == "__main__":
    main()
