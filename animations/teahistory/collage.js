// Коллаж: заголовки из вырезанных букв, ярлыки глав, гравюры-вырезки с белой каймой, документы на скотче,
// машинопись, марки, билеты, печати. Всё появляется один раз своей короткой анимацией (моушн-графика), дальше
// статично; «живут» только варианты гравюры (кипение) и лёгкий наезд камеры.
(function () {
  'use strict';
  const P = window.PENCIL;
  const { rng, seg, lerp, easeOut, easeIO, pencil, hand, ellipse } = P;
  const SH = 'rgba(25,20,15,0.32)';
  const RANSOM_FONTS = ['R_Oswald', 'R_Playfair', 'R_RubikMono', 'R_Russo', 'R_Yeseva', 'R_Ruslan', 'R_Lobster', 'R_Unbounded', 'R_Kelly', 'R_Plex', 'R_Alice', 'R_Prata', 'R_Cormorant'];
  const PAPERS = [['#f4f1ea', '#1b1916'], ['#1b1916', '#f4f1ea'], ['#b8322a', '#f7efe2'], ['#c9a77a', '#1b1916'], ['#e9d48a', '#1b1916'], ['#d9d6cf', '#1b1916'], ['#f4f1ea', '#b8322a'], ['#2e4a63', '#f4f1ea']];
  const mk = (w, h) => { const c = document.createElement('canvas'); c.width = Math.ceil(w); c.height = Math.ceil(h); return c; };
  const backOut = u => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(u - 1, 3) + c1 * Math.pow(u - 1, 2); };

  // ---------- заголовок из вырезанных букв ----------
  const ransomCache = new Map();
  function ransomLayout(g, text, o) {
    const key = o.id + text; if (ransomCache.has(key)) return ransomCache.get(key);
    const R = rng(o.id, 'ransom'), words = text.split(' '), lines = [[]], size = o.size || 120, maxW = o.maxW || 960;
    let lineW = 0;
    const glyphs = [];
    words.forEach((w, wi) => {
      const ws = [];
      for (const ch of w) {
        const font = RANSOM_FONTS[Math.floor(R() * RANSOM_FONTS.length)], pp = PAPERS[Math.floor(R() * PAPERS.length)];
        const sz = size * (0.82 + R() * 0.3);
        g.font = `${sz}px ${font}`; const cw = g.measureText(ch).width;
        const padX = 10 + R() * 8, padY = 8 + R() * 10, w2 = cw + padX * 2, h2 = sz * 0.95 + padY * 2;
        const corners = [[-w2 / 2 + R() * 6, -h2 / 2 + R() * 6], [w2 / 2 - R() * 6, -h2 / 2 + R() * 6], [w2 / 2 - R() * 6, h2 / 2 - R() * 6], [-w2 / 2 + R() * 6, h2 / 2 - R() * 6]];
        ws.push({ ch, font, sz, bg: pp[0], fg: pp[1], w: w2, h: h2, rot: (R() - 0.5) * 0.24, dy: (R() - 0.5) * 18, corners });
      }
      const wW = ws.reduce((a, q) => a + q.w * 0.92, 0);
      if (lineW + wW > maxW && lines[lines.length - 1].length) { lines.push([]); lineW = 0; }
      if (lines[lines.length - 1].length) lines[lines.length - 1].push(null);
      ws.forEach(q => lines[lines.length - 1].push(q)); lineW += wW + size * 0.35;
    });
    const out = []; let idx = 0;
    lines.forEach((ln, li) => {
      const W = ln.reduce((a, q) => a + (q ? q.w * 0.92 : size * 0.35), 0);
      let x = o.x - W / 2;
      ln.forEach(q => { if (!q) { x += size * 0.35; return; } out.push(Object.assign({}, q, { cx: x + q.w * 0.46, cy: o.y + li * size * 1.25 + q.dy, i: idx++ })); x += q.w * 0.92; });
    });
    ransomCache.set(key, out); return out;
  }
  function ransom(g, text, lt, o) {
    const L = ransomLayout(g, text, o);
    L.forEach(q => {
      const u = seg(lt, o.t + q.i * (o.step || 0.06), o.t + q.i * (o.step || 0.06) + 0.16); if (u <= 0) return;
      const s = lerp(1.5, 1, backOut(u)), r = q.rot + (1 - u) * 0.4;
      g.save(); g.translate(q.cx, q.cy); g.rotate(r); g.scale(s, s);
      const path = (dx = 0, dy = 0) => { g.beginPath(); q.corners.forEach((c, k) => (k ? g.lineTo(c[0] + dx, c[1] + dy) : g.moveTo(c[0] + dx, c[1] + dy))); g.closePath(); };
      path(5, 7); g.fillStyle = SH; g.fill();
      path(); g.fillStyle = q.bg; g.fill();
      g.fillStyle = q.fg; g.font = `${q.sz}px ${q.font}`; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(q.ch, 0, q.sz * 0.04);
      g.restore();
    });
  }

  // ---------- ярлык главы: бумажная полоска въезжает слева ----------
  function label(g, text, x, y, lt, o) {
    const u = easeOut(seg(lt, o.t, o.t + 0.35)); if (u <= 0) return;
    g.font = '600 52px R_Oswald'; const w = g.measureText(text).width + 80, h = 92, xx = lerp(-w - 40, x, u);
    g.save(); g.translate(xx, y); g.rotate(-0.02);
    g.fillStyle = SH; g.fillRect(5, 7, w, h); g.fillStyle = '#f6f3ec'; g.fillRect(0, 0, w, h);
    g.fillStyle = '#1b1916'; g.textBaseline = 'middle'; g.fillText(text, 40, h / 2 + 3);
    g.restore();
    tape(g, { a: [xx + w - 40, y - 10], b: [xx + w + 40, y + 40], color: '#d9cfb8', w: 40 }, 1);
  }

  // скотч (бумажный/малярный): полупрозрачная полоска с зубчатыми краями
  function tape(g, o, u0 = 1) {
    const u = u0; if (u <= 0) return;
    const [x0, y0] = o.a, x1 = lerp(x0, o.b[0], u), y1 = lerp(y0, o.b[1], u), Lx = Math.hypot(x1 - x0, y1 - y0), ang = Math.atan2(y1 - y0, x1 - x0), w = o.w || 50;
    const R = rng(o.id || 'tp' + x0 + y0, 'tape');
    g.save(); g.translate(x0, y0); g.rotate(ang);
    const n = 6, e1 = [], e2 = [];
    for (let i = 0; i <= n; i++) { e1.push([(i % 2 ? 5 : 0) + R() * 3, -w / 2 + i * w / n]); e2.push([Lx - (i % 2 ? 5 : 0) - R() * 3, -w / 2 + i * w / n]); }
    g.beginPath(); e1.concat(e2.reverse()).forEach((q, i) => (i ? g.lineTo(q[0], q[1]) : g.moveTo(q[0], q[1]))); g.closePath();
    g.fillStyle = o.color || '#e6dcc4'; g.globalAlpha = 0.82; g.fill(); g.globalAlpha = 1;
    g.restore();
  }

  // ---------- гравюра-вырезка: белая высечка по силуэту, тень, «падает» на лист ----------
  const cutCache = new Map();
  function cutoutBase(eng, key) {
    if (cutCache.has(key)) return cutCache.get(key);
    const m = 30, S = eng.size + m * 2, base = mk(S, S), shadow = mk(S, S);
    [base, shadow].forEach((c, k) => {
      const g = c.getContext('2d'); g.translate(m, m); g.lineJoin = 'round'; g.lineWidth = 34;
      g.fillStyle = g.strokeStyle = k ? 'rgba(25,20,15,1)' : '#fbf8f1';
      eng.sil.forEach(poly => { g.beginPath(); poly.forEach((p, i) => (i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]))); g.closePath(); g.fill(); g.stroke(); });
    });
    const out = { base, shadow, m, S }; cutCache.set(key, out); return out;
  }
  function cutout(g, eng, key, x, y, lt, d, o) {
    const u = seg(lt, o.t, o.t + 0.32); if (u <= 0) return;
    const c = cutoutBase(eng, key), sc = (o.scale || 1) * lerp(1.15, 1, backOut(u)), r = (o.rot || 0) + (1 - u) * 0.12, dy = -80 * (1 - easeOut(u));
    g.save(); g.translate(x, y + dy); g.rotate(r); g.scale(sc, sc);
    g.globalAlpha = 0.3; g.drawImage(c.shadow, -c.S / 2 + 10, -c.S / 2 + 14); g.globalAlpha = 1;
    g.drawImage(c.base, -c.S / 2, -c.S / 2);
    g.drawImage(eng.vars[Math.floor(d / 2) % 3], -c.S / 2 + c.m, -c.S / 2 + c.m); // кипение: смена варианта 6 раз/с
    g.restore();
  }

  // ---------- документ: старая бумага, рваные края, скотч по углам ----------
  const docCache = new Map();
  function doc(g, o, lt, d) {
    const u = seg(lt, o.t, o.t + 0.3); if (u <= 0) return;
    let c = docCache.get(o.id);
    if (!c) {
      c = mk(o.w + 20, o.h + 20); const b = c.getContext('2d'), R = rng(o.id, 'doc'), pts = [];
      const edge = (x0, y0, x1, y1, n) => { for (let i = 0; i < n; i++) { const t = i / n; pts.push([10 + lerp(x0, x1, t) + (R() - 0.5) * (y0 === y1 ? 0 : 7), 10 + lerp(y0, y1, t) + (R() - 0.5) * (x0 === x1 ? 0 : 7)]); } };
      edge(0, 0, o.w, 0, 30); edge(o.w, 0, o.w, o.h, 40); edge(o.w, o.h, 0, o.h, 30); edge(0, o.h, 0, 0, 40);
      b.beginPath(); pts.forEach((p, i) => (i ? b.lineTo(p[0], p[1]) : b.moveTo(p[0], p[1]))); b.closePath();
      b.fillStyle = o.paper || '#eadcb8'; b.fill(); b.save(); b.clip();
      for (let i = 0; i < 40; i++) { const x = R() * o.w, y = R() * o.h, r = 20 + R() * 80, gr = b.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, 'rgba(140,100,50,0.10)'); gr.addColorStop(1, 'rgba(140,100,50,0)'); b.fillStyle = gr; b.fillRect(0, 0, c.width, c.height); }
      const vg = b.createRadialGradient(c.width / 2, c.height / 2, Math.min(o.w, o.h) * 0.3, c.width / 2, c.height / 2, Math.max(o.w, o.h) * 0.75);
      vg.addColorStop(0, 'rgba(120,80,30,0)'); vg.addColorStop(1, 'rgba(120,80,30,0.28)'); b.fillStyle = vg; b.fillRect(0, 0, c.width, c.height);
      b.translate(10, 10); o.draw(b, o.w, o.h); b.restore();
      docCache.set(o.id, c);
    }
    const s = lerp(1.1, 1, easeOut(u)), r = (o.rot || 0) + (1 - u) * 0.1;
    g.save(); g.translate(o.x, o.y - 40 * (1 - easeOut(u))); g.rotate(r); g.scale(s, s);
    g.fillStyle = SH; g.fillRect(-o.w / 2 + 8, -o.h / 2 + 12, o.w, o.h);
    g.drawImage(c, -c.width / 2, -c.height / 2);
    g.restore();
    if (u >= 1 && o.tapes !== false) {
      const c0 = Math.cos(o.rot || 0), s0 = Math.sin(o.rot || 0), at = (x, y) => [o.x + x * c0 - y * s0, o.y + x * s0 + y * c0];
      const tl = at(-o.w / 2 + 10, -o.h / 2 + 5), tr = at(o.w / 2 - 10, -o.h / 2 + 5);
      const ut = seg(lt, o.t + 0.3, o.t + 0.5);
      tape(g, { id: o.id + 't1', a: [tl[0] - 45, tl[1] - 25], b: [tl[0] + 45, tl[1] + 25], color: o.tape || '#e6dcc4' }, ut);
      tape(g, { id: o.id + 't2', a: [tr[0] - 45, tr[1] + 25], b: [tr[0] + 45, tr[1] - 25], color: o.tape || '#e6dcc4' }, ut);
    }
  }

  // ---------- машинопись: текст печатается по буквам на бумажных полосках ----------
  function typed(g, lines, x, y, lt, o) {
    const size = o.size || 46, lh = size * 1.45; let t = o.t;
    g.font = `${size}px R_Mono`;
    lines.forEach((ln, i) => {
      const n = Math.max(0, Math.min(ln.length, Math.floor((lt - t) * o.cps)));
      if (lt >= t) {
        const full = g.measureText(ln).width, yy = y + i * lh;
        g.save(); g.translate(x, yy); g.rotate(((i * 37) % 5 - 2) * 0.004);
        g.fillStyle = SH; g.fillRect(-12 + 4, -size * 0.85 + 5, full + 24, size * 1.2);
        g.fillStyle = '#f7f4ec'; g.fillRect(-12, -size * 0.85, full + 24, size * 1.2);
        g.fillStyle = '#1b1916'; g.font = `${size}px R_Mono`; g.fillText(ln.slice(0, n), 0, 0);
        if (n < ln.length && Math.floor(lt * 4) % 2) { const cw = g.measureText(ln.slice(0, n)).width; g.fillRect(cw + 2, -size * 0.7, size * 0.5, size * 0.85); } // каретка
        g.restore();
      }
      t += ln.length / o.cps + 0.1;
    });
  }

  // ---------- почтовая марка: зубчатый край ----------
  function postage(g, o, lt, d) {
    const u = seg(lt, o.t, o.t + 0.2); if (u <= 0) return;
    const s = lerp(1.4, 1, backOut(u)), w = o.w, h = o.h, r = 7;
    g.save(); g.translate(o.x, o.y); g.rotate(o.rot + (1 - u) * 0.3); g.scale(s, s);
    const path = (dx = 0, dy = 0) => {
      g.beginPath(); g.rect(-w / 2 + dx, -h / 2 + dy, w, h);
      for (let x = -w / 2 + r; x < w / 2; x += r * 2.2) { g.moveTo(x + dx + r, -h / 2 + dy); g.arc(x + dx, -h / 2 + dy, r, 0, Math.PI * 2); g.moveTo(x + dx + r, h / 2 + dy); g.arc(x + dx, h / 2 + dy, r, 0, Math.PI * 2); }
      for (let y = -h / 2 + r; y < h / 2; y += r * 2.2) { g.moveTo(-w / 2 + dx + r, y + dy); g.arc(-w / 2 + dx, y + dy, r, 0, Math.PI * 2); g.moveTo(w / 2 + dx + r, y + dy); g.arc(w / 2 + dx, y + dy, r, 0, Math.PI * 2); }
    };
    g.fillStyle = SH; path(5, 7); g.fill('evenodd');
    g.fillStyle = '#f6f2e8'; path(); g.fill('evenodd');
    g.fillStyle = o.color || '#2e4a63'; g.fillRect(-w / 2 + 16, -h / 2 + 16, w - 32, h - 32);
    if (o.draw) o.draw(g, w - 32, h - 32);
    g.restore();
  }
  // ---------- билет/бирка ----------
  function ticket(g, o, lt) {
    const u = seg(lt, o.t, o.t + 0.25); if (u <= 0) return;
    const s = lerp(1.2, 1, backOut(u)), w = o.w, h = o.h;
    g.save(); g.translate(o.x, o.y); g.rotate(o.rot + (1 - u) * 0.2); g.scale(s, s);
    const path = (dx = 0, dy = 0) => { g.beginPath(); g.moveTo(-w / 2 + dx, -h / 2 + dy); g.lineTo(w / 2 + dx, -h / 2 + dy); g.lineTo(w / 2 + dx, -14 + dy); g.arc(w / 2 + dx, dy, 14, -Math.PI / 2, Math.PI / 2, true); g.lineTo(w / 2 + dx, h / 2 + dy); g.lineTo(-w / 2 + dx, h / 2 + dy); g.lineTo(-w / 2 + dx, 14 + dy); g.arc(-w / 2 + dx, dy, 14, Math.PI / 2, -Math.PI / 2, true); g.closePath(); };
    g.fillStyle = SH; path(5, 7); g.fill(); g.fillStyle = o.bg || '#e9d48a'; path(); g.fill();
    g.setLineDash([8, 6]); g.strokeStyle = o.fg ? 'rgba(246,242,232,0.55)' : 'rgba(30,25,20,0.5)'; g.lineWidth = 2; g.strokeRect(-w / 2 + 14, -h / 2 + 12, w - 28, h - 24); g.setLineDash([]);
    g.fillStyle = o.fg || '#1b1916'; g.textAlign = 'center'; g.textBaseline = 'middle';
    o.lines.forEach((ln, i) => { g.font = i ? `${o.size2 || 34}px R_Mono` : `${o.size || 54}px R_Oswald`; g.fillText(ln, 0, (i - (o.lines.length - 1) / 2) * (o.size || 54) * 0.95); });
    g.restore();
  }
  // ---------- красная печать (тушь) ----------
  function seal(g, o, lt, tooth) {
    const u = seg(lt, o.t, o.t + 0.12); if (u <= 0) return;
    const s = lerp(1.35, 1, easeOut(u)), S = o.size;
    g.save(); g.translate(o.x, o.y); g.rotate(o.rot || 0); g.scale(s, s); g.globalAlpha = 0.86;
    g.strokeStyle = '#b8322a'; g.lineWidth = 8; g.strokeRect(-S, -S, 2 * S, 2 * S);
    g.fillStyle = '#b8322a'; g.textAlign = 'center'; g.textBaseline = 'middle';
    const ch = o.chars;
    if (ch.length === 2) { g.font = `${S * 0.86}px Glyph`; g.fillText(ch[0], 0, -S * 0.44); g.fillText(ch[1], 0, S * 0.5); }
    else { g.font = `${S * 1.45}px Glyph`; g.fillText(ch, 0, S * 0.06); }
    g.restore();
  }
  // ---------- рукописная пометка со стрелкой ----------
  function scribble(g, o, lt, d) {
    hand(g, o.text, o.x, o.y, { id: o.id, d, size: o.size || 56, color: o.color || '#b8322a', p: seg(lt, o.t, o.t + 0.5) });
    if (o.arrow) {
      const p = seg(lt, o.t + 0.4, o.t + 0.8); if (p <= 0) return;
      pencil(g, o.arrow, { id: o.id + 'a', d, color: o.color || '#b8322a', w: 3.6, p, screen: true });
      if (p >= 1) { const a = o.arrow[o.arrow.length - 1], b = o.arrow[o.arrow.length - 3], an = Math.atan2(a[1] - b[1], a[0] - b[0]); [0.5, -0.5].forEach((k, i) => pencil(g, [a, [a[0] - Math.cos(an + k) * 28, a[1] - Math.sin(an + k) * 28]], { id: o.id + 'h' + i, d, color: o.color || '#b8322a', w: 3.6, screen: true, sketch: false })); }
    }
  }

  // обрывок газеты: рваные края, колонки «текста», заголовок, растровая картинка
  function newsprint(g, x, y, w, h, rot, seed) {
    const R = rng(seed, 'news'), pts = [];
    const edge = (x0, y0, x1, y1, n, j) => { for (let i = 0; i < n; i++) { const t = i / n; pts.push([lerp(x0, x1, t) + (R() - 0.5) * j, lerp(y0, y1, t) + (R() - 0.5) * j]); } };
    edge(-w / 2, -h / 2, w / 2, -h / 2, 24, 9); edge(w / 2, -h / 2, w / 2, h / 2, 24, 9); edge(w / 2, h / 2, -w / 2, h / 2, 24, 9); edge(-w / 2, h / 2, -w / 2, -h / 2, 24, 9);
    g.save(); g.translate(x, y); g.rotate(rot);
    g.beginPath(); pts.forEach((p, i) => (i ? g.lineTo(p[0] + 5, p[1] + 7) : g.moveTo(p[0] + 5, p[1] + 7))); g.closePath(); g.fillStyle = 'rgba(25,20,15,0.22)'; g.fill();
    g.beginPath(); pts.forEach((p, i) => (i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]))); g.closePath(); g.fillStyle = '#e7e3d9'; g.fill();
    g.save(); g.clip();
    g.fillStyle = '#2b2824'; g.fillRect(-w / 2 + 20, -h / 2 + 20, w * (0.5 + R() * 0.4), 26);
    const cols = Math.max(2, Math.floor(w / 140)), cw = (w - 40) / cols;
    for (let c = 0; c < cols; c++) for (let yy = -h / 2 + 70; yy < h / 2 - 10; yy += 13) { if (R() < 0.08) continue; g.fillStyle = 'rgba(40,36,32,0.55)'; g.fillRect(-w / 2 + 20 + c * cw, yy, (cw - 16) * (R() < 0.15 ? 0.5 : 0.95), 5); }
    if (R() < 0.7) { const ix = -w / 2 + 20 + Math.floor(R() * cols) * cw, iy = -h / 2 + 70; g.fillStyle = '#e7e3d9'; g.fillRect(ix, iy, cw - 16, h * 0.35);
      for (let yy = 0; yy < h * 0.35; yy += 7) for (let xx = 0; xx < cw - 16; xx += 7) { const r = 3 * (0.5 + 0.5 * Math.sin(xx * 0.05 + yy * 0.03 + R())); g.fillStyle = '#3a3631'; g.beginPath(); g.arc(ix + xx, iy + yy, r * 0.8, 0, 7); g.fill(); } }
    g.restore(); g.restore();
  }
  function stain(g, x, y, r, seed) { // кольцо от чашки
    const R = rng(seed, 'stain'); g.save(); g.strokeStyle = 'rgba(120,80,40,0.16)';
    for (let k = 0; k < 3; k++) { g.lineWidth = 4 + R() * 6; g.beginPath(); g.arc(x + R() * 4, y + R() * 4, r * (0.96 + R() * 0.06), R() * 6, R() * 6 + 5.2); g.stroke(); }
    g.fillStyle = 'rgba(120,80,40,0.05)'; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); g.restore();
  }
  function clip(g, x, y, rot) { // скрепка
    g.save(); g.translate(x, y); g.rotate(rot); g.lineCap = 'round';
    const pth = () => { g.beginPath(); g.moveTo(0, 60); g.lineTo(0, -40); g.arc(14, -40, 14, Math.PI, 0); g.lineTo(28, 50); g.arc(18, 50, 10, 0, Math.PI); g.lineTo(8, -30); };
    g.strokeStyle = 'rgba(25,20,15,0.3)'; g.lineWidth = 6; g.translate(3, 4); pth(); g.stroke(); g.translate(-3, -4);
    g.strokeStyle = '#8f8a83'; g.lineWidth = 5; pth(); g.stroke(); g.strokeStyle = '#d8d4cc'; g.lineWidth = 1.6; pth(); g.stroke(); g.restore();
  }
  function reset() { ransomCache.clear(); docCache.clear(); } // после загрузки шрифтов пересчитать раскладку
  window.COLLAGE = { newsprint, stain, clip, reset, ransom, label, tape, cutout, doc, typed, postage, ticket, seal, scribble, mk, SH };
})();
