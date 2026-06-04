# L1 邊緣感測層 (Firmware) — 待實作

角色 A 負責。硬體到位後放 `platformio.ini` 與 `src/main.cpp`。
規格見 [../docs/SPEC.md](../docs/SPEC.md) §3（BOM/腳位）、§4「角色 A」。

## 現況
- 硬體尚未取得；**L1 來源資料目前由模擬替代**：
  - 離線：[../middleware/mocksource.py](../middleware/mocksource.py)
  - 經 MQTT：[../tools/mock_publisher.py](../tools/mock_publisher.py)
- 到貨後韌體只要送出符合 [../contracts/telemetry.schema.json](../contracts/telemetry.schema.json) 的封包即可，L2 無須改動。

## MVP 韌體待辦
1. 讀 GPIO34 土壤濕度（10 次取樣取中位數）。
2. `temp_c`/`humidity_pct` 先填模擬值、封包加 `sim:true`。
3. 打包 JSON → MQTT publish 到 `plants/{node}/telemetry`。
4. 編譯旗標切換「真實 ↔ 模擬」。

擴充：接 BME280 (I2C GPIO21/22)、光照 (GPIO35)、深度睡眠。
