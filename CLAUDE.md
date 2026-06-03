# CLAUDE.md

本檔案為 Claude Code (claude.ai/code) 在此儲存庫工作時的指引，同時也是本專題的開發總覽。
所有開發者（含學生分組）請先讀本檔，再依角色閱讀 [docs/SPEC.md](docs/SPEC.md)（規格書 / 分工）與 [docs/FEASIBILITY.md](docs/FEASIBILITY.md)（可行性與難點）。

---

## 1. 專題概述 (Project Overview)

**名稱：** 擬人化物聯網 — 基於大型語言模型 (LLM) 與環境感測數據之盆栽幽默日記生成系統
**英文：** Anthropomorphic IoT: LLM-based Humorous Diary Generation System for Potted Plants

**核心問題：** 傳統 IoT 儀表板（土壤濕度 40%、溫度 25°C…）要求使用者自行「翻譯」冷冰冰的數據，產生**認知負荷**與**警報疲乏 (Alert Fatigue)**，導致植物高死亡率。

**本專題的解法：** 結合**園藝治療 (Horticultural Therapy)** 概念，把盆栽**擬人化**。系統將感測數據轉成統計「狀態」，再交由 LLM 以**第一人稱、幽默口吻**撰寫植物的「每日日記」，讓使用者透過情感互動而非數據判讀來照顧植物（Human-in-the-loop）。

**研究定位（相對於現有領域）：**
| 取向 | 互動性 | 硬體成本 | 缺口 |
|---|---|---|---|
| 智慧園藝自動化 (Smart Gardening) | 將人排除 (Human-out-of-the-loop)，只自動澆水 | 中（致動器） | 無情感互動 |
| 會說話的植物 (Talking Plants) | 規則寫死 (Rule-based)，對話重複 | 高（觸控/馬達） | 內容千篇一律 |
| **本專題（生成式 AI 擬人化）** | **LLM 即時生成情境，Human-in-the-loop** | **低（純感測 + 雲端推論）** | — |

---

## 2. 系統架構 (Architecture) — 三層式端到端有機數據流

資料單向流動：**感測 → 處理 → 生成 → 呈現**。各層以明確介面（MQTT / 函式 I/O）解耦，是分工的邊界。

```
┌─────────────────────┐   MQTT/JSON   ┌──────────────────────┐   狀態標籤   ┌──────────────────────┐
│  L1 邊緣感測層        │ ───────────▶ │  L2 中介處理層         │ ─────────▶ │  L3 認知生成層         │
│  Edge Sensing        │  raw telemetry │  Middleware          │  state label │  Cognitive Generation │
│  ESP32 (C/C++)       │               │  Python + Pandas      │  + 統計摘要  │  LLM + Prompt Eng.    │
│  感測/取樣/深睡/上傳  │               │  清洗/校準/特徵工程    │             │  人格/情境/約束/日記   │
└─────────────────────┘               └──────────────────────┘             └───────────┬──────────┘
                                                                                        │ 日記文字
                                                                              ┌─────────▼──────────┐
                                                                              │  呈現層 (Display)   │
                                                                              │  Web / App / 電子紙 │
                                                                              └────────────────────┘
```

- **L1 邊緣感測層（韌體）：** ESP32-WROOM-32 擷取土壤濕度、溫濕度、光照；10 次取樣中位數濾波；以 JSON 經 MQTT 發布；採**極深度睡眠**（每 4 小時喚醒 3–5 秒）省電。
- **L2 中介處理層（後端/數據）：** 訂閱 MQTT；Pandas 清洗、ADC 校準、特徵工程；**把數字陣列萃取成統計狀態標籤**（解決 LLM 不擅長處理原始數字的問題）。
- **L3 認知生成層（AI）：** 提示工程（系統人格 + 情境注入 + 生成約束）呼叫 LLM，產出第一人稱幽默日記。
- **呈現層：** 並列呈現傳統儀表板與第一人稱幽默日記，凸顯「冷數據 vs 擬人化」的差異。

