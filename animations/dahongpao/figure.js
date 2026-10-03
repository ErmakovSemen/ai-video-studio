// Карандашная кукла: скелет с суставами -> халат, рукава, голова, шапка. Позы, смешивание, ходьба.
// Углы в градусах. Ноги/руки: от направления «вниз», плюс = вперёд (куда смотрит герой).
// Корпус: от «вверх», плюс = наклон вперёд. Руки считаются относительно корпуса.
(function () {
  'use strict';
  const P = window.PENCIL;
  const { pencil, hatch, ellipse, lerp, CAM } = P;
  const D = Math.PI / 180;

  const POSES = {
    stand:   { hipY: 0.5,  lean: 0,  head: 0,   th: [3, -3],    kn: [0, 0],     sh: [8, -6],    el: [14, 12] },
    stagger: { hipY: 0.48, lean: 22, head: 18,  th: [12, -14],  kn: [-10, -4],  sh: [34, -8],   el: [34, 22] },
    kneel:   { hipY: 0.27, lean: 38, head: 28,  th: [6, -4],    kn: [-95, -85], sh: [50, 22],   el: [30, 40] },
    lie:     { hipY: 0.07, lean: 86, head: -14, th: [-82, -88], kn: [-6, -12],  sh: [168, 150], el: [6, 14] },
    sit:     { hipY: 0.06, lean: -8, head: 6,   th: [84, 78],   kn: [2, 8],     sh: [24, 8],    el: [46, 30] },
    drink:   { hipY: 0.06, lean: -12, head: -16, th: [84, 78],  kn: [2, 8],     sh: [118, 8],   el: [118, 30] },
    crouch:  { hipY: 0.3,  lean: 42, head: 16,  th: [62, 8],    kn: [-82, -64], sh: [56, 30],   el: [26, 10] },
    pour:    { hipY: 0.3,  lean: 46, head: 22,  th: [62, 8],    kn: [-82, -64], sh: [82, 30],   el: [6, 10] },
    offer:   { hipY: 0.32, lean: 30, head: 10,  th: [62, 8],    kn: [-82, -64], sh: [92, 30],   el: [-4, 10] },
    bow:     { hipY: 0.49, lean: 40, head: 14,  th: [0, 0],     kn: [0, 0],     sh: [6, 2],     el: [84, 80] },
    hold:    { hipY: 0.5,  lean: -6, head: -10, th: [3, -3],    kn: [0, 0],     sh: [158, 146], el: [12, 22] },
    throw:   { hipY: 0.48, lean: 18, head: 4,   th: [22, -16],  kn: [-6, -12],  sh: [98, 86],   el: [0, 4] },
  };

  function mix(a, b, u) {
    const o = {};
    for (const k in a) o[k] = Array.isArray(a[k]) ? a[k].map((v, i) => lerp(v, b[k][i], u)) : lerp(a[k], b[k], u);
    return o;
  }
  // цикл ходьбы: фаза в радианах; amp — размах шага
  function walk(phase, amp = 13) {
    const s = Math.sin(phase), c = Math.cos(phase);
    return { hipY: 0.5 - 0.008 * Math.abs(c), lean: 5, head: 2, th: [amp * s, -amp * s],
      kn: [-Math.max(0, c) * 26 - 3, -Math.max(0, -c) * 26 - 3], sh: [-16 * s, 16 * s], el: [16, 16] };
  }

  function hull(pts) { // выпуклая оболочка (монотонная цепь)
    const p = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const lo = [], up = [];
    for (const q of p) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], q) <= 0) lo.pop(); lo.push(q); }
    for (let i = p.length - 1; i >= 0; i--) { const q = p[i]; while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], q) <= 0) up.pop(); up.push(q); }
    return lo.slice(0, -1).concat(up.slice(0, -1));
  }
  function blob(c, rx, ry, n = 6) { // «эллипс» как набор точек для оболочки
    const o = []; for (let i = 0; i < n; i++) { const a = i / n * 2 * Math.PI; o.push([c[0] + Math.cos(a) * rx, c[1] + Math.sin(a) * ry]); } return o;
  }
  function erase(g, polyW) { // фигура непрозрачна: стираем то, что за ней
    const q = polyW.map(CAM.map);
    g.save(); g.globalCompositeOperation = 'destination-out'; g.beginPath();
    q.forEach((p, i) => (i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1]))); g.closePath(); g.fill(); g.restore();
  }

  function rig(p) {
    const H = p.H, dir = p.dir || 1;
    const Lt = 0.25 * H, Ls = 0.25 * H, T = 0.31 * H, La = 0.14 * H, Lf = 0.125 * H, R = 0.075 * H;
    const dn = a => [Math.sin(a * D) * dir, Math.cos(a * D)];
    const up = a => [Math.sin(a * D) * dir, -Math.cos(a * D)];
    const add = (a, v, l) => [a[0] + v[0] * l, a[1] + v[1] * l];
    const hip = [p.x, p.gy - p.hipY * H];
    const legs = [0, 1].map(i => { const k = add(hip, dn(p.th[i]), Lt); return { k, f: add(k, dn(p.th[i] + p.kn[i]), Ls), a: p.th[i] + p.kn[i] }; });
    const neck = add(hip, up(p.lean), T);
    const head = add(neck, up(p.lean + p.head), R * 1.25);
    const sh = add(neck, up(p.lean), -0.035 * H);
    const arms = [0, 1].map(i => { const e = add(sh, dn(p.sh[i] + p.lean), La); return { e, h: add(e, dn(p.sh[i] + p.lean + p.el[i]), Lf) }; });
    const u = up(p.lean), n = [-u[1], u[0]];
    return { H, dir, hip, legs, neck, head, sh, arms, R, u, n, lean: p.lean, hd: p.head, add, up };
  }

  // c: { id, d, x, gy, H, dir, pose, robe (цвет халата), inner, kind: 'student'|'monk', prop, fade }
  function draw(g, c, pal) {
    const r = rig(Object.assign({ x: c.x, gy: c.gy, H: c.H, dir: c.dir }, c.pose));
    const H = r.H, fade = c.fade === undefined ? 1 : c.fade, id = c.id, d = c.d;
    if (fade <= 0.01) return r;
    const L = { d, fade, color: pal.line };
    const ln = (pts, k, o = {}) => pencil(g, pts, Object.assign({ id: id + k, w: 3.2 }, L, o));
    const front = r.legs[0].k[0] * r.dir >= r.legs[1].k[0] * r.dir ? 0 : 1, back = 1 - front;
    // 1) дальняя рука и нога
    const arm = (i, k) => {
      const A = r.arms[i];
      const sl = hull(blob(r.sh, 0.028 * H, 0.028 * H).concat(blob(A.e, 0.03 * H, 0.03 * H), blob(A.h, 0.042 * H, 0.036 * H)));
      erase(g, sl);
      hatch(g, sl, { id: id + k + 'sh', d, color: c.robe, angle: 60, spacing: 7, w: 2, alpha: 0.75, fade });
      ln(sl, k + 'so', { closed: true, w: 2.8 });
      const hand = ellipse(A.h[0] + r.dir * 0.02 * H, A.h[1] + 0.012 * H, 0.022 * H, 0.022 * H, 0, 14);
      erase(g, hand); ln(hand, k + 'hd', { closed: true, w: 2.2, sketch: false });
    };
    const leg = (i, k) => {
      const Lg = r.legs[i];
      ln([[lerp(Lg.k[0], Lg.f[0], 0.4), lerp(Lg.k[1], Lg.f[1], 0.4)], Lg.f], k + 'shin', { w: 3 });
      const fa = (Lg.a + 90) * D; // ступня перпендикулярно голени, вперёд
      ln([Lg.f, [Lg.f[0] + Math.sin(fa) * r.dir * 0.07 * H, Lg.f[1] + Math.cos(fa) * 0.07 * H]], k + 'foot', { w: 4.4, sketch: false });
    };
    leg(back, 'lb'); arm(back, 'ab');
    // 2) халат: выпуклая оболочка шеи, бёдер, колен и подола
    const hem = Lg => [lerp(Lg.k[0], Lg.f[0], 0.55), lerp(Lg.k[1], Lg.f[1], 0.55)];
    const robePts = [].concat(blob(r.neck, 0.05 * H, 0.03 * H), blob(r.hip, 0.1 * H, 0.06 * H),
      blob(r.legs[0].k, 0.05 * H, 0.05 * H), blob(r.legs[1].k, 0.05 * H, 0.05 * H),
      blob(hem(r.legs[0]), 0.07 * H, 0.03 * H), blob(hem(r.legs[1]), 0.07 * H, 0.03 * H));
    const robe = hull(robePts);
    erase(g, robe);
    hatch(g, robe, { id: id + 'rh', d, color: c.robe, angle: 70, spacing: 6, w: 2.1, alpha: 0.8, fade });
    hatch(g, robe, { id: id + 'rh2', d, color: c.robe, angle: -20, spacing: 13, w: 1.6, alpha: 0.5, fade });
    ln(robe, 'robe', { closed: true, w: 3.4 });
    ln([r.hip, r.add(r.hip, r.n, 0.09 * H * r.dir)], 'belt', { w: 3, color: pal.line, sketch: false }); // пояс
    if (c.prop === 'books') { // узелок с книгами за спиной
      const bk = r.add(r.add(r.neck, r.u, -0.12 * H), r.n, -0.09 * H * r.dir);
      const box = hull(blob(bk, 0.07 * H, 0.09 * H, 4));
      erase(g, box); hatch(g, box, { id: id + 'bk', d, color: pal.soft, angle: 20, spacing: 6, w: 1.8, alpha: 0.6, fade });
      ln(box, 'bko', { closed: true, w: 2.6 });
    }
    leg(front, 'lf');
    // 3) голова
    const hc = r.head, R = r.R;
    const headPts = ellipse(hc[0], hc[1], R * 0.92, R, (r.lean + r.hd) * D * r.dir, 30);
    erase(g, headPts);
    ln(headPts, 'head', { closed: true, w: 3 });
    const fwd = r.up(r.lean + r.hd + 90), upv = r.up(r.lean + r.hd);
    const at = (a, b) => [hc[0] + fwd[0] * a * R + upv[0] * b * R, hc[1] + fwd[1] * a * R + upv[1] * b * R];
    ln([at(0.9, 0.05), at(1.15, -0.12), at(0.92, -0.22)], 'nose', { w: 2.4, sketch: false });
    const eye = at(0.5, 0.12);
    g.globalAlpha = fade; g.fillStyle = pal.line; const e = CAM.map(eye); g.beginPath(); g.arc(e[0], e[1], 3.2, 0, 7); g.fill(); g.globalAlpha = 1;
    ln([at(-0.15, 0.1), at(-0.3, -0.05), at(-0.12, -0.2)], 'ear', { w: 2, sketch: false });
    if (c.kind === 'student') { // шапка учёного: чёрный «квадратный» колпак + две ленты
      const cap = [at(-0.95, 0.5), at(-0.75, 1.25), at(0.6, 1.3), at(0.8, 0.55)];
      erase(g, cap); hatch(g, cap, { id: id + 'cap', d, color: pal.line, angle: 30, spacing: 4, w: 2, alpha: 0.9, fade });
      ln(cap, 'capo', { closed: true, w: 2.8 });
      ln([at(-0.9, 0.7), at(-1.6, 0.2), at(-1.75, -0.5)], 'rib', { w: 2.2 });
    } else { // монах: бритая голова, лёгкая тень
      hatch(g, headPts, { id: id + 'bald', d, color: pal.soft, angle: 40, spacing: 9, w: 1.4, alpha: 0.35, fade });
    }
    // 4) ближняя рука поверх всего
    arm(front, 'af');
    r.handFront = r.arms[front].h; r.handBack = r.arms[back].h; r.mouth = at(1.0, -0.35);
    return r;
  }

  window.FIGURE = { POSES, mix, walk, draw, hull, erase };
})();
