// Сцены «Цзинь Цзюнь Мэй — рождение чая». Всё от времени t, рисунок на двойках (12/с).
(function () {
  'use strict';
  const P = window.PENCIL, T = window.T;
  const { W, H, rng, seg, lerp, ease, easeIO, easeOut, smooth, ellipse, pod, along, resample, CAM, pencil, hatch, hand, glyph } = P;

  let pal, paper, tooth, ink, ig, og;
  function init(theme, canvas) {
    pal = P.PALETTES[theme];
    paper = P.makePaper(pal); tooth = P.makeTooth();
    ink = document.createElement('canvas'); ink.width = W; ink.height = H; ig = ink.getContext('2d');
    og = canvas.getContext('2d');
  }

  // ---------- мир: горы Уишань ----------
  function ridgePts(id, base, peaks, x0 = -40, x1 = 1120, step = 10) {
    const R = rng(id, 'ridge'), pts = [];
    for (let x = x0; x <= x1; x += step) {
      let h = 0;
      for (const k of peaks) { const u = (x - k.x) / k.w * (x < k.x ? 1 : (k.k || 1)); h = Math.max(h, k.h / (1 + Math.pow(Math.abs(u), k.e || 6))); }
      pts.push([x, base - h + (R() - 0.5) * 4]);
    }
    return pts;
  }
  const RIDGES = [
    { id: 'far', base: 940, peaks: [{ x: 90, h: 230, w: 70, e: 8 }, { x: 230, h: 300, w: 55, e: 10, k: 1.4 }, { x: 400, h: 360, w: 62, e: 9 }, { x: 590, h: 250, w: 95, e: 5 }, { x: 790, h: 380, w: 60, e: 10, k: 0.8 }, { x: 960, h: 270, w: 70, e: 7 }],
      role: 'soft', w: 3.2, draw: [0, 1.4], hr: { role: 'cold', angle: 76, spacing: 11, alpha: 0.42 }, ht: [1.3, 2.8] },
    { id: 'mid', base: 1100, peaks: [{ x: 30, h: 240, w: 110, e: 6 }, { x: 250, h: 320, w: 75, e: 9, k: 1.3 }, { x: 470, h: 180, w: 90, e: 5 }, { x: 690, h: 340, w: 80, e: 10 }, { x: 950, h: 280, w: 95, e: 7, k: 0.7 }],
      role: 'line', w: 4, draw: [0.6, 2.0], hr: { role: 'soft', angle: 78, spacing: 8, alpha: 0.5 }, ht: [1.8, 3.2] },
    { id: 'near', base: 1270, peaks: [{ x: -60, h: 360, w: 170 }, { x: 1140, h: 380, w: 165 }, { x: 470, h: 90, w: 190 }],
      role: 'line', w: 4.8, draw: [1.2, 2.5], hr: { role: 'line', angle: 66, spacing: 7, alpha: 0.5 }, ht: [2.2, 3.6] },
  ];
  RIDGES.forEach(r => { r.pts = ridgePts(r.id, r.base, r.peaks); r.poly = r.pts.concat([[1120, r.base + 50], [-40, r.base + 50]]); });

  function wavyBand(id, y0, y1, amp) {
    const R = rng(id, 'band'), top = [], bot = [];
    for (let x = -40; x <= 1120; x += 60) { top.push([x, y0 + (R() - 0.5) * amp]); bot.push([x, y1 + (R() - 0.5) * amp]); }
    return smooth(top, 4).concat(smooth(bot.reverse(), 4));
  }
  const MIST = [
    { id: 'mist1', poly: wavyBand('m1', 905, 985, 40), t: [2.6, 3.5] },
    { id: 'mist2', poly: wavyBand('m2', 1070, 1140, 40), t: [2.9, 3.8] },
  ];
  const SKY = [[-40, 610], [1120, 570], [1120, 690], [-40, 720]];

  // ---------- мир: деревня Тунму ----------
  const HOUSES = [
    { x: 470, y: 1440, w: 120, h: 58 }, { x: 610, y: 1468, w: 96, h: 48 }, { x: 880, y: 1446, w: 132, h: 62 }, { x: 330, y: 1478, w: 100, h: 46 },
    { x: 735, y: 1400, w: 120, h: 118, dry: true },
  ];
  HOUSES.forEach((h, i) => {
    const top = h.y - h.h, L = h.x - h.w / 2, Rr = h.x + h.w / 2;
    h.t0 = h.dry ? 4.6 : 4.0 + i * 0.28;
    h.walls = [[L, top], [L, h.y], [Rr, h.y], [Rr, top]];
    const ridge = smooth([[L - 34, top - 14], [L - 14, top - 6], [L + 4, top - 30], [h.x, top - 38], [Rr - 4, top - 30], [Rr + 14, top - 6], [Rr + 34, top - 14]], 5);
    h.roof = ridge.concat([[Rr + 18, top + 2], [L - 18, top + 2]]);
    h.door = [[h.x - 12, h.y], [h.x - 12, h.y - 30], [h.x + 12, h.y - 30], [h.x + 12, h.y]];
    if (h.dry) h.chimney = [[h.x + 18, top - 8], [h.x + 18, top - 78], [h.x + 38, top - 78], [h.x + 38, top - 8]];
  });
  const CHIMNEY = [763, 1196];
  const TERRACES = [0, 1, 2, 3, 4].map(i => {
    const pts = [];
    for (let x = 30; x <= 430; x += 8) pts.push([x, 1300 + i * 34 - 26 * Math.sin((x - 30) / 400 * Math.PI) - 5 * Math.abs(Math.sin(x / 13))]);
    return pts;
  });
  function smokePts(k, tq, len) {
    const pts = [], ph = tq * 2.4 + k * 1.9;
    for (let s = 0; s <= len; s += 8) {
      const amp = 8 + 26 * Math.min(1, s / 220);
      pts.push([CHIMNEY[0] + k * 9 + s * 0.07 + amp * Math.sin(s * 0.02 - ph), CHIMNEY[1] - s]);
    }
    return pts;
  }

  // ---------- мир: ветка и почка (экранные координаты при s=1) ----------
  const BRANCH = smooth([[250, 1580], [330, 1310], [430, 1080], [520, 880], [590, 720], [612, 660]], 10);
  const BUD_BASE = [612, 662], BUD_TIP = [660, 536], BUD_C = [636, 600];
  const BUD = pod(BUD_BASE, BUD_TIP, 25, 0.6, 30);
  const LEAVES = [[0.30, 1, 250, 62], [0.50, -1, 220, 54], [0.70, 1, 170, 44], [0.90, -1, 90, 26]].map((L, i) => {
    const a = along(BRANCH, L[0]), rot = L[1] * 55 * Math.PI / 180;
    const dx = a.dir[0] * Math.cos(rot) - a.dir[1] * Math.sin(rot), dy = a.dir[0] * Math.sin(rot) + a.dir[1] * Math.cos(rot);
    const tip = [a.p[0] + dx * L[2], a.p[1] + dy * L[2]];
    return { i, base: a.p, tip, poly: pod(a.p, tip, L[3], 0.9, 24), ang: Math.atan2(dy, dx) * 180 / Math.PI };
  });

  // ---------- горка почек ----------
  const HEAP = (() => {
    const rows = [7, 6, 5, 4, 2], out = [], R = rng('heap');
    rows.forEach((c, r) => {
      for (let k = 0; k < c; k++) {
        const x = 540 + (k - (c - 1) / 2) * 110 + (R() - 0.5) * 24, y = 1470 - r * 54 + (R() - 0.5) * 10;
        const a = -0.35 + (R() - 0.5) * 1.0, x0 = x + (R() - 0.5) * 260, a0 = a + (R() - 0.5) * 3;
        out.push({ x, y, a, x0, a0 });
      }
    });
    out.forEach((b, i) => { b.land = T.budLand[i]; });
    return out;
  })();
  function budAt(cx, cy, ang, len, wid) {
    const dx = Math.cos(ang) * len / 2, dy = Math.sin(ang) * len / 2;
    return pod([cx - dx, cy - dy], [cx + dx, cy + dy], wid, 0.6, 18);
  }
  const GLYPHS = ['金', '骏', '眉'], GLABEL = ['золото', 'горы', 'бровь'], GX = [270, 540, 810], GY = 760;
  const POSTER_RIDGE = ridgePts('poster', 470, [{ x: 200, h: 130, w: 50 }, { x: 360, h: 180, w: 45 }, { x: 540, h: 150, w: 60 }, { x: 720, h: 190, w: 46 }, { x: 880, h: 130, w: 55 }], 110, 970, 8);

  // ---------- камера ----------
  function camLand(t) {
    if (t < 3.5) { const s = 1 + 0.05 * easeIO(seg(t, 0, 3.5)); CAM.set(s, 540, 960, 540, 960); return; }
    if (t < 6.6) { const u = easeIO(seg(t, 3.5, 6.6)); CAM.set(lerp(1.05, 1.6, u), lerp(540, 660, u), lerp(960, 1330, u), 540, lerp(960, 1120, u)); return; }
    const u = easeIO(seg(t, 6.6, 7.0)); CAM.set(lerp(1.6, 2.0, u), lerp(660, 780, u), lerp(1330, 990, u), 540, lerp(1120, 900, u));
  }
  function camBud(t) {
    if (t < T.turn) { CAM.reset(); return; }
    if (t < 9.8) { const u = easeOut(seg(t, T.turn, T.turn + 0.45)); CAM.set(lerp(1, 5.2, u), BUD_C[0], BUD_C[1], lerp(BUD_C[0], 540, u), lerp(BUD_C[1], 900, u)); return; }
    const u = easeIO(seg(t, 9.8, 10.5)); CAM.set(lerp(5.2, 1.8, u), BUD_C[0], BUD_C[1], 540, lerp(900, 640, u));
  }

  // ---------- рисование ----------
  function erase(g, polyW, a) { // «ластик»: передний план закрывает то, что позади
    const q = polyW.map(CAM.map);
    g.save(); g.globalCompositeOperation = 'destination-out'; g.globalAlpha = a; g.beginPath();
    q.forEach((p, i) => (i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]))); g.closePath(); g.fill(); g.restore();
  }
  function drawLand(g, t, d) {
    camLand(t);
    const fade = 1 - seg(t, 6.85, 7.35), ta = t + 0.5; // рисунок начинается чуть раньше нуля
    if (fade <= 0) return;
    // строительные линии
    const gf = (1 - seg(t, 1.3, 2.3)) * fade, gp = seg(ta, 0, 0.9);
    if (gf > 0) {
      RIDGES.slice(0, 2).forEach(r => r.peaks.forEach((k, i) =>
        pencil(g, ellipse(k.x, r.base - k.h * 0.55, k.w * 1.05, k.h * 0.55, 0.1, 40), { id: 'gd' + r.id + i, d, color: pal.guide, w: 1.6, alpha: 0.45, p: gp, fade: gf, gaps: false, sketch: false })));
      [[[-40, 940], [1120, 940]], [[-40, 1100], [1120, 1100]], [[0, 1320], [1080, 640]]].forEach((L, i) =>
        pencil(g, L, { id: 'ga' + i, d, color: pal.guide, w: 1.5, alpha: 0.4, p: gp, fade: gf, sketch: false }));
    }
    hatch(g, SKY, { id: 'sky', d, color: pal.cold, angle: -3, spacing: 11, w: 2, alpha: 0.45, maxLen: 110, p: seg(t, 1.6, 3.0), fade });
    RIDGES.forEach((r, i) => {
      const pr = seg(ta, r.draw[0], r.draw[1]);
      if (i > 0 && pr > 0) erase(g, r.poly.slice(0, Math.max(2, Math.round(pr * (r.pts.length)))).concat(r.poly.slice(r.pts.length)), fade);
      hatch(g, r.poly, { id: 'h' + r.id, d, color: pal[r.hr.role], angle: r.hr.angle, spacing: r.hr.spacing, w: 2.3, alpha: r.hr.alpha, p: seg(t, r.ht[0], r.ht[1]), fade });
      pencil(g, r.pts, { id: 'r' + r.id, d, color: pal[r.role], w: r.w, p: seg(ta, r.draw[0], r.draw[1]), fade });
    });
    MIST.forEach(m => hatch(g, m.poly, { id: m.id, d, color: pal.light, angle: 2, spacing: 7, w: 2.4, alpha: 0.6, maxLen: 120, p: seg(t, m.t[0], m.t[1]), fade }));
    // деревня
    TERRACES.forEach((pts, i) => pencil(g, pts, { id: 'ter' + i, d, color: pal.soft, w: 3, p: seg(t, 3.6 + i * 0.15, 4.2 + i * 0.15), fade }));
    HOUSES.forEach((h, i) => {
      const t0 = h.t0;
      hatch(g, h.walls, { id: 'wl' + i, d, color: pal.light, angle: 82, spacing: 8, w: 2, alpha: 0.5, p: seg(t, t0 + 0.3, t0 + 0.8), fade });
      hatch(g, h.roof, { id: 'rf' + i, d, color: pal.line, angle: 18, spacing: 5.5, w: 1.6, alpha: 0.55, maxLen: 40, p: seg(t, t0 + 0.4, t0 + 0.9), fade });
      pencil(g, h.walls, { id: 'w' + i, d, color: pal.soft, w: 2.4, p: seg(t, t0, t0 + 0.4), fade });
      pencil(g, h.roof, { id: 'rof' + i, d, color: pal.line, w: 3, closed: true, p: seg(t, t0 + 0.1, t0 + 0.5), fade });
      pencil(g, h.door, { id: 'dr' + i, d, color: pal.line, w: 2, p: seg(t, t0 + 0.4, t0 + 0.6), fade });
      if (h.chimney) pencil(g, h.chimney, { id: 'ch', d, color: pal.line, w: 2.6, p: seg(t, t0 + 0.5, t0 + 0.8), fade });
    });
    // дым: главный завиток станет веткой
    const len = 420 * ease(seg(t, 5.5, 6.6));
    if (len > 10 && t < 7.0) for (let k = -1; k <= 1; k++)
      pencil(g, smokePts(k, t, len * (k ? 0.8 : 1)), { id: 'smoke' + k, d, color: pal.soft, w: 3.2, alpha: 0.85 });
  }

  function drawBranch(g, t, d) {
    if (t < 7.0 || t >= 10.3) return;
    const bf = 1 - seg(t, 9.8, 10.2);
    if (t < 7.75) { // дым -> ветка (переход формой)
      camLand(7.0);
      const N = 90, sm = resample(smokePts(0, 7.0, 420).map(CAM.map), 1), br = resample(BRANCH, 1);
      const pick = (a, i) => a[Math.round(i / (N - 1) * (a.length - 1))];
      const u = easeIO(seg(t, 7.0, 7.7)), pts = [];
      for (let i = 0; i < N; i++) { const a = pick(sm, i), b = pick(br, i); pts.push([lerp(a[0], b[0], u), lerp(a[1], b[1], u)]); }
      pencil(g, pts, { id: 'morph', d, color: u < 0.5 ? pal.soft : pal.line, w: lerp(2.4, 4, u), screen: true });
      [-1, 1].forEach(k => pencil(g, smokePts(k, 7.0, 336).map(CAM.map), { id: 'smoke' + k, d, color: pal.soft, w: 2.4, alpha: 0.7, screen: true, fade: 1 - seg(t, 7.0, 7.3) }));
    }
    camBud(t);
    if (t >= 7.7) pencil(g, BRANCH, { id: 'branch', d, color: pal.line, w: 4, fade: bf });
    LEAVES.forEach(L => {
      const t0 = 7.3 + L.i * 0.12;
      hatch(g, L.poly, { id: 'lh' + L.i, d, color: pal.soft, angle: L.ang + 50, spacing: 9, w: 1.6, alpha: 0.4, p: seg(t, t0 + 0.25, t0 + 0.6), fade: bf });
      pencil(g, L.poly, { id: 'lf' + L.i, d, color: pal.line, w: 3, closed: true, p: seg(t, t0, t0 + 0.4), fade: bf });
      pencil(g, [L.base, L.tip], { id: 'lr' + L.i, d, color: pal.soft, w: 1.8, p: seg(t, t0 + 0.2, t0 + 0.5), fade: bf });
    });
  }

  function drawBud(g, t, d) {
    if (t < 7.6 || t >= 12.7) return;
    camBud(t);
    const fade = 1 - seg(t, 12.3, 12.6), wS = Math.min(2.2, Math.sqrt(CAM.s));
    const scr = BUD.map(CAM.map), ang = Math.atan2(BUD_TIP[1] - BUD_BASE[1], BUD_TIP[0] - BUD_BASE[0]) * 180 / Math.PI;
    hatch(g, scr, { id: 'budc', d, color: pal.soft, angle: ang + 35, spacing: 9, w: 1.6, alpha: 0.35, screen: true, p: seg(t, 7.75, 8.0), fade });
    if (t >= T.turn) {
      hatch(g, scr, { id: 'budg', d, color: pal.warm, angle: ang + 6, spacing: 6, w: 2.2, alpha: 0.85, screen: true, p: seg(t, T.turn + 0.05, T.turn + 0.9), fade });
      // золотые ворсинки
      const R = rng('hair'), Rd = rng('hair', d), edge = resample(scr, 9), nShow = Math.floor(edge.length * seg(t, 8.25, 9.1));
      g.strokeStyle = pal.warm; g.lineCap = 'round';
      for (let i = 0; i < edge.length; i++) {
        const a = edge[Math.max(0, i - 1)], b = edge[Math.min(edge.length - 1, i + 1)];
        let nx = b[1] - a[1], ny = -(b[0] - a[0]); const L = Math.hypot(nx, ny) || 1; nx /= L; ny /= L;
        const len = (6 + R() * 14) * Math.min(2, wS), jx = (Rd() - 0.5) * 3, jy = (Rd() - 0.5) * 3, wr = R();
        if (i >= nShow) continue;
        g.globalAlpha = 0.8 * fade; g.lineWidth = 1.4 + wr;
        g.beginPath(); g.moveTo(edge[i][0] - nx * 3, edge[i][1] - ny * 3); g.lineTo(edge[i][0] + nx * len + jx, edge[i][1] + ny * len + jy); g.stroke();
      }
      g.globalAlpha = 1;
    }
    pencil(g, scr, { id: 'bud', d, color: pal.line, w: 3.2 * wS, closed: true, screen: true, p: seg(t, 7.65, 7.95), fade });
    // вспышка
    if (t >= T.turn && t < 9.3) {
      const c = CAM.map(BUD_C), R = rng('rays'), grow = easeOut(seg(t, T.turn, T.turn + 0.25)), rf = 1 - seg(t, 8.5, 9.2);
      for (let i = 0; i < 22; i++) {
        const a = i / 22 * Math.PI * 2 + (R() - 0.5) * 0.15, r0 = 75 * CAM.s * 0.95 + 20, r1 = r0 + (180 + R() * 260) * grow;
        pencil(g, [[c[0] + Math.cos(a) * r0, c[1] + Math.sin(a) * r0], [c[0] + Math.cos(a) * r1, c[1] + Math.sin(a) * r1]],
          { id: 'ray' + i, d, color: pal.warm, w: 6, alpha: 1, screen: true, fade: rf, gaps: false });
        if (i % 2 === 0) pencil(g, [[c[0] + Math.cos(a) * r0, c[1] + Math.sin(a) * r0], [c[0] + Math.cos(a) * (r0 + (r1 - r0) * 0.6), c[1] + Math.sin(a) * (r0 + (r1 - r0) * 0.6)]], { id: 'rayl' + i, d, color: pal.line, w: 2, alpha: 0.6, screen: true, fade: rf });
      }
    }
  }

  function drawHeap(g, t, d) {
    if (t < T.rainStart - 0.6 || t >= 16.2) return;
    CAM.reset();
    HEAP.forEach((b, i) => {
      const chosen = i >= HEAP.length - 3, gi = i - (HEAP.length - 3);
      let x, y, a, fade = 1, scale = 1;
      const u = seg(t, b.land - 0.55, b.land);
      if (u <= 0) return;
      x = lerp(b.x0, b.x, u); y = lerp(-120, b.y, u * u); a = lerp(b.a0, b.a, u);
      if (!chosen) fade = 1 - seg(t, 12.5, 13.0);
      else {
        const tg = T.glyphs[gi], r = easeIO(seg(t, tg - 0.5, tg - 0.1));
        x = lerp(x, GX[gi], r); y = lerp(y, GY, r); a = lerp(a, -Math.PI / 2 + 0.5, r); scale = lerp(1, 1.6, r);
        fade = 1 - seg(t, tg + 0.1, tg + 0.5);
      }
      if (fade <= 0) return;
      const poly = budAt(x, y, a, 104 * scale, 23 * scale);
      hatch(g, poly, { id: 'hb' + i, d, color: pal.warm, angle: a * 180 / Math.PI + 8, spacing: 5, w: 1.8, alpha: 0.85, fade });
      pencil(g, poly, { id: 'hbo' + i, d, color: pal.line, w: 3, closed: true, fade });
    });
  }

  function drawGlyphs(g, t, d) {
    if (t < T.glyphs[0]) return;
    GLYPHS.forEach((ch, i) => {
      const tg = T.glyphs[i];
      glyph(g, ch, GX[i], GY, { id: 'gl' + i, d, size: 260, fill: pal.warm, tone: pal.line, line: pal.line, p: seg(t, tg, tg + 0.8) });
      hand(g, GLABEL[i], GX[i], 1010, { id: 'gla' + i, d, size: 84, color: pal.line, p: seg(t, tg + 0.45, tg + 0.95), fade: 1 - seg(t, 16.0, 16.25) });
    });
  }

  function drawPoster(g, t, d) {
    if (t < 16.1) return;
    CAM.reset();
    hatch(g, POSTER_RIDGE.concat([[970, 500], [110, 500]]), { id: 'pr', d, color: pal.soft, angle: 72, spacing: 10, w: 1.6, alpha: 0.3, p: seg(t, 16.4, 16.9) });
    pencil(g, POSTER_RIDGE, { id: 'prl', d, color: pal.soft, w: 3.2, p: seg(t, 16.1, 16.7) });
    const sun = ellipse(880, 250, 34, 34, 0, 36);
    hatch(g, sun, { id: 'sunh', d, color: pal.warm, angle: 30, spacing: 5, w: 1.8, alpha: 0.85, p: seg(t, 16.5, 16.9) });
    pencil(g, sun, { id: 'sun', d, color: pal.warm, w: 3, p: seg(t, 16.4, 16.8) });
    hand(g, 'Цзинь Цзюнь Мэй', 540, 1110, { id: 'pt1', d, size: 124, color: pal.line, p: seg(t, 16.15, 16.7) });
    hand(g, 'Золотые брови Уишаня', 540, 1225, { id: 'pt2', d, size: 80, color: pal.soft, p: seg(t, 16.4, 16.85) });
    hand(g, 'с 2005 года', 540, 1320, { id: 'pt3', d, size: 80, color: pal.soft, p: seg(t, 16.6, 16.95) });
    if (t >= T.seal) { // печать
      const sc = lerp(1.25, 1, seg(t, T.seal, T.seal + 0.1)), S = 78 * sc, cx = 540, cy = 1470;
      const sq = [[cx - S, cy - S], [cx + S, cy - S], [cx + S, cy + S], [cx - S, cy + S]];
      hatch(g, sq, { id: 'seal', d, color: pal.seal, angle: 45, spacing: 3.5, w: 2.4, alpha: 0.9, maxLen: 50, ends: 2 });
      hatch(g, sq, { id: 'seal2', d, color: pal.seal, angle: -45, spacing: 5, w: 1.8, alpha: 0.6, maxLen: 40, ends: 2 });
      pencil(g, sq, { id: 'sealo', d, color: pal.seal, w: 3.4, closed: true });
      glyph(g, '茶', cx, cy + 4, { id: 'sealg', d, size: 100 * sc, fill: pal.paperLight, tone: pal.paperLight, line: pal.paperLight, base: 1, lineW: 2 });
    }
  }

  function drawCaptions(g, t, d) {
    CAM.reset();
    hand(g, 'Горы Уишань · Фуцзянь', 540, 330, { id: 'c1', d, size: 96, color: pal.line, p: seg(t, 0.8, 1.8), fade: 1 - seg(t, 3.5, 3.8) });
    const f2 = 1 - seg(t, 6.7, 7.0);
    hand(g, 'Тунму — здесь родился', 540, 1470, { id: 'c2a', d, size: 88, color: pal.line, p: seg(t, 4.3, 5.2), fade: f2 });
    hand(g, 'первый красный чай', 540, 1570, { id: 'c2b', d, size: 88, color: pal.line, p: seg(t, 5.0, 5.8), fade: f2 });
    const f3 = 1 - seg(t, 12.3, 12.6);
    if (t >= T.turn) {
      hand(g, '2005', 540, 330, { id: 'y2005', d, size: 230, weight: 700, color: pal.line, p: seg(t, T.turn + 0.05, T.turn + 0.45), fade: f3 });
      pencil(g, [[400, 360], [680, 352]], { id: 'u2005', d, color: pal.warm, w: 6, screen: true, p: seg(t, 8.4, 8.6), fade: f3 });
      hand(g, 'Только почки', 540, 1380, { id: 'only', d, size: 100, color: pal.line, p: seg(t, 8.9, 9.5), fade: 1 - seg(t, 9.95, 10.2) });
    }
    if (t >= T.rainStart) {
      const n = Math.round(50000 * easeOut(seg(t, T.rainStart, T.budLand[T.budLand.length - 1])) / 500) * 500;
      hand(g, '≈ ' + String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' почек', 540, 930, { id: 'cnt', d, size: 92, color: pal.line, fade: f3 });
      hand(g, '= 500 г чая', 540, 1035, { id: 'g500', d, size: 92, color: pal.line, p: seg(t, 11.7, 12.0), fade: f3 });
    }
  }

  // реальное время -> время сюжета (паузы на чтение)
  function story(t) {
    let shift = 0;
    for (const [h, dur] of T.holds) {
      const hr = h + shift; // момент паузы в реальном времени
      if (t >= hr + dur) shift += dur; else if (t > hr) return h;
    }
    return t - shift;
  }

  function render(t) {
    const d = Math.floor(t * T.drawRate + 1e-6), tq = story(d / T.drawRate); // на двойках; кипение идёт по реальному времени
    ig.setTransform(1, 0, 0, 1, 0, 0); ig.globalCompositeOperation = 'source-over'; ig.globalAlpha = 1; ig.clearRect(0, 0, W, H);
    drawLand(ig, tq, d); drawBranch(ig, tq, d); drawBud(ig, tq, d); drawHeap(ig, tq, d); drawGlyphs(ig, tq, d); drawPoster(ig, tq, d); drawCaptions(ig, tq, d);
    ig.globalCompositeOperation = 'destination-out'; ig.globalAlpha = 0.5; ig.drawImage(tooth, 0, 0);
    ig.globalCompositeOperation = 'source-over'; ig.globalAlpha = 1;
    og.globalCompositeOperation = 'source-over'; og.globalAlpha = 1; og.drawImage(paper, 0, 0);
    const wa = 0.1 * ease(seg(tq, T.turn - 0.05, T.turn + 0.25)); // после поворота бумага теплеет
    if (wa > 0) { og.globalAlpha = wa; og.fillStyle = pal.wash; og.fillRect(0, 0, W, H); og.globalAlpha = 1; }
    og.drawImage(ink, 0, 0);
  }

  window.SCENES = { init, render };
})();
