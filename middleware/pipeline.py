"""L2 數據清洗、校準與特徵工程（Pandas）。

對應簡報「Key Insight：從數學陣列萃取統計狀態，徹底解決 LLM 處理數字能力不足」。
流程：原始 ADC 陣列 → 校準成物理量 → 算出供 L3 使用的統計摘要 (stats)。
本模組為純函式、不做 I/O，可離線單元測試。
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


def load_calibration(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return float(max(lo, min(hi, x)))


def _none_if_nan(x: Any) -> Any:
    if x is None:
        return None
    if isinstance(x, float) and math.isnan(x):
        return None
    return x


def raw_to_moisture_pct(raw: float, calib: dict) -> float:
    """電容式感測：raw 越接近 raw_wet（越小）→ 濕度百分比越高。"""
    m = calib["moisture"]
    dry, wet = float(m["raw_dry"]), float(m["raw_wet"])
    if dry == wet:
        return 0.0
    return _clamp((dry - float(raw)) / (dry - wet) * 100.0)


def raw_to_light_pct(raw: float, calib: dict) -> float:
    l = calib["light"]
    dark, bright = float(l["raw_dark"]), float(l["raw_bright"])
    if bright == dark:
        return 0.0
    return _clamp((float(raw) - dark) / (bright - dark) * 100.0)


def median_filter(values: Iterable[float]) -> float:
    """對一組樣本取中位數（去突波），自動忽略 NaN。"""
    arr = np.asarray(list(values), dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return float("nan")
    return float(np.median(arr))


def compute_stats(
    records: Iterable[dict],
    calib: dict,
    diff_window_sec: int = 3600,
    smooth_samples: int = 5,
) -> dict:
    """把一段近期 telemetry（同一 node、依 ts 排序前不限）萃取成 stats 摘要。

    回傳欄位對齊規格書 §2.2 State Packet 的 stats。
    """
    recs = list(records)
    if not recs:
        raise ValueError("compute_stats: 無資料")

    df = pd.DataFrame(recs).sort_values("ts").reset_index(drop=True)

    # 校準 ADC → 物理百分比
    df["moisture_pct"] = df["moisture_raw"].apply(lambda r: raw_to_moisture_pct(r, calib))
    has_light = "light_raw" in df.columns
    if has_light:
        df["light_pct"] = df["light_raw"].apply(
            lambda r: raw_to_light_pct(r, calib) if pd.notna(r) else np.nan
        )

    latest = df.iloc[-1]
    now_ts = int(latest["ts"])

    # 目前值：最近 smooth_samples 筆取中位數，濾掉殘餘突波
    recent = df.tail(smooth_samples)
    moisture_now = median_filter(recent["moisture_pct"])

    # 1 小時前的濕度：取 ts <= now-window 的最後一筆；資料不足則用最早一筆
    past = df[df["ts"] <= now_ts - diff_window_sec]
    moisture_past = float((past.iloc[-1] if len(past) else df.iloc[0])["moisture_pct"])
    moisture_diff = moisture_now - moisture_past

    sim_val = latest.get("sim", False)
    sim = bool(sim_val) if pd.notna(sim_val) else False

    light_pct = median_filter(recent["light_pct"]) if has_light else None
    humidity = float(latest["humidity_pct"]) if "humidity_pct" in df.columns else None

    return {
        "moisture_pct": round(moisture_now, 1),
        "moisture_diff_1h": round(moisture_diff, 1),
        "temp_c": round(float(latest["temp_c"]), 1) if "temp_c" in df.columns else None,
        "humidity_pct": _none_if_nan(round(humidity, 1) if humidity is not None else None),
        "light_pct": _none_if_nan(round(light_pct, 1) if light_pct is not None else None),
        "n_samples": int(len(df)),
        "sim": sim,
    }
