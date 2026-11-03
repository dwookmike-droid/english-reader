#!/usr/bin/env python3
"""그라시아의 열쇠 — 원고(src/*.txt)와 단어표(src/vocab.tsv)로 두 가지를 만든다.

  1. print/book.html → (render.js) → print/*.pdf   A6 문고판 인쇄용
  2. ../es.html                                     웹 리더 (책의 QR이 가리키는 곳)

원고 표기법
  # 1 | Hola | 올라          장 제목: 번호 | 스페인어 제목 | 한글 발음
  {hola|*올*라}             그 단어가 책에서 처음 나오는 자리. 발음이 붙는다.
                            *굵게* = 강세, _밑줄_ = 혀를 무는 th 소리
  —¿Turismo? :: 관광이에요?  스페인어 대사 :: 작은 글씨로 붙는 우리말 뜻
  ##                        장면 바뀜
  @letter … @end            편지 / @address … @end 봉투의 주소

본문의 다른 라틴 문자 단어는 단어표와 맞춰 자동으로 감싼다. 단어표에 없는
스페인어 단어가 나오면 경고를 낸다 — 쓰고 나서 반드시 단어표를 채울 것.
"""
import html, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'
OUT = ROOT / 'print'
SITE = ROOT.parent
BASE_URL = 'https://dwookmike-droid.github.io/english-reader/es.html'
TITLE_ES, TITLE_KO = 'La llave de Gràcia', '그라시아의 열쇠'

# 읽기 도움(처음 나온 단어의 한글 발음, 대사 밑 우리말 뜻)은 이 장까지만 본문에 싣는다.
# 그 뒤로는 장 끝 단어 목록과 웹 리더에만 발음이 남는다.
AIDS_UNTIL = 15
# 이 장까지는 스페인어 대사 한 줄 전체의 한글 발음을 대사 밑에 붙인다.
LINE_PRON_UNTIL = 6

LATIN = r"A-Za-zÀ-ÖØ-öø-ÿ"
WORD = re.compile(rf"[{LATIN}](?:[{LATIN}\-]*[{LATIN}])?")
SKIP = {'h', 'th', 'k', 'app', 'a', 'o', 's', 'll', 'sh', 'kg', 'g', 'd'}   # 본문 설명에 쓰인 글자 이름          # 본문 설명에 쓰인 글자 이름 등


# ── 단어표 ────────────────────────────────────────────────────────────
def load_vocab():
    entries, forms = {}, {}
    for line in (SRC / 'vocab.tsv').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        c = line.split('\t') + [''] * 7
        key, fs, pron, ko, kind, ch, note = c[:7]
        entries[key] = dict(k=key, p=pron, d=ko, t=kind, c=int(ch or 0), n=note)
        for f in fs.split('|'):
            forms[tuple(f.lower().split())] = key
    return entries, forms


def pron_html(p):
    p = html.escape(p)
    p = re.sub(r'\*(.+?)\*', r'<b>\1</b>', p)
    p = re.sub(r'_(.+?)_', r'<u>\1</u>', p)
    return p


