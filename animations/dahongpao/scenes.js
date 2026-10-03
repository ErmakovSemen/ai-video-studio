// «Да Хун Пао» как книжка из карточек: статичные иллюстрации карандашом + бумажные переходы.
// Карточка рисуется в своих координатах (960×1480). Переходы: смять в комок и выбросить,
// перевернуть страницу, развернуть свиток. Минимум движения внутри кадра.
(function () {
  'use strict';
  const P = window.PENCIL, T = window.T;
  const { W, H, rng, seg, lerp, ease, easeIO, easeOut, smooth, ellipse, pod, CAM, pencil, hatch, hand, glyph } = P;
  const CW = 960, CH = 1480, CX = 60, CY = 120; // карточка на столе: низ 1600 < 1632 (зона интерфейса)

  let pal, desk, tooth, cardPaper, scrollPaper, ink, ig, og, bufs = [];
  function mk(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
  function init(theme, canvas) {
    pal = P.PALETTES[theme];
    const deskPal = Object.assign({}, pal, { name: pal.name + 'desk', paper: pal.paperDark, paperLight: pal.paper, grain: 16 });
    desk = P.makePaper(deskPal); tooth = P.makeTooth();
    const full = P.makePaper(Object.assign({}, pal, { paper: pal.paperLight, paperLight: '#fffaf0', grain: 12 }));
    cardPaper = mk(CW, CH); cardPaper.getContext('2d').drawImage(full, 0, 0, CW, CH, 0, 0, CW, CH);
    scrollPaper = mk(CW, CH); const sg = scrollPaper.getContext('2d'); sg.drawImage(full, 100, 200, CW, CH, 0, 0, CW, CH);
    sg.globalAlpha = 0.18; sg.fillStyle = pal.light; sg.fillRect(0, 0, CW, CH);
    ink = mk(CW, CH); ig = ink.getContext('2d');
    og = canvas.getContext('2d');
    bufs = [0, 1, 2, 3, 4, 5].map(() => mk(CW, CH));
  }

  // ---------- общие рисунки ----------
  function ridgePts(id, base, peaks, x0, x1, step = 8) {
    const R = rng(id, 'ridge'), pts = [];
    for (let x = x0; x <= x1; x += step) {
      let h = 0; for (const k of peaks) h = Math.max(h, k.h / (1 + Math.pow(Math.abs((x - k.x) / k.w), k.e || 8)));
      pts.push([x, base - h + (R() - 0.5) * 3]);
    }
    return pts;
  }
  function band(id, y0, y1, amp, x0 = -20, x1 = CW + 20) {
    const R = rng(id, 'band'), top = [], bot = [];
    for (let x = x0; x <= x1; x += 60) { top.push([x, y0 + (R() - 0.5) * amp]); bot.push([x, y1 + (R() - 0.5) * amp]); }
    return smooth(top, 4).concat(smooth(bot.reverse(), 4));
  }
  function caption(g, lines, lt, d, id, y0 = 1290, size = 78) {
    lines.forEach((s, i) => hand(g, s, CW / 2, y0 + i * size * 1.12, { id: id + i, d, size, color: pal.line, p: seg(lt, 1.0 + i * 0.6, 1.7 + i * 0.6) }));
  }
  function temple(g, x, y, s, lt, d, id) {
    const roof = smooth([[x - 62 * s, y], [x - 40 * s, y - 18 * s], [x, y - 30 * s], [x + 40 * s, y - 18 * s], [x + 62 * s, y]], 4).concat([[x + 40 * s, y - 6 * s], [x - 40 * s, y - 6 * s]]);
    hatch(g, roof, { id: id + 'r', d, color: pal.line, angle: 15, spacing: 4.5, w: 1.5, alpha: 0.6, maxLen: 30, p: seg(lt, 0.6, 1.0) });
    pencil(g, roof, { id: id + 'ro', d, color: pal.line, w: 2.6, closed: true, p: seg(lt, 0.3, 0.8) });
    pencil(g, [[x - 34 * s, y - 6 * s], [x - 34 * s, y + 34 * s], [x + 34 * s, y + 34 * s], [x + 34 * s, y - 6 * s]], { id: id + 'w', d, color: pal.soft, w: 2.2, p: seg(lt, 0.5, 1.0) });
  }
  function bush(g, x, y, r, lt, d, id, t0 = 0.6) {
    const pts = [];
    for (let k = 0; k <= 40; k++) { const a = Math.PI + k / 40 * Math.PI, rr = r * (1 + 0.1 * Math.sin(a * 9 + x)); pts.push([x + Math.cos(a) * rr * 1.2, y + Math.sin(a) * rr]); }
    const poly = pts.concat([[x + r * 1.2, y + 6], [x - r * 1.2, y + 6]]);
    hatch(g, poly, { id: id + 'h', d, color: pal.line, angle: 48, spacing: 6, w: 1.7, alpha: 0.5, maxLen: 24, p: seg(lt, t0 + 0.3, t0 + 0.9) });
    pencil(g, pts, { id: id, d, color: pal.line, w: 3, p: seg(lt, t0, t0 + 0.6) });
    return pts;
  }
  function robeOver(g, bushes, lt, d, id, t0) { // красная мантия, наброшенная на кусты
    const x0 = bushes[0].x - bushes[0].r * 1.3, x1 = bushes[2].x + bushes[2].r * 1.3, top = [];
    for (let x = x0; x <= x1; x += 8) {
      let y = bushes[2].y + 10;
      for (const b of bushes) { const dx = (x - b.x) / (b.r * 1.25); if (Math.abs(dx) < 1) y = Math.min(y, b.y - b.r * Math.sqrt(1 - dx * dx) - 4); }
      top.push([x, y]);
    }
    const yb = bushes[0].y + 14, hem = [];
    for (let x = x1 + 30; x >= x0 - 30; x -= 12) hem.push([x, yb + 8 * Math.sin(x * 0.08)]);
    const poly = top.concat(hem);
    const sleeveL = [[x0 + 10, top[0][1] + 10], [x0 - 60, yb - 20], [x0 - 40, yb + 10], [x0 + 30, yb]];
    const sleeveR = [[x1 - 10, top[top.length - 1][1] + 10], [x1 + 60, yb - 24], [x1 + 44, yb + 10], [x1 - 30, yb]];
    [poly, sleeveL, sleeveR].forEach((q, i) => {
      hatch(g, q, { id: id + 'h' + i, d, color: pal.seal, angle: 62, spacing: 4.5, w: 2.2, alpha: 0.9, p: seg(lt, t0 + 0.3, t0 + 1.0) });
      hatch(g, q, { id: id + 'k' + i, d, color: pal.seal, angle: -25, spacing: 10, w: 1.6, alpha: 0.6, p: seg(lt, t0 + 0.6, t0 + 1.2) });
      pencil(g, q, { id: id + 'o' + i, d, color: pal.line, w: 3, closed: true, p: seg(lt, t0, t0 + 0.7) });
    });
    for (let k = 0; k < 6; k++) { const x = lerp(x0 + 40, x1 - 40, k / 5); pencil(g, [[x, yb - 8], [x + 8, yb - 70 - 20 * (k % 2)]], { id: id + 'f' + k, d, color: pal.line, w: 1.8, alpha: 0.5, p: seg(lt, t0 + 0.8, t0 + 1.2) }); }
  }
  function seal(g, cx, cy, S, lt, d, id, at) {
    if (lt < at) return;
    const k = lerp(1.3, 1, seg(lt, at, at + 0.1)), s = S * k, sq = [[cx - s, cy - s], [cx + s, cy - s], [cx + s, cy + s], [cx - s, cy + s]];
    hatch(g, sq, { id: id + 'h', d, color: pal.seal, angle: 45, spacing: 3.5, w: 2.4, alpha: 0.9, maxLen: 40, ends: 2 });
    pencil(g, sq, { id: id + 'o', d, color: pal.seal, w: 3, closed: true });
    glyph(g, '茶', cx, cy + 3, { id: id + 'g', d, size: 1.5 * s, fill: pal.paperLight, tone: pal.paperLight, line: pal.paperLight, base: 1, lineW: 2 });
  }

  // ---------- карточки ----------
  const PEAKS1 = ridgePts('c1', 640, [{ x: 110, h: 230, w: 55 }, { x: 290, h: 320, w: 50 }, { x: 460, h: 210, w: 62 }, { x: 650, h: 340, w: 50 }, { x: 830, h: 250, w: 58 }], -20, CW + 20);
  function card1(g, lt, d) { // горы, тропа, крошечный силуэт студента со спины
    hand(g, 'Легенда о Да Хун Пао', CW / 2, 130, { id: 'hdr', d, size: 64, color: pal.soft, p: seg(lt, 0.2, 1.0) });
    hatch(g, PEAKS1.concat([[CW + 20, 700], [-20, 700]]), { id: 'p1h', d, color: pal.cold, angle: 78, spacing: 10, w: 1.8, alpha: 0.45, p: seg(lt, 0.6, 1.6) });
    pencil(g, PEAKS1, { id: 'p1', d, color: pal.line, w: 3.2, p: seg(lt, 0, 1.0) });
    temple(g, 650, 296, 0.8, lt, d, 't1');
    hatch(g, band('m1', 620, 700, 30), { id: 'm1', d, color: pal.light, angle: 2, spacing: 7, w: 2.4, alpha: 0.7, maxLen: 120, p: seg(lt, 1.0, 1.7) });
    const L = smooth([[230, 1180], [370, 1010], [320, 870], [462, 720]], 8), Rr = smooth([[730, 1180], [610, 1010], [570, 870], [510, 720]], 8);
    hatch(g, [[-20, 720], [CW + 20, 720], [CW + 20, 1180], [-20, 1180]], { id: 'gr', d, color: pal.soft, angle: 8, spacing: 12, w: 1.6, alpha: 0.3, maxLen: 70, p: seg(lt, 0.8, 1.6) });
    P.erasePolyLocal(g, L.concat(Rr.slice().reverse()));
    pencil(g, L, { id: 'pl', d, color: pal.line, w: 3, p: seg(lt, 0.4, 1.1) });
    pencil(g, Rr, { id: 'pr', d, color: pal.line, w: 3, p: seg(lt, 0.4, 1.1) });
    // студент со спины: шапка, халат, узелок
    const sx = 468, sy = 905, f = { d };
    if (lt > 0.9) {
      const robe = [[sx - 26, 812], [sx + 26, 812], [sx + 38, sy], [sx - 38, sy]];
      P.erasePolyLocal(g, robe);
      hatch(g, robe, { id: 'sr', d, color: pal.cold, angle: 75, spacing: 4, w: 1.8, alpha: 0.9, p: seg(lt, 1.0, 1.4) });
      pencil(g, robe, { id: 'sro', d, color: pal.line, w: 2.4, closed: true, p: seg(lt, 0.9, 1.2) });
      const bundle = [[sx - 18, 818], [sx + 20, 818], [sx + 22, 858], [sx - 20, 858]];
      P.erasePolyLocal(g, bundle); hatch(g, bundle, { id: 'sb', d, color: pal.soft, angle: 20, spacing: 4, w: 1.6, alpha: 0.7, p: seg(lt, 1.1, 1.4) });
      pencil(g, bundle, { id: 'sbo', d, color: pal.line, w: 2, closed: true, p: seg(lt, 1.0, 1.3) });
      const head = ellipse(sx, 798, 13, 14, 0, 18); P.erasePolyLocal(g, head); pencil(g, head, { id: 'sh', d, color: pal.line, w: 2.2, closed: true, p: seg(lt, 0.9, 1.1) });
      const cap = [[sx - 15, 790], [sx + 15, 790], [sx + 13, 772], [sx - 13, 772]];
      hatch(g, cap, { id: 'sc', d, color: pal.line, angle: 30, spacing: 3, w: 1.6, alpha: 0.95, p: seg(lt, 1.1, 1.3) });
      pencil(g, [[sx - 14, 782], [sx - 30, 796]], { id: 'sr1', d, color: pal.line, w: 1.8, p: seg(lt, 1.2, 1.4) });
      pencil(g, [[sx + 14, 782], [sx + 30, 796]], { id: 'sr2', d, color: pal.line, w: 1.8, p: seg(lt, 1.2, 1.4) });
    }
    caption(g, ['Эпоха Мин. Бедный студент', 'шёл в столицу на экзамен'], lt, d, 'c1');
  }

  const CLIFF2 = smooth([[700, 1180], [690, 980], [722, 760], [700, 560], [742, 380], [820, 300], [CW + 20, 280]], 6).concat([[CW + 20, 1180]]);
  function card2(g, lt, d) { // у скалы: на тропе шапка и рассыпанные книги
    hatch(g, CLIFF2, { id: 'c2h', d, color: pal.soft, angle: 87, spacing: 8, w: 2, alpha: 0.5, p: seg(lt, 0.3, 1.2) });
    pencil(g, CLIFF2.slice(0, -2), { id: 'c2', d, color: pal.line, w: 4, p: seg(lt, 0, 0.8) });
    [520, 700, 900].forEach((y, i) => pencil(g, [[716, y], [820, y + 8], [CW + 10, y - 6]], { id: 'st' + i, d, color: pal.soft, w: 2, p: seg(lt, 0.5, 1.0) }));
    const ground = smooth([[-20, 860], [200, 846], [420, 870], [700, 856]], 6);
    hatch(g, ground.concat([[700, 1180], [-20, 1180]]), { id: 'g2', d, color: pal.soft, angle: 6, spacing: 13, w: 1.6, alpha: 0.3, maxLen: 70, p: seg(lt, 0.4, 1.2) });
    pencil(g, ground, { id: 'g2l', d, color: pal.line, w: 3, p: seg(lt, 0, 0.7) });
    // книги
    [[300, 1000, -0.25], [420, 1050, 0.15], [250, 1090, 0.05]].forEach(([x, y, a], i) => {
      const c = Math.cos(a), s = Math.sin(a), m = q => [x + q[0] * c - q[1] * s, y + q[0] * s + q[1] * c];
      const bk = [[-90, -24], [90, -24], [90, 24], [-90, 24]].map(m);
      P.erasePolyLocal(g, bk);
      hatch(g, bk, { id: 'bk' + i, d, color: i === 1 ? pal.cold : pal.soft, angle: a * 57 + 80, spacing: 5, w: 1.7, alpha: 0.7, p: seg(lt, 0.8 + i * 0.1, 1.2 + i * 0.1) });
      pencil(g, bk, { id: 'bko' + i, d, color: pal.line, w: 2.6, closed: true, p: seg(lt, 0.5 + i * 0.1, 0.9 + i * 0.1) });
      pencil(g, [[-90, -12], [90, -12]].map(m), { id: 'bks' + i, d, color: pal.line, w: 1.6, alpha: 0.6, p: seg(lt, 0.9, 1.2) });
    });
    pencil(g, [[480, 980], [600, 940]], { id: 'brush', d, color: pal.line, w: 4, p: seg(lt, 1.0, 1.2) });
    pencil(g, [[600, 940], [625, 931]], { id: 'brt', d, color: pal.line, w: 7, p: seg(lt, 1.1, 1.3), sketch: false });
    // шапка учёного
    const cap = [[470, 905], [600, 890], [610, 950], [470, 962]];
    P.erasePolyLocal(g, cap);
    hatch(g, cap, { id: 'cap', d, color: pal.line, angle: 30, spacing: 3.5, w: 2, alpha: 0.9, p: seg(lt, 0.9, 1.3) });
    pencil(g, cap, { id: 'capo', d, color: pal.line, w: 3, closed: true, p: seg(lt, 0.7, 1.1) });
    pencil(g, smooth([[475, 930], [420, 960], [380, 945]], 6), { id: 'rib1', d, color: pal.line, w: 2.4, p: seg(lt, 1.1, 1.4) });
    pencil(g, smooth([[606, 925], [660, 965], [700, 950]], 6), { id: 'rib2', d, color: pal.line, w: 2.4, p: seg(lt, 1.1, 1.4) });
    [[150, 930, 0.3], [640, 1080, -0.6], [560, 1120, 0.9]].forEach(([x, y, a], i) => {
      const lf = pod([x, y], [x + Math.cos(a) * 60, y + Math.sin(a) * 60], 14, 0.9, 14);
      hatch(g, lf, { id: 'lh' + i, d, color: pal.soft, angle: a * 57 + 50, spacing: 5, w: 1.4, alpha: 0.5, p: seg(lt, 1.2, 1.5) });
      pencil(g, lf, { id: 'lf' + i, d, color: pal.line, w: 2, closed: true, p: seg(lt, 1.0, 1.4) });
    });
    caption(g, ['У скал Уишаня он выбился', 'из сил и упал без чувств'], lt, d, 'c2');
  }

  function teapot(g, at, tilt, lt, d) {
    const c = Math.cos(tilt), s = Math.sin(tilt), m = q => [at[0] + q[0] * c - q[1] * s, at[1] + q[0] * s + q[1] * c];
    const body = ellipse(0, 40, 92, 68, 0, 30).map(m);
    P.erasePolyLocal(g, body);
    hatch(g, body, { id: 'tph', d, color: pal.soft, angle: 30, spacing: 6, w: 1.8, alpha: 0.6, p: seg(lt, 0.4, 0.9) });
    pencil(g, body, { id: 'tp', d, color: pal.line, w: 3.2, closed: true, p: seg(lt, 0.1, 0.6) });
    pencil(g, [[-80, 30], [-140, -14], [-162, -26]].map(m), { id: 'tps', d, color: pal.line, w: 4, p: seg(lt, 0.4, 0.7) });
    pencil(g, [[-30, -26], [30, -26]].map(m), { id: 'tpl', d, color: pal.line, w: 5, p: seg(lt, 0.4, 0.6), sketch: false });
    pencil(g, ellipse(0, -34, 10, 7, 0, 10).map(m), { id: 'tpk', d, color: pal.line, w: 2.4, closed: true, p: seg(lt, 0.5, 0.7) });
    return { spout: m([-162, -26]), handle: m([88, 10]), m };
  }
  function card3(g, lt, d) { // рукав монаха, чайник, чашка на камне, ветка чая
    const ang = 0.35, br = smooth([[-20, 420], [140, 360], [260, 270], [330, 210]], 8);
    pencil(g, br, { id: 'br', d, color: pal.line, w: 4, p: seg(lt, 0, 0.6) });
    [[0.3, 1], [0.55, -1], [0.8, 1]].forEach(([u, sd], i) => {
      const a = P.along(br, u), rot = sd * 55 * Math.PI / 180;
      const dx = a.dir[0] * Math.cos(rot) - a.dir[1] * Math.sin(rot), dy = a.dir[0] * Math.sin(rot) + a.dir[1] * Math.cos(rot);
      const lf = pod(a.p, [a.p[0] + dx * 130, a.p[1] + dy * 130], 34, 0.9, 20);
      hatch(g, lf, { id: 'l3h' + i, d, color: pal.soft, angle: 40, spacing: 7, w: 1.5, alpha: 0.45, p: seg(lt, 0.6, 1.0) });
      pencil(g, lf, { id: 'l3' + i, d, color: pal.line, w: 2.6, closed: true, p: seg(lt, 0.3 + i * 0.1, 0.7 + i * 0.1) });
    });
    const bud = pod([330, 210], [358, 140], 14, 0.6, 16);
    pencil(g, bud, { id: 'bud3', d, color: pal.line, w: 2.6, closed: true, p: seg(lt, 0.6, 0.9) });
    // камень и чашка
    const stone = smooth([[220, 990], [300, 930], [520, 915], [690, 940], [740, 1000], [220, 1000]], 6);
    hatch(g, stone, { id: 'sth', d, color: pal.soft, angle: 12, spacing: 7, w: 1.7, alpha: 0.5, p: seg(lt, 0.5, 1.1) });
    pencil(g, stone, { id: 'sto', d, color: pal.line, w: 3.2, closed: true, p: seg(lt, 0.2, 0.8) });
    const cup = [[400, 840], [500, 840], [482, 924], [418, 924]];
    P.erasePolyLocal(g, cup);
    hatch(g, cup, { id: 'cuph', d, color: pal.cold, angle: 20, spacing: 5, w: 1.6, alpha: 0.6, p: seg(lt, 0.6, 1.0) });
    pencil(g, cup, { id: 'cup', d, color: pal.line, w: 3, closed: true, p: seg(lt, 0.4, 0.8) });
    // чайник в руке монаха: наливает (единственное движение карточки)
    const tilt = -0.55 * easeIO(seg(lt, 1.8, 2.1)) * (1 - easeIO(seg(lt, 3.3, 3.6)));
    const tp = teapot(g, [700, 620], tilt, lt, d);
    if (lt > 2.05 && lt < 3.45) pencil(g, smooth([tp.spout, [tp.spout[0] - 30, tp.spout[1] + 60], [450, 845]], 6), { id: 'stream', d, color: pal.cold, w: 4, alpha: 0.9, gaps: false });
    const h = tp.handle, sleeve = [[h[0] - 6, h[1] - 50], [CW + 20, h[1] - 170], [CW + 20, h[1] + 150], [h[0] + 10, h[1] + 56]];
    P.erasePolyLocal(g, sleeve);
    hatch(g, sleeve, { id: 'slh', d, color: pal.soft, angle: 70, spacing: 5, w: 2, alpha: 0.8, p: seg(lt, 0.5, 1.1) });
    pencil(g, sleeve, { id: 'sl', d, color: pal.line, w: 3.2, closed: true, p: seg(lt, 0.2, 0.8) });
    [0.3, 0.55, 0.8].forEach((u, i) => pencil(g, [[lerp(h[0], CW, u), lerp(h[1] - 50, h[1] - 170, u)], [lerp(h[0], CW, u) + 10, lerp(h[1] + 56, h[1] + 150, u)]], { id: 'slf' + i, d, color: pal.line, w: 1.6, alpha: 0.5, p: seg(lt, 0.8, 1.1) }));
    if (lt > 3.4) for (let k = -1; k <= 1; k++) { // пар над чашкой
      const pts = [], ph = lt * 2.4 + k * 2;
      for (let s = 0; s <= 110 * Math.min(1, (lt - 3.4) * 1.5); s += 6) pts.push([450 + k * 18 + 9 * Math.sin(s * 0.06 - ph), 830 - s]);
      if (pts.length > 2) pencil(g, pts, { id: 'stm' + k, d, color: pal.soft, w: 2.2, alpha: 0.7 });
    }
    caption(g, ['Монах из храма напоил его', 'чаем с кустов у скалы'], lt, d, 'c3');
  }

  function card4(g, lt, d) { // свиток 状元
    hand(g, 'Император объявил:', CW / 2, 150, { id: 'emp', d, size: 66, color: pal.soft, p: seg(lt, 0.0, 0.6) });
    glyph(g, '状', CW / 2, 430, { id: 'zh', d, size: 300, fill: pal.warm, tone: pal.line, line: pal.line, p: seg(lt, 0.1, 0.6) });
    glyph(g, '元', CW / 2, 770, { id: 'yu', d, size: 300, fill: pal.warm, tone: pal.line, line: pal.line, p: seg(lt, 0.4, 0.9) });
    seal(g, 740, 1000, 48, lt, d, 'seal4', T.stamp - T.drawStart[3]);
    caption(g, ['Студент стал первым', 'на императорском экзамене'], lt, d, 'c4', 1250, 74);
  }

  const BUSH5 = [[250, 1000, 100], [480, 975, 122], [710, 1000, 98]].map(([x, y, r]) => ({ x, y, r }));
  const CLIFF5 = smooth([[-20, 1060], [40, 900], [20, 700], [70, 500], [60, 330], [160, 250], [330, 230], [520, 260], [700, 240], [860, 300], [CW + 20, 360]], 6).concat([[CW + 20, 1060]]);
  function card5(g, lt, d, t0 = 0) { // кусты под красной мантией у скалы
    hatch(g, CLIFF5, { id: 'c5h', d, color: pal.soft, angle: 86, spacing: 9, w: 2, alpha: 0.45, p: seg(lt, t0 + 0.3, t0 + 1.2) });
    pencil(g, CLIFF5.slice(0, -2), { id: 'c5', d, color: pal.line, w: 4, p: seg(lt, t0, t0 + 0.8) });
    [420, 600, 780].forEach((y, i) => pencil(g, [[60, y], [400, y + 10], [CW, y - 8]], { id: 'c5s' + i, d, color: pal.soft, w: 2, alpha: 0.7, p: seg(lt, t0 + 0.4, t0 + 0.9) }));
    temple(g, 520, 236, 0.9, lt - t0, d, 't5');
    P.erasePolyLocal(g, [[-20, 1040], [CW + 20, 1040], [CW + 20, 1180], [-20, 1180]]);
    pencil(g, [[-20, 1040], [CW + 20, 1036]], { id: 'g5', d, color: pal.line, w: 3, p: seg(lt, t0 + 0.2, t0 + 0.7) });
    const bs = BUSH5.map((b, i) => (bush(g, b.x, b.y + 28, b.r, lt, d, 'b5' + i, t0 + 0.5), b));
    robeOver(g, bs.map(b => ({ x: b.x, y: b.y + 28, r: b.r })), lt, d, 'rb5', t0 + 0.9);
  }
  function card5full(g, lt, d) { card5(g, lt, d); caption(g, ['В благодарность он укрыл', 'кусты своей красной мантией'], lt, d, 'c5'); }

  function card6(g, lt, d) { // постер
    ['大', '红', '袍'].forEach((ch, i) => glyph(g, ch, 210 + 270 * i, 210, { id: 'pg' + i, d, size: 210, fill: pal.seal, tone: pal.line, line: pal.line, p: seg(lt, 0.1 + i * 0.25, 0.6 + i * 0.25) }));
    CAM.set(0.62, CW / 2, 760, CW / 2, 690);
    card5(g, lt, d, 0.4);
    CAM.reset();
    hand(g, 'Да Хун Пао', CW / 2, 1200, { id: 'pt1', d, size: 120, color: pal.line, p: seg(lt, 1.1, 1.7) });
    hand(g, 'Большой красный халат', CW / 2, 1300, { id: 'pt2', d, size: 76, color: pal.soft, p: seg(lt, 1.4, 1.9) });
    seal(g, CW / 2, 1400, 40, lt, d, 'seal6', 2.0);
  }
  const CARDS = [card1, card2, card3, card4, card5full, card6];

  // ---------- карточка -> изображение ----------
  function renderCard(i, lt, d) {
    ig.setTransform(1, 0, 0, 1, 0, 0); ig.globalCompositeOperation = 'source-over'; ig.globalAlpha = 1; ig.clearRect(0, 0, CW, CH);
    CAM.reset();
    CARDS[i](ig, lt, d);
    ig.globalCompositeOperation = 'destination-out'; ig.globalAlpha = 0.5; ig.drawImage(tooth, 0, 0, CW, CH, 0, 0, CW, CH);
    ig.globalCompositeOperation = 'source-over'; ig.globalAlpha = 1;
    const b = bufs[i], g = b.getContext('2d');
    g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1;
    g.drawImage(i === 3 ? scrollPaper : cardPaper, 0, 0);
    g.drawImage(ink, 0, 0);
    return b;
  }

  // ---------- переходы ----------
  function shadow(x, y, w, h, a = 0.28) { og.globalAlpha = a; og.fillStyle = '#1a120b'; og.fillRect(x + 14, y + 20, w, h); og.globalAlpha = 1; }
  function plain(img) { shadow(CX, CY, CW, CH); og.drawImage(img, CX, CY); }

  function crumple(img, u, d, id) {
    const R = rng(id, 'crumple');
    const per = []; // точки контура карточки с «вмятинами»
    const N = 36; for (let k = 0; k < N; k++) { const s = k / N * 4, side = Math.floor(s), f = s - side; per.push([[f, 0], [1, f], [1 - f, 1], [0, 1 - f]][side]); }
    const jit = per.map(() => R() * 2 - 1), creases = []; for (let k = 0; k < 16; k++) creases.push([R(), R(), R(), R(), R()]);
    const cx0 = CX + CW / 2, cy0 = CY + CH / 2;
    if (u < 0.55) {
      const k = easeIO(u / 0.55), s = 1 - 0.8 * k, rot = 0.6 * k;
      og.save(); og.translate(cx0, cy0); og.rotate(rot); og.scale(s, s);
      og.beginPath();
      per.forEach((q, i) => { const x = (q[0] - 0.5) * CW, y = (q[1] - 0.5) * CH, pull = 1 - 0.22 * k * (0.5 + 0.5 * jit[i]); i ? og.lineTo(x * pull, y * pull) : og.moveTo(x * pull, y * pull); });
      og.closePath(); og.save(); og.globalAlpha = 0.28; og.fillStyle = '#1a120b'; og.translate(14 / s, 20 / s); og.fill(); og.restore();
      og.clip(); og.drawImage(img, -CW / 2, -CH / 2);
      og.lineCap = 'round';
      creases.slice(0, Math.round(16 * k)).forEach((c, i) => { // складки
        og.strokeStyle = i % 2 ? pal.soft : pal.paperLight; og.globalAlpha = 0.6; og.lineWidth = 3 / s;
        og.beginPath(); og.moveTo((c[0] - 0.5) * CW, (c[1] - 0.5) * CH); og.lineTo((c[2] - 0.5) * CW, (c[3] - 0.5) * CH); og.stroke();
      });
      og.globalAlpha = k * 0.25; og.fillStyle = pal.paperDark; og.fillRect(-CW / 2, -CH / 2, CW, CH);
      og.restore(); og.globalAlpha = 1;
    } else { // комок летит прочь
      const v = (u - 0.55) / 0.45, x = lerp(cx0, 1280, easeIO(v)), y = lerp(cy0, -260, v) - 320 * Math.sin(Math.PI * v), rr = 135, rot = 0.6 + 7 * v;
      const ball = []; for (let k = 0; k < 22; k++) { const a = k / 22 * 2 * Math.PI + rot, r = rr * (0.78 + 0.32 * Math.abs(jit[k])); ball.push([x + Math.cos(a) * r, y + Math.sin(a) * r]); }
      og.globalAlpha = 0.25; og.fillStyle = '#1a120b'; og.beginPath(); ball.forEach((q, i) => (i ? og.lineTo(q[0] + 10, q[1] + 16) : og.moveTo(q[0] + 10, q[1] + 16))); og.fill(); og.globalAlpha = 1;
      og.fillStyle = pal.paperLight; og.beginPath(); ball.forEach((q, i) => (i ? og.lineTo(q[0], q[1]) : og.moveTo(q[0], q[1]))); og.closePath(); og.fill();
      hatch(og, ball, { id: id + 'bh', d, color: pal.soft, angle: 40, spacing: 9, w: 1.6, alpha: 0.5, screen: true });
      creases.forEach((c, i) => { if (i < 9) pencil(og, [[x + (c[0] - 0.5) * rr * 1.4, y + (c[1] - 0.5) * rr * 1.4], [x + (c[2] - 0.5) * rr * 1.2, y + (c[3] - 0.5) * rr * 1.2]], { id: id + 'cr' + i, d, color: pal.soft, w: 2, alpha: 0.7, screen: true, sketch: false }); });
      pencil(og, ball, { id: id + 'bo', d, color: pal.line, w: 3, closed: true, screen: true });
    }
  }
  function fold(img, u) { // страница поднимается и переворачивается через верхний край
    const a = Math.PI * easeIO(u), sy = Math.cos(a);
    if (sy > 0) {
      shadow(CX, CY, CW, CH * sy, 0.28 * sy);
      og.drawImage(img, CX, CY, CW, CH * sy);
      og.globalAlpha = (1 - sy) * 0.35; og.fillStyle = '#1a120b'; og.fillRect(CX, CY, CW, CH * sy); og.globalAlpha = 1;
    } else {
      const h = -sy * CH;
      og.drawImage(cardPaper, CX, CY - h, CW, h);
      og.globalAlpha = 0.15 + 0.2 * (1 + sy); og.fillStyle = pal.paperDark; og.fillRect(CX, CY - h, CW, h); og.globalAlpha = 1;
    }
  }
  function unroll(img, u, d) { // свиток раскрывается сверху вниз
    const h = Math.max(6, CH * easeOut(u));
    shadow(CX, CY, CW, h);
    og.drawImage(img, 0, 0, CW, h, CX, CY, CW, h);
    pencil(og, [[CX - 40, CY - 8], [CX + CW + 40, CY - 8]], { id: 'rodT', d, color: pal.line, w: 16, screen: true, sketch: false, gaps: false });
    pencil(og, [[CX - 40, CY + h + 8], [CX + CW + 40, CY + h + 8]], { id: 'rodB', d, color: pal.line, w: 16, screen: true, sketch: false, gaps: false });
  }

  // ---------- кадр ----------
  function render(t) {
    const d = Math.floor(t * T.drawRate + 1e-6), tq = d / T.drawRate;
    og.globalCompositeOperation = 'source-over'; og.globalAlpha = 1;
    og.drawImage(desk, 0, 0);
    const B = T.B, TR = T.trans;
    let cur = B.findIndex(b => tq < b); if (cur < 0) cur = B.length;
    // карточка-«подложка» во время перехода: следующая уже лежит на столе
    const tr = cur > 0 ? cur - 1 : -1, inTrans = tr >= 0 && tq < B[tr] + TR;
    const lt = i => tq - T.drawStart[i];
    if (inTrans) {
      const nxt = tr + 1, u = seg(tq, B[tr], B[tr] + TR), kind = T.kind[tr];
      if (nxt !== 3) plain(renderCard(nxt, lt(nxt), d));
      else if (tq >= T.unroll[0]) unroll(renderCard(3, lt(3), d), seg(tq, T.unroll[0], T.unroll[1]), d);
      const img = renderCard(tr, lt(tr), d);
      if (kind === 'crumple') crumple(img, u, d, 'cr' + tr); else fold(img, u);
    } else if (cur === 3) {
      // свиток: после того как карточка 3 перевернулась
      if (tq >= T.unroll[0]) unroll(renderCard(3, lt(3), d), seg(tq, T.unroll[0], T.unroll[1]), d);
    } else plain(renderCard(cur, lt(cur), d));
    if (cur === 3 && tq >= T.unroll[1] - 0.6 && tq < 16.4) { // вспышка вокруг свитка
      const Rr = rng('rays'), grow = easeOut(seg(tq, T.unroll[1] - 0.3, T.unroll[1] + 0.1)), rf = 1 - seg(tq, 15.6, 16.4);
      for (let i = 0; i < 26; i++) {
        const a = i / 26 * Math.PI * 2 + (Rr() - 0.5) * 0.12, r0 = 560, r1 = r0 + (90 + Rr() * 160) * grow;
        pencil(og, [[540 + Math.cos(a) * r0 * 0.95, 860 + Math.sin(a) * r0 * 1.45], [540 + Math.cos(a) * r1 * 0.95, 860 + Math.sin(a) * r1 * 1.45]], { id: 'ray' + i, d, color: pal.warm, w: 7, alpha: 1, screen: true, fade: rf, gaps: false });
      }
    }
    const wa = 0.08 * ease(seg(tq, T.turn, T.turn + 0.4));
    if (wa > 0) { og.globalAlpha = wa; og.fillStyle = pal.wash; og.fillRect(0, 0, W, H); og.globalAlpha = 1; }
  }

  window.SCENES = { init, render };
})();
