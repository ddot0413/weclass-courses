# WeClass 課綱單元課程包（SEO 靜態網站版）

把課程網站預先產生成一頁一頁的 HTML，搜尋引擎與 AI 搜尋（ChatGPT、Perplexity、Google AI 摘要）不需執行程式就能讀到完整內容；使用者打開後仍是原本的互動網頁。

## 產生出來的內容

| 網址 | 內容 |
|---|---|
| `/courses/` | 課綱單元課程包：依學習目標找單元＋常見問題 |
| `/courses/all/` | 全部課程方案 |
| `/courses/<網址代稱>/` | 每個課程方案一頁（例如 `/courses/steam-little-inventor/`） |
| `/courses/sitemap.xml` | 網站地圖，提交給 Google Search Console |
| `/courses/robots.txt`、`/courses/llms.txt` | 給搜尋引擎與 AI 爬蟲的說明 |

每頁都有：專屬標題與描述、canonical 網址、分享縮圖（Open Graph）、結構化資料（Course、FAQPage、BreadcrumbList、ItemList、Organization），以及畫面上看得到的常見問題。

## 在自己電腦產生

```bash
pip install playwright
python -m playwright install chromium
python build.py                                  # 用 src/data.json
python build.py --data-url "<試算表網頁應用程式網址>" --live-data   # 用試算表最新資料
```

選項：`--origin`（正式網域，預設 https://weclass.tw）、`--base`（路徑，預設 /courses/）。輸出在 `dist/`。

## 上線方式（擇一）

**A. 放在官網底下（SEO 最好）**：把 `dist/courses/` 整個資料夾上傳到 weclass.tw 主機，網址就是 `https://weclass.tw/courses/`。之後課程有更新，重新產生再上傳。

**B. 獨立子網域、自動更新**：把這個資料夾放到 GitHub，開啟 Pages，設定 `SITE_ORIGIN=https://courses.weclass.tw`、`SITE_BASE=/` 與 `DATA_URL`；網域商把 `courses` 指向 GitHub Pages。之後每天自動從試算表重新產生（也可手動按 Run workflow）。

加上 `--live-data` 時，頁面打開後還會向試算表讀最新內容，所以後台發布後使用者約 5 分鐘內就看得到；搜尋引擎讀到的則是最近一次產生的版本。新增的方案要等下次重新產生後才會有自己的網頁。

## 上線後要做

1. 到 Google Search Console 新增網站並提交 `sitemap.xml`。
2. 官網「Find Your Course」第三張卡連到 `/courses/`。
3. 網址代稱上線後不要再改；要改的話請在主機設定舊網址轉址到新網址。

## 資料夾

- `src/template.html`：互動網頁範本（和預覽版同一份程式）
- `src/data.json`：內建課程資料（沒有試算表時使用）
- `src/assets/`：圖片
- `apps-script/`：試算表後台程式（Code.gs、Admin.html）
- `build.py`：產生器
