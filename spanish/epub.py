#!/usr/bin/env python3
"""그라시아의 열쇠 — 전자책(EPUB 3). build.py 뒤에 돌린다.

  python3 build.py        # print/cover.pdf 가 있어야 한다(표지 앞면을 잘라 쓴다)
  python3 epub.py         # → print/la-llave-de-gracia.epub

  - 원고와 단어표는 build.py 와 같은 것을 읽는다. 본문 마크업도 block_html() 그대로다.
  - 표지: cover.pdf 의 앞면(재단선 안 128×188mm)을 300dpi JPEG로 잘라 넣는다.
  - QR 대신 장 첫머리에 '이 장을 스페인어로 듣기' 링크(웹 리더)를 둔다.
  - 글꼴: EB Garamond(라틴)만 넣는다. 한글은 읽는 기기의 글꼴을 쓴다.
  - 판권면은 아직 ○○○ 이라 넣지 않는다. 정해지면 front_xhtml()에 더한다.
"""
import datetime, html, re, subprocess, sys, tempfile, uuid, zipfile
from pathlib import Path
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B

OUT = B.OUT / 'la-llave-de-gracia.epub'
LANG = 'ko'
BOOK_ID = 'urn:uuid:' + str(uuid.uuid5(uuid.NAMESPACE_URL, B.BASE_URL))
SVG_NS = 'xmlns="http://www.w3.org/2000/svg"'
GARAMOND = [  # (파일, 굵기, 기울임)
    ('eb-garamond-latin-400-normal.woff2', 400, 'normal'),
    ('eb-garamond-latin-400-italic.woff2', 400, 'italic'),
    ('eb-garamond-latin-600-normal.woff2', 600, 'normal'),
    ('eb-garamond-latin-600-italic.woff2', 600, 'italic'),
]

