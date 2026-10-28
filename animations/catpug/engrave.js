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
  const loop = (pts, n = 8) => smooth(pts.concat([pts[0], pts[1]]), n).slice(0, -n); // замкнутый сглаженный контур
  // «трубка» по средней линии с меняющейся толщиной (хвост, лапы)
  function tube(pts0, w0, w1) {
    const pts = smooth(pts0, 8), L = [], Rr = [];
    pts.forEach((p, i) => {
      const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)], dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1;
      const w = w0 + (w1 - w0) * i / (pts.length - 1); L.push([p[0] - dy / l * w, p[1] + dx / l * w]); Rr.push([p[0] + dy / l * w, p[1] - dx / l * w]);
    });
    return L.concat(Rr.reverse());
  }
  const curve = (ink, pts, w, n = 6) => { const q = smooth(pts, n); for (let i = 1; i < q.length; i++) { const k = Math.sin(Math.PI * i / q.length); ink.seg(q[i - 1][0], q[i - 1][1], q[i][0], q[i][1], w * (0.35 + 0.65 * k)); } };
  const solidE = (g, x, y, rx, ry) => fillWhite(g, ellipse(x, y, rx, ry, 0, 32), INK);
  // светлое пятно-блик
  const glint = (g, x, y, r) => fillWhite(g, ellipse(x, y, r, r, 0, 16));
  const fur = (x0, y0, w, h, a = 0.15, b = 0.8) => (x, y) => a + (b - a) * (0.75 * (x - x0) / w + 0.25 * (y - y0) / h); // свет слева сверху
  function legPart(g, ink, leg, o) { // лапа без верхнего контура: сверху она «растёт» из тела
    part(g, ink, leg, Object.assign({ outline: false }, o)); const n = leg.length / 2;
    outline(ink, leg.slice(Math.floor(n * 0.35), n), 2.5, false, o.seed + 'l'); outline(ink, leg.slice(n, Math.ceil(n * 1.65)), 2.5, false, o.seed + 'r');
    return leg;
  }
  function paw(g, ink, x, y, s, seed) { const p = ellipse(x, y, 36, 20, 0, 28); part(g, ink, p, { angle: 0, spacing: 3.6, wmax: 1.6, th: 0.35, seed, shade: fur(x - 36, y - 20, 72, 40, 0.2, 0.8) }); [-14, 0, 14].forEach(dx => ink.seg(x + dx, y + 6, x + dx, y + 18, 1.6)); return p; }

  OBJ.cat = (g, ink, s) => { // сидящая полосатая кошка, анфас
    const sil = [];
    const tail = tube([[400, 545], [470, 540], [530, 500], [545, 430], [520, 380]], 22, 14);
    sil.push(part(g, ink, tail, { angle: 70, spacing: 3.8, wmax: 2, th: 0.2, seed: s + 'tail', shade: (x, y) => 0.45 + 0.4 * (x - 400) / 150 }));
    [[[500, 520], [528, 490]], [[536, 455], [548, 430]]].forEach((st, i) => curve(ink, st, 6));
    const body = loop([[300, 255], [395, 290], [440, 400], [432, 520], [380, 568], [300, 575], [220, 568], [168, 520], [160, 400], [205, 290]]);
    sil.push(part(g, ink, body, { angle: 75, spacing: 4.2, wmax: 2.1, th: 0.25, seed: s + 'body', shade: fur(160, 255, 280, 320, 0.12, 0.95) }));
    for (let k = 0; k < 6; k++) { const y = 320 + k * 42; curve(ink, [[405 - k * 2, y - 8], [380, y + 6], [350, y + 12]], 7 - k * 0.5); curve(ink, [[195 + k * 2, y - 8], [215, y + 4], [235, y + 8]], 4.5 - k * 0.4); } // полоски
    [[255, 1], [345, -1]].forEach(([x, d], i) => {
      const leg = tube([[x, 430], [x - 2 * d, 500], [x - 4 * d, 560]], 30, 26);
      sil.push(legPart(g, ink, leg, { angle: 88, spacing: 4, wmax: 1.9, th: 0.3, seed: s + 'leg' + i, shade: (px) => 0.2 + 0.6 * (px - x + 30) / 60 + (i ? 0.1 : 0) }));
      sil.push(paw(g, ink, x - 4 * d, 568, 1, s + 'paw' + i));
    });
    const head = loop([[300, 95], [372, 112], [418, 168], [424, 236], [384, 292], [300, 310], [216, 292], [176, 236], [182, 168], [228, 112]]);
    [[[200, 165], [185, 40], [275, 112]], [[400, 165], [415, 40], [325, 112]]].forEach((tr, i) => {
      sil.push(part(g, ink, tr, { angle: i ? 110 : 70, spacing: 3.6, seed: s + 'ear' + i, shade: () => (i ? 0.85 : 0.5) }));
      const c = [(tr[0][0] + tr[1][0] + tr[2][0]) / 3, (tr[0][1] + tr[1][1] + tr[2][1]) / 3], inner = tr.map(([x, y]) => [c[0] + (x - c[0]) * 0.55, c[1] + (y - c[1]) * 0.55 + 8]);
      fillWhite(g, inner, '#f4efe4'); for (let k = 0; k < 5; k++) ink.seg(inner[1][0] + (k - 2) * 4, inner[1][1] + 14, c[0] + (k - 2) * 7, c[1] + 22, 1);
    });
    sil.push(part(g, ink, head, { angle: 80, spacing: 4, wmax: 2, th: 0.28, seed: s + 'head', shade: fur(176, 95, 248, 215, 0.1, 0.9) }));
    [[300, 120, 300, 165], [278, 125, 284, 160], [322, 125, 316, 160]].forEach(([a, b, c, d]) => ink.seg(a, b, c, d, 4)); // «М» на лбу
    [[248, 200], [352, 200]].forEach(([x, y], i) => { // глаза-миндалины, зрачок-щель
      const eye = pod([x - 34, y], [x + 34, y], 17, 1, 18); fillWhite(g, eye);
      field(ink, eye, { angle: 10, spacing: 3, wmax: 1.4, th: 0.1, seed: s + 'iris' + i, shade: () => 0.5 });
      outline(ink, eye, 3, true, s + 'eo' + i); fillWhite(g, pod([x, y - 15], [x, y + 15], 5, 1, 12), INK); glint(g, x - 9, y - 5, 4);
    });
    fillWhite(g, [[284, 238], [316, 238], [300, 254]], INK);
    curve(ink, [[300, 254], [300, 266], [286, 276], [274, 272]], 2.6); curve(ink, [[300, 266], [314, 276], [326, 272]], 2.6);
    [[-1, 0], [1, 0]].forEach(([d]) => [-12, 0, 12].forEach((dy, k) => curve(ink, [[300 + d * 40, 262 + dy * 0.4], [300 + d * 120, 254 + dy * 1.6], [300 + d * 200, 248 + dy * 3]], 1.4)));
    return sil;
  };

  function pugBody(g, ink, s, sil) {
    const tail = []; for (let k = 0; k <= 40; k++) { const a = Math.PI * 0.9 + k / 40 * Math.PI * 1.8, r = 34 - k * 0.45; tail.push([440 + Math.cos(a) * r, 318 + Math.sin(a) * r]); }
    sil.push(part(g, ink, tube(tail, 15, 9), { angle: 30, spacing: 3.4, wmax: 1.6, th: 0.3, seed: s + 'tail', shade: () => 0.6 }));
    const body = loop([[300, 280], [408, 312], [456, 430], [444, 548], [380, 578], [300, 584], [220, 578], [156, 548], [144, 430], [192, 312]]);
    sil.push(part(g, ink, body, { angle: 75, spacing: 4.4, wmax: 1.8, th: 0.35, seed: s + 'body', shade: fur(144, 280, 312, 304, 0.12, 0.92) }));
    [[232, 360], [252, 380], [272, 396]].forEach(([x, y], k) => curve(ink, [[x, y], [300, y + 14], [600 - x, y]], 2.2)); // складки на груди
    [[250, 1], [350, -1]].forEach(([x, d], i) => {
      const leg = tube([[x, 440], [x - 2 * d, 505], [x - 3 * d, 565]], 36, 32);
      sil.push(legPart(g, ink, leg, { angle: 88, spacing: 4.2, wmax: 1.8, th: 0.35, seed: s + 'leg' + i, shade: (px) => 0.2 + 0.6 * (px - x + 36) / 72 + (i ? 0.1 : 0) }));
      sil.push(paw(g, ink, x - 3 * d, 574, 1, s + 'paw' + i));
    });
  }
  function pugHead(g, ink, s, sil) {
    [[[178, 130], [122, 150], [140, 225], [196, 182]], [[422, 130], [478, 150], [460, 225], [404, 182]]].forEach((ear, i) => sil.push(part(g, ink, loop(ear, 5), { angle: i ? 120 : 60, spacing: 3, wmax: 2.3, th: 0, seed: s + 'ear' + i, shade: () => 0.95, cross: 0.5 })));
    const head = loop([[300, 92], [386, 106], [440, 160], [446, 236], [406, 296], [300, 322], [194, 296], [154, 236], [160, 160], [214, 106]]);
    sil.push(part(g, ink, head, { angle: 80, spacing: 4.2, wmax: 1.8, th: 0.35, seed: s + 'head', shade: fur(154, 92, 292, 230, 0.12, 0.9) }));
    [[128, 4], [146, 3.6], [164, 3]].forEach(([y, w], k) => curve(ink, [[250 + k * 6, y + 6], [300, y - 6], [350 - k * 6, y + 6]], w)); // морщины лба
    const mask = loop([[250, 212], [300, 198], [350, 212], [372, 262], [338, 306], [300, 314], [262, 306], [228, 262]]);
    part(g, ink, mask, { angle: 70, spacing: 3, wmax: 2.4, th: 0, seed: s + 'mask', shade: (x) => 0.75 + 0.2 * (x - 228) / 144, cross: 0.6 });
    curve(ink, [[236, 228], [260, 214], [300, 210], [340, 214], [364, 228]], 3.6); // складка над носом
    [[242, 186], [358, 186]].forEach(([x, y], i) => { const e = ellipse(x, y, 32, 30, 0, 32); fillWhite(g, e); outline(ink, e, 3, true, s + 'eo' + i); solidE(g, x + (i ? -3 : 3), y + 2, 23, 23); glint(g, x - 6, y - 7, 7); glint(g, x + 8, y + 9, 3); });
    fillWhite(g, ellipse(300, 244, 24, 15, 0, 24), INK); glint(g, 292, 238, 4);
    fillWhite(g, loop([[300, 262], [318, 284], [300, 290], [282, 284]], 4), '#1d1a17');
  }
  OBJ.pug = (g, ink, s) => { const sil = []; pugBody(g, ink, s, sil); pugHead(g, ink, s, sil); return sil; };
  OBJ.prof = (g, ink, s) => { // мопс-профессор: шапочка выпускника и монокль
    const sil = []; pugBody(g, ink, s, sil); pugHead(g, ink, s, sil);
    sil.push(part(g, ink, [[232, 92], [368, 92], [356, 128], [244, 128]], { angle: 0, spacing: 3, wmax: 2.3, th: 0, seed: s + 'cap', shade: () => 0.9, cross: 0.5 }));
    sil.push(part(g, ink, [[300, 34], [460, 74], [300, 112], [140, 74]], { angle: 15, spacing: 3, wmax: 2.3, th: 0, seed: s + 'board', shade: (x) => 0.55 + 0.4 * (x - 140) / 320, cross: 0.6 }));
    solidE(g, 300, 72, 9, 6);
    curve(ink, [[300, 72], [380, 78], [452, 84], [458, 120], [460, 150]], 3.2);
    sil.push(part(g, ink, pod([460, 140], [462, 205], 12, 0.6, 14), { angle: 90, spacing: 2.6, wmax: 2, seed: s + 'tas', shade: () => 0.9 }));
    const mono = ellipse(358, 186, 44, 42, 0, 48); outline(ink, mono, 5, true, s + 'mono'); outline(ink, ellipse(358, 186, 38, 36, 0, 48), 1.6, true, s + 'mono2');
    curve(ink, [[398, 204], [430, 260], [416, 320], [380, 352]], 1.8, 8);
    return sil;
  };
  OBJ.loupe = (g, ink, s) => { // лупа, в линзе — след кошачьей лапы
    const sil = [];
    const handle = [[352, 386], [386, 352], [560, 526], [526, 560]];
    sil.push(part(g, ink, handle, { angle: 45, spacing: 3.6, wmax: 2.2, th: 0.1, seed: s + 'hd', shade: (x, y) => 0.4 + 0.5 * Math.max(0, Math.min(1, ((x - y) + 40) / 80)), cross: 0.7 }));
    sil.push(part(g, ink, [[336, 370], [370, 336], [400, 366], [366, 400]], { angle: -45, spacing: 3, seed: s + 'nk', shade: () => 0.5 }));
    const outer = ellipse(250, 250, 180, 180, 0, 72), inner = ellipse(250, 250, 152, 152, 0, 72);
    fillWhite(g, outer); field(ink, outer, { angle: 30, spacing: 3.4, wmax: 2, th: 0.2, seed: s + 'ring', shade: (x, y) => 0.25 + 0.6 * ((x - 70) + (y - 70)) / 720 });
    fillWhite(g, inner, '#f7f3ea'); outline(ink, outer, 3, true, s + 'o1'); outline(ink, inner, 2.4, true, s + 'o2');
    field(ink, inner, { angle: -40, spacing: 5, wmax: 0.9, th: 0.5, seed: s + 'lens', shade: (x, y) => ((x - 250) + (y - 250)) / 300 + 0.4 });
    fillWhite(g, ellipse(250, 290, 46, 38, 0, 32), INK); // подушечка
    [[196, 228, 16, 22], [234, 200, 17, 24], [278, 202, 17, 24], [312, 232, 16, 22]].forEach(([x, y, rx, ry]) => fillWhite(g, ellipse(x, y, rx, ry, 0, 24), INK));
    curve(ink, [[150, 150], [175, 125], [205, 110]], 6); // блик
    sil.push(outer);
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
