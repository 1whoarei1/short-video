'use strict';
// Real-browser regression: BROWSER_PATH=... node tests/cover-check-smoke.cjs
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const {spawnSync} = require('node:child_process'), assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const project = fs.mkdtempSync(path.join(os.tmpdir(), 'cover-check-'));
const browser = process.env.BROWSER_PATH || 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
fs.mkdirSync(path.join(project, 'frames'));
fs.writeFileSync(path.join(project, 'project.json'), JSON.stringify({slug:'cover-check', width:1080, height:1440, fps:24, order:[]}));
function html({width=1920, height=1080, font=100, title='看懂<em>增长</em>背后', tag='h1', css='', body='' } = {}) {
  return `<!doctype html><meta charset="utf-8"><style>
    html,body{margin:0;width:${width}px;height:${height}px;background:#f2eddf}
    .title{position:absolute;left:120px;top:200px;margin:0;width:${width-240}px;font:${font}px/1.2 Arial,sans-serif;color:#264b35}
    em{font-style:normal;color:#a51928} ${css}
    </style><${tag} class="title">${title}</${tag}>${body}
    <script>window.__tl={duration:()=>1,pause:()=>{}};</script>`;
}
function check(name, source, key='169', expected=0, shot=false) {
  fs.writeFileSync(path.join(project, 'frames', `cover_${key}.html`), source);
  const run = spawnSync(process.execPath, [path.join(root, 'vendor/html-explainer/scripts/check_cover.mjs'),
    project, '--only', key, '--browser', browser, '--json', ...(shot ? ['--shot'] : [])],
    {encoding:'utf8', timeout:30000});
  assert.equal(run.status, expected, `${name}: ${run.stderr}\n${run.stdout}`);
  const report = JSON.parse(run.stdout)[0];
  assert(report.frozen.frozen, `${name}: must measure completed timeline`);
  console.log(`PASS ${name}: ${report.hook?.sel} ${report.hook?.fontSize}px, ${report.checks.filter(c=>c.level==='fail').length} failures`);
  return report;
}
try {
  const nested = check('nested inline hook and adjacent emphasis do not overlap', html(), '169', 0, true);
  assert.equal(nested.hook.text, '看懂增长背后');
  assert.equal(nested.hook.fontSize, 100);
  const number = check('spaced number is not mistaken for hook', html({tag:'div', body:'<div class="num">123 456 789</div>',
    css:'.num{position:absolute;left:120px;top:500px;font:125px Arial}'}));
  assert.equal(number.hook.sel, '.title');
  const hidden = check('opacity on ancestor excludes hidden text', html({body:'<div style="opacity:0"><div class="ghost">隐藏标题不能抢焦点</div></div>',
    css:'.ghost{position:absolute;left:120px;top:300px;font-size:180px}'}));
  assert.equal(hidden.hook.sel, '.title');
  const overlap = check('real text overlap fails', html({body:'<div class="label">原因标签被标题压住</div>',
    css:'.label{position:absolute;left:140px;top:220px;font:30px Arial}'}), '169', 1);
  assert(overlap.checks.some(c=>c.name==='文字无重叠' && c.level==='fail'));
  const overflow = check('text overflow beyond small container is caught', html({body:'<div class="a">这条说明溢出容器压到别的字</div><div class="b">另一个独立标签</div>',
    css:'.a,.b{position:absolute;top:500px;font:30px Arial;white-space:nowrap}.a{left:120px;width:60px}.b{left:200px}'}), '169', 1);
  assert(overflow.checks.some(c=>c.name==='文字无重叠' && c.level==='fail'));
  const vertical = check('small chart labels are allowed in portrait', html({width:1080,height:1920,font:140,
    body:'<div class="left">基期</div><div class="right">本期</div>',
    css:'.left,.right{position:absolute;top:900px;font:28px Arial}.left{left:120px}.right{right:120px}'}), '916');
  assert(vertical.checks.some(c=>c.name==='9:16 无左右两栏' && c.ok));
  check('explicit short hook is supported', html({title:'增长'}));
  check('true 3:4 geometry', html({width:1080,height:1440,font:120}), '34', 0, true);
  // Check the actual PNG dimensions rather than only the CSS viewport report.
  const png = fs.readFileSync(path.join(project,'out/check_169.png'));
  assert.equal(png.readUInt32BE(16), 1920); assert.equal(png.readUInt32BE(20), 1080);
  const png34 = fs.readFileSync(path.join(project,'out/check_34.png'));
  assert.equal(png34.readUInt32BE(16),1080); assert.equal(png34.readUInt32BE(20),1440);
  const build = spawnSync(process.execPath,[path.join(root,'vendor/html-explainer/scripts/cover_build.mjs'),
    project,'--only','34','--browser',browser],{encoding:'utf8',timeout:30000});
  assert.equal(build.status,0,build.stderr);
  const cover34 = fs.readFileSync(path.join(project,'out/cover_34.png'));
  assert.equal(cover34.readUInt32BE(16),2160); assert.equal(cover34.readUInt32BE(20),2880);
  console.log('PASS cover screenshots physical resolution: 169=1920x1080, 34=1080x1440, built34=2160x2880 (2x); 8 browser fixtures verified');
} finally {
  // Leave artifacts only when explicitly requested for inspection.
  if(process.env.KEEP_COVER_FIXTURES==='1') console.log(`Cover fixtures: ${project}`);
  else fs.rmSync(project,{recursive:true,force:true});
}
