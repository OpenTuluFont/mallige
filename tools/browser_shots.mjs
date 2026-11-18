// Screenshot the shaping test page in Chromium, Firefox and WebKit (Playwright).
// Usage: NODE_PATH=<dir with playwright> node browser_shots.mjs TEST_HTML OUTDIR
// Each engine ships its own text stack: Chromium and Firefox use HarfBuzz, WebKit on macOS
// uses CoreText, so the WebKit shot is the Safari evidence.
import { createRequire } from "node:module";
import path from "node:path";
import fs from "node:fs";
const require = createRequire(import.meta.url);
const pw = require("playwright");
const [html, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const url = "file://" + path.resolve(html);
for (const name of ["chromium", "firefox", "webkit"]) {
  let browser;
  try { browser = await pw[name].launch(); }
  catch (e) { console.log(`${name}: not available (${e.message.split("\n")[0]})`); continue; }
  const page = await browser.newPage({ viewport: { width: 1100, height: 900 }, deviceScaleFactor: 2 });
  await page.goto(url);
  await page.evaluate(() => document.fonts.ready);
  const ver = await page.evaluate(() => navigator.userAgent);
  const file = path.join(out, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  console.log(`${name}: ${file}  (${ver})`);
  await browser.close();
}
