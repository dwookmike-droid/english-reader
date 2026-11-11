"""HyperFrames 시험: 화면 디자인 시안(mock/)과 1장 제목 카드·편지 장면 영상(ch01/)을 만든다.

  python3 audiobook/video/hf/make.py           # mock/index.html, ch01/index.html, 자산
  cd audiobook/video/hf/mock && ../hf.sh snapshot --at 0.5,1.5,...
  cd audiobook/video/hf/ch01 && ../hf.sh render -o ../out/ch01_hf.mp4

책 디자인(print.css, build.py)을 그대로 따른다.
  색: 테라코타 #b5532f, 짙은 초록 #2f5b4a, 크림 #fbf3e6, 먹 #1d1d1b, 편지 망 #f8eeea
  글꼴: 고운바탕(한국어), EB Garamond(스페인어·제목), Noto Sans KR(발음·보조)
  문양: 1부 타일, 꽃, 꽃 손잡이 열쇠(build.py의 SVG)
읽기만 하는 것: build.py, src/, audiobook/out/, video/render.py.
"""
import html
import json
import math
import random
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HF = Path(__file__).resolve().parent
VIDEO = HF.parent
AB = VIDEO.parent
ES = AB.parent
sys.path.insert(0, str(ES))
sys.path.insert(0, str(VIDEO))
import build as B          # noqa: E402  (읽기만: 발음·새 낱말·문양)
import render as R         # noqa: E402  (읽기만: 시간표 → 쪽 나누기)

FONT_SRC = HF / 'fonts'
FONT_CSS = [
    ('fontsource-gowun-batang-5.1.0', ['400.css', '700.css'], 'Gowun Batang', 'Book Batang'),
    ('fontsource-eb-garamond-5.1.0', ['400.css', '400-italic.css', '500.css', '500-italic.css', '600.css', '600-italic.css'],
     'EB Garamond', 'Book Garamond'),
    ('fontsource-noto-sans-kr-5.1.0', ['400.css', '700.css'], 'Noto Sans KR', 'Book Sans'),
]


# ---------------------------------------------------------------- 자산

def font_faces():
    """fontsource CSS를 assets/fonts 경로로 바꿔 붙인다. 이름은 내장 글꼴과 겹치지 않게 바꾼다."""
    out = []
    for d, files, fam, new in FONT_CSS:
        for f in files:
            css = (FONT_SRC / d / f).read_text()
            css = css.replace(f"'{fam}'", f"'{new}'")
            css = re.sub(r",\s*url\([^)]*\.woff\) format\('woff'\)", '', css)
            css = css.replace('url(./files/', f'url(assets/fonts/{d}/files/')
            out.append(css)
    return '\n'.join(out)


def painted(path, base, blobs, seed, label):
    """수채화 느낌의 임시 그림(1920×1080). 아래 1/3은 비교적 비워 둔다."""
    W, H = 1920, 1080
    rnd = random.Random(seed)
    im = Image.new('RGB', (W, H), base[0])
    g = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        c = tuple(int(base[0][i] * (1 - t) + base[1][i] * t) for i in range(3))
        g.line([(0, y), (W, y)], fill=c)
    for color, n, rmin, rmax, ymax in blobs:
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for _ in range(n):
            x, y = rnd.uniform(-100, W + 100), rnd.uniform(-50, ymax)
            r = rnd.uniform(rmin, rmax)
            d.ellipse([x - r, y - r * rnd.uniform(.6, 1), x + r, y + r * rnd.uniform(.6, 1)],
                      fill=color + (rnd.randint(40, 110),))
        layer = layer.filter(ImageFilter.GaussianBlur(rnd.uniform(18, 40)))
        im = Image.alpha_composite(im.convert('RGBA'), layer).convert('RGB')
    grain = Image.effect_noise((W, H), 28).convert('RGB')
    im = Image.blend(im, grain, 0.05)
    d = ImageDraw.Draw(im)
    f = R.sd(26, 'regular')
    R.text(d, (40, 34), f'임시 그림 · {label}', f, (255, 255, 255))
    im.save(path)


