"""模擬 L1 資料來源（硬體未到位時用）。

產生一段「盆栽逐漸變乾 → 被澆水 → 午後高溫」的合成 telemetry，
讓整條 L2→L3 管線在無實體感測器、甚至無 MQTT broker 的情況下也能跑通與展示。
輸出格式完全符合 contracts/telemetry.schema.json，並標記 sim=true。

BME280 / LDR 到貨後，韌體把對應欄位換成實測值、移除 sim 即可，下游無須改動。
"""
from __future__ import annotations

import math
import random
import time
from typing import Iterator

# 與 calibration.json 對應：raw 越大越乾
RAW_DRY = 3000
RAW_WET = 1300


def _moisture_pct_to_raw(pct: float) -> int:
    pct = max(0.0, min(100.0, pct))
    raw = RAW_DRY - (pct / 100.0) * (RAW_DRY - RAW_WET)
    return int(round(raw))


def generate(n: int = 240, dt: int = 300, start_ts: int | None = None,
             node: str = "plant_01", seed: int = 42) -> list[dict]:
    """產生 n 筆、每筆間隔 dt 秒的模擬 telemetry。

    劇本（讓每個狀態都至少出現一次）：
      - 前段：穩定濕潤                          → STABLE
      - 中段：持續變乾，跌破 20% 且仍在下降      → CRITICAL_DROUGHT
      - 約 70% 處：一次澆水，1 小時內濕度急升     → WATERING_DETECTED
      - 50%~60% 疊加一波熱浪，溫度 > 30°C         → HEAT_STRESS
    """
    rng = random.Random(seed)
    if start_ts is None:
        start_ts = int(time.time()) - n * dt
    water_idx = int(n * 0.70)

    records: list[dict] = []
    moisture = 75.0  # 起始濕度 %
    for i in range(n):
        ts = start_ts + i * dt
        frac = i / max(1, n - 1)

        # --- 濕度模型 ---
        if i < water_idx:
            moisture -= 0.25 + 0.5 * frac        # 緩慢變乾，中後段加速
        elif i == water_idx:
            moisture += 55.0                      # 澆水：急升
        else:
            moisture -= 0.3
        moisture = max(3.0, min(98.0, moisture))
        moisture_raw = _moisture_pct_to_raw(moisture + rng.uniform(-1.0, 1.0))

        # --- 溫度：日夜正弦（24h 週期），50%~60% 一波熱浪 ---
        hours = (ts % 86400) / 3600.0
        temp = 25.0 + 6.0 * math.sin((hours - 9) / 24.0 * 2 * math.pi) + rng.uniform(-0.5, 0.5)
        if 0.50 <= frac <= 0.60:
            temp += 6.0
        temp = round(temp, 1)

        humidity = round(max(20.0, min(95.0, 70.0 - (temp - 25.0) * 2.0 + rng.uniform(-3, 3))), 1)

        light_pct = max(0.0, math.sin((hours - 6) / 24.0 * 2 * math.pi)) * 100.0
        light_raw = int(round(light_pct / 100.0 * 4095))

        records.append({
            "node": node,
            "ts": ts,
            "moisture_raw": moisture_raw,
            "light_raw": light_raw,
            "temp_c": temp,
            "humidity_pct": humidity,
            "sim": True,
        })
    return records


def stream(dt: int = 300, node: str = "plant_01", seed: int = 42,
           realtime: bool = False, interval: float = 1.0) -> Iterator[dict]:
    """無限串流（給 mock_publisher 用）。ts 以 dt 持續遞增、時間序連貫；
    realtime=True 時每筆之間實際 sleep interval 秒。"""
    cycle = generate(n=240, dt=dt, node=node, seed=seed)
    offset = 0
    while True:
        for rec in cycle:
            out = dict(rec)
            out["ts"] = rec["ts"] + offset
            yield out
            if realtime:
                time.sleep(interval)
        offset += len(cycle) * dt
