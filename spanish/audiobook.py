#!/usr/bin/env python3
"""오디오북을 장 단위로 만든다. 서술·대사는 Gemini TTS, 마르티와 엄마의 편지는 ElevenLabs.

    python3 spanish/audiobook.py --plan              # 요청 없이 조각 수·글자 수·예상 비용만 본다
    python3 spanish/audiobook.py --plan --ch 1 -v    # 1장 조각 목록까지

조각을 나누는 규칙과 엔진 배정은 AUDIOBOOK.md에 있다.
- 서술(한국어)·장 제목·주소: 윤하 목소리(audiobook/cast.tsv의 narr)
- 대사 `@이름 —…`: src/voices.tsv의 인물 목소리. 뜻 줄(` :: `)은 읽지 않는다
- 편지 `@letter`: audiobook/letters.tsv의 작성자. 없으면 윤하
- 문법 쪽지 `@note`: 읽지 않는다
"""
import argparse, base64, difflib, hashlib, io, unicodedata, json, os, re, subprocess, sys, threading, time, urllib.error, urllib.request, wave
from array import array
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'
CONF = ROOT / 'audiobook'
CACHE = CONF / 'cache'             # 조각 음원(wav)과 비용 장부. 커밋하지 않는다
OUT = CONF / 'out'                 # 장별 m4a. 커밋하지 않는다
LEDGER = CACHE / 'ledger.tsv'
RATE = 24000
GEMINI_MODEL = 'gemini-2.5-flash-preview-tts'       # 서술만 있는 묶음
DIALOG_MODEL = 'gemini-3.1-flash-tts-preview'       # 대사가 든 묶음. 2.5 Flash는 연기가 과했다(11-09 Mike)
# 책 전체를 한 모델로(11-10 Mike: 모델을 섞으면 윤하 목소리가 바뀐다. 비교판에서 2.5 Pro가 가장 나았다)
BOOK_MODEL = 'gemini-2.5-pro-preview-tts'
ELEVEN_MODEL = 'eleven_v4'

NARR_MAX = 700                     # 서술 조각 하나의 최대 글자 수(문단을 이어 붙이되 이 이하로)
PAUSE = dict(line=0.5, para=0.8, scene=2.0)

# 비용 추정용. 실제 비용은 생성 때 응답의 토큰 수로 센다.
CHARS_PER_SEC = dict(ko=6.5, es=14.0)   # 낭독 속도(공백 포함 글자/초) 어림값
GEMINI_TOKENS_PER_SEC = 25              # 오디오 출력 토큰
GEMINI_USD_PER_M = {GEMINI_MODEL: dict(out=10.0, inp=0.5),        # 달러/100만 토큰
                    'gemini-3.1-flash-tts-preview': dict(out=20.0, inp=1.0),
                    'gemini-2.5-pro-preview-tts': dict(out=20.0, inp=1.0)}
ELEVEN_COST = 1.0                       # eleven_v4 글자당 크레딧


def load_tsv(path, ncol):
    rows = []
    for line in path.read_text().splitlines():
        if line.startswith('#') or not line.strip():
            continue
        rows.append(line.split('\t')[:ncol])
    return rows


VOICES = {k: dict(engine='gemini', voice=v, style=s, label=n) for k, n, v, s in load_tsv(SRC / 'voices.tsv', 4)}
CAST = {k: dict(engine=e, voice=v, style=s, label='Yuna') for k, e, v, s in load_tsv(CONF / 'cast.tsv', 4)}
VOICES['yunha']['label'] = 'Yuna'
PROFILES = dict(load_tsv(CONF / 'profiles.tsv', 2))
LETTERS = [(int(c), p, who) for c, p, who in load_tsv(CONF / 'letters.tsv', 3)]


def clean(s):
    """책 표기를 걷어 낸다: {낱말|발음} → 낱말, 강세·밑줄 표시 삭제."""
    s = re.sub(r'\{([^|}]+)\|[^}]*\}', r'\1', s)
    return s.replace('*', '').replace('_', '').strip()


def lang(s):
    return 'ko' if re.search('[가-힣]', s) else 'es'


def letter_author(ch, block):
    for c, prefix, who in LETTERS:
        if c == ch and block.startswith(prefix):
            return who
    return 'yunha'


def segments(ch):
    """장 하나를 낭독 조각 목록으로. 조각: dict(kind, who, text, pause)"""
    lines = (SRC / f'ch{ch:02d}.txt').read_text().split('\n')
    out, narr = [], []

    def add(kind, who, text, pause='para'):
        out.append(dict(kind=kind, who=who, text=text, pause=pause, lang=lang(text)))

    def flush():
        if narr:
            add('narr', 'narr', ' '.join(narr))
            narr.clear()

    i = 0
    notes = load_notes(ch)
    while i < len(lines):
        s = lines[i].strip()
        i += 1
        if not s:
            continue
        if s.startswith('# '):
            n, es, _ = [x.strip() for x in s[2:].split('|')]
            add('title', 'narr', f'{n}장. {es}.', 'scene')
        elif s == '##':
            flush()
            if out:
                out[-1]['pause'] = 'scene'
        elif s in ('@letter', '@address', '@note'):
            flush()
            body = []
            while i < len(lines) and lines[i].strip() != '@end':
                body.append(lines[i].strip())
                i += 1
            i += 1
            block = '\n'.join(b for b in body if b)
            if s == '@note':
                continue
            who = letter_author(ch, block) if s == '@letter' else 'narr'
            if who == 'yunha':          # 윤하가 소리 내어 읽는 쪽지·수첩은 서술 목소리로
                who = 'narr'
            # 여러 줄 블록은 한 줄로. 줄바꿈을 그대로 두면 묶음 안에서 건너뛰고 읽는다(11-09 1장 주소)
            text = ' '.join(l if re.search(r'[.:,;!?…»]$', l) else l + '.' for l in clean(block).split('\n'))
            # 대문자 간판(SERRALLERIA)은 철자를 한 글자씩 읽을 수 있어 첫 글자만 대문자로
            text = re.sub(r'\b[A-ZÀ-Ý]{2,}(?:\s+[A-ZÀ-Ý]{2,})*\b', lambda m: m.group(0).capitalize(), text)
            add('letter' if s == '@letter' else 'address', who, text.replace(' · ', ', '))
        elif re.match(r'@\w+ ', s):
            flush()
            who, rest = s[1:].split(' ', 1)
            text = clean(rest.split(' :: ')[0]).lstrip('—').strip()
            add('say', who, text, 'line')
            if ' :: ' in rest:                  # 책의 한국어 뜻풀이. 화면(유튜브)용, 낭독·프롬프트에는 안 쓴다
                out[-1]['gloss'] = clean(rest.split(' :: ', 1)[1])
        else:
            t = clean(s)
            if narr and (sum(len(x) for x in narr) + len(t) > NARR_MAX
                         or any(t.startswith(clean(note_prefix(p))) for p, _ in notes)):   # 지시가 붙는 문단은 새 조각으로
                flush()
            narr.append(t)
    flush()
    apply_notes(ch, out, notes)
    return out


