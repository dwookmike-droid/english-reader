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
import html, json, math, os, re, subprocess, sys, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'
OUT = ROOT / 'print'
SITE = ROOT.parent
BASE_URL = 'https://dwookmike-droid.github.io/english-reader/es.html'
TITLE_ES, TITLE_KO = 'La llave de Gràcia', '그라시아의 열쇠'

# 판면(mm). 여백은 이 숫자만 고친다. 아래 page_rules()가 모든 @page에 넣는다.
# 손에 쥐는 책이라 안쪽(제본 쪽)을 바깥보다 넓게 둔다.
MARGIN_TOP_MM = 15
MARGIN_BOTTOM_MM = 16
MARGIN_INNER_MM = 16
MARGIN_OUTER_MM = 12
# 종이 한 장 두께. 미색 모조 80g 근처. 책등(mm) = 쪽수 ÷ 2 × 이 값.
PAPER_CALIPER_MM = 0.1

# 장 표제지에 작게 넣는 날짜. STORY.md 「때」표의 날짜만 옮겼다(괄호 안 장면 메모는 빼었다).
DATES = {
    1: '2026년 8월 6일 목요일',
    2: '2026년 8월 7일 금요일',
    3: '2026년 8월 8일 토요일',
    4: '2026년 8월 9일 일요일',
    5: '2026년 8월 10일 월요일',
    6: '2026년 8월 12일 수요일 – 14일 금요일 밤',
    7: '2026년 8월 17일 월요일',
    8: '2026년 8월 19일 수요일',
    9: '2026년 8월 20일 목요일',
    10: '2026년 8월 23일 일요일',
    11: '2026년 8월 29일 토요일',
    12: '2026년 9월 1일 화요일',
    13: '2026년 9월 3일 목요일',
    14: '2026년 9월 5일 토요일',
    15: '2026년 9월 13일 일요일',
    16: '2026년 9월 16일 수요일',
    17: '2026년 9월 20일 일요일',
    18: '2026년 9월 26일 토요일',
    19: '2026년 9월 27일 일요일',
    20: '2026년 10월 3일 토요일',
    21: '2026년 10월 11일 일요일',
    22: '2026년 10월 17일 토요일 밤',
    23: '2026년 10월 18일 일요일 – 22일 목요일',
    24: '2026년 10월 24일 토요일',
    25: '2026년 10월 24일 – 31일 토요일',
    26: '2026년 11월 3일 화요일 – 8일 일요일',
    27: '2026년 11월 9일 월요일 – 10일 화요일',
    28: '2026년 11월 11일 수요일',
    29: '2026년 11월 20일 금요일',
    30: '2027년 8월 14일 토요일 – 15일 일요일',
}

# 읽기 도움(처음 나온 단어의 한글 발음, 대사 밑 우리말 뜻)은 이 장까지만 본문에 싣는다.
# 그 뒤로는 장 끝 단어 목록과 웹 리더에만 발음이 남는다.
AIDS_UNTIL = 15
# 이 장까지는 스페인어 대사 한 줄 전체의 한글 발음을 대사 밑에 붙인다.
LINE_PRON_UNTIL = 6

LATIN = r"A-Za-zÀ-ÖØ-öø-ÿ"
WORD = re.compile(rf"[{LATIN}](?:[{LATIN}\-]*[{LATIN}])?")
SKIP = {'h', 'th', 'k', 'app', 'a', 'o', 's', 'll', 'sh', 'kg', 'g', 'd', 'r', 'ero', 'c', 'emos', 'á', 'án', 'ás', 'é', 'éis', 'ía'}   # 본문 설명에 쓰인 글자 이름          # 본문 설명에 쓰인 글자 이름 등


