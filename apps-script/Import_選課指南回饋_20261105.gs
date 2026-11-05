/**
 * 選課指南回饋（2026-11-05）一次性更新：在「WeClass 課程資料庫」試算表的 Apps Script 執行一次即可，重複執行也不會出錯。
 *
 * 1. 「神奇平衡鳥 / 蝕刻鑰匙圈」拆成兩個單元，各 90 分鐘；STEAM創意實驗室第 2 天課表一起改。
 * 2. 「銅箔發光卡片」上課時間改成 180 分鐘（課表本來就排一整個上午）。
 * 3. 「單元」分頁新增三欄：課綱原理、難易度（1 最簡單～5 最難）、分齡學期（例如 一上、三下）。
 *    空白的格子會填入草稿，已經填過的不會被蓋掉；之後可以在後台或直接在試算表修改。
 */
function 套用選課指南回饋_20261105() {
  const ss = SpreadsheetApp.getActive();
  const packs = ss.getSheetByName('方案'), units = ss.getSheetByName('單元');
  const PLAN = {"3D列印筆:藝術作品": [1, "熱與材料", "一上"], "彈珠平衡迷宮": [1, "邏輯與數學", "一上"], "熱縮磁力釣魚": [1, "磁力、熱與材料", "一上"], "氫氣鞭炮": [2, "化學反應", "一下"], "震盪緩降機": [1, "摩擦力", "一上"], "聲音顯示器": [2, "聲音與振動", "一下"], "神奇平衡鳥": [1, "重心與平衡", "一上"], "蝕刻鑰匙圈": [2, "化學反應", "二上"], "歡樂剪叉懶人爪": [2, "連桿機構", "二上"], "銅箔發光卡片": [1, "電路", "一下"], "水晶寶寶小夜燈": [2, "光學", "二下"], "寶石越嶺": [2, "滑輪與輪軸", "二下"], "電流急急棒": [2, "電路", "三上"], "轉圈圈畫圖機": [2, "邏輯與數學、馬達與動力", "三上"], "電動混色戰鬥陀螺": [2, "光學、馬達與動力", "三下"], "電控螺旋迷宮": [3, "電路、馬達與動力", "四上"], "滑雪機器人": [2, "槓桿與力矩、馬達與動力", "二下"], "轉圈圈機器人": [2, "重心與平衡、馬達與動力", "二上"], "磁力足球場": [2, "磁力", "二上"], "相撲機器人大戰": [3, "摩擦力、馬達與動力", "四上"], "蟲蟲爬行機器人": [3, "連桿機構", "四下"], "皮克斯小檯燈": [2, "連桿機構", "三上"], "可愛槓桿垃圾桶": [1, "槓桿與力矩", "一下"], "瘋狂扭扭筆": [2, "聲音與振動、馬達與動力", "三上"], "搖頭電風扇": [3, "連桿機構", "五上"], "磁吸懸浮燈": [3, "磁力", "五下"], "3D列印筆:壽司料理": [2, "熱與材料", "三下"], "美麗的化學鮭魚卵": [2, "化學反應", "三下"], "日式搖獎機": [3, "滑輪與輪軸、邏輯與數學", "五上"], "自助飲料機": [4, "空氣與流體", "六上"], "自製藍寶石": [3, "化學反應", "四下"], "解密小金庫": [4, "邏輯與數學", "六上"], "隱形墨水筆": [3, "化學反應", "四下"], "存錢機器人": [4, "電路", "六下"], "氣壓火箭": [3, "空氣與流體", "三下"], "陸上龍舟:競速賽": [3, "摩擦力、馬達與動力", "五上"], "吊索纜車機器人": [4, "連桿機構、重心與平衡", "五下"], "跑跑線控車": [4, "電路、馬達與動力", "六下"], "感光小夜燈專案": [5, "程式設計、光學、電路", ""], "掃地機器人專案": [5, "程式設計、電路、馬達與動力", ""], "投籃機系統整合": [5, "程式設計、槓桿與力矩", ""], "錄音分幣存錢筒專案": [5, "程式設計、光學、聲音與振動", ""]};
  const SPLIT = [["P2", 0, "神奇平衡鳥", "90分鐘", "找出重心的位置，做一隻用鳥嘴就能穩穩站在指尖上的平衡鳥。", "重心與力矩", "實驗與試誤", "重心與力矩", "實驗試誤", "", "創意聯想", "u-p2-2.jpg", "低年級"], ["P2", 0, "蝕刻鑰匙圈", "90分鐘", "用氧化還原反應在金屬片上蝕刻出自己的圖案，做成獨一無二的鑰匙圈。", "氧化還原反應", "蝕刻技術、化學實驗工具", "氧化還原", "化學實驗工具", "晶片蝕刻介紹", "蝕刻藝術介紹", "", "低年級"]];
  const OLD = '神奇平衡鳥 / 蝕刻鑰匙圈', log = [];

  // ── 單元分頁：整張讀出來改好，再一次寫回去
  let rows = units.getDataRange().getValues();
  const head = rows[0].map(String);
  ['課綱原理', '難易度', '分齡學期'].forEach(h => { if (!head.includes(h)) head.push(h); });
  const W = head.length, col = n => head.indexOf(n);
  rows = rows.map(r => { const x = r.slice(0, W); while (x.length < W) x.push(''); return x; });
  rows[0] = head;
  const out = [head];
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i];
    if (String(r[col('單元名稱')]).trim() === OLD) {
      SPLIT.forEach((s, k) => { const x = Array(W).fill(''); s.forEach((v, j) => x[j] = v); x[col('方案編號')] = r[col('方案編號')]; if (k === 0 && r[col('單元照片')]) x[col('單元照片')] = r[col('單元照片')]; x[col('分齡')] = r[col('分齡')] || s[12]; out.push(x); });
      log.push('拆開平衡鳥／蝕刻鑰匙圈');
    } else out.push(r);
  }
  // 方案內重新編排序
  const seq = {};
  out.slice(1).forEach(r => { const id = String(r[0]).trim(); if (id) { seq[id] = (seq[id] || 0) + 1; r[col('排序')] = seq[id]; } });
  const seen = new Set();
  out.slice(1).forEach(r => {
    const t = String(r[col('單元名稱')]).trim();
    if (t === '銅箔發光卡片' && r[col('上課時間')] !== '180分鐘') { r[col('上課時間')] = '180分鐘'; log.push('銅箔發光卡片 180 分鐘'); }
    const d = PLAN[t];
    if (d) {
      if (!r[col('難易度')]) r[col('難易度')] = d[0];
      if (!String(r[col('課綱原理')]).trim()) r[col('課綱原理')] = d[1];
      if (!String(r[col('分齡學期')]).trim() && !seen.has(t)) r[col('分齡學期')] = d[2];
    }
    seen.add(t);
  });
  units.getRange(1, 1, out.length, W).setValues(out);
  if (units.getLastRow() > out.length) units.getRange(out.length + 1, 1, units.getLastRow() - out.length, W).setValues(Array.from({ length: units.getLastRow() - out.length }, () => Array(W).fill('')));

  // ── 方案分頁：STEAM創意實驗室第 2 天課表
  const pv = packs.getDataRange().getValues(), ph = pv[0], sc = ph.indexOf('課程表');
  for (let r = 1; r < pv.length; r++) {
    const s = String(pv[r][sc]);
    if (s.includes(OLD)) { packs.getRange(r + 1, sc + 1).setValue(s.replace('09:00 ' + OLD + '；10:40 ' + OLD, '09:00 神奇平衡鳥；10:40 蝕刻鑰匙圈').split(OLD).join('神奇平衡鳥')); log.push(pv[r][0] + ' 課表'); }
  }
  CacheService.getScriptCache().remove('courses-json');
  Logger.log('完成：' + (log.join('、') || '已經是最新的了') + '。課綱原理、難易度、分齡學期的空白格已填入草稿。');
}
