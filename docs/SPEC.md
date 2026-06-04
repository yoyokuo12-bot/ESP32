# 規格書 (System Specification) — 擬人化盆栽幽默日記系統

本規格書供**分工**使用。每位（組）開發者只需確保自己模組的**輸入/輸出符合 §2 介面合約**，即可獨立開發、平行進行。
上層脈絡見 [../CLAUDE.md](../CLAUDE.md)；可行性與風險見 [FEASIBILITY.md](FEASIBILITY.md)。

文件版本：v0.3（2026-06，鎖定 MVP 與 BME280；溫濕度暫以模擬替代；**移除功耗與 HCI 實驗，聚焦 app 呈現**）　目標展示：下週二

---

## 1. 範圍與目標 (Scope & Goals)

| 項目 | 內容 |
|---|---|
| 目標產物 | 一套可運作的端到端 demo：真實盆栽 → 感測 → 雲端 → LLM → 幽默日記畫面 |
| 必達 (MVP) | 單盆、單一感測器（至少土壤濕度）、一條 telemetry→標籤→日記管線、能展示一篇真實生成的日記 |
| 完整目標 | 三感測器（土壤＋BME280＋光照）、雙畫面呈現（儀表板 vs 日記）端到端自動更新 |
| 加分 | 多盆栽、不同人格、數據趨勢圖 |
| 不在範圍 | 自動澆水/致動器（本專題刻意保留 Human-in-the-loop） |

**已定案（2026-06）：** ① 目前範圍＝MVP，實體感測**僅土壤濕度（GPIO34）**。② 溫濕度感測器選定 **BME280**。
**硬體缺料對策：** 完整專題需要溫濕度資料，但 BME280 目前不易取得，故**暫以模擬資料替代**（韌體填模擬值，或用 `tools/mock_publisher.py` 產生整包模擬 telemetry）。介面與 schema 不變，到貨後換實測即可，L2/L3 無須改動；模擬封包以 `sim:true` 標記（見 §2.1）。

---

## 2. 介面合約（凍結項）

與 [../CLAUDE.md §6](../CLAUDE.md) 一致；此為**契約測試**的依據，任一方修改須全員同意。

### 2.1 L1 → L2 Telemetry（MQTT）
- Topic：`plants/{node_id}/telemetry`、QoS 1（注意：ESP32 端 PubSubClient 只支援 QoS 0 發布；broker 與 L2 訂閱用 QoS 1）
- Schema（`contracts/telemetry.schema.json`）：

| 欄位 | 型別 | 單位/說明 |
|---|---|---|
| `node` | string | 節點 ID，如 `plant_01` |
| `ts` | int | Unix epoch 秒 (UTC) |
| `moisture_raw` | int | 土壤 ADC 原始值（0–4095） |
| `light_raw` | int | 光照 ADC 原始值（0–4095） |
| `temp_c` | float | 攝氏（BME280 數位輸出；**MVP 期間為模擬值**） |
| `humidity_pct` | float | 相對濕度 %（BME280；**MVP 期間為模擬值**） |
| `sim` | bool（選填） | `true`＝此封包含模擬資料；正式實測時省略或設 false |

### 2.2 L2 → L3 State Packet（函式/訊息）
| 欄位 | 型別 | 說明 |
|---|---|---|
| `node` / `ts` | — | 同上 |
| `state` | enum | 見 §2.3 |
| `stats.moisture_pct` | float | 校準後濕度 % |
| `stats.moisture_diff_1h` | float | 近 1 小時變化量 |
| `stats.temp_c` / `light_pct` | float | 摘要值 |

### 2.3 狀態標籤 Enum（觸發規則）
| state | 條件 | 來源 |
|---|---|---|
| `CRITICAL_DROUGHT` | `moisture_pct < 20` 且 `moisture_diff_1h < 0` | 簡報 §11 |
| `HEAT_STRESS` | `temp_c > 30.0` | 簡報 §11 |
| `WATERING_DETECTED` | `moisture_pct` 1h 內升幅 `> 30` | 簡報 §11 |
| `STABLE` | 其餘 | 預設 |
| `LOW_LIGHT`（選做） | `light_pct < 15` 持續 N 筆 | 擴充 |

