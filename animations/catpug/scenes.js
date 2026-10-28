// «Все кошки — мопсы» — коллаж: гравюры-вырезки, заголовки из букв, вклейки. Каждая глава — лист,
// новый лист въезжает поверх старого с рваным краем. Камера чуть наезжает (3%) за главу.
(function () {
  'use strict';
  const P = window.PENCIL, E = window.ENGRAVE, C = window.COLLAGE, T = window.T;
  const { W, H, rng, seg, lerp, ease, easeIO, easeOut, smooth, ellipse, pencil, hand } = P;
  let og, sheets = [], bufs = [], ENG = {}, tooth, coverSheet, coverBuf;

  function init(theme, canvas) {
    og = canvas.getContext('2d');
    tooth = P.makeTooth();
    const pal = P.PALETTES.kraft;
    const tones = ['#d3d0c8', '#cfc9bd', '#d6d2c9', '#cdc8bf', '#d4cdbf', '#d0ccc4', '#d8d3c8'];
    sheets = tones.map((tn, i) => P.makePaper(Object.assign({}, pal, { name: 'sheet' + i, paper: tn, paperLight: '#e8e5de', paperDark: '#9d978b', grain: 16 })));
    bufs = T.scenes.map(() => C.mk(W, H));
    const CL = [ // [газеты [x,y,w,h,rot]], кольца, скрепка
      [[[980, 1560, 420, 360, 0.12], [90, 760, 300, 420, -0.08]], [[930, 470, 95]]],
      [[[110, 1520, 380, 300, -0.1], [990, 300, 320, 260, 0.15]], [[180, 1100, 80]]],
      [[[1000, 1450, 380, 420, 0.1], [80, 520, 260, 360, -0.12]], [[300, 1200, 90]]],
      [[[90, 1560, 400, 300, 0.06], [1010, 560, 260, 300, -0.1]], [[880, 1240, 85]]],
      [[[1000, 1560, 360, 320, -0.08], [70, 380, 240, 260, 0.1]], [[150, 1180, 70]]],
      [[[120, 1100, 320, 380, -0.12], [990, 1500, 360, 330, 0.08]], [[860, 380, 95]]],
      [[[90, 640, 300, 360, 0.1], [1000, 1180, 320, 380, -0.1]], [[270, 1250, 90]]],
    ];
    sheets.forEach((sh, i) => { const g = sh.getContext('2d'); CL[i][0].forEach(([x, y, w, h, r], k) => C.newsprint(g, x, y, w, h, r, 'np' + i + k)); CL[i][1].forEach(([x, y, r], k) => C.stain(g, x, y, r, 'st' + i + k)); });
    ['cat', 'pug', 'prof', 'loupe'].forEach(n => { ENG[n] = E.render(n, 760); });
    coverSheet = P.makePaper(Object.assign({}, pal, { name: 'sheetCover', paper: '#d2cec5', paperLight: '#e8e5de', paperDark: '#9d978b', grain: 16 }));
    const cg = coverSheet.getContext('2d');
    [[1010, 300, 300, 300, 0.12], [80, 1540, 380, 320, -0.08], [1000, 1700, 320, 260, 0.1]].forEach(([x, y, w, h, r], k) => C.newsprint(cg, x, y, w, h, r, 'npc' + k));
    C.stain(cg, 960, 1260, 90, 'stc');
    coverBuf = C.mk(W, H);
  }

  // ---------- содержимое вклеек ----------
  const ink = (b, font, color = '#2a211a') => { b.font = font; b.fillStyle = color; };
  function drawPoll(b, w, h) { // планшет с «опросом»: столбики ДА 100% / НЕТ 0%
    b.textAlign = 'center'; b.textBaseline = 'middle';
    ink(b, '600 46px R_Oswald'); b.fillText('ОПРОС', w / 2, 60);
    ink(b, '30px R_Mono'); b.fillText('Кошки — мопсы?', w / 2, 112);
    b.strokeStyle = '#2a211a'; b.lineWidth = 3; b.beginPath(); b.moveTo(60, h - 120); b.lineTo(w - 40, h - 120); b.stroke();
    b.fillStyle = '#b8322a'; b.fillRect(90, 170, 120, h - 290);
    b.strokeStyle = '#2a211a'; b.lineWidth = 2; b.strokeRect(90, 170, 120, h - 290); b.strokeRect(w - 210, h - 124, 120, 4);
    ink(b, '600 44px R_Oswald', '#f6f2e8'); b.fillText('100%', 150, 220);
    ink(b, '600 40px R_Oswald'); b.fillText('ДА', 150, h - 80); b.fillText('НЕТ', w - 150, h - 80); b.fillText('0%', w - 150, h - 160);
    ink(b, '30px R_Mono', '#5a5048'); b.fillText('опрошено: 3 мопса', w / 2, h - 30);
  }
  function drawDiploma(b, w, h) {
    b.strokeStyle = '#7a5a2a'; b.lineWidth = 4; b.strokeRect(14, 14, w - 28, h - 28); b.lineWidth = 1.5; b.strokeRect(24, 24, w - 48, h - 48);
    b.textAlign = 'center'; b.textBaseline = 'middle';
    ink(b, '44px R_Ruslan', '#7a2a20'); b.fillText('ДИПЛОМ', w / 2, 62);
    ink(b, '24px R_Mono'); b.fillText('доктор', w / 2, 112); b.fillText('мопсологии', w / 2, 142);
    ink(b, '30px Hand', '#2e4a63'); b.fillText('проф. Мопсон', w / 2 - 30, h - 52);
    b.globalAlpha = 0.85; b.fillStyle = '#b8322a'; b.beginPath(); b.arc(w - 62, h - 62, 30, 0, 7); b.fill(); b.globalAlpha = 1;
  }
  function drawDict(b, w, h) { // страница толкового словаря, нужная статья жирная
    const R = rng('dict'); b.textBaseline = 'alphabetic'; b.textAlign = 'left';
    ink(b, '600 34px R_Oswald'); b.fillText('МОП — МОР', 40, 56);
    b.fillStyle = 'rgba(40,34,28,0.45)';
    for (let y = 100; y < h - 30; y += 22) { if (y > 190 && y < 330) continue; let x = 40; while (x < w - 60) { const ww = 20 + R() * 70; b.fillRect(x, y, ww, 6); x += ww + 12; } }
    ink(b, '700 38px R_Mono'); b.fillText('МОПС,', 40, 222); ink(b, '30px R_Mono'); b.fillText('м. — любое существо,', 185, 222);
    b.fillText('что спит 16 часов в сутки.', 40, 266); ink(b, 'italic 26px R_Mono', '#5a5048'); b.fillText('Ср.: кошка, кот, котик.', 40, 308);
    b.strokeStyle = '#b8322a'; b.lineWidth = 4; b.beginPath(); b.ellipse(108, 212, 82, 36, -0.04, 0, 7); b.stroke();
  }
  function drawZero(b, w, h) {
    b.textAlign = 'center'; b.textBaseline = 'middle';
    ink(b, '600 34px R_Oswald'); b.fillText('ОПРОВЕРЖЕНИЙ', w / 2, 48);
    ink(b, '120px R_Oswald', '#b8322a'); b.fillText('0', w / 2, h / 2 + 30);
    ink(b, '24px R_Mono', '#5a5048'); b.fillText('найдено', w / 2, h - 32);
  }

  // ---------- главы (локальное время lt, координаты экрана) ----------
  const L = T.L;
  function common(g, s, lt, d, i) {
    C.label(g, s.label, 60, 110, lt, { t: L.label });
    C.ransom(g, s.head, lt, { id: 'h' + i, x: 545, y: 330, size: s.head.length > 9 ? 128 : 150, maxW: 940, t: L.head, step: L.letter });
  }
  function notes(g, s, lt, x, y) { C.typed(g, s.note, x, s.note.length > 3 ? y - 60 : y, lt, { t: L.note, cps: T.cps, size: 52 }); }
  // финал шага: штамп «ДОКАЗАНО»
  function proved(g, s, lt, st, tr) {
    C.rubber(g, { x: st[0], y: st[1], rot: st[2], size: 52, text: 'ДОКАЗАНО', t: s.sealAt }, lt);
  }
  const pawStamp = (b) => { b.fillStyle = '#f6f2e8'; b.textAlign = 'center'; b.textBaseline = 'middle'; b.font = '78px R_Oswald'; b.fillText('4', 0, -34); b.font = '28px R_Mono'; b.fillText('ЛАПЫ', 0, 40); };
  const SC = [
    (g, s, lt, d) => { // 4 лапы
      common(g, s, lt, d, 0);
      C.cutout(g, ENG.cat, 'cat', 300, 930, lt, d, { t: L.obj, rot: -0.04, scale: 0.62 });
      C.cutout(g, ENG.pug, 'pug', 780, 960, lt, d, { t: L.obj + 0.15, rot: 0.04, scale: 0.62 });
      C.postage(g, { x: 900, y: 600, w: 190, h: 230, rot: 0.1, t: L.ins1, color: '#2e4a63', draw: pawStamp }, lt, d);
      C.scribble(g, { id: 'sc0', text: 'одно и то же!', x: 300, y: 600, t: L.ins2, size: 56, arrow: smooth([[330, 630], [420, 700], [560, 760]], 6) }, lt, d);
      notes(g, s, lt, 110, 1390);
      proved(g, s, lt, [790, 1245, -0.12], [250, 1195, 0.06]);
    },
    (g, s, lt, d) => { // опрос
      common(g, s, lt, d, 1);
      C.doc(g, { id: 'poll', x: 790, y: 860, w: 380, h: 500, rot: 0.06, t: L.ins1, paper: '#efe9da', draw: drawPoll }, lt, d);
      if (lt > L.ins1 + 0.3) C.clip(g, 880, 610, 0.25);
      C.cutout(g, ENG.pug, 'pug', 360, 960, lt, d, { t: L.obj, rot: -0.03, scale: 0.78 });
      C.ticket(g, { x: 230, y: 610, w: 240, h: 110, rot: -0.1, t: L.ins2, lines: ['n = 3'], size: 50 }, lt);
      C.scribble(g, { id: 'sc1', text: 'надёжно!', x: 820, y: 1170, t: L.ins2 + 0.4, size: 56, arrow: smooth([[800, 1140], [790, 1110], [800, 1080]], 6) }, lt, d);
      notes(g, s, lt, 110, 1400);
      proved(g, s, lt, [300, 1250, 0.1], [820, 1265, -0.06]);
    },
    (g, s, lt, d) => { // профессор
      common(g, s, lt, d, 2);
      C.cutout(g, ENG.prof, 'prof', 470, 930, lt, d, { t: L.obj, rot: -0.02, scale: 0.86 });
      C.doc(g, { id: 'dipl', x: 860, y: 640, w: 320, h: 230, rot: 0.1, t: L.ins1, paper: '#f1e6c8', draw: drawDiploma }, lt, d);
      C.scribble(g, { id: 'sc2', text: 'выдал себе сам', x: 840, y: 860, t: L.ins2, size: 46, arrow: smooth([[860, 835], [870, 800], [865, 770]], 6) }, lt, d);
      notes(g, s, lt, 110, 1400);
      proved(g, s, lt, [790, 1250, -0.1], [240, 1250, 0.07]);
    },
    (g, s, lt, d) => { // словарь
      common(g, s, lt, d, 3);
      C.doc(g, { id: 'dict', x: 590, y: 760, w: 740, h: 400, rot: -0.03, t: L.ins1 - 0.7, paper: '#ebe4d2', draw: drawDict }, lt, d);
      if (lt > L.ins1 - 0.4) C.clip(g, 270, 560, -0.2);
      C.cutout(g, ENG.cat, 'cat', 300, 1110, lt, d, { t: L.obj + 0.6, rot: -0.06, scale: 0.42 });
      C.ticket(g, { x: 850, y: 1050, w: 260, h: 120, rot: 0.08, t: L.ins2, lines: ['16 ч', 'сна в сутки'], size: 50, size2: 26 }, lt);
      C.scribble(g, { id: 'sc3', text: 'Zzz…', x: 520, y: 1040, t: L.ins2 + 0.3, size: 64 }, lt, d);
      notes(g, s, lt, 110, 1400);
      C.rubber(g, { x: 860, y: 1240, rot: -0.12, size: 44, text: 'ДОКАЗАНО', t: s.sealAt }, lt);
    },
    (g, s, lt, d) => { // перс
      common(g, s, lt, d, 4);
      C.cutout(g, ENG.cat, 'cat', 520, 930, lt, d, { t: L.obj, rot: 0.02, scale: 0.86 });
      C.ticket(g, { x: 220, y: 620, w: 320, h: 130, rot: -0.1, t: L.ins1, lines: ['1 порода', 'из 70'], size: 48, size2: 30 }, lt);
      C.scribble(g, { id: 'sc4', text: 'почти мопс!', x: 860, y: 600, t: L.ins2, size: 54, arrow: smooth([[840, 630], [760, 690], [640, 740]], 6) }, lt, d);
      notes(g, s, lt, 110, 1400);
      proved(g, s, lt, [810, 1235, -0.1], [250, 1205, 0.06]);
    },
    (g, s, lt, d) => { // обратное?
      common(g, s, lt, d, 5);
      C.cutout(g, ENG.loupe, 'loupe', 480, 900, lt, d, { t: L.obj, rot: -0.08, scale: 0.8 });
      C.doc(g, { id: 'zero', x: 870, y: 630, w: 280, h: 240, rot: 0.08, t: L.ins1, paper: '#efe9da', draw: drawZero }, lt, d);
      C.scribble(g, { id: 'sc5', text: 'искали 5 минут', x: 270, y: 620, t: L.ins2, size: 50 }, lt, d);
      notes(g, s, lt, 110, 1400);
      proved(g, s, lt, [790, 1250, -0.1], [250, 1255, 0.06]);
    },
    (g, s, lt, d) => { // Ч.Т.Д.
      common(g, s, lt, d, 6);
      C.cutout(g, ENG.cat, 'cat', 300, 820, lt, d, { t: L.obj, rot: -0.04, scale: 0.55 });
      C.cutout(g, ENG.pug, 'pug', 780, 840, lt, d, { t: L.obj + 0.15, rot: 0.04, scale: 0.55 });
      C.ticket(g, { x: 545, y: 560, w: 420, h: 120, rot: -0.04, t: L.ins1, lines: ['КОШКА = МОПС'], size: 54, bg: '#b8322a', fg: '#f6f2e8' }, lt);
      C.scribble(g, { id: 'sc6', text: '«я не мопс!»', x: 300, y: 1130, t: L.ins2, size: 54, arrow: smooth([[300, 1100], [300, 1060], [310, 1030]], 6) }, lt, d);
      notes(g, s, lt, 110, 1330);
      C.rubber(g, { x: 560, y: 860, rot: -0.14, size: 78, text: 'ДОКАЗАНО', t: s.sealAt }, lt);
    },
  ];

  // ---------- обложка «Все кошки — мопсы»: стоит целиком с первого кадра (постер для ленты) ----------
  function renderCover(d) {
    const g = coverBuf.getContext('2d'), lt = 99;
    g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
    g.drawImage(coverSheet, 0, 0);
    P.CAM.reset();
    C.label(g, '7 ШАГОВ · 0 ЛОГИКИ', 60, 110, lt, { t: 0 });
    C.ransom(g, 'ВСЕ КОШКИ', lt, { id: 'cv1', x: 540, y: 330, size: 150, maxW: 1060, t: 0 });
    C.ransom(g, 'МОПСЫ', lt, { id: 'cv2', x: 470, y: 560, size: 200, maxW: 900, t: 0 });
    C.ticket(g, { x: 830, y: 770, w: 420, h: 130, rot: -0.08, t: 0, lines: ['НАУЧНО ДОКАЗАНО'], size: 48, bg: '#b8322a', fg: '#f6f2e8' }, lt);
    C.cutout(g, ENG.cat, 'cat', 300, 1130, lt, d, { t: 0, rot: -0.05, scale: 0.62 });
    C.cutout(g, ENG.pug, 'pug', 790, 1160, lt, d, { t: 0, rot: 0.05, scale: 0.62 });
    hand(g, '=', 548, 1160, { id: 'eq', d, size: 280, color: '#b8322a', p: 1 });
    C.ticket(g, { x: 230, y: 780, w: 300, h: 120, rot: -0.1, t: 0, lines: ['за 1 минуту'], size: 46 }, lt);
    C.rubber(g, { x: 560, y: 1520, rot: -0.06, size: 58, text: 'Ч.Т.Д.', t: 0 }, lt);
    return coverBuf;
  }

  function renderScene(i, lt, d) {
    const b = bufs[i], g = b.getContext('2d');
    g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
    g.drawImage(sheets[i], 0, 0);
    P.CAM.reset();
    SC[i](g, T.scenes[i], lt, d);
    return b;
  }
  // камера: лёгкий наезд за главу
  function drawCam(img, u) {
    const s = 1 + 0.03 * easeIO(u);
    og.save(); og.translate(W / 2, H * 0.45); og.scale(s, s); og.translate(-W / 2, -H * 0.45); og.drawImage(img, 0, 0); og.restore();
  }
  // новый лист въезжает справа с рваным краем
  const tornCache = [];
  function tornEdge(i) {
    if (tornCache[i]) return tornCache[i];
    const R = rng('torn' + i), pts = []; let x = 0;
    for (let y = -20; y <= H + 20; y += 14) { x += (R() - 0.5) * 16; x = Math.max(-22, Math.min(22, x)); pts.push([x, y]); }
    return (tornCache[i] = pts);
  }
  function sheetIn(img, u, i, camU) {
    const k = easeIO(u), X = lerp(W + 60, 0, k), edge = tornEdge(i);
    const path = (dx = 0, grow = 0) => { og.beginPath(); og.moveTo(W + 400, -20); edge.forEach(([x, y]) => og.lineTo(X + x + dx - grow, y)); og.lineTo(W + 400, H + 20); og.closePath(); };
    og.save(); path(-14, 0); og.fillStyle = 'rgba(25,20,15,0.35)'; og.fill(); og.restore();
    og.save(); path(0, 8); og.fillStyle = '#efece5'; og.fill(); og.restore(); // белый «сердечник» рваной бумаги
    og.save(); path(0, 0); og.clip(); og.translate(X, 0); drawCam(img, camU); og.restore();
  }

  function render(t) {
    const d = Math.floor(t * T.drawRate + 1e-6), tq = d / T.drawRate;
    og.setTransform(1, 0, 0, 1, 0, 0); og.globalAlpha = 1; og.globalCompositeOperation = 'source-over';
    const S = T.scenes;
    if (tq < S[0].start) { drawCam(renderCover(d), seg(tq, 0, S[0].start)); return; } // обложка
    let cur = S.length - 1; while (cur > 0 && tq < S[cur].start) cur--;
    const lt = i => tq - S[i].local0, camU = i => seg(tq, S[i].start, S[i].start + S[i].dur);
    const u = seg(tq, S[cur].start, S[cur].start + T.trans);
    if (u < 1) { drawCam(cur > 0 ? renderScene(cur - 1, lt(cur - 1), d) : renderCover(d), cur > 0 ? camU(cur - 1) : 1); sheetIn(renderScene(cur, lt(cur), d), u, cur, camU(cur)); }
    else drawCam(renderScene(cur, lt(cur), d), camU(cur));
  }
  window.SCENES = { init, render };
})();
