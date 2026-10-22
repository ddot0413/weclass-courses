#!/usr/bin/env python3
"""
WeClass 選課指南：靜態網站產生器（SEO 版）

把 src/template.html（互動網頁）預先轉成一頁一頁的靜態 HTML：
  /courses/                        選課指南（依主題／年齡／學習目標，同一頁切換）
  /courses/<方案網址>/              每個課程方案一頁
並產生 sitemap.xml、robots.txt、llms.txt，每頁附上標題、描述、分享圖與結構化資料（Course、FAQPage、BreadcrumbList、ItemList）。
頁面打開後仍是原本的互動網頁（篩選、角色標籤、展開學習重點都照常運作）。

用法
  python build.py                                   # 用 src/data.json 的課程資料
  python build.py --data-url "<試算表網頁應用程式網址>"   # 改用試算表最新資料
  選項：--origin https://weclass.tw  --base /courses/  --out dist

需要：Python 3.9+、playwright（pip install playwright && python -m playwright install chromium）
"""
import argparse, html, json, re, shutil, sys, threading, urllib.request, functools
from datetime import date
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'

ap = argparse.ArgumentParser()
ap.add_argument('--data-url', default='', help='試算表部署的網頁應用程式網址；留空則用 src/data.json')
ap.add_argument('--origin', default='https://weclass.tw', help='網站正式網域，用於 canonical 與 sitemap')
ap.add_argument('--base', default='/courses/', help='課程站在網域下的路徑，前後都要有 /')
ap.add_argument('--out', default='dist', help='輸出資料夾')
ap.add_argument('--live-data', action='store_true', help='頁面打開後再向試算表讀最新資料（需搭配 --data-url）')
ap.add_argument('--noindex', action='store_true', help='預覽用：請搜尋引擎不要收錄（給客戶看的暫時網址用）')
args = ap.parse_args()
BASE = '/' + args.base.strip('/') + '/' if args.base.strip('/') else '/'
ORIGIN = args.origin.rstrip('/')
OUT = (ROOT / args.out).resolve()
SITE = OUT / BASE.strip('/') if BASE != '/' else OUT
A = BASE + 'assets/'

# ── 1. 課程資料 ──────────────────────────────────────────
if args.data_url:
    with urllib.request.urlopen(args.data_url, timeout=60) as r:
        courses = json.loads(r.read().decode('utf-8'))['courses']
    print(f'從試算表讀到 {len(courses)} 個方案')
else:
    courses = json.loads((SRC / 'data.json').read_text('utf-8'))
if not courses:
    sys.exit('沒有課程資料')

# ── 2. 準備輸出資料夾與共用檔案 ─────────────────────────────
if OUT.exists():
    shutil.rmtree(OUT)
(SITE / 'assets').mkdir(parents=True)
for f in (SRC / 'assets').iterdir():
    shutil.copy(f, SITE / 'assets' / f.name)
meta = json.loads((SRC / 'assets.json').read_text('utf-8'))
t = (SRC / 'template.html').read_text('utf-8')
t = t.replace('{{ASSET_VARS}}', '\n  '.join(f'--{k}: url("{A}{v}");' for k, v in meta['css_vars'].items()))
t = t.replace('{{PHOTOS}}', json.dumps({k: A + v for k, v in meta['photos'].items()}))
t = t.replace('{{HERO_GIRL}}', A + meta['hero_girl'])
t = t.replace('{{BLOB}}', meta['blob'])
t = t.replace('{{DB}}', 'const db = ' + json.dumps(courses, ensure_ascii=False) + ';')
if args.live_data and args.data_url:
    t = t.replace("const DATA_URL = '';", f"const DATA_URL = {json.dumps(args.data_url)};")
assert '{{' not in t, '範本還有沒替換的欄位'