# ── 단어표 ────────────────────────────────────────────────────────────
def load_vocab():
    entries, forms = {}, {}
    for line in (SRC / 'vocab.tsv').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        c = line.split('\t') + [''] * 7
        key, fs, pron, ko, kind, ch, note = c[:7]
        if not pron and kind not in ('c', 'p', 'f'):
            from hangul import to_hangul           # 스페인어는 발음을 비워 두면 철자에서 만든다
            pron = ' '.join(to_hangul(w) for w in key.split())
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
        p = e.get('p') or pron      # 단어표 발음(비우면 철자에서 자동 생성)을 우선한다
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
        if text.startswith('—') and not who:
            # 3부부터는 소설식 대화(—…—dijo Marc.)를 서술 문단으로 둔다. 음성은 붙지 않는다.
            return dict(t='p', h=inline(text), cls='dlg')
        if text.startswith('—'):
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
        cls = f' class="{b["cls"]}"' if b.get('cls') else ''
        return f'<p{cls}>{b["h"]}</p>'
    if b['t'] == 'say':
        gl = f'<span class="gl">{b["ko"]}</span>' if b['ko'] else ''
        if b.get('lp'):
            gl = f'<span class="lp">[{b["lp"]}]</span>' + gl
        has = (AUDIO / f'{b["a"]}.mp3').exists()
        aud = f' data-a="{b["a"]}"' if has else ''
        return (f'<p class="say" data-say="{html.escape(b["plain"])}"{aud}>'
                f'<span class="sp">{b["es"]}</span>{gl}</p>')
    if b['t'] == 'br':
        return f'<p class="br">{flower_svg()}</p>'
    if b['t'] == 'letter':
        return '<div class="letter">' + ''.join(f'<p>{x}</p>' for x in b['lines']) + '</div>'
    if b['t'] == 'address':
        inner = ''.join(f'<p>{x}</p>' for x in b['lines'])
        return f'<div class="address"><div class="address-in">{inner}</div></div>'
    raise ValueError(b)


# ── 문양 (인라인 SVG. 꽃 하나가 타일·장면 바뀜·열쇠가 된다) ──────────────
def _petals(r):
    """꽃잎 다섯 장. 중심은 (0, 0), 한 잎은 위를 향한다."""
    return ''.join(
        f'<ellipse cx="0" cy="{-r * 0.55:.2f}" rx="{r * 0.32:.2f}" ry="{r * 0.52:.2f}" '
        f'transform="rotate({i * 72})"/>'
        for i in range(5))


def flower_svg():
    """장면 바뀜·단어 쪽에 쓰는 작은 꽃. 색은 currentColor."""
    return ('<svg class="fl" viewBox="-12 -12 24 24" aria-hidden="true">'
            f'<g fill="currentColor">{_petals(10)}</g><circle r="1.6" fill="#fff"/></svg>')


def key_svg(color='currentColor', sw=2.2):
    """손잡이가 꽃인 태엽 열쇠."""
    pet = ''.join(
        f'<ellipse cx="0" cy="-6.3" rx="3.5" ry="5.8" transform="rotate({i * 72})"/>'
        for i in range(5))
    return ('<svg viewBox="0 0 124 42" aria-hidden="true">'
            f'<g fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">'
            f'<g transform="translate(18 21)">{pet}<circle r="2.15"/></g>'
            '<path d="M29 21 H112 M92 21 v8.5 M100 21 v5.5 M108 21 v9"/>'
            '</g></svg>')


KEY_SVG = key_svg()


def part_of(n):
    """1부 1–6, 2부 7–12, 3부 13–18, 4부 19–24, 5부 25–30."""
    return (n - 1) // 6 + 1


# 부마다 타일을 조금씩 바꾼다. 꽃 크기·귀퉁이·곡선이 달라 1도 인쇄에서도 구분된다.
# ground 'frame' = 흰 속 + 테라코타 테 (3부, 색 반전).
TILES = {
    1: dict(ground='acc', flower='paper', dot='ink', corner='ink', curve='paper',
            fr=0.58, cr=0.30, bow=0.38),
    2: dict(ground='acc', flower='paper', dot='ink', corner='ink', curve='paper',
            fr=0.66, cr=0.24, bow=0.50),
    3: dict(ground='frame', flower='acc', dot='paper', corner='ink', curve='acc',
            fr=0.60, cr=0.32, bow=0.34),
    4: dict(ground='acc', flower='ink', dot='paper', corner='paper', curve='ink',
            fr=0.56, cr=0.28, bow=0.46),
    5: dict(ground='acc', flower='paper', dot='acc', corner='paper', curve='paper',
            fr=0.60, cr=0.38, bow=0.36),
}