CSS = """
@charset "utf-8";
""" + ''.join(
    f'@font-face {{ font-family: "EB Garamond"; font-weight: {w}; font-style: {s}; '
    f'src: url("../fonts/{f}") format("woff2"); }}\n' for f, w, s in GARAMOND) + """
body { margin: 0 4%; line-height: 1.75; text-align: justify; word-break: keep-all; }
.w, .es, .t-es, .opener h2, .num, .pron i, .pron td.l, .words li > b, .letter p, .address p {
  font-family: "EB Garamond", serif;
}
.w, .es { font-size: 1.1em; }
.w.new { font-weight: 600; }
.pr { font-family: sans-serif; font-size: .7em; color: #6a655c; margin-left: .25em; white-space: nowrap; }
.pr b, .lp b, .opr b { font-weight: 700; color: #1d1d1b; }
u { text-underline-offset: .18em; }
svg.fl, svg.wfl, svg.orn { display: block; margin: 0 auto; }

/* 본문 */
.chapter p { margin: 0; text-indent: 1em; }
.chapter p.say { text-indent: 0; margin: .5em 0; }
.chapter p.say .sp { display: block; line-height: 1.5; text-align: left; }
.chapter p.say .sp .w, .chapter p.say .sp .es { font-size: 1.18em; }
.chapter p.say .lp { display: block; font-family: sans-serif; font-size: .76em; color: #4f4b45; padding-left: .9em; text-align: left; }
.chapter p.say .gl { display: block; font-size: .8em; color: #77726a; padding-left: .9em; }
.chapter p.dlg { text-indent: 0; margin: .3em 0; }
.chapter p.br { text-indent: 0; text-align: center; color: #b5532f; margin: 1em 0; }
.chapter p.br svg { width: 1.3em; height: 1.3em; }
.chapter p.br + p { text-indent: 0; }
.chapter p.end { text-indent: 0; text-align: center; color: #9a958b; margin-top: 1.6em; }
.chapter p.end svg { width: 4em; height: auto; }
.letter { margin: 1em 0; padding: .6em .9em; background: #f8eeea; border-left: 3px solid #b5532f; }
.letter p { text-indent: 0; text-align: left; font-style: italic; font-size: 1.12em; line-height: 1.55; margin: 0 0 .15em; }
.letter .w, .letter .es { font-style: italic; font-size: 1em; }
.address { margin: 1em auto; padding: 2px; border: 1.5px solid #b5532f; max-width: 90%; }
.address-in { border: 1px solid #b5532f; padding: .45em .8em; text-align: center; }
.address p { text-indent: 0; text-align: center; margin: 0; line-height: 1.4; }
aside.note { margin: 1.2em 0 .6em; padding: .6em .9em; border: 1px solid #b5532f; border-radius: 4px; }
aside.note h4 { margin: 0 0 .3em; font: 700 .72em sans-serif; color: #b5532f; letter-spacing: .12em; }
aside.note p { text-indent: 0; text-align: left; font-family: sans-serif; font-size: .88em; line-height: 1.6; margin: 0 0 .2em; }
aside.note h4 + p { font-weight: 700; }

/* 장 첫머리 */
.opener { text-align: center; margin: 2.5em 0 2em; }
.opener .mark svg { width: 7em; height: 7em; }
.opener .mark.clock svg { width: 9em; height: 9em; }
.opener .num { margin-top: 1.2em; font-size: .78em; letter-spacing: .32em; color: #b5532f; }
.opener h2 { font-weight: 400; font-style: italic; font-size: 2.1em; line-height: 1.1; margin: .3em 0 .2em; }
.opener .opr { font-family: sans-serif; font-size: .75em; color: #77726a; margin: 0; }
.opener .listen { margin-top: 1.2em; font-family: sans-serif; font-size: .8em; }
.opener .listen a { color: #b5532f; }

/* 장 끝 단어 */
.words { margin-top: 2.5em; }
.words .wmark { color: #b5532f; }
.words .wmark svg { width: 8em; height: auto; }
.words h3 { font: 700 .9em sans-serif; border-bottom: 1px solid #b5532f; padding-bottom: .2em; }
.words h3 small { font-weight: 400; color: #77726a; margin-left: .5em; }
.words ol { list-style: none; margin: 0; padding: 0; }
.words li { margin: 0 0 .45em; line-height: 1.3; text-align: left; }
.words li > b { font-weight: 600; }
.words li .m { display: block; font-size: .85em; color: #4f4b45; }

/* 앞붙이 */
.orn .acc { fill: #b5532f; } .orn .ink { fill: #1d1d1b; } .orn .paper { fill: #fff; }
.orn .acc-s { stroke: #b5532f; fill: none; } .orn .ink-s { stroke: #1d1d1b; fill: none; } .orn .paper-s { stroke: #fff; fill: none; }
.title { text-align: center; margin-top: 3em; }
.title .t-mark svg { width: 5em; height: 5em; }
.title .t-es { margin-top: 1em; font-size: 2.4em; line-height: 1.05; font-style: italic; }
.title .t-ko { margin-top: 1em; letter-spacing: .18em; }
.title .t-sub { margin-top: .3em; font-family: sans-serif; font-size: .75em; color: #b5532f; letter-spacing: .14em; }
.pg h3 { font: 700 1em sans-serif; margin: 1.6em 0 .8em; }
.pg { text-align: left; }
.guide li, .pron p, .cast dd { line-height: 1.65; }
.guide li { margin-bottom: .6em; }
.pron table { border-collapse: collapse; width: 100%; }
.pron td { padding: .3em 0; border-bottom: 1px solid #d6d1c6; vertical-align: baseline; text-align: left; }
.pron td.l { width: 6em; font-weight: 600; }
.pron .ex { text-align: center; }
.pron .note { font-size: .85em; color: #77726a; }
.cast dt { font-weight: 700; margin-top: .8em; }
.cast dd { margin: .2em 0 0; color: #3a3833; }
nav ol { list-style: none; padding-left: 0; }
nav ol ol { padding-left: 1.2em; }
nav li { margin: .25em 0; }
nav a { color: inherit; text-decoration: none; }
"""

