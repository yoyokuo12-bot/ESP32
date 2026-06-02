# 呈現層 / 整合 (App) — ✅ 已實作（零相依、離線可跑）

並列呈現「**傳統儀表板（對照組）**」與「**植物幽默日記（實驗組）**」—— 正是簡報 HCI 實驗要對比的兩個畫面。
規格見 [../docs/SPEC.md](../docs/SPEC.md) §4「角色 D」。

## 兩步驟啟動

```bash
# 1) 產生模擬資料寫入 DB（telemetry + 生成的日記）。預設 stub，免金鑰。
python -m app.seed --reset
#    用真實 LLM 生成並存檔（之後網頁只讀 DB，不會再重複呼叫）：
#    python -m app.seed --reset --provider gemini --sleep 5

# 2) 啟動網頁
python -m app.server
#    瀏覽 http://127.0.0.1:8000
```

## 為什麼要先 seed 進 DB？
- **日記只生成一次、存進 DB**：網頁每次刷新只讀 DB，不會重新呼叫 LLM → 不燒額度、不撞 429。
- 日記本身就是「時間軸記錄」，持久化最自然。
- 把「生成（seed，可能用 LLM）」與「呈現（server，純讀取）」解耦，貼近真實架構（L1→L2→L3 產資料、app 只顯示）。
- 用的是既有的 SQLite（[../middleware/store.py](../middleware/store.py) 的 `diaries` 表），零設定。

純管線單元測試（`python -m middleware.simulate`）仍是記憶體內、不落 DB —— 那種不需要 DB。

## 端點
| 路徑 | 內容 |
|---|---|
| `/` | 雙欄網頁（左儀表板、右日記），每 5 秒自動刷新 |
| `/api/state` | 最新 telemetry 計算出的 stats 與狀態（給儀表板） |
| `/api/diaries` | 最近的日記列表（給時間軸） |

## 檔案
| 檔案 | 職責 |
|---|---|
| `seed.py` | 模擬 telemetry → 算狀態 → 生成日記，全部寫入 SQLite |
| `server.py` | 零相依（Python 內建 `http.server`）網頁 + 兩個 JSON API，只讀 DB |