# ── 문단 안의 표기 처리 ─────────────────────────────────────────────────
class Inline:
    def __init__(self, forms, entries):
        self.forms, self.entries = forms, entries
        self.unknown, self.seen, self.uses = set(), set(), {}
        self.shown = set()      # 발음을 이미 보여 준 말
        self.ch = 1
        self.quiet = False      # True면 발음을 붙이지 않고 본 것으로만 친다(대사 전체 발음을 따로 달 때)

    def word(self, text, key, first=False, pron=None):
        """단어를 감싼다. 15장까지는 단어표의 어떤 말이든(스페인어·카탈루냐어·아직 안 가르친 말)
        책에서 처음 나오는 자리에 한 번 발음을 붙인다. 사람 이름에는 붙이지 않는다."""
        self.uses[key] = self.uses.get(key, 0) + 1
        cls = 'w new' if first else 'w'
        s = f'<b class="{cls}" data-k="{html.escape(key)}">{html.escape(text)}</b>'
        e = self.entries.get(key, {})
        p = pron or e.get('p')
        if (p and key not in self.shown and e.get('t') != 'p'
                and self.ch <= AIDS_UNTIL and not self.quiet):
            s += f'<span class="pr">[{pron_html(p)}]</span>'
        self.shown.add(key)
        return s

    def latin_run(self, run):
        """라틴 문자 덩어리 → 단어표 구(句)를 긴 것부터 맞춰 감싼다."""
        toks = list(WORD.finditer(run))
        out, pos, i = [], 0, 0
        while i < len(toks):
            hit = None
            for n in (5, 4, 3, 2, 1):
                if i + n > len(toks):
                    continue
                grp = toks[i:i + n]
                gap_ok = all(run[grp[j].end():grp[j + 1].start()] == ' ' for j in range(n - 1))
                key = self.forms.get(tuple(t.group().lower() for t in grp))
                if key and gap_ok:
                    hit = (n, key)
                    break
            t0 = toks[i]
            out.append(html.escape(run[pos:t0.start()]))
            if hit:
                n, key = hit
                end = toks[i + n - 1].end()
                out.append(self.word(run[t0.start():end], key))
                pos, i = end, i + n
            else:
                w = t0.group()
                if w.lower() not in SKIP:
                    self.unknown.add(w)
                out.append(f'<span class="es">{html.escape(w)}</span>')
                pos, i = t0.end(), i + 1
        out.append(html.escape(run[pos:]))
        return ''.join(out)

    def line_pron(self, text):
        """스페인어 대사 한 줄 → 한글 발음. 카탈루냐어와 이름은 단어표의 발음을, 스페인어는 철자로 만든다."""
        from hangul import to_hangul
        toks = list(WORD.finditer(text))
        out, pos, i = [], 0, 0
        while i < len(toks):
            hit = None
            for n in (5, 4, 3, 2, 1):
                grp = toks[i:i + n]
                if len(grp) < n:
                    continue
                if not all(text[grp[j].end():grp[j + 1].start()] == ' ' for j in range(n - 1)):
                    continue
                key = self.forms.get(tuple(t.group().lower() for t in grp))
                if key and self.entries[key]['t'] in ('c', 'p', 'f'):   # f = 외래 발음(영어, 아르헨티나식 등)
                    hit = (n, self.entries[key]['p'])
                    break
            t0 = toks[i]
            out.append(text[pos:t0.start()])
            if hit:
                n, pr = hit
                out.append(pr)
                pos, i = toks[i + n - 1].end(), i + n
            else:
                out.append(to_hangul(t0.group()))
                pos, i = t0.end(), i + 1
        out.append(text[pos:])
        s = ''.join(out)
        s = re.sub(r'[¿¡«»]', '', s)
        return re.sub(r'\s+', ' ', s).strip()

    def __call__(self, text):
        out, pos = [], 0
        pat = re.compile(rf"\{{([^|}}]+)\|([^}}]+)\}}|[{LATIN}][{LATIN}\- ]*")
        for m in pat.finditer(text):
            out.append(html.escape(text[pos:m.start()]))
            if m.group(1):
                es, pron = m.group(1), m.group(2)
                key = self.forms.get(tuple(es.lower().split()))
                if not key:
                    self.unknown.add(es)
                    key = es.lower()
                if key in self.seen:
                    print(f'  ! 처음 표시가 두 번: {es}', file=sys.stderr)
                self.seen.add(key)
                out.append(self.word(es, key, first=True, pron=pron))
            else:
                run = m.group()
                tail = len(run) - len(run.rstrip(' '))
                out.append(self.latin_run(run.rstrip(' ')) + ' ' * tail)
            pos = m.end()
        out.append(html.escape(text[pos:]))
        return ''.join(out)