BGS = {
    's01': ([(34, 40, 66), (58, 48, 52)], [((222, 170, 98), 9, 120, 300, 600), ((80, 92, 130), 14, 160, 360, 900),
                                           ((150, 110, 90), 8, 80, 200, 700)], '서울 방, 과자 상자 속 편지와 열쇠'),
    's02': ([(30, 38, 58), (48, 52, 66)], [((210, 170, 110), 12, 40, 120, 500), ((70, 90, 120), 12, 200, 380, 900)],
            '밤 비행기, 승무원이 물과 커피를 권함'),
    's04': ([(226, 206, 170), (196, 168, 132)], [((176, 98, 72), 10, 120, 260, 700), ((104, 136, 160), 8, 140, 300, 500),
                                                 ((120, 128, 82), 8, 80, 180, 800)], '택시 안, 그라시아 골목'),
}


def assets(proj):
    a = proj / 'assets'
    (a / 'img').mkdir(parents=True, exist_ok=True)
    fonts = a / 'fonts'
    if not fonts.exists():
        shutil.copytree(FONT_SRC, fonts)
    for k, (base, blobs, label) in BGS.items():
        p = a / 'img' / f'ch01_{k}.png'
        real = VIDEO / 'img' / f'ch01_{k}.png'
        if real.exists():
            shutil.copy(real, p)
        elif not p.exists():
            painted(p, base, blobs, hash(k) % 1000, label)
    shutil.copy(HF / 'gsap.min.js', a / 'gsap.min.js')
    if (AB / 'out' / 'ch01.m4a').exists():
        shutil.copy(AB / 'out' / 'ch01.m4a', a / 'ch01.m4a')


# ---------------------------------------------------------------- 책 데이터

def book():
    entries, forms = B.load_vocab()
    inline = B.Inline(forms, entries)
    chs = [B.parse_chapter(p, inline) for p in sorted(B.SRC.glob('ch*.txt'))[:3]]
    return chs, entries


def tile():
    return B.tile_svg(1).replace('class="orn"', 'class="orn tile"')


FLOWER = B.flower_svg()
KEY = B.key_svg('#b5532f', 2.2)

