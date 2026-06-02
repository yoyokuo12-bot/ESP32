"""L3 設定（皆可用環境變數覆寫）。"""
from __future__ import annotations

import os
from pathlib import Path

try:  # 載入 repo 根目錄 .env（只補未設定的鍵；shell 既有環境變數優先）
    from common.env import load_dotenv
    load_dotenv()
except Exception:
    pass

ROOT = Path(__file__).resolve().parent

# 供應商：stub（離線預設）| openai | ollama | gemini（皆走 OpenAI 相容介面）
PROVIDER = os.getenv("LLM_PROVIDER", "stub")
MODEL_ENV = os.getenv("LLM_MODEL")          # None＝未指定，讓各供應商用自己的預設模型
MODEL = MODEL_ENV or "gpt-4o-mini"
# OpenAI 相容端點；Ollama 用 http://localhost:11434/v1；Gemini 由 get_client 自動帶入
BASE_URL = os.getenv("LLM_BASE_URL") or None
API_KEY = (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
           or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or None)
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.9"))
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))  # 429/5xx 自動重試（SDK 會指數退避並尊重 Retry-After）
# 輸出 token 上限。Gemini 2.5 等「思考」模型會先用 token 思考再輸出，太小會把可見文字截掉，故給足。
MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))

MAX_CHARS = int(os.getenv("DIARY_MAX_CHARS", "120"))
PERSONA_PATH = Path(os.getenv("PERSONA_PATH", str(ROOT / "prompts" / "persona.md")))
