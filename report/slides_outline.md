# Topic 4 Slides 内容稿（约 10 分钟）

> 用法：按页复制到 PPT / Keynote / Google Slides。  
> 配图直接用 `report/acc_by_method.png`、`report/acc_vs_tokens.png`。  
> 括号内为建议口播时长。

---

## Slide 1 — 标题（20s）

**Inference-Time Reasoning for Scientific Problem Solving**  
Topic 4 · DSC6020 · AI for Scientific Knowledge Discovery

副标题：不训练大模型，只比较推理时策略

口播：我们研究的是——同一底座模型下，换不同推理策略，科学题准确率能提升多少。

---

## Slide 2 — 动机（45s）

**问题**
- 大学水平科学题（物理 / 化学 / 材料）对 LLM 仍然很难
- 微调成本高；课程约束：**只做 inference-time 方法**

**研究问题**
> 在固定模型下，Direct / CoT / Self-Consistency / PoT / Adaptive  
> 谁更准？谁更划算（token）？错在哪里？

口播：重点不是换更大模型，而是问「怎么问模型」和「怎么验算」。

---

## Slide 3 — 实验设置（60s）

| 项 | 选择 |
|---|---|
| 模型 | **qwen-plus**（全程同一底座） |
| 基准 | SciBench phys / chem；MatSciBench（文本单答案） |
| 规模 | **每方法 × 每子集 100 题** |
| 判分 | 数值相对误差 < 1e-4；符号 sympy |
| 可复现 | seed=42，结果 JSONL 落盘 |

口播：满足课程硬性要求——双基准、≥100 题、同模型、至少 Direct vs CoT。

---

## Slide 4 — 方法（70s）

五种推理时策略（由便宜到贵）：

1. **Direct** — 直接给最终答案  
2. **CoT** — 最多 5 步简短推理再作答  
3. **Self-Consistency** — CoT 采样 k=5，答案投票  
4. **Program-of-Thought (PoT)** — 写 Python，本地执行（15s 超时）  
5. **Adaptive** — 启发式路由：短概念→Direct；精确计算/符号→PoT；其余→CoT

口播：Adaptive 的卖点是「该深则深、该浅则浅」，看能否在准确率与成本之间折中。

---

## Slide 5 — 主结果表（70s）

**Accuracy（qwen-plus, n=100）**

| method | chem | matsci | phys |
|---|---|---|---|
| Direct | 30% | 6% | 13% |
| CoT | **40%** | **26%** | 23% |
| SelfCons | — | — | 22% |
| PoT | — | — | **29%** |
| Adaptive | — | — | 24% |

口播要点：
- 三个子集上 **CoT 都显著高于 Direct**
- phys 上 Bonus 里 **PoT 最好（29%）**
- Self-Consistency **没有超过 CoT**

配图：可放简化表，详细图放下一页。

---

## Slide 6 — 准确率柱状图（50s）

**插图：** `report/acc_by_method.png`

口播：
- chem 相对最容易（CoT 40%）
- matsci Direct 几乎崩（6%），说明材料题很吃推理
- phys 上方法分化最清楚：PoT > Adaptive ≈ CoT > SC > Direct

---

## Slide 7 — 成本 vs 准确率（70s）

**插图：** `report/acc_vs_tokens.png`

phys 上大致位置（avg tokens）：

| method | acc | avg tokens |
|---|---|---|
| Direct | 13% | ~189 |
| CoT | 23% | ~1129 |
| Adaptive | 24% | ~1414 |
| PoT | 29% | ~3194 |
| SelfCons | 22% | ~5843 |

口播：
- **SelfCons 最贵却不更准** → 对这模型「多采样」不划算
- **PoT 更准但更贵**
- **Adaptive ≈ CoT 准确率，token 远低于 PoT/SC**（多数题路由到 CoT：78/100）

---

## Slide 8 — 错误分析（80s）

人工复核 **40** 条错误样本：

| 错因 | 占比 |
|---|---|
| 计算 / 单位 (`b_calculation`) | **70%** |
| 知识 / 公式 (`a_knowledge`) | 25% |
| 理解题意 | 2.5% |
| 格式抽取失败 | 2.5% |

**典型案例（挑 2 个讲）：**
1. **单位：** chem 金标 `+3.60 kJ`，模型输出 `3595 J`（算对了，单位没换）  
2. **近失分：** 金标 `25`，预测 `24.9`（推理基本对，1e-4 容差判错）

口播：主瓶颈不是「答不出来」，而是 **单位与数值精度**；知识错误仍占约 1/4。

---

## Slide 9 — 结论（50s）

1. Inference-time 策略有效：**CoT > Direct**（全基准一致）  
2. phys 上 **PoT 是最强单策略**；**SC 性价比差**  
3. **Adaptive** 提供准确率≈CoT、成本低于 PoT/SC 的折中  
4. 错误以 **计算/单位** 为主 → 提示词约束单位 + 工具执行（PoT）是合理方向

---

## Slide 10 — 局限与下一步（40s）

**局限**
- Bonus 方法主要在 phys；chem/matsci 未全跑 PoT/Adaptive  
- 自适应目前是规则路由，不是学习路由  
- 数值容差严格，部分「几乎对」被算错

**下一步**
- 把 PoT/Adaptive 扩到 chem  
- 提示词强制单位与金标一致  
- （可选）学习型路由器 / Solver–Verifier

口播收尾：谢谢，欢迎提问。

---

## 计时总览（约 9.5–10.5 min）

| 页 | 秒 |
|---|---|
| 1 标题 | 20 |
| 2 动机 | 45 |
| 3 设置 | 60 |
| 4 方法 | 70 |
| 5 主表 | 70 |
| 6 柱状图 | 50 |
| 7 成本图 | 70 |
| 8 错误 | 80 |
| 9 结论 | 50 |
| 10 局限 | 40 |
| **合计** | **~555s ≈ 9.3 min**（留 1 min 缓冲/提问） |

## 提问预案（2 min 讨论）

- Q: 为什么 SC 没涨点？  
  A: 单次 CoT 错误常是系统性的（单位/公式），投票无法纠正；且 k=5 方差不够大。
- Q: 为什么 PoT 更好？  
  A: 把算术交给解释器，减少中间算错；但仍会单位错、建模错。
- Q: Adaptive 为何多走 CoT？  
  A: 启发式偏保守；phys 题多数被判「需要多步但未必要代码」。
