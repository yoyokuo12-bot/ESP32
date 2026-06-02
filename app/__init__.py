"""呈現層 / 整合 (App)。

seed.py 把模擬資料（telemetry + 生成的日記）寫入 SQLite；
server.py 是零相依網頁，只從 DB 讀取並呈現「對照組儀表板 vs 實驗組日記」。
"""
