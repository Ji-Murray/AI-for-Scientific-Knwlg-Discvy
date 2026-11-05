"""各推理方法的提示词模板。

约定：所有方法都强制模型把最终答案放进 `\boxed{...}`，
便于 grading.py 统一抽取。open-ended 题改用 JSON 输出。
"""

from __future__ import annotations

SYSTEM = (
    "You are an expert solving college-level science problems. "
    "Follow the requested response format exactly. Never stop before giving a final answer."
)

DIRECT = """Solve the following problem. Do not show your work. Return exactly one short line in this format:
FINAL ANSWER: <number or expression>
Do not include derivation, alternatives, or commentary. Include units only when the question requests them.

Problem:
{question}"""

COT = """Solve the problem using concise reasoning in at most 5 short steps. Avoid repeating calculations or reconsidering settled steps. Finish with exactly one separate line in this format:
FINAL ANSWER: <number or expression>
The final line must contain only the answer after the colon. Do not include units unless requested, and do not stop before the final line.

Problem:
{question}"""

# Program-of-Thought：让模型写 Python 代码，由我们执行取结果
POT = """Solve the following problem by writing a short Python script (use sympy for exact math if helpful).
Print the final answer with `print(ANSWER)`. Do not ask for input.
First write the code in a ```python block, then on the last line write the final answer inside \\boxed{{...}}.

Problem:
{question}"""

SELF_CHECK = """You previously solved this problem:

Problem:
{question}

Your answer was: {answer}

Carefully verify whether the answer is correct. If it is wrong, give the corrected final answer inside \\boxed{{...}}; if correct, repeat the same answer inside \\boxed{{...}}."""

ADAPTIVE_ROUTE = """You are a router. Given a science problem, decide the cheapest solving strategy:
- "direct": short/conceptual question, answerable in one line
- "cot": requires multi-step reasoning but simple arithmetic
- "pot": requires precise/complex numerical calculation or symbolic manipulation

Reply with exactly one word: direct, cot, or pot.

Problem:
{question}"""


def format_prompt(template: str, question: str, **kw) -> str:
    return template.format(question=question, **kw)
