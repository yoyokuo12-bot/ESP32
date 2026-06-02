"""呈現層：零相依網頁，並列「傳統儀表板（對照組）」與「植物幽默日記（實驗組）」。

只從 DB 讀取（先跑 python -m app.seed 產生資料）。不需安裝任何套件。

用法：
    python -m app.seed         # 先產生資料
    python -m app.server       # 再啟動，瀏覽 http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from middleware import config as mw
from middleware import store
from middleware.pipeline import compute_stats, load_calibration
from middleware.state import build_state_packet

_CALIB: dict | None = None

PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>擬人化盆栽 · 對照組 vs 實驗組</title>
<style>
  :root { --bg:#0f1410; --card:#19201a; --ink:#e8f0e6; --muted:#8aa088; --line:#2a352a; --accent:#7fc77f; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:"Segoe UI","PingFang TC","Microsoft JhengHei",sans-serif; background:var(--bg); color:var(--ink); }
  header { padding:18px 24px; border-bottom:1px solid var(--line); }
  header h1 { margin:0; font-size:18px; }
  header .sub { color:var(--muted); font-size:13px; margin-top:4px; }
  .wrap { display:grid; grid-template-columns:1fr 1fr; gap:18px; padding:18px 24px; max-width:1100px; margin:0 auto; }
  @media (max-width:760px){ .wrap { grid-template-columns:1fr; } }
  .card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; }
  .card h2 { margin:0 0 14px; font-size:15px; }
  .tag { font-size:12px; color:var(--muted); font-weight:400; }
  .metrics { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .metric { background:#11160f; border:1px solid var(--line); border-radius:10px; padding:14px; }
  .metric .label { color:var(--muted); font-size:12px; }
  .metric .value { font-size:30px; font-weight:700; margin-top:6px; font-variant-numeric:tabular-nums; }
  .metric .unit { font-size:14px; color:var(--muted); font-weight:400; }
  .statusline { margin-top:14px; font-size:13px; color:var(--muted); }
  .diary { display:flex; flex-direction:column; gap:14px; max-height:72vh; overflow:auto; }
  .entry { background:#11160f; border:1px solid var(--line); border-left:4px solid var(--accent); border-radius:10px; padding:12px 14px; }
  .entry .meta { display:flex; align-items:center; gap:8px; font-size:12px; color:var(--muted); margin-bottom:6px; }
  .badge { font-size:11px; padding:2px 8px; border-radius:999px; color:#0f1410; font-weight:700; }
  .entry p { margin:0; line-height:1.75; }
  .empty { color:var(--muted); font-size:14px; }
</style>
</head>
<body>
<header>
  <h1>🪴 擬人化盆栽物聯網 · 即時展示</h1>
  <div class="sub">同一份感測數據，兩種呈現 —— 左：傳統儀表板（對照組）／右：第一人稱幽默日記（實驗組）</div>
</header>
<div class="wrap">
  <section class="card">
    <h2>📊 傳統儀表板 <span class="tag">對照組 · Dashboard</span></h2>
    <div class="metrics" id="metrics"><div class="empty">載入中…</div></div>
    <div class="statusline" id="statusline"></div>
  </section>
  <section class="card">
    <h2>📔 植物的日記 <span class="tag">實驗組 · Diary</span></h2>
    <div class="diary" id="diary"><div class="empty">載入中…</div></div>
  </section>
</div>
<script>
const BADGE = {
  CRITICAL_DROUGHT:["缺水危急","#ff6b6b"], HEAT_STRESS:["高溫","#ffa94d"],
  WATERING_DETECTED:["剛澆水","#4dabf7"], LOW_LIGHT:["光照不足","#b197fc"],
  STABLE:["穩定","#7fc77f"],
};
function fmt(ts){ return new Date(ts*1000).toLocaleString('zh-TW',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}); }
function num(v){ return (v===null||v===undefined) ? '–' : v; }
async function tick(){
  try {
    const s = await (await fetch('/api/state')).json();
    const m = document.getElementById('metrics');
    if (s.empty) {
      m.innerHTML = '<div class="empty">尚無資料，請先執行：python -m app.seed</div>';
      document.getElementById('statusline').textContent = '';
    } else {
      const st = s.stats;
      m.innerHTML =
        '<div class="metric"><div class="label">土壤濕度</div><div class="value">'+num(st.moisture_pct)+'<span class="unit">%</span></div></div>'+
        '<div class="metric"><div class="label">溫度</div><div class="value">'+num(st.temp_c)+'<span class="unit">°C</span></div></div>'+
        '<div class="metric"><div class="label">空氣濕度</div><div class="value">'+num(st.humidity_pct)+'<span class="unit">%</span></div></div>'+
        '<div class="metric"><div class="label">光照</div><div class="value">'+num(st.light_pct)+'<span class="unit">%</span></div></div>';
      const b = BADGE[s.state] || [s.state,'#7fc77f'];
      document.getElementById('statusline').innerHTML =
        '目前狀態：<b style="color:'+b[1]+'">'+b[0]+'</b> · 節點 '+s.node+' · '+fmt(s.ts);
    }
    const ds = await (await fetch('/api/diaries')).json();
    const d = document.getElementById('diary');
    if (!ds.length) {
      d.innerHTML = '<div class="empty">尚無日記，請先執行：python -m app.seed</div>';
    } else {
      d.innerHTML = ds.map(function(e){
        const b = BADGE[e.state] || [e.state,'#7fc77f'];
        return '<div class="entry" style="border-left-color:'+b[1]+'">'+
          '<div class="meta"><span class="badge" style="background:'+b[1]+'">'+b[0]+'</span><span>'+fmt(e.ts)+'</span></div>'+
          '<p>'+e.diary+'</p></div>';
      }).join('');
    }
  } catch (err) { /* 靜默重試 */ }
}
tick(); setInterval(tick, 5000);
</script>
</body>
</html>
"""