**設計關鍵（必記）：** LLM 不直接看原始數字。L2 先把 `moisture_raw=2850` 之類的陣列轉成 `CRITICAL_DROUGHT` 這種**語義標籤 + 統計摘要**，L3 只依標籤生成文字。這是避免 LLM 幻覺 (Hallucination) 與算錯數字的核心手段。

---

## 3. 技術棧 (Tech Stack)

| 層 | 語言/框架 | 關鍵套件/工具 |
|---|---|---|
| L1 韌體 | C/C++（Arduino core 或 ESP-IDF） | PlatformIO、`PubSubClient`(MQTT)、`Adafruit_BME280`、`esp_sleep` |
| 傳輸 | MQTT | Mosquitto（本機）或 HiveMQ/EMQX（雲端） |
| L2 中介 | Python 3.11+ | `paho-mqtt`、`pandas`、`numpy`、SQLite/InfluxDB |
| L3 認知 | Python | LLM API（雲端，見下方決策）、提示工程 |
| 呈現 | Web（Python 內建 `http.server`，零相依）+ 簡易前端 | — |

 **已定案決策（截至 2026-06）：**
 1. **目前範圍＝MVP**：實體感測只接 GPIO32 **土壤濕度**一顆；溫濕度、光照先不接實體感測器。
 2. **溫濕度感測器＝BME280**（I2C，GPIO21/22）。目前硬體不易取得，**完整專題所需的溫濕度資料暫以模擬資料替代**，到貨後換成真實讀值（程式介面不變）。

 **未定決策（請於 kickoff 確認，預設值見括號）：**
 1. LLM 供應商（預設：雲端 API，因 ESP32 無法跑 LLM；本機可選 Ollama 降成本）。
 2. 韌體框架（預設：PlatformIO + Arduino core，學習曲線最低）。
 3. 時序資料庫（預設：先用 SQLite/CSV，量大再換 InfluxDB）。

---

## 4. 儲存庫結構 (Repository Structure) — 規劃中

```
ESP32/
├── CLAUDE.md                  # 本檔
├── docs/
│   ├── SPEC.md                # 規格書（分工、模組規格、驗收標準）
│   └── FEASIBILITY.md         # 可行性與難點分析
├── firmware/                  # L1 ─ 角色 A
│   ├── platformio.ini
│   └── src/main.cpp           # 感測 + 中位數濾波 + MQTT + 深度睡眠
├── middleware/                # L2 ─ 角色 B
│   ├── ingest.py              # MQTT 訂閱 → 落地
│   ├── pipeline.py            # Pandas 清洗/校準/特徵
│   ├── state.py               # 觸發邏輯 → 狀態標籤
│   └── calibration.json       # ADC ↔ 物理量 對照
├── cognition/                 # L3 ─ 角色 C
│   ├── prompts/persona.md     # 系統人格定義
│   ├── generator.py           # 標籤 → LLM → 日記
│   └── llm_client.py
├── app/                       # 呈現層 + 整合 ─ 角色 D
│   ├── seed.py                # 模擬資料 → 落 DB（telemetry + 日記）
│   └── server.py              # 儀表板 vs 日記（讀 DB）
├── tools/
│   └── mock_publisher.py      # 缺感測器時，產生模擬 telemetry（溫濕度等）供全鏈測試
└── contracts/
    └── telemetry.schema.json  # 跨層資料合約（單一真實來源）
```

---

## 5. 開發流程 (Development Workflows) — 分階段拆解

 階段間以「介面合約」交付，可平行開發。每階段都要有可驗證的「完成定義 (DoD)」。

### P0 — 環境與骨架 (全員，第 0 週)
- 建 MQTT broker（先本機 Mosquitto）、Python venv、ESP32 toolchain、LLM API key。
- 凍結 [contracts/telemetry.schema.json](contracts/telemetry.schema.json) 與狀態標籤 enum（見 §6）。
- **DoD：** 一支假的 publisher 能送 JSON，假的 subscriber 能收到並印出。

### P1 — 邊緣感測層 (角色 A)
**MVP（現階段）：** 只接 GPIO32 土壤濕度；`temp_c`/`humidity_pct` 由韌體填**模擬值**（或改用 [tools/mock_publisher.py](tools/mock_publisher.py) 產生整包模擬資料），維持 schema 完整；**先不做深度睡眠**（always-on 較好除錯）。待 BME280 到貨再接 I2C，把模擬值換成實測。

