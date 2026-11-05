# 项目规则（供 Cursor 遵循）

## 项目背景

这是 DSC6020 (AI for Scientific Knowledge Discovery) 的课程项目 **Topic 4: Scientific Reasoning with Large Language Models**。

目标：研究**推理时（inference-time）策略**如何提升 LLM 解决科学问题的能力，**不训练/微调大模型**。

## 硬性要求（必须满足，不可删减）

1. 在 SciBench 和 MatSciBench 中**至少选一个基准**（我们两个都做，主报 SciBench 的物理/化学，MatSciBench 做补充）。
2. **每个基准评测至少 100 道题**。
3. 所有实验使用**同一个基座 LLM**（默认 `gpt-4o-mini`，可通过 config 更换，但换模型必须重跑全部方法，不允许混用）。
4. 至少对比两种方法：**Direct Answer**（直接作答） vs **Chain-of-Thought**（思维链）。
5. 报告**整体准确率**，并进行**基础错误分析**（按题型/知识点/错误类型分类统计）。

## Bonus 目标（按优先级实现，时间不够时保 3、4）

1. 增加更强的推理方法：Self-Consistency（多采样投票）、Program-of-Thought（写代码求解）、Solver-Verifier（求解器+校验）。
2. 构建**自适应推理策略**：根据题目特征（如是否需要多步计算）选择不同推理深度的方法。
3. （可选）用 LoRA/QLoRA 微调一个小的开源模型（如 Qwen2.5-7B）做对比。

## 代码规范

- Python 3.10+，只用 `requirements.txt` 里声明的依赖。
- LLM 调用**必须**走 `src/llm.py` 的统一封装，禁止在别处直接 import openai —— 保证可切换模型、统一日志与重试。
- 所有实验结果以 JSONL 追加写入 `results/`，每条记录包含：题目 ID、方法名、原始输出、抽取的答案、是否正确、耗时、token 用量。
- 答案判定：数值题用数值容差比较（相对误差 < 1e-4 视为正确），符号/表达式题用 sympy 化简后比较；判定逻辑集中在 `src/grading.py`。
- 每次实验必须固定 `seed` 并记录在结果中，保证可复现。
- 代码要有类型注解，关键函数有 docstring。
- 不要引入重量级框架（langchain 之类），保持依赖精简。

## 数据说明

- SciBench: https://github.com/mandyyyyii/scibench —— 大学水平的数学/物理/化学题，含数值与符号答案，数据文件在仓库 `data/` 下。
- MatSciBench: https://github.com/Jun-Kai-Zhang/MatSciBench —— 大学水平材料科学题，覆盖概念、数值、符号与多模态推理。
- 下载脚本在 `scripts/download_data.sh`；数据统一放 `data/` 目录。
