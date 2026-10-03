// Сцены «Да Хун Пао — легенда о красной мантии». Всё от времени сюжета t, рисунок на двойках (12/с).
(function () {
  'use strict';
  const P = window.PENCIL, F = window.FIGURE, T = window.T;
  const { W, H, rng, seg, lerp, ease, easeIO, easeOut, smooth, ellipse, resample, CAM, pencil, hatch, hand, glyph } = P;
  const GY = 1380; // линия земли

  let pal, paper, tooth, ink, ig, og;
  function init(theme, canvas) {
    pal = P.PALETTES[theme];
    paper = P.makePaper(pal); tooth = P.makeTooth();
    ink = document.createElement('canvas'); ink.width = W; ink.height = H; ig = ink.getContext('2d');
    og = canvas.getContext('2d');
  }

  // ---------- мир: скалы Уишаня, храм, чайные кусты ----------
  function ridgePts(id, base, peaks, x0, x1, step = 10) {
    const R = rng(id, 'ridge'), pts = [];
    for (let x = x0; x <= x1; x += step) {
      let h = 0; for (const k of peaks) h = Math.max(h, k.h / (1 + Math.pow(Math.abs((x - k.x) / k.w), k.e || 7)));
      pts.push([x, base - h + (R() - 0.5) * 4]);
    }
    return pts;
  }
  const FAR = ridgePts('far', 1010, [{ x: 60, h: 190, w: 60 }, { x: 210, h: 260, w: 55 }, { x: 380, h: 170, w: 70 }, { x: 540, h: 240, w: 58 }, { x: 680, h: 200, w: 60 }], -40, 760);
  const FAR_POLY = FAR.concat([[760, 1060], [-40, 1060]]);
  const CLIFF = smooth([[700, 1380], [688, 1210], [712, 1010], [702, 830], [730, 650], [772, 566], [850, 534], [960, 522], [1060, 540], [1120, 556]], 6);
  const CLIFF_POLY = CLIFF.concat([[1120, 1380]]);
  const STRATA = [700, 880, 1060, 1230].map((y, i) => [[720 + i * 6, y], [860, y + 8], [980, y - 4], [1120, y + 6]]);
  const TEMPLE = { x: 380, y: 846 };
  const BUSHES = [[772, 1320, 56], [862, 1304, 66], [952, 1322, 54]].map(([x, y, r], i) => {
    const pts = [];
    for (let k = 0; k <= 40; k++) { const a = Math.PI + k / 40 * Math.PI; const rr = r * (1 + 0.09 * Math.sin(a * 9 + i)); pts.push([x + Math.cos(a) * rr * 1.15, Math.min(GY - 4, y + Math.sin(a) * rr)]); }
    pts.push([x + r * 1.15, GY - 4], [x - r * 1.15, GY - 4]);
    return { i, x, y, r, pts };
  });
  const GROUND = (() => { const R = rng('ground'), o = []; for (let x = -40; x <= 1120; x += 20) o.push([x, GY + (R() - 0.5) * 3]); return o; })();
  const MIST = (() => { const R = rng('mist'), top = [], bot = []; for (let x = -40; x <= 760; x += 60) { top.push([x, 990 + (R() - 0.5) * 30]); bot.push([x, 1070 + (R() - 0.5) * 30]); } return smooth(top, 4).concat(smooth(bot.reverse(), 4)); })();

  function erasePoly(g, polyW) { F.erase(g, polyW); }
  function eraseRect(g, x, y, w, h) { // подложка под подпись: стираем фон
    g.save(); g.globalCompositeOperation = 'destination-out'; g.globalAlpha = 0.92; g.fillRect(x, y, w, h); g.restore();
  }

  // lp — «часы рисования»: штрихи появляются по ним (для повторной прорисовки сцены)
  function drawLand(g, lp, d, fade) {
    if (fade <= 0) return;
    pencil(g, GROUND, { id: 'ground', d, color: pal.line, w: 3.6, p: seg(lp, 0, 0.8), fade });
    hatch(g, [[-40, GY + 4], [1120, GY + 4], [1120, GY + 60], [-40, GY + 52]], { id: 'gh', d, color: pal.soft, angle: 4, spacing: 9, w: 1.6, alpha: 0.35, maxLen: 90, p: seg(lp, 0.5, 1.3), fade });
    hatch(g, FAR_POLY, { id: 'farh', d, color: pal.cold, angle: 76, spacing: 11, w: 1.8, alpha: 0.4, p: seg(lp, 1.0, 2.2), fade });
    pencil(g, FAR, { id: 'far', d, color: pal.soft, w: 2.8, p: seg(lp, 0, 1.2), fade });
    // храм Тяньсинь на хребте
    const tx = TEMPLE.x, ty = TEMPLE.y;
    const roof = smooth([[tx - 62, ty - 4], [tx - 40, ty - 22], [tx, ty - 34], [tx + 40, ty - 22], [tx + 62, ty - 4]], 4).concat([[tx + 40, ty - 10], [tx - 40, ty - 10]]);
    erasePoly(g, roof.concat([[tx + 36, ty + 34], [tx - 36, ty + 34]]));
    hatch(g, roof, { id: 'trf', d, color: pal.line, angle: 15, spacing: 4.5, w: 1.5, alpha: 0.6, maxLen: 30, p: seg(lp, 1.0, 1.6), fade });
    pencil(g, roof, { id: 'troof', d, color: pal.line, w: 2.6, closed: true, p: seg(lp, 0.6, 1.2), fade });
    pencil(g, [[tx - 34, ty - 10], [tx - 34, ty + 34], [tx + 34, ty + 34], [tx + 34, ty - 10]], { id: 'twall', d, color: pal.soft, w: 2.2, p: seg(lp, 0.8, 1.4), fade });
    hatch(g, MIST, { id: 'mist', d, color: pal.light, angle: 2, spacing: 7, w: 2.4, alpha: 0.6, maxLen: 120, p: seg(lp, 1.8, 2.6), fade });
    // скала: закрывает всё позади
    erasePoly(g, CLIFF_POLY);
    hatch(g, CLIFF_POLY, { id: 'clh', d, color: pal.soft, angle: 87, spacing: 9, w: 2, alpha: 0.5, p: seg(lp, 1.0, 2.4), fade });
    hatch(g, CLIFF_POLY, { id: 'clh2', d, color: pal.line, angle: 60, spacing: 16, w: 1.6, alpha: 0.25, p: seg(lp, 1.6, 2.6), fade });
    STRATA.forEach((s, i) => pencil(g, s, { id: 'str' + i, d, color: pal.soft, w: 2, p: seg(lp, 1.4 + i * 0.1, 2.0 + i * 0.1), fade }));
    pencil(g, CLIFF, { id: 'cliff', d, color: pal.line, w: 4.2, p: seg(lp, 0.3, 1.6), fade });
    // чайные кусты у подножия
    BUSHES.forEach(b => {
      erasePoly(g, b.pts);
      hatch(g, b.pts, { id: 'bh' + b.i, d, color: pal.line, angle: 48, spacing: 6, w: 1.7, alpha: 0.5, maxLen: 26, p: seg(lp, 1.6, 2.4), fade });
      pencil(g, b.pts.slice(0, 41), { id: 'bush' + b.i, d, color: pal.line, w: 3, p: seg(lp, 1.2 + b.i * 0.15, 1.9 + b.i * 0.15), fade });
    });
  }

  // ---------- персонажи: ключевые кадры ----------
  const walkOf = who => T.walks.find(w => w[0] === who);
  function walking(who, t) {
    const [, a, b, x0, x1] = walkOf(who);
    return { x: lerp(x0, x1, seg(t, a, b)), pose: F.walk(2 * Math.PI * (Math.min(t, b) - a) / T.walkCycle) };
  }
  const PS = F.POSES, mx = (a, b, t, t0, t1) => F.mix(a, b, easeIO(seg(t, t0, t1)));
  function student(t) {
    if (t < 4.2) return walking('student', t);
    const w = walking('student', 4.2).pose;
    let pose;
    if (t < 4.7) pose = mx(w, PS.stagger, t, 4.2, 4.7);
    else if (t < 5.2) pose = mx(PS.stagger, PS.kneel, t, 4.7, 5.2);
    else if (t < 10.6) pose = mx(PS.kneel, PS.lie, t, 5.2, 5.7);
    else if (t < 12.2) pose = mx(PS.lie, PS.sit, t, 10.6, 11.4);
    else pose = mx(PS.sit, PS.drink, t, 12.2, 12.7);
    return { x: lerp(470, 490, seg(t, 4.2, 4.7)), pose };
  }
  function monk(t) {
    if (t < 8.6) return walking('monk', t);
    const w = walking('monk', 8.6).pose;
    let pose;
    if (t < 9.1) pose = mx(w, PS.crouch, t, 8.6, 9.1);
    else if (t < 10.6) pose = mx(PS.crouch, PS.pour, t, 9.1, 9.3);
    else if (t < 12.2) pose = mx(PS.pour, PS.offer, t, 10.6, 11.1);
    else pose = mx(PS.offer, PS.crouch, t, 12.2, 12.8);
    return { x: 760, pose };
  }
  function hero(t) { // после экзамена: в красной мантии
    if (t < 22.4) return walking('red', t);
    const w = walking('red', 22.4).pose;
    let pose;
    if (t < 22.8) pose = mx(w, PS.stand, t, 22.4, 22.8);
    else if (t < 23.9) pose = mx(PS.stand, PS.bow, t, 22.8, 23.3);
    else if (t < 24.3) pose = mx(PS.bow, PS.stand, t, 23.9, 24.3);
    else if (t < 25.4) pose = mx(PS.stand, PS.hold, t, 24.3, 24.8);
    else if (t < 26.6) pose = mx(PS.hold, PS.throw, t, 25.4, 25.8);
    else if (t < 28.0) pose = mx(PS.throw, PS.stand, t, 26.6, 27.2);
    else pose = mx(PS.stand, PS.bow, t, 28.0, 28.8);
    return { x: 600, pose };
  }

  // ---------- реквизит ----------
  function teapot(g, at, tilt, d, fade) {
    const c = Math.cos(tilt), s = Math.sin(tilt), m = q => [at[0] + q[0] * c - q[1] * s, at[1] + q[0] * s + q[1] * c];
    const body = ellipse(0, 26, 34, 26, 0, 24).map(m);
    erasePoly(g, body);
    hatch(g, body, { id: 'tph', d, color: pal.soft, angle: 30, spacing: 6, w: 1.6, alpha: 0.6, fade });
    pencil(g, body, { id: 'tp', d, color: pal.line, w: 2.8, closed: true, fade });
    pencil(g, [[-30, 18], [-58, -2], [-66, -10]].map(m), { id: 'tps', d, color: pal.line, w: 3, fade }); // носик
    pencil(g, [[26, 8], [46, 14], [44, 38], [28, 40]].map(m), { id: 'tpr', d, color: pal.line, w: 2.6, fade }); // ручка
    pencil(g, [[-12, 0], [12, 0]].map(m), { id: 'tpl', d, color: pal.line, w: 4, fade, sketch: false });
    return m([-66, -10]); // кончик носика
  }
  function cup(g, c, d, fade) {
    const pts = [[c[0] - 20, c[1] - 26], [c[0] + 20, c[1] - 26], [c[0] + 13, c[1]], [c[0] - 13, c[1]]];
    erasePoly(g, pts);
    hatch(g, pts, { id: 'cuph', d, color: pal.cold, angle: 20, spacing: 5, w: 1.5, alpha: 0.6, fade });
    pencil(g, pts, { id: 'cup', d, color: pal.line, w: 2.6, closed: true, fade, sketch: false });
  }
  function steamPts(k, base, t, len) {
    const pts = [], ph = t * 2.6 + k * 2.1;
    for (let s = 0; s <= len; s += 6) pts.push([base[0] + k * 8 + (6 + 14 * Math.min(1, s / 120)) * Math.sin(s * 0.045 - ph), base[1] - s]);
    return pts;
  }

  // ---------- камера ----------
  const BASE = [1.15, 580, 1100, 540, 1200]; // общий план: земля у нижней кромки, над ней место под подписи
  function wide() { CAM.set.apply(null, BASE); }
  function cam(t) {
    if (t < 8.2) { CAM.set(BASE[0] * (1 + 0.03 * seg(t, 0, 8)), 580, 1100, 540, 1200); return; }
    if (t < 13.4) { const u = easeIO(seg(t, 8.2, 9.0)); CAM.set(lerp(1.185, 1.6, u), lerp(580, 640, u), lerp(1100, 1300, u), 540, lerp(1200, 1260, u)); return; }
    if (t < 16) { const u = easeIO(seg(t, 13.4, 15.0)); CAM.set(lerp(1.6, 2.8, u), lerp(640, 600, u), lerp(1300, 1180, u), 540, lerp(1260, 1020, u)); return; }
    wide();
  }

  // ---------- кадр ----------
  let lastStudent = null, lastMonk = null;
  function drawStory(g, t, d) {
    // 1-3: путь, падение, чай
    if (t < 15.2) {
      cam(t);
      const lf = 1 - seg(t, 14.4, 15.0);
      drawLand(g, t + 0.5, d, lf);
      let rm = null, rs = null;
      if (t >= T.walks[1][1]) { const m = monk(t); rm = F.draw(g, { id: 'monk', d, x: m.x, gy: GY, H: 400, dir: -1, pose: m.pose, robe: pal.soft, kind: 'monk', fade: lf }, pal); }
      const s = student(t);
      rs = F.draw(g, { id: 'stu', d, x: s.x, gy: GY, H: 380, dir: 1, pose: s.pose, robe: pal.cold, kind: 'student', prop: t < 4.7 ? 'books' : null, fade: lf }, pal);
      if (t >= 4.7 && t < 15.2) { // упавший узелок с книгами
        const bx = 360, box = [[bx - 30, GY - 34], [bx + 34, GY - 34], [bx + 34, GY], [bx - 30, GY]];
        F.erase(g, box); hatch(g, box, { id: 'bks', d, color: pal.soft, angle: 20, spacing: 6, w: 1.8, alpha: 0.6, fade: lf * seg(t, 4.7, 5.0) });
        pencil(g, box, { id: 'bkso', d, color: pal.line, w: 2.6, closed: true, fade: lf * seg(t, 4.7, 5.0) });
      }
      // чайник и чашка
      if (rm && t >= 8.6 && t < 12.8) {
        const tilt = -0.9 * easeIO(seg(t, 9.1, 9.4)) * (1 - easeIO(seg(t, 10.4, 10.7)));
        const spout = teapot(g, [rm.handFront[0] - 6, rm.handFront[1] - 20], tilt, d, lf);
        if (t >= 9.35 && t < 10.45) pencil(g, [spout, [lerp(spout[0], 700, 0.5), lerp(spout[1], GY - 26, 0.4)], [700, GY - 26]].map(q => [q[0], q[1]]),
          { id: 'stream', d, color: pal.cold, w: 3.4, alpha: 0.9, fade: lf, gaps: false });
      }
      let cp = [700, GY];
      if (t >= 11.0 && rm) cp = [lerp(700, rm.handFront[0], easeIO(seg(t, 11.0, 11.4))), lerp(GY, rm.handFront[1] + 14, easeIO(seg(t, 11.0, 11.4)))];
      if (t >= 11.4 && rm) cp = [lerp(rm.handFront[0], rs.handFront[0], easeIO(seg(t, 11.4, 12.0))), lerp(rm.handFront[1] + 14, rs.handFront[1] + 14, easeIO(seg(t, 11.4, 12.0)))];
      if (t >= 12.0) cp = [rs.handFront[0], rs.handFront[1] + 14];
      if (t >= 8.8) cup(g, cp, d, lf * seg(t, 8.8, 9.1));
      // пар: тонкий у чашки, потом растёт и становится свитком
      if (t >= 9.8 && t < 14.6) {
        const len = t < 13.4 ? 90 : lerp(90, 420, easeIO(seg(t, 13.4, 14.6)));
        for (let k = -1; k <= 1; k++) pencil(g, steamPts(k, [cp[0], cp[1] - 30], t, len * (k ? 0.75 : 1)), { id: 'steam' + k, d, color: pal.light, w: k ? 2.4 : 3.2, alpha: 0.9 });
      }
      lastStudent = rs; lastMonk = rm;
    }
    // переход: пар -> свиток (экран)
    if (t >= 14.6 && t < 16.0) {
      cam(14.6);
      const base = (() => { const s = student(14.6); return [600, 1180]; })();
      const steam = resample(steamPts(0, [CAM.map([600, 1180])[0], CAM.map([600, 1180])[1]], 14.6, 420 * 2.6).map(q => q), 1);
      const N = 70, u = easeIO(seg(t, 14.6, 15.5));
      const roll = []; for (let i = 0; i < N; i++) roll.push([540 + 18 * Math.sin(i / (N - 1) * Math.PI * 2), lerp(1230, 470, i / (N - 1))]);
      const pick = (a, i) => a[Math.round(i / (N - 1) * (a.length - 1))];
      const pts = []; for (let i = 0; i < N; i++) { const a = pick(steam, i), b = roll[i]; pts.push([lerp(a[0], b[0], u), lerp(a[1], b[1], u)]); }
      CAM.reset();
      pencil(g, pts, { id: 'morph', d, color: u < 0.5 ? pal.light : pal.line, w: lerp(3.2, 4.4, u), screen: true });
      if (t >= 15.5) pencil(g, [[480, 470], [600, 470]], { id: 'rodT', d, color: pal.line, w: 8, screen: true, p: seg(t, 15.5, 15.8) });
    }
    // 4: поворот — свиток 状元
    if (t >= T.turn && t < 18.0) {
      CAM.reset();
      const f = 1 - seg(t, 17.5, 17.9), w = lerp(40, 540, easeOut(seg(t, T.turn, T.turn + 0.4))), x0 = 540 - w / 2, x1 = 540 + w / 2;
      const sc = [[x0, 480], [x1, 480], [x1, 1220], [x0, 1220]];
      F.erase(g, sc);
      hatch(g, sc, { id: 'scr', d, color: pal.light, angle: 85, spacing: 8, w: 2, alpha: 0.55, screen: true, fade: f });
      pencil(g, sc, { id: 'scro', d, color: pal.line, w: 3.2, closed: true, screen: true, fade: f });
      pencil(g, [[x0 - 40, 476], [x1 + 40, 476]], { id: 'rod1', d, color: pal.line, w: 9, screen: true, fade: f, sketch: false });
      pencil(g, [[x0 - 40, 1224], [x1 + 40, 1224]], { id: 'rod2', d, color: pal.line, w: 9, screen: true, fade: f, sketch: false });
      glyph(g, '状', 540, 700, { id: 'zh', d, size: 220, fill: pal.warm, tone: pal.line, line: pal.line, p: seg(t, 16.25, 16.7), fade: f });
      glyph(g, '元', 540, 960, { id: 'yu', d, size: 220, fill: pal.warm, tone: pal.line, line: pal.line, p: seg(t, 16.45, 16.9), fade: f });
      if (t >= T.stamp) { // красная печать — первый красный в ролике
        const k = lerp(1.3, 1, seg(t, T.stamp, T.stamp + 0.1)), S = 46 * k, cx = 680, cy = 1130;
        const sq = [[cx - S, cy - S], [cx + S, cy - S], [cx + S, cy + S], [cx - S, cy + S]];
        hatch(g, sq, { id: 'st', d, color: pal.seal, angle: 45, spacing: 3.5, w: 2.4, alpha: 0.9, maxLen: 40, ends: 2, screen: true, fade: f });
        pencil(g, sq, { id: 'sto', d, color: pal.seal, w: 3, closed: true, screen: true, fade: f });
        glyph(g, '茶', cx, cy + 3, { id: 'stg', d, size: 70 * k, fill: pal.paperLight, tone: pal.paperLight, line: pal.paperLight, base: 1, lineW: 2, fade: f });
      }
      if (t < 17.4) {
        const R = rng('rays'), grow = easeOut(seg(t, T.turn, T.turn + 0.3)), rf = 1 - seg(t, 16.6, 17.4);
        for (let i = 0; i < 24; i++) {
          const a = i / 24 * Math.PI * 2 + (R() - 0.5) * 0.12, r0 = 420, r1 = r0 + (120 + R() * 200) * grow;
          pencil(g, [[540 + Math.cos(a) * r0 * 0.75, 850 + Math.sin(a) * r0], [540 + Math.cos(a) * r1 * 0.75, 850 + Math.sin(a) * r1]], { id: 'ray' + i, d, color: pal.warm, w: 6, alpha: 1, screen: true, fade: rf, gaps: false });
        }
      }
    }
    // 5-6: возвращение в красной мантии, мантия на кустах, постер
    if (t >= 17.6) {
      wide();
      drawLand(g, (t - 17.6) * 2.6, d, 1);
      const h = hero(t);
      const holding = t >= 24.3, thrown = t >= T.throw;
      const r = F.draw(g, { id: 'hero', d, x: h.x, gy: GY, H: 380, dir: 1, pose: h.pose, robe: holding ? pal.light : pal.seal, kind: 'student' }, pal);
      // мантия в руках -> летит -> ложится на кусты (переход формой)
      if (holding) {
        const N = 40, hf = r.handFront, hb = r.handBack;
        const held = []; // полотнище: верх в руках, низ свисает волнами
        const mx2 = (hf[0] + hb[0]) / 2, my2 = Math.min(hf[1], hb[1]);
        for (let i = 0; i < N; i++) {
          const u = i / (N - 1);
          if (u < 0.5) { const v = u * 2; held.push([mx2 - 95 + 190 * v, my2 - 8 + 10 * Math.sin(v * Math.PI)]); }
          else { const v = (u - 0.5) * 2; held.push([mx2 + 105 - 210 * v + 6 * Math.sin(v * 9 + t * 6), my2 + 230 + 14 * Math.sin(v * 14)]); }
        }
        const drape = [];
        for (let i = 0; i < N; i++) {
          const u = i / (N - 1);
          if (u < 0.5) { const v = u * 2, x = lerp(BUSHES[0].x - 70, BUSHES[2].x + 70, v); const b = BUSHES.reduce((m, q) => Math.min(m, q.y - Math.sqrt(Math.max(0, q.r * q.r * 1.3 - (x - q.x) * (x - q.x) * 0.75)) - 6), GY - 30); drape.push([x, Math.min(b, 1330)]); }
          else { const v = (u - 0.5) * 2, x = lerp(BUSHES[2].x + 70, BUSHES[0].x - 70, v); drape.push([x, 1318 + 10 * Math.sin(v * 22)]); }
        }
        const fl = easeIO(seg(t, T.throw, T.drape)), arc = Math.sin(fl * Math.PI) * 260;
        const pts = held.map((q, i) => [lerp(q[0], drape[i][0], fl) + Math.sin(i * 0.7 + t * 9) * 14 * Math.sin(fl * Math.PI), lerp(q[1], drape[i][1], fl) - arc]);
        const poly = thrown ? pts : held;
        F.erase(g, poly);
        hatch(g, poly, { id: 'robe', d, color: pal.seal, angle: 60, spacing: 5, w: 2.2, alpha: 0.9 });
        hatch(g, poly, { id: 'robe2', d, color: pal.seal, angle: -25, spacing: 11, w: 1.7, alpha: 0.6 });
        pencil(g, poly, { id: 'robeo', d, color: pal.line, w: 3.2, closed: true });
      }
      if (t >= T.posterFrom) {
        CAM.reset();
        ['大', '红', '袍'].forEach((ch, i) => glyph(g, ch, 270 + 270 * i, 290, { id: 'pg' + i, d, size: 200, fill: pal.seal, tone: pal.line, line: pal.line, p: seg(t, 33.0 + i * 0.3, 33.6 + i * 0.3) }));
      }
    }
  }

  function caption(g, lines, y0, size, t0, t1, tf, d, t, id) { // подпись с подложкой
    const f = 1 - seg(t, tf, tf + 0.3), n = lines.length;
    if (t < t0 || f <= 0) return;
    lines.forEach((s, i) => {
      const y = y0 + i * size * 1.02, a = t0 + (t1 - t0) * i / n, b = t0 + (t1 - t0) * (i + 1) / n;
      if (t < a) return;
      g.font = `600 ${size}px Hand`; const w = g.measureText(s).width;
      eraseRect(g, 540 - w / 2 - 22, y - size * 0.82, (w + 44) * seg(t, a, b), size * 1.05);
      hand(g, s, 540, y, { id: id + i, d, size, color: pal.line, p: seg(t, a, b), fade: f });
    });
  }
  function drawCaptions(g, t, d) {
    CAM.reset();
    caption(g, ['Эпоха Мин.', 'Студент идёт на экзамен', 'в столицу'], 250, 88, 0.6, 2.4, 5.6, d, t, 'c1');
    caption(g, ['Монах из храма поит его', 'чаем с кустов у скалы'], 250, 88, 8.4, 9.6, 13.2, d, t, 'c2');
    caption(g, ['Первый на экзамене!'], 340, 110, 16.1, 16.6, 17.5, d, t, 'c3');
    caption(g, ['Став первым, он вернулся', 'к чайным кустам'], 250, 88, 18.8, 19.8, 24.0, d, t, 'c4');
    caption(g, ['и укрыл их своей', 'красной мантией'], 250, 88, 26.0, 27.0, 32.6, d, t, 'c5');
    caption(g, ['Да Хун Пао'], 520, 112, 33.3, 33.9, 99, d, t, 'p1');
    caption(g, ['Большой красный халат'], 610, 76, 33.6, 34.2, 99, d, t, 'p2');
  }

  function story(t) { // реальное время -> время сюжета (паузы на чтение)
    let shift = 0;
    for (const [h, dur] of T.holds) { const hr = h + shift; if (t >= hr + dur) shift += dur; else if (t > hr) return h; }
    return t - shift;
  }

  function render(t) {
    const d = Math.floor(t * T.drawRate + 1e-6), tq = story(d / T.drawRate);
    ig.setTransform(1, 0, 0, 1, 0, 0); ig.globalCompositeOperation = 'source-over'; ig.globalAlpha = 1; ig.clearRect(0, 0, W, H);
    drawStory(ig, tq, d); drawCaptions(ig, tq, d);
    ig.globalCompositeOperation = 'destination-out'; ig.globalAlpha = 0.5; ig.drawImage(tooth, 0, 0);
    ig.globalCompositeOperation = 'source-over'; ig.globalAlpha = 1;
    og.globalCompositeOperation = 'source-over'; og.globalAlpha = 1; og.drawImage(paper, 0, 0);
    const wa = 0.09 * ease(seg(tq, T.turn - 0.05, T.turn + 0.25));
    if (wa > 0) { og.globalAlpha = wa; og.fillStyle = pal.wash; og.fillRect(0, 0, W, H); og.globalAlpha = 1; }
    og.drawImage(ink, 0, 0);
  }

  window.SCENES = { init, render };
})();
