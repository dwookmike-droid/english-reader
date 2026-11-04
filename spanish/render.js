// 인쇄용 HTML → PDF. 사용법: node render.js book.html out.pdf
// 판형은 print.css 의 @page 가 정한다 (preferCSSPageSize).
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const [src, out] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(src), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({ path: out, preferCSSPageSize: true, printBackground: true });
  await browser.close();
  console.log('→ ' + out);
})();
