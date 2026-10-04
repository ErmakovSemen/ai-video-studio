// Элементы дневника: бумага в точку, пружина, скотч washi, наклейки, полароиды, стикеры-заметки,
// печати, маркер, стрелки. Каждый элемент появляется один раз своей короткой анимацией, дальше
// живёт только «кипением» линий (смена рисунка 12 раз в секунду).
(function () {
  'use strict';
  const P = window.PENCIL;
  const { W, H, rng, seg, lerp, easeOut, easeIO, ellipse, CAM, pencil, hatch, hand, glyph, wash } = P;
  const PX = 40, PY = 70, PW = 1000, PH = 1520; // страница дневника на экране (низ 1590 — выше зоны интерфейса)
  const SHADOW = 'rgba(40,28,18,0.28)';
  function mk(w, h) { const c = document.createElement('canvas'); c.width = Math.ceil(w); c.height = Math.ceil(h); return c; }
  const COLORS = { // дополнительные цвета дневника
    cream: '#f6efdf', creamDark: '#d9cdb4', dot: '#b9ab90', yellow: '#f3d25b', mint: '#a9cdb3', coral: '#e58a6f',
    sky: '#9cc3d9', red: '#c8402e', gold: '#e2a21c', ink: '#2c2420', white: '#fffdf6', kraft: '#c9a77a',
  };

  let tooth = null;
  function setTooth(t) { tooth = t; }

  // ---------- бумага дневника ----------
  function makePage(pal) {
    const full = P.makePaper(Object.assign({}, pal, { name: 'cream', paper: COLORS.cream, paperLight: '#fffaf0', paperDark: COLORS.creamDark, grain: 10 }));
    const c = mk(PW, PH), g = c.getContext('2d');
    g.drawImage(full, 0, 0, PW, PH, 0, 0, PW, PH);
    g.fillStyle = COLORS.dot; g.globalAlpha = 0.55;
    for (let y = 40; y < PH - 20; y += 40) for (let x = 80; x < PW - 20; x += 40) { g.beginPath(); g.arc(x, y, 2.2, 0, 7); g.fill(); }
    g.globalAlpha = 1; g.fillStyle = '#5a4a3a';
    for (let y = 60; y < PH - 40; y += 64) { g.beginPath(); g.arc(30, y, 9, 0, 7); g.fill(); } // отверстия под пружину
    return c;
  }
  function rings(g, d) { // пружина поверх края страницы
    for (let y = PY + 60, i = 0; y < PY + PH - 40; y += 64, i++) {
      g.save(); g.lineCap = 'round';
      g.strokeStyle = '#3a3330'; g.lineWidth = 7; g.beginPath(); g.ellipse(PX + 12, y, 26, 12, 0, Math.PI * 0.55, Math.PI * 1.95); g.stroke();
      g.strokeStyle = '#a9a39b'; g.lineWidth = 2.5; g.beginPath(); g.ellipse(PX + 12, y - 2, 25, 10, 0, Math.PI * 1.1, Math.PI * 1.7); g.stroke();
      g.restore();
    }
  }

  // ---------- общие анимации появления ----------
  const slapScale = u => (u >= 1 ? 1 : u < 0.75 ? lerp(1.38, 0.96, easeOut(u / 0.75)) : lerp(0.96, 1, (u - 0.75) / 0.25));
  function shapePath(g, shp, grow = 0) {
    g.beginPath();
    if (shp.type === 'circle') g.arc(0, 0, shp.r + grow, 0, Math.PI * 2);
    else if (shp.type === 'star') {
      const n = shp.n || 5;
      for (let i = 0; i <= n * 2; i++) { const a = -Math.PI / 2 + i * Math.PI / n, r = (i % 2 ? shp.r * 0.48 : shp.r) + grow; i ? g.lineTo(Math.cos(a) * r, Math.sin(a) * r) : g.moveTo(Math.cos(a) * r, Math.sin(a) * r); }
      g.closePath();
    } else { const w = shp.w / 2 + grow, h = shp.h / 2 + grow, r = Math.min(shp.r || 20, w, h); g.roundRect(-w, -h, 2 * w, 2 * h, r); }
  }
  function grain(c) { // зерно карандаша внутри офскрина
    const g = c.getContext('2d'); g.save(); g.globalCompositeOperation = 'destination-out'; g.globalAlpha = 0.45;
    g.drawImage(tooth, 0, 0, c.width, c.height, 0, 0, c.width, c.height); g.restore();
  }

  // наклейка: белая высечка, тень, «шлёп» с отскоком
  const stickerBufs = new Map();
  function sticker(g, o, lt, d) {
    const u = seg(lt, o.t, o.t + 0.2); if (u <= 0) return;
    const s = slapScale(u), r = o.rot + (1 - easeOut(Math.min(1, u))) * 0.3, shp = o.shape;
    const bw = shp.type === 'circle' || shp.type === 'star' ? shp.r * 2 : shp.w, bh = shp.type === 'circle' || shp.type === 'star' ? shp.r * 2 : shp.h;
    let buf = stickerBufs.get(o.id); if (!buf) { buf = mk(bw, bh); stickerBufs.set(o.id, buf); }
    const b = buf.getContext('2d'); b.setTransform(1, 0, 0, 1, 0, 0); b.clearRect(0, 0, bw, bh);
    if (o.draw) { CAM.reset(); o.draw(b, bw, bh, d); }
    grain(buf);
    g.save(); g.translate(o.x, o.y); g.rotate(r); g.scale(s, s);
    g.save(); g.translate(5, 9); shapePath(g, shp, 13); g.fillStyle = SHADOW; g.fill(); g.restore();
    shapePath(g, shp, 13); g.fillStyle = COLORS.white; g.fill();
    g.save(); shapePath(g, shp); g.clip(); g.fillStyle = o.bg; g.fillRect(-bw / 2, -bh / 2, bw, bh); g.drawImage(buf, -bw / 2, -bh / 2); g.restore();
    shapePath(g, shp, 13); g.strokeStyle = 'rgba(60,45,35,0.25)'; g.lineWidth = 1.5; g.stroke();
    g.restore();
  }

  // скотч washi: полоска раскатывается, края-«зубчики», полоски узора
  function tape(g, o, lt, d) {
    const u = easeOut(seg(lt, o.t, o.t + 0.22)); if (u <= 0) return;
    const [x0, y0] = o.a, x1 = lerp(x0, o.b[0], u), y1 = lerp(y0, o.b[1], u);
    const L = Math.hypot(x1 - x0, y1 - y0), ang = Math.atan2(y1 - y0, x1 - x0), w = o.w || 56, R = rng(o.id, 'tape');
    g.save(); g.translate(x0, y0); g.rotate(ang);
    const edge = [], n = 7;
    for (let i = 0; i <= n; i++) edge.push([(i % 2 ? 7 : 0) * (R() * 0.6 + 0.6), -w / 2 + i * w / n]);
    const end = edge.map(q => [L - q[0] * (u >= 1 ? 1 : 0), q[1]]).reverse();
    g.beginPath(); edge.concat(end).forEach((q, i) => (i ? g.lineTo(q[0], q[1]) : g.moveTo(q[0], q[1]))); g.closePath();
    g.save(); g.translate(2, 4); g.fillStyle = 'rgba(40,28,18,0.12)'; g.fill(); g.restore();
    g.fillStyle = o.color; g.globalAlpha = 0.8; g.fill(); g.globalAlpha = 1;
    g.save(); g.clip(); g.strokeStyle = 'rgba(255,255,255,0.45)'; g.lineWidth = 7;
    for (let x = -w; x < L + w; x += 22) { g.beginPath(); g.moveTo(x, -w / 2); g.lineTo(x + w * 0.6, w / 2); g.stroke(); }
    g.restore(); g.restore();
  }

  // полароид: фото-офскрин + белая рамка + подпись от руки; «падает» на страницу
  const photoBufs = new Map();
  function polaroid(g, o, lt, d) {
    const u = seg(lt, o.t, o.t + 0.25); if (u <= 0) return null;
    const e = easeOut(u), s = lerp(1.08, 1, e), r = o.rot + 0.1 * (1 - e), dy = -70 * (1 - e);
    const m = 26, fw = o.w + 2 * m, fh = o.h + m + 120;
    let buf = photoBufs.get(o.id); if (!buf) { buf = mk(o.w, o.h); photoBufs.set(o.id, buf); }
    const b = buf.getContext('2d'); b.setTransform(1, 0, 0, 1, 0, 0); b.globalCompositeOperation = 'source-over'; b.globalAlpha = 1;
    b.clearRect(0, 0, o.w, o.h);
    CAM.reset(); o.draw(b, o.w, o.h, lt - o.t, d);
    grain(buf);
    g.save(); g.translate(o.x, o.y + dy); g.rotate(r); g.scale(s, s);
    g.fillStyle = SHADOW; g.fillRect(-fw / 2 + 8, -fh / 2 + 14, fw, fh);
    g.fillStyle = COLORS.white; g.fillRect(-fw / 2, -fh / 2, fw, fh);
    g.fillStyle = o.bg || '#efe7d6'; g.fillRect(-o.w / 2, -fh / 2 + m, o.w, o.h);
    g.drawImage(buf, -o.w / 2, -fh / 2 + m);
    g.strokeStyle = 'rgba(60,45,35,0.3)'; g.lineWidth = 1.5; g.strokeRect(-o.w / 2, -fh / 2 + m, o.w, o.h);
    if (o.caption) hand(g, o.caption, 0, fh / 2 - 38, { id: o.id + 'cap', d, size: 60, color: COLORS.ink, p: seg(lt, o.t + 0.5, o.t + 1.1) });
    g.restore();
    return { fw, fh };
  }

  // стикер-заметка: мягкий «шлёп», загнутый уголок, строки от руки
  function sticky(g, o, lt, d) {
    const u = seg(lt, o.t, o.t + 0.2); if (u <= 0) return;
    const s = lerp(1.15, 1, easeOut(u)), r = o.rot + 0.12 * (1 - easeOut(u)), w = o.w, h = o.h;
    g.save(); g.translate(o.x, o.y); g.rotate(r); g.scale(s, s);
    g.fillStyle = SHADOW; g.beginPath(); g.moveTo(-w / 2 + 6, -h / 2 + 10); g.lineTo(w / 2 + 6, -h / 2 + 10); g.lineTo(w / 2 + 2, h / 2 + 16); g.lineTo(-w / 2 + 8, h / 2 + 12); g.fill();
    g.fillStyle = o.color; g.beginPath(); g.moveTo(-w / 2, -h / 2); g.lineTo(w / 2, -h / 2); g.lineTo(w / 2, h / 2 - 34); g.lineTo(w / 2 - 34, h / 2); g.lineTo(-w / 2, h / 2); g.closePath(); g.fill();
    g.fillStyle = 'rgba(0,0,0,0.06)'; g.fillRect(-w / 2, -h / 2, w, 34); // клеевой край
    g.fillStyle = 'rgba(0,0,0,0.12)'; g.beginPath(); g.moveTo(w / 2, h / 2 - 34); g.lineTo(w / 2 - 34, h / 2); g.lineTo(w / 2 - 30, h / 2 - 30); g.closePath(); g.fill();
    o.lines.forEach((s2, i) => hand(g, s2, 0, -h / 2 + 90 + i * (o.size || 58) * 1.05, { id: o.id + i, d, size: o.size || 58, color: COLORS.ink, p: seg(lt, o.t + 0.25 + i * 0.45, o.t + 0.7 + i * 0.45) }));
    g.restore();
  }

  // печать: «бух» и неровный оттиск
  const stampBufs = new Map();
  function stamp(g, o, lt, d) {
    const u = seg(lt, o.t, o.t + 0.12); if (u <= 0) return;
    const s = lerp(1.3, 1, easeOut(u)), S = o.size;
    let buf = stampBufs.get(o.id);
    if (!buf) {
      buf = mk(S * 2.4, S * 2.4); const b = buf.getContext('2d'), c = S * 1.2;
      b.strokeStyle = COLORS.red; b.lineWidth = 7; b.strokeRect(c - S, c - S, 2 * S, 2 * S); b.lineWidth = 2.5; b.strokeRect(c - S + 12, c - S + 12, 2 * S - 24, 2 * S - 24);
      b.fillStyle = COLORS.red; b.font = `${o.chars.length > 2 ? S * 0.62 : S * 0.82}px Glyph`; b.textAlign = 'center'; b.textBaseline = 'middle';
      if (o.chars.length === 2) { b.fillText(o.chars[0], c, c - S * 0.42); b.fillText(o.chars[1], c, c + S * 0.46); } else b.fillText(o.chars, c, c + 4);
      b.globalCompositeOperation = 'destination-out'; b.globalAlpha = 0.6; b.drawImage(tooth, 300, 500, buf.width, buf.height, 0, 0, buf.width, buf.height);
      stampBufs.set(o.id, buf);
    }
    g.save(); g.translate(o.x, o.y); g.rotate(o.rot || 0); g.scale(s, s); g.globalAlpha = 0.88;
    g.drawImage(buf, -buf.width / 2, -buf.height / 2); g.restore();
  }

  // маркер: широкий полупрозрачный мазок слева направо
  function marker(g, o, lt) {
    const u = easeIO(seg(lt, o.t, o.t + 0.35)); if (u <= 0) return;
    g.save(); g.globalAlpha = 0.45; g.fillStyle = o.color || COLORS.yellow; g.globalCompositeOperation = 'multiply';
    const x1 = lerp(o.x0, o.x1, u); g.beginPath();
    g.moveTo(o.x0, o.y - o.h / 2 + 3); g.lineTo(x1, o.y - o.h / 2); g.lineTo(x1 + 6, o.y + o.h / 2); g.lineTo(o.x0 - 4, o.y + o.h / 2 - 2); g.closePath(); g.fill(); g.restore();
  }
  // стрелка-каракуля: рисуется рукой, на конце наконечник
  function arrow(g, o, lt, d) {
    const p = seg(lt, o.t, o.t + 0.45); if (p <= 0) return;
    pencil(g, o.pts, { id: o.id, d, color: COLORS.ink, w: 3.4, p, screen: true });
    if (p >= 1) {
      const a = o.pts[o.pts.length - 1], b = o.pts[o.pts.length - 3], ang = Math.atan2(a[1] - b[1], a[0] - b[0]);
      [0.5, -0.5].forEach((k, i) => pencil(g, [a, [a[0] - Math.cos(ang + k) * 30, a[1] - Math.sin(ang + k) * 30]], { id: o.id + 'h' + i, d, color: COLORS.ink, w: 3.4, screen: true, sketch: false }));
    }
  }
  // закладка-язычок над верхним краем страницы
  function tab(g, x, color, label, d) {
    const y = PY;
    g.fillStyle = SHADOW; g.fillRect(x + 4, y - 44, 84, 60);
    g.fillStyle = color; g.beginPath(); g.moveTo(x, y + 10); g.lineTo(x, y - 48); g.lineTo(x + 84, y - 48); g.lineTo(x + 84, y + 10); g.fill();
    if (label) hand(g, label, x + 42, y - 14, { id: 'tab' + label, d, size: 36, color: COLORS.white });
  }
  function doodleStars(g, list, lt, d, id) {
    list.forEach(([x, y, r, t], i) => {
      const p = seg(lt, t, t + 0.25); if (p <= 0) return;
      const pts = []; for (let k = 0; k <= 10; k++) { const a = -Math.PI / 2 + k * Math.PI / 5, rr = k % 2 ? r * 0.45 : r; pts.push([x + Math.cos(a) * rr, y + Math.sin(a) * rr]); }
      pencil(g, pts, { id: id + i, d, color: COLORS.ink, w: 2.4, p, screen: true, sketch: false });
    });
  }

  window.JOURNAL = { PX, PY, PW, PH, COLORS, mk, setTooth, makePage, rings, sticker, tape, polaroid, sticky, stamp, marker, arrow, tab, doodleStars };
})();
