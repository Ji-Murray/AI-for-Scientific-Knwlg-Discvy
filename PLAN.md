# Topic 4 项目计划 — Scientific Reasoning with LLMs

> 课程：DSC6020 AI for Scientific Knowledge Discovery
> 展示：11 月 19 日（10 分钟讲 + 2 分钟讨论），今天 11 月 2 日，剩 ~2.5 周。

## 时间线

| 阶段 | 时间 | 产出 |
|---|---|---|
| W1 环境 + 数据 + 基线 | 11/2 – 11/8 | 数据下载完成；Direct & CoT 在 ≥100 题上跑通；初步准确率表 |
| W2 扩展方法 + 分析 | 11/9 – 11/15 | Self-Consistency / PoT（/自适应策略）；错误分析；完整结果表 |
| W2.5 Slides + 排练 | 11/16 – 11/19 | 10 页以内 slides；组内排练一次 |

## 任务清单

### P0 — 最低要求（必做）
- [ ] 下载数据：SciBench（physics/chemistry）+ MatSciBench
- [ ] `src/llm.py` 统一 LLM 封装（OpenAI 兼容接口，支持 base_url 覆盖，便于用其他供应商）
- [ ] 数据加载器：把两个基准统一成 `{"id", "question", "answer", "type", "subject"}` 格式
- [ ] 答案抽取与判分 `src/grading.py`（数值容差 + sympy 符号比较）
- [ ] 方法 1：Direct Answer 提示词 + 评测
- [ ] 方法 2：Chain-of-Thought 提示词 + 评测
- [ ] 每题 ≥100，两个基准都评；记录 accuracy
- [ ] 错误分析：错误按 (a) 知识错误 (b) 计算错误 (c) 理解题意错误 (d) 格式/抽取失败 分类，人工标注 30–50 条错误样本

### P1 — Bonus（按优先级）
- [ ] Self-Consistency（同一 CoT 提示采样 k=5/10 次，多数投票）
- [ ] Program-of-Thought（让模型写 Python 代码并执行得到答案）
- [ ] 自适应策略：一个轻量分类器/规则，根据题目特征（长度、是否含"计算/求值"、是否多问）在 Direct / CoT / PoT 之间路由，目标是"更高准确率 + 更低平均 token 开销"的双赢图
- [ ] （可选）Solver–Verifier：生成答案后让模型自检一遍
- [ ] （可选，时间充裕）QLoRA 微调 Qwen2.5-7B-Instruct 与 API 模型对比

### P2 — 报告与展示
- [ ] 主结果表：行=方法，列=基准，格=accuracy（± 若多 seed）
- [ ] 图 1：各方法准确率对比柱状图；图 2：token 成本 vs 准确率散点（自适应策略的卖点）
- [ ] 错误分析表 + 典型失败案例 2–3 个（这是评分点，"why good / why poor"）
- [ ] 10 分钟 slides：动机(1) 设置(2) 方法(2) 结果(3) 分析(2)

## 风险与对策

- **API 花费/限速**：先用 gpt-4o-mini 跑通全流程；正式实验一次锁定 config；结果全部落盘 JSONL，避免重复调用。
- **答案抽取失败**：提示词里强制输出格式 `\boxed{...}` 或 JSON；grading 单独统计"抽取失败率"，它与"模型答错"分开报告。
- **两个基准格式差异大**：统一中间格式，grading 按 answer type 分派（numeric / expression / multiple-choice / open-ended）。

## 组内分工建议（4 人组）

- A：LLM 封装 + 评测流水线（`llm.py`, `evaluate.py`）
- B：数据 + 判分（`data_*.py`, `grading.py`）
- C：Bonus 方法（self-consistency, PoT, 自适应路由）
- D：错误分析 + 可视化 + slides（`analysis.py`）