css = '\n'.join(re.findall(r'<style[^>]*>(.*?)</style>', t, re.S))
js = re.search(r'<script>(.*?)</script>', t, re.S).group(1)
body = t[t.index('</style>', t.index('<style>\n')) + len('</style>'):t.index('<script>')].strip()
def _nav_drop():
    def col(kind, note):
        items = ''.join(f'<li><a href="#{p["id"]}" data-pid="{p["id"]}"><span>{html.escape(p["title"])}</span><small>{html.escape(p["grades"])}</small></a></li>' for p in courses if p['type'] == kind)
        return f'<div class="nd-col"><p class="nd-h">{kind}課程<small>{note}</small></p><ul>{items}</ul></div>'
    return col('初階', '單元實作') + col('進階', '3 天專案') + '<a class="nd-all" href="#theme">看全部課程方案 →</a>'
body = body.replace('<!--NAVDROP-->', _nav_drop())   # 下拉選單直接寫進每一頁，搜尋引擎也看得到每個課程的連結
(SITE / 'assets' / 'site.css').write_text(css, 'utf-8')
(SITE / 'assets' / 'site.js').write_text(js, 'utf-8')
import hashlib
VER = hashlib.md5((css + js).encode('utf-8')).hexdigest()[:8]   # 內容變了檔名參數就變，瀏覽器不會用到舊的快取

# 官方 LINE 加入好友 QR Code（電腦版課程清單用）；有安裝 qrcode 套件才產生，沒有時網頁改用線上套件畫
QR_JS = ''
try:
    import qrcode, qrcode.image.svg
    qrcode.make('https://line.me/R/ti/p/%40238hxhaz', image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2).save(str(SITE / 'assets' / 'line-qr.svg'))
    QR_JS = f"window.WECLASS_QR = {json.dumps(A + 'line-qr.svg')};"
except Exception as e:
    print('（略過 QR Code：', e, '）')

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@500;700;900&family=Poppins:wght@700;900&display=swap" rel="stylesheet">')


def page(head, app_html=''):
    return f'''<!DOCTYPE html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
{head}
{FONTS}
<link rel="stylesheet" href="{A}site.css?v={VER}">
<link rel="icon" href="{A}logo.svg" type="image/svg+xml">
<script>window.WECLASS_BASE = {json.dumps(BASE)};{QR_JS}</script>
</head>
<body>
{body.replace('<main id="app"></main>', '<main id="app">' + app_html + '</main>')}
<script src="{A}site.js?v={VER}"></script>
</body>
</html>
'''


# ── 3. 每一頁的網址 ───────────────────────────────────────
SLUGS = dict(re.findall(r"(p\d+): '([a-z0-9-]+)'", re.search(r'const SLUGS = \{(.*?)\};', js).group(1)))
slug = lambda p: p.get('slug') or SLUGS.get(p['id']) or p['id']
routes = [('', None)] + [(slug(p) + '/', p) for p in courses]
for rel, _ in routes:
    (SITE / rel).mkdir(parents=True, exist_ok=True)
    (SITE / rel / 'index.html').write_text(page('<title>WeClass</title>'), 'utf-8')