def _state_payload(node: str | None = None) -> dict:
    conn = store.connect(mw.DB_PATH)
    try:
        ns = store.nodes(conn)
        node = node or (ns[0] if ns else None)
        if not node:
            return {"empty": True}
        recs = store.recent_by_count(conn, node, 60)
        if not recs:
            return {"empty": True}
        stats = compute_stats(recs, _CALIB, diff_window_sec=mw.DIFF_WINDOW_SEC,
                              smooth_samples=mw.SMOOTH_SAMPLES)
        pkt = build_state_packet(node, recs[-1]["ts"], stats)
        return {"node": node, "ts": pkt["ts"], "state": pkt["state"], "stats": stats}
    finally:
        conn.close()


def _diaries_payload(node: str | None = None, limit: int = 50) -> list[dict]:
    conn = store.connect(mw.DB_PATH)
    try:
        return store.recent_diaries(conn, node=node, limit=limit)
    finally:
        conn.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 靜音
        pass

    def _send(self, code: int, ctype: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj) -> None:
        self._send(200, "application/json; charset=utf-8",
                   json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        u = urlparse(self.path)
        node = (parse_qs(u.query).get("node") or [None])[0]
        if u.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", PAGE.encode("utf-8"))
        elif u.path == "/api/state":
            self._json(_state_payload(node))
        elif u.path == "/api/diaries":
            self._json(_diaries_payload(node))
        else:
            self._send(404, "text/plain; charset=utf-8", b"not found")


def main() -> None:
    global _CALIB
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="呈現層：傳統儀表板 vs 植物日記")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-open", action="store_true", help="啟動時不要自動開啟瀏覽器")
    args = ap.parse_args()

    _CALIB = load_calibration(mw.CALIBRATION_PATH)
    try:
        srv = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as e:
        raise SystemExit(f"無法在 {args.host}:{args.port} 啟動（{e}）。"
                         f"埠號可能被占用，改用 --port 8001 再試。")

    host_for_url = "127.0.0.1" if args.host in ("0.0.0.0", "") else args.host
    url = f"http://{host_for_url}:{args.port}"
    print(f"呈現層啟動 → {url}")
    print("瀏覽器不會自動「跳出」是正常的；此終端會持續執行（Ctrl-C 結束）。")
    print("若沒自動開啟，請手動在瀏覽器貼上上面的網址。")
    print("（畫面空白＝尚無資料：在另一個終端執行 python -m app.seed --reset）")
    if not args.no_open:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