CSS = r"""
:root { --acc:#b5532f; --green:#2f5b4a; --cream:#fbf3e6; --ink:#1d1d1b; --soft:#f8eeea; --mute:#6d685f; }
* { margin:0; padding:0; box-sizing:border-box; }
html, body { width:1920px; height:1080px; overflow:hidden; background:#000; }
#root { position:relative; width:100%; height:100%; }
.orn .acc { fill:var(--acc); } .orn .ink { fill:var(--ink); } .orn .paper { fill:var(--cream); }
.orn .acc-s { stroke:var(--acc); fill:none; } .orn .ink-s { stroke:var(--ink); fill:none; } .orn .paper-s { stroke:var(--cream); fill:none; }
.frame { position:absolute; inset:0; overflow:hidden; }
.bg { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }
.es, .w { font-family:'Book Garamond', serif; }
.pr { font-family:'Book Sans', sans-serif; font-size:.62em; color:#6a655c; margin-left:.2em; white-space:nowrap; vertical-align:.12em; }
.pr b { font-weight:700; color:var(--ink); }
u { text-decoration:underline; text-decoration-thickness:.08em; text-underline-offset:.18em; }
.tag { position:absolute; left:40px; top:30px; font:400 22px 'Book Sans'; color:#fff; opacity:.75; }

/* 제목 카드 = 책 표제지 */
.title { position:absolute; inset:0; background:var(--cream); display:flex; flex-direction:column; align-items:center; }
.title .tile { width:250px; height:250px; margin-top:150px; display:block; }
.title .num { margin-top:62px; font:500 30px 'Book Garamond'; letter-spacing:.42em; padding-left:.42em; color:var(--acc); }
.title h1 { margin-top:18px; font:italic 400 170px/1 'Book Garamond'; color:var(--ink); letter-spacing:-.005em; }
.title .opr { margin-top:26px; font:400 32px 'Book Sans'; color:#77726a; }
.title .opr b { color:var(--ink); }
.title .book { position:absolute; bottom:70px; font:400 26px 'Book Batang'; letter-spacing:.3em; color:var(--mute); }

/* 편지 = 책의 편지 상자 */
.letter { position:absolute; left:calc(50% - 590px); top:600px; width:1180px;
  background:rgba(248,238,234,.97); border-left:7px solid var(--acc); padding:34px 56px 38px 52px;
  box-shadow:0 18px 50px rgba(0,0,0,.28); }
.letter .lab { font:700 26px 'Book Sans'; letter-spacing:.16em; color:var(--acc); }
.letter p { margin-top:14px; font:italic 400 66px/1.3 'Book Garamond'; color:var(--ink); }
/* 주소 = 책의 초록 상자 */
.addr { position:absolute; left:0; right:0; margin:0 auto; width:max-content; top:610px; background:var(--green);
  padding:34px 64px; box-shadow:0 18px 50px rgba(0,0,0,.3); }
.addr p { font:400 50px/1.45 'Book Garamond'; color:var(--cream); }

/* A. 책 한 쪽 */
.A .panel { position:absolute; left:0; right:0; bottom:0; height:340px; background:rgba(251,243,230,.95);
  border-top:4px solid var(--acc); padding:44px 190px 0; }
.A .narr { font:400 44px/1.62 'Book Batang'; color:var(--ink); word-break:keep-all; text-wrap:pretty; }
.A .narr .w { font-size:1.16em; } .A .narr .w.new { color:var(--acc); font-weight:500; }
.A .who { font:700 24px 'Book Sans'; letter-spacing:.14em; color:var(--acc); }
.A .say { margin-top:4px; font:400 70px/1.2 'Book Garamond'; color:var(--ink); }
.A .lp { margin-top:6px; font:400 30px 'Book Sans'; color:#4f4b45; } .A .lp b { color:var(--ink); }
.A .gl { margin-top:6px; font:400 32px 'Book Batang'; color:#77726a; }

/* B. 대사 카드 + 낱말 카드(서술 글자는 띄우지 않음) */
.B .chip { position:absolute; right:80px; top:80px; background:var(--cream); padding:22px 34px 24px;
  border-top:5px solid var(--acc); box-shadow:0 14px 40px rgba(0,0,0,.25); }
.B .chip .k { font:500 58px/1 'Book Garamond'; color:var(--acc); }
.B .chip .p { margin-top:10px; font:400 26px 'Book Sans'; color:#6a655c; } .B .chip .p b { color:var(--ink); }
.B .chip .d { margin-top:8px; font:400 32px 'Book Batang'; color:var(--ink); }
.B .chip .lab { font:700 24px 'Book Sans'; letter-spacing:.2em; color:var(--mute); margin-bottom:12px; }
.B .card { position:absolute; left:0; right:0; margin:0 auto; width:max-content; bottom:110px; min-width:900px; text-align:center;
  background:rgba(251,243,230,.96); padding:34px 70px 38px; box-shadow:0 18px 50px rgba(0,0,0,.3); }
.B .card .flw { width:30px; height:30px; color:var(--acc); margin:0 auto 8px; display:block; }
.B .who { font:700 24px 'Book Sans'; letter-spacing:.14em; color:var(--acc); }
.B .say { margin-top:6px; font:italic 400 92px/1.15 'Book Garamond'; color:var(--ink); }
.B .lp { margin-top:8px; font:400 32px 'Book Sans'; color:#4f4b45; } .B .lp b { color:var(--ink); }
.B .gl { margin-top:6px; font:400 34px 'Book Batang'; color:#6d685f; }

/* C. 영화 자막 */
.C .shade { position:absolute; left:0; right:0; bottom:0; height:460px;
  background:linear-gradient(to bottom, rgba(0,0,0,0), rgba(0,0,0,.62)); }
.C .box { position:absolute; left:200px; right:200px; bottom:84px; text-align:center; color:#fff;
  text-shadow:0 2px 6px rgba(0,0,0,.65); }
.C .narr { font:400 46px/1.6 'Book Batang'; word-break:keep-all; text-wrap:balance; }
.C .narr .w { font-size:1.14em; color:#f6b48f; } .C .narr .pr { color:#e8dccb; } .C .narr .pr b { color:#fff; }
.C .who { font:700 24px 'Book Sans'; letter-spacing:.14em; color:#f6b48f; }
.C .say { margin-top:4px; font:400 76px/1.2 'Book Garamond'; }
.C .lp { margin-top:6px; font:400 30px 'Book Sans'; color:#ece3d6; } .C .lp b { color:#fff; }
.C .gl { margin-top:4px; font:400 34px 'Book Batang'; color:#ece3d6; }
"""