GUIDE_QR = ('<li>장마다 첫 쪽의 <b>QR코드</b>로 소리를 들으세요. 소리 내어 따라 읽으면 입이 먼저 기억합니다.</li>')
GUIDE_LINK = ('<li>장마다 첫머리의 <b>‘이 장을 스페인어로 듣기’</b>를 누르면 웹 리더에서 소리를 들을 수 있습니다. '
              '소리 내어 따라 읽으면 입이 먼저 기억합니다.</li>')


def xhtml(title, body, epub_ns=False):
    ns = ' xmlns:epub="http://www.idpf.org/2007/ops"' if epub_ns else ''
    return (f'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml"{ns} xml:lang="{LANG}" lang="{LANG}">'
            f'<head><meta charset="utf-8"/><title>{html.escape(title)}</title>'
            f'<link rel="stylesheet" type="text/css" href="../css/book.css"/></head>'
            f'<body>{body}</body></html>')


def to_xml(s):
    """build.py 의 HTML 조각을 XHTML로: 빈 요소 닫기, 인라인 SVG에 이름공간."""
    s = re.sub(r'<svg(?![^>]*xmlns)', f'<svg {SVG_NS}', s)
    s = re.sub(r'<(br|hr|img|meta|link)(\b[^>]*?)(?<!/)>', r'<\1\2/>', s)
    return s.replace('&nbsp;', '&#160;')


def front_xhtml():
    """속표지 + 읽는 법 + 발음 + 사람들. 반표제·빈 쪽·판권·차례(인쇄 쪽수)는 뺀다."""
    s = (B.SRC / 'front.html').read_text(encoding='utf-8')
    secs = {m.group(1): m.group(0) for m in
            re.finditer(r'<section class="pg (\w+)">.*?</section>', s, re.S)}
    pron = re.findall(r'<section class="pg pron">.*?</section>', s, re.S)
    title = secs['title'].replace('<!--TITLE_MARK-->',
        f'<svg class="orn" viewBox="-20 -20 40 40" aria-hidden="true">{B.tile_inner(B.TITLE_TILE)}</svg>')
    title = re.sub(r'\s*<div class="t-pub">.*?</div>', '', title)
    guide = secs['guide']
    assert GUIDE_QR in guide, '읽는 법의 QR 문장이 바뀌었다. epub.py GUIDE_QR 를 맞출 것'
    guide = guide.replace(GUIDE_QR, GUIDE_LINK)
    pron = [re.sub(r'<tr><td>', '<tr><td class="l">', p) for p in pron]
    return {
        'title': xhtml(B.TITLE_KO, to_xml(title)),
        'guide': xhtml('이 책을 읽는 법', to_xml(guide + ''.join(pron))),
        'cast': xhtml('사람들', to_xml(secs['cast'])),
    }


def chapter_xhtml(ch, entries):
    n = ch['n']
    mark = (f'<div class="mark clock">{B.dial_svg()}</div>' if n == 28
            else f'<div class="mark">{B.tile_svg(B.part_of(n))}</div>')
    opener = f'''<section class="opener" id="c{n}">
  {mark}
  <p class="num">CAPÍTULO {n}</p>
  <h2>{html.escape(ch["es"])}</h2>
  <p class="opr">[{B.pron_html(ch["pr"])}]</p>
  <p class="listen"><a href="{B.BASE_URL}#c{n}">이 장을 스페인어로 듣기</a></p>
</section>'''
    body = (opener
            + f'<section class="chapter">{"".join(B.block_html(b) for b in ch["blocks"])}'
            + f'<p class="end">{B.KEY_SVG}</p></section>'
            + B.wordlist_html(ch, entries))
    return xhtml(f'{n}. {ch["es"]}', to_xml(body))