def _fill(token):
    if token.startswith('#'):
        return f'fill="{token}"'
    return f'class="{token}"'


def _stroke(token, sw):
    if token.startswith('#'):
        return f'fill="none" stroke="{token}" stroke-width="{sw}"'
    return f'class="{token}-s" stroke-width="{sw}"'


def tile_inner(spec, s=20):
    """타일 한 장의 안쪽. 좌표계는 -s…s. 호출하는 SVG의 viewBox가 귀퉁이를 잘라 사분꽃이 된다."""
    if spec['ground'] == 'frame':
        bg = f'<rect x="{-s}" y="{-s}" width="{2*s}" height="{2*s}" {_fill(spec.get("frame", "acc"))}/>'
        inset = s - 1.55
        bg += f'<rect x="{-inset}" y="{-inset}" width="{2*inset}" height="{2*inset}" {_fill(spec.get("field", "paper"))}/>'
    else:
        bg = f'<rect x="{-s}" y="{-s}" width="{2*s}" height="{2*s}" {_fill(spec["ground"])}/>'
    bow = spec['bow']
    curves = ''.join(
        f'<path d="M{-s} {-s} q{s} {s * bow:.2f} {2 * s} 0" {_stroke(spec["curve"], 0.55)} '
        f'transform="rotate({k * 90})"/>'
        for k in range(4))
    corners = ''.join(
        f'<g transform="rotate({k * 90}) translate({-s} {-s})">'
        f'<g {_fill(spec["corner"])}>{_petals(s * spec["cr"])}</g></g>'
        for k in range(4))
    ring = ''
    if spec.get('ring'):
        ring = f'<circle r="{s * spec["fr"] * 1.25:.2f}" {_stroke(spec["ring"], 0.45)}/>'
    center = (f'{ring}<g {_fill(spec["flower"])}>{_petals(s * spec["fr"])}</g>'
              f'<circle r="{s * spec["fr"] * 0.16:.2f}" {_fill(spec["dot"])}/>')
    return bg + curves + corners + center


def tile_svg(part):
    spec = TILES[part]
    return (f'<svg class="orn" viewBox="-20 -20 40 40" aria-hidden="true">{tile_inner(spec)}</svg>')


def dial_svg():
    """28장 표제지. 3시 10분(배가 떠난 시각)에 멈춘 시계판. 먹 눈금, 테라코타 바늘."""
    R, h, m = 40, 3, 10
    parts = [
        f'<circle r="{R}" class="ink-s" stroke-width="0.9"/>',
        f'<circle r="{R - 2.4}" class="ink-s" stroke-width="0.35"/>',
    ]
    for i in range(60):
        a = math.radians(i * 6)
        long = i % 5 == 0
        outer = R - 2.4
        inner = outer - (3.4 if long else 1.55)
        x1, y1 = outer * math.sin(a), -outer * math.cos(a)
        x2, y2 = inner * math.sin(a), -inner * math.cos(a)
        parts.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'class="ink-s" stroke-width="{0.7 if long else 0.32}"/>')
    R2 = R - 11
    for i, label in enumerate('XII I II III IV V VI VII VIII IX X XI'.split()):
        a = math.radians(i * 30)
        x, y = R2 * math.sin(a), -R2 * math.cos(a) + 2.05
        parts.append(
            f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="middle" class="ink" '
            f'font-family="EB Garamond" font-size="5.4">{label}</text>')
    ah = math.radians((h % 12 + m / 60) * 30)
    am = math.radians(m * 6)
    hx, hy = 16 * math.sin(ah), -16 * math.cos(ah)
    mx, my = 26 * math.sin(am), -26 * math.cos(am)
    parts.append(f'<line x1="0" y1="2" x2="{hx:.2f}" y2="{hy:.2f}" class="acc-s" stroke-width="1.55" stroke-linecap="round"/>')
    parts.append(f'<line x1="0" y1="2" x2="{mx:.2f}" y2="{my:.2f}" class="acc-s" stroke-width="0.85" stroke-linecap="round"/>')
    parts.append('<circle r="1.8" class="acc"/>')
    parts.append('<circle r="0.7" class="paper"/>')
    return f'<svg class="orn" viewBox="-46 -46 92 92" aria-hidden="true">{"".join(parts)}</svg>'