1. 接線並對齊腳位（MVP：GPIO32 土壤；〔擴充〕GPIO33 光照、GPIO21/22 I2C 溫濕度）。
2. 感測器讀值；每項 10 次取樣取**中位數**（Median Filter）去突波。
3. Wi-Fi 連線 → 打包 JSON（缺的感測項以模擬值補齊）→ MQTT publish。
4. 〔擴充〕進入 `esp_deep_sleep_start()`，由 RTC 計時器每 4 小時喚醒。
- **DoD（MVP）：** 實機定時上傳一筆符合 schema 的 JSON（moisture 實測、溫濕度模擬）。
- **DoD（完整）：** 三感測皆實測、定時自動上傳。

### P2 — 中介處理層 (角色 B)
1. `ingest.py`：訂閱 MQTT，將每筆 telemetry 落地（含時間戳）。
2. `pipeline.py`：ADC → 物理量校準（用 [middleware/calibration.json](middleware/calibration.json)）、再次中位數/移動平均。
3. `state.py`：依 §6 觸發規則輸出**狀態標籤 + 統計摘要**。
- **DoD：** 餵入歷史資料能穩定輸出標籤；對人為突波過濾率達標（目標 100%）。

### P3 — 認知生成層 (角色 C)
1. 寫 `persona.md`（人格、語氣、禁止事項）。
2. `generator.py`：組裝 prompt（人格 + 情境標籤 + 約束）→ 呼叫 LLM → 回傳日記。
3. 約束：第一人稱、字數上限、禁止「我是一個 AI 語言模型…」、不得捏造未提供的數據。
- **DoD：** 給定每個狀態標籤都能產出風格一致、無幻覺、符合字數的中文日記。

### P4 — 呈現層與整合 (角色 D)
1. 串起 L1→L2→L3 端到端自動管線。
2. 做兩種畫面：**對照組**＝傳統儀表板、**實驗組**＝幽默日記。
- **DoD：** 真實感測一次喚醒能在數分鐘內反映成一篇新日記。

---

## 6. 關鍵介面合約 (Interface Contracts) — 單一真實來源

 ⚠️ 這是分工的命脈。改動任何一項都必須三層開發者一起同意並更新本節與 [contracts/telemetry.schema.json](contracts/telemetry.schema.json)。

### 6.1 L1 → L2：MQTT Telemetry
- **Topic：** `plants/{node_id}/telemetry`
- **建議 Payload（送原始值，校準交給 L2 — 對齊「Key Insight：校準屬於中介層」）：**
```json
{ "node": "plant_01", "ts": 1730000000,
  "moisture_raw": 2850, "light_raw": 1980,
  "temp_c": 28.5, "humidity_pct": 61.2 }
```
註：簡報 §8 範例曾以 `moisture: 32.5`（已換算）呈現，§9 則以 `moisture_raw 2850` 處理。**兩者擇一、全隊統一**。建議用 raw（土壤/光照走 ADC 需校準），溫濕度因 BME280 為數位 I2C 可直接給物理量。

**MVP 模擬註記：** 現階段無 BME280／LDR，`temp_c`、`humidity_pct` 由模擬值填入（`light_raw` 可省略），schema 不變。為避免把模擬當實測，模擬封包請加上 `"sim": true`（schema 已允許此選填欄位）；BME280 到貨後移除模擬旗標即為實測，下游 L2/L3 不需改動。

### 6.2 L2 → L3：狀態包 (State Packet)
```json
{ "node": "plant_01", "ts": 1730000000,
  "state": "CRITICAL_DROUGHT",
  "stats": { "moisture_pct": 18.0, "moisture_diff_1h": -3.2,
             "temp_c": 28.5, "light_pct": 60 } }
```