def nav_xhtml(chapters):
    parts = []
    for part in range(1, 6):
        items = ''.join(f'<li><a href="ch{c["n"]:02d}.xhtml">{c["n"]}. {html.escape(c["es"])}</a></li>'
                        for c in chapters if B.part_of(c['n']) == part)
        first = next(c['n'] for c in chapters if B.part_of(c['n']) == part)
        parts.append(f'<li><a href="ch{first:02d}.xhtml">{part}부</a><ol>{items}</ol></li>')
    body = f'''<nav epub:type="toc" id="toc"><h1>차례</h1><ol>
<li><a href="title.xhtml">속표지</a></li>
<li><a href="guide.xhtml">이 책을 읽는 법</a></li>
<li><a href="cast.xhtml">사람들</a></li>
{"".join(parts)}</ol></nav>
<nav epub:type="landmarks" hidden=""><ol>
<li><a epub:type="cover" href="cover.xhtml">표지</a></li>
<li><a epub:type="toc" href="nav.xhtml">차례</a></li>
<li><a epub:type="bodymatter" href="ch01.xhtml">본문</a></li>
</ol></nav>'''
    return xhtml('차례', body, epub_ns=True)


def ncx(chapters, docs):
    pts = ''.join(
        f'<navPoint id="np{i}" playOrder="{i}"><navLabel><text>{html.escape(label)}</text></navLabel>'
        f'<content src="text/{href}"/></navPoint>'
        for i, (href, label) in enumerate(docs, 1))
    return (f'<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
            f'<head><meta name="dtb:uid" content="{BOOK_ID}"/></head>'
            f'<docTitle><text>{B.TITLE_KO}</text></docTitle><navMap>{pts}</navMap></ncx>')


def cover_jpeg(dst):
    """cover.pdf 펼침에서 앞표지(재단선 안)만 잘라 낸다."""
    pdf = B.OUT / 'cover.pdf'
    if not pdf.exists():
        raise SystemExit('print/cover.pdf 가 없습니다. 먼저 python3 build.py')
    info = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True, check=True).stdout
    w_pt = float(re.search(r'Page size:\s+([\d.]+)', info).group(1))
    o = B.BLEED_MM + B.SLUG_MM
    spine = w_pt / B.PT - 2 * o - 2 * B.TRIM_W
    dpi = 300
    px = lambda mm: round(mm / 25.4 * dpi)
    with tempfile.TemporaryDirectory() as td:
        stem = Path(td) / 'c'
        subprocess.run(['pdftoppm', '-r', str(dpi), '-jpeg', '-jpegopt', 'quality=90', '-singlefile',
                        '-x', str(px(o + B.TRIM_W + spine)), '-y', str(px(o)),
                        '-W', str(px(B.TRIM_W)), '-H', str(px(B.TRIM_H)), str(pdf), str(stem)],
                       check=True)
        dst.write_bytes(stem.with_suffix('.jpg').read_bytes())