def word_mark_svg():
    """단어 쪽 위, 가는 선과 작은 꽃. currentColor라 웹 리더에서도 그대로 보인다."""
    return ('<svg class="wfl" viewBox="0 0 160 22" aria-hidden="true">'
            '<line x1="6" y1="11" x2="64" y2="11" stroke="currentColor" stroke-width="0.7"/>'
            f'<g transform="translate(80 11)" fill="currentColor">{_petals(8)}</g>'
            '<circle cx="80" cy="11" r="1.25" fill="#fff"/>'
            '<line x1="96" y1="11" x2="154" y2="11" stroke="currentColor" stroke-width="0.7"/>'
            '</svg>')


def cover_floor_svg():
    """앞표지. 타일을 가장자리 밖으로 깔아 잘리게 한다. 초록은 표지에만."""
    spec = dict(ground='#b5532f', flower='#fbf3e6', dot='#2f5b4a', corner='#2f5b4a',
                curve='#fbf3e6', fr=0.60, cr=0.32, bow=0.40)
    inner = tile_inner(spec)
    tiles = []
    for x in range(-4, 140, 32):
        for y in range(-4, 200, 32):
            tiles.append(
                f'<svg x="{x}" y="{y}" width="32" height="32" viewBox="-20 -20 40 40">{inner}</svg>')
    return ('<svg class="floor" viewBox="0 0 128 188" preserveAspectRatio="xMidYMid slice">'
            + ''.join(tiles) + '</svg>')


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
    return (f'<section class="words"><div class="wmark" aria-hidden="true">{word_mark_svg()}</div>'
            f'<h3><span>{ch["n"]}장의 새 단어</span>'
            f'<small>{len(rows)}개</small></h3><ol>{items}</ol></section>')


def css_quote(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')


def folio_flower_uri(color):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="-12 -12 24 24">'
           f'<g fill="{color}">{_petals(9)}</g><circle r="1.45" fill="#ffffff"/></svg>')
    return 'data:image/svg+xml,' + urllib.parse.quote(svg, safe='')


def title_class(es):
    n = len(es)
    if n >= 25:
        return 'long'
    if n >= 20:
        return 'mid'
    return ''


