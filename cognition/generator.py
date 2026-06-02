"""L3 主程式：state packet → 提示工程 → LLM → 幽默日記。

用法：
    python -m cognition.generator --state CRITICAL_DROUGHT     # 單一狀態（合成資料）
    python -m cognition.generator --demo                       # 串接 L2 模擬，跑 L2→L3
    python -m cognition.generator --demo --provider openai     # 換真實 LLM（需設定金鑰）

輸出符合 CLAUDE.md §6.4：{ node, ts, state, diary }
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import config
from .examples import FEW_SHOT
from .llm_client import get_client

# 違規字串：人格破格 / 自曝 AI 身分（簡報 §10 生成約束）
BANNED = [
    "我是一個 AI", "我是一個人工智慧", "作為一個 AI", "作為一個人工智慧",
    "身為一個 AI", "我是一個語言模型", "語言模型", "as an AI", "language model",
]

# 各狀態的代表性 stats，供 --state 合成測試
SAMPLE_STATS = {
    "CRITICAL_DROUGHT": {"moisture_pct": 15.0, "moisture_diff_1h": -4.0, "temp_c": 28.0, "humidity_pct": 40.0, "light_pct": 50.0},
    "HEAT_STRESS":      {"moisture_pct": 55.0, "moisture_diff_1h": -1.0, "temp_c": 33.0, "humidity_pct": 45.0, "light_pct": 90.0},
    "WATERING_DETECTED": {"moisture_pct": 60.0, "moisture_diff_1h": 40.0, "temp_c": 24.0, "humidity_pct": 65.0, "light_pct": 30.0},
    "LOW_LIGHT":        {"moisture_pct": 50.0, "moisture_diff_1h": -1.0, "temp_c": 24.0, "humidity_pct": 60.0, "light_pct": 8.0},
    "STABLE":           {"moisture_pct": 65.0, "moisture_diff_1h": 0.0, "temp_c": 25.0, "humidity_pct": 60.0, "light_pct": 70.0},
}

PERSONA_FALLBACK = "你是一株有自我意識的盆栽，用第一人稱、帶點黑色幽默的傲嬌口吻寫今天的日記；不得自曝 AI 身分，不得虛構未提供的事件，120 字內。"


def load_persona() -> str:
    p = Path(config.PERSONA_PATH)
    return p.read_text(encoding="utf-8") if p.exists() else PERSONA_FALLBACK


def postprocess(text: str, max_chars: int) -> str:
    """清掉違規字串、修剪空白、限制長度（盡量在句尾截斷）。"""
    text = (text or "").strip()
    for b in BANNED:
        text = text.replace(b, "")
    text = text.strip(" ，,、。\n\t")
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    for sep in ("。", "！", "？", "\n"):
        idx = cut.rfind(sep)
        if idx >= max_chars * 0.6:
            return cut[: idx + 1]
    return cut


def synthetic_packet(state: str, node: str = "plant_demo", ts: int | None = None) -> dict:
    stats = dict(SAMPLE_STATS.get(state, SAMPLE_STATS["STABLE"]))
    stats.update({"n_samples": 12, "sim": True})
    return {"node": node, "ts": int(ts or time.time()), "state": state, "stats": stats}


def _error_hint(e: Exception) -> str:
    """依錯誤內容給對症的排解提示。"""
    msg = f"{type(e).__name__}: {e}".lower()
    if "401" in msg or "invalid_api_key" in msg or "authentication" in msg:
        return ("  → 401 認證失敗：金鑰與供應商不符或端點不對。\n"
                "    ollama 不需要金鑰、但要先啟動本機服務；gemini/openai 請確認金鑰正確。")
    if "429" in msg or "ratelimit" in msg or "resource_exhausted" in msg or "quota" in msg:
        return ("  → 429 額度/速率：免費額度可能為 0 或達每分鐘上限。\n"
                "    先用單次 --state、加 --sleep 5、或換模型(--model)/供應商。")
    if any(s in msg for s in ("connection", "refused", "connect", "timed out", "timeout")):
        return ("  → 連線失敗：本機服務沒開？Ollama 需先安裝並執行（啟動 Ollama App / ollama serve）。")
    return "  → 先用 --provider stub 確認流程，再排查供應商設定（金鑰、端點、模型名）。"


def _print_usage(client) -> None:
    """印出最近一次 LLM 呼叫的 token 用量（stub 無此資訊則略過）。"""
    u = getattr(client, "last_usage", None)
    if u is None:
        return
    pt = getattr(u, "prompt_tokens", "?")
    ct = getattr(u, "completion_tokens", "?")
    tt = getattr(u, "total_tokens", "?")
    print(f"  · tokens：prompt={pt} completion={ct} total={tt}")


def generate_diary(packet: dict, client=None, persona: str | None = None,
                   max_chars: int | None = None) -> dict:
    client = client or get_client()
    persona = persona or load_persona()
    max_chars = max_chars or config.MAX_CHARS
    raw = client.generate(packet, system=persona, few_shot=FEW_SHOT)
    return {
        "node": packet["node"],
        "ts": packet["ts"],
        "state": packet["state"],
        "diary": postprocess(raw, max_chars),
    }


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="L3 認知生成層：state → 幽默日記")
    ap.add_argument("--state", choices=list(SAMPLE_STATS), help="單一狀態（用合成資料）")
    ap.add_argument("--demo", action="store_true", help="串接 L2 模擬，跑 L2→L3")
    ap.add_argument("--provider", default=None,
                    help="stub（預設）/ openai / ollama / gemini")
    ap.add_argument("-n", type=int, default=240, help="--demo 的模擬樣本數")
    ap.add_argument("--dt", type=int, default=300, help="--demo 每筆間隔秒")
    ap.add_argument("--all", action="store_true",
                    help="--demo 時每次狀態變化都生成（預設只各狀態各一篇，避免免費額度）")
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="每次 LLM 呼叫間隔秒；免費額度（如 Gemini）建議 4~5")
    ap.add_argument("--model", default=None,
                    help="覆寫模型名稱，如 gemini-2.5-flash / gemini-1.5-flash")
    ap.add_argument("--usage", action="store_true",
                    help="顯示每次呼叫的 token 用量（僅雲端供應商）")
    args = ap.parse_args()

    client = get_client(args.provider)
    if args.model and hasattr(client, "model"):
        client.model = args.model

    if args.demo:
        from middleware.simulate import iter_packets  # 重用 L2
        seen: set[str] = set()
        last = None
        for pkt in iter_packets(args.n, args.dt):
            st = pkt["state"]
            if st == last:
                continue
            last = st
            if not args.all and st in seen:   # 預設每個狀態只生成一篇（≤5 次呼叫，避免觸發額度）
                continue
            seen.add(st)
            try:
                d = generate_diary(pkt, client=client)
            except Exception as e:
                print(f"\n[中止] 呼叫 LLM 失敗：{type(e).__name__}: {e}")
                print(_error_hint(e))
                break
            s = pkt["stats"]
            print(f"[{d['state']:17s}] moist={s['moisture_pct']:.0f}% temp={s['temp_c']:.0f}C")
            print(f"  {d['diary']}")
            if args.usage:
                _print_usage(client)
            print()
            if args.sleep:
                time.sleep(args.sleep)
            if not args.all and len(seen) >= len(SAMPLE_STATS):
                break
    else:
        pkt = synthetic_packet(args.state or "CRITICAL_DROUGHT")
        try:
            print(json.dumps(generate_diary(pkt, client=client), ensure_ascii=False, indent=2))
            if args.usage:
                _print_usage(client)
        except Exception as e:
            print(f"[失敗] {type(e).__name__}: {e}")
            print(_error_hint(e))


if __name__ == "__main__":
    main()