# ── 4. 用瀏覽器把互動網頁預先畫好（預先渲染） ─────────────────
from playwright.sync_api import sync_playwright

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
handler = functools.partial(Quiet, directory=str(OUT))
srv = ThreadingHTTPServer(('127.0.0.1', 0), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
local = f'http://127.0.0.1:{srv.server_address[1]}'


def clean_links(s):
    """把 #p1、#all、# 這類預覽網址換成真正的網址，搜尋引擎才找得到每一頁。"""
    by_id = {p['id']: slug(p) for p in courses}
    def sub(m):
        h = m.group(1)
        if h == '#': return f'href="{BASE}"'
        if h == '#all': return f'href="{BASE}#theme"'
        if h in ('#theme', '#stage', '#goal'): return f'href="{BASE}{h}"'
        mm = re.fullmatch(r'#(p\d+)(?:\.(\d+))?', h)
        if mm and mm.group(1) in by_id:
            return f'href="{BASE}{by_id[mm.group(1)]}/' + (f'#u{mm.group(2)}' if mm.group(2) else '') + '"'
        return m.group(0)
    return re.sub(r'href="(#[^"]*)"', sub, s)


rendered = {}
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    pg = browser.new_page(viewport={'width': 1280, 'height': 900})
    pg.route('**/*', lambda r: r.continue_() if r.request.url.startswith(local) else r.abort())   # 只載入本機檔案，字型等外部資源略過
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    for rel, p in routes:
        pg.goto(local + BASE + rel, wait_until='load')
        pg.wait_for_timeout(250)
        rendered[rel] = {
            'app': pg.eval_on_selector('#app', 'e => e.innerHTML'),
            'faq': pg.eval_on_selector_all('.qa-item', 'els => els.map(d => ({ q: d.querySelector("summary").textContent.trim(), a: d.querySelector(".ans").innerText.trim() }))'),
        }
    browser.close()
srv.shutdown()
if errors:
    sys.exit('預先渲染時發生錯誤：\n' + '\n'.join(errors))

# ── 5. 每頁的標題、描述、分享圖與結構化資料 ─────────────────────
ORG = {'@type': 'Organization', 'name': 'WeClass 維課教育', 'url': 'https://weclass.tw/', 'logo': ORIGIN + A + 'logo.svg',
       'email': 'weclass.tw@gmail.com', 'telephone': '+886-3-5611887',
       'address': {'@type': 'PostalAddress', 'streetAddress': '中華路三段 9 號 6 樓之 4', 'addressLocality': '新竹市北區', 'addressCountry': 'TW'}}
PKG_PHOTO = dict(re.findall(r"(p\d+): '([a-z0-9]+)'", re.search(r'const PKG_PHOTO = \{(.*?)\};', js).group(1)))
esc = lambda s: html.escape(str(s or ''), quote=True)
url = lambda rel: ORIGIN + BASE + rel


def minutes(p):
    return sum(int(m.group()) for u in p['units'] for m in [re.match(r'\d+', u.get('duration') or '')] if m)


def syllabus(u):
    s = {'@type': 'Syllabus', 'name': u['title'], 'description': u.get('desc', '')}
    m = re.match(r'\d+', u.get('duration') or '')
    if m: s['timeRequired'] = 'PT' + m.group() + 'M'
    return s


def photo(p):
    img = p.get('intro_image') or ''
    return img if img.startswith('http') else ORIGIN + A + meta['photos'].get(PKG_PHOTO.get(p['id'], 'class'), 'ph-class.jpg')


def jsonld(*objs):
    return ''.join(f'<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", **o}, ensure_ascii=False)}</script>' for o in objs)


def head(title, desc, rel, image, *ld):
    return (('<meta name="robots" content="noindex, nofollow">\n' if args.noindex else '') + f'<title>{esc(title)}</title>\n<meta name="description" content="{esc(desc)}">\n<link rel="canonical" href="{url(rel)}">\n'
            f'<meta property="og:type" content="website"><meta property="og:site_name" content="WeClass 維課教育">\n'
            f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">\n'
            f'<meta property="og:url" content="{url(rel)}"><meta property="og:image" content="{esc(image)}"><meta property="og:locale" content="zh_TW">\n'
            f'<meta name="twitter:card" content="summary_large_image">\n<meta name="theme-color" content="#1D4C58">\n' + jsonld(*ld))


def faq_ld(items):
    return {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': i['q'], 'acceptedAnswer': {'@type': 'Answer', 'text': i['a']}} for i in items]}


def crumbs(*pairs):
    return {'@type': 'BreadcrumbList', 'itemListElement': [{'@type': 'ListItem', 'position': n + 1, 'name': name, 'item': link} for n, (name, link) in enumerate(pairs)]}


total_units = sum(len(p['units']) for p in courses)
item_list = {'@type': 'ItemList', 'name': 'WeClass STEAM 課程方案', 'itemListElement': [
    {'@type': 'ListItem', 'position': n + 1, 'url': url(slug(p) + '/'), 'name': p['title']} for n, p in enumerate(courses)]}
home_crumb = ('WeClass 官網', 'https://weclass.tw/')

for rel, p in routes:
    r = rendered[rel]
    if rel == '':
        title = '選課指南｜依主題、年齡、學習目標找 STEAM 實作課程｜WeClass 維課教育'
        desc = (f'WeClass 校長選課指南：{len(courses)} 個 STEAM 課程方案、{total_units} 個實作單元，可依主題、依孩子年齡，'
                '或依 108 課綱四大學習世界（科學、工程、科技、藝術）找到適合的課程。適合學校、安親班、營隊與企業合作。')
        h = head(title, desc, rel, ORIGIN + A + 'cast-group.webp', ORG, crumbs(home_crumb, ('選課指南', url(''))), item_list, faq_ld(r['faq']))
    elif rel == 'all/':
        title = f'全部 STEAM 課程方案（{len(courses)} 個）｜WeClass 維課教育'
        desc = '、'.join(f"{c['title']}（{c['grades']}）" for c in courses)
        desc = f'WeClass 全部課程方案：{desc}。'[:150]
        h = head(title, desc, rel, ORIGIN + A + 'cast-group.webp', crumbs(home_crumb, ('課綱單元課程包', url('')), ('全部課程方案', url('all/'))), item_list)
    else:
        m = minutes(p)
        dur = '3 天跨日專案' if p['type'] == '進階' else f"{len(p['units'])} 個單元・共 {m} 分鐘"
        title = f"{p['title']}｜{p['grades']} STEAM 課程方案｜WeClass 維課教育"
        desc = f"{p['desc']}（{p['grades']}，{dur}）單元：{'、'.join(u['title'] for u in p['units'])}。"[:160]
        teaches = sorted({t for u in p['units'] for k in ('sci', 'eng', 'tech', 'art') for t in u[k]})
        course = {'@type': 'Course', 'name': p['title'], 'description': p['desc'], 'url': url(rel), 'image': photo(p), 'inLanguage': 'zh-TW',
                  'educationalLevel': p['grades'], 'provider': ORG, 'teaches': teaches,
                  'hasCourseInstance': {'@type': 'CourseInstance', 'courseMode': 'Onsite',
                                        'courseWorkload': 'P3D' if p['type'] == '進階' else f'PT{m}M'},
                  'syllabusSections': [syllabus(u) for u in p['units']]}
        h = head(title, desc, rel, photo(p), course, faq_ld(r['faq']),
                 crumbs(home_crumb, ('選課指南', url('')), (p['title'], url(rel))))
    (SITE / rel / 'index.html').write_text(clean_links(page(h, r['app'])), 'utf-8')

# ── 6. sitemap.xml、robots.txt、llms.txt、404 ────────────────
today = date.today().isoformat()
(SITE / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
                                  ''.join(f'  <url><loc>{url(rel)}</loc><lastmod>{today}</lastmod></url>\n' for rel, _ in routes) + '</urlset>\n', 'utf-8')
robots = 'User-agent: *\nDisallow: /\n' if args.noindex else f'User-agent: *\nAllow: /\n\nSitemap: {url("sitemap.xml")}\n'
(SITE / 'robots.txt').write_text(robots, 'utf-8')
if BASE != '/':
    (OUT / 'robots.txt').write_text(robots, 'utf-8')   # 若課程站獨立部署（例如子網域），根目錄也放一份
llms = [f'# WeClass 選課指南\n\n> WeClass 維課教育的 STEAM 實作課程方案：{len(courses)} 個方案、{total_units} 個單元，對應 108 課綱與四大學習世界（科學／化學、工程、科技、藝術）。官網：https://weclass.tw/\n',
        f'- [選課指南：依主題、年齡、學習目標找課]({url("")})\n\n## 課程方案\n']
for p in courses:
    m = minutes(p)
    llms.append(f"- [{p['title']}]({url(slug(p) + '/')})：{p['grades']}，{'3 天跨日專案' if p['type'] == '進階' else str(len(p['units'])) + ' 個單元、共 ' + str(m) + ' 分鐘'}。{p['desc']}\n")
(SITE / 'llms.txt').write_text(''.join(llms), 'utf-8')
(SITE / '404.html').write_text(page('<title>找不到這個頁面｜WeClass 維課教育</title><meta name="robots" content="noindex">',
                                    f'<section class="hero" style="padding:80px 0"><div class="wrap"><div class="hero-copy"><h1>找不到這個頁面</h1><p class="d">這個課程可能已經改名或下架。</p><a class="btn orange" href="{BASE}">回選課指南</a></div></div></section>'), 'utf-8')

print(f'完成：{len(routes)} 頁，輸出在 {SITE}')
for rel, _ in routes:
    print('  ' + url(rel))
