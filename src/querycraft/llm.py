"""Adapter mỏng cho các LLM backend: Ollama (local), Anthropic, OpenAI, Mock."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass, field


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0
    seconds: float = 0.0

    def add(self, p: int, c: int, s: float) -> None:
        self.prompt_tokens += p
        self.completion_tokens += c
        self.calls += 1
        self.seconds += s


class LLM:
    name = "base"

    def __init__(self) -> None:
        self.usage = Usage()

    def chat(self, system: str, user: str, temperature: float = 0.0, seed: int = 0) -> str:
        raise NotImplementedError


class OllamaLLM(LLM):
    def __init__(self, model: str = "qwen3:8b", host: str = "http://localhost:11434", num_ctx: int = 8192):
        super().__init__()
        self.model, self.host, self.num_ctx = model, host, num_ctx
        self.name = f"ollama/{model}"

    def chat(self, system, user, temperature=0.0, seed=0):
        body = {
            "model": self.model,
            "stream": False,
            "think": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": temperature, "seed": seed, "num_ctx": self.num_ctx, "num_predict": 1024},
        }
        req = urllib.request.Request(
            f"{self.host}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
        )
        t0 = time.time()
        for attempt in range(3):  # Ollama đôi khi treo khi nhiều client tranh GPU: timeout ngắn rồi thử lại
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    out = json.load(r)
                break
            except (TimeoutError, OSError):
                if attempt == 2:
                    raise
        self.usage.add(out.get("prompt_eval_count", 0), out.get("eval_count", 0), time.time() - t0)
        return out["message"]["content"]


class AnthropicLLM(LLM):
    def __init__(self, model: str = "claude-haiku-5-5", max_tokens: int = 1024):
        super().__init__()
        import anthropic

        self.client = anthropic.Anthropic()
        self.model, self.max_tokens = model, max_tokens
        self.name = f"anthropic/{model}"

    def chat(self, system, user, temperature=0.0, seed=0):
        t0 = time.time()
        r = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        self.usage.add(r.usage.input_tokens, r.usage.output_tokens, time.time() - t0)
        return "".join(b.text for b in r.content if b.type == "text")


class OpenAILLM(LLM):
    def __init__(self, model: str = "gpt-4o-mini", base_url: str | None = None):
        super().__init__()
        from openai import OpenAI

        self.client = OpenAI(base_url=base_url or os.getenv("OPENAI_BASE_URL"))
        self.model = model
        self.name = f"openai/{model}"

    def chat(self, system, user, temperature=0.0, seed=0):
        t0 = time.time()
        r = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            seed=seed,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        u = r.usage
        self.usage.add(u.prompt_tokens, u.completion_tokens, time.time() - t0)
        return r.choices[0].message.content or ""


@dataclass
class MockLLM(LLM):
    """Trả về chuỗi định sẵn; dùng cho unit test."""

    replies: list[str] = field(default_factory=list)
    name: str = "mock"

    def __post_init__(self) -> None:
        LLM.__init__(self)
        self.calls: list[tuple[str, str]] = []

    def chat(self, system, user, temperature=0.0, seed=0):
        self.calls.append((system, user))
        self.usage.add(0, 0, 0.0)
        return self.replies.pop(0) if self.replies else "SELECT 1"


def make_llm(spec: str) -> LLM:
    """spec dạng 'ollama:qwen3:8b', 'anthropic:claude-haiku-5-5', 'openai:gpt-4o-mini'."""
    kind, _, model = spec.partition(":")
    if kind == "ollama":
        return OllamaLLM(model or "qwen3:8b")
    if kind == "anthropic":
        return AnthropicLLM(model or "claude-haiku-5-5")
    if kind == "openai":
        return OpenAILLM(model or "gpt-4o-mini")
    raise ValueError(f"Unknown LLM spec: {spec}")


_SQL_BLOCK = re.compile(r"```(?:sql)?\s*(.*?)```", re.S | re.I)


def extract_sql(text: str) -> str:
    m = _SQL_BLOCK.search(text)
    sql = (m.group(1) if m else text).strip()
    sql = re.sub(r"<think>.*?</think>", "", sql, flags=re.S).strip()
    return sql.rstrip(";").strip()
