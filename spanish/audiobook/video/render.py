"""「그라시아의 열쇠」 유튜브판: 장 하나를 mp4(1920×1080)로 만든다.

입력(읽기만 함)
  audiobook/out/pilot/final/chNN.m4a            소리(--src로 바꿈)
  audiobook/out/pilot/final/chNN.timeline.json  조각마다 start, end, scene, kind, who, text, gloss
  audiobook/video/img/chNN_sMM.png   장면 그림(없으면 장면 번호를 적은 임시 그림)
  src/chNN.txt 첫 줄                 장 제목("# 1 | Hola | 올라")
출력
  audiobook/video/out/chNN.mp4                    (ffmpeg 필요)
  audiobook/video/out/placeholder/chNN_sMM.png    임시 그림(실제 그림이 없을 때만)
  audiobook/video/out/chNN_check/                 --check: 조각마다 시작 직후 프레임 + 목록

사용
  python3 audiobook/video/render.py 1 2 3              # 장 영상
  python3 audiobook/video/render.py 1 --from 60 --to 120   # 일부만(시험용)
  python3 audiobook/video/render.py 1 --check          # ffmpeg 없이 프레임만 뽑아 싱크·배치 확인
  python3 audiobook/video/render.py 1 --at 12.5 80     # 지정 시각 프레임 PNG
  python3 audiobook/video/render.py 1 --plan           # 글자 쪽(page) 시간표만 출력

화면
  - 장면 그림: 장면 바뀔 때 1초 교차 전환, 장면 내내 천천히 확대(6%).
  - 아래 1/3 반투명 띠에 지금 읽는 조각.
    서술: 2–3줄씩 넘김(문장 단위로 묶고 시간은 글자 수 비율).
    대사: 화자 이름 + 스페인어 + 한국어 뜻풀이(gloss).
    편지: 종이 질감 띠. 주소·간판(address): 가운데 정렬.
  - 장 시작 제목 카드(최소 3초), 장 끝에 소리가 남으면(간주) 다음 장 제목 카드.
"""
import argparse
import functools
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent            # audiobook/video
AB = HERE.parent                                  # audiobook
SRC = AB.parent / 'src'
# 소리·시간표 폴더. 파일럿은 audiobook/out/pilot/final(시작 테마·간주 포함, 2026-11-10 오디오북 세션 지정).
# 다른 판은 --src 또는 환경 변수 AUDIOBOOK_SRC로. (병렬 작업자도 같은 값을 쓰도록 환경 변수로 넘긴다.)
AUDIO = Path(os.environ.get('AUDIOBOOK_SRC') or AB / 'out' / 'pilot' / 'final')


def set_src(path):
    global AUDIO
    AUDIO = Path(path).resolve()
    os.environ['AUDIOBOOK_SRC'] = str(AUDIO)
IMG = HERE / 'img'
OUT = HERE / 'out'
SCENES = HERE / 'scenes.tsv'

W, H = 1920, 1080
BAND_Y = 720                  # 아래 1/3
BAND_FADE = 70                # 띠 위쪽 그러데이션 높이
BAND_RGB = (16, 12, 8)        # 일반 띠 색
BAND_A = 245                  # 일반 띠 불투명도(BAND_Y 아래). 그림 아래쪽 빈 띠를 가린다
MARGIN = 170                  # 글자 좌우 여백
TEXT_W = W - 2 * MARGIN
FPS = 24
XFADE = 1.0                   # 장면 전환
ZOOM = 0.06                   # 장면 하나 동안 확대 비율
TITLE_MIN = 3.0               # 제목 카드 최소 길이
HOLD = 1.2                    # 다음 조각까지 이보다 짧게 비면 앞 글자를 그대로 둔다
TAIL = 0.4                    # 길게 비면 끝난 뒤 이만큼 더 보여 주고 지운다
NARR_LINES = 3
MIN_SHOW = 0.8             # 아무리 짧은 조각도 이만큼은 보인다(다음 쪽 표시를 늦춤)

SD = '/System/Library/Fonts/AppleSDGothicNeo.ttc'          # 0 Regular 2 Medium 4 SemiBold 6 Bold 8 Light
MYUNGJO = '/System/Library/Fonts/Supplemental/AppleMyungjo.ttf'
GEORGIA_I = '/System/Library/Fonts/Supplemental/Georgia Italic.ttf'
GEORGIA_BI = '/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf'


AVENIR = '/System/Library/Fonts/Avenir Next.ttc'                # 0 Bold 2 DemiBold 5 Medium 7 Regular


@functools.lru_cache(None)
def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


