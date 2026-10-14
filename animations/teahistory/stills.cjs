// Быстрые стоп-кадры без рендера видео: node stills.cjs . out/stills.png 0 6 28.5 64.9
// Открывает index.html через локальный http (шрифты), вызывает SCENES.render(t), склеивает кадры в лист.
const load = m => { try { return require(m); } catch (e) { return null; } };
const { chromium } = load('playwright-core') || load('playwright') || require('/opt/node-tools/node_modules/playwright-core');
const http = require('http'), fs = require('fs'), path = require('path');
const [dir, out, ...ts] = process.argv.slice(2);
const types = { '.html': 'text/html', '.js': 'text/javascript', '.ttf': 'font/ttf', '.json': 'application/json' };
const srv = http.createServer((q, r) => { const f = path.join(dir, decodeURIComponent(q.url.split('?')[0])); fs.readFile(f, (e, b) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }); r.end(b); }); }).listen(8765);
(async () => {
  const exe = fs.existsSync('/opt/pw-browsers/chromium') ? { executablePath: '/opt/pw-browsers/chromium' } : {};
  const br = await chromium.launch(exe);
  const pg = await br.newPage({ viewport: { width: 1080, height: 1920 } });
  pg.on('console', m => { if (m.type() === 'error') console.log('ERR', m.text()); });
  pg.on('pageerror', e => console.log('PAGEERR', e.message));
  await pg.goto('http://localhost:8765/index.html'); await pg.waitForTimeout(2500);
  const imgs = [];
  for (const t of ts) { imgs.push(await pg.evaluate(t => { SCENES.render(+t); return document.getElementById('cv').toDataURL('image/jpeg', 0.85); }, t)); }
  const html = `<body style="margin:0;background:#111;display:flex;flex-wrap:wrap;width:${Math.min(ts.length, 6) * 360}px">` + imgs.map((u, i) => `<div style="position:relative"><img src="${u}" width=360><span style="position:absolute;left:6px;top:4px;color:red;font:bold 22px sans-serif">${ts[i]}</span></div>`).join('') + '</body>';
  const p2 = await br.newPage({ viewport: { width: Math.min(ts.length, 6) * 360, height: 640 * Math.ceil(ts.length / 6) } });
  await p2.setContent(html); await p2.waitForTimeout(300); await p2.screenshot({ path: out, fullPage: true });
  await br.close(); srv.close();
})();
