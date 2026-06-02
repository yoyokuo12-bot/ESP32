# tools

開發/測試輔助工具。

| 檔案 | 用途 |
|---|---|
| `mock_publisher.py` | 模擬 L1，經 MQTT 持續發布合成 telemetry 給 L2（需 broker + paho-mqtt） |

無 broker 時請改用 [../middleware/simulate.py](../middleware/simulate.py)（離線、免安裝）。