def is_latin(c):
    return ord(c) < 0x250 and c != ' '


class Mix:
    """한글 글꼴 + 라틴 글꼴. Apple SD Gothic Neo에는 á é í ó ú ñ ¿ ¡ 같은 글자가 없어서
    라틴 문자(U+0000–024F)는 라틴 글꼴로 그린다. 기준선은 한글 글꼴에 맞춘다."""

    def __init__(self, cjk, latin):
        self.cjk, self.latin, self.size = cjk, latin, cjk.size

    def runs(self, s):
        out = []
        for c in s:
            f = self.latin if is_latin(c) else (out[-1][0] if c == ' ' and out else self.cjk)
            if out and out[-1][0] is f:
                out[-1][1] += c
            else:
                out.append([f, c])
        return out

    def getlength(self, s):
        return sum(f.getlength(t) for f, t in self.runs(s))


def sd(size, weight='medium'):
    return Mix(font(SD, size, {'regular': 0, 'medium': 2, 'semibold': 4, 'bold': 6, 'light': 8}[weight]),
               font(AVENIR, size, {'regular': 7, 'medium': 5, 'semibold': 2, 'bold': 0, 'light': 7}[weight]))


def text(d, xy, s, f, fill, anchor='la'):
    """d.text와 같되 Mix 글꼴이면 글꼴을 바꿔 가며 그린다. anchor: 가로 l/m + 세로 a/m."""
    if not isinstance(f, Mix):
        d.text(xy, s, font=f, fill=fill, anchor=anchor)
        return
    x, y = xy
    asc, desc = f.cjk.getmetrics()
    if anchor[0] == 'm':
        x -= f.getlength(s) / 2
    base = y + asc if anchor[1] == 'a' else y + (asc - desc) / 2
    for g, t in f.runs(s):
        d.text((x, base), t, font=g, fill=fill, anchor='ls')
        x += g.getlength(t)


HANGUL = re.compile('[가-힣]')

# 화면에 쓰는 화자 이름(책 본문 표기). 없는 이름은 영문 그대로.
NAMES = {
    'yunha': '윤하', 'montse': '몬세', 'vale': '발레', 'marc': '마르크', 'joan': '조안',
    'marti': '마르티', 'madre': '엄마', 'mama': '엄마', 'quique': '키케', 'sofia': '소피아',
    'luca': '루카', 'pau': '파우', 'jaume': '자우메',
    'taxista': '택시 기사', 'azafata': '승무원', 'policia': '경찰', 'policia_mossos': '경찰',
    'hombre': '남자', 'mujer': '여자', 'frutera': '과일 가게 주인', 'senyora': '아주머니',
    'archivera': '기록 보관소 직원', 'vecinos': '이웃들', 'carnicero': '정육점 주인',
    'bibliotecario': '사서', 'narrador': '해설', 'vendedor': '상인', 'taquillera': '매표소 직원',
    'castanyera': '군밤 장수', 'todos': '모두', 'chica': '아가씨', 'megafonia': '안내 방송',
}
NAME_COLOR = {
    'yunha': (150, 196, 230), 'montse': (236, 150, 118), 'vale': (238, 200, 100),
    'marc': (160, 200, 150), 'joan': (200, 170, 220), 'marti': (220, 190, 150),
    'madre': (230, 170, 190), 'mama': (230, 170, 190),
}
NAME_OTHER = (205, 196, 180)
WHITE = (250, 247, 240)
GLOSS = (214, 205, 188)
INK = (64, 44, 28)
ADDR = (240, 220, 165)

PLACE_COLORS = [(176, 98, 72), (104, 136, 160), (196, 154, 82), (120, 128, 82),
                (170, 120, 120), (96, 110, 120), (80, 128, 124), (150, 130, 100)]


# ---------------------------------------------------------------- 입력

def chapter_title(ch):
    """src/chNN.txt 첫 줄 '# 1 | Hola | 올라' → ('1', 'Hola', '올라')."""
    p = SRC / f'ch{ch:02d}.txt'
    if not p.exists():
        return None
    first = p.read_text().split('\n', 1)[0]
    n, es, ko = [x.strip() for x in first[2:].split('|')]
    return n, es, ko


def load_scenes():
    """scenes.tsv → {(ch, scene): ko 설명}."""
    out = {}
    for line in SCENES.read_text().splitlines()[1:]:
        c = line.split('\t')
        if len(c) >= 5:
            out[(int(c[0]), int(c[1]))] = c[4]
    return out


