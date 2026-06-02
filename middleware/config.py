"""L2 設定（皆可用環境變數覆寫）。"""
from __future__ import annotations

import os
from pathlib import Path

try:  # 載入 repo 根目錄 .env（只補未設定的鍵；shell 既有環境變數優先）
    from common.env import load_dotenv
    load_dotenv()
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent

# --- MQTT ---
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TELEMETRY_TOPIC = os.getenv("TELEMETRY_TOPIC", "plants/+/telemetry")
STATE_TOPIC_FMT = os.getenv("STATE_TOPIC_FMT", "plants/{node}/state")

# --- 儲存（SQLite；data/ 由程式自動建立，已列入 .gitignore） ---
DB_PATH = Path(os.getenv("L2_DB_PATH", str(ROOT / "data" / "telemetry.db")))

# --- 校準檔 ---
CALIBRATION_PATH = Path(os.getenv("CALIBRATION_PATH", str(ROOT / "calibration.json")))

# --- 特徵視窗 ---
DIFF_WINDOW_SEC = int(os.getenv("DIFF_WINDOW_SEC", "3600"))  # moisture_diff_1h 的回看視窗（秒）
SMOOTH_SAMPLES = int(os.getenv("SMOOTH_SAMPLES", "5"))       # L2 再做的移動中位數樣本數