def page(cid, dur, body, script='', extra_css=''):
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=1920, height=1080"/>
<script src="assets/gsap.min.js"></script>
<style>
{font_faces()}
{CSS}
{extra_css}
</style>
</head>
<body>
<div id="root" data-composition-id="{cid}" data-start="0" data-duration="{dur}" data-width="1920" data-height="1080">
{body}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{script}
window.__timelines["{cid}"] = tl;
</script>
</body>
</html>
"""


def title_html(ch, id_):
    return f"""<div class="title" id="{id_}">
  {tile()}
  <div class="num">CAPÍTULO {ch['n']}</div>
  <h1>{html.escape(ch['es'])}</h1>
  <div class="opr">[{B.pron_html(ch['pr'])}]</div>
  <div class="book">그라시아의 열쇠</div>
</div>"""


def find_say(ch, plain):
    return next(b for b in ch['blocks'] if b['t'] == 'say' and b['plain'] == plain)


def find_p(ch, start):
    return next(b for b in ch['blocks'] if b['t'] == 'p' and re.sub('<[^>]+>', '', b['h']).startswith(start))


def mock(chs, entries):
    """시안 9장: 공통(제목·편지·주소) + 방향 A·B·C × (서술, 대사)."""
    c1 = chs[0]
    narr = find_p(c1, '첫 번째는')['h']                       # hola[올라] 새 낱말
    nxt = find_p(c1, '이상하게도')['h']
    narr += ' ' + nxt.split('였다.')[0] + '였다.'                # 두 줄짜리 실제 분량
    say = find_say(c1, 'Hola. ¿Adónde?')
    gl = '어디로 갈까요?'
    hola = entries['hola']
    who = '택시 기사'
    lp = say['lp']
    es = html.escape(say['plain'])
    frames = [
        ('공통 · 제목 카드', 's01', title_html(c1, 't')),
        ('공통 · 편지', 's01', '<div class="letter"><div class="lab">마르티의 편지 · 1978</div><p>Querida Sun-rye:</p></div>'),
        ('공통 · 주소', 's01', '<div class="addr"><p>M.<br>Carrer del Rellotger, 7<br>Gràcia · Barcelona</p></div>'),
        ('A 책 한 쪽 · 서술', 's02', f'<div class="A"><div class="panel"><div class="narr">{narr}</div></div></div>'),
        ('A 책 한 쪽 · 대사', 's04', f'<div class="A"><div class="panel"><div class="who">{who}</div>'
                               f'<div class="say">{es}</div><div class="lp">[{lp}]</div><div class="gl">{gl}</div></div></div>'),
        ('B 대사 카드 · 서술', 's02', f'<div class="B"><div class="chip"><div class="lab">새 낱말</div>'
                                f'<div class="k">hola</div><div class="p">[{B.pron_html(hola["p"])}]</div>'
                                f'<div class="d">{html.escape(hola["d"])}</div></div></div>'),
        ('B 대사 카드 · 대사', 's04', f'<div class="B"><div class="card">{FLOWER.replace("class=\"fl\"", "class=\"flw\"")}'
                                f'<div class="who">{who}</div><div class="say">{es}</div>'
                                f'<div class="lp">[{lp}]</div><div class="gl">{gl}</div></div></div>'),
        ('C 영화 자막 · 서술', 's02', f'<div class="C"><div class="shade"></div><div class="box"><div class="narr">{narr}</div></div></div>'),
        ('C 영화 자막 · 대사', 's04', f'<div class="C"><div class="shade"></div><div class="box"><div class="who">{who}</div>'
                                f'<div class="say">{es}</div><div class="lp">[{lp}]</div><div class="gl">{gl}</div></div></div>'),
    ]
    body = []
    for i, (label, bg, inner) in enumerate(frames):
        body.append(f'<div class="frame clip" id="f{i}" data-start="{i}" data-duration="1" data-track-index="0">'
                    f'<img class="bg" src="assets/img/ch01_{bg}.png" alt=""/>{inner}</div>')
    proj = HF / 'mock'
    proj.mkdir(exist_ok=True)
    assets(proj)
    (proj / 'index.html').write_text(page('mock', len(frames), '\n'.join(body)))
    (proj / 'frames.json').write_text(json.dumps([f[0] for f in frames], ensure_ascii=False))
    print(f'mock: {len(frames)}장 → {proj / "index.html"}')


def ch01_test(chs):
    """1장 제목 카드(0–4초) + 편지 대목(시간표 73.8–124.4초). 소리는 ch01.m4a 두 토막.
    서술 글자는 A안(책 한 쪽) 모양으로 띄운다."""
    c1 = chs[0]
    items = json.loads((AB / 'out' / 'ch01.timeline.json').read_text())
    pages = R.make_pages(items)
    T0, T1 = 73.8, 129.0          # 주소 → 서술 → 편지 → 서술 → '그날 밤 나는 비행기표를 샀다'
    TITLE = 4.0
    dur = TITLE + (T1 - T0) + 0.6
    body = [
        f'<audio id="a-title" class="clip" src="assets/ch01.m4a" data-start="0" data-duration="{TITLE}" data-media-start="0" data-fade-out="0.4"></audio>',
        f'<audio id="a-letter" class="clip" src="assets/ch01.m4a" data-start="{TITLE}" data-duration="{T1 - T0 + 0.6:.2f}" data-media-start="{T0}" data-fade-in="0.2" data-fade-out="0.5"></audio>',
        f'<div class="frame clip" id="scene" data-start="0" data-duration="{dur:.2f}" data-track-index="0">'
        f'<img class="bg" id="bgimg" src="assets/img/ch01_s01.png" alt=""/></div>',
        f'<div class="frame clip" id="titlecard" data-start="0" data-duration="{TITLE + 0.01:.2f}" data-track-index="1">'
        f'{title_html(c1, "tc")}</div>',
    ]
    script = [
        # 제목 카드: 타일이 살짝 커지며 나타나고, 글자가 아래에서 올라온다. 마지막 0.7초에 걷힌다.
        'tl.from("#tc .tile", {opacity:0, scale:0.9, rotation:-8, duration:1.0, ease:"power2.out"}, 0.1);',
        'tl.from("#tc .num", {opacity:0, y:16, duration:0.6, ease:"power2.out"}, 0.5);',
        'tl.from("#tc h1", {opacity:0, y:26, duration:0.8, ease:"power2.out"}, 0.7);',
        'tl.from("#tc .opr, #tc .book", {opacity:0, duration:0.6}, 1.2);',
        f'tl.to("#tc", {{opacity:0, duration:0.7, ease:"power1.in"}}, {TITLE - 0.7});',
        # 배경: 천천히 확대(6%)
        f'tl.fromTo("#bgimg", {{scale:1.0}}, {{scale:1.06, duration:{dur:.2f}, ease:"none"}}, 0);',
    ]
    k = 0
    for p in pages:
        if p.start < T0 - 0.01 or p.start >= T1:
            continue
        s = TITLE + p.start - T0
        e = TITLE + min(p.show, T1 + 0.4) - T0
        d = max(0.3, e - s)
        pid = f'p{k}'
        text = html.escape(' '.join(p.lines))
        if p.kind == 'letter':
            inner = (f'<div class="letter" id="{pid}i"><div class="lab">마르티의 편지 · 1978</div>'
                     f'<p>{text}</p></div>')
            script.append(f'tl.from("#{pid}i", {{opacity:0, y:30, duration:0.6, ease:"power2.out"}}, {s:.2f});')
        elif p.kind == 'address':
            parts = [x.strip() for x in p.lines[0].split('. ') if x.strip()] if len(p.lines) == 1 else p.lines
            inner = f'<div class="addr" id="{pid}i"><p>{"<br>".join(html.escape(x if x == "M" else x.rstrip(".")) + ("." if x == "M" else "") for x in parts)}</p></div>'
            script.append(f'tl.from("#{pid}i", {{opacity:0, y:30, duration:0.6, ease:"power2.out"}}, {s:.2f});')
        else:
            t = re.sub(r"([A-Za-zÀ-ÿñÑ][A-Za-zÀ-ÿñÑ'’-]*)", r'<span class="w">\1</span>', text)
            inner = f'<div class="A"><div class="panel"><div class="narr">{t}</div></div></div>'
        body.append(f'<div class="frame clip" id="{pid}" data-start="{s:.2f}" data-duration="{d:.2f}" data-track-index="2">{inner}</div>')
        k += 1
    proj = HF / 'ch01'
    proj.mkdir(exist_ok=True)
    assets(proj)
    (proj / 'index.html').write_text(page('ch01', round(dur, 2), '\n'.join(body), '\n'.join(script)))
    print(f'ch01: {dur:.1f}초, 글자 {k}쪽 → {proj / "index.html"}')


if __name__ == '__main__':
    chs, entries = book()
    mock(chs, entries)
    ch01_test(chs)
