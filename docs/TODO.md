# 專案待辦清單 (Project TODO)

擬人化盆栽幽默日記系統。對照 [../CLAUDE.md](../CLAUDE.md) §5 開發流程、[SPEC.md](SPEC.md) 分工、[../DATAFLOW.md](../DATAFLOW.md) 實作細節。
最後更新：2026-06。

**圖例：** `- [x]` 已完成 ／ `- [ ]` 待辦 ／ 🔒 待硬體到貨 ／ ⭐ 加分項

---

## 進度總覽

| 層 / 階段 | 狀態 | 備註 |
|---|---|---|
| 文件與介面合約 | ✅ 完成 | 4 份文件 + 2 份 schema |
| P0 環境與骨架 | 🟡 部分 | 程式骨架完成；Mosquitto/paho-mqtt 未裝 |
| P1 L1 邊緣感測（韌體） | 🔒 待硬體 | 目前以模擬資料替代 |
| P2 L2 中介處理 | ✅ 完成 | 含單元測試；待硬體後填真實校準值 |
| P3 L3 認知生成 | ✅ 完成 | stub / Gemini / OpenAI 皆驗證可用 |
| P4 呈現層 / 整合 | ✅ MVP 完成 | 端到端跑通、網頁可展示 |

---

## 文件與介面合約
- [x] CLAUDE.md（專題總覽、架構、流程、合約）
- [x] docs/SPEC.md（規格書、分工、驗收標準）
- [x] docs/FEASIBILITY.md（可行性與難點）
- [x] DATAFLOW.md（實作資料流、函數相依、演算法）
- [x] contracts/telemetry.schema.json（L1→L2 合約）
- [x] contracts/state_packet.schema.json（L2→L3 合約）
- [x] 各模組 README（middleware / cognition / app / tools / firmware）
- [x] docs/TODO.md（本清單）

## P0 — 環境與骨架（全員）
- [x] 儲存庫目錄骨架（firmware / middleware / cognition / app / tools / contracts / common）
- [x] 凍結介面合約（telemetry / state packet / 狀態 enum 與閾值）
- [x] `.env` 自動載入（common/env.py）+ `.env.example`、`.gitignore`、`requirements.txt`
- [x] 假 publisher→subscriber 打通（以離線 `simulate` 等效驗證）
- [ ] 安裝本機 MQTT broker（Mosquitto）並實際連線
- [ ] `pip install paho-mqtt`（即時路徑才需要）
- [ ] kickoff 拍板：LLM 供應商 / 韌體框架 / 時序資料庫（見 CLAUDE.md §3）

## P1 — L1 邊緣感測層（角色 A）🔒 待硬體
 目前由 [middleware/mocksource.py](../middleware/mocksource.py)、[tools/mock_publisher.py](../tools/mock_publisher.py) 模擬替代。
- [x] 模擬資料來源（mocksource：乾旱→澆水→熱浪劇本，標 `sim:true`）
- [x] 模擬 MQTT 發布器（tools/mock_publisher.py）
- [ ] 🔒 接線土壤濕度感測器（GPIO32）並讀值
- [ ] 🔒 韌體 10 次取樣取中位數
- [ ] 🔒 `temp_c`/`humidity_pct` 先填模擬值、封包加 `sim:true`
- [ ] 🔒 Wi-Fi 連線 → 打包 JSON → MQTT publish（`plants/{node}/telemetry`）
- [ ] 🔒 編譯旗標一鍵切換「真實 ↔ 模擬」感測來源
- [ ] 🔒 接 BME280（I2C GPIO21/22）與 LDR（GPIO33），移除對應模擬值
- [ ] ⭐ 深度睡眠（選用；省電功能，本專題不做功耗實驗）
- [ ] 🔒 DoD：實機定時上傳合規 JSON

