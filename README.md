# 🪴 擬人化盆栽物聯網 — LLM 幽默日記生成系統

把冷冰冰的盆栽感測數據，交給 LLM 寫成**第一人稱、幽默的「植物日記」**，並用**可單頁拖曳翻動的手寫日記本**呈現。
三層式架構：**L1 邊緣感測 (ESP32) → L2 中介處理 (Pandas) → L3 認知生成 (LLM) → 網頁呈現**。

---

## 🚀 一鍵 Demo

需求：Python 3.11+ 與 `pandas`、`numpy`（通常已具備）。**離線、免金鑰、免硬體**就能跑完整條鏈。

```bash
python -m app.demo
```

這條指令會：
1. 產生模擬感測資料 → 跑出狀態標籤 → 生成日記，全部寫入 SQLite；
2. 啟動網頁並自動開瀏覽器 **http://127.0.0.1:8000**
   （左：傳統數據儀表板＝**對照組**／右：可翻頁手寫日記＝**實驗組**）。

> 等同於手動兩步：`python -m app.seed --reset` 然後 `python -m app.server`。

**常用選項：**
```bash
python -m app.demo --provider gemini      # 改用真實 LLM 生成日記（需設定金鑰，見下）
python -m app.demo --port 8001 --no-open  # 換埠號、不自動開瀏覽器
python -m app.demo --sleep 5              # 真實 LLM 放慢，避免免費額度 429
python -m app.demo --no-reset             # 沿用現有資料、不清空重建
```

---

## 🔑 用真實 LLM（選用）

預設供應商是離線 `stub`（用模板＋真實數據生成，免金鑰）。要接真實 LLM：
複製 `.env.example` 為 `.env`（已被 `.gitignore` 忽略），填入：

```ini
LLM_PROVIDER=gemini
GEMINI_API_KEY=你的金鑰
# LLM_MODEL=gemini-2.5-flash   # 2.5 系列為「思考」模型，已預留足夠 token
```

支援 `gemini` / `openai`（OpenAI 相容）/ `ollama`（本機免金鑰）/ `stub`。細節見 [cognition/README.md](cognition/README.md)。

---

## 🧩 各層也可單獨執行

```bash
# L2 中介（離線，免 broker / 硬體）：模擬感測 → 狀態
python -m middleware.simulate --summary

# L3 認知：狀態 → 幽默日記
python -m cognition.generator --demo

# L2 即時 MQTT（需 broker + paho-mqtt）：訂閱 telemetry → 落地 → 狀態 →（狀態變化時）生成日記
python -m middleware.ingest --host localhost --provider stub
python -m tools.mock_publisher --host localhost      # 另一終端：模擬 L1 發布
```

## 🧪 測試
```bash
python middleware/tests/test_state.py
python middleware/tests/test_pipeline.py
python cognition/tests/test_generator.py
```

---

## 📁 文件地圖

| 檔案 | 內容 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 專題總覽、三層架構、開發流程、介面合約 |
| [DATAFLOW.md](DATAFLOW.md) | 實作資料流、函數相依、數值轉換演算法 |
| [FLIPBOOK.md](FLIPBOOK.md) | 翻書效果如何做出來（StPageFlip） |
| [docs/SPEC.md](docs/SPEC.md) | 規格書 / 分工 / 驗收標準 |
| [docs/FEASIBILITY.md](docs/FEASIBILITY.md) | 可行性與難點分析 |
| [docs/TODO.md](docs/TODO.md) | 專案待辦清單 |

## 🗂️ 目錄結構

```
firmware/    L1 ESP32 韌體（感測→MQTT）            middleware/  L2 Pandas 清洗/校準/狀態
cognition/   L3 LLM 提示工程→日記                  app/         呈現層（seed 落 DB + 翻書網頁）
contracts/   跨層資料合約 (JSON Schema)             tools/       模擬發布器等
```

> 硬體尚未到位時，L1 由 [middleware/mocksource.py](middleware/mocksource.py) 模擬替代；介面與 schema 不變，到貨後換實測即可，下游不動。