### 2.4 L3 → 呈現 Diary
| 欄位 | 型別 | 說明 |
|---|---|---|
| `node`/`ts`/`state` | — | 溯源 |
| `diary` | string | 第一人稱中文日記，≤120 字 |

---

## 3. 硬體規格 (Hardware BOM) — 取自簡報 §7

| 元件 | 型號 | 備註 |
|---|---|---|
| 微控制器 | ESP32-WROOM-32 | 內建 Wi-Fi、ADC、深度睡眠 |
| 土壤濕度 | 電容式土壤濕度感測器 v2.0 | 抗腐蝕；類比輸出 |
| 溫濕度 | **BME280**（已選定） | I2C 數位；**目前缺料，暫以模擬資料替代**，到貨後接 GPIO21/22 |
| 光照 | LDR + 分壓電路 | 類比輸出 |
| 電源 | **USB 供電**（開發 / 展示 / 部署皆可） | 本專題不做功耗實驗，USB 即可；如需可攜再自行加電池模組 |

**現階段採購（MVP）：** 只需「電容式土壤濕度感測器 v2.0 + 麵包板 + 杜邦線 + USB 線」。BME280、LDR 待 MVP 跑通＋到貨再購。

**Pin Mapping（凍結）：**

| GPIO | 介面 | 接到 |
|---|---|---|
| GPIO 34 | ADC1（input-only） | 土壤濕度 |
| GPIO 35 | ADC1（input-only） | 光照（KY-018） |
| GPIO 21 / 22 | I2C (SDA/SCL) | BME280 |

 MVP 只使用 **GPIO 34（土壤濕度）**；GPIO35（光照）與 GPIO21/22（BME280）待擴充時啟用。GPIO34/35 為 input-only ADC1，與 Wi-Fi 不衝突。

---

## 4. 模組規格與分工 (Modules & Roles)

角色可依實際人數合併。建議 **4 人各認領 A–D 一角**；2–3 人時 A+B 或 C+D 合併。

### 角色 A — 韌體 / 邊緣感測 (`firmware/`)
- **負責：** ESP32 感測、濾波、MQTT 上傳、（擴充）深度睡眠。
- **MVP 需求（現階段）：**
  - F-A1：讀取 **GPIO34 土壤濕度**；10 次取樣取**中位數**。
  - F-A2：`temp_c`/`humidity_pct` 以**模擬值**填入（合理區間隨機/正弦變化），封包加 `sim:true`，維持 §2.1 schema 完整。
  - F-A3：依 §2.1 打包 JSON、經 MQTT publish（QoS 1）；定時迴圈上傳（**MVP 先不睡眠**，always-on 較好除錯）。
  - F-A4：以**編譯旗標／設定檔**一鍵切換「真實 ↔ 模擬」感測來源，方便 BME280 到貨後無痛換真值。
- **擴充需求（硬體到貨後）：**
  - F-A5：接 BME280（I2C，GPIO21/22）與光照感測（GPIO35），對應欄位由模擬改實測、移除 `sim` 旗標。
  - F-A6：上傳後 `esp_deep_sleep_start()`，RTC 每 **4 小時**喚醒、Active 3–5 秒；Wi-Fi 連線逾時與重試上限。
- **驗收（MVP）：** 實機定時上傳合規 JSON（moisture 實測、溫濕度 `sim:true`），L2 能正常解析。
- **驗收（完整）：** 三感測皆實測、定時上傳。
- **交付：** `firmware/src/main.cpp`、`platformio.ini`、接線圖；（缺料期可選）`tools/mock_publisher.py` 由 A 或 B 維護。

### 角色 B — 中介 / 數據工程 (`middleware/`)
- **負責：** 訂閱、落地、清洗、校準、特徵工程、狀態判斷。
- **需求：**
  - F-B1：`ingest.py` 訂閱 `plants/+/telemetry`，落地時序資料（SQLite/CSV）。
  - F-B2：`pipeline.py` 以 `calibration.json` 把 `moisture_raw`/`light_raw` 換算成 `*_pct`；再次中位數/移動平均去殘餘突波。
  - F-B3：`state.py` 依 §2.3 規則輸出 `state` + `stats`。
  - F-B4：對人為/電磁突波過濾（目標濾除率 100%，對齊簡報結果）。
