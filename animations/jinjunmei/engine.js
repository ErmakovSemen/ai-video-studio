// Карандашный движок: случайность только с зерном, всё считается от времени t.
// Модули: RNG, геометрия, камера, карандаш (линия/штриховка/рукопись/иероглиф), бумага, палитры.
(function () {
  'use strict';
  const W = 1080, H = 1920;

  // ---------- случайность с зерном (никакого Math.random) ----------
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function hash() {
    let h = 2166136261 >>> 0;
    for (let k = 0; k < arguments.length; k++) {
      const s = String(arguments[k]);
      for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) >>> 0; }
      h ^= 124; h = Math.imul(h, 16777619) >>> 0;
    }
    return h >>> 0;
  }
  const rng = function () { return mulberry32(hash.apply(null, arguments)); };

  // ---------- математика ----------
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const seg = (t, a, b) => clamp((t - a) / (b - a));
  const lerp = (a, b, u) => a + (b - a) * u;
  const ease = u => u * u * (3 - 2 * u);
  const easeIO = u => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
  const easeOut = u => 1 - Math.pow(1 - u, 3);
  // «появился → стёрт»: 1 внутри окна, плавно по краям
  const life = (t, a, b, fin = 0.15, fout = 0.25) => Math.min(seg(t, a - fin, a), 1 - seg(t, b, b + fout));

  function resample(pts, step) {
    const out = [[pts[0][0], pts[0][1]]];
    let need = step;
    for (let i = 1; i < pts.length; i++) {
      let x0 = pts[i - 1][0], y0 = pts[i - 1][1];
      const x1 = pts[i][0], y1 = pts[i][1];
      let len = Math.hypot(x1 - x0, y1 - y0);
      while (len >= need) {
        x0 += (x1 - x0) / len * need; y0 += (y1 - y0) / len * need;
        out.push([x0, y0]);
        len = Math.hypot(x1 - x0, y1 - y0); need = step;
      }
      need -= len;
    }
    const last = pts[pts.length - 1], lo = out[out.length - 1];
    if (Math.hypot(last[0] - lo[0], last[1] - lo[1]) > step * 0.3) out.push([last[0], last[1]]);
    return out;
  }

  // Catmull-Rom сглаживание по опорным точкам
  function smooth(pts, segs = 8) {
    if (pts.length < 3) return pts.slice();
    const out = [];
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
      for (let j = 0; j < segs; j++) {
        const t = j / segs, t2 = t * t, t3 = t2 * t;
        out.push([0, 1].map(k => 0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3)));
      }
    }
    out.push(pts[pts.length - 1].slice());
    return out;
  }

  function ellipse(cx, cy, rx, ry, rot = 0, n = 56, a0 = 0) {
    const out = [], c = Math.cos(rot), s = Math.sin(rot);
    for (let i = 0; i <= n; i++) {
      const a = a0 + i / n * Math.PI * 2, x = Math.cos(a) * rx, y = Math.sin(a) * ry;
      out.push([cx + x * c - y * s, cy + x * s + y * c]);
    }
    return out;
  }

  // лист/почка: замкнутый контур от основания к кончику
  function pod(base, tip, width, shape = 0.8, n = 26) {
    const dx = tip[0] - base[0], dy = tip[1] - base[1], L = Math.hypot(dx, dy);
    const nx = -dy / L, ny = dx / L, side = [];
    for (let i = 0; i <= n; i++) {
      const u = i / n, wv = width * Math.pow(Math.sin(Math.PI * Math.pow(u, shape)), 0.9);
      side.push([base[0] + dx * u, base[1] + dy * u, wv]);
    }
    const left = side.map(p => [p[0] + nx * p[2], p[1] + ny * p[2]]);
    const right = side.map(p => [p[0] - nx * p[2], p[1] - ny * p[2]]).reverse();
    return left.concat(right.slice(1));
  }

  function along(pts, u) { // точка и направление на доле длины
    const rs = resample(pts, 3), i = Math.min(rs.length - 2, Math.max(0, Math.floor(u * (rs.length - 1))));
    const a = rs[i], b = rs[i + 1], L = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
    return { p: a, dir: [(b[0] - a[0]) / L, (b[1] - a[1]) / L] };
  }

  // ---------- камера: мир -> экран (толщина линий не масштабируется) ----------
  const CAM = { s: 1, cx: W / 2, cy: H / 2, sx: W / 2, sy: H / 2 };
  CAM.set = function (s, cx, cy, sx, sy) { CAM.s = s; CAM.cx = cx; CAM.cy = cy; CAM.sx = sx; CAM.sy = sy; };
  CAM.reset = function () { CAM.set(1, W / 2, H / 2, W / 2, H / 2); };
  CAM.map = p => [CAM.sx + (p[0] - CAM.cx) * CAM.s, CAM.sy + (p[1] - CAM.cy) * CAM.s];

  // ---------- КАРАНДАШ: лента с нажимом, кипение, разрывы, второй проход ----------
  function pencil(g, ptsW, o) {
    const p = o.p === undefined ? 1 : o.p, fade = o.fade === undefined ? 1 : o.fade;
    if (p <= 0 || fade <= 0.01 || !ptsW || ptsW.length < 2) return;
    let pts = o.screen ? ptsW : ptsW.map(CAM.map);
    if (o.closed) pts = pts.concat([pts[0]]);
    let rs = resample(pts, 4);
    if (o.closed) rs = rs.concat(rs.slice(1, Math.min(9, rs.length))); // контур заходит за начало
    const n = rs.length; if (n < 2) return;
    const R = rng(o.id, o.d, 'p');
    const jit = o.jitter === undefined ? 1.4 : o.jitter, w = o.w || 3, a0 = (o.alpha === undefined ? 0.9 : o.alpha) * fade;
    // сначала тянем ВСЕ случайные числа, потом пропускаем невидимое
    const K = 10, kn = []; for (let i = 0; i < Math.ceil(n / K) + 2; i++) kn.push(R() * 2 - 1);
    const hf = new Float32Array(n), wr = new Float32Array(n), ar = new Float32Array(n);
    for (let i = 0; i < n; i++) { hf[i] = R() - 0.5; wr[i] = R(); ar[i] = R(); }
    const gaps = new Uint8Array(n);
    if (o.gaps !== false && n > 40) {
      let i = 8;
      while (i < n - 8) { if (R() < 0.03) { const L = 2 + Math.floor(R() * 3); for (let j = 0; j < L; j++) gaps[i + j] = 1; i += L + 8; } else i++; }
    }
    const off = i => {
      const a = rs[Math.max(0, i - 1)], b = rs[Math.min(n - 1, i + 1)];
      let nx = -(b[1] - a[1]), ny = b[0] - a[0]; const L = Math.hypot(nx, ny) || 1; nx /= L; ny /= L;
      const k = i / K, k0 = Math.floor(k), f = k - k0, sm = (1 - Math.cos(f * Math.PI)) / 2;
      const o2 = jit * lerp(kn[k0], kn[k0 + 1], sm) + 0.4 * hf[i];
      return [rs[i][0] + nx * o2, rs[i][1] + ny * o2];
    };
    const m = Math.max(1, Math.floor(p * (n - 1))), taper = Math.max(2, Math.min(9, n / 4));
    g.lineCap = 'round'; g.strokeStyle = o.color;
    let A = off(0);
    for (let i = 0; i < m; i++) {
      const B = off(i + 1);
      if (!gaps[i]) {
        const pr = Math.min(1, (i + 1) / taper, (n - 1 - i) / taper);
        g.lineWidth = w * (0.3 + 0.7 * Math.sqrt(Math.max(0, pr))) * (0.85 + 0.3 * wr[i]);
        g.globalAlpha = a0 * (0.7 + 0.3 * ar[i]);
        g.beginPath(); g.moveTo(A[0], A[1]); g.lineTo(B[0], B[1]); g.stroke();
      }
      A = B;
    }
    if (o.sketch !== false) // тонкий набросочный проход поверх
      pencil(g, rs, Object.assign({}, o, { screen: true, closed: false, id: o.id + 's', w: w * 0.42, alpha: (o.alpha === undefined ? 0.9 : o.alpha) * 0.42, jitter: jit * 2.2, sketch: false }));
    g.globalAlpha = 1;
  }

  // ---------- ШТРИХОВКА вместо заливки: короткие штрихи с разбросом концов ----------
  function hatch(g, polyW, o) {
    const p = o.p === undefined ? 1 : o.p, fade = o.fade === undefined ? 1 : o.fade;
    if (p <= 0 || fade <= 0.01) return;
    const poly = o.screen ? polyW : polyW.map(CAM.map);
    const ang = (o.angle === undefined ? 45 : o.angle) * Math.PI / 180, ca = Math.cos(ang), sa = Math.sin(ang);
    const P = poly.map(q => [q[0] * ca + q[1] * sa, -q[0] * sa + q[1] * ca]);
    let vmin = Infinity, vmax = -Infinity; for (const q of P) { vmin = Math.min(vmin, q[1]); vmax = Math.max(vmax, q[1]); }
    const sp = o.spacing || 10, E = o.ends === undefined ? 7 : o.ends, maxLen = o.maxLen || 70;
    const Rs = rng(o.id, 'layout'), Rd = rng(o.id, o.d, 'boil');
    const strokes = [];
    for (let v = vmin + sp * (0.3 + 0.4 * Rs()); v < vmax; v += sp * (0.8 + 0.4 * Rs())) {
      const xs = [];
      for (let i = 0; i < P.length; i++) {
        const a = P[i], b = P[(i + 1) % P.length];
        if ((a[1] <= v && b[1] > v) || (b[1] <= v && a[1] > v)) xs.push(a[0] + (v - a[1]) / (b[1] - a[1]) * (b[0] - a[0]));
      }
      xs.sort((x, y) => x - y);
      for (let k = 0; k + 1 < xs.length; k += 2) {
        let u = xs[k] + (Rd() - 0.25) * E; const uEnd = xs[k + 1] - (Rd() - 0.25) * E;
        while (u < uEnd - 3) {
          const L = Math.min(uEnd - u, maxLen * (0.6 + 0.8 * Rd()));
          const dv = (Rd() - 0.5) * 1.2, tilt = (Rd() - 0.5) * 2.2;
          strokes.push([u, v + dv, u + L, v + dv + tilt, Rd(), Rd()]);
          u += L + 2 + Rd() * 7;
        }
      }
    }
    const nShow = Math.ceil(strokes.length * p);
    const w = o.w || 1.6, a0 = (o.alpha === undefined ? 0.5 : o.alpha) * fade;
    g.lineCap = 'round'; g.strokeStyle = o.color;
    for (let i = 0; i < nShow; i++) {
      const s = strokes[i];
      const x0 = s[0] * ca - s[1] * sa, y0 = s[0] * sa + s[1] * ca, x1 = s[2] * ca - s[3] * sa, y1 = s[2] * sa + s[3] * ca;
      g.lineWidth = w * (0.7 + 0.6 * s[4]); g.globalAlpha = a0 * (0.55 + 0.45 * s[5]);
      g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke();
    }
    g.globalAlpha = 1;
  }

  // ---------- РУКОПИСЬ: текст «пишется» слева направо и кипит ----------
  function hand(g, str, x, y, o) {
    const p = o.p === undefined ? 1 : o.p, fade = o.fade === undefined ? 1 : o.fade;
    if (p <= 0 || fade <= 0.01) return;
    const R = rng(o.id, o.d, 't');
    const dx = (R() - 0.5) * 1.8, dy = (R() - 0.5) * 1.8, rot = (R() - 0.5) * 0.007, ox = R() - 0.5, oy = R() - 0.5;
    g.save();
    g.font = `${o.weight || 600} ${o.size}px ${o.font || 'Hand'}`;
    g.textAlign = o.align || 'center'; g.textBaseline = 'alphabetic';
    const tw = g.measureText(str).width, left = (o.align === 'left') ? x : x - tw / 2;
    g.translate(x + dx, y + dy); g.rotate(rot); g.translate(-x, -y);
    if (p < 1) { g.beginPath(); g.rect(left - 30, y - o.size * 1.3, (tw + 60) * p, o.size * 1.8); g.clip(); }
    g.globalAlpha = fade * (o.alpha === undefined ? 1 : o.alpha);
    g.fillStyle = o.color; g.fillText(str, x, y);
    g.globalAlpha *= 0.45; g.lineWidth = 1.3; g.strokeStyle = o.color; g.strokeText(str, x + ox * 2, y + oy * 2);
    g.restore();
  }

  // ---------- ИЕРОГЛИФ: штриховка внутри формы + кипящий контур, пишется сверху вниз ----------
  let glyphBuf = null;
  function glyph(g, ch, x, y, o) {
    const p = o.p === undefined ? 1 : o.p, fade = o.fade === undefined ? 1 : o.fade;
    if (p <= 0 || fade <= 0.01) return;
    const S = o.size, B = Math.ceil(S * 1.5);
    if (!glyphBuf || glyphBuf.width < B) { glyphBuf = document.createElement('canvas'); glyphBuf.width = glyphBuf.height = B; }
    const b = glyphBuf.getContext('2d');
    b.setTransform(1, 0, 0, 1, 0, 0); b.globalCompositeOperation = 'source-over'; b.clearRect(0, 0, B, B);
    const font = `${S}px Glyph`, cx = B / 2, cy = B / 2;
    // штриховка тона
    const box = [[0, 0], [B, 0], [B, B], [0, B]];
    b.fillStyle = o.fill; b.globalAlpha = o.base === undefined ? 0.55 : o.base; b.fillRect(0, 0, B, B); b.globalAlpha = 1;
    hatch(b, box, { screen: true, id: o.id + 'h', d: o.d, angle: o.angle || 62, spacing: o.spacing || 5, color: o.tone || o.fill, w: 2.4, alpha: 0.9, maxLen: 40, ends: 0 });
    hatch(b, box, { screen: true, id: o.id + 'h2', d: o.d, angle: (o.angle || 62) - 75, spacing: 9, color: o.fill, w: 2, alpha: 0.9, maxLen: 30, ends: 0 });
    b.globalCompositeOperation = 'destination-in';
    b.font = font; b.textAlign = 'center'; b.textBaseline = 'middle'; b.fillStyle = '#000';
    b.fillText(ch, cx, cy);
    b.globalCompositeOperation = 'source-over';
    const R = rng(o.id, o.d, 'g');
    // кипящий контур карандашом
    for (let k = 0; k < 2; k++) {
      b.globalAlpha = k ? 0.5 : 0.95; b.lineWidth = k ? 1.6 : (o.lineW || 4); b.strokeStyle = o.line;
      b.strokeText(ch, cx + (R() - 0.5) * 2.4, cy + (R() - 0.5) * 2.4);
    }
    b.globalAlpha = 1;
    g.save();
    g.globalAlpha = fade;
    if (p < 1) { g.beginPath(); g.rect(x - B / 2, y - B / 2, B, B * p); g.clip(); }
    const sc = o.scale || 1;
    g.translate(x, y); g.scale(sc, sc);
    g.drawImage(glyphBuf, 0, 0, B, B, -B / 2, -B / 2, B, B);
    g.restore();
  }

  // ---------- БУМАГА: зерно, волокна, пятна, ластик, призраки линий ----------
  function hexA(hex, a) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  }
  function makePaper(pal) {
    const c = document.createElement('canvas'); c.width = W; c.height = H;
    const g = c.getContext('2d'), R = rng('paper', pal.name);
    g.fillStyle = pal.paper; g.fillRect(0, 0, W, H);
    for (let i = 0; i < 140; i++) { // пятнистость
      const x = R() * W, y = R() * H, r = 60 + R() * 220, col = R() < 0.5 ? pal.paperDark : pal.paperLight;
      const gr = g.createRadialGradient(x, y, 0, x, y, r);
      gr.addColorStop(0, hexA(col, 0.02 + R() * 0.035)); gr.addColorStop(1, hexA(col, 0));
      g.fillStyle = gr; g.fillRect(x - r, y - r, 2 * r, 2 * r);
    }
    g.lineCap = 'round';
    for (let i = 0; i < 2800; i++) { // волокна
      const x = R() * W, y = R() * H, L = 5 + R() * 28, a = R() * Math.PI, bend = (R() - 0.5) * 8;
      g.strokeStyle = hexA(R() < 0.6 ? pal.paperDark : pal.paperLight, 0.06 + R() * 0.12); g.lineWidth = 0.5 + R() * 0.9;
      g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + Math.cos(a) * L / 2 - Math.sin(a) * bend, y + Math.sin(a) * L / 2 + Math.cos(a) * bend, x + Math.cos(a) * L, y + Math.sin(a) * L); g.stroke();
    }
    for (let i = 0; i < 2; i++) { // следы от чашки
      const x = 150 + R() * 780, y = 200 + R() * 1300, r = 90 + R() * 70;
      g.strokeStyle = hexA(pal.paperDark, 0.07); g.lineWidth = 3 + R() * 5;
      g.beginPath(); g.arc(x, y, r, R() * 6, R() * 6 + 4.6 + R()); g.stroke();
      g.fillStyle = hexA(pal.paperDark, 0.025); g.beginPath(); g.arc(x, y, r, 0, 7); g.fill();
    }
    for (let i = 0; i < 7; i++) { // следы ластика
      const x = R() * W, y = R() * H; g.save(); g.translate(x, y); g.rotate(R() * Math.PI);
      const gr = g.createRadialGradient(0, 0, 0, 0, 0, 90); gr.addColorStop(0, hexA(pal.paperLight, 0.16)); gr.addColorStop(1, hexA(pal.paperLight, 0));
      g.scale(1.8, 0.5); g.fillStyle = gr; g.beginPath(); g.arc(0, 0, 90, 0, 7); g.fill(); g.restore();
    }
    for (let i = 0; i < 9; i++) { // недотёртые призраки линий
      const pts = []; let x = R() * W, y = R() * H, a = R() * 6.28;
      for (let k = 0; k < 14; k++) { pts.push([x, y]); a += (R() - 0.5) * 0.6; x += Math.cos(a) * 22; y += Math.sin(a) * 22; }
      g.globalAlpha = 1; pencil(g, pts, { screen: true, id: 'ghost' + i, d: 0, color: pal.soft, w: 2, alpha: 0.07, sketch: false });
    }
    const img = g.getImageData(0, 0, W, H), dd = img.data, gr = pal.grain;
    for (let i = 0; i < dd.length; i += 4) { const n = (R() - 0.5) * gr; dd[i] += n; dd[i + 1] += n; dd[i + 2] += n; }
    g.putImageData(img, 0, 0);
    const vg = g.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * 0.75);
    vg.addColorStop(0, hexA(pal.paperDark, 0)); vg.addColorStop(1, hexA(pal.paperDark, 0.18));
    g.fillStyle = vg; g.fillRect(0, 0, W, H);
    return c;
  }
  // зерно карандаша: выбивает пиксели из штрихов там, где бумага «не взяла» графит
  function makeTooth() {
    const c = document.createElement('canvas'); c.width = W; c.height = H;
    const g = c.getContext('2d'), img = g.createImageData(W, H), dd = img.data, R = rng('tooth');
    for (let i = 0; i < dd.length; i += 4) { const r = R(); dd[i + 3] = r < 0.34 ? 90 + R() * 165 : 0; }
    g.putImageData(img, 0, 0); return c;
  }

  // ---------- ПАЛИТРЫ: бумага + роли цветов ----------
  const PALETTES = {
    kraft: { name: 'kraft', paper: '#c4a27a', paperDark: '#7d5f3e', paperLight: '#e6cfab', line: '#2f2118', soft: '#5a432f', guide: '#7b6047', light: '#f7f0e3', cold: '#3b5878', warm: '#e2a21c', seal: '#ad2f26', wash: '#f2b544', grain: 20 },
    ink:   { name: 'ink',   paper: '#efe8d9', paperDark: '#a89c84', paperLight: '#fbf8f0', line: '#1b1917', soft: '#4c4741', guide: '#a39a8a', light: '#93a8b4', cold: '#557488', warm: '#c88a12', seal: '#b2241c', wash: '#f4c86a', grain: 14 },
  };

  window.PENCIL = { W, H, rng, hash, clamp, seg, lerp, ease, easeIO, easeOut, life, resample, smooth, ellipse, pod, along, CAM, pencil, hatch, hand, glyph, makePaper, makeTooth, hexA, PALETTES };
})();
