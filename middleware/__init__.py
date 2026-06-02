"""L2 中介處理層 (Middleware Processing Layer)。

職責：訂閱 L1 telemetry → 清洗/校準 → 特徵工程 → 輸出狀態標籤 (state packet) 給 L3。
核心邏輯（pipeline、state）為純函式，可離線單元測試；MQTT 相關模組才需 broker。
"""
