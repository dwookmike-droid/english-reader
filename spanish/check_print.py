#!/usr/bin/env python3
"""인쇄본 점검 — build.py 뒤에 돌린다. 지시서(design/BRIEF-B.md) 5장 완성 기준 중 기계로 볼 수 있는 것.

  python3 check_print.py

  - 장 표제지가 모두 홀수 쪽인가
  - 차례의 쪽수 30개가 실제 표제지 쪽과 같은가
  - 모든 글꼴이 포함(emb yes)되었는가
  - 인쇄용 PDF의 TrimBox·BleedBox가 맞는가
  - CMYK 변환본에서 본문 쪽이 K 한 판인가 (gs inkcov)
"""
import re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'print'
PT = 72 / 25.4
fail = []


def run(*a):
    return subprocess.run(a, capture_output=True, text=True, check=True).stdout


def ok(cond, msg):
    print(('  ok  ' if cond else '  !!  ') + msg)
    if not cond:
        fail.append(msg)


screen = OUT / 'la-llave-de-gracia_sample.pdf'
pages = run('pdftotext', '-layout', str(screen), '-').split('\f')
openers = {int(m.group(1)): i for i, t in enumerate(pages, 1)
           for m in [re.search(r'CAPÍTULO (\d+)', t)] if m}
print(f'{screen.name}: {len(pages) - 1}쪽')
ok(sorted(openers) == list(range(1, 31)), f'표제지 30개를 찾음 ({len(openers)}개)')
even = {n: i for n, i in openers.items() if i % 2 == 0}
ok(not even, f'표제지가 모두 홀수 쪽 {even or ""}')

toc_page = next(t for t in pages if '차례' in t and '1부' in t)
toc = {int(n): int(p) for n, p in
       re.findall(r'^\s*(?:\d부\s+)?(\d{1,2})\s+\S.*?(\d{1,3})\s*$', toc_page, re.M)}
diff = {n: (toc.get(n), openers.get(n)) for n in range(1, 31) if toc.get(n) != openers.get(n)}
ok(not diff, f'차례 쪽수 30개 = 실제 표제지 쪽 {diff or ""}')

for f in ('la-llave-de-gracia_sample.pdf', 'interior-print.pdf', 'cover.pdf',
          'interior-print-cmyk.pdf', 'cover-cmyk.pdf'):
    p = OUT / f
    if not p.exists():
        ok(f.endswith('-cmyk.pdf'), f'{f} 없음')
        continue
    rows = run('pdffonts', str(p)).splitlines()[2:]
    bad = [r.split()[0] for r in rows if r.split()[-5] != 'yes']
    ok(not bad, f'{f}: 글꼴 {len(rows)}개 모두 포함 {bad or ""}')


def boxes(p, page=1):
    info = run('pdfinfo', '-box', '-f', str(page), '-l', str(page), str(p))
    get = lambda k: [float(v) for v in re.search(rf'{k}:\s+([\d.\s]+)', info).group(1).split()[-4:]]
    return get('TrimBox'), get('BleedBox')


def mm(b):
    return round((b[2] - b[0]) / PT, 2), round((b[3] - b[1]) / PT, 2)


for f in ('interior-print.pdf', 'interior-print-cmyk.pdf'):
    p = OUT / f
    if p.exists():
        t, b = boxes(p)
        ok(mm(t) == (128.0, 188.0) and mm(b) == (134.0, 194.0),
           f'{f}: TrimBox {mm(t)} BleedBox {mm(b)} mm')
for f in ('cover.pdf', 'cover-cmyk.pdf'):
    p = OUT / f
    if p.exists():
        n = int(re.search(r'Pages:\s+(\d+)', run('pdfinfo', str(OUT / 'interior-print.pdf'))).group(1))
        spine = n / 2 * 0.1
        t, b = boxes(p)
        ok(mm(t) == (round(256 + spine, 2), 188.0) and mm(b) == (round(262 + spine, 2), 194.0),
           f'{f}: TrimBox {mm(t)} BleedBox {mm(b)} mm (책등 {spine:.1f}mm)')

# CMYK 변환본: RGB 연산자가 남지 않았고, 무채색이 C=M=Y로 섞인 색(4색 검정·4색 회색)이 없는가.
# 판별로 직접 보려면: gs -o p.tif -sDEVICE=tiffsep -r100 -dFirstPage=12 -dLastPage=12 print/interior-print-cmyk.pdf
from pypdf import PdfReader
from pypdf.generic import ContentStream
for f in ('interior-print-cmyk.pdf', 'cover-cmyk.pdf'):
    p = OUT / f
    if not p.exists():
        continue
    r = PdfReader(p)
    colors, rgb = set(), 0
    for pg in r.pages:
        for operands, op in ContentStream(pg.get_contents(), r).operations:
            if op in (b'rg', b'RG', b'g', b'G', b'sc', b'scn', b'SC', b'SCN'):
                rgb += 1
            elif op in (b'k', b'K'):
                colors.add(tuple(round(float(v), 3) for v in operands))
    rich = sorted(c for c in colors if c[0] > 0 and c[0] == c[1] == c[2] and c != (1, 1, 1, 1))
    k100 = (0, 0, 0, 1) in colors
    ok(not rgb and not rich and (k100 or f.startswith('cover')),
       f'{f}: CMYK 색 {len(colors)}가지, RGB 남음 {rgb}, 4색 무채색 {rich or "없음"}, 먹 K100 {"있음" if k100 else "없음"}')

print('점검 실패: ' + '; '.join(fail) if fail else '모두 통과')
sys.exit(1 if fail else 0)
