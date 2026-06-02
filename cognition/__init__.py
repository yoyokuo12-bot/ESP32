"""L3 認知生成層 (Cognitive Generation Layer)。

輸入 L2 的 state packet（state + stats）→ 提示工程 → LLM → 第一人稱幽默日記。
預設使用 StubLLMClient（離線、免 API key），可切換為 OpenAI 相容供應商。
"""