def load_notes(ch):
    """audiobook/chNN.tsv: 조각 앞머리 → 지시(영어, 짧게).
    - 서술 조각: 말투. 장면이 바뀔 때까지 이어진다.
    - 대사 조각(스페인어 앞머리): 그 줄의 말투.
    - `@scene 앞머리`: 장면 설명. 그 조각부터 장면이 끝날(##) 때까지 모든 요청에 붙는다."""
    p = CONF / f'ch{ch:02d}.tsv'
    return load_tsv(p, 2) if p.exists() else []


def note_prefix(p):
    return p[7:] if p.startswith('@scene ') else p


def apply_notes(ch, segs, notes):
    hits = {}
    texts = {x['text'] for x in segs}
    for s in segs:
        for j, (prefix, note) in enumerate(notes):
            pf = clean(note_prefix(prefix))
            # 앞머리가 어떤 조각 전체와 똑같으면 그 조각에만 붙인다("Eso."가 "Eso. Y mi abuelo…"에 붙지 않게)
            if (s['text'] == pf) if pf in texts else s['text'].startswith(pf):
                s['scene' if prefix.startswith('@scene ') else 'note'] = note
                hits[j] = hits.get(j, 0) + 1
    for j, (prefix, _) in enumerate(notes):
        if j not in hits:
            print(f'  ! {ch}장 지시를 붙일 조각을 못 찾음: {prefix}', file=sys.stderr)
        elif hits[j] > 1:
            print(f'  ! {ch}장 지시가 조각 {hits[j]}개에 붙음(앞머리를 늘릴 것): {prefix}', file=sys.stderr)
    mood = scene = ''
    for s in segs:
        scene = s.get('scene', scene)
        if scene:
            s['scene'] = scene
        if s['kind'] in ('narr', 'letter', 'address') and s['who'] == 'narr':
            mood = s.get('note', mood)
            s['mood'] = mood
        if s['pause'] == 'scene':
            mood = scene = ''


def voice_of(seg):
    v = CAST.get(seg['who']) or VOICES.get(seg['who'])
    if not v:
        sys.exit(f'목소리 없음: @{seg["who"]} — src/voices.tsv 또는 audiobook/cast.tsv에 추가')
    return v


CHUNK_MAX = 1200          # 묶음 하나의 최대 글자 수(약 3분)
DLG_LINES = 6             # 대화 묶음 하나의 최대 줄 수. 9줄 묶음에서 3.1이 줄을 빠뜨렸다(11-09)
YUNA = ('narr', 'yunha')  # 서술과 윤하 대사는 같은 목소리(ElevenLabs Seulki, 11-10)


SHORT = 80   # 이보다 짧은 서술은 혼자 요청하지 않고 옆 대화 묶음에 넣는다(짧은 요청은 엉뚱하게 읽힌다, 11-09 "1장. Hola.")


def lane(s):
    """요청 갈래. narr: 서술(2.5 Flash) / dlg: 대화(3.1 Flash, 화자 둘까지) / solo:이름: 윤하 아닌 인물이 읽는 편지 / eleven."""
    if voice_of(s)['engine'] == 'eleven':
        return 'eleven'
    if s['kind'] == 'say':
        return 'dlg'
    if s['who'] not in YUNA:
        return 'solo:' + s['who']
    return 'narr'


def units(ch):
    return scene_units(segments(ch))


