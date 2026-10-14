// «Карп у Врат Дракона» — дневник: детальные страницы, элементы появляются по одному, листание с уголка.
(function () {
  'use strict';
  const P = window.PENCIL, J = window.JOURNAL, T = window.T;
  const { W, H, rng, seg, lerp, ease, easeIO, easeOut, smooth, ellipse, pod, CAM, pencil, hatch, hand, glyph, wash } = P;
  const C = J.COLORS, el = id => T.el[id];

  let pal, desk, tooth, pagePaper, og, bufs = [], layer, lg;
  function init(theme, canvas) {
    pal = P.PALETTES[theme];
    desk = P.makePaper(Object.assign({}, pal, { name: 'desk', paper: '#6b4f37', paperLight: '#8a6a4c', paperDark: '#4a3424', grain: 18 }));
    tooth = P.makeTooth(); J.setTooth(tooth);
    pagePaper = J.makePage(pal);
    og = canvas.getContext('2d');
    bufs = T.pages.map(() => J.mk(W, H));
    layer = J.mk(W, H); lg = layer.getContext('2d'); // прозрачный слой рисунка: «ластик» стирает только его, не бумагу
  }

  // ---------- рисунки ----------
  // карп: тело вдоль +x (голова справа); m — преобразование локальных точек
  function carp(g, x, y, s, ang, d, id, p = 1, o = {}) {
    const c = Math.cos(ang), sn = Math.sin(ang), m = q => [x + (q[0] * c - q[1] * sn) * s, y + (q[0] * sn + q[1] * c) * s];
    const top = [], bot = [];
    for (let i = 0; i <= 24; i++) { const u = i / 24, xx = lerp(-100, 112, u), hw = 46 * Math.pow(Math.sin(Math.PI * Math.pow(u, 0.78)), 0.75); top.push([xx, -hw]); bot.push([xx, hw * 0.92]); }
    const body = top.concat(bot.reverse()).map(m);
    const tail = [[-92, -4], [-150, -56], [-128, -6], [-132, 4], [-152, 54], [-92, 6]].map(m);
    const dorsal = [[-40, -40], [-8, -66], [40, -44]].map(m), pect = pod([42, 22], [6, 62], 12, 0.8, 10).map(m);
    if (o.silhouette) {
      P.erasePolyLocal(g, body);
      wash(g, body, { id: id + 'sw', color: o.fill || pal.soft, alpha: 0.35, layers: 3, spread: 2, p });
      pencil(g, body, { id: id + 'b', d, color: pal.line, w: 2, closed: true, p, sketch: false });
      pencil(g, tail, { id: id + 't', d, color: pal.line, w: 2, closed: true, p, sketch: false });
      return;
    }
    P.erasePolyLocal(g, body.concat(tail));
    wash(g, tail, { id: id + 'tw', color: o.fill || C.coral, alpha: 0.35, layers: 5, spread: 4, p: seg(p, 0.3, 0.8) });
    wash(g, body, { id: id + 'bw', color: o.fill || C.gold, alpha: 0.3, layers: 7, spread: 5, p: seg(p, 0.3, 0.8) });
    wash(g, [[-40, -40], [20, -46], [10, 10], [-50, 6]].map(m), { id: id + 'kp', color: C.red, alpha: 0.4, layers: 5, spread: 6, p: seg(p, 0.5, 0.9) }); // пятно кои
    hatch(g, body, { id: id + 'bh', d, color: pal.warm, angle: ang * 57 + 70, spacing: 6, w: 1.6, alpha: 0.6, screen: false, p: seg(p, 0.5, 1) });
    for (let xx = -70; xx <= 50; xx += 17) for (let yy = -26; yy <= 26; yy += 15) { // чешуя дугами
      if (Math.abs(yy) > 40 * Math.sin(Math.PI * Math.pow((xx + 100) / 212, 0.78)) - 8) continue;
      const arc = []; for (let k = 0; k <= 6; k++) { const a = -Math.PI / 2 + k * Math.PI / 6; arc.push([xx + Math.cos(a) * 7, yy + Math.sin(a) * 7]); }
      pencil(g, arc.map(m), { id: id + 'sc' + xx + '_' + yy, d, color: pal.line, w: 1.3, alpha: 0.55, p: seg(p, 0.6, 1), sketch: false });
    }
    pencil(g, body, { id: id + 'b', d, color: pal.line, w: 3, closed: true, p: seg(p, 0, 0.5) });
    pencil(g, tail, { id: id + 't', d, color: pal.line, w: 2.8, closed: true, p: seg(p, 0.2, 0.6) });
    [[-138, -40], [-140, 0], [-138, 40]].forEach((q, i) => pencil(g, [[-96, q[1] * 0.1], q].map(m), { id: id + 'tr' + i, d, color: pal.line, w: 1.3, alpha: 0.6, p: seg(p, 0.5, 0.8), sketch: false }));
    wash(g, dorsal.concat([[40, -40], [-40, -38]].map(m)), { id: id + 'dw', color: C.coral, alpha: 0.35, layers: 4, spread: 3, p: seg(p, 0.4, 0.8) });
    pencil(g, dorsal, { id: id + 'd', d, color: pal.line, w: 2.6, p: seg(p, 0.3, 0.6) });
    pencil(g, pect, { id: id + 'pf', d, color: pal.line, w: 2.2, closed: true, p: seg(p, 0.4, 0.7) });
    pencil(g, [[66, -30], [58, 0], [66, 28]].map(m), { id: id + 'gl', d, color: pal.line, w: 2, p: seg(p, 0.4, 0.7) }); // жабра
    pencil(g, [[106, 10], [122, 24], [140, 22]].map(m), { id: id + 'us', d, color: pal.line, w: 1.8, p: seg(p, 0.6, 0.8), sketch: false }); // ус
    if (p > 0.6) { const e = m([82, -12]); g.fillStyle = pal.line; g.beginPath(); g.arc(e[0], e[1], 5.5 * Math.min(1.2, s), 0, 7); g.fill(); g.fillStyle = '#fff'; g.beginPath(); g.arc(e[0] + 1.5, e[1] - 1.5, 1.8, 0, 7); g.fill(); }
  }
  function waves(g, x0, x1, y, amp, n, d, id, p, col) {
    for (let k = 0; k < n; k++) {
      const pts = []; for (let x = x0; x <= x1; x += 10) pts.push([x, y + k * 26 + amp * Math.sin(x * 0.035 + k * 1.7)]);
      pencil(g, pts, { id: id + k, d, color: col || pal.cold, w: 2, alpha: 0.75, p: seg(p, k * 0.08, 0.5 + k * 0.08), sketch: false });
    }
  }
  function cloud(g, x, y, r, d, id, p) { // облако-«жуи» со спиралью
    const pts = []; for (let k = 0; k <= 48; k++) { const a = Math.PI + k / 48 * Math.PI; const rr = r * (1 + 0.22 * Math.abs(Math.sin(a * 3))); pts.push([x + Math.cos(a) * rr * 1.6, y + Math.sin(a) * rr]); }
    const poly = pts.concat([[x + r * 1.6, y + r * 0.35], [x - r * 1.6, y + r * 0.35]]);
    P.erasePolyLocal(g, poly);
    wash(g, poly, { id: id + 'w', color: '#ffffff', alpha: 0.5, layers: 5, spread: 6, p });
    wash(g, poly, { id: id + 'w2', color: pal.sky, alpha: 0.12, layers: 4, spread: 8, p });
    pencil(g, pts, { id, d, color: pal.line, w: 2.6, p });
    const sp = []; for (let k = 0; k < 30; k++) { const a = k * 0.42, rr = r * 0.5 * (1 - k / 34); sp.push([x - r * 0.4 + Math.cos(a) * rr, y - r * 0.15 + Math.sin(a) * rr * 0.8]); }
    pencil(g, sp, { id: id + 's', d, color: pal.line, w: 2, alpha: 0.8, p: seg(p, 0.4, 1), sketch: false });
    pencil(g, [[x - r * 1.6, y + r * 0.35], [x + r * 1.6, y + r * 0.35]], { id: id + 'b', d, color: pal.line, w: 2, alpha: 0.7, p, sketch: false });
  }

  // ---------- фото для полароидов (координаты внутри фото) ----------
  function photoRiver(g, w, h, lt, d) {
    const p = seg(lt, 0, 1.4);
    wash(g, [[-10, -10], [w + 10, -10], [w + 10, 140], [-10, 170]], { id: 'rsky', color: pal.sky, alpha: 0.12, layers: 6, spread: 20, p });
    const hills = smooth([[-10, 170], [120, 110], [260, 150], [420, 90], [560, 130], [w + 10, 100]], 6);
    wash(g, hills.concat([[w + 10, 220], [-10, 230]]), { id: 'rhw', color: pal.leaf, alpha: 0.12, layers: 6, spread: 10, p });
    pencil(g, hills, { id: 'rh', d, color: pal.line, w: 2.4, p });
    const bankL = smooth([[-10, 260], [180, 300], [360, 420], [520, h + 10]], 6), bankR = smooth([[300, 190], [500, 230], [640, 330], [w + 10, 420]], 6);
    const river = bankL.concat(bankR.slice().reverse());
    wash(g, river, { id: 'rw', color: pal.sky, alpha: 0.2, layers: 8, spread: 12, p });
    hatch(g, river, { id: 'rwh', d, color: pal.cold, angle: -30, spacing: 10, w: 1.4, alpha: 0.35, p });
    wash(g, bankL.concat([[-10, h + 10]]), { id: 'blw', color: pal.ochre, alpha: 0.12, layers: 6, spread: 10, p });
    wash(g, bankR.concat([[w + 10, 190]]), { id: 'brw', color: pal.leaf, alpha: 0.12, layers: 6, spread: 10, p });
    pencil(g, bankL, { id: 'bl', d, color: pal.line, w: 2.6, p });
    pencil(g, bankR, { id: 'br', d, color: pal.line, w: 2.6, p });
    for (let k = 0; k < 7; k++) { // волны течения
      const cx = 160 + k * 70, cy = 300 + k * 32, pts = [];
      for (let s = -40; s <= 40; s += 8) pts.push([cx + s, cy + s * 0.55 + 5 * Math.sin(s * 0.2)]);
      pencil(g, pts, { id: 'rv' + k, d, color: pal.cold, w: 1.8, alpha: 0.7, p: seg(lt, 0.3 + k * 0.05, 0.8 + k * 0.05), sketch: false });
    }
    [[250, 330], [330, 380], [420, 300], [470, 400], [380, 460], [540, 350], [300, 430], [560, 450], [460, 250]].forEach(([x, y], i) =>
      carp(g, x, y, 0.22, -0.55, d, 'rf' + i, seg(lt, 0.6 + i * 0.06, 1.0 + i * 0.06), { silhouette: true, fill: C.coral }));
  }
  function photoFalls(g, w, h, lt, d) {
    const p = seg(lt, 0, 1.3);
    wash(g, [[-10, -10], [w + 10, -10], [w + 10, 200], [-10, 200]], { id: 'fsky', color: pal.sky, alpha: 0.14, layers: 6, spread: 20, p });
    const lip = 170, pool = 470;
    const cl = smooth([[-10, 60], [120, 50], [250, 90], [300, lip], [290, 360], [320, h + 10]], 6).concat([[-10, h + 10]]);
    const cr = smooth([[w + 10, 40], [620, 60], [520, 100], [470, lip], [480, 360], [450, h + 10]], 6).concat([[w + 10, h + 10]]);
    [cl, cr].forEach((q, i) => {
      P.erasePolyLocal(g, q);
      wash(g, q, { id: 'fcw' + i, color: pal.stone, alpha: 0.18, layers: 8, spread: 10, p });
      hatch(g, q, { id: 'fch' + i, d, color: pal.line, angle: i ? 70 : 110, spacing: 6, w: 1.5, alpha: 0.45, p: seg(lt, 0.5, 1.3) });
      pencil(g, q.slice(0, -1), { id: 'fc' + i, d, color: pal.line, w: 3, p });
    });
    [[60, 40], [180, 30], [650, 30]].forEach(([x, y], i) => { // сосны на скалах
      pencil(g, [[x, y + 20], [x, y - 30]], { id: 'pt' + i, d, color: pal.line, w: 2, p, sketch: false });
      [[-24, 8], [-16, -6], [-10, -18]].forEach(([wd, dy], k) => pencil(g, [[x - wd * -1 - 0, y + dy], [x, y + dy - 14], [x - wd, y + dy]], { id: 'pn' + i + k, d, color: pal.line, w: 1.8, p, sketch: false }));
    });
    const fall = [[300, lip], [470, lip], [480, pool], [290, pool]];
    wash(g, fall, { id: 'fw', color: pal.sky, alpha: 0.25, layers: 6, spread: 4, p });
    for (let k = 0; k < 14; k++) { const x = 305 + k * 12; pencil(g, [[x, lip], [x + 3, pool - 10]], { id: 'fl' + k, d, color: k % 3 ? pal.cold : '#ffffff', w: k % 3 ? 1.6 : 3, alpha: 0.8, p: seg(lt, 0.4 + k * 0.03, 0.9 + k * 0.03), sketch: false }); }
    const poolP = ellipse(385, pool + 10, 260, 50, 0, 30);
    wash(g, poolP, { id: 'pw', color: '#ffffff', alpha: 0.5, layers: 5, spread: 10, p });
    waves(g, 120, 640, pool + 50, 6, 3, d, 'pwv', seg(lt, 0.6, 1.4));
    // ворота: перекладина над водопадом (древний знак Лунмэнь)
    const gate = [[262, lip - 72], [508, lip - 72], [500, lip - 52], [270, lip - 52]];
    wash(g, gate, { id: 'gw', color: C.red, alpha: 0.4, layers: 4, spread: 2, p: seg(lt, 0.8, 1.2) });
    pencil(g, gate, { id: 'gt', d, color: pal.line, w: 2.6, closed: true, p: seg(lt, 0.7, 1.1) });
    [[290, lip - 52], [480, lip - 52]].forEach(([x, y], i) => pencil(g, [[x, y], [x, lip]], { id: 'gp' + i, d, color: pal.line, w: 4, p: seg(lt, 0.8, 1.0) }));
    [[200, 540], [560, 530], [330, 560]].forEach(([x, y], i) => carp(g, x, y, 0.2, -1.1, d, 'ff' + i, seg(lt, 1.0 + i * 0.1, 1.4 + i * 0.1), { silhouette: true, fill: C.coral }));
  }
  function photoDragon(g, w, h, lt, d) {
    const p = seg(lt, 0, 1.6);
    wash(g, [[-10, -10], [w + 10, -10], [w + 10, h + 10], [-10, h + 10]], { id: 'dsky', color: pal.sky, alpha: 0.12, layers: 6, spread: 30, p });
    const spine = smooth([[40, 560], [150, 470], [270, 520], [380, 430], [470, 330], [560, 250], [600, 200]], 10);
    const L = spine.length, left = [], right = [];
    for (let i = 0; i < L; i++) {
      const a = spine[Math.max(0, i - 1)], b = spine[Math.min(L - 1, i + 1)], dx = b[0] - a[0], dy = b[1] - a[1], ln = Math.hypot(dx, dy) || 1;
      const wd = lerp(8, 40, Math.pow(i / (L - 1), 0.6));
      left.push([spine[i][0] - dy / ln * wd, spine[i][1] + dx / ln * wd]); right.push([spine[i][0] + dy / ln * wd, spine[i][1] - dx / ln * wd]);
    }
    const body = left.concat(right.slice().reverse());
    P.erasePolyLocal(g, body);
    wash(g, body, { id: 'dbw', color: C.gold, alpha: 0.35, layers: 8, spread: 4, p: seg(lt, 0.3, 1.0) });
    hatch(g, body, { id: 'dbh', d, color: pal.warm, angle: 40, spacing: 6, w: 1.5, alpha: 0.6, p: seg(lt, 0.5, 1.2) });
    for (let i = 4; i < L - 4; i += 4) { // чешуя
      const q = spine[i], arc = []; for (let k = 0; k <= 6; k++) { const a = Math.PI + k * Math.PI / 6; arc.push([q[0] + Math.cos(a) * 10, q[1] + Math.sin(a) * 10]); }
      pencil(g, arc, { id: 'dsc' + i, d, color: pal.line, w: 1.4, alpha: 0.6, p: seg(lt, 0.8, 1.2), sketch: false });
    }
    for (let i = 6; i < L - 6; i += 5) { const a = right[i], b = right[i + 2]; pencil(g, [a, [(a[0] + b[0]) / 2 + 6, (a[1] + b[1]) / 2 - 22], b], { id: 'dsp' + i, d, color: pal.line, w: 2, p: seg(lt, 0.7, 1.1), sketch: false }); } // гребень
    pencil(g, left, { id: 'dl', d, color: pal.line, w: 3, p: seg(lt, 0.1, 0.8) });
    pencil(g, right, { id: 'dr', d, color: pal.line, w: 3, p: seg(lt, 0.1, 0.8) });
    // голова
    const hx = 600, hy = 200, head = [[hx - 20, hy - 44], [hx + 60, hy - 52], [hx + 112, hy - 28], [hx + 118, hy - 8], [hx + 70, hy + 6], [hx + 104, hy + 22], [hx + 60, hy + 38], [hx - 10, hy + 40]];
    P.erasePolyLocal(g, head);
    wash(g, head, { id: 'dhw', color: C.gold, alpha: 0.4, layers: 6, spread: 3, p: seg(lt, 0.6, 1.1) });
    pencil(g, head, { id: 'dh', d, color: pal.line, w: 3, closed: true, p: seg(lt, 0.5, 1.0) });
    pencil(g, [[hx + 40, hy - 50], [hx + 10, hy - 100], [hx - 20, hy - 120]], { id: 'dho', d, color: pal.line, w: 3, p: seg(lt, 0.9, 1.2) }); // рог
    pencil(g, [[hx + 20, hy - 74], [hx - 6, hy - 80]], { id: 'dho2', d, color: pal.line, w: 2.4, p: seg(lt, 1.0, 1.2), sketch: false });
    pencil(g, smooth([[hx + 112, hy - 20], [hx + 150, hy - 60], [hx + 130, hy - 110], [hx + 150, hy - 150]], 6), { id: 'dwh1', d, color: pal.line, w: 2, p: seg(lt, 1.0, 1.4) }); // усы
    pencil(g, smooth([[hx + 100, hy + 20], [hx + 140, hy + 60], [hx + 120, hy + 100]], 6), { id: 'dwh2', d, color: pal.line, w: 2, p: seg(lt, 1.0, 1.4) });
    if (lt > 0.9) { g.fillStyle = pal.line; g.beginPath(); g.arc(hx + 56, hy - 24, 6, 0, 7); g.fill(); g.fillStyle = '#fff'; g.beginPath(); g.arc(hx + 58, hy - 26, 2, 0, 7); g.fill(); }
    pencil(g, [[hx + 70, hy + 6], [hx + 30, hy + 8]], { id: 'dmo', d, color: pal.line, w: 2, p: seg(lt, 0.9, 1.1), sketch: false });
    cloud(g, 140, 600, 70, d, 'cl1', seg(lt, 0.9, 1.5)); cloud(g, 330, 470, 55, d, 'cl2', seg(lt, 1.0, 1.6)); cloud(g, 520, 330, 50, d, 'cl3', seg(lt, 1.1, 1.7)); cloud(g, 120, 160, 60, d, 'cl4', seg(lt, 1.2, 1.8));
  }

  // ---------- страницы (локальное время lt, экранные координаты) ----------
  const TX = J.PX + J.PW / 2 + 20; // центр текстовой колонки
  function text(g, lines, y0, size, lt, t0, step, d, id, color) {
    lines.forEach((s, i) => hand(g, s, TX, y0 + i * size * 1.1, { id: id + i, d, size, color: color || C.ink, p: seg(lt, t0 + i * step, t0 + (i + 1) * step) }));
  }
  function pageCover(g, lt, d) {
    J.tab(g, 820, C.red, '01', d);
    J.tape(g, { id: 'ctape', a: [110, 190], b: [380, 150], color: C.coral, t: el('cover.tape') }, lt, d);
    text(g, ['Легенда'], 380, 150, lt, el('cover.title'), 0.6, d, 'ct');
    text(g, ['о карпе'], 530, 150, lt, el('cover.title') + 0.6, 0.6, d, 'ct2');
    pencil(g, smooth([[330, 570], [500, 585], [700, 565], [790, 580]], 6), { id: 'cul', d, color: C.red, w: 5, screen: true, p: seg(lt, 1.7, 2.0) });
    J.doodleStars(g, [[250, 270, 22, 1.2], [860, 330, 16, 1.35], [820, 500, 12, 1.5]], lt, d, 'cs');
    waves(g, 110, 980, 1440, 9, 3, d, 'cw', seg(lt, 0.0, 1.2));
    J.sticker(g, { id: 'koi', x: 540, y: 900, rot: -0.08, t: el('cover.koi'), shape: { type: 'circle', r: 230 }, bg: '#dcebf2',
      draw: (b, w, h, dd) => { waves(b, -10, w + 10, 120, 7, 4, dd, 'kw', 1, pal.cold); waves(b, -10, w + 10, 360, 7, 2, dd, 'kw2', 1, pal.cold); carp(b, w / 2 + 10, h / 2 + 10, 1.25, -0.25, dd, 'kc', 1);
        [[110, 170, 9], [140, 130, 6], [370, 120, 7]].forEach(([x, y, r], i) => pencil(b, ellipse(x, y, r, r, 0, 12), { id: 'kb' + i, d: dd, color: pal.cold, w: 2, closed: true, sketch: false })); } }, lt, d);
    J.sticky(g, { id: 'cnote', x: 780, y: 1250, w: 320, h: 270, rot: 0.08, t: el('cover.note'), color: C.yellow, lines: ['Китай,', 'река Хуанхэ'], size: 60 }, lt, d);
    J.stamp(g, { id: 'cst', x: 270, y: 1250, size: 90, rot: -0.12, t: el('cover.stamp'), chars: '龙门' }, lt, d);
  }
  function pageRiver(g, lt, d) {
    J.tab(g, 820, C.red, '02', d);
    J.polaroid(g, { id: 'rph', x: 545, y: 690, w: 740, h: 520, rot: -0.04, t: el('river.photo'), draw: photoRiver, caption: 'Хуанхэ' }, lt, d);
    J.tape(g, { id: 'rt1', a: [150, 330], b: [330, 300], color: C.mint, t: el('river.tape1') }, lt, d);
    J.tape(g, { id: 'rt2', a: [760, 300], b: [940, 340], color: C.coral, t: el('river.tape2') }, lt, d);
    text(g, ['Каждую весну тысячи', 'карпов плывут вверх', 'по реке Хуанхэ'], 1180, 78, lt, el('river.text'), 0.55, d, 'rtx');
    J.arrow(g, { id: 'rar', t: el('river.arrow'), pts: smooth([[230, 1470], [170, 1400], [190, 1260], [260, 1120]], 8) }, lt, d);
    hand(g, 'против течения!', 470, 1480, { id: 'rpt', d, size: 62, color: C.red, p: seg(lt, el('river.arrow') + 0.3, el('river.arrow') + 0.8) });
    J.sticker(g, { id: 'rbadge', x: 880, y: 1450, rot: 0.15, t: el('river.badge'), shape: { type: 'star', r: 95 }, bg: C.yellow,
      draw: (b, w, h, dd) => hand(b, '1000+', w / 2, h / 2 + 12, { id: 'rb', d: dd, size: 44, color: C.ink }) }, lt, d);
  }
  function pageFalls(g, lt, d) {
    J.tab(g, 820, C.red, '03', d);
    J.polaroid(g, { id: 'fph', x: 545, y: 640, w: 740, h: 600, rot: 0.035, t: el('falls.photo'), draw: photoFalls, caption: 'Лунмэнь' }, lt, d);
    J.tape(g, { id: 'ft1', a: [450, 230], b: [640, 245], color: C.sky, t: el('falls.tape1') }, lt, d);
    J.marker(g, { t: el('falls.hl'), x0: 300, x1: 800, y: 1290, h: 64 }, lt);
    text(g, ['Наверху их ждёт водопад', '«Врата Дракона»'], 1200, 82, lt, el('falls.text'), 0.6, d, 'ftx');
    J.sticky(g, { id: 'fnote', x: 300, y: 1450, w: 330, h: 230, rot: -0.07, t: el('falls.note'), color: C.mint, lines: ['почти все', 'сдаются'], size: 58 }, lt, d);
    J.stamp(g, { id: 'fst', x: 820, y: 1450, size: 78, rot: 0.1, t: el('falls.stamp'), chars: '龙门' }, lt, d);
  }
  function pageLeap(g, lt, d) {
    J.tab(g, 820, C.red, '04', d);
    text(g, ['Но один карп', 'прыгнул выше всех!'], 250, 92, lt, el('leap.text'), 0.6, d, 'ltx');
    const t0 = el('leap.draw') + 0.3, p = seg(lt, t0, t0 + 1.3);
    const cr = smooth([[1040, 420], [860, 460], [760, 560], [730, 760], [760, 1000], [720, 1250], [1040, 1250]], 6);
    wash(g, cr, { id: 'lcw', color: pal.stone, alpha: 0.16, layers: 8, spread: 10, p });
    hatch(g, cr, { id: 'lch', d, color: pal.line, angle: 70, spacing: 7, w: 1.5, alpha: 0.4, screen: true, p });
    pencil(g, cr.slice(0, -1), { id: 'lc', d, color: pal.line, w: 3.2, screen: true, p });
    for (let k = 0; k < 9; k++) { const x = 760 - k * 22; pencil(g, [[x, 560], [x - 10, 1180]], { id: 'lf' + k, d, color: k % 3 ? pal.cold : '#ffffff', w: k % 3 ? 2 : 4, alpha: 0.85, screen: true, p: seg(lt, t0 + k * 0.04, t0 + 0.5 + k * 0.04), sketch: false }); }
    wash(g, [[540, 540], [770, 540], [760, 1190], [530, 1190]], { id: 'lfw', color: pal.sky, alpha: 0.2, layers: 6, spread: 6, p });
    wash(g, [[100, 1180], [1000, 1180], [1000, 1330], [100, 1330]], { id: 'lpw', color: pal.sky, alpha: 0.18, layers: 6, spread: 12, p });
    waves(g, 110, 1000, 1210, 8, 4, d, 'lw', p);
    pencil(g, smooth([[180, 1170], [260, 980], [360, 820], [430, 760]], 8), { id: 'ltr', d, color: pal.cold, w: 2.2, alpha: 0.6, screen: true, p: seg(lt, t0 + 0.5, t0 + 1.0) }); // траектория прыжка
    [[200, 1120], [240, 1090], [170, 1080], [260, 1140]].forEach(([x, y], i) => pencil(g, pod([x, y + 18], [x + (i - 1.5) * 8, y - 10], 6, 0.5, 8), { id: 'ld' + i, d, color: pal.cold, w: 2, closed: true, screen: true, p: seg(lt, t0 + 0.7, t0 + 1.0), sketch: false })); // брызги
    carp(g, 500, 700, 1.7, -0.75, d, 'lcarp', seg(lt, t0 + 0.2, t0 + 1.4));
    [[0, 0], [1, 30], [2, 60]].forEach(([k, o]) => pencil(g, smooth([[320 - o, 900 + o], [360 - o, 830 + o * 0.5], [410 - o, 800]], 6), { id: 'lml' + k, d, color: pal.line, w: 2.2, alpha: 0.7, screen: true, p: seg(lt, t0 + 1.0, t0 + 1.3), sketch: false }));
    const tb = el('leap.burst');
    [[700, 520, 60, 0], [330, 520, 48, 0.12], [690, 900, 44, 0.24], [250, 760, 38, 0.36]].forEach(([x, y, r, dt], i) =>
      J.sticker(g, { id: 'lst' + i, x, y, rot: i * 0.3 - 0.4, t: tb + dt, shape: { type: 'star', r }, bg: C.gold }, lt, d));
    J.marker(g, { t: el('leap.hl'), x0: 240, x1: 860, y: 352, h: 70 }, lt);
  }
  function pageDragon(g, lt, d) {
    J.tab(g, 820, C.red, '05', d);
    J.polaroid(g, { id: 'dph', x: 545, y: 690, w: 740, h: 640, rot: -0.03, t: el('dragon.photo'), draw: photoDragon, caption: 'дракон' }, lt, d);
    J.tape(g, { id: 'dt1', a: [170, 300], b: [360, 250], color: C.yellow, t: el('dragon.tape1') }, lt, d);
    text(g, ['…и стал драконом!'], 1300, 100, lt, el('dragon.text'), 0.8, d, 'dtx');
    J.sticker(g, { id: 'dgl', x: 880, y: 330, rot: 0.12, t: el('dragon.glyph'), shape: { type: 'circle', r: 95 }, bg: C.red,
      draw: (b, w, h, dd) => { b.fillStyle = '#fff6e8'; b.font = '130px Glyph'; b.textAlign = 'center'; b.textBaseline = 'middle'; b.fillText('龙', w / 2, h / 2 + 6); } }, lt, d);
    const t0 = el('dragon.doodle');
    carp(g, 290, 1450, 0.42, 0, d, 'dmini', seg(lt, t0, t0 + 0.5));
    J.arrow(g, { id: 'dar', t: t0 + 0.4, pts: smooth([[400, 1450], [500, 1420], [600, 1450]], 8) }, lt, d);
    hand(g, 'дракон!', 760, 1470, { id: 'ddt', d, size: 70, color: C.red, p: seg(lt, t0 + 0.8, t0 + 1.2) });
  }
  function pageMoral(g, lt, d) {
    J.tab(g, 820, C.red, '06', d);
    ['鲤', '鱼', '跃', '龙', '门'].forEach((ch, i) => glyph(g, ch, 210 + i * 165, 290, { id: 'mg' + i, d, size: 150, fill: C.red, tone: pal.line, line: pal.line, p: seg(lt, el('moral.glyphs') + i * 0.18, el('moral.glyphs') + 0.4 + i * 0.18) }));
    text(g, ['«Карп прыгнул через', 'Врата Дракона»'], 480, 78, lt, el('moral.quote'), 0.5, d, 'mq', pal.soft);
    // карточка-вставка на скотче
    const tn = el('moral.note'), u = seg(lt, tn, tn + 0.22);
    if (u > 0) {
      const s = lerp(1.12, 1, easeOut(u));
      g.save(); g.translate(545, 930); g.rotate(-0.025); g.scale(s, s);
      g.fillStyle = 'rgba(40,28,18,0.25)'; g.fillRect(-390 + 8, -230 + 12, 780, 460);
      g.fillStyle = '#d8bf96'; g.fillRect(-390, -230, 780, 460);
      g.strokeStyle = 'rgba(90,60,30,0.35)'; g.setLineDash([10, 8]); g.lineWidth = 2; g.strokeRect(-370, -210, 740, 420); g.setLineDash([]);
      ['Так в Китае говорят о том,', 'кто добился успеха упорством:', 'например, сдал труднейший', 'императорский экзамен'].forEach((s2, i) =>
        hand(g, s2, 0, -120 + i * 82, { id: 'mn' + i, d, size: 64, color: C.ink, p: seg(lt, tn + 0.3 + i * 0.4, tn + 0.7 + i * 0.4) }));
      g.restore();
      J.tape(g, { id: 'mt1', a: [140, 720], b: [300, 690], color: C.coral, t: tn + 0.15 }, lt, d);
      J.tape(g, { id: 'mt2', a: [790, 690], b: [950, 725], color: C.mint, t: tn + 0.25 }, lt, d);
    }
    J.sticker(g, { id: 'mbadge', x: 690, y: 1330, rot: 0.08, t: el('moral.badge'), shape: { type: 'rrect', w: 470, h: 130, r: 40 }, bg: C.red,
      draw: (b, w, h, dd) => hand(b, 'Не сдавайся!', w / 2, h / 2 + 22, { id: 'mb', d: dd, size: 76, color: '#fff6e8' }) }, lt, d);
    J.stamp(g, { id: 'mst', x: 240, y: 1350, size: 86, rot: -0.1, t: el('moral.stamp'), chars: '龙门' }, lt, d);
    carp(g, 230, 1520, 0.32, -0.2, d, 'mmini', seg(lt, el('moral.stamp') + 0.2, el('moral.stamp') + 0.7));
  }
  const PAGES = [pageCover, pageRiver, pageFalls, pageLeap, pageDragon, pageMoral];

  function renderPage(i, lt, d) {
    const b = bufs[i], g = b.getContext('2d');
    g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1; g.clearRect(0, 0, W, H);
    g.drawImage(pagePaper, J.PX, J.PY);
    lg.setTransform(1, 0, 0, 1, 0, 0); lg.globalCompositeOperation = 'source-over'; lg.globalAlpha = 1; lg.clearRect(0, 0, W, H);
    CAM.reset();
    PAGES[i](lg, lt, d);
    g.drawImage(layer, 0, 0);
    J.rings(g, d);
    return b;
  }

  // ---------- листание: страница загибается с нижнего правого уголка ----------
  function curl(img, u) {
    const CX = J.PX, CY = J.PY - 50, CW = J.PW, CH = J.PH + 50; // захватываем и язычок закладки
    const k = easeIO(u), diag = Math.hypot(CW, CH), vx = -CW / diag, vy = -CH / diag;
    const Cn = [CX + CW, CY + CH], F = [Cn[0] + vx * diag * 1.08 * k, Cn[1] + vy * diag * 1.08 * k];
    const side = q => (q[0] - F[0]) * vx + (q[1] - F[1]) * vy;
    const rect = [[CX, CY], [CX + CW, CY], [CX + CW, CY + CH], [CX, CY + CH]];
    const clip = keep => { const out = []; for (let i = 0; i < 4; i++) { const a = rect[i], b = rect[(i + 1) % 4], sa = side(a) * keep, sb = side(b) * keep; if (sa >= 0) out.push(a); if (sa * sb < 0) { const t = sa / (sa - sb); out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]); } } return out; };
    const A = clip(1), Bf = clip(-1), refl = q => { const s2 = 2 * side(q); return [q[0] - s2 * vx, q[1] - s2 * vy]; };
    const path = (pts, dx = 0, dy = 0) => { og.beginPath(); pts.forEach((q, i) => (i ? og.lineTo(q[0] + dx, q[1] + dy) : og.moveTo(q[0] + dx, q[1] + dy))); og.closePath(); };
    if (A.length > 2) {
      og.save(); path(A); og.clip(); og.drawImage(img, 0, 0);
      const g2 = og.createLinearGradient(F[0], F[1], F[0] + vx * 90, F[1] + vy * 90);
      g2.addColorStop(0, 'rgba(26,18,11,0.35)'); g2.addColorStop(1, 'rgba(26,18,11,0)'); og.fillStyle = g2; og.fillRect(0, 0, W, H); og.restore();
    }
    if (Bf.length > 2) {
      const flap = Bf.map(refl);
      og.save(); og.globalAlpha = 0.22; og.fillStyle = '#1a120b'; path(flap, 10, 14); og.fill(); og.restore();
      og.save(); path(flap); og.clip(); og.drawImage(pagePaper, J.PX, J.PY); og.globalAlpha = 0.16; og.fillStyle = '#5a4630'; og.fillRect(0, 0, W, H); og.restore();
      og.save(); og.strokeStyle = 'rgba(90,70,50,0.6)'; og.lineWidth = 2; path(flap); og.stroke(); og.restore();
    }
  }

  function render(t) {
    const d = Math.floor(t * T.drawRate + 1e-6), tq = d / T.drawRate;
    og.setTransform(1, 0, 0, 1, 0, 0); og.globalCompositeOperation = 'source-over'; og.globalAlpha = 1;
    og.drawImage(desk, 0, 0);
    og.fillStyle = 'rgba(20,12,6,0.35)'; og.fillRect(J.PX + 14, J.PY + 20, J.PW, J.PH); // тень дневника
    const B = T.B, TR = T.trans;
    let cur = B.findIndex(b => tq < b); if (cur < 0) cur = B.length;
    const tr = cur - 1, inTrans = tr >= 0 && tq < B[tr] + TR, lt = i => tq - T.drawStart[i];
    if (inTrans) { og.drawImage(renderPage(cur, lt(cur), d), 0, 0); curl(renderPage(tr, lt(tr), d), seg(tq, B[tr], B[tr] + TR)); }
    else og.drawImage(renderPage(cur, lt(cur), d), 0, 0);
    const wa = 0.06 * ease(seg(tq, T.turn, T.turn + 0.4)); // после прыжка свет теплее
    if (wa > 0) { og.globalAlpha = wa; og.fillStyle = pal.wash; og.fillRect(0, 0, W, H); og.globalAlpha = 1; }
  }
  window.SCENES = { init, render };
})();