# ── 장 원고 읽기 ─────────────────────────────────────────────────────
def parse_chapter(path, inline):
    lines = path.read_text(encoding='utf-8').split('\n')
    head = lines[0].lstrip('# ').split('|')
    ch = dict(n=int(head[0]), es=head[1].strip(), pr=head[2].strip(), blocks=[])
    inline.ch = ch['n']
    aids = ch['n'] <= AIDS_UNTIL
    buf, mode, raw = [], None, []

    def flush():
        if buf:
            ch['blocks'].append(para(' '.join(buf)))
            buf.clear()

    def para(text):
        who = None
        m = re.match(r'@(\w+)\s+(—.*)', text)
        if m:
            who, text = m.groups()
        if text.startswith('—'):
            if not who:
                print(f'  ! 말하는 사람 표시(@이름)가 없는 대사: {text[:30]}', file=sys.stderr)
            es, _, ko = text.partition(' :: ')
            plain = strip_marks(es)
            lp = ''
            if ch['n'] <= LINE_PRON_UNTIL:
                lp = pron_html(inline.line_pron(plain))
                inline.quiet = True
            h = inline(es)
            inline.quiet = False
            return dict(t='say', es=h, lp=lp, ko=html.escape(ko.strip()) if aids else '', plain=plain,
                        who=who, a=audio_id(who, plain))
        return dict(t='p', h=inline(text))

    for line in lines[1:]:
        s = line.strip()
        if mode:
            if s == '@end':
                ch['blocks'].append(dict(t=mode, lines=[inline(x) for x in raw]))
                mode, raw = None, []
            else:
                raw.append(s)
            continue
        if s in ('@letter', '@address'):
            flush(); mode = s[1:]; continue
        if s == '##':
            flush(); ch['blocks'].append(dict(t='br')); continue
        if not s:
            flush(); continue
        buf.append(s)
    flush()
    return ch


def strip_marks(s):
    """소리로 읽을 스페인어만 남긴다: {단어|발음} 표기와 「—그녀가 말했다.—」 같은 우리말 지문을 뺀다."""
    s = re.sub(r'\{([^|}]+)\|[^}]+\}', r'\1', s)
    s = re.sub(r'\s*—[^—]*[가-힣][^—]*—\s*', ' ', s)
    return s.lstrip('—').strip()


# ── 음성 ──────────────────────────────────────────────────────────
# 대사마다 (말하는 사람, 목소리, 문장)으로 이름을 정한다. 셋 중 하나라도 바뀌면 새로 만든다.
AUDIO = SITE / 'audio' / 'es'


def load_voices():
    v = {}
    for line in (SRC / 'voices.tsv').read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.startswith('#'):
            c = line.split('\t')
            v[c[0]] = dict(id=c[0], label=c[1], voice=c[2], style=c[3])
    return v


VOICES = load_voices()


def audio_id(who, text):
    import hashlib
    voice = VOICES.get(who, {}).get('voice', '')
    return hashlib.sha1(f'{who}|{voice}|{text}'.encode()).hexdigest()[:12]


def block_html(b):
    if b['t'] == 'p':
        return f'<p>{b["h"]}</p>'
    if b['t'] == 'say':
        gl = f'<span class="gl">{b["ko"]}</span>' if b['ko'] else ''
        if b.get('lp'):
            gl = f'<span class="lp">[{b["lp"]}]</span>' + gl
        has = (AUDIO / f'{b["a"]}.mp3').exists()
        aud = f' data-a="{b["a"]}"' if has else ''
        return (f'<p class="say" data-say="{html.escape(b["plain"])}"{aud}>'
                f'<span class="sp">{b["es"]}</span>{gl}</p>')
    if b['t'] == 'br':
        return '<p class="br">·&ensp;·&ensp;·</p>'
    if b['t'] in ('letter', 'address'):
        return f'<div class="{b["t"]}">' + ''.join(f'<p>{x}</p>' for x in b['lines']) + '</div>'
    raise ValueError(b)


KEY_SVG = ('<svg viewBox="0 0 120 40" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="2.6" '
           'stroke-linecap="round"><circle cx="17" cy="20" r="11"/><circle cx="17" cy="20" r="4"/>'
           '<path d="M28 20h80M90 20v9M98 20v6M106 20v10"/></g></svg>')


