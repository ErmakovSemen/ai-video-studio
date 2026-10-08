// «История чая» — коллаж: гравюры-вырезки, заголовки из букв, вклейки. Каждая глава — лист,
// новый лист въезжает поверх старого с рваным краем. Камера чуть наезжает (3%) за главу.
(function () {
  'use strict';
  const P = window.PENCIL, E = window.ENGRAVE, C = window.COLLAGE, T = window.T;
  const { W, H, rng, seg, lerp, ease, easeIO, easeOut, smooth, ellipse, pencil, hand } = P;
  let og, sheets = [], bufs = [], ENG = {}, tooth;

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
    T.scenes.forEach(s => { ENG[s.obj] = E.render(s.obj, s.obj === 'compass' ? 420 : 760); });
  }

  // ---------- содержимое вклеек ----------
  function drawManuscript(b, w, h) { // рукопись «Ча цзин»: колонки знаков, красный заголовок
    b.fillStyle = '#7a2a20'; b.font = '120px Glyph'; b.textAlign = 'center'; b.textBaseline = 'middle';
    b.fillText('茶', w - 70, 110); b.fillText('经', w - 70, 230);
    b.strokeStyle = '#7a2a20'; b.lineWidth = 2; b.strokeRect(w - 130, 40, 120, 260);
    const R = rng('manu');
    b.fillStyle = '#2a211a';
    for (let c = 0; c < 6; c++) { const x = w - 170 - c * 44; for (let k = 0; k < 14; k++) { const y = 50 + k * 30; if (R() < 0.08) continue; const s = 9 + R() * 5; b.fillRect(x - s, y, s * 2, 2.4); b.fillRect(x - 1.2, y - s * 0.6, 2.4, s * 1.4); if (R() < 0.5) b.fillRect(x - s * 0.7, y + 7, s * 1.4, 2); } }
    b.strokeStyle = 'rgba(80,40,20,0.35)'; b.lineWidth = 1; for (let c = 0; c <= 6; c++) { const x = w - 148 - c * 44; b.beginPath(); b.moveTo(x, 30); b.lineTo(x, h - 30); b.stroke(); }
  }
  function drawEdict(b, w, h) { // свиток-указ с печатью 明
    b.fillStyle = '#c9a33a'; b.fillRect(0, 0, w, 26); b.fillRect(0, h - 26, w, 26);
    const R = rng('edict'); b.fillStyle = '#2a211a';
    for (let c = 0; c < 8; c++) { const x = w - 50 - c * 40; for (let k = 0; k < 10; k++) { const y = 60 + k * 30; if (R() < 0.1) continue; const s = 8 + R() * 5; b.fillRect(x - s, y, s * 2, 2.4); b.fillRect(x - 1.2, y - s * 0.6, 2.4, s * 1.4); } }
    b.globalAlpha = 0.85; b.strokeStyle = '#b8322a'; b.lineWidth = 6; b.strokeRect(40, h - 140, 90, 90);
    b.fillStyle = '#b8322a'; b.font = '78px Glyph'; b.textAlign = 'center'; b.textBaseline = 'middle'; b.fillText('明', 85, h - 92); b.globalAlpha = 1;
  }
  function drawMap(b, w, h) { // карта Великого чайного пути
    const R = rng('map');
    b.strokeStyle = 'rgba(60,40,25,0.25)'; b.lineWidth = 1;
    for (let x = 0; x < w; x += 60) { b.beginPath(); b.moveTo(x, 0); b.lineTo(x, h); b.stroke(); }
    for (let y = 0; y < h; y += 60) { b.beginPath(); b.moveTo(0, y); b.lineTo(w, y); b.stroke(); }
    const coast = []; for (let k = 0; k <= 20; k++) coast.push([w - 40 - 60 * Math.sin(k * 0.5) - R() * 20, h * 0.35 + k * (h * 0.6 / 20)]);
    b.strokeStyle = '#3a3027'; b.lineWidth = 2.5; b.beginPath(); coast.forEach((p, i) => (i ? b.lineTo(p[0], p[1]) : b.moveTo(p[0], p[1]))); b.stroke();
    for (let k = 0; k < 6; k++) { const y = h * 0.4 + k * 50; b.beginPath(); b.moveTo(w - 20, y); b.quadraticCurveTo(w - 30, y + 8, w - 45, y); b.stroke(); }
    const mts = [[200, 330], [240, 320], [280, 335], [330, 300], [370, 315]];
    mts.forEach(([x, y]) => { b.beginPath(); b.moveTo(x - 22, y + 18); b.lineTo(x, y - 18); b.lineTo(x + 22, y + 18); b.stroke(); b.beginPath(); b.moveTo(x, y - 18); b.lineTo(x + 8, y + 18); b.stroke(); });
    const cities = [['Пекин', w - 150, h - 120], ['Кяхта', w * 0.52, h * 0.42], ['Иркутск', w * 0.38, h * 0.3], ['Москва', 90, 110]];
    const route = [[w - 150, h - 120], [w - 220, h * 0.62], [w * 0.52, h * 0.42], [w * 0.38, h * 0.3], [w * 0.2, h * 0.22], [90, 110]];
    b.strokeStyle = '#b8322a'; b.lineWidth = 4; b.setLineDash([12, 10]); b.beginPath(); route.forEach((p, i) => (i ? b.lineTo(p[0], p[1]) : b.moveTo(p[0], p[1]))); b.stroke(); b.setLineDash([]);
    cities.forEach(([n, x, y]) => { b.fillStyle = '#b8322a'; b.beginPath(); b.arc(x, y, 9, 0, 7); b.fill(); b.fillStyle = '#2a211a'; b.font = '38px Hand'; b.textAlign = 'center'; b.fillText(n, x, y - 22); });
  }

  // ---------- главы (локальное время lt, координаты экрана) ----------
  const L = T.L;
  const CHIPS = [['белый', '#f4f1ea'], ['зелёный', '#5d7a4a', '#f6f2e8'], ['улун', '#c9a33a'], ['красный', '#b8322a', '#f6f2e8'], ['пуэр', '#3a2a20', '#f6f2e8']];
  function common(g, s, lt, d, i) {
    C.label(g, s.label, 60, 110, lt, { t: L.label });
    C.ransom(g, s.head, lt, { id: 'h' + i, x: 545, y: 330, size: s.head.length > 9 ? 128 : 150, maxW: 940, t: L.head, step: L.letter });
  }
  function notes(g, s, lt, x, y) { C.typed(g, s.note, x, s.note.length > 3 ? y - 60 : y, lt, { t: L.note, cps: T.cps, size: 52 }); }
  const SC = [
    (g, s, lt, d) => { // легенда
      common(g, s, lt, d, 0);
      C.cutout(g, ENG.cauldron, 'cauldron', 555, 900, lt, d, { t: L.obj, rot: -0.03 });
      C.ticket(g, { x: 250, y: 1215, w: 330, h: 150, rot: -0.1, t: L.ins1, lines: ['2737', 'до н. э.'], size: 64, size2: 34 }, lt);
      C.scribble(g, { id: 'sc0', text: 'лист упал в котёл!', x: 800, y: 560, t: L.ins2, size: 54, arrow: smooth([[760, 590], [700, 640], [640, 700]], 6) }, lt, d);
      notes(g, s, lt, 110, 1390);
      C.seal(g, { x: 905, y: 1220, size: 64, rot: 0.08, t: s.sealAt, chars: s.seal }, lt);
    },
    (g, s, lt, d) => { // Тан
      common(g, s, lt, d, 1);
      C.doc(g, { id: 'manu', x: 800, y: 720, w: 380, h: 470, rot: 0.06, t: L.ins1, draw: drawManuscript }, lt, d);
      if (lt > L.ins1 + 0.3) C.clip(g, 900, 470, 0.25);
      C.scribble(g, { id: 'sc1', text: '3 свитка, 10 глав', x: 800, y: 1010, t: L.ins2 + 0.4, size: 52, arrow: smooth([[880, 990], [900, 960], [890, 930]], 6) }, lt, d);
      C.cutout(g, ENG.book, 'book', 470, 960, lt, d, { t: L.obj, rot: -0.04, scale: 0.92 });
      C.postage(g, { x: 220, y: 640, w: 200, h: 240, rot: -0.12, t: L.ins2, color: '#7a2a20', draw: (b, w, h) => { b.fillStyle = '#f6f2e8'; b.font = '64px R_Oswald'; b.textAlign = 'center'; b.textBaseline = 'middle'; b.fillText('760', 0, -20); b.font = '30px R_Mono'; b.fillText('КИТАЙ', 0, 50); } }, lt, d);
      notes(g, s, lt, 110, 1390);
      C.seal(g, { x: 905, y: 1240, size: 58, rot: -0.06, t: s.sealAt, chars: s.seal }, lt);
    },
    (g, s, lt, d) => { // Сун
      common(g, s, lt, d, 2);
      C.cutout(g, ENG.bowl, 'bowl', 520, 930, lt, d, { t: L.obj, rot: 0.02 });
      C.postage(g, { x: 860, y: 640, w: 210, h: 250, rot: 0.1, t: L.ins1, color: '#2e4a63', draw: (b, w, h) => { b.fillStyle = '#f6f2e8'; b.font = '56px R_Oswald'; b.textAlign = 'center'; b.textBaseline = 'middle'; b.fillText('1191', 0, -30); b.font = '28px R_Mono'; b.fillText('ЯПОНИЯ', 0, 40); b.strokeStyle = '#f6f2e8'; b.lineWidth = 3; b.beginPath(); b.moveTo(-60, 90); b.lineTo(0, 40 + 20); b.lineTo(60, 90); b.stroke(); } }, lt, d);
      C.scribble(g, { id: 'sc2', text: 'матча!', x: 860, y: 1180, t: L.ins2, size: 60, arrow: smooth([[810, 1150], [760, 1110], [700, 1080]], 6) }, lt, d);
      notes(g, s, lt, 110, 1360);
      C.seal(g, { x: 930, y: 1560, size: 58, rot: -0.1, t: s.sealAt, chars: s.seal }, lt);
    },
    (g, s, lt, d) => { // Мин
      common(g, s, lt, d, 3);
      C.doc(g, { id: 'edict', x: 830, y: 880, w: 360, h: 520, rot: 0.05, t: L.ins1, paper: '#efe2bf', draw: drawEdict }, lt, d);
      if (lt > L.ins1 + 0.3) C.clip(g, 760, 620, -0.2);
      C.cutout(g, ENG.teapot, 'teapot', 460, 960, lt, d, { t: L.obj, rot: -0.03, scale: 0.92 });
      C.scribble(g, { id: 'sc3', text: 'глина из Исина', x: 330, y: 680, t: L.ins2, size: 54, arrow: smooth([[330, 700], [360, 760], [400, 800]], 6) }, lt, d);
      notes(g, s, lt, 110, 1360);
    },
    (g, s, lt, d) => { // Россия
      common(g, s, lt, d, 4);
      C.doc(g, { id: 'map', x: 545, y: 860, w: 860, h: 620, rot: -0.02, t: L.obj, paper: '#e8dcbc', draw: drawMap }, lt, d);
      if (lt > L.obj + 0.3) C.clip(g, 300, 560, -0.15);
      C.cutout(g, ENG.compass, 'compass', 860, 1110, lt, d, { t: L.ins1, rot: 0.1 });
      C.scribble(g, { id: 'sc4', text: 'через Сибирь', x: 420, y: 1110, t: L.ins2 + 0.5, size: 50 }, lt, d);
      C.ticket(g, { x: 270, y: 1190, w: 420, h: 140, rot: -0.06, t: L.ins2, lines: ['ЧАЙНЫЙ ПУТЬ', 'Кяхта — Москва'], size: 46, size2: 30 }, lt);
      notes(g, s, lt, 110, 1400);
      C.ticket(g, { x: 870, y: 560, w: 260, h: 120, rot: 0.12, t: s.sealAt, lines: ['4 ПУДА', '≈ 64 кг'], size: 46, size2: 30, bg: '#f4f1ea' }, lt);
    },
    (g, s, lt, d) => { // самовар
      common(g, s, lt, d, 5);
      C.cutout(g, ENG.samovar, 'samovar', 520, 920, lt, d, { t: L.obj, rot: 0.02 });
      C.postage(g, { x: 880, y: 680, w: 220, h: 260, rot: 0.12, t: L.ins1, color: '#3f5a3a', draw: (b, w, h) => { b.fillStyle = '#f6f2e8'; b.textAlign = 'center'; b.textBaseline = 'middle'; b.font = '60px R_Oswald'; b.fillText('1778', 0, -40); b.font = '30px R_Mono'; b.fillText('ТУЛА', 0, 20); b.strokeStyle = '#f6f2e8'; b.lineWidth = 3; b.beginPath(); b.arc(0, 75, 22, 0, 7); b.stroke(); b.beginPath(); b.arc(0, 75, 12, 0, 7); b.stroke(); } }, lt, d);
      C.ticket(g, { x: 900, y: 1180, w: 250, h: 110, rot: -0.1, t: L.ins2 + 0.3, lines: ['ПЕРВАЯ', 'мастерская'], size: 40, size2: 26, bg: '#f4f1ea' }, lt);
      C.scribble(g, { id: 'sc5', text: 'чай с баранками', x: 235, y: 505, t: L.ins2, size: 48, arrow: smooth([[250, 530], [280, 620], [330, 700]], 6) }, lt, d);
      notes(g, s, lt, 110, 1420);
    },
    (g, s, lt, d) => { // сегодня
      common(g, s, lt, d, 6);
      C.cutout(g, ENG.cup, 'cup', 545, 910, lt, d, { t: L.obj, rot: -0.02 });
      C.ticket(g, { x: 850, y: 640, w: 240, h: 130, rot: 0.14, t: L.ins1, lines: ['№ 2', 'в мире'], size: 58, size2: 30, bg: '#b8322a' }, lt);
      C.scribble(g, { id: 'sc6', text: 'пора заварить!', x: 300, y: 620, t: L.ins2, size: 58, arrow: smooth([[320, 650], [370, 720], [420, 780]], 6) }, lt, d);
      notes(g, s, lt, 150, 1330);
      CHIPS.forEach(([n, bg, fg], k) => C.ticket(g, { x: 135 + k * 202, y: 1545 + (k % 2 ? -14 : 10), w: 196, h: 92, rot: [-0.08, 0.06, -0.03, 0.09, -0.06][k], t: s.chipAt + k * 0.15, lines: [n], size: 40, bg, fg }, lt));
      C.seal(g, { x: 950, y: 1340, size: 58, rot: 0.06, t: s.sealAt, chars: s.seal }, lt);
    },
  ];

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
    const S = T.scenes; let cur = S.length - 1; while (cur > 0 && tq < S[cur].start) cur--;
    const lt = i => tq - S[i].local0, camU = i => seg(tq, S[i].start, S[i].start + S[i].dur);
    const u = cur > 0 ? seg(tq, S[cur].start, S[cur].start + T.trans) : 1;
    if (u < 1) { drawCam(renderScene(cur - 1, lt(cur - 1), d), camU(cur - 1)); sheetIn(renderScene(cur, lt(cur), d), u, cur, camU(cur)); }
    else drawCam(renderScene(cur, lt(cur), d), camU(cur));
  }
  window.SCENES = { init, render };
})();
