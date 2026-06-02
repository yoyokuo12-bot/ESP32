"""L2 狀態分類：把 stats 摘要映射成語義標籤（供 L3 生成日記）。

規則取自簡報 §11 / 規格書 §2.3。所有閾值集中於 THRESHOLDS，便於用真實資料調校。
純函式、無 I/O，可離線單元測試。
"""
from __future__ import annotations

from typing import Any

# 狀態標籤（大寫 SNAKE_CASE，與 contracts/state_packet.schema.json 一致）
CRITICAL_DROUGHT = "CRITICAL_DROUGHT"
HEAT_STRESS = "HEAT_STRESS"
WATERING_DETECTED = "WATERING_DETECTED"
LOW_LIGHT = "LOW_LIGHT"
STABLE = "STABLE"

ALL_STATES = [CRITICAL_DROUGHT, HEAT_STRESS, WATERING_DETECTED, LOW_LIGHT, STABLE]

THRESHOLDS = {
    "drought_moisture_pct": 20.0,  # 低於此且仍在變乾 → 乾旱危急
    "heat_temp_c": 30.0,           # 高於此 → 高溫壓力
    "watering_rise_pct": 30.0,     # 1 小時內濕度升幅高於此 → 偵測到澆水
    "low_light_pct": 15.0,         # 低於此 → 光照不足（選做；目前為瞬時判斷，未做持續 N 筆）
}


def classify(stats: dict, thresholds: dict | None = None) -> str:
    """依優先序回傳單一主要狀態：澆水 > 乾旱 > 高溫 > 光照不足 > 穩定。"""
    t = {**THRESHOLDS, **(thresholds or {})}
    moisture = stats.get("moisture_pct")
    diff = stats.get("moisture_diff_1h")
    temp = stats.get("temp_c")
    light = stats.get("light_pct")

    if diff is not None and diff >= t["watering_rise_pct"]:
        return WATERING_DETECTED
    if moisture is not None and moisture < t["drought_moisture_pct"] and (diff is not None and diff < 0):
        return CRITICAL_DROUGHT
    if temp is not None and temp > t["heat_temp_c"]:
        return HEAT_STRESS
    if light is not None and light < t["low_light_pct"]:
        return LOW_LIGHT
    return STABLE


def build_state_packet(node: str, ts: int, stats: dict, thresholds: dict | None = None) -> dict:
    """組裝符合規格書 §2.2 的 state packet。"""
    return {
        "node": node,
        "ts": int(ts),
        "state": classify(stats, thresholds),
        "stats": stats,
    }
