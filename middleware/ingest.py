"""L2 即時管線：訂閱 MQTT telemetry → 落地 → 清洗/特徵/狀態 → 回發 state packet。

需要 MQTT broker（如本機 Mosquitto）與 paho-mqtt：
    pip install paho-mqtt
    python -m middleware.ingest --host localhost
搭配模擬 L1：另開一個終端跑 `python -m tools.mock_publisher`。
若還沒裝 broker，只想驗證 L2 邏輯，請改用：python -m middleware.simulate
"""
from __future__ import annotations

import argparse
import json
import sys

from . import config, store
from .pipeline import compute_stats, load_calibration
from .state import build_state_packet
from cognition.generator import generate_diary
from cognition.llm_client import get_client

_LAST_STATE = {}


def handle_payload(conn, calib, payload: bytes | str, publish=None, client=None) -> dict | None:
    """處理單筆 telemetry：落地 → 算 stats/state → （可選）生成日記 → （可選）回發。回傳 state packet。"""
    try:
        rec = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        print("! 收到非 JSON 訊息，略過")
        return None
    if "node" not in rec or "ts" not in rec:
        print("! 缺 node/ts，略過：", rec)
        return None

    # ESP32 傳來的是 uptime (開機幾秒)，小於 1000000000 代表不是 Unix timestamp
    import time
    if rec["ts"] < 1000000000:
        rec["ts"] = int(time.time())

    store.insert(conn, rec)
    # 回看視窗：diff 視窗再加緩衝，確保抓得到 1 小時前那筆
    since = int(rec["ts"]) - config.DIFF_WINDOW_SEC - 2 * 3600
    window = store.recent(conn, rec["node"], since)
    stats = compute_stats(window, calib,
                          diff_window_sec=config.DIFF_WINDOW_SEC,
                          smooth_samples=config.SMOOTH_SAMPLES)
    pkt = build_state_packet(rec["node"], rec["ts"], stats)
    print(json.dumps(pkt, ensure_ascii=False))

    if publish is not None:
        publish(config.STATE_TOPIC_FMT.format(node=rec["node"]),
                json.dumps(pkt, ensure_ascii=False))

    # --- 串接 L3 生成日記 ---
    global _LAST_STATE
    node_id = rec["node"]
    if client:
        # 如果是剛啟動或是狀態改變，才觸發生成（避免無限消耗 LLM 額度）
        if _LAST_STATE.get(node_id) != pkt["state"]:
            print(f"🌿 狀態改變 ({_LAST_STATE.get(node_id)} -> {pkt['state']})，正在生成新日記...")
            try:
                diary = generate_diary(pkt, client=client)
                diary["stats"] = pkt["stats"]
                store.insert_diary(conn, diary)
                _LAST_STATE[node_id] = pkt["state"]
                print(f"📖 日記已儲存: {diary['diary']}")
            except Exception as e:
                print(f"❌ 生成日記失敗: {e}")
                
    return pkt


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="L2 中介層（MQTT 即時）")
    ap.add_argument("--host", default=config.MQTT_HOST)
    ap.add_argument("--port", type=int, default=config.MQTT_PORT)
    ap.add_argument("--topic", default=config.TELEMETRY_TOPIC)
    ap.add_argument("--db", default=str(config.DB_PATH))
    ap.add_argument("--no-publish", action="store_true", help="只印 state，不回發 MQTT")
    ap.add_argument("--provider", default="stub", help="L3 思考引擎：stub(預設)/gemini/openai/ollama")
    args = ap.parse_args()

    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        raise SystemExit("需要 paho-mqtt：pip install paho-mqtt"
                         "（或改用免 broker 的 python -m middleware.simulate）")

    calib = load_calibration(config.CALIBRATION_PATH)
    conn = store.connect(args.db)
    llm_client = get_client(args.provider)

    def on_connect(client, userdata, flags, reason_code, properties=None):
        print(f"已連線 broker {args.host}:{args.port}，訂閱 {args.topic}")
        client.subscribe(args.topic, qos=1)

    def on_message(mqtt_client, userdata, msg):
        publish = None if args.no_publish else (lambda t, p: mqtt_client.publish(t, p, qos=1))
        handle_payload(conn, calib, msg.payload, publish=publish, client=llm_client)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.host, args.port, keepalive=60)
    print("L2 ingest 啟動，Ctrl-C 結束")
    client.loop_forever()


if __name__ == "__main__":
    main()
