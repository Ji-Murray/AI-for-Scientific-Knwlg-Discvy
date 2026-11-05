# Experiment Summary — Topic 4

**Model:** qwen-plus (DashScope)  
**Protocol:** final-answer-v2  
**Seed:** 42  
**n:** 100 per method × subset

## Main accuracy

| method | chem | matsci | phys |
|---| --- | --- | --- |
| direct | 30% | 6% | 13% |
| cot | 40% | 26% | 23% |
| selfcons | — | — | 22% |
| pot | — | — | 29% |
| adaptive | — | — | 24% |

## Key findings

1. **CoT consistently beats Direct** across phys / chem / matsci.
2. On SciBench phys, **PoT is strongest (29%)**, ahead of CoT (23%) and Self-Consistency (22%).
3. **Self-Consistency does not beat CoT** here, at ~5× token cost.
4. **Adaptive (~24%)** is slightly above CoT with lower average tokens than PoT/SelfCons (mostly routes to CoT).
5. Chem is easier than phys for this model (CoT 40% vs 23%); MatSci Direct is very weak (6%).

## Error analysis (heuristic)

Labels: `a_knowledge` / `b_calculation` / `c_comprehension` / `d_format_extract`.
See `errors_sample_40.csv` for human review; full dump in `errors_for_annotation.csv`.

| error_type | count |
|---|---|
| a_knowledge | 359 |
| b_calculation | 310 |
| d_format_extract | 16 |
| c_comprehension | 2 |

## Files

- `main_results.csv` — full table
- `acc_pivot.csv` — method × subject
- `acc_by_method.png` / `acc_vs_tokens.png`
- `error_type_counts.csv` / `errors_sample_40.csv`