def scene_units(segs):
    """요청 단위(11-10, 한 모델 장면 묶음). 서술과 대사를 한 요청에 섞어, 앞뒤 맥락 안에서 읽게 한다.
    끊는 곳:
    - 장면이 바뀜(##), ElevenLabs 조각, 윤하 아닌 인물이 읽는 편지(혼자 한 단위)
    - 화자가 셋째로 늘어남(Gemini는 한 요청에 둘까지)
    - CHUNK_MAX를 넘음. 이때는 대사를 주고받는 가운데가 아니라 서술 문단 앞에서 끊는다
    분위기 지시가 바뀌어도 끊지 않는다(줄별 지시로 넣는다). 같은 장면 안에서 끊긴 요청에는
    바로 앞 대목을 '읽지 말 것'으로 함께 준다(ctx)."""
    for s in segs:
        if s['kind'] == 'title':
            s['pause'] = 'para'                      # 제목은 첫 문단과 한 요청(짧은 요청은 엉뚱하게 읽힌다)
    alone = lambda s: lane(s) == 'eleven' or lane(s).startswith('solo:')
    spk = lambda xs: len({voice_of(x)['label'] for x in xs})
    size = lambda xs: sum(len(x['text']) for x in xs)
    out, cur = [], []
    for s in segs:
        if cur and (alone(s) or alone(cur[-1]) or cur[-1]['pause'] == 'scene' or spk(cur + [s]) > 2):
            out.append(cur); cur = []
        elif cur and size(cur) + len(s['text']) > CHUNK_MAX:
            # 뒤쪽 절반 안에서 가장 늦은 서술 문단 앞. 없으면 여기서
            c = next((k for k in range(len(cur) - 1, len(cur) // 2 - 1, -1)
                      if k and cur[k]['kind'] == 'narr' and len(cur[k]['text']) >= SHORT), len(cur))
            out.append(cur[:c]); cur = cur[c:]
        cur.append(s)
    if cur:
        out.append(cur)
    for k, u in enumerate(out):
        ln = lane(u[0])
        if not alone(u[0]):
            ln = 'narr' if all(x['kind'] != 'say' and x['who'] in YUNA for x in u) else 'dlg'
        for x in u:
            x['lane'] = ln
            x.pop('ctx', None)
        prev = out[k - 1] if k else None
        if prev and prev[-1]['pause'] != 'scene' and not alone(u[0]):     # 앞이 ElevenLabs 윤하여도 맥락으로 준다
            u[0]['ctx'] = [(voice_of(x)['label'], x['text'] if len(x['text']) <= 160 else '…' + x['text'][-160:])
                           for x in prev[-2:]]
    flat = [x for u in out for x in u]                 # ElevenLabs 이어 읽기용 앞뒤 글(같은 장면 안에서만)
    for k, x in enumerate(flat):
        x['prev_text'] = flat[k - 1]['text'] if k and flat[k - 1]['pause'] != 'scene' else ''
        x['next_text'] = flat[k + 1]['text'] if k + 1 < len(flat) and x['pause'] != 'scene' else ''
    return out


def plan(chs, verbose):
    tot = dict(gemini_chars=0, gemini_sec=0.0, gemini_req=0, eleven_chars=0, eleven_req=0)
    print(f'{"장":>3} {"조각":>4} {"Gemini 글자":>11} {"요청":>4} {"ElevenLabs 글자":>15} {"길이(분)":>8}')
    for ch in chs:
        segs = segments(ch)
        for s in segs:
            if voice_of(s)['voice'] == 'TBD':
                print(f'  ! {ch}장: {s["who"]} 목소리가 아직 없음(audiobook/cast.tsv)')
        g = [s for s in segs if voice_of(s)['engine'] == 'gemini']
        gus = [u for u in units(ch) if voice_of(u[0])['engine'] == 'gemini']
        greq = len(gus)
        for u in gus:
            m = unit_model(u)
            usec = sum(len(x['text']) / CHARS_PER_SEC[x['lang']] for x in u)
            r = GEMINI_USD_PER_M[m]
            tot.setdefault(m, [0, 0.0])
            tot[m][0] += 1
            tot[m][1] += usec * GEMINI_TOKENS_PER_SEC / 1e6 * r['out'] + sum(len(x['text']) for x in u) * 1.5 / 1e6 * r['inp']
        e = [s for s in segs if voice_of(s)['engine'] == 'eleven']
        sec = sum(len(s['text']) / CHARS_PER_SEC[s['lang']] for s in segs)
        gsec = sum(len(s['text']) / CHARS_PER_SEC[s['lang']] for s in g)
        gc, ec = sum(len(s['text']) for s in g), sum(len(s['text']) for s in e)
        tot['gemini_chars'] += gc; tot['gemini_sec'] += gsec; tot['gemini_req'] += greq
        tot['eleven_chars'] += ec; tot['eleven_req'] += len(e)
        print(f'{ch:>3} {len(segs):>4} {gc:>11,} {greq:>4} {ec:>15,} {sec / 60:>8.1f}')
        if verbose:
            for s in segs:
                v = voice_of(s)
                print(f'      {s["kind"]:7} {s["who"]:8} {v["engine"]:6} {len(s["text"]):4}  {s["text"][:60]}')
    print(f'\nGemini: {tot["gemini_req"]:,}회 요청, {tot["gemini_chars"]:,}자, 약 {tot["gemini_sec"] / 3600:.1f}시간')
    for m in GEMINI_USD_PER_M:
        if m in tot:
            n, usd = tot[m]
            print(f'  {m}: {n}회(하루 100회 → 최소 {-(-n // 100)}일), 약 ${usd:.2f}')
    print(f'ElevenLabs: {tot["eleven_req"]:,}회 요청, {tot["eleven_chars"]:,}자 → 약 {tot["eleven_chars"] * ELEVEN_COST:,.0f} 크레딧 (eleven_v4)')


# ── 생성 ─────────────────────────────────────────────────────────────
# 지시가 길면 2.5 Flash가 지시문을 소리 내어 읽는다(11-09 1장 시험에서 9곳). 짧게 둔다.
NARR_STYLE = 'Read in a natural, understated way, like an audiobook narrator'
SAY_STYLE = 'Say in Spanish, naturally and not theatrically, as {style}'


def prompt_of(seg):
    v = voice_of(seg)
    if v['engine'] == 'eleven':
        return seg['text']
    if seg['who'] == 'narr':
        extra = seg.get('mood') or seg.get('note')
        return f'{NARR_STYLE}{"; " + extra if extra else ""}: {seg["text"]}'
    style = SAY_STYLE.format(style=v['style'])
    if seg.get('note'):
        style += '; ' + seg['note']
    return f'{style}: {seg["text"]}'


def cache_path(seg):
    v = voice_of(seg)
    model = ELEVEN_MODEL if v['engine'] == 'eleven' else GEMINI_MODEL
    h = hashlib.sha1(f'{model}|{v["voice"]}|{prompt_of(seg)}'.encode()).hexdigest()[:16]
    return CACHE / f'{h}.wav'


def unit_model(unit):
    """책 전체 한 모델(BOOK_MODEL). compare.py가 바꿔 끼운다."""
    return BOOK_MODEL


def voice_cfg(name):
    return {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': name}}}


def quote(t, n=28):
    return '"' + (t if len(t) <= n else t[:n].rstrip() + '…') + '"'


# 모든 요청 맨 앞에 똑같이 넣는 기준 문장(11-10). 요청마다 목소리를 새로 만들기 때문에 톤이 흔들렸다.
ANCHOR = ('This is one excerpt of a long audiobook recorded in many parts. Yuna, the narrator, must sound exactly the same '
          'in every part: the same voice, the same calm, even, mid-low tone, the same steady pace. '
          'Scene moods and notes below may change her energy only slightly; they never change her voice.')


def unit_prompt(unit):
    """묶음의 프롬프트와 목소리 설정. 원칙(AUDIOBOOK.md 8절):
    - 인물은 profiles.tsv의 중립 설명만. 연기 형용사는 과장된다.
    - 쉼·속도는 지시하지 않는다. 쉼은 조립할 때 넣는다(쉼을 지시하니 주고받기가 어색해졌다, 11-09).
    - "적힌 그대로" 읽게 한다. 원문을 바꾸거나 덧붙인 일이 있었다(De nada → De res).
    - 맥락(11-10): 장면 설명, 줄별 지시, 바로 앞 대목은 대본 앞 지시 칸에만 둔다. 대본 줄에 괄호로 넣으면 소리 내어 읽는다."""
    ln = unit[0]['lane']
    narr_voice = CAST['narr']['voice']
    lines_plain = '\n'.join(s['text'] for s in unit)
    if ln.startswith('solo:'):
        who = ln[5:]
        return (f'{voice_of(unit[0])["label"]} is {PROFILES[who]}. She reads aloud, quietly and plainly, a letter she wrote. '
                f'Read it exactly as written:\n{lines_plain}'), voice_cfg(VOICES[who]['voice'])
    yuna = f'Yuna is {PROFILES["yunha"]}; she narrates in Korean, calm and understated'
    labels = list(dict.fromkeys(voice_of(s)['label'] for s in unit))          # 나온 순서대로, 둘까지
    who_of = {voice_of(s)['label']: ('yunha' if s['who'] in YUNA else s['who']) for s in unit}
    voice = {l: (narr_voice if l == 'Yuna' else VOICES[who_of[l]]['voice']) for l in labels}
    head = [ANCHOR]
    if ln == 'narr':
        head.append('An audiobook narration. ' + yuna + '.')
    else:
        head.append('An audiobook scene. ' + ' '.join(f'{yuna}.' if l == 'Yuna' else f'{l} is {PROFILES[who_of[l]]}.'
                                                       for l in labels))
    scene = next((x['scene'] for x in unit if x.get('scene')), '')   # 장 제목 조각에는 아직 장면 설명이 없다
    if scene:
        head.append('Scene: ' + scene)
    if unit[0].get('ctx'):
        head.append('Just before this part (already read; do not read it again):\n'
                    + '\n'.join(f'{l}: {t}' for l, t in unit[0]['ctx']))
    notes = []
    if unit[0].get('mood') and not unit[0].get('note'):
        notes.append(f'Narration at the start: {unit[0]["mood"]}.')
    for s in unit:
        if s.get('note'):
            if s['kind'] == 'say':
                notes.append(f'{voice_of(s)["label"]}, {quote(s["text"])}: {s["note"]}.')
            else:
                notes.append(f'Narration from {quote(s["text"], 16)}: {s["note"]}.')
    if notes:
        head.append('Delivery notes (small adjustments of energy only, never of voice; not to be read aloud):\n' + '\n'.join('- ' + n for n in notes))
    head.append('Natural, understated delivery. Read every line below exactly as written; do not add words.')
    # 화자가 하나여도 늘 두 명 설정으로 보낸다(11-10 Mike: 한 명 설정과 두 명 설정에서 윤하 톤이 달랐다, 2장 0:50).
    # 윤하만 나오면 쓰이지 않는 둘째 화자로 몬세 목소리를 둔다.
    if len(labels) == 1:
        spare = 'Montse' if labels[0] != 'Montse' else 'Yuna'
        labels = labels + [spare]
        voice[spare] = narr_voice if spare == 'Yuna' else VOICES['montse']['voice']
    lines = '\n'.join(f'{voice_of(s)["label"]}: {s["text"]}' for s in unit)
    cfg = {'multiSpeakerVoiceConfig': {'speakerVoiceConfigs': [
        {'speaker': l, **voice_cfg(voice[l])} for l in labels]}}
    return '\n\n'.join(head) + '\n\n' + lines, cfg


def turn(a, b):
    """a 다음 b에서 말하는 사람이 바뀌나(서술과 대사 사이도 바뀜으로 본다)."""
    return a['who'] != b['who'] or a['kind'] != b['kind']


def unit_path(unit):
    prompt, cfg = unit_prompt(unit)
    h = hashlib.sha1(f'{unit_model(unit)}|{json.dumps(cfg, sort_keys=True)}|{prompt}'.encode()).hexdigest()[:16]
    return CACHE / f'u{h}.wav'


def unit_check(pcm, unit):
    a = array('h', pcm)
    sec = len(a) / RATE
    expect = sum(len(s['text']) / CHARS_PER_SEC[s['lang']] for s in unit) + 0.4 * (len(unit) - 1)
    # 대화(3.1)는 윤하의 느린 스페인어와 주고받는 쉼 때문에 예상의 1.5배쯤이 정상이었다(11-09). 섞임은 받아쓰기로 잡는다.
    # 짧은 묶음은 지시 칸(장면 설명·앞 대목)이 본문의 수십 배라, 그것을 읽어 버리면 길이가 몇 배가 된다
    if expect >= 2 and sec > expect * (1.45 if unit[0]['lane'] == 'narr' else 2.0) + 1.5:
        return f'지시문 섞임 의심 {sec:.1f}초(예상 {expect:.1f}초)'
    if sec < expect * 0.55 or sec > expect * 3 + 4:
        return f'길이 이상 {sec:.1f}초(예상 {expect:.1f}초)'
    if sum(1 for x in a[-int(RATE * 0.1):] if abs(x) > 30000):
        return '끝 잡음'
    return None


class Budget(Exception):
    pass


class DailyLimit(Exception):
    pass


class NoAudio(Exception):
    pass


_lock = threading.Lock()


def spent():
    if not LEDGER.exists():
        return 0.0, 0
    usd = credits = 0
    for line in LEDGER.read_text().splitlines():
        f = line.split('\t')
        if len(f) < 5:
            continue
        if f[1] == 'gemini':
            usd += float(f[4])
        else:
            credits += int(f[4])
    return usd, credits


def log(engine, a, b, cost, what):
    with _lock:
        CACHE.mkdir(parents=True, exist_ok=True)
        with LEDGER.open('a') as fp:
            fp.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")}\t{engine}\t{a}\t{b}\t{cost}\t{what[:40]!r}\n')


def post(url, body, headers, raw=False):
    req = urllib.request.Request(url, json.dumps(body).encode(), {'Content-Type': 'application/json', **headers})
    for n in range(8):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read() if raw else json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors='replace')[:600]
            if e.code == 429 and 'per_day' in msg:
                raise DailyLimit('Gemini 하루 요청 한도(100회). 미국 태평양 시간 자정(한국 17시 전후)에 풀린다')
            if e.code in (429, 500, 502, 503, 504) and n < 7:
                time.sleep(20 * (n + 1)); continue
            raise RuntimeError(f'HTTP {e.code}: {msg}')
        except (urllib.error.URLError, TimeoutError):
            if n == 7:
                raise
            time.sleep(10)


def gemini(seg, prompt=None, cfg=None, model=GEMINI_MODEL):
    if prompt is None:
        prompt = prompt_of(seg)
        cfg = {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice_of(seg)['voice']}}}
    body = {'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'responseModalities': ['AUDIO'], 'speechConfig': cfg}}
    r = post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent', body,
             {'x-goog-api-key': os.environ['GEMINI_API_KEY']})
    try:
        pcm = base64.b64decode(r['candidates'][0]['content']['parts'][0]['inlineData']['data'])
    except (KeyError, IndexError):
        raise NoAudio(f'오디오 없음({r.get("candidates", [{}])[0].get("finishReason")})')
    u = r.get('usageMetadata', {})
    out_tok, in_tok = u.get('candidatesTokenCount', 0), u.get('promptTokenCount', 0)
    r = GEMINI_USD_PER_M[model]
    usd = out_tok / 1e6 * r['out'] + in_tok / 1e6 * r['inp']
    log('gemini', in_tok, out_tok, f'{usd:.6f}', f'[{model[7:10]}] ' + seg['text'])
    return pcm


