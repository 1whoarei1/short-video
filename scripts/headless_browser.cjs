#!/usr/bin/env node
/** Resolve an optional isolated npm headless runtime. Never changes OS settings.
 * Install: npm install --prefix <runtime-dir> --ignore-scripts @sparticuz/chromium@153.0.0
 * Usage: BROWSER_PATH=$(node scripts/headless_browser.cjs <runtime-dir>) node vendor/html-explainer/scripts/render_video.mjs <project>
 */
const path = require('node:path');
const {createRequire}=require('node:module');
const runtime = process.argv[2] || process.env.HEADLESS_RUNTIME;
if (!runtime) {console.error('Provide a runtime directory containing @sparticuz/chromium@153.0.0');process.exit(2);}
const load=createRequire(path.resolve(runtime,'package.json'));
const moduleValue=load('@sparticuz/chromium');
(moduleValue.default || moduleValue).executablePath().then(p=>process.stdout.write(p+'\n')).catch(e=>{console.error(e.message);process.exit(1)});
