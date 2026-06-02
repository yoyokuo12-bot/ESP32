# L2 中介處理層 (Middleware)

訂閱 L1 telemetry → 清洗/校準 → 特徵工程 → 輸出**狀態標籤** (state packet) 給 L3。
規格見 [../docs/SPEC.md](../docs/SPEC.md) §2、§4「角色 B」。

## 安裝

```bash
python -m pip install -r ../requirements.txt   # 離線路徑其實只需 pandas/numpy
```

## 兩種執行路徑

### A. 離線（無需 MQTT broker、無需硬體）— 先用這個
用模擬 L1 資料把整條 L2 跑一遍，印出每筆的狀態：

```bash
python -m middleware.simulate            # 從 repo 根目錄執行
python -m middleware.simulate --summary  # 只看狀態變化的時點
```

### B. 即時（需 Mosquitto + paho-mqtt）— 之後接真資料/模擬發布器
```bash
# 終端 1：啟動 broker（先安裝 Mosquitto）
mosquitto -v
# 終端 2：L2 訂閱並處理
python -m middleware.ingest --host localhost
# 終端 3：模擬 L1 持續發布
python -m tools.mock_publisher --host localhost --interval 1
```

## 測試
```bash
pytest middleware/tests            # 有裝 pytest
python middleware/tests/test_state.py     # 沒裝 pytest 也能跑
python middleware/tests/test_pipeline.py
```

## 模組
| 檔案 | 職責 |
|---|---|
| `pipeline.py` | ADC 校準、中位數濾波、`compute_stats()`（純函式） |
| `state.py` | `classify()` 把 stats → 狀態標籤；閾值集中於 `THRESHOLDS` |
| `store.py` | SQLite 落地與近期視窗查詢 |
| `mocksource.py` | 模擬 L1 telemetry（乾旱→澆水→熱浪劇本），標 `sim:true` |
| `simulate.py` | 離線驅動（A 路徑） |
| `ingest.py` | MQTT 即時驅動（B 路徑） |
| `calibration.json` | 土壤/光照 ADC↔物理量 校準（到貨後更新） |

## 介面合約
- 輸入：[../contracts/telemetry.schema.json](../contracts/telemetry.schema.json)
- 輸出：[../contracts/state_packet.schema.json](../contracts/state_packet.schema.json)
