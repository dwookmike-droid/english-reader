// 인쇄용 HTML → PDF. 사용법: node render.js book.html out.pdf
// 판형은 print.css 의 @page 가 정한다 (preferCSSPageSize).
const { chromium } = require('playwright');
const path = require('path');

// 양끝 맞춤에서 줄 끝에 '스페인어+[발음]' 덩어리가 걸리면 그 줄의 낱말 사이가 크게 벌어진다.
// 판면 폭(body data-measure)으로 한 번 짜 보고, 낱말 사이가 data-loose(em) 보다 넓은 줄만
// 줄 끝에 <br>을 넣어 왼쪽 정렬로 둔다(강제 줄바꿈 앞 줄은 text-align-last 를 따른다).
// 줄 나눔 자리는 그대로이므로 다른 줄과 쪽 나눔은 바뀌지 않는다.
function settleLooseLines() {
  const measure = document.body.dataset.measure;
  if (!measure) return 0;
  const limit = parseFloat(document.body.dataset.loose || '0.6');
  document.body.style.width = measure;
  const align = new Map();
  const justified = el => {
    if (!align.has(el)) align.set(el, getComputedStyle(el).textAlign === 'justify');
    return align.get(el);
  };
  const blocks = new Map();
  const walker = document.createTreeWalker(document.querySelector('body'), NodeFilter.SHOW_TEXT);
  for (let t; (t = walker.nextNode());) {
    const el = t.parentElement;
    if (!el.closest('.chapter') || !justified(el)) continue;
    const block = el.closest('.gl, p');
    if (!block) continue;
    if (!blocks.has(block)) blocks.set(block, []);
    blocks.get(block).push(t);
  }
  const range = document.createRange();
  const rectAt = (node, i) => {
    range.setStart(node, i); range.setEnd(node, i + 1);
    const rs = range.getClientRects();
    return rs.length ? rs[0] : null;
  };
  const cuts = [];
  for (const [block, nodes] of blocks) {
    const cs = getComputedStyle(block);
    const em = parseFloat(cs.fontSize);
    const half = parseFloat(cs.lineHeight) / 2 || em * .8;
    const right = block.getBoundingClientRect().right - 1;
    // 낱말 사이(공백)를 줄별로 모은다
    const lines = [];
    for (const node of nodes) {
      const s = node.data;
      for (let i = 0; i < s.length; i++) {
        if (s[i] !== ' ') continue;
        const r = rectAt(node, i);
        if (!r || r.width === 0 || r.right >= right) continue;     // 줄 끝에 걸린 공백은 뺀다
        const y = r.top + r.height / 2;
        let line = lines.find(l => Math.abs(l.y - y) < half);
        if (!line) lines.push(line = { y, max: 0, node, i });
        line.max = Math.max(line.max, r.width);
        line.node = node; line.i = i;                              // 이 줄의 마지막 공백
      }
    }
    lines.sort((a, b) => a.y - b.y);
    const last = block.getClientRects();
    const lastY = last.length ? last[last.length - 1].bottom - half : Infinity;
    for (const line of lines) {
      if (line.max <= limit * em || line.y >= lastY) continue;
      // 마지막 공백 뒤에서 다음 줄의 첫 글자를 찾는다
      let k = nodes.indexOf(line.node), i = line.i + 1, hit = null;
      while (k < nodes.length && !hit) {
        const node = nodes[k];
        for (; i < node.data.length; i++) {
          const r = rectAt(node, i);
          if (r && r.top + r.height / 2 > line.y + half) { hit = [node, i]; break; }
        }
        k++; i = 0;
      }
      if (hit) cuts.push(hit);
    }
  }
  // 뒤에서부터 넣어야 앞의 자리가 흔들리지 않는다
  cuts.sort((a, b) => a[0] === b[0] ? b[1] - a[1]
    : (a[0].compareDocumentPosition(b[0]) & Node.DOCUMENT_POSITION_FOLLOWING ? 1 : -1));
  for (const [node, i] of cuts) {
    const rest = i > 0 ? node.splitText(i) : node;
    rest.parentNode.insertBefore(document.createElement('br'), rest);
  }
  document.body.style.width = '';
  return cuts.length;
}

(async () => {
  const [src, out] = process.argv.slice(2);
  const opts = { args: ['--no-sandbox', '--disable-dev-shm-usage'] };
  if (process.env.CHROME_PATH) opts.executablePath = process.env.CHROME_PATH;
  const browser = await chromium.launch(opts);
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(src), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.emulateMedia({ media: 'print' });
  const loose = await page.evaluate(settleLooseLines);
  await page.pdf({ path: out, preferCSSPageSize: true, printBackground: true, outline: true });
  await browser.close();
  console.log('→ ' + out + (loose ? `  (벌어진 줄 ${loose}곳 왼쪽 정렬)` : ''));
})();
