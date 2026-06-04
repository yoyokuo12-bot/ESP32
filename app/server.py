"""呈現層：零相依後端 + 真實翻書日記（前端用 vendored StPageFlip，離線可跑）。

左：傳統儀表板（對照組）；右：可單頁拖曳翻動的手寫日記本（實驗組）。
每篇日記 = 一頁日誌（日期 + 印章 + 手寫日記 + 當日數據邊註）。
StPageFlip 函式庫已下載到 app/vendor/，由本服務在 /vendor/ 提供，不需連外。

用法：
    python -m app.seed         # 先產生資料
    python -m app.server       # 再啟動，瀏覽 http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from middleware import config as mw
from middleware import store
from middleware.pipeline import compute_stats, load_calibration
from middleware.state import build_state_packet

_CALIB: dict | None = None
_VENDOR = Path(__file__).resolve().parent / "vendor"

PAGE = r"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>擬人化盆栽 · 對照組 vs 實驗組</title>
<style>
  * { box-sizing:border-box; }
  body { margin:0; min-height:100vh;
    font-family:"Segoe UI","PingFang TC","Microsoft JhengHei",sans-serif;
    background:#0d1411; color:#e8f0e6; }
  header { padding:16px 24px; border-bottom:1px solid #243024; }
  header h1 { margin:0; font-size:18px; }
  header .sub { color:#8aa088; font-size:13px; margin-top:4px; }

  .stage { display:grid; grid-template-columns:minmax(240px,.8fr) minmax(440px,1.4fr);
           gap:20px; padding:22px 24px; max-width:1280px; margin:0 auto; }
  @media (max-width:900px){ .stage { grid-template-columns:1fr; } }
  .panel-h { font-size:14px; margin:0 0 14px; font-weight:700; }
  .panel-h span { font-size:12px; font-weight:400; }

  /* 左：冷數據儀表板 */
  .dash { background:#11171d; border:1px solid #20303c; border-radius:14px; padding:20px; height:fit-content; }
  .dash .panel-h span { color:#6f8aa0; }
  .metrics { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  .metric { background:#0c1116; border:1px solid #1c2a34; border-radius:10px; padding:14px; }
  .metric .label { color:#6f8aa0; font-size:12px; letter-spacing:1px; }
  .metric .value { font-size:30px; font-weight:700; margin-top:6px;
                   font-family:"Consolas","SF Mono",monospace; font-variant-numeric:tabular-nums; }
  .metric .unit { font-size:14px; color:#6f8aa0; font-weight:400; }
  .statusline { margin-top:14px; font-size:13px; color:#8aa0b0; }
  .dash-note { margin-top:16px; font-size:12px; color:#566; border-top:1px dashed #20303c; padding-top:10px; }

  /* 右：日記本 */
  .diarywrap { background:radial-gradient(120% 120% at 50% 0%, #2a2016 0%, #1a140d 70%);
               border:1px solid #3a2e1c; border-radius:14px; padding:20px; }
  .diarywrap .panel-h { color:#f3e7cf; }
  .diarywrap .panel-h span { color:#b59b6e; }
  .book-stage { display:flex; justify-content:center; align-items:flex-start; padding:6px 0 4px; }
  .flipbook { margin:0 auto; }

  /* 每一頁（一篇日記）*/
  .page { background:#f7efdd; }
  .page .pg { width:100%; height:100%; padding:24px 26px; position:relative; overflow:hidden;
    color:#3b3324; background-image:repeating-linear-gradient(transparent 0 31px, rgba(120,100,60,.18) 31px 32px);
    background-position:0 86px; }
  .page .pg::before { content:""; position:absolute; top:0; bottom:0; left:18px; width:2px; background:rgba(200,90,80,.28); }
  .date { font-family:"KaiTi","DFKai-SB","BiauKai","STKaiti",cursive,serif;
          font-size:23px; font-weight:700; color:#5a4a2e; padding-left:14px; }
  .date .wd { display:block; font-size:13px; font-weight:400; color:#8a7550; margin-top:2px; }
  .diary-text { margin-top:16px; padding-left:14px;
    font-family:"KaiTi","DFKai-SB","BiauKai","STKaiti",cursive,serif;
    font-size:20px; line-height:32px; color:#3b3324; letter-spacing:.5px;
    white-space:pre-wrap; word-break:break-word; }
  .note { position:absolute; left:26px; right:26px; bottom:54px; font-size:13px; color:#7c6a45;
          font-family:"KaiTi","DFKai-SB",cursive,serif; border-top:1px dotted #cdbb90; padding-top:8px; }
  .sign { position:absolute; right:26px; bottom:22px; font-size:17px; color:#7a6747;
          font-family:"KaiTi","DFKai-SB",cursive,serif; }
  .seal { position:absolute; top:20px; right:22px; width:66px; height:66px; border-radius:50%;
          border:3px solid; display:flex; flex-direction:column; align-items:center; justify-content:center;
          transform:rotate(-9deg); opacity:.92; background:rgba(255,255,255,.4); box-shadow:0 2px 6px rgba(0,0,0,.18); }
  .seal-emoji { font-size:22px; line-height:1; }
  .seal-label { font-size:11px; font-weight:700; margin-top:2px; font-family:"KaiTi","DFKai-SB",cursive,serif; }
  .empty-paper { display:flex; flex-direction:column; align-items:center; justify-content:center;
                 height:100%; color:#8a7550; text-align:center; font-family:"KaiTi","DFKai-SB",cursive,serif; font-size:18px; }
  .empty-paper span { font-size:12px; color:#a89770; margin-top:10px; font-family:monospace; }

  /* 封面 / 封底（硬頁）*/
  .page-cover .pg { background:linear-gradient(135deg,#2f4a32,#23381f); color:#e9dcb8;
    background-image:none; display:flex; flex-direction:column; align-items:center; justify-content:center; }
  .page-cover .pg::before { display:none; }
  .cover-emoji { font-size:54px; }
  .cover-title { font-family:"KaiTi","DFKai-SB",cursive,serif; font-size:30px; font-weight:700; margin-top:10px; letter-spacing:4px; }
  .cover-sub { color:#bcae86; font-size:13px; margin-top:8px; }

  .controls { display:flex; align-items:center; justify-content:center; gap:14px; margin-top:14px; }
  .nav { width:42px; height:40px; border:none; border-radius:8px; cursor:pointer;
         background:rgba(0,0,0,.4); color:#f3e7cf; font-size:18px; transition:background .2s,opacity .2s; }
  .nav:hover { background:rgba(0,0,0,.6); }
  .pager { color:#b59b6e; font-size:13px; min-width:200px; text-align:center; }
  .pager b { color:#f3e7cf; }
  .fallback { color:#e9c46a; font-size:13px; text-align:center; padding:20px; }
</style>
</head>
<body>
<header>
  <h1>🪴 擬人化盆栽物聯網 · 即時展示</h1>
  <div class="sub">同一份感測數據，兩種呈現 —— 左：冷冰冰的儀表板／右：植物的手寫日記本（拖曳頁角可單頁翻動）</div>
</header>

<div class="stage">
  <section class="dash">
    <div class="panel-h">📊 數據儀表板 <span>對照組 · Dashboard</span></div>
    <div class="metrics" id="metrics"><div class="statusline">載入中…</div></div>
    <div class="statusline" id="statusline"></div>
    <div class="dash-note">⚠ 冷冰冰的數字，要你自己判讀植物的心情。</div>
  </section>

  <section class="diarywrap">
    <div class="panel-h">📖 植物的日記 <span>實驗組 · Diary（拖曳頁角翻頁）</span></div>
    <div class="book-stage"><div id="flipbook" class="flipbook"></div></div>
    <div class="controls">
      <button class="nav" id="prev" title="上一頁">◀</button>
      <div class="pager" id="pager">載入中…</div>
      <button class="nav" id="next" title="下一頁">▶</button>
    </div>
  </section>
</div>

<script src="/vendor/page-flip.browser.js"></script>
<script>
const DASH = {
  CRITICAL_DROUGHT:["缺水危急","#ff6b6b"], HEAT_STRESS:["高溫","#ffa94d"],
  WATERING_DETECTED:["剛澆水","#4dabf7"], LOW_LIGHT:["光照不足","#b197fc"], STABLE:["穩定","#7fc77f"],
};
const STATE = {
  CRITICAL_DROUGHT:{label:"快渴死", emoji:"🥵", color:"#c0392b"},
  HEAT_STRESS:    {label:"熱融化", emoji:"🔥", color:"#d4731f"},
  WATERING_DETECTED:{label:"喝到水", emoji:"💧", color:"#2e7fb8"},
  LOW_LIGHT:      {label:"好暗喔", emoji:"🌙", color:"#7a5fb0"},
  STABLE:         {label:"歲月靜好", emoji:"🌿", color:"#4f9a4f"},
};
const WD = ["日","一","二","三","四","五","六"];
const el = function(id){ return document.getElementById(id); };
function num(v){ return (v===null||v===undefined) ? "–" : v; }
function pad(n){ return String(n).padStart(2,"0"); }
function escapeHtml(s){ return (s||"").replace(/[&<>]/g, function(c){
  return {"&":"&amp;","<":"&lt;",">":"&gt;"}[c]; }); }

let diaries = [];
let pf = null;
let lastCount = -1;

function coverFront(){
  return '<div class="page page-cover" data-density="hard"><div class="pg">'
    + '<div class="cover-emoji">🌱</div><div class="cover-title">我的植物日記</div>'
    + '<div class="cover-sub">' + (diaries.length ? diaries.length + ' 篇 · 翻頁閱讀' : '') + '</div></div></div>';
}
function coverBack(){
  return '<div class="page page-cover" data-density="hard"><div class="pg">'
    + '<div class="cover-emoji">🌿</div><div class="cover-title">—— 完 ——</div></div></div>';
}
function entryPage(e){
  const st = e.stats || null;
  const s = STATE[e.state] || {label:e.state, emoji:"🌿", color:"#4f9a4f"};
  const d = new Date(e.ts * 1000);
  const dateStr = (d.getMonth()+1) + "月" + d.getDate() + "日";
  const wd = "星期" + WD[d.getDay()] + " · " + pad(d.getHours()) + ":" + pad(d.getMinutes());
  const note = st
    ? ("📋 今日數據　土壤 " + num(st.moisture_pct) + "% ｜ 氣溫 " + num(st.temp_c)
       + "°C ｜ 空氣濕度 " + num(st.humidity_pct) + "% ｜ 光照 " + num(st.light_pct) + "%")
    : "📋 今日數據　（這篇沒有附數據）";
  return '<div class="page"><div class="pg">'
    + '<div class="seal" style="border-color:' + s.color + ';color:' + s.color + '">'
    +   '<div class="seal-emoji">' + s.emoji + '</div><div class="seal-label">' + s.label + '</div></div>'
    + '<div class="date">' + dateStr + '<span class="wd">' + wd + '</span></div>'
    + '<div class="diary-text">' + escapeHtml(e.diary) + '</div>'
    + '<div class="note">' + note + '</div>'
    + '<div class="sign">—— 你的植物 敬上</div>'
    + '</div></div>';
}

function buildBook(){
  const book = el("flipbook");
  if (typeof St === "undefined" || !St.PageFlip){
    book.innerHTML = '<div class="fallback">翻書元件載入失敗（/vendor/page-flip.browser.js）。<br>請確認檔案存在，或重新整理。</div>';
    return;
  }
  let html = coverFront();
  if (!diaries.length){
    html += '<div class="page"><div class="pg"><div class="empty-paper">這株植物還沒寫日記…'
          + '<span>請先執行：python -m app.seed --reset</span></div></div></div>';
  } else {
    diaries.forEach(function(e){ html += entryPage(e); });
  }
  html += coverBack();

  if (pf){ try { pf.destroy(); } catch (e) {} pf = null; }
  book.innerHTML = html;

  pf = new St.PageFlip(book, {
    width: 380, height: 520, size: "stretch",
    minWidth: 260, maxWidth: 600, minHeight: 360, maxHeight: 760,
    maxShadowOpacity: 0.5, showCover: true, drawShadow: true,
    flippingTime: 650, usePortrait: true, mobileScrollSupport: false,
    showPageCorners: true,
  });
  pf.loadFromHTML(book.querySelectorAll(".page"));
  pf.on("flip", function(ev){ updatePager(ev.data); });
  // 開到最新一篇（封面=0、第 i 篇=i、封底=len+1）
  const target = diaries.length ? diaries.length : 0;
  try { pf.turnToPage(target); } catch (e) {}
  updatePager(pf.getCurrentPageIndex ? pf.getCurrentPageIndex() : target);
}

function updatePager(idx){
  const n = diaries.length;
  let label;
  if (n === 0) label = "（尚無日記）";
  else if (idx <= 0) label = "封面";
  else if (idx >= n + 1) label = "封底";
  else label = "第 <b>" + idx + "</b> / " + n + " 篇";
  el("pager").innerHTML = label;
}

async function loadDiaries(){
  try {
    const raw = await (await fetch("/api/diaries")).json();
    const asc = Array.isArray(raw) ? raw.slice().reverse() : [];
    if (asc.length === lastCount) return;   // 沒有新日記就不重建，避免打斷閱讀
    lastCount = asc.length;
    diaries = asc;
    buildBook();
  } catch (e) { /* 靜默重試 */ }
}

el("prev").onclick = function(){ if (pf) pf.flipPrev(); };
el("next").onclick = function(){ if (pf) pf.flipNext(); };
document.addEventListener("keydown", function(ev){
  if (!pf) return;
  if (ev.key === "ArrowLeft")  pf.flipPrev();
  if (ev.key === "ArrowRight") pf.flipNext();
});

async function tickDash(){
  try {
    const s = await (await fetch("/api/state")).json();
    const m = el("metrics");
    if (s.empty){
      m.innerHTML = '<div class="statusline">尚無資料，請先執行 python -m app.seed</div>';
      el("statusline").textContent = ""; return;
    }
    const st = s.stats;
    m.innerHTML =
      '<div class="metric"><div class="label">土壤濕度</div><div class="value">'+num(st.moisture_pct)+'<span class="unit">%</span></div></div>'
    + '<div class="metric"><div class="label">溫度</div><div class="value">'+num(st.temp_c)+'<span class="unit">°C</span></div></div>'
    + '<div class="metric"><div class="label">空氣濕度</div><div class="value">'+num(st.humidity_pct)+'<span class="unit">%</span></div></div>'
    + '<div class="metric"><div class="label">光照</div><div class="value">'+num(st.light_pct)+'<span class="unit">%</span></div></div>';
    const b = DASH[s.state] || [s.state,"#7fc77f"];
    el("statusline").innerHTML = '目前狀態：<b style="color:'+b[1]+'">'+b[0]+'</b> · 節點 '+s.node;
  } catch (e) { /* 靜默重試 */ }
}

loadDiaries();
tickDash();
setInterval(tickDash, 6000);
setInterval(loadDiaries, 20000);
window.addEventListener("resize", function(){ /* StPageFlip stretch 會自行處理 */ });
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
        elif u.path == "/vendor/page-flip.browser.js":
            p = _VENDOR / "page-flip.browser.js"
            if p.exists():
                self._send(200, "application/javascript; charset=utf-8", p.read_bytes())
            else:
                self._send(404, "text/plain; charset=utf-8", b"vendor lib missing")
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
