# FLIPBOOK.md — 日記本「翻書效果」是怎麼做出來的

說明 [app/server.py](app/server.py) 右側那本「可單頁拖曳翻動」的手寫日記本，從原理到逐段程式碼。
其餘架構見 [CLAUDE.md](CLAUDE.md)、資料流見 [DATAFLOW.md](DATAFLOW.md)。

---

## 0. TL;DR

 用一個現成的翻書函式庫 **StPageFlip**（純 JS、MIT）負責「翻頁物理」，我們只負責：
 ① 把每篇日記**組成一頁 HTML** ② 設定外觀（紙張/手寫字/印章） ③ 接上翻頁控制。
 函式庫**下載到本機** `app/vendor/`、由後端在 `/vendor/` 提供 → **離線也能跑、不連外**。

---

## 1. 為什麼用函式庫？（自己用 CSS 翻不出「單頁」）

第一版是純 CSS：把整個攤開的書當成**一個元素**做 `transform: rotateY(...)`。問題正是你看到的——
**兩頁一起翻、而且不能抓單獨一頁拖曳**。

因為「真實翻書」需要同時處理很多事：
- 每一**葉（leaf）**是獨立可翻的物件，且有**正面 / 背面**兩個面；
- 翻到一半時，露出**底下那一頁**；
- **滑鼠/手指拖曳頁角**時，頁面要跟著手指彎曲（即時計算角度）；
- 翻頁時動態畫出**漸層陰影 / 紙張捲曲**；
- 直式（手機）顯示單頁、橫式顯示雙頁，還要響應視窗大小。

這些用手刻 CSS/JS 會非常多，**StPageFlip 已經把這套物理與互動做好了**，所以改用它。

---

## 2. 三段式管線：資料 → DOM 頁面 → 函式庫接管

```
/api/diaries (JSON)
      │  fetch
      ▼
JS 把每篇日記組成一個 <div class="page">…</div>（封面+各篇+封底）
      │  塞進 #flipbook，再交給函式庫
      ▼
new St.PageFlip(#flipbook, opts)  →  loadFromHTML(.page)
      │  函式庫把這些頁堆疊、加上翻頁互動與陰影
      ▼
使用者：拖曳頁角 / ◀ ▶ / ← →  翻動單一葉
```

重點：**我們不碰翻頁動畫**，只給「一頁一頁的 HTML」和「外觀 CSS」，動畫與拖曳交給函式庫。

---

## 3. 把函式庫離線化（vendored + `/vendor/` 路由）

專案要能離線跑，所以不直接用 CDN，而是把函式庫**下載到本機**再自己提供：

```bash
curl -sL https://cdn.jsdelivr.net/npm/page-flip/dist/js/page-flip.browser.js \
     -o app/vendor/page-flip.browser.js     # 44 KB，已進版控
```

後端加一條靜態路由（[app/server.py](app/server.py) 的 `Handler.do_GET`）：

```python
elif u.path == "/vendor/page-flip.browser.js":
    p = _VENDOR / "page-flip.browser.js"
    self._send(200, "application/javascript; charset=utf-8", p.read_bytes())
```

網頁就用本機路徑載入它（不連外）：

```html
<script src="/vendor/page-flip.browser.js"></script>
```

這個 UMD 版會掛一個全域物件 `St`，類別就是 **`St.PageFlip`**。

---

## 4. 逐段程式碼解說（都在 [app/server.py](app/server.py) 的 `PAGE` 內）

### 4.1 把「一篇日記」組成「一頁」
每篇日記 = 一頁日誌（日期 + 狀態印章 + 手寫日記 + 當日數據邊註 + 署名）：

```js
function entryPage(e){
  const s = STATE[e.state];                       // 印章：emoji + 顏色 + 標籤
  // …組出日期字串、把 e.stats 寫成「📋 今日數據 土壤18%｜氣溫28°C…」…
  return '<div class="page"><div class="pg">'     // .page = 一葉；.pg = 內容
       +   '<div class="seal" …>…</div>'           // 右上角蠟封印章
       +   '<div class="date">…</div>'
       +   '<div class="diary-text">' + escapeHtml(e.diary) + '</div>'
       +   '<div class="note">📋 今日數據…</div>'  // ← 第 #3 點：把數據手寫進頁面
       +   '<div class="sign">—— 你的植物 敬上</div>'
       + '</div></div>';
}
```

封面/封底是**硬頁**，靠 `data-density="hard"` 告訴函式庫不要像軟紙那樣彎：

```js
'<div class="page page-cover" data-density="hard"><div class="pg">…我的植物日記…</div></div>'
```

