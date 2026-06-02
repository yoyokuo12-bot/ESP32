"""LLM 供應商抽象。

- StubLLMClient：離線、免 API key，用模板 + 真實 stats 產生擬人化日記。
- OpenAICompatibleClient：OpenAI / Ollama / Gemini / 任意相容端點（延遲載入 openai 套件）。
- get_client()：依設定挑選，預設 stub。

介面：client.generate(packet, system, few_shot) -> str
"""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Protocol

from . import config
from .examples import STUB_TEMPLATES

# Gemini 的 OpenAI 相容端點與預設模型（用 Gemini API key 即可走這條）
GEMINI_OPENAI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_DEFAULT_MODEL = "gemini-2.0-flash"

# 本機 Ollama 的 OpenAI 相容端點與預設模型（不需金鑰）
OLLAMA_DEFAULT_BASE = "http://localhost:11434/v1"
OLLAMA_DEFAULT_MODEL = "llama3.1"


class LLMClient(Protocol):
    def generate(self, packet: dict, system: str, few_shot: list[tuple[str, str]]) -> str:
        ...


def _stat_fmt(stats: dict) -> defaultdict:
    """供模板 format 用；缺值回 0.0，避免 KeyError。"""
    base = {
        "moisture": stats.get("moisture_pct"),
        "temp": stats.get("temp_c"),
        "light": stats.get("light_pct"),
    }
    base = {k: (v if v is not None else 0.0) for k, v in base.items()}
    return defaultdict(lambda: 0.0, base)


def _grounding(packet: dict) -> str:
    s = packet.get("stats", {})
    return (
        f"今天的狀態是 {packet.get('state')}。"
        f"感測數據：土壤濕度 {s.get('moisture_pct')}%"
        f"（過去一小時變化 {s.get('moisture_diff_1h')}）、"
        f"溫度 {s.get('temp_c')}°C、空氣濕度 {s.get('humidity_pct')}%、光照 {s.get('light_pct')}%。"
        f"請只根據這些數據，用你的人格寫一篇今天的日記。"
    )


class StubLLMClient:
    """離線生成器：不需任何 API。"""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def generate(self, packet: dict, system: str | None = None,
                 few_shot: list | None = None) -> str:
        state = packet.get("state", "STABLE")
        templates = STUB_TEMPLATES.get(state) or STUB_TEMPLATES["STABLE"]
        tmpl = self._rng.choice(templates)
        try:
            return tmpl.format_map(_stat_fmt(packet.get("stats", {})))
        except Exception:
            return tmpl


class OpenAICompatibleClient:
    """OpenAI 相容 Chat Completions（OpenAI / Ollama / 其他相容端點）。"""

    def __init__(self, model: str | None = None, base_url: str | None = None,
                 api_key: str | None = None, temperature: float | None = None,
                 max_retries: int | None = None, max_tokens: int | None = None):
        self.model = model or config.MODEL
        self.base_url = base_url or config.BASE_URL
        self.api_key = api_key or config.API_KEY
        self.temperature = config.TEMPERATURE if temperature is None else temperature
        self.max_retries = config.MAX_RETRIES if max_retries is None else max_retries
        self.max_tokens = config.MAX_OUTPUT_TOKENS if max_tokens is None else max_tokens
        self.last_usage = None  # 最近一次呼叫的 token 用量（供 --usage 顯示）

    def generate(self, packet: dict, system: str,
                 few_shot: list[tuple[str, str]]) -> str:
        try:
            from openai import OpenAI  # 延遲載入
        except ImportError as e:
            raise SystemExit("需要 openai 套件：pip install openai（或用預設 stub 供應商）") from e

        client = OpenAI(api_key=self.api_key or "ollama", base_url=self.base_url,
                        max_retries=self.max_retries)
        messages = [{"role": "system", "content": system}]
        for st, ex in (few_shot or []):
            messages.append({"role": "user", "content": f"今天的狀態是 {st}。請寫日記。"})
            messages.append({"role": "assistant", "content": ex})
        messages.append({"role": "user", "content": _grounding(packet)})

        resp = client.chat.completions.create(
            model=self.model, messages=messages,
            temperature=self.temperature, max_tokens=self.max_tokens,
        )
        self.last_usage = getattr(resp, "usage", None)
        return resp.choices[0].message.content or ""


def get_client(provider: str | None = None) -> LLMClient:
    provider = (provider or config.PROVIDER or "stub").lower()
    if provider in ("stub", "offline", "mock", ""):
        return StubLLMClient()
    if provider in ("openai", "compatible"):
        return OpenAICompatibleClient()
    if provider == "ollama":
        # 本機 Ollama：自動指向本機端點、用 dummy 金鑰，
        # 避免 base_url 未設定時退回 OpenAI 端點、又誤用其他供應商的金鑰。
        return OpenAICompatibleClient(
            model=config.MODEL_ENV or OLLAMA_DEFAULT_MODEL,
            base_url=config.BASE_URL or OLLAMA_DEFAULT_BASE,
            api_key="ollama",
        )
    if provider == "gemini":
        # Gemini 提供 OpenAI 相容端點：沿用 OpenAICompatibleClient，只換 base_url 與預設模型
        return OpenAICompatibleClient(
            model=config.MODEL_ENV or GEMINI_DEFAULT_MODEL,
            base_url=config.BASE_URL or GEMINI_OPENAI_BASE,
        )
    raise ValueError(f"未知的 LLM provider：{provider}"
                     "（可用：stub / openai / ollama / gemini）")