def qr_svg(url):
    import segno
    q = segno.make(url, error='m')
    import io
    buf = io.BytesIO()
    q.save(buf, kind='svg', scale=1, border=0, xmldecl=False, svgns=True, dark='#1d1d1b', nl=False)
    return buf.getvalue().decode()


# ── 인쇄용 HTML ──────────────────────────────────────────────────────
def front_matter():
    return open(SRC / 'front.html', encoding='utf-8').read()


def wordlist_html(ch, entries):
    rows = [e for e in entries.values() if e['t'] == 'n' and e['c'] == ch['n']]
    items = ''.join(
        f'<li><b>{html.escape(e["k"])}</b> <span class="pr">[{pron_html(e["p"])}]</span>'
        f'<span class="m">{html.escape(e["d"])}</span></li>' for e in rows)
    return (f'<section class="words"><h3><span>{ch["n"]}장의 새 단어</span>'
            f'<small>{len(rows)}개</small></h3><ol>{items}</ol></section>')


# 장마다 이름 붙은 쪽: 왼쪽 머리에 책 제목, 오른쪽 머리에 장 제목, 바깥 아래에 쪽번호
HEAD = 'font: italic 7.8pt "EB Garamond"; color: #8a857c; vertical-align: bottom; padding-bottom: 4.5mm;'
FOOT = 'font: 7.8pt "EB Garamond"; color: #6d685f; vertical-align: top; padding-top: 5.5mm;'
PAGE_CSS = (
    '@page c{n}:left {{ margin-left: 10mm; margin-right: 13mm;'
    ' @top-left {{ content: "La llave de Gràcia"; ' + HEAD.replace('{', '{{').replace('}', '}}') + ' }}'
    ' @bottom-left {{ content: counter(page); ' + FOOT + ' }} }}\n'
    '@page c{n}:right {{ margin-left: 13mm; margin-right: 10mm;'
    ' @top-right {{ content: "{run}"; ' + HEAD + ' }}'
    ' @bottom-right {{ content: counter(page); ' + FOOT + ' }} }}\n')


def print_html(chapters, entries, fontdir):
    css = (ROOT / 'print.css').read_text(encoding='utf-8')
    fonts = ''.join(f'<link rel="stylesheet" href="{(fontdir / f).as_uri()}">' for f in (
        'fontsource-gowun-batang-5.1.0/400.css', 'fontsource-gowun-batang-5.1.0/700.css',
        'fontsource-eb-garamond-5.1.0/400.css', 'fontsource-eb-garamond-5.1.0/400-italic.css',
        'fontsource-eb-garamond-5.1.0/600.css', 'fontsource-eb-garamond-5.1.0/600-italic.css', 'fontsource-eb-garamond-5.1.0/500-italic.css',
        'fontsource-noto-sans-kr-5.1.0/400.css', 'fontsource-noto-sans-kr-5.1.0/700.css'))
    body = [front_matter()]
    for ch in chapters:
        url = f'{BASE_URL}#c{ch["n"]}'
        body.append(f'''
<section class="opener" data-n="{ch["n"]}">
  <div class="num">Capítulo {ch["n"]}</div>
  <h2>{html.escape(ch["es"])}</h2>
  <div class="opr">[{pron_html(ch["pr"])}]</div>
  <div class="qr">{qr_svg(url)}<span>이 장을<br>스페인어로<br>듣기</span></div>
</section>
<section class="chapter" style="page: c{ch["n"]}">
{''.join(block_html(b) for b in ch["blocks"])}
</section>
{wordlist_html(ch, entries)}''')
    css += ''.join(PAGE_CSS.format(n=c['n'], run=f"{c['n']} · {c['es']}") for c in chapters)
    return f'''<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>{TITLE_ES} — 인쇄용</title>{fonts}<style>{css}</style></head>
<body>{''.join(body)}</body></html>'''


# ── 웹 리더 ─────────────────────────────────────────────────────────
def chapter_audio(ch):
    f = AUDIO / f'ch{ch["n"]:02d}.mp3'
    if not f.exists():
        return ''
    return (f'<a class="dl ui" href="audio/es/{f.name}" download>'
            f'이 장 음성 파일 받기 (mp3 · {f.stat().st_size // 1024} KB)</a>')