ELEVEN_SEED = 7      # 같은 글이면 같은 소리. 목소리 흔들림을 줄인다


def eleven(seg):
    v = voice_of(seg)
    body = {'text': prompt_of(seg), 'model_id': ELEVEN_MODEL, 'seed': ELEVEN_SEED}
    if seg.get('prev_text'):
        body['previous_text'] = seg['prev_text'][-300:]     # 앞뒤 글을 주면 이음새의 억양이 이어진다(읽지는 않는다)
    if seg.get('next_text'):
        body['next_text'] = seg['next_text'][:300]
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{v["voice"]}?output_format=pcm_24000'
    hdr = {'xi-api-key': os.environ['ELEVENLABS_API_KEY']}
    try:
        pcm = post(url, body, hdr, raw=True)
    except RuntimeError as e:                               # 모델이 앞뒤 글을 받지 않으면 빼고 다시
        if 'previous_text' not in str(e) and 'next_text' not in str(e):
            raise
        body.pop('previous_text', None); body.pop('next_text', None)
        pcm = post(url, body, hdr, raw=True)
    log('eleven', len(seg['text']), 0, len(seg['text']), seg['text'])
    return pcm


def check(pcm, seg):
    """버릴 소리면 이유를, 괜찮으면 None."""
    a = array('h', pcm)
    sec = len(a) / RATE
    expect = len(seg['text']) / CHARS_PER_SEC[seg['lang']]
    if sec < min(0.3, expect * 0.3) or sec > expect * 3 + 4:
        return f'길이 이상 {sec:.1f}초(예상 {expect:.1f}초)'
    # 지시문을 읽으면 서술 조각이 길어진다. 정상은 예상의 0.8–1.2배였고, 지시문이 섞인 것은 1.6–2.5배였다.
    if seg['who'] == 'narr' and seg['lang'] == 'ko' and len(seg['text']) >= 20 and sec > expect * 1.45:
        return f'지시문 섞임 의심 {sec:.1f}초(예상 {expect:.1f}초)'
    tail = a[-int(RATE * 0.1):]
    if sum(1 for x in tail if abs(x) > 30000):
        return '끝 잡음'
    return None


