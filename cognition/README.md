# L3 認知生成層 (Cognition) — ✅ 已實作（預設離線可跑）

把 L2 的 state packet → 提示工程 → LLM → 第一人稱幽默日記。
規格見 [../docs/SPEC.md](../docs/SPEC.md) §4「角色 C」、[../CLAUDE.md](../CLAUDE.md) §6.4。

## 立即可跑（不需 API key）
預設供應商是 `stub`（離線、用模板 + 真實 stats 生成）：

```bash
# 單一狀態（合成資料，輸出 JSON）
python -m cognition.generator --state CRITICAL_DROUGHT

# 串接 L2 模擬，跑完整 L2→L3（每次狀態變化生成一篇日記）
python -m cognition.generator --demo
```

## 換成真實 LLM
OpenAI / Ollama / **Gemini** 都走同一個 OpenAI 相容介面，只需 `pip install openai`：

```bash
pip install openai

# Gemini（推薦；用 Gemini API key，base_url 由程式自動帶入）
$env:LLM_PROVIDER="gemini"; $env:LLM_API_KEY="<你的 Gemini API key>"
python -m cognition.generator --demo --provider gemini
#   預設模型 gemini-2.0-flash，可用 $env:LLM_MODEL 覆寫（如 gemini-2.5-flash / gemini-1.5-pro）

# OpenAI
$env:LLM_PROVIDER="openai"; $env:LLM_API_KEY="sk-..."; $env:LLM_MODEL="gpt-4o-mini"
python -m cognition.generator --demo --provider openai

# 本機 Ollama（免費、免金鑰）
$env:LLM_PROVIDER="ollama"; $env:LLM_BASE_URL="http://localhost:11434/v1"; $env:LLM_MODEL="llama3.1"
python -m cognition.generator --demo --provider ollama
```

 **Gemini API key 與 OpenAICompatibleClient 相容**：Google 提供 OpenAI 相容端點
 （`https://generativelanguage.googleapis.com/v1beta/openai/`），所以沿用同一個 client 即可。
 金鑰也可放 `GEMINI_API_KEY` 或 `GOOGLE_API_KEY` 環境變數。

## 模組
| 檔案 | 職責 |
|---|---|
| `prompts/persona.md` | 系統人格 + 寫作規則（可直接編輯調語氣） |
| `examples.py` | `FEW_SHOT`（真實 LLM 示範）、`STUB_TEMPLATES`（離線模板） |
| `llm_client.py` | `StubLLMClient` / `OpenAICompatibleClient` / `get_client()` |
| `generator.py` | `generate_diary()`：組 prompt → 呼叫 LLM → 後處理（去違規字、限字數） |
| `config.py` | 供應商、模型、金鑰、字數上限（皆吃環境變數） |

## 介面合約
- 輸入：[../contracts/state_packet.schema.json](../contracts/state_packet.schema.json)（L2 產出）
- 輸出：`{ "node", "ts", "state", "diary" }`，日記 ≤ 120 字、第一人稱、無幻覺、不自曝 AI 身分。

## 測試
```bash
python cognition/tests/test_generator.py     # 免 pytest
pytest cognition/tests
```
