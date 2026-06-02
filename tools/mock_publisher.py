"""模擬 L1：把合成 telemetry 經 MQTT 發布給 L2（硬體未到位時用）。

需要 broker 與 paho-mqtt：
    pip install paho-mqtt
    python -m tools.mock_publisher --host localhost --interval 1
無 broker、只想看 L2 結果，請改用：python -m middleware.simulate
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 允許以 `python tools/mock_publisher.py` 直接執行（補上 repo root 到 sys.path）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from middleware import config, mocksource  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="模擬 L1 telemetry 發布器")
    ap.add_argument("--host", default=config.MQTT_HOST)
    ap.add_argument("--port", type=int, default=config.MQTT_PORT)
    ap.add_argument("--node", default="plant_01")
    ap.add_argument("--dt", type=int, default=300, help="每筆間隔（模擬時間秒）")
    ap.add_argument("--interval", type=float, default=1.0, help="實際每筆發布間隔秒")
    ap.add_argument("--count", type=int, default=0, help="發布筆數，0=持續")
    args = ap.parse_args()

    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        raise SystemExit("需要 paho-mqtt：pip install paho-mqtt")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(args.host, args.port, keepalive=60)
    client.loop_start()

    topic = f"plants/{args.node}/telemetry"
    sent = 0
    try:
        for rec in mocksource.stream(dt=args.dt, node=args.node,
                                     realtime=True, interval=args.interval):
            client.publish(topic, json.dumps(rec, ensure_ascii=False), qos=1)
            print("→", topic, rec)
            sent += 1
            if args.count and sent >= args.count:
                break
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