def page_rules(chapters, accent, mute):
    """여백의 단일 출처. 안쪽 > 바깥. 쪽 번호는 바깥 아래, 작은 꽃과 함께."""
    top, bot = MARGIN_TOP_MM, MARGIN_BOTTOM_MM
    inn, out = MARGIN_INNER_MM, MARGIN_OUTER_MM
    # 표제지 높이를 본문 상자보다 1mm 낮춰, 반올림으로 다음 쪽으로 넘치지 않게 한다.
    body = 188 - top - bot - 1
    uri = folio_flower_uri(accent)
    head = f'font: italic 7.8pt "EB Garamond"; color: {mute}; vertical-align: bottom; padding-bottom: 3mm;'
    foot_r = (f'content: counter(page) url("{uri}"); '
              f'font: 8pt "EB Garamond"; color: {accent}; vertical-align: top; padding-top: 3.8mm;')
    foot_l = (f'content: url("{uri}") counter(page); '
              f'font: 8pt "EB Garamond"; color: {accent}; vertical-align: top; padding-top: 3.8mm;')
    book = css_quote(TITLE_ES)
    css = (
        f':root {{ --body: {body}mm; }}\n'
        f'@page {{ margin-top: {top}mm; margin-bottom: {bot}mm; }}\n'
        f'@page :left {{ margin-left: {out}mm; margin-right: {inn}mm; }}\n'
        f'@page :right {{ margin-left: {inn}mm; margin-right: {out}mm; }}\n'
        f'@page bare:left {{ margin-left: {out}mm; margin-right: {inn}mm; }}\n'
        f'@page bare:right {{ margin-left: {inn}mm; margin-right: {out}mm; }}\n'
        f'@page words:left {{ margin-left: {out}mm; margin-right: {inn}mm; @bottom-left {{ {foot_l} }} }}\n'
        f'@page words:right {{ margin-left: {inn}mm; margin-right: {out}mm; @bottom-right {{ {foot_r} }} }}\n'
    )
    for c in chapters:
        run = css_quote(f'{c["n"]} · {c["es"]}')
        n = c['n']
        css += (
            f'@page c{n}:left {{ margin-left: {out}mm; margin-right: {inn}mm; '
            f'@top-left {{ content: "{book}"; {head} }} @bottom-left {{ {foot_l} }} }}\n'
            f'@page c{n}:right {{ margin-left: {inn}mm; margin-right: {out}mm; '
            f'@top-right {{ content: "{run}"; {head} }} @bottom-right {{ {foot_r} }} }}\n'
        )
    return css


FONT_FILES = (
    'fontsource-gowun-batang-5.1.0/400.css', 'fontsource-gowun-batang-5.1.0/700.css',
    'fontsource-eb-garamond-5.1.0/400.css', 'fontsource-eb-garamond-5.1.0/400-italic.css',
    'fontsource-eb-garamond-5.1.0/600.css', 'fontsource-eb-garamond-5.1.0/600-italic.css',
    'fontsource-eb-garamond-5.1.0/500-italic.css',
    'fontsource-noto-sans-kr-5.1.0/400.css', 'fontsource-noto-sans-kr-5.1.0/700.css',
)


def font_links(fontdir):
    return ''.join(f'<link rel="stylesheet" href="{(fontdir / f).as_uri()}">' for f in FONT_FILES)


def opener_html(ch):
    n = ch['n']
    part = part_of(n)
    if n == 28:
        mark = f'<div class="mark clock">{dial_svg()}</div>'
    else:
        mark = f'<div class="mark">{tile_svg(part)}</div>'
    cls = title_class(ch['es'])
    hcls = f' class="{cls}"' if cls else ''
    url = f'{BASE_URL}#c{n}'
    return f'''
<section class="opener" data-n="{n}" data-part="{part}">
  {mark}
  <div class="num">CAPÍTULO {n}</div>
  <h2{hcls}>{html.escape(ch["es"])}</h2>
  <div class="opr">[{pron_html(ch["pr"])}]</div>
  <div class="when">{html.escape(DATES[n])}</div>
  <div class="qr">{qr_svg(url)}<span>이 장을<br>스페인어로<br>듣기</span></div>
</section>'''


def print_html(chapters, entries, fontdir, mono=False):
    accent = '#666666' if mono else '#b5532f'
    mute = '#555555' if mono else '#6d685f'
    css = (ROOT / 'print.css').read_text(encoding='utf-8')
    css += page_rules(chapters, accent, mute)
    if mono:
        # 강조색 하나(--accent)를 먹 60% 근처로. 망점도 같이 옅어진다.
        css += '\n:root { --accent: #666666; --soft: #f0f0f0; --mute: #555555; }\n'
    fonts = font_links(fontdir)
    body = [front_matter()]
    for ch in chapters:
        body.append(f'''{opener_html(ch)}
<section class="chapter" style="page: c{ch["n"]}">
{''.join(block_html(b) for b in ch["blocks"])}
</section>
{wordlist_html(ch, entries)}''')
    return f'''<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>{TITLE_ES} — 인쇄용</title>{fonts}<style>{css}</style></head>
<body>{''.join(body)}</body></html>'''


