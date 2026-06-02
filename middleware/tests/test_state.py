"""狀態分類單元測試。可用 pytest 或直接 `python middleware/tests/test_state.py` 執行。"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from middleware.state import (  # noqa: E402
    CRITICAL_DROUGHT, HEAT_STRESS, LOW_LIGHT, STABLE, WATERING_DETECTED, classify,
)


def test_watering_detected():
    assert classify({"moisture_pct": 60, "moisture_diff_1h": 35, "temp_c": 25}) == WATERING_DETECTED


def test_critical_drought():
    assert classify({"moisture_pct": 15, "moisture_diff_1h": -3, "temp_c": 25}) == CRITICAL_DROUGHT


def test_drought_needs_falling():
    # 低濕但未下降（diff>=0）不算乾旱
    assert classify({"moisture_pct": 15, "moisture_diff_1h": 0, "temp_c": 25}) == STABLE


def test_heat_stress():
    assert classify({"moisture_pct": 50, "moisture_diff_1h": -1, "temp_c": 31}) == HEAT_STRESS


def test_watering_beats_heat():
    # 優先序：澆水 > 高溫
    assert classify({"moisture_pct": 50, "moisture_diff_1h": 40, "temp_c": 35}) == WATERING_DETECTED


def test_low_light():
    assert classify({"moisture_pct": 50, "moisture_diff_1h": 0, "temp_c": 25, "light_pct": 5}) == LOW_LIGHT


def test_stable():
    assert classify({"moisture_pct": 50, "moisture_diff_1h": 0, "temp_c": 25, "light_pct": 80}) == STABLE


def test_handles_missing_fields():
    # 缺欄位不應拋例外
    assert classify({"moisture_pct": None, "moisture_diff_1h": None, "temp_c": None}) == STABLE


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
