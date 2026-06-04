"""產生模擬資料並寫入 DB：模擬 telemetry → 狀態 → 生成日記，全部落地 SQLite。

之後 app.server 只從 DB 讀，不會每次重新呼叫 LLM（避免成本與 429）。

用法：
    python -m app.seed                       # stub（離線、免金鑰）
    python -m app.seed --reset               # 先清掉舊資料再重建
    python -m app.seed --provider gemini --sleep 5   # 用真實 LLM 生成並存檔（放慢避免額度）
"""
from __future__ import annotations

import argparse
import sys
import time

from cognition.generator import generate_diary
from cognition.llm_client import get_client
from middleware import config as mw
from middleware import store
from middleware.mocksource import generate
from middleware.pipeline import compute_stats, load_calibration
from middleware.state import build_state_packet


def run(n: int = 240, dt: int = 300, provider: str | None = None, node: str = "plant_01",
        reset: bool = False, sleep: float = 0.0, model: str | None = None) -> tuple[int, int]:
    conn = store.connect(mw.DB_PATH)
    if reset:
        conn.execute("DELETE FROM telemetry WHERE node = ?", (node,))
        conn.execute("DELETE FROM diaries WHERE node = ?", (node,))
        conn.commit()

    calib = load_calibration(mw.CALIBRATION_PATH)
    client = get_client(provider)
    if model and hasattr(client, "model"):
        client.model = model

    records = generate(n=n, dt=dt, node=node)
    history: list[dict] = []
    last_state = None
    n_tel = n_diary = 0
    for rec in records:
        store.insert(conn, rec)
        n_tel += 1
        history.append(rec)
        cutoff = rec["ts"] - mw.DIFF_WINDOW_SEC - dt
        window = [r for r in history if r["ts"] >= cutoff]
        stats = compute_stats(window, calib,
                              diff_window_sec=mw.DIFF_WINDOW_SEC,
                              smooth_samples=mw.SMOOTH_SAMPLES)
        pkt = build_state_packet(rec["node"], rec["ts"], stats)
        if pkt["state"] != last_state:          # 狀態變化才生成日記（貼近實際、也省呼叫）
            diary = generate_diary(pkt, client=client)
            diary["stats"] = pkt["stats"]      # 附上當下統計，供日記本左頁「觀察便箋」
            store.insert_diary(conn, diary)
            n_diary += 1
            if sleep:
                time.sleep(sleep)
        last_state = pkt["state"]

    conn.close()
    print(f"已寫入：telemetry {n_tel} 筆、diaries {n_diary} 篇 → {mw.DB_PATH}")
    return n_tel, n_diary


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="產生模擬資料並寫入 DB（telemetry + 日記）")
    ap.add_argument("--provider", default=None, help="stub（預設）/ gemini / openai / ollama")
    ap.add_argument("--model", default=None, help="覆寫模型，如 gemini-2.5-flash")
    ap.add_argument("-n", type=int, default=240, help="模擬樣本數")
    ap.add_argument("--dt", type=int, default=300, help="每筆間隔秒（模擬時間）")
    ap.add_argument("--node", default="plant_01")
    ap.add_argument("--reset", action="store_true", help="先清空此 node 的舊資料")
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="每次 LLM 呼叫間隔秒（真實供應商免費額度建議 4~5）")
    args = ap.parse_args()
    run(n=args.n, dt=args.dt, provider=args.provider, node=args.node,
        reset=args.reset, sleep=args.sleep, model=args.model)


if __name__ == "__main__":
    main()