### 6.3 狀態標籤 Enum 與觸發規則（取自簡報 §11，可擴充）
| 狀態 (state) | 觸發條件 (Pandas) |
|---|---|
| `CRITICAL_DROUGHT` | `moisture_pct < 20%` 且 1 小時差值 `< 0` |
| `HEAT_STRESS` | `temp_c > 30.0` |
| `WATERING_DETECTED` | `moisture_pct` 1 小時內急升 `> 30%` |
| `STABLE`（預設） | 不符合上述任一者 |
 可再擴充 `LOW_LIGHT`、`COLD_STRESS` 等；新增標籤必須同步更新 L3 的 persona/prompt。

### 6.4 L3 輸出：日記
```json
{ "node": "plant_01", "ts": 1730000000, "state": "CRITICAL_DROUGHT",
  "diary": "（第一人稱、幽默、≤120 字的中文日記）" }
```

---

## 7. 常用指令 (Common Commands)

 L2 與 L3 已實作（離線即可跑）；L1/呈現層為目標指令。Python 模組請用 `python -m`（內部用相對匯入，不可用檔案路徑直接跑）。

```bash
# L1 韌體（PlatformIO）
pio run -d firmware                 # 編譯
pio run -d firmware -t upload       # 燒錄
pio device monitor                  # 看序列埠輸出

# 基礎設施
mosquitto -v                        # 本機 MQTT broker

# L2 中介（離線，免 broker/硬體；用模擬 L1）
python -m middleware.simulate --summary              # 跑模擬資料看狀態變化
python middleware/tests/test_state.py                # 測試（免 pytest）
# L2 即時（需 broker + paho-mqtt）
python -m middleware.ingest --host localhost         # MQTT 訂閱→落地→狀態
python -m tools.mock_publisher --host localhost      # 模擬 L1 經 MQTT 發布

# L3 認知（離線預設 stub，免 API key）
python -m cognition.generator --state CRITICAL_DROUGHT   # 單一狀態日記
python -m cognition.generator --demo                     # 串接 L2，跑 L2→L3
python -m cognition.generator --demo --provider ollama   # 換真實 LLM（需設定）

# 呈現層（離線、零相依；先 seed 再啟動）
python -m app.seed --reset          # 產生模擬資料寫入 DB（telemetry + 日記）
python -m app.server                # 啟動網頁 http://127.0.0.1:8000（左儀表板／右日記）
```

---

## 8. 慣例 (Conventions)

- **文件語言：** 繁體中文（程式碼識別字用英文）。
- **狀態標籤：** 一律大寫 `SNAKE_CASE`，集中定義於 [contracts/](contracts/)，禁止各層各自硬寫字串。
- **時間：** 一律 Unix epoch 秒 (UTC)，呈現層才轉本地時間。
- **祕密金鑰：** LLM API key 等放 `.env`，**不可進版控**（加 `.gitignore`）。
- **單位：** `*_raw`＝ADC 原始值；`*_pct`＝百分比；`temp_c`＝攝氏。
- **提交訊息：** 標明所屬層，如 `[L2] 加入中位數濾波`。

---

## 9. 重要決策與陷阱 (Key Decisions & Gotchas)

- **校準位置：** 放在 L2，不要散落在韌體（韌體只送 raw），維持單一校準來源。
- **LLM 不碰數字：** 任何「>30%」「<20%」的判斷都在 L2（Pandas）完成，L3 只接標籤。
- **深度睡眠陷阱：** Wi-Fi 重連（DHCP/關聯）是耗電與耗時大宗；省電成敗在這裡，別只看睡眠電流。
- **ESP32 ADC 非線性：** GPIO32/33 的 ADC 有已知非線性與雜訊，校準與中位數濾波缺一不可。
- **幻覺防治：** prompt 必須明令「只能根據提供的狀態與數據描述，不得虛構事件」。
- **成本：** 每日多次呼叫 LLM 會累積 API 成本；建議只在**狀態變化**時生成、用小模型（gpt-4o-mini / gemini-flash）或本機 Ollama（詳見 FEASIBILITY）。
- **模擬資料要可切換、要標記：** MVP 期間溫濕度為模擬值。務必用編譯旗標／設定檔一鍵切換「真實 ↔ 模擬」，封包以 `sim` 欄位標記；demo 與報告也要誠實標示哪些是模擬，切勿把模擬數據當實測結果呈現。
