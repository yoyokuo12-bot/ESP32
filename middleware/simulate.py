"""離線執行 L2：用模擬 L1 資料 → 清洗/特徵 → 狀態標籤（不需 MQTT broker）。

這是「硬體與 broker 都還沒有」時，驗證整條 L2 邏輯的入口。

用法：
    python -m middleware.simulate                 # 印出每筆的狀態
    python -m middleware.simulate --summary       # 只印狀態「變化」的時點
    python -m middleware.simulate -n 300 --dt 300
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

from . import config, mocksource
from .pipeline import compute_stats, load_calibration
from .state import build_state_packet


def _fmt(pkt: dict, marker: str = " ") -> str:
    s = pkt["stats"]
    light = s.get("light_pct")
    light_str = f"{light:5.1f}%" if light is not None else "  n/a"
    return (f"{marker} ts={pkt['ts']} {pkt['state']:17s} "
            f"moist={s['moisture_pct']:5.1f}% d1h={s['moisture_diff_1h']:+6.1f} "
            f"temp={s['temp_c']:4.1f}C light={light_str}"
            + ("  [sim]" if s.get("sim") else ""))


def iter_packets(n: int, dt: int):
    """產生一連串 state packet（供本檔與 L3 認知層重用）。"""
    calib = load_calibration(config.CALIBRATION_PATH)
    records = mocksource.generate(n=n, dt=dt)
    history: list[dict] = []
    for rec in records:
        history.append(rec)
        # 只取最近 (視窗 + 一點緩衝)，模擬 L2 的近期查詢
        cutoff = rec["ts"] - config.DIFF_WINDOW_SEC - dt
        window = [r for r in history if r["ts"] >= cutoff]
        stats = compute_stats(window, calib,
                              diff_window_sec=config.DIFF_WINDOW_SEC,
                              smooth_samples=config.SMOOTH_SAMPLES)
        yield build_state_packet(rec["node"], rec["ts"], stats)


def run(n: int, dt: int, summary: bool = False) -> Counter:
    counts: Counter = Counter()
    last_state = None
    for pkt in iter_packets(n, dt):
        counts[pkt["state"]] += 1
        if summary:
            if pkt["state"] != last_state:
                print(_fmt(pkt, marker="->"))
        else:
            print(_fmt(pkt))
        last_state = pkt["state"]

    print("\n=== 狀態統計 ===")
    for st, c in counts.most_common():
        print(f"  {st:18s} {c:4d}")
    return counts


def main() -> None:
    try:  # Windows 主控台預設非 UTF-8，強制 UTF-8 避免中文亂碼
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="離線執行 L2 中介層（模擬 L1）")
    ap.add_argument("-n", type=int, default=240, help="模擬樣本數")
    ap.add_argument("--dt", type=int, default=300, help="每筆間隔秒數（模擬時間）")
    ap.add_argument("--summary", action="store_true", help="只印狀態變化的時點")
    args = ap.parse_args()
    run(args.n, args.dt, summary=args.summary)


if __name__ == "__main__":
    main()