def cover_front_html(fontdir):
    """앞표지만. 책등·뒤표지·재단 여백은 확인 뒤에 만든다."""
    fonts = font_links(fontdir)
    css = '''
@page { size: 128mm 188mm; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
.sheet { position: relative; width: 128mm; height: 188mm; overflow: hidden; background: #b5532f; }
.floor { position: absolute; inset: 0; width: 128mm; height: 188mm; }
.plate {
  position: absolute; left: 15mm; right: 15mm; top: 52mm; height: 82mm;
  background: #fbf3e6; color: #1d1d1b;
  border: .7pt solid #2f5b4a;
  outline: .7pt solid #fbf3e6; outline-offset: 1.5mm;
  text-align: center;
}
.plate .es {
  margin-top: 9mm; font-family: "EB Garamond", serif; font-style: italic; font-weight: 400;
  font-size: 28pt; line-height: 1.02;
}
.plate .ko {
  margin-top: 5mm; font-family: "Gowun Batang", serif; font-size: 11pt;
  letter-spacing: .26em; padding-left: .26em;
}
.plate .sub {
  margin-top: 2mm; font-family: "Noto Sans KR", sans-serif; font-size: 6.7pt;
  letter-spacing: .16em; padding-left: .16em; color: #b5532f;
}
.plate .key { margin-top: 3.6mm; }
.plate .key svg { width: 22mm; height: auto; }
'''
    plate = f'''<div class="plate">
  <div class="es">La llave<br>de Gràcia</div>
  <div class="ko">그라시아의 열쇠</div>
  <div class="sub">스페인어로 읽는 소설</div>
  <div class="key">{key_svg("#2f5b4a", 2.35)}</div>
</div>'''
    return f'''<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>{TITLE_ES} — 앞표지</title>{fonts}<style>{css}</style></head>
<body><div class="sheet">{cover_floor_svg()}{plate}</div></body></html>'''


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

    mono = '--mono' in sys.argv
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
    pdf = OUT / ('la-llave-de-gracia_mono.pdf' if mono else 'la-llave-de-gracia_sample.pdf')
    page = print_html(chapters, entries, fontdir, mono=mono)
    # 장 표제지는 언제나 오른쪽(홀수) 쪽에 온다. 크롬은 break-before: right 를 지키지 않으므로
    # 찍어 보고, 왼쪽에 떨어진 표제지 앞에 빈 쪽을 넣어 다시 찍는다.
    # 빈 쪽 하나가 그 뒤 쪽수를 모두 밀므로, 앞쪽부터 하나씩 맞춘다.
    for _ in range(40):
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
        needle = f'<section class="opener" data-n="{n}"'
        if needle not in page:
            raise SystemExit(f'표제지 마크업을 찾지 못했습니다: {n}장')
        page = page.replace(needle, f'<section class="pg blank"></section>{needle}', 1)
        print(f'  빈 쪽 ← {n}장 앞', file=sys.stderr)
    else:
        raise SystemExit(f'장 표제지가 짝수 쪽에 남았습니다: {even}')
    info = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True, check=True).stdout
    pages = int(re.search(r'Pages:\s+(\d+)', info).group(1))
    spine = pages / 2 * PAPER_CALIPER_MM
    print(f'→ {pdf}  ({pages}쪽, 기준 305, 책등 약 {spine:.1f}mm)')

    if not mono:
        cover_pdf = OUT / 'cover-front.pdf'
        (OUT / 'cover-front.html').write_text(cover_front_html(fontdir), encoding='utf-8')
        subprocess.run(['node', str(ROOT / 'render.js'), str(OUT / 'cover-front.html'), str(cover_pdf)],
                       check=True, stdout=subprocess.DEVNULL)
        print(f'→ {cover_pdf}  (앞면만)')


if __name__ == '__main__':
    main()
