"""清洗/校準/特徵單元測試。可用 pytest 或直接 `python middleware/tests/test_pipeline.py` 執行。"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from middleware.pipeline import (  # noqa: E402
    compute_stats, median_filter, raw_to_light_pct, raw_to_moisture_pct,
)

CALIB = {"moisture": {"raw_dry": 3000, "raw_wet": 1300},
         "light": {"raw_dark": 0, "raw_bright": 4095}}


def test_moisture_calibration_endpoints():
    assert raw_to_moisture_pct(3000, CALIB) == 0.0      # 全乾
    assert raw_to_moisture_pct(1300, CALIB) == 100.0    # 全濕
    assert abs(raw_to_moisture_pct((3000 + 1300) / 2, CALIB) - 50.0) < 0.01


def test_moisture_clamped():
    assert raw_to_moisture_pct(4095, CALIB) == 0.0      # 比全乾還乾 → 夾在 0
    assert raw_to_moisture_pct(0, CALIB) == 100.0       # 比全濕還濕 → 夾在 100


def test_light_calibration():
    assert raw_to_light_pct(0, CALIB) == 0.0
    assert raw_to_light_pct(4095, CALIB) == 100.0


def test_median_filter_ignores_spike():
    assert median_filter([1, 100, 2, 3, 2]) == 2.0


def test_compute_stats_diff_positive_after_watering():
    dt = 300
    recs = []
    for i in range(13):  # 13*300 = 3900s > 3600，確保有「1 小時前」那筆
        raw = 2800 if i < 7 else 1500   # 先乾後濕
        recs.append({"node": "p", "ts": i * dt, "moisture_raw": raw,
                     "temp_c": 26.0, "humidity_pct": 55.0, "light_raw": 2000, "sim": True})
    stats = compute_stats(recs, CALIB, diff_window_sec=3600, smooth_samples=3)
    assert stats["moisture_diff_1h"] > 0
    assert stats["temp_c"] == 26.0
    assert stats["sim"] is True
    assert stats["n_samples"] == 13


def test_compute_stats_empty_raises():
    try:
        compute_stats([], CALIB)
    except ValueError:
        return
    raise AssertionError("空資料應拋 ValueError")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print("PASS", fn.__name__)
        except AssertionError as e:
            failed += 1
            print("FAIL", fn.__name__, repr(e))
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
