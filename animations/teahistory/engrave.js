// Гравюра кодом: тон передаётся толщиной и густотой резцовых линий (как в старых книжных гравюрах).
// Тела вращения штрихуются «по форме» (широтные дуги + меридианы в тени), плоские детали — параллельной
// штриховкой с перекрёстной в тенях. Свет — слева сверху. Рисуется один раз в офскрин (3 варианта для «кипения»).
(function () {
  'use strict';
  const P = window.PENCIL;
  const { rng, smooth, ellipse, pod } = P;
  const sstep = (a, b, x) => { const t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  const INK = '#1d1a17';

  function inPoly(x, y, poly) {
    let c = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const a = poly[i], b = poly[j];
      if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
    }
    return c;
  }
  // сборщик штрихов: группирует сегменты по толщине (быстро рисуется)
  function Ink() { this.bins = new Map(); }
  Ink.prototype.seg = function (x0, y0, x1, y1, w) {
    if (w < 0.3) return;
    const k = Math.round(w * 4) / 4; let p = this.bins.get(k);
    if (!p) { p = new Path2D(); this.bins.set(k, p); }
    p.moveTo(x0, y0); p.lineTo(x1, y1);
  };
  Ink.prototype.flush = function (g, color = INK) {
    g.lineCap = 'round'; g.strokeStyle = color;
    for (const [w, p] of this.bins) { g.lineWidth = w; g.stroke(p); }
    this.bins.clear();
  };

  // параллельная штриховка внутри полигона; ширина линии = тон
  function field(ink, poly, o) {
    const ang = (o.angle || 0) * Math.PI / 180, ca = Math.cos(ang), sa = Math.sin(ang);
    const R = rng(o.seed || 'f', 'field'), sp = o.spacing || 4, step = 2.5, wmax = o.wmax || 2.2, th = o.th === undefined ? 0.2 : o.th;
    let vmin = 1e9, vmax = -1e9, umin = 1e9, umax = -1e9;
    for (const [x, y] of poly) { const u = x * ca + y * sa, v = -x * sa + y * ca; vmin = Math.min(vmin, v); vmax = Math.max(vmax, v); umin = Math.min(umin, u); umax = Math.max(umax, u); }
    for (let v = vmin + sp * R(); v < vmax; v += sp) {
      const ph = R() * 6.28, amp = o.wobble === undefined ? 0.5 : o.wobble, fr = 0.03 + R() * 0.02;
      let prev = null;
      for (let u = umin; u <= umax + step; u += step) {
        const vv = v + amp * Math.sin(u * fr + ph), x = u * ca - vv * sa, y = u * sa + vv * ca;
        if (!inPoly(x, y, poly)) { prev = null; continue; }
        const w = wmax * sstep(th, th + (o.soft || 0.45), o.shade(x, y));
        if (prev && w > 0.3) ink.seg(prev[0], prev[1], x, y, (w + prev[2]) / 2);
        prev = [x, y, w];
      }
    }
  }
  // точки-«пунктир» в полутонах
  function stipple(ink, poly, o) {
    const R = rng(o.seed || 's', 'stip');
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const [x, y] of poly) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
    const n = Math.round((x1 - x0) * (y1 - y0) * (o.density || 0.004));
    for (let i = 0; i < n; i++) {
      const x = x0 + R() * (x1 - x0), y = y0 + R() * (y1 - y0), r = R();
      if (!inPoly(x, y, poly)) continue;
      const s = o.shade(x, y); if (r > s * 0.9) continue;
      ink.seg(x, y, x + 0.6, y + 0.4, 1.4);
    }
  }
  function outline(ink, pts, w, closed, seed) {
    const R = rng(seed || 'o', 'ol');
    const q = closed ? pts.concat([pts[0]]) : pts;
    for (let i = 1; i < q.length; i++) ink.seg(q[i - 1][0], q[i - 1][1], q[i][0], q[i][1], w * (0.85 + 0.3 * R()));
  }
  function fillWhite(g, poly, color = '#fbf8f1') { g.fillStyle = color; g.beginPath(); poly.forEach((p, i) => (i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]))); g.closePath(); g.fill(); }

  // тело вращения: prof = [[y, r], ...] сверху вниз; e — сплющенность эллипсов (перспектива)
  function prof(profile, y) {
    if (y <= profile[0][0]) return profile[0][1];
    for (let i = 1; i < profile.length; i++) if (y <= profile[i][0]) { const a = profile[i - 1], b = profile[i], t = (y - a[0]) / (b[0] - a[0]); return a[1] + (b[1] - a[1]) * t; }
    return profile[profile.length - 1][1];
  }
  function revolve(g, ink, cx, profile0, o = {}) {
    const profile = profile0.length > 2 ? smooth(profile0, 6) : profile0;
    const e = o.e || 0.28, y0 = profile[0][0], y1 = profile[profile.length - 1][0], sp = o.spacing || 4.2, R = rng(o.seed || 'rv', 'rev');
    const sm = [];
    for (let y = y0; y <= y1; y += 2) sm.push([y, prof(profile, y)]);
    const left = sm.map(([y, r]) => [cx - r, y]), right = sm.map(([y, r]) => [cx + r, y]).reverse();
    const rb = prof(profile, y1), bottom = []; for (let k = 0; k <= 24; k++) { const a = Math.PI - k / 24 * Math.PI; bottom.push([cx + Math.cos(a) * rb, y1 + Math.sin(a) * rb * e]); }
    const sil = left.concat(bottom, right);
    const rt = prof(profile, y0);
    if (o.cap !== false) for (let k = 0; k <= 24; k++) { const a = -k / 24 * Math.PI; sil.push([cx + Math.cos(a) * rt, y0 + Math.sin(a) * rt * e]); }
    fillWhite(g, sil);
    const shadeT = th => { const s = 0.5 - 0.5 * Math.cos(th - Math.PI * 0.78); return Math.min(1, s * 1.08 + (o.dark || 0)); };
    // широтные дуги (передняя половина)
    for (let y = y0 + sp * 0.5; y < y1; y += sp) {
      const r = prof(profile, y), slope = (prof(profile, y + 2) - prof(profile, y - 2)) / 4, ph = R() * 6.28;
      let prev = null; const n = Math.max(16, Math.round(r / 2.5));
      for (let k = 0; k <= n; k++) {
        const th = k / n * Math.PI, x = cx + Math.cos(th) * r, yy = y + Math.sin(th) * r * e + 0.35 * Math.sin(k * 0.7 + ph);
        const s = Math.min(1, shadeT(th) + Math.max(0, -slope) * 0.25 + (o.shadeY ? o.shadeY(y) : 0));
        const w = (o.wmax || 2.1) * sstep(0.14, 0.75, s);
        if (prev && w > 0.3) ink.seg(prev[0], prev[1], x, yy, (w + prev[2]) / 2);
        prev = [x, yy, w];
      }
    }
    // меридианы в тени (перекрёстная штриховка)
    for (let th = 0.02; th < Math.PI * 0.5; th += 0.045) {
      const s = shadeT(th); if (s < 0.62) continue;
      let prev = null;
      for (let y = y0 + 2; y <= y1; y += 3) {
        const r = prof(profile, y), x = cx + Math.cos(th) * r, yy = y + Math.sin(th) * r * e, w = 1.6 * sstep(0.62, 0.95, s);
        if (prev) ink.seg(prev[0], prev[1], x, yy, w);
        prev = [x, yy];
      }
    }
    outline(ink, left, 2.6, false, o.seed + 'L'); outline(ink, right, 2.6, false, o.seed + 'R'); outline(ink, bottom, 2.4, false, o.seed + 'B');
    if (o.cap !== false && rt > 6) { // верхняя плоскость: светлая, штрих только справа
      const cap = ellipse(cx, y0, rt, rt * e, 0, 40); fillWhite(g, cap);
      field(ink, cap, { angle: 6, spacing: 4.4, wmax: 1.5, th: 0.35, seed: o.seed + 'cap', shade: (x) => 0.2 + 0.6 * (x - cx + rt) / (2 * rt) });
      outline(ink, cap, 2.2, true, o.seed + 'capo');
    }
    return sil;
  }
  function rim(g, ink, cx, y, r, o = {}) { // верхний край/отверстие: эллипс, внутренность в тени
    const e = o.e || 0.28, el = ellipse(cx, y, r, r * e, 0, 48);
    fillWhite(g, el, o.inner ? '#f4efe4' : '#fbf8f1');
    if (o.inner) field(ink, el, { angle: 8, spacing: 3.6, wmax: 1.8, th: 0.1, seed: o.seed + 'in', shade: (x) => o.inner === 'liquid' ? 0.35 + 0.4 * (x - cx + r) / (2 * r) : 0.75 - 0.5 * (x - cx + r) / (2 * r) });
    outline(ink, el, 2.4, true, o.seed + 'rim');
    return el;
  }
  // плоская деталь: полигон + функция тона
  function part(g, ink, poly, o) {
    if (o.solid) { fillWhite(g, poly, INK); return poly; }
    if (o.white !== false) fillWhite(g, poly);
    field(ink, poly, { angle: o.angle || 0, spacing: o.spacing || 4, wmax: o.wmax || 2, th: o.th, seed: o.seed, shade: o.shade, wobble: o.wobble });
    if (o.cross) field(ink, poly, { angle: (o.angle || 0) + 70, spacing: (o.spacing || 4) * 1.2, wmax: 1.5, th: o.cross, seed: o.seed + 'x', shade: o.shade });
    if (o.outline !== false) outline(ink, poly, o.ow || 2.5, true, o.seed);
    return poly;
  }
  const lin = (x0, y0, x1, y1, a = 0.1, b = 0.9) => (x, y) => { const t = ((x - x0) * (x1 - x0) + (y - y0) * (y1 - y0)) / ((x1 - x0) ** 2 + (y1 - y0) ** 2); return a + (b - a) * Math.max(0, Math.min(1, t)); };
  function leaf(g, ink, base, tip, w, seed) {
    const poly = pod(base, tip, w, 0.85, 22);
    fillWhite(g, poly);
    const dx = tip[0] - base[0], dy = tip[1] - base[1], L = Math.hypot(dx, dy), ang = Math.atan2(dy, dx) * 180 / Math.PI;
    field(ink, poly, { angle: ang + 55, spacing: 3.4, wmax: 1.7, th: 0.25, seed, shade: (x, y) => ((x - base[0]) * -dy + (y - base[1]) * dx) / L > 0 ? 0.85 : 0.25 });
    outline(ink, poly, 2.2, true, seed); ink.seg(base[0], base[1], tip[0], tip[1], 1.5);
    for (let u = 0.2; u < 0.85; u += 0.16) { const m = [base[0] + dx * u, base[1] + dy * u]; [-1, 1].forEach(sd => ink.seg(m[0], m[1], m[0] + dx * 0.13 - dy / L * sd * w * 0.8, m[1] + dy * 0.13 + dx / L * sd * w * 0.8, 1)); }
    return poly;
  }
  function curl(ink, x, y, h, amp, seed, w = 1.6) { // пар/дым
    const R = rng(seed, 'curl'), ph = R() * 6; let prev = null;
    for (let s = 0; s <= h; s += 4) { const xx = x + amp * Math.sin(s * 0.035 + ph) * (s / h), yy = y - s; if (prev) ink.seg(prev[0], prev[1], xx, yy, w * (1 - s / h * 0.7)); prev = [xx, yy]; }
  }

  // ---------- библиотека предметов (рисуют в g, координаты ~0..600) ----------
  const OBJ = {};
  OBJ.cauldron = (g, ink, s) => { // котёл на огне, падают листья
    const sil = [];
    [[200, 470, -0.3], [400, 470, 0.3], [300, 490, 0]].forEach(([x, y, a], i) => sil.push(part(g, ink, [[x - 14, 400], [x + 14, 400], [x + 18 + a * 40, y + 60], [x - 10 + a * 40, y + 60]], { angle: 80, seed: s + 'lg' + i, shade: lin(x - 14, 0, x + 18, 0, 0.3, 0.9) })));
    [[200, 545, 190, 420, 34], [260, 545, 265, 380, 42], [330, 545, 345, 370, 44], [395, 545, 410, 425, 34], [300, 545, 300, 450, 30]].forEach(([bx, by, tx, ty, w], i) => {
      const fl = pod([bx, by], [tx, ty], w, 0.45, 20);
      sil.push(part(g, ink, fl, { angle: 90, spacing: 4, wmax: 1.8, th: 0.15, seed: s + 'fl' + i, shade: (x, y) => 0.2 + 0.8 * (y - ty) / (by - ty) }));
    });
    for (let k = 0; k < 7; k++) { const x = 180 + k * 40, y = 360 - (k % 3) * 25; ink.seg(x, y, x + 3, y - 6, 2); } // искры
    sil.push(part(g, ink, [[150, 540], [450, 540], [470, 575], [130, 575]], { angle: 10, spacing: 3.5, seed: s + 'logs', shade: () => 0.7, cross: 0.6 })); // поленья
    sil.push(revolve(g, ink, 300, [[220, 190], [260, 200], [320, 185], [380, 140], [410, 60]], { seed: s + 'pot', e: 0.26 }));
    rim(g, ink, 300, 220, 190, { seed: s + 'rim', inner: 'liquid', e: 0.26 });
    [[110, 200], [490, 200]].forEach(([x, y], i) => { const ear = [[x - 18, y], [x + 18, y], [x + 22, y - 70], [x - 22, y - 70]]; sil.push(part(g, ink, ear, { angle: 85, seed: s + 'ear' + i, shade: lin(x - 22, 0, x + 22, 0, 0.2, 0.85) })); fillWhite(g, [[x - 8, y - 12], [x + 8, y - 12], [x + 10, y - 56], [x - 10, y - 56]], '#f4efe4'); });
    sil.push(leaf(g, ink, [250, 222], [330, 210], 18, s + 'lf0'));
    [[[90, 40], [150, 90]], [[470, 70], [520, 140]], [[380, 20], [420, 80]]].forEach(([a, b], i) => sil.push(leaf(g, ink, a, b, 14, s + 'lf' + (i + 1))));
    curl(ink, 260, 200, 140, 18, s + 'st1'); curl(ink, 330, 200, 170, 22, s + 'st2');
    return sil;
  };
  OBJ.book = (g, ink, s) => { // раскрытая книга, кисть, тушечница
    const sil = [];
    const L = [[300, 150], [80, 110], [40, 400], [300, 430]], Rp = [[300, 150], [520, 110], [560, 400], [300, 430]];
    [L, Rp].forEach((pg, i) => {
      sil.push(part(g, ink, pg, { angle: i ? 98 : 82, spacing: 6, wmax: 1, th: 0.55, seed: s + 'pg' + i, shade: (x) => 0.3 + 0.6 * (1 - Math.abs(x - 300) / 260) }));
      for (let c = 0; c < 6; c++) { // колонки иероглифов
        const t = (c + 0.6) / 7, xTop = i ? 300 + t * 220 : 300 - t * 220, xBot = i ? 300 + t * 260 : 300 - t * 260;
        for (let k = 0; k < 10; k++) { const u = 0.12 + k * 0.075, x = xTop + (xBot - xTop) * u, y = 150 - 30 * t + u * 290; ink.seg(x - 5, y, x + 5, y, 1.6); ink.seg(x, y - 4, x, y + 6, 1.4); }
      }
    });
    ink.seg(300, 150, 300, 430, 2.8);
    sil.push(part(g, ink, [[60, 420], [540, 420], [560, 440], [40, 440]], { angle: 0, spacing: 3, wmax: 1.4, th: 0, seed: s + 'edge', shade: () => 0.6 }));
    const br = [[380, 470], [560, 380], [570, 395], [392, 486]]; sil.push(part(g, ink, br, { angle: -27, spacing: 3.5, seed: s + 'br', shade: lin(380, 470, 392, 486, 0.2, 0.9) }));
    sil.push(part(g, ink, pod([392, 478], [340, 510], 12, 0.5, 12), { angle: 60, spacing: 3, seed: s + 'tip', shade: () => 0.9 }));
    const ink2 = [[80, 470], [250, 470], [250, 540], [80, 540]]; sil.push(part(g, ink, ink2, { angle: 15, spacing: 3.6, seed: s + 'is', shade: lin(80, 0, 250, 0, 0.35, 0.95), cross: 0.7 }));
    rim(g, ink, 165, 492, 60, { seed: s + 'well', inner: 'well', e: 0.3 });
    return sil;
  };
  OBJ.bowl = (g, ink, s) => { // чаша цзянь и бамбуковый венчик
    const sil = [];
    sil.push(revolve(g, ink, 230, [[300, 200], [340, 196], [400, 160], [450, 100], [470, 70]], { seed: s + 'bw', dark: 0.25 }));
    rim(g, ink, 230, 300, 200, { seed: s + 'brim', inner: 'liquid', e: 0.3 });
    for (let k = 0; k < 16; k++) { const a = Math.PI * (0.1 + k * 0.05), x = 230 + Math.cos(a) * 190; ink.seg(x, 330 + Math.sin(a) * 40, 230 + Math.cos(a) * 120, 420, 1.2); } // «заячий мех»
    sil.push(revolve(g, ink, 230, [[470, 90], [490, 120]], { seed: s + 'foot' }));
    const hx = 470; sil.push(part(g, ink, [[hx - 22, 60], [hx + 22, 60], [hx + 22, 200], [hx - 22, 200]], { angle: 90, spacing: 3.5, seed: s + 'wh', shade: lin(hx - 22, 0, hx + 22, 0, 0.15, 0.9) }));
    const tines = []; for (let k = 0; k <= 22; k++) { const t = k / 22, a = -0.9 + t * 1.8; const p0 = [hx + Math.sin(a) * 20, 200], p1 = [hx + Math.sin(a) * 70, 330 - Math.cos(a) * 20]; ink.seg(p0[0], p0[1], (p0[0] + p1[0]) / 2 + Math.sin(a) * 14, 270, 1.3); ink.seg((p0[0] + p1[0]) / 2 + Math.sin(a) * 14, 270, p1[0], p1[1], 1.3); tines.push(p1); }
    sil.push([[hx - 24, 195], [hx + 24, 195]].concat(tines.slice().reverse()));
    return sil;
  };
  OBJ.teapot = (g, ink, s) => { // исинский чайник
    const sil = [];
    const sp = [[160, 340], [120, 280], [62, 196], [34, 168], [58, 156], [92, 186], [160, 262], [185, 300]];
    sil.push(part(g, ink, sp, { angle: -40, spacing: 3.6, seed: s + 'sp', shade: lin(40, 180, 170, 300, 0.3, 0.85) }));
    const hd = []; for (let k = 0; k <= 30; k++) { const a = -Math.PI / 2 + k / 30 * Math.PI; hd.push([430 + Math.cos(a) * 110, 290 + Math.sin(a) * 100]); }
    const hdIn = hd.map(([x, y]) => [430 + (x - 430) * 0.62, 290 + (y - 290) * 0.55]).reverse();
    sil.push(part(g, ink, hd.concat(hdIn), { angle: 20, spacing: 3.5, seed: s + 'hd', shade: lin(430, 0, 540, 0, 0.3, 0.95), cross: 0.75 }));
    sil.push(revolve(g, ink, 300, [[200, 160], [240, 190], [300, 200], [360, 180], [400, 140], [420, 120]], { seed: s + 'body', dark: 0.12 }));
    sil.push(revolve(g, ink, 300, [[150, 120], [190, 130], [205, 160]], { seed: s + 'lid' }));
    sil.push(revolve(g, ink, 300, [[115, 22], [140, 28], [152, 18]], { seed: s + 'knob' }));
    return sil;
  };
  OBJ.compass = (g, ink, s) => { // роза ветров
    const sil = [], c = [300, 300];
    const ring = ellipse(300, 300, 230, 230, 0, 72); fillWhite(g, ring); outline(ink, ring, 3, true, s + 'r1'); outline(ink, ellipse(300, 300, 205, 205, 0, 72), 1.6, true, s + 'r2');
    for (let k = 0; k < 72; k++) { const a = k / 72 * Math.PI * 2, r0 = k % 9 === 0 ? 180 : 195; ink.seg(300 + Math.cos(a) * r0, 300 + Math.sin(a) * r0, 300 + Math.cos(a) * 205, 300 + Math.sin(a) * 205, 1.2); }
    sil.push(ring);
    for (let k = 0; k < 8; k++) {
      const a = k / 8 * Math.PI * 2 - Math.PI / 2, L = k % 2 ? 120 : 200, wd = k % 2 ? 22 : 34;
      const tip = [300 + Math.cos(a) * L, 300 + Math.sin(a) * L], l = [300 + Math.cos(a - Math.PI / 2) * wd, 300 + Math.sin(a - Math.PI / 2) * wd], r = [300 + Math.cos(a + Math.PI / 2) * wd, 300 + Math.sin(a + Math.PI / 2) * wd];
      part(g, ink, [c, l, tip], { solid: true }); part(g, ink, [c, tip, r], { seed: s + 'b' + k, shade: () => 0.05 });
    }
    return sil;
  };
  OBJ.samovar = (g, ink, s) => { // тульский самовар
    const sil = [];
    [[-1, 230], [1, 370]].forEach(([d, x], i) => sil.push(part(g, ink, [[x - 10, 540], [x + 10, 540], [x + 20 * d + 10, 590], [x + 20 * d - 10, 590]], { angle: 80, spacing: 3.5, seed: s + 'leg' + i, shade: () => 0.7 })));
    sil.push(revolve(g, ink, 300, [[500, 70], [530, 110], [545, 120]], { seed: s + 'base' }));
    sil.push(revolve(g, ink, 300, [[470, 40], [500, 70]], { seed: s + 'neck' }));
    sil.push(revolve(g, ink, 300, [[230, 140], [280, 175], [360, 185], [430, 160], [470, 110]], { seed: s + 'body', dark: 0.05 }));
    for (let k = 0; k < 5; k++) { // медали на «груди» самовара
      const th = Math.PI * (0.32 + k * 0.09), mx = 300 + Math.cos(th) * 176, my = 300 + Math.sin(th) * 176 * 0.28 - 8, rx = 15 * Math.sin(th);
      const m = ellipse(mx, my, rx, 15, 0, 28); fillWhite(g, m); outline(ink, m, 1.8, true, s + 'md' + k);
      outline(ink, ellipse(mx, my, rx * 0.62, 9, 0, 20), 1.1, true, s + 'mi' + k); ink.seg(mx - 0.8, my, mx + 0.8, my, 3);
    }
    sil.push(revolve(g, ink, 300, [[200, 110], [230, 140]], { seed: s + 'shoulder' }));
    sil.push(revolve(g, ink, 300, [[150, 55], [200, 60]], { seed: s + 'crown' }));
    // кран: труба, вентиль, носик
    sil.push(part(g, ink, [[126, 318], [62, 318], [62, 334], [126, 334]], { angle: 0, spacing: 3, seed: s + 'tap', shade: (x, y) => 0.25 + 0.65 * (y - 318) / 16 }));
    sil.push(part(g, ink, [[62, 320], [48, 326], [46, 362], [58, 368], [64, 350], [64, 330]], { angle: 90, spacing: 3, seed: s + 'tap2', shade: (x) => 0.3 + 0.6 * (x - 46) / 18 }));
    sil.push(part(g, ink, ellipse(84, 308, 7, 12, 0, 20), { angle: 90, spacing: 2.6, seed: s + 'vk', shade: (x) => 0.3 + 0.6 * (x - 77) / 14 }));
    sil.push(part(g, ink, ellipse(84, 294, 20, 6, 0, 24), { angle: 0, spacing: 2.6, seed: s + 'vk2', shade: (x, y) => 0.2 + 0.6 * (y - 288) / 12 }));
    // ручки: металлические кронштейны + деревянные рукояти-«бочонки»
    [[142, 250, -1], [458, 250, 1]].forEach(([x, y, dd], i) => {
      const gx = x + 44 * dd;
      [-16, 16].forEach((oy, j) => sil.push(part(g, ink, [[x, y + oy - 3], [gx, y + oy - 3], [gx, y + oy + 3], [x, y + oy + 3]], { angle: 0, spacing: 2.4, seed: s + 'st' + i + j, shade: () => 0.6, ow: 1.6 })));
      sil.push(part(g, ink, ellipse(gx, y, 13, 40, 0, 32), { angle: 90, spacing: 2.8, wmax: 2.2, seed: s + 'h' + i, shade: (px) => 0.25 + 0.7 * (px - gx + 13) / 26 + (i ? 0.15 : 0) }));
      outline(ink, [[gx - 12, y - 22], [gx + 12, y - 22]], 1.4, false, s + 'r1' + i); outline(ink, [[gx - 12, y + 22], [gx + 12, y + 22]], 1.4, false, s + 'r2' + i);
    });
    sil.push(revolve(g, ink, 300, [[40, 80], [80, 95], [130, 85], [150, 60]], { seed: s + 'pot' })); // заварочный чайник сверху
    sil.push(part(g, ink, [[380, 80], [450, 50], [460, 60], [395, 100]], { angle: -25, spacing: 3, seed: s + 'psp', shade: () => 0.7 }));
    sil.push(revolve(g, ink, 300, [[10, 18], [40, 30]], { seed: s + 'pk' }));
    return sil;
  };
  OBJ.cup = (g, ink, s) => { // чашка с блюдцем и паром
    const sil = [];
    sil.push(revolve(g, ink, 280, [[440, 250], [470, 230]], { seed: s + 'sau', e: 0.22 }));
    rim(g, ink, 280, 440, 250, { seed: s + 'saurim', e: 0.22, inner: 'well' });
    const hd = []; for (let k = 0; k <= 26; k++) { const a = -Math.PI / 2 + k / 26 * Math.PI; hd.push([420 + Math.cos(a) * 70, 330 + Math.sin(a) * 60]); }
    sil.push(part(g, ink, hd.concat(hd.map(([x, y]) => [420 + (x - 420) * 0.55, 330 + (y - 330) * 0.5]).reverse()), { angle: 20, spacing: 3.4, seed: s + 'hd', shade: () => 0.7 }));
    sil.push(revolve(g, ink, 280, [[260, 160], [330, 155], [400, 130], [440, 100]], { seed: s + 'cup', e: 0.25 }));
    rim(g, ink, 280, 260, 160, { seed: s + 'crim', inner: 'liquid', e: 0.25 });
    curl(ink, 240, 220, 190, 26, s + 's1'); curl(ink, 300, 210, 220, 30, s + 's2'); curl(ink, 340, 225, 160, 20, s + 's3');
    sil.push(leaf(g, ink, [470, 470], [560, 430], 20, s + 'leaf'));
    return sil;
  };

  // рендер предмета: 3 варианта (кипение) + силуэты для белой высечки
  function render(name, size = 600) {
    const vars = [], sil0 = [];
    for (let v = 0; v < 3; v++) {
      const c = document.createElement('canvas'); c.width = c.height = size; const g = c.getContext('2d');
      g.save(); g.scale(size / 600, size / 600);
      const ink = new Ink(), sil = OBJ[name](g, ink, name + 'v' + v);
      ink.flush(g); g.restore();
      if (v === 0) sil.forEach(p => sil0.push(p.map(([x, y]) => [x * size / 600, y * size / 600])));
      vars.push(c);
    }
    return { vars, sil: sil0, size };
  }

  window.ENGRAVE = { render, OBJ, Ink, field, revolve, part, leaf, outline, INK };
})();