def trim(pcm, head=0.05, tail=0.3, thr=150, fade=0.03):
    """앞뒤 무음을 걷는다. 끝은 넉넉히 남기고 짧게 줄인다. 전에는 끝 0.05초만 남겨(문턱 400)
    작아지며 끝나는 끝음절이 잘렸다(11-10 2.5 Pro 비교본 7묶음 중 6개)."""
    a = array('h', pcm)
    i = next((k for k, x in enumerate(a) if abs(x) > thr), 0)
    j = next((k for k in range(len(a) - 1, -1, -1) if abs(a[k]) > thr), len(a) - 1)
    a = a[max(0, i - int(RATE * head)):min(len(a), j + int(RATE * tail))]
    n = min(len(a), int(RATE * fade))
    for k in range(n):
        a[len(a) - n + k] = int(a[len(a) - n + k] * (n - k) / n)
    return a.tobytes()


def tail_cut(pcm):
    """모델이 말하다 만 채로 끝냈는지(원본 끝 0.05초에 아직 말소리)."""
    a = array('h', pcm)
    end = a[-int(RATE * 0.05):]
    return '끝 잘림 의심' if end and max(map(abs, end)) > 2500 else None


def render(seg, budget):
    p = cache_path(seg)
    if p.exists():
        return p
    engine = voice_of(seg)['engine']
    for attempt in range(4):
        usd, credits = spent()
        if engine == 'gemini' and usd >= budget:
            raise Budget(f'Gemini 누적 ${usd:.2f} — 상한 ${budget}')
        try:
            pcm = gemini(seg) if engine == 'gemini' else eleven(seg)
            why = check(pcm, seg)
        except NoAudio as e:
            why = str(e)
        if not why:
            break
        print(f'  다시: {why} — {seg["text"][:30]}', file=sys.stderr)
    else:
        raise RuntimeError(f'4번 모두 실패: {seg["text"][:40]}')
    p.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(trim(pcm))
    return p