def web_html(chapters, entries):
    tpl = (ROOT / 'reader.html').read_text(encoding='utf-8')
    secs = []
    for ch in chapters:
        secs.append(f'''<section class="ch" id="c{ch["n"]}">
{chapter_audio(ch)}<h2><span class="cn">Capítulo {ch["n"]}</span><span class="ct">{html.escape(ch["es"])}</span>
<span class="cp">[{pron_html(ch["pr"])}]</span></h2>
{''.join(block_html(b) for b in ch["blocks"])}
<p class="end">{KEY_SVG}</p>
{wordlist_html(ch, entries)}
</section>''')
    vocab = {k: dict(p=pron_html(e['p']), d=e['d'], n=e['n'], t=e['t'], c=e['c'])
             for k, e in entries.items()}
    toc = [dict(n=c['n'], es=c['es']) for c in chapters]
    return (tpl.replace('/*VOCAB*/{}', json.dumps(vocab, ensure_ascii=False))
               .replace('/*TOC*/[]', json.dumps(toc, ensure_ascii=False))
               .replace('<!--BOOK-->', '\n'.join(secs)))


def main():
    entries, forms = load_vocab()
    inline = Inline(forms, entries)
    chapters = [parse_chapter(p, inline) for p in sorted(SRC.glob('ch*.txt'))]

    if inline.unknown:
        print('  ! 단어표에 없는 말:', ', '.join(sorted(inline.unknown)), file=sys.stderr)
    # 반복 점검 — 새 단어가 그 장 안에서 몇 번 나왔나
    print('새 단어 등장 횟수 (처음 포함):')
    for e in entries.values():
        if e['t'] == 'n':
            k = e['k']; c = inline.uses.get(k, 0)
            flag = '' if c >= 3 else '  ← 적음'
            print(f'  {k:16s}{c:3d}{flag}')

    (SITE / 'es.html').write_text(web_html(chapters, entries), encoding='utf-8')
    print('→ es.html')
    if '--web-only' in sys.argv:
        return

    fontdir = Path(os.environ.get('FONTS', ROOT / '.fonts'))
    if not fontdir.exists():
        fontdir.mkdir(parents=True)
        subprocess.run(['npm', 'pack', '--silent', '@fontsource/gowun-batang@5.1.0',
                        '@fontsource/eb-garamond@5.1.0', '@fontsource/noto-sans-kr@5.1.0'],
                       cwd=fontdir, check=True)
        for t in fontdir.glob('*.tgz'):
            d = fontdir / t.name[:-4]; d.mkdir()
            subprocess.run(['tar', 'xzf', t.name, '-C', d.name, '--strip-components=1'],
                           cwd=fontdir, check=True)
    OUT.mkdir(exist_ok=True)
    pdf = OUT / 'la-llave-de-gracia_sample.pdf'
    page = print_html(chapters, entries, fontdir)
    # 장 표제지는 언제나 오른쪽(홀수) 쪽에 온다. 크롬은 break-before: right 를 지키지 않으므로
    # 한 번 찍어 보고, 왼쪽에 떨어진 표제지 앞에 빈 쪽을 넣어 다시 찍는다.
    for _ in range(4):
        (OUT / 'book.html').write_text(page, encoding='utf-8')
        subprocess.run(['node', str(ROOT / 'render.js'), str(OUT / 'book.html'), str(pdf)],
                       check=True, stdout=subprocess.DEVNULL)
        txt = subprocess.run(['pdftotext', '-layout', str(pdf), '-'], capture_output=True,
                             text=True, check=True).stdout.split('\f')
        even = [int(m.group(1)) for i, t in enumerate(txt, 1) if i % 2 == 0
                for m in [re.search(r'CAPÍTULO (\d+)', t)] if m]
        if not even:
            break
        n = even[0]
        page = page.replace(f'<section class="opener" data-n="{n}">',
                            f'<section class="pg blank"></section><section class="opener" data-n="{n}">', 1)
    print(f'→ {pdf}')


if __name__ == '__main__':
    main()
