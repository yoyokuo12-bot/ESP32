"""極簡 .env 載入器（零相依，不需 python-dotenv）。

讀取 repo 根目錄的 .env，把其中「尚未設定」的鍵補進 os.environ。
已存在的環境變數（shell 設定）優先，不會被覆寫。
支援格式：KEY=VALUE、# 註解、空行、可選的前綴 export、值可加引號。
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = REPO_ROOT / ".env"


def load_dotenv(path: str | Path | None = None) -> dict[str, str]:
    """載入 .env；回傳這次實際寫入 os.environ 的鍵值（方便除錯）。"""
    env_path = Path(path) if path else DEFAULT_ENV_PATH
    loaded: dict[str, str] = {}
    if not env_path.exists():
        return loaded
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val
            loaded[key] = val
    return loaded
