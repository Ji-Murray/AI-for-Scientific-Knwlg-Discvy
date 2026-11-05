# LLM 科学推理评测 — Topic 4 (DSC6020)

研究推理时策略（Direct / CoT / Self-Consistency / Program-of-Thought / 自适应路由）对 LLM 科学题解题的影响。不训练大模型，纯评测 + 分析。

## 目录结构

```
.
├── AGENTS.md            # 给 Cursor 的项目规则（先读这个）
├── PLAN.md              # 项目计划 / 任务清单 / 分工
├── config.example.yaml  # 实验配置模板（复制为 config.yaml 并填 API key）
├── requirements.txt
├── data/                # 基准数据（download_data.sh 下载）
├── results/             # 每次实验的 JSONL 输出
├── scripts/
│   ├── download_data.sh # 下载 SciBench + MatSciBench
│   └── make_report.py   # 汇总 results/ 生成结果表与图
└── src/
    ├── llm.py           # 统一 LLM 调用封装（唯一入口）
    ├── prompts.py       # 各方法的提示词模板
    ├── data_loaders.py  # SciBench / MatSciBench 统一加载器
    ├── grading.py       # 答案抽取 + 判分
    ├── methods.py       # Direct / CoT / SelfConsistency / PoT / Adaptive
    └── evaluate.py      # 评测主流程 CLI
```

## 快速开始

```bash
pip install -r requirements.txt
bash scripts/download_data.sh
cp config.example.yaml config.yaml   # 填入 OPENAI_API_KEY / base_url / model

# 最低要求实验：Direct vs CoT，各评 100 题
python -m src.evaluate --dataset scibench --subset phys --methods direct cot --n 100

# Bonus 方法
python -m src.evaluate --dataset scibench --subset phys --methods selfcons pot adaptive --n 100

# 汇总结果表 + 图
python scripts/make_report.py --results results/ --out report/
```

## 结果记录格式（results/*.jsonl，每行一条）

```json
{"qid": "phys-0007", "dataset": "scibench", "subject": "phys",
 "method": "cot", "seed": 42, "question": "...", "gold": "12.5",
 "raw_output": "...", "pred": "12.48", "correct": true,
 "extract_fail": false, "latency_s": 3.2, "tokens": 741}
```
# AI-for-Scientific-Knwlg-Discvy
# AI-for-Scientific-Knwlg-Discvy
# AI-for-Scientific-Knwlg-Discvy
