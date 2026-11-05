"""统一 LLM 调用封装 —— 全项目唯一调用 LLM 的入口。

规则（见 AGENTS.md）：其他模块禁止直接 import openai；
换模型 / 换供应商只改 config，不改代码。
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

import yaml
from openai import APIStatusError, OpenAI


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class LLMResponse:
    text: str
    tokens: int
    latency_s: float
    finish_reason: str | None = None
    raw: dict = field(default_factory=dict)


class LLMClient:
    """OpenAI 兼容的 LLM 客户端，带重试与用量记录。"""

    def __init__(self, config: dict | None = None, config_path: str = "config.yaml"):
        self.config = config or load_config(path=config_path)
        key_env = self.config.get("api_key_env", "OPENAI_API_KEY")
        api_key = os.environ.get(key_env, "")
        if not api_key:
            raise RuntimeError(
                f"API key is not set. Export {key_env} in the shell before evaluation."
            )
        base_url = self.config.get("api_base") or None
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = self.config["model"]
        self.default_temp = float(self.config.get("temperature", 0.0))
        self.max_tokens = int(self.config.get("max_tokens", 2048))
        self.enable_thinking = self.config.get("enable_thinking")
        self.seed = int(self.config.get("seed", 42))

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        seed: int | None = None,
        max_retries: int = 5,
    ) -> LLMResponse:
        """调用 chat completion，指数退避重试。

        Args:
            messages: OpenAI 消息列表 [{"role", "content"}]。
            temperature: 覆盖默认温度（self-consistency 需要 >0）。
            seed: 覆盖随机种子。
            max_retries: 对 429/5xx 的最大重试次数。
        """
        last_err: Exception | None = None
        for attempt in range(max_retries):
            try:
                t0 = time.time()
                request = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.default_temp if temperature is None else temperature,
                    "seed": self.seed if seed is None else seed,
                    "max_tokens": self.max_tokens,
                }
                if self.enable_thinking is not None:
                    request["extra_body"] = {"enable_thinking": bool(self.enable_thinking)}
                resp = self.client.chat.completions.create(**request)
                latency = time.time() - t0
                tokens = resp.usage.total_tokens if resp.usage else 0
                choice = resp.choices[0]
                text = choice.message.content or ""
                return LLMResponse(
                    text=text, tokens=tokens, latency_s=latency,
                    finish_reason=choice.finish_reason, raw=resp.model_dump(),
                )
            except APIStatusError as e:
                status = getattr(e, "status_code", None)
                error_text = str(e).lower()
                no_credit = status == 429 and any(
                    phrase in error_text
                    for phrase in ("no credits", "insufficient_quota", "billing")
                )
                if status in {400, 401, 403, 404} or no_credit:
                    detail = (
                        "Check API billing/quota."
                        if no_credit
                        else "Check the API key, endpoint, model, and provider region support."
                    )
                    raise RuntimeError(
                        f"Non-retryable LLM API error ({status}). {detail}"
                    ) from e
                last_err = e
                wait = min(2 ** attempt * 1.5, 60)
                time.sleep(wait)
            except Exception as e:  # noqa: BLE001 — 统一重试
                last_err = e
                wait = min(2 ** attempt * 1.5, 60)
                time.sleep(wait)
        raise RuntimeError(f"LLM call failed after {max_retries} retries: {last_err}")

    # ---- 便捷封装 ----

    def complete(self, prompt: str, *, system: str | None = None, **kw: Any) -> LLMResponse:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kw)


def record_result(path: str, record: dict) -> None:
    """把一条评测记录追加写入 JSONL（results/ 下）。"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