- **驗收：** 給定一段含突波的歷史資料，輸出標籤與簡報描述一致；契約測試通過 §2.2。
- **交付：** `ingest.py`、`pipeline.py`、`state.py`、`calibration.json`、測試資料。

### 角色 C — AI / 提示工程 (`cognition/`)
- **負責：** 人格設計、Prompt 工程、LLM 串接、日記生成。
- **需求（取自簡報 §10）：**
  - F-C1 系統人格：強制第一人稱、預設性格（如「帶點黑色幽默的傲嬌」或「適度怠惰的文青」）。
  - F-C2 情境注入：把 L2 的 `state` + `stats` 餵入 prompt。
  - F-C3 生成約束：字數上限；禁止「我是一個 AI 語言模型…」；**不得虛構未提供的數據/事件**。
  - F-C4：每個 `state` 至少各有 1 組對應語氣範例（few-shot）。
- **驗收：** 對四種以上 `state` 各生成 5 篇，人工檢視語氣一致、無幻覺、符合字數；契約測試通過 §2.4。
- **交付：** `prompts/persona.md`、`generator.py`、`llm_client.py`、生成樣本集。

### 角色 D — 呈現 / 整合 / UX (`app/`)
- **負責：** 端到端串接、雙模式畫面、demo。
- **需求：**
  - F-D1：把 L1→L2→L3 串成自動管線（新 telemetry 進來→產生新日記）。
  - F-D2：傳統數據儀表板（冷數據呈現，簡報 §3 樣式）。
  - F-D3：幽默日記時間軸（擬人化呈現）。
  - F-D4：兩種畫面並列，凸顯「冷數據 vs 擬人化」對比。
- **驗收：** 一次真實喚醒，數分鐘內可見對應的新日記；兩種畫面皆可展示。
- **交付：** `app/server.py`、前端頁面、demo 腳本。

---

## 5. 非功能需求 (NFR)

| 編號 | 需求 | 量化目標 |
|---|---|---|
| NFR-1 數據穩定 | 突波濾除 | 中位數濾波 + 校準，對人為/電磁突波濾除率達標 |
| NFR-2 延遲 | 感測 → 日記 | < 數分鐘 |
| NFR-3 內容品質 | 幻覺率 | 抽樣人工檢視，捏造數據/事件 = 0 |
| NFR-4 成本 | LLM API | 限頻生成（只在狀態變化）＋估算每月呼叫量與上限 |

---

## 6. 里程碑與時程 (Milestones)

| 週 | 里程碑 | 主責 |
|---|---|---|
| W0 | P0 環境 + 凍結合約；假 publisher/subscriber 打通 | 全員 |
| W1 | P1 韌體上傳資料（MVP：moisture 實測＋溫濕度模擬）；P2 落地+清洗 | A、B |
| W2 | P2 狀態標籤完成；P3 日記生成可單測 | B、C |
| W3 | P4 端到端整合 + 雙畫面 demo | D（A/B/C 支援） |

 **下週二展示建議切到 MVP：** 單盆 + 土壤濕度一感測 + 一條管線 + 一篇真實日記，其餘以模擬資料或預錄補足。

---

## 7. 風險與相依 (Dependencies)
- L2 阻塞 L3、L4：合約一凍結，C/D 可先用**假狀態包**平行開發，不必等 A 的硬體到位。
- LLM 供應商與金鑰需 W0 前確認（影響 C）。
- 硬體採購到貨時間影響 A；**對策：MVP 僅需土壤濕度感測器，溫濕度以模擬資料替代**，故 BME280 缺料不阻塞全鏈開發（風險見 [FEASIBILITY.md](FEASIBILITY.md)）。

---

## 8. 驗收總表 (Definition of Done)
- [ ] 介面合約 §2 全部凍結並有 `contracts/telemetry.schema.json`。
- [ ] A（MVP）：實機定時上傳合規 JSON（moisture 實測、溫濕度 `sim:true`）。
- [ ] A（完整）：三感測實測、定時上傳。
- [ ] B：歷史資料 → 正確標籤、突波濾除達標、契約測試綠燈。
- [ ] C：各 state 生成語氣一致、零幻覺、符合字數。
- [ ] D：端到端真實 demo、雙畫面可切換。