CHECK_MODEL = 'gemini-2.5-flash'   # 받아쓰기 검사. TTS가 아니라 TTS 하루 한도를 쓰지 않는다
CHECK = False
CHECK_UNDER = 150                  # 이보다 짧은 서술 묶음과 모든 대화·편지 묶음을 받아써서 확인한다
REVIEW = []                        # 세 번 만들어도 검사를 통과하지 못한 묶음 → out/chNN_review.tsv


def norm(t):
    t = unicodedata.normalize('NFKD', t.lower())
    return ''.join(c for c in t if c.isalnum() and not unicodedata.combining(c))


def heard(pcm):
    """소리를 받아써서 글로. 비용은 장부에 gemini로 적는다."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(pcm)
    body = {'contents': [{'parts': [
        {'inlineData': {'mimeType': 'audio/wav', 'data': base64.b64encode(buf.getvalue()).decode()}},
        {'text': 'Transcribe this audio verbatim. Write Korean in Hangul, and write Spanish and Catalan words in '
                 'their own Latin spelling (never in Hangul). Names: Yuna, Yunha, Montse, Marc. '
                 'Include any extra words, laughs or English instructions you hear. Output only the transcript.'}]}],
            'generationConfig': {'thinkingConfig': {'thinkingBudget': 0}}}
    r = post(f'https://generativelanguage.googleapis.com/v1beta/models/{CHECK_MODEL}:generateContent', body,
             {'x-goog-api-key': os.environ['GEMINI_API_KEY']})
    u = r.get('usageMetadata', {})
    usd = u.get('promptTokenCount', 0) / 1e6 * 1.0 + u.get('candidatesTokenCount', 0) / 1e6 * 2.5
    log('gemini', u.get('promptTokenCount', 0), u.get('candidatesTokenCount', 0), f'{usd:.6f}', '[chk] 받아쓰기')
    try:
        return r['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError):
        return ''


def judge(unit, pcm):
    """소리가 원고와 맞는지 Gemini(텍스트 모델)에게 원고를 주고 묻는다. 문제 목록을 돌려준다(빈 목록이면 통과).
    글자 대조(difflib)는 받아쓰기 흔들림(숫자 표기, 스페인어를 한글로 적기) 때문에 맞는 소리도 0.7대가 나와 쓰지 않는다(11-09)."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(pcm)
    script = '\n'.join(s['text'] for s in unit)
    body = {'contents': [{'parts': [
        {'inlineData': {'mimeType': 'audio/wav', 'data': base64.b64encode(buf.getvalue()).decode()}},
        {'text': 'This audio should be a reading of the script below (Korean narration, Spanish/Catalan dialogue). '
                 'Check it against the script. Report only real problems: a line or phrase skipped, words changed, '
                 'words or sounds added (including any English instructions read aloud), or a line clearly garbled. '
                 'Ignore accent, pronunciation details, number formats and punctuation.\n\nSCRIPT:\n' + script}]}],
            'generationConfig': {'thinkingConfig': {'thinkingBudget': 0}, 'responseMimeType': 'application/json',
                                 'responseSchema': {'type': 'OBJECT', 'properties': {
                                     'problems': {'type': 'ARRAY', 'items': {'type': 'STRING'}}}, 'required': ['problems']}}}
    r = post(f'https://generativelanguage.googleapis.com/v1beta/models/{CHECK_MODEL}:generateContent', body,
             {'x-goog-api-key': os.environ['GEMINI_API_KEY']})
    u = r.get('usageMetadata', {})
    usd = u.get('promptTokenCount', 0) / 1e6 * 1.0 + u.get('candidatesTokenCount', 0) / 1e6 * 2.5
    log('gemini', u.get('promptTokenCount', 0), u.get('candidatesTokenCount', 0), f'{usd:.6f}', '[chk] 대조')
    try:
        return json.loads(r['candidates'][0]['content']['parts'][0]['text'])['problems']
    except (KeyError, IndexError, ValueError):
        return []