## P2 — L2 中介處理層（角色 B）
- [x] config.py（視窗、路徑、MQTT、.env）
- [x] calibration.json（兩點校準，預設值）
- [x] pipeline.py：ADC→% 校準、中位數濾波、`compute_stats`（特徵工程）
- [x] state.py：`classify` 狀態分類（優先序 + 閾值）+ `build_state_packet`
- [x] store.py：SQLite 落地與查詢（telemetry + diaries 表）
- [x] simulate.py：離線驅動（`iter_packets`）
- [x] ingest.py：MQTT 即時驅動（paho 延遲載入）
- [x] 單元測試 test_pipeline / test_state（14 項全過）
- [ ] 用真實 MQTT broker 跑通 ingest + mock_publisher（待 P0 裝 broker）
- [ ] 🔒 硬體到貨後量測，填入真實 `raw_dry` / `raw_wet` 校準值
- [ ] 以真實資料微調 `state.THRESHOLDS` 門檻
- [ ] ⭐ 用 jsonschema 對封包做契約測試（schema 已備）

## P3 — L3 認知生成層（角色 C）
- [x] prompts/persona.md（第一人稱、傲嬌幽默、禁止自曝 AI/虛構、≤120 字）
- [x] examples.py（FEW_SHOT 範例 + STUB_TEMPLATES 離線模板）
- [x] llm_client.py：StubLLMClient + OpenAICompatibleClient + `get_client`
- [x] 供應商：stub（離線）/ OpenAI / Ollama / Gemini（OpenAI 相容端點）
- [x] generator.py：`generate_diary` + `postprocess`（去違規字、限字數、句尾截斷）
- [x] 錯誤處理：429/401/連線失敗對症提示、自動重試、`--usage` token 顯示
- [x] 單元測試 test_generator（5 項全過）
- [x] 實測三供應商：stub ✓、Gemini 2.5-flash ✓、OpenAI gpt-4o-mini ✓
- [ ] 以真實互動微調人格語氣與 few-shot
- [ ] ⭐ 多種人格（傲嬌 / 文青 / 厭世…）可切換

## P4 — 呈現層 / 整合（角色 D）
- [x] app/seed.py：模擬→落 DB（telemetry + 生成日記）
- [x] app/server.py：零相依網頁 + `/api/state`、`/api/diaries`
- [x] 雙畫面：對照組（傳統儀表板）vs 實驗組（幽默日記時間軸）
- [x] 端到端驗證（seed 240 筆 + 11 篇日記、首頁 HTTP 200）
- [x] 啟動自動開瀏覽器、埠號被占用友善提示
- [ ] ⭐ 多盆栽 node 切換選單
- [ ] ⭐ 數據趨勢圖（濕度/溫度時間軸折線）

---

## 硬體採購

**供電：** 一律 **USB 供電**即可（本專題不做功耗實驗，不需電池 / INA219）。

**MVP（現在就要）**
- [ ] 電容式土壤濕度感測器 v2.0（抗腐蝕）
- [ ] 麵包板 + 杜邦線（公對母）
- [ ] USB 傳輸線（供電 + 燒錄）
- [x] ESP32-WROOM-32（已有）

**完整功能 — 感測（之後）**
- [ ] BME280（I2C 溫濕度，已選定）
- [ ] LDR + 10kΩ 電阻（光照分壓）

---

## 下週二展示準備
- [x] 可離線展示的完整管線（stub，免金鑰）
- [x] 真實 LLM 可選展示（Gemini / OpenAI）
- [ ] 決定展示用哪個供應商（stub 最穩 / 真實 LLM 較驚艷）
- [ ] 先跑 `python -m app.seed --reset` 準備好資料
- [ ] 演練展示腳本（讓土壤「變乾→喊渴」對比儀表板）
- [ ] 投影：架構圖 + DATAFLOW 重點 + 難點（FEASIBILITY）
- [ ] 備援：預錄畫面或截圖（萬一現場網路/額度出問題）