### 4.2 建立書本：把頁面交給 StPageFlip
```js
function buildBook(){
  let html = coverFront() + diaries.map(entryPage).join("") + coverBack();
  if (pf) pf.destroy();                 // 資料變了就先拆掉舊的
  book.innerHTML = html;                // 把所有 .page 放進 #flipbook

  pf = new St.PageFlip(book, {
    width:380, height:520, size:"stretch",   // 單頁基準比例；stretch=隨容器縮放
    minWidth:260, maxWidth:600, minHeight:360, maxHeight:760,
    showCover:true,        // 第一/最後一頁當封面
    drawShadow:true,       // 翻頁時畫陰影
    flippingTime:650,      // 翻頁動畫毫秒
    usePortrait:true,      // 窄畫面自動切單頁直式
    showPageCorners:true,  // 顯示可拖曳的頁角（單頁拖曳的關鍵）
  });
  pf.loadFromHTML(book.querySelectorAll(".page"));   // ← 真正把 DOM 變成可翻的書
  pf.on("flip", function(ev){ updatePager(ev.data); });
  pf.turnToPage(diaries.length);        // 一開始翻到最新一篇
}
```

`loadFromHTML()` 是關鍵：函式庫把這些 `.page` 元素**重新堆疊**到它自己的容器裡，套上絕對定位、transform 與事件監聽，從此**翻頁由它接管**。

### 4.3 翻頁控制
我們只要呼叫它的 API；不用自己寫動畫：

```js
prev.onclick = () => pf.flipPrev();     // 上一葉
next.onclick = () => pf.flipNext();     // 下一葉
document.addEventListener("keydown", e => {
  if (e.key === "ArrowLeft")  pf.flipPrev();
  if (e.key === "ArrowRight") pf.flipNext();
});
pf.on("flip", ev => updatePager(ev.data));   // 翻到第幾頁 → 更新「第 k / N 篇」
```
**拖曳**完全由函式庫處理（因為 `showPageCorners:true`）：抓頁角拖動就會單葉跟著彎、放開就翻過去或彈回。

### 4.4 資料更新不打斷閱讀
每 20 秒重抓一次日記，但**只有篇數變了才重建書本**，避免你正在看時被打斷：

```js
if (asc.length === lastCount) return;   // 沒有新日記就不重建
lastCount = asc.length; diaries = asc; buildBook();
```

---

## 5. StPageFlip 背後到底做了什麼？（翻頁物理）

概念上（不需要你寫，但理解有幫助）：

1. **堆疊頁面**：把所有頁絕對定位疊在一起，只顯示目前攤開的一葉（橫式為左右兩頁）。
2. **互動偵測**：監聽 `pointer`/`mouse`/`touch`，判斷你是不是抓在**頁角熱區**。
3. **即時彎折**：拖曳時依手指位置，用 CSS `transform`（含 3D `rotate`）把那一葉折起，露出底下頁。
4. **動態陰影**：用漸層 / canvas 在折線與頁背畫陰影，模擬紙張厚度與捲曲。
5. **吸附判定**：放手時若超過一半就完成翻頁、否則彈回（带動畫，時間 = `flippingTime`）。
6. **軟頁 vs 硬頁**：`data-density="hard"` 的頁（封面）不彎、像書殼；軟頁才會彎折。
7. **方向自適應**：依容器寬高在「橫式雙頁 / 直式單頁」間切換（`usePortrait`、`size:"stretch"`）。

---

## 6. 讓紙張像紙張（CSS，這部分是我們寫的）

外觀和「翻頁」是分開的——函式庫管翻、CSS 管長相：

```css
.page .pg {
  /* 橫線稿紙：每 32px 一條淡褐線 */
  background-image:repeating-linear-gradient(transparent 0 31px, rgba(120,100,60,.18) 31px 32px);
}
.page .pg::before { /* 左側紅色邊界線 */ left:18px; width:2px; background:rgba(200,90,80,.28); }
.diary-text { font-family:"KaiTi","DFKai-SB","BiauKai","STKaiti",cursive,serif; }  /* 手寫毛筆感 */
.seal { border-radius:50%; transform:rotate(-9deg); }                              /* 蠟封印章 */
.page-cover .pg { background:linear-gradient(135deg,#2f4a32,#23381f); }            /* 深綠書皮 */
```
（`KaiTi/標楷體` 是 Windows 內建字型，所以你的電腦會顯示手寫感；沒有的環境會退回 cursive/serif。）

---

## 7. 想調整時改這裡

| 想改 | 改哪個（`buildBook()` 的 options 或 CSS） |
|---|---|
| 翻頁速度 | `flippingTime`（毫秒，預設 650） |
| 書本大小 | `maxWidth` / `maxHeight`（預設 600 / 760） |
| 一律雙頁 / 允許單頁 | `usePortrait`（true=窄畫面自動單頁） |
| 是否顯示可拖曳頁角 | `showPageCorners` |
| 紙張顏色 / 線距 / 字體 | `.page .pg` 背景與 `.diary-text` 的 `font-family` |
| 每頁內容 | `entryPage()`（日記本文、數據邊註的文字） |

---

## 8. 參考
- 函式庫：StPageFlip（npm: `page-flip`），MIT 授權。本機檔：`app/vendor/page-flip.browser.js`。
- 主要 API：`new St.PageFlip(el, opts)`、`loadFromHTML()`、`flipNext()`/`flipPrev()`、`turnToPage()`、`on("flip", …)`、`destroy()`。