def main():
    entries, forms = B.load_vocab()
    inline = B.Inline(forms, entries)
    chapters = [B.parse_chapter(p, inline) for p in sorted(B.SRC.glob('ch*.txt'))]
    fontdir = B.ROOT / '.fonts' / 'fontsource-eb-garamond-5.1.0' / 'files'

    files = {}  # OEBPS 안 경로 → bytes/str
    fr = front_xhtml()
    files['text/title.xhtml'] = fr['title']
    files['text/guide.xhtml'] = fr['guide']
    files['text/cast.xhtml'] = fr['cast']
    for ch in chapters:
        files[f'text/ch{ch["n"]:02d}.xhtml'] = chapter_xhtml(ch, entries)
    files['text/nav.xhtml'] = nav_xhtml(chapters)
    files['text/cover.xhtml'] = xhtml(B.TITLE_KO,
        '<div style="text-align:center;margin:0;padding:0">'
        f'<img src="../images/cover.jpg" alt="{B.TITLE_KO} 표지" style="max-width:100%;max-height:100%"/></div>')
    files['css/book.css'] = CSS
    for f, _, _ in GARAMOND:
        files[f'fonts/{f}'] = (fontdir / f).read_bytes()
    with tempfile.TemporaryDirectory() as td:
        c = Path(td) / 'cover.jpg'
        cover_jpeg(c)
        files['images/cover.jpg'] = c.read_bytes()

    docs = [('title.xhtml', '속표지'), ('guide.xhtml', '이 책을 읽는 법'), ('cast.xhtml', '사람들')]
    docs += [(f'ch{c["n"]:02d}.xhtml', f'{c["n"]}. {c["es"]}') for c in chapters]
    files['toc.ncx'] = ncx(chapters, docs)

    # 모든 XHTML이 XML로 읽히는지 먼저 본다.
    for k, v in files.items():
        if k.endswith(('.xhtml', '.ncx')):
            try:
                etree.fromstring(v.encode('utf-8'))
            except etree.XMLSyntaxError as e:
                raise SystemExit(f'{k}: {e}')

    svg_docs = {k for k, v in files.items() if k.endswith('.xhtml') and '<svg' in v}
    media = {'xhtml': 'application/xhtml+xml', 'css': 'text/css', 'woff2': 'font/woff2',
             'jpg': 'image/jpeg', 'ncx': 'application/x-dtbncx+xml'}
    items = []
    for k in files:
        iid = re.sub(r'\W', '_', k)
        props = []
        if k == 'text/nav.xhtml':
            props.append('nav')
        if k == 'images/cover.jpg':
            props.append('cover-image')
        if k in svg_docs:
            props.append('svg')
        p = f' properties="{" ".join(props)}"' if props else ''
        items.append(f'<item id="{iid}" href="{k}" media-type="{media[k.rsplit(".", 1)[1]]}"{p}/>')
    spine = ['text/cover.xhtml', 'text/title.xhtml', 'text/nav.xhtml', 'text/guide.xhtml', 'text/cast.xhtml']
    spine += [f'text/ch{c["n"]:02d}.xhtml' for c in chapters]
    itemrefs = ''.join(
        f'<itemref idref="{re.sub(chr(92) + "W", "_", k)}"{" linear=\"no\"" if k == "text/nav.xhtml" else ""}/>'
        for k in spine)
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    opf = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="{LANG}">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">{BOOK_ID}</dc:identifier>
<dc:title id="t1">{B.TITLE_KO}</dc:title>
<meta refines="#t1" property="title-type">main</meta>
<dc:title id="t2">{B.TITLE_ES}</dc:title>
<meta refines="#t2" property="title-type">subtitle</meta>
<dc:language>{LANG}</dc:language>
<dc:language>es</dc:language>
<dc:description>{html.escape(B.BACK_BLURB)}</dc:description>
<meta property="dcterms:modified">{now}</meta>
<meta name="cover" content="images_cover_jpg"/>
</metadata>
<manifest>
{chr(10).join(items)}
</manifest>
<spine toc="toc_ncx">{itemrefs}</spine>
</package>'''
    etree.fromstring(opf.encode('utf-8'))
    container = ('<?xml version="1.0" encoding="utf-8"?>\n'
                 '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
                 '</rootfiles></container>')

    B.OUT.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUT, 'w') as z:
        z.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        z.writestr('META-INF/container.xml', container, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr('OEBPS/content.opf', opf, compress_type=zipfile.ZIP_DEFLATED)
        for k, v in files.items():
            z.writestr(f'OEBPS/{k}', v, compress_type=zipfile.ZIP_DEFLATED)
    print(f'→ {OUT}  ({len(chapters)}장, {OUT.stat().st_size // 1024}KB)')


if __name__ == '__main__':
    main()