def audio_duration(path):
    """m4a 길이(초). ffprobe가 고장이면 macOS afinfo로."""
    for cmd in (['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                ['afinfo', str(path)]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        if r.returncode:
            continue
        if cmd[0] == 'ffprobe':
            return float(r.stdout.strip())
        m = re.search(r'estimated duration: ([\d.]+)', r.stdout)
        if m:
            return float(m.group(1))
    raise SystemExit(f'소리 길이를 못 읽었습니다: {path}')


# ---------------------------------------------------------------- 글자 배치

def wrap(text, f, width):
    """낱말(띄어쓰기) 단위로 줄바꿈. 한 낱말이 너무 길면 글자 단위로 자른다."""
    lines, cur = [], ''
    for word in text.split():
        cand = f'{cur} {word}' if cur else word
        if f.getlength(cand) <= width:
            cur = cand
            continue
        if cur:
            lines.append(cur)
        cur = ''
        while f.getlength(word) > width:
            k = len(word)
            while k > 1 and f.getlength(word[:k]) > width:
                k -= 1
            lines.append(word[:k])
            word = word[k:]
        cur = word
    if cur:
        lines.append(cur)
    return lines


SENT = re.compile(r'(?<=[.!?…”"’»])\s+')


def sentences(text):
    return [s for s in SENT.split(text.strip()) if s]


def pack(text, f, width, maxlines):
    """문장 단위로 maxlines 줄까지 한 쪽에 묶는다. 문장 하나가 넘치면 줄 단위로 자른다."""
    pages, cur = [], []
    for s in sentences(text):
        cand = wrap(' '.join(cur + [s]), f, width)
        if len(cand) <= maxlines:
            cur.append(s)
            continue
        if cur:
            pages.append(wrap(' '.join(cur), f, width))
            cur = []
        lines = wrap(s, f, width)
        if len(lines) <= maxlines:
            cur = [s]
        else:
            chunks = [lines[i:i + maxlines] for i in range(0, len(lines), maxlines)]
            if len(chunks[-1]) == 1 and len(chunks) > 1 and maxlines > 2:   # 한 줄만 남는 쪽 피하기
                chunks[-1].insert(0, chunks[-2].pop())
            pages.extend(chunks[:-1])
            cur = [' '.join(chunks[-1])]
    if cur:
        pages.append(wrap(' '.join(cur), f, width))
    return pages


def weight(lines):
    return max(1, sum(len(l.replace(' ', '')) for l in lines))


class Page:
    __slots__ = ('start', 'end', 'show', 'kind', 'who', 'lines', 'gloss', 'scene', 'idx')

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


NARR_FONT = lambda: sd(46, 'medium')
SAY_FONT = lambda: sd(56, 'bold')
GLOSS_FONT = lambda: sd(36, 'regular')
NAME_FONT = lambda: sd(32, 'semibold')


def letter_font(t):
    return Mix(font(MYUNGJO, 46), font(GEORGIA_I, 46)) if HANGUL.search(t) else font(GEORGIA_I, 50)


def addr_font():
    return font(GEORGIA_BI, 58)


def make_pages(items):
    """시간표 조각 → 화면 한 쪽씩(Page). 제목(title) 조각은 카드로 따로 그린다."""
    pages = []
    for it in items:
        k = it['kind']
        if k == 'title':
            continue
        text, gloss = it['text'].strip(), (it.get('gloss') or '').strip()
        if k == 'narr':
            chunks = pack(text, NARR_FONT(), TEXT_W, NARR_LINES)
        elif k == 'say':
            chunks = pack(text, SAY_FONT(), TEXT_W, 2)
        elif k == 'letter':
            chunks = pack(text, letter_font(text), TEXT_W - 80, 3)
        else:   # address
            chunks = pack(text, addr_font(), TEXT_W, 2)
        total = sum(weight(c) for c in chunks)
        t = it['start']
        span = it['end'] - it['start']
        for c in chunks:
            d = span * weight(c) / total
            pages.append(Page(start=t, end=t + d, kind=k, who=it.get('who'), lines=c,
                              gloss=gloss, scene=it['scene']))
            t += d
    for a, b in zip(pages, pages[1:]):               # 0.03초짜리 조각 같은 것도 읽히게
        if b.start - a.start < MIN_SHOW:
            b.start = min(a.start + MIN_SHOW, max(b.start, b.end - 0.3))
    for i, p in enumerate(pages):
        p.idx = i
        nxt = pages[i + 1].start if i + 1 < len(pages) else math.inf
        p.show = nxt if nxt - p.end < HOLD else p.end + TAIL
    return pages


# ---------------------------------------------------------------- 그림

def placeholder(ch, scene, label):
    """장면 번호와 장면 설명을 적은 단색 임시 그림(아래 1/3은 비움)."""
    path = OUT / 'placeholder' / f'ch{ch:02d}_s{scene:02d}.png'
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    base = PLACE_COLORS[(ch * 3 + scene) % len(PLACE_COLORS)]
    im = Image.new('RGB', (W, H), base)
    d = ImageDraw.Draw(im)
    for y in range(H):                                     # 위가 밝은 그러데이션
        k = 1.12 - 0.3 * y / H
        d.line([(0, y), (W, y)], fill=tuple(min(255, int(c * k)) for c in base))
    rnd = random.Random(ch * 1000 + scene)                 # 확대가 보이도록 점 몇 개
    for _ in range(120):
        x, y, r = rnd.randrange(W), rnd.randrange(int(H * 0.66)), rnd.randrange(3, 14)
        d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(min(255, c + 30) for c in base))
    text(d, (W // 2, 300), f'{ch}장 · 장면 {scene}', sd(120, 'bold'), WHITE, 'mm')
    for i, line in enumerate(wrap(label, sd(48, 'medium'), 1400)[:2]):
        text(d, (W // 2, 430 + i * 66), line, sd(48, 'medium'), WHITE, 'mm')
    text(d, (W // 2, 590), '임시 그림', sd(34, 'regular'), (235, 230, 220), 'mm')
    im.save(path)
    return path


def scene_image(ch, scene, labels):
    p = IMG / f'ch{ch:02d}_s{scene:02d}.png'
    if p.exists():
        return p, False
    return placeholder(ch, scene, labels.get((ch, scene), '')), True


def cover(im, w, h):
    """가운데를 기준으로 w:h 비율로 잘라 w×h로 맞춘다."""
    im = im.convert('RGB')
    r = w / h
    if im.width / im.height > r:
        nw = int(im.height * r)
        im = im.crop(((im.width - nw) // 2, 0, (im.width - nw) // 2 + nw, im.height))
    else:
        nh = int(im.width / r)
        im = im.crop((0, (im.height - nh) // 2, im.width, (im.height - nh) // 2 + nh))
    return im.resize((w, h), Image.LANCZOS)


# ---------------------------------------------------------------- 띠와 글자 그리기

def band_base(paper=False):
    """아래 1/3 띠(RGBA, 높이 H-BAND_Y+BAND_FADE)."""
    bh = H - BAND_Y + BAND_FADE
    if paper:
        im = Image.new('RGBA', (W, bh), (0, 0, 0, 0))
        paper_rgb = Image.new('RGB', (W - 160, bh - BAND_FADE - 30), (238, 226, 198))
        noise = Image.effect_noise(paper_rgb.size, 22).convert('RGB')      # 종이 결
        paper_rgb = Image.blend(paper_rgb, noise, 0.08)
        mask = Image.new('L', paper_rgb.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, paper_rgb.width - 1, paper_rgb.height - 1], 18, fill=242)
        mask = mask.filter(ImageFilter.GaussianBlur(2))
        shadow = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            [86, BAND_FADE + 14, 80 + paper_rgb.width + 6, BAND_FADE + 14 + paper_rgb.height + 6], 18, fill=(0, 0, 0, 110))
        im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
        layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
        layer.paste(paper_rgb.convert('RGBA'), (80, BAND_FADE + 10), mask)
        im.alpha_composite(layer)
        return im
    im = Image.new('RGBA', (W, bh), BAND_RGB + (0,))
    alpha = []
    for y in range(bh):
        a = BAND_A * min(1.0, y / BAND_FADE) ** 1.6
        alpha.append(int(a))
    a_img = Image.new('L', (1, bh))
    a_img.putdata(alpha)
    im.putalpha(a_img.resize((W, bh)))
    return im


@functools.lru_cache(4)
def band(paper=False):
    return band_base(paper)


def draw_lines(d, lines, f, color, y, align='center', spacing=1.5, shadow=True):
    lh = int(f.size * spacing)
    for i, line in enumerate(lines):
        x = W // 2 if align == 'center' else MARGIN
        anchor = 'ma' if align == 'center' else 'la'
        if shadow:
            text(d, (x + 2, y + i * lh + 2), line, f, (0, 0, 0, 150), anchor)
        text(d, (x, y + i * lh), line, f, color, anchor)
    return y + len(lines) * lh


def block_height(parts):
    return sum(int(f.size * sp) * n + gap for f, sp, n, gap in parts)


def render_page(p):
    """Page → 띠+글자 RGBA (W × 띠 높이). 띠 안쪽 위치 0 = 화면 y BAND_Y-BAND_FADE."""
    im = band(p.kind == 'letter').copy()
    d = ImageDraw.Draw(im)
    top, bottom = BAND_FADE + 24, im.height - 30          # 글자가 들어갈 세로 범위(띠 기준)
    if p.kind == 'narr':
        f = NARR_FONT()
        hgt = block_height([(f, 1.5, len(p.lines), 0)])
        draw_lines(d, p.lines, f, WHITE, top + (bottom - top - hgt) // 2)
    elif p.kind == 'say':
        fn, fs, fg = NAME_FONT(), SAY_FONT(), GLOSS_FONT()
        gl = wrap(p.gloss, fg, TEXT_W)[:2] if p.gloss else []
        parts = [(fn, 1.45, 1, 4), (fs, 1.3, len(p.lines), 10 if gl else 0)] + ([(fg, 1.45, len(gl), 0)] if gl else [])
        y = top + (bottom - top - block_height(parts)) // 2
        name = NAMES.get(p.who, (p.who or '').capitalize())
        y = draw_lines(d, [name], fn, NAME_COLOR.get(p.who, NAME_OTHER), y, spacing=1.45) + 4
        y = draw_lines(d, p.lines, fs, WHITE, y, spacing=1.3) + 10
        if gl:
            draw_lines(d, gl, fg, GLOSS, y, spacing=1.45)
    elif p.kind == 'letter':
        f = letter_font(' '.join(p.lines))
        fg = GLOSS_FONT()
        gl = wrap(p.gloss, fg, TEXT_W - 80)[:2] if p.gloss else []
        label = None if p.who in (None, 'narr') else f'{NAMES.get(p.who, p.who)}의 편지'
        parts = ([(sd(28, 'semibold'), 1.5, 1, 0)] if label else []) + [(f, 1.5, len(p.lines), 0)] + \
                ([(fg, 1.4, len(gl), 6)] if gl else [])
        y = top + 4 + (bottom - top - block_height(parts)) // 2
        if label:
            y = draw_lines(d, [label], sd(28, 'semibold'), (140, 100, 70), y, shadow=False)
        y = draw_lines(d, p.lines, f, INK, y, shadow=False)
        if gl:
            draw_lines(d, gl, fg, (110, 90, 70), y + 6, spacing=1.4, shadow=False)
    else:   # address: 적힌 글(주소·간판)
        f, fg = addr_font(), GLOSS_FONT()
        gl = wrap(p.gloss, fg, TEXT_W)[:2] if p.gloss else []
        parts = [(f, 1.35, len(p.lines), 0)] + ([(fg, 1.45, len(gl), 12)] if gl else [])
        y0 = top + (bottom - top - block_height(parts)) // 2
        y = draw_lines(d, p.lines, f, ADDR, y0, spacing=1.35)
        wmax = max(f.getlength(l) for l in p.lines)
        ym = y0 + int(f.size * 0.62)
        for sgn in (-1, 1):                                       # 양옆 가는 줄
            x0 = W // 2 + sgn * (wmax / 2 + 40)
            d.line([(x0, ym), (x0 + sgn * 120, ym)], fill=ADDR + (200,), width=2)
        if gl:
            draw_lines(d, gl, fg, GLOSS, y + 12, spacing=1.45)
    return im


def render_title(n, es, ko, small_top='그라시아의 열쇠', lead=None):
    """전체 화면 제목 카드(RGBA). 글자 묶음은 띠 위 영역(0 ~ BAND_Y-BAND_FADE)의 세로 가운데."""
    im = Image.new('RGBA', (W, H), (14, 10, 6, 150))
    d = ImageDraw.Draw(im)
    # 기준 배치(묶음 안 상대 위치)는 예전과 같고, 묶음 전체를 dy만큼 옮긴다
    top = 300 - 20 if small_top else (420 - 20 if lead else 470 - 32)
    bottom = 710 + 24 if ko else 590 + 60
    dy = round((BAND_Y - BAND_FADE) / 2 - (top + bottom) / 2)
    if small_top:   # 끝 카드(다음 장)에는 책 이름을 쓰지 않는다
        text(d, (W // 2, 300 + dy), small_top, sd(40, 'medium'), (230, 220, 200), 'mm')
        d.line([(W // 2 - 60, 345 + dy), (W // 2 + 60, 345 + dy)], fill=(230, 220, 200), width=2)
    if lead:
        text(d, (W // 2, 420 + dy), lead, sd(40, 'regular'), (225, 215, 195), 'mm')
    text(d, (W // 2, 470 + dy), f'{n}장', sd(64, 'semibold'), WHITE, 'mm')
    text(d, (W // 2, 590 + dy), es, font(GEORGIA_BI, 120), WHITE, 'mm')
    if ko:
        text(d, (W // 2, 710 + dy), ko, sd(48, 'regular'), (235, 225, 205), 'mm')
    return im


def render_end():
    im = Image.new('RGBA', (W, H), (14, 10, 6, 160))
    d = ImageDraw.Draw(im)
    text(d, (W // 2, 500), '그라시아의 열쇠', sd(72, 'semibold'), WHITE, 'mm')
    text(d, (W // 2, 610), '끝', sd(52, 'regular'), (235, 225, 205), 'mm')
    return im


# ---------------------------------------------------------------- 장 하나

class Chapter:
    def __init__(self, ch):
        self.ch = ch
        tl = AUDIO / f'ch{ch:02d}.timeline.json'
        self.audio = AUDIO / f'ch{ch:02d}.m4a'
        if not tl.exists() or not self.audio.exists():
            raise SystemExit(f'{ch}장: 시간표나 소리가 없습니다 ({tl.name}, {self.audio.name})')
        self.items = json.loads(tl.read_text())
        self.duration = audio_duration(self.audio)
        self.pages = make_pages(self.items)
        self.page_starts = [p.start for p in self.pages]
        labels = load_scenes()
        # 장면 시작 시각
        first = {}
        for it in self.items:
            first.setdefault(it['scene'], it['start'])
        self.scenes = sorted(first)
        self.scene_start = {s: (0.0 if i == 0 else first[s]) for i, s in enumerate(self.scenes)}
        self.scene_end = {s: (self.scene_start[self.scenes[i + 1]] if i + 1 < len(self.scenes) else self.duration)
                          for i, s in enumerate(self.scenes)}
        self.images, self.placeholders = {}, []
        for s in self.scenes:
            p, ph = scene_image(ch, s, labels)
            self.images[s] = p
            if ph:
                self.placeholders.append(s)
        t = chapter_title(ch)
        title_item = next((x for x in self.items if x['kind'] == 'title'), None)
        self.title = t or (str(ch), title_item['text'] if title_item else '', '')
        self.title_end = max(TITLE_MIN, title_item['end'] + 0.3 if title_item else 0)
        last_end = max(x['end'] for x in self.items)
        self.outro = last_end + 1.0 if self.duration - last_end > 4.0 else None   # 간주가 있으면
        self.next_title = chapter_title(ch + 1)

    # -- 배경
    @functools.lru_cache(3)
    def base(self, scene):
        im = Image.open(self.images[scene])
        return cover(im, int(W * (1 + ZOOM)), int(H * (1 + ZOOM)))

    def bg_at(self, scene, t):
        s0, s1 = self.scene_start[scene] - XFADE, self.scene_end[scene]
        prog = min(1.0, max(0.0, (t - s0) / max(1.0, s1 - s0)))
        src = self.base(scene)
        # src는 W×H의 (1+ZOOM)배. z=1이면 W×H만큼(전체의 1/(1+ZOOM)), z=1+ZOOM이면 그보다 작게 잘라 확대.
        z = 1 + ZOOM * prog
        cw = W / z
        ch_ = H / z
        drift = (prog - 0.5) * 0.012 * W * (1 if scene % 2 else -1)   # 아주 약한 좌우 흐름
        cx = src.width / 2 + drift
        cy = src.height / 2 - 0.004 * H * prog
        box = (cx - cw / 2, cy - ch_ / 2, cx + cw / 2, cy + ch_ / 2)
        return src.resize((W, H), Image.BILINEAR, box=box)

    def scene_at(self, t):
        cur = self.scenes[0]
        for s in self.scenes:
            if self.scene_start[s] <= t:
                cur = s
        return cur

    def background(self, t):
        s = self.scene_at(t)
        i = self.scenes.index(s)
        if i + 1 < len(self.scenes):
            nxt = self.scenes[i + 1]
            ts = self.scene_start[nxt]
            if ts - XFADE <= t < ts:
                a = (t - (ts - XFADE)) / XFADE
                a = a * a * (3 - 2 * a)
                return Image.blend(self.bg_at(s, t), self.bg_at(nxt, t), a)
        return self.bg_at(s, t)

    # -- 글자
    def page_at(self, t):
        import bisect
        i = bisect.bisect_right(self.page_starts, t) - 1
        if i < 0:
            return None
        p = self.pages[i]
        return p if t < p.show else None

    @functools.lru_cache(6)
    def page_img(self, idx):
        return render_page(self.pages[idx])

    @functools.lru_cache(2)
    def card(self, which):
        if which == 'title':
            n, es, ko = self.title
            return render_title(n, es, ko)
        if which == 'next':
            if self.next_title:
                n, es, ko = self.next_title
                return render_title(n, es, ko, small_top=None)   # 장 번호·제목만, 시작 카드와 같은 자리
            return render_end()

    def frame(self, t):
        im = self.background(t).convert('RGBA')
        p = self.page_at(t)
        y = BAND_Y - BAND_FADE
        im.alpha_composite(self.page_img(p.idx) if p else band(False), (0, y))
        # 제목 카드: 0 ~ title_end, 마지막 0.6초 동안 사라짐
        if t < self.title_end:
            a = min(1.0, (self.title_end - t) / 0.6)
            im = overlay(im, self.card('title'), a)
        if self.outro is not None and t >= self.outro:
            a = min(1.0, (t - self.outro) / 0.8)
            im = overlay(im, self.card('next'), a)
        im = im.convert('RGB')
        # 시작 0.4초 검은 화면에서 밝아짐, 끝 1초 어두워짐
        k = min(1.0, t / 0.4, max(0.0, (self.duration - t) / 1.0))
        if k < 1.0:
            im = Image.blend(Image.new('RGB', (W, H)), im, max(0.0, k))
        return im


def overlay(im, card, a):
    if a >= 1.0:
        im.alpha_composite(card)
        return im
    if a <= 0:
        return im
    c = card.copy()
    c.putalpha(c.getchannel('A').point(lambda v: int(v * a)))
    im.alpha_composite(c)
    return im


# ---------------------------------------------------------------- 병렬 프레임 생성

_CH = None


def _init(ch):
    global _CH
    _CH = Chapter(ch)


def _chunk(args):
    i0, i1, fps, raw = args
    return b''.join(_CH.frame(i / fps).tobytes('raw', raw) for i in range(i0, i1))


def find_ffmpeg():
    exe = os.environ.get('FFMPEG') or shutil.which('ffmpeg')
    if not exe:
        return None
    r = subprocess.run([exe, '-hide_banner', '-encoders'], capture_output=True, text=True)
    if r.returncode or 'libx264' not in r.stdout:
        return None
    return exe


def avenc():
    """ffmpeg가 고장일 때 쓰는 macOS AVFoundation 인코더(avenc.swift)를 필요하면 컴파일."""
    exe = OUT / '.bin' / 'avenc'
    src = HERE / 'avenc.swift'
    if not exe.exists() or exe.stat().st_mtime < src.stat().st_mtime:
        exe.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(['swiftc', '-O', str(src), '-o', str(exe)], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit('avenc 컴파일 실패:\n' + r.stderr[-2000:])
    return exe


def encode(c, fps, t0, t1, out, workers, encoder='auto'):
    """프레임을 병렬로 만들어 인코더 stdin으로 흘린다.
    ffmpeg(libx264, 소리 AAC 160k 스테레오 48 kHz로 다시 인코딩) 또는
    avenc(H.264 8 Mbps, 소리는 원본 AAC 그대로)."""
    i0, i1 = int(t0 * fps), int(math.ceil(t1 * fps))
    dur = (i1 - i0) / fps
    ff = find_ffmpeg() if encoder in ('auto', 'ffmpeg') else None
    if encoder == 'ffmpeg' and not ff:
        raise SystemExit('ffmpeg가 동작하지 않습니다(libx264 필요).')
    if ff:
        raw = 'RGB'
        cmd = [ff, '-y', '-hide_banner', '-loglevel', 'error',
               '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
               '-ss', f'{t0:.3f}', '-t', f'{dur:.3f}', '-i', str(c.audio),
               '-map', '0:v', '-map', '1:a',
               '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-tune', 'stillimage',
               '-pix_fmt', 'yuv420p', '-g', str(fps * 2),
               '-c:a', 'aac', '-b:a', '160k', '-ac', '2', '-ar', '48000',
               '-movflags', '+faststart', '-shortest', str(out)]
        name = 'ffmpeg'
    else:
        raw = 'BGRX'
        cmd = [str(avenc()), str(out), str(W), str(H), str(fps), str(c.audio), f'{t0:.3f}', f'{dur:.3f}']
        name = 'avenc'
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
    step = fps * 2
    jobs = [(i, min(i + step, i1), fps, raw) for i in range(i0, i1, step)]
    t = time.time()
    with Pool(workers, initializer=_init, initargs=(c.ch,)) as pool:
        for k, buf in enumerate(pool.imap(_chunk, jobs)):
            proc.stdin.write(buf)
            if k % 30 == 0:
                done = (jobs[k][1] - i0) / fps
                print(f'\r  {c.ch}장 {done:6.0f}/{dur:.0f}초  ({time.time() - t:.0f}초 경과, {name})', end='', flush=True)
    proc.stdin.close()
    if proc.wait():
        raise SystemExit(f'{name} 인코딩 실패')
    print(f'\r  {c.ch}장 → {out}  ({time.time() - t:.0f}초, {name})            ')


# ---------------------------------------------------------------- 확인용

def fmt(t):
    return f'{int(t // 60):02d}:{t % 60:05.2f}'


def print_plan(c):
    print(f'{c.ch}장 「{c.title[1]}」 소리 {c.duration:.1f}초, 쪽 {len(c.pages)}개, 장면 {c.scenes}, '
          f'임시 그림 {c.placeholders}')
    for p in c.pages:
        head = NAMES.get(p.who, p.who) if p.kind == 'say' else p.kind
        print(f'  {fmt(p.start)}–{fmt(p.show)} s{p.scene} {head:6} | ' + ' / '.join(p.lines)
              + (f'  ({p.gloss})' if p.gloss else ''))


def check(c, sheet=True):
    """조각마다 시작 0.1초 뒤 프레임을 저장하고, 줄인 그림을 모아 한 장(sheet)으로."""
    d = OUT / f'ch{c.ch:02d}_check'
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    times = [0.5, c.title_end - 0.3] + [p.start + 0.1 for p in c.pages]
    times += [c.scene_start[s] - XFADE / 2 for s in c.scenes[1:]]
    if c.outro:
        times.append(c.outro + 1.5)
    times = sorted(set(round(t, 2) for t in times if 0 <= t < c.duration))
    lines = []
    thumbs = []
    for t in times:
        im = c.frame(t)
        p = c.page_at(t)
        name = f'{fmt(t).replace(":", "m")}s.png'
        im.save(d / name)
        lines.append(f'{fmt(t)}\t{name}\t' + (' / '.join(p.lines) if p else '-'))
        thumbs.append(im.resize((480, 270), Image.BILINEAR))
    (d / 'index.tsv').write_text('\n'.join(lines) + '\n')
    if sheet:
        cols = 4
        for k in range(0, len(thumbs), 24):
            part = thumbs[k:k + 24]
            rows = math.ceil(len(part) / cols)
            sh = Image.new('RGB', (cols * 480, rows * 270), 'black')
            for j, th in enumerate(part):
                sh.paste(th, ((j % cols) * 480, (j // cols) * 270))
            sh.save(d / f'_sheet{k // 24 + 1:02d}.jpg', quality=82)
    print(f'{c.ch}장: 프레임 {len(times)}장 → {d}')


def main():
    ap = argparse.ArgumentParser(description='장 하나를 mp4로')
    ap.add_argument('chapters', nargs='+', type=int)
    ap.add_argument('--fps', type=int, default=FPS)
    ap.add_argument('--from', dest='t0', type=float, default=0.0)
    ap.add_argument('--to', dest='t1', type=float)
    ap.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 4) - 3))
    ap.add_argument('--src', help='소리·시간표 폴더(기본 audiobook/out/pilot/final)')
    ap.add_argument('--plan', action='store_true', help='글자 쪽 시간표만 출력')
    ap.add_argument('--check', action='store_true', help='ffmpeg 없이 확인용 프레임만')
    ap.add_argument('--encoder', choices=['auto', 'ffmpeg', 'avenc'], default='auto',
                    help='auto: ffmpeg가 되면 ffmpeg, 아니면 macOS AVFoundation(avenc)')
    ap.add_argument('--at', type=float, nargs='*', help='이 시각들의 프레임 PNG')
    a = ap.parse_args()
    if a.src:
        set_src(a.src)
    print(f'입력: {AUDIO}')
    OUT.mkdir(parents=True, exist_ok=True)
    for ch in a.chapters:
        c = Chapter(ch)
        if a.plan:
            print_plan(c)
        elif a.check:
            check(c)
        elif a.at:
            for t in a.at:
                p = OUT / f'ch{ch:02d}_{fmt(t).replace(":", "m")}s.png'
                c.frame(t).save(p)
                print(p)
        else:
            t1 = min(a.t1 or c.duration, c.duration)
            part = '' if (a.t0 == 0 and t1 >= c.duration) else f'_{int(a.t0)}-{int(t1)}'
            encode(c, a.fps, a.t0, t1, OUT / f'ch{ch:02d}{part}.mp4', a.workers, a.encoder)
            if c.placeholders:
                print(f'  임시 그림 사용 장면: {c.placeholders}')


if __name__ == '__main__':
    main()