def render_unit(unit, budget):
    """묶음 하나를 만든다. 길이·잡음 검사, 필요하면 받아쓰기 대조. 세 번 안에 통과하지 못하면
    가장 나은 것을 쓰고 REVIEW에 적는다(사람이 들어 볼 목록). 경로 목록을 돌려준다."""
    if voice_of(unit[0])['engine'] == 'eleven':
        return [render(unit[0], budget)]
    p = unit_path(unit)
    if p.exists():
        return [p]
    prompt, cfg = unit_prompt(unit)
    chars = sum(len(s['text']) for s in unit)
    # 자동 대조는 끈다: 2.5 Flash 판정이 맞는 소리도 틀렸다고 하는 일이 많아(11-09 1장 29묶음 중 20개) 재생성 비용만 늘었다.
    # 대신 장을 만든 뒤 받아쓰기 전문을 원고와 대조한다(AUDIOBOOK.md 8절).
    want_check = CHECK and (unit[0]['lane'] != 'narr' or chars < CHECK_UNDER)
    best, best_score, why = None, -1.0, ''
    for attempt in range(3):
        usd, _ = spent()
        if usd >= budget:
            raise Budget(f'Gemini 누적 ${usd:.2f} — 상한 ${budget}')
        try:
            pcm = gemini(unit[0], prompt, cfg, unit_model(unit))      # 원본 그대로 저장. 자르기는 조립할 때(끝음절 잘림, 11-10)
        except NoAudio as e:
            why = str(e); print(f'  다시: {why} — {unit[0]["text"][:30]}', file=sys.stderr); continue
        why = unit_check(trim(pcm), unit) or tail_cut(pcm)
        score = 0.0 if why else 1.0
        if not why and want_check:
            problems = judge(unit, pcm)
            score = 1.0 / (1 + len(problems))
            if problems:
                why = '원고와 다름: ' + '; '.join(problems)[:150]
        if score > best_score:
            best, best_score = pcm, score
        if not why:
            break
        print(f'  다시: {why} — {unit[0]["text"][:30]}', file=sys.stderr)
    if best is None:
        raise RuntimeError(f'세 번 모두 소리 없음: {unit[0]["text"][:40]}')
    if why:
        REVIEW.append((unit, why))
    p.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(p), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(best)
    return [p]


def squash_gaps(pcm, longest=1.2, to=0.8):
    """묶음 안의 지나치게 긴 무음(모델이 멈칫한 곳)을 줄인다."""
    a = array('h', pcm)
    fr = RATE // 100
    out, run_start, k = array('h'), None, 0
    for k in range(0, len(a), fr):
        q = max(map(abs, a[k:k + fr]), default=0) < 500
        if q and run_start is None:
            run_start = k
        if not q:
            if run_start is not None:
                gap = a[run_start:k]
                out.extend(gap if len(gap) <= RATE * longest else gap[:int(RATE * to)])
                run_start = None
            out.extend(a[k:k + fr])
    if run_start is not None:
        out.extend(a[run_start:])
    return out.tobytes()


def level(pcm, target=4100):        # 말소리 RMS 약 -18 dBFS(1장 첫 판은 3000, 작다는 평, 11-09)
    """말소리 부분의 크기(RMS)를 맞춘다. 두 Gemini 모델과 ElevenLabs의 음량 차이를 없앤다."""
    a = array('h', pcm)
    loud = [x for x in a if abs(x) > 500]
    if not loud:
        return pcm
    rms = (sum(x * x for x in loud) / len(loud)) ** 0.5
    g = min(2.5, max(0.5, target / rms), 30000 / max(map(abs, a)))
    return array('h', (int(x * g) for x in a)).tobytes()


TURN_PAUSE = 0.45   # 묶음 안에서 말하는 사람이 바뀌는 자리에 더하는 쉼(초)


