"""一鍵 Demo：產生模擬資料 → 生成日記 → 啟動翻書網頁。

    python -m app.demo                      # stub（離線、免金鑰、最穩）
    python -m app.demo --provider gemini    # 用真實 LLM（需先設定 .env 金鑰）
    python -m app.demo --port 8001 --no-open --no-reset --sleep 5

等同於依序執行：
    python -m app.seed --reset
    python -m app.server
"""
from __future__ import annotations

import argparse

from app import seed, server


def main() -> None:
    ap = argparse.ArgumentParser(description="一鍵 Demo：產生資料後啟動翻書網頁")
    ap.add_argument("--provider", default="stub",
                    help="L3 供應商：stub(預設,免金鑰) / gemini / openai / ollama")
    ap.add_argument("--model", default=None, help="覆寫模型，如 gemini-2.5-flash")
    ap.add_argument("-n", type=int, default=240, help="模擬樣本數")
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="每次 LLM 呼叫間隔秒（真實供應商免費額度建議 4~5）")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-open", action="store_true", help="不自動開啟瀏覽器")
    ap.add_argument("--no-reset", action="store_true", help="沿用現有 DB，不清空重建")
    args = ap.parse_args()

    print("=== 步驟 1/2：產生模擬資料、計算狀態並生成日記 → 寫入 DB ===")
    seed.run(n=args.n, provider=args.provider, model=args.model,
             reset=not args.no_reset, sleep=args.sleep)

    print("\n=== 步驟 2/2：啟動翻書網頁 ===")
    server.serve(host=args.host, port=args.port, open_browser=not args.no_open)


if __name__ == "__main__":
    main()