def turn_pauses(pcm, unit):
    """묶음 소리에서 말하는 사람이 바뀌는 자리를 찾아 쉼을 더한다. API를 쓰지 않는다.
    줄별 글자 수로 경계 시각을 어림하고(실제 길이에 맞춰 늘이거나 줄임), ±1.2초 안의 가장 가까운 무음 구간 한가운데에 넣는다.
    못 찾으면 그 자리는 그대로 둔다."""
    a = array('h', pcm)
    fr = RATE // 100                                       # 10ms
    quiet = [max(map(abs, a[i:i + fr])) < 500 for i in range(0, len(a) - fr, fr)]
    gaps, run = [], 0                                      # (가운데 프레임, 길이) — 120ms 이상 무음
    for k, q in enumerate(quiet + [False]):
        if q:
            run += 1
        else:
            if run >= 12:
                gaps.append((k - run // 2, run))
            run = 0
    est = [len(s['text']) / CHARS_PER_SEC[s['lang']] + 0.4 for s in unit]
    scale = len(quiet) / max(1, sum(est) * 100)
    t, cuts = 0.0, []
    for k in range(len(unit) - 1):
        t += est[k] * 100 * scale
        if not turn(unit[k], unit[k + 1]):
            continue
        near = [g for g in gaps if abs(g[0] - t) <= 120 and g[0] not in cuts]
        # 0.12초짜리 무음은 '었다'의 ㄷ 닫힘 같은 낱말 안 틈일 때가 많다. 거기에 넣으면 '…었 (0.6초) 다'가 된다
        # (11-10 파일럿 1–3장 21곳, audiobook/out/pilot/turn_pause_fix.tsv). 0.25초 넘는 진짜 쉼이 근처에 있으면 그쪽만 쓴다.
        near = [g for g in near if g[1] >= 25] or near
        # 그래도 틈 뒤에 0.3초 이하 소리('다' 한 음절)만 있고 다시 쉬면 그 틈은 문장 끝이 아니다(11-10 4장 5:34).
        nxt = {g[0]: next((h for h in gaps if h[0] > g[0]), None) for g in near}
        # 그런 틈은 바로 뒤 쉼('다' 뒤)으로 바꾼다.
        near = [nxt[g[0]] if nxt[g[0]] and (nxt[g[0]][0] - nxt[g[0]][1] // 2) - (g[0] + g[1] - g[1] // 2) <= 30
                else g for g in near]
        near = [g for g in near if g[0] not in cuts]
        if near:
            cuts.append(min(near, key=lambda g: abs(g[0] - t))[0])
    out, prev = bytearray(), 0
    for c in sorted(cuts):
        out += a[prev * fr:c * fr].tobytes() + b'\0\0' * int(RATE * TURN_PAUSE)
        prev = c
    return bytes(out + a[prev * fr:].tobytes())


def marks(pcm, unit):
    """묶음 소리 안에서 조각 사이 경계 시각(초)을 어림한다. 화면 글자 싱크용. API를 쓰지 않는다.
    turn_pauses와 같은 방식: 글자 수로 어림한 뒤 ±1.2초 안의 가장 가까운 무음(120ms 이상) 가운데로 옮긴다."""
    if len(unit) < 2:
        return []
    a = array('h', pcm)
    fr = RATE // 100
    quiet = [max(map(abs, a[i:i + fr])) < 500 for i in range(0, len(a) - fr, fr)]
    gaps, run = [], 0
    for k, q in enumerate(quiet + [False]):
        if q:
            run += 1
        else:
            if run >= 12:
                gaps.append(k - run // 2)
            run = 0
    est = [len(s['text']) / CHARS_PER_SEC[s['lang']] + 0.4 for s in unit]
    scale = len(quiet) / max(1, sum(est) * 100)
    t, out, last = 0.0, [], 0
    for k in range(len(unit) - 1):
        t += est[k] * 100 * scale
        near = [g for g in gaps if abs(g - t) <= 120 and g > last]
        c = min(near, key=lambda g: abs(g - t)) if near else max(int(t), last + 1)
        out.append(c / 100)
        last = c
    return out


JOIN = 0.5      # 같은 장면 안 요청 사이 쉼(초). 편지 앞뒤는 PAUSE['para'], 장면 사이는 PAUSE['scene']


def letter(unit):
    return unit[0]['lane'] not in ('dlg', 'narr')


def assemble(us, results, turns=True, tl=None):
    """캐시된 묶음 소리를 이어 붙인다. API를 쓰지 않는다. turns=False면 화자 전환 쉼을 넣지 않는다.
    tl에 목록을 주면 조각마다 시각(초)을 적는다(유튜브 화면 글자 싱크용)."""
    pcm = bytearray()
    scene = 1
    for k, (unit, paths) in enumerate(zip(us, results)):
        segs = unit if len(paths) == len(unit) else [unit[-1]]
        for seg, p in zip(segs, paths):
            with wave.open(str(p)) as w:
                a = trim(w.readframes(w.getnframes()))
            a = squash_gaps(a)
            if turns and len(unit) > 1:
                a = turn_pauses(a, unit)
            if tl is not None:
                t0, dur = len(pcm) / 2 / RATE, len(a) / 2 / RATE
                inner = unit if len(paths) == 1 else [seg]
                cuts = [0.0] + (marks(a, unit) if len(inner) > 1 else []) + [dur]
                for x, (b0, b1) in zip(inner, zip(cuts, cuts[1:])):
                    tl.append(dict(start=round(t0 + b0, 2), end=round(t0 + b1, 2), scene=scene,
                                   kind=x['kind'], who=x['who'], text=x['text'],
                                   **({'gloss': x['gloss']} if x.get('gloss') else {})))
                    if x['pause'] == 'scene' and x['kind'] != 'title':
                        scene += 1
            pcm += level(a)
            if seg['pause'] == 'scene':
                gap = PAUSE['scene']
            elif letter(unit) or (k + 1 < len(us) and letter(us[k + 1])):
                gap = PAUSE['para']
            else:
                gap = JOIN
            pcm += b'\0\0' * int(RATE * gap)
    return bytes(pcm)


def write_timeline(ch, tl):
    """장별 시간표: out/chNN.timeline.json(조각·장면 번호·뜻풀이)과 out/chNN.srt(유튜브 자막)."""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'ch{ch:02d}.timeline.json').write_text(json.dumps(tl, ensure_ascii=False, indent=1))
    def ts(x):
        ms = int(round(x * 1000))
        return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
    (OUT / f'ch{ch:02d}.srt').write_text(''.join(
        f'{i}\n{ts(x["start"])} --> {ts(x["end"])}\n{x["text"]}\n\n' for i, x in enumerate(tl, 1)))


def build_chapter(ch, budget, workers):
    us = units(ch)
    done = [0]

    def job(unit):
        paths = render_unit(unit, budget)
        with _lock:
            done[0] += 1
            print(f'  {ch}장 {done[0]}/{len(us)}', end='\r', flush=True)
        return paths

    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(job, us))
    tl = []
    pcm = assemble(us, results, tl=tl)
    OUT.mkdir(parents=True, exist_ok=True)
    write_timeline(ch, tl)
    wav, m4a = OUT / f'ch{ch:02d}.wav', OUT / f'ch{ch:02d}.m4a'
    with wave.open(str(wav), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(bytes(pcm))
    subprocess.run(['afconvert', '-f', 'm4af', '-d', 'aac', '-b', '64000', str(wav), str(m4a)], check=True)
    wav.unlink()
    rv = OUT / f'ch{ch:02d}_review.tsv'
    mine = [(u, why) for u, why in REVIEW if any(u is x for x in us)]
    if mine:
        rv.write_text(''.join(f'{why}\t{" / ".join(x["text"] for x in u)[:200]}\n' for u, why in mine))
        print(f'  ! {ch}장 들어 볼 곳 {len(mine)}개 → {rv.relative_to(ROOT)}')
    elif rv.exists():
        rv.unlink()
    usd, credits = spent()
    print(f'  {ch}장: {len(pcm) / 2 / RATE / 60:.1f}분 → {m4a.relative_to(ROOT)}  (누적 Gemini ${usd:.2f}, ElevenLabs {credits}자)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', action='store_true', help='요청 없이 조각·비용만 본다')
    ap.add_argument('--ch', type=int, nargs='*', help='장 번호(없으면 전체)')
    ap.add_argument('-v', action='store_true', help='조각 목록까지')
    ap.add_argument('--budget', type=float, default=6.5, help='Gemini 누적 비용 상한(달러). 넘으면 멈춘다')
    ap.add_argument('--workers', type=int, default=2)
    a = ap.parse_args()
    chs = a.ch or range(1, 31)
    if a.plan:
        plan(chs, a.v)
        return
    for ch in chs:
        try:
            build_chapter(ch, a.budget, a.workers)
        except (Budget, DailyLimit) as e:
            sys.exit(f'멈춤: {e}')


if __name__ == '__main__':
    main()
