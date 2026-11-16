"""장 음성을 Voicebox(로컬 Qwen3-TTS 복제)로 만들고 받아쓰기로 검수한다(AUDIOBOOK.md 0절).

  python3 audiobook/voicebox_book.py 1 --plan          # 생성 없이 조각·낭독 글·언어만
  python3 audiobook/voicebox_book.py 1 --only 12       # 앞 12조각만(시험)
  python3 audiobook/voicebox_book.py 1 2 3             # 장 전체

- 11-11 Mike: "오디오북 1-30은 전부 보이스박스에서 한다", "1-3장을 배포가능한 수준까지 반복해서 테스트 생성 검수".
- 원고 조각은 audiobook.py segments(). 조각 하나를 언어별 '토막'으로 나눈다: 한국어 서술 속 스페인어 낱말은
  같은 목소리로 스페인어로 따로 만들어 잇는다(한국어로 읽히면 '쾌리다'가 된다, 11-11 시험).
- 읽기 고침: voicebox/readings.tsv(글자 이름 h·ll, 숫자 등). 한국어 토막의 숫자는 한자어 수로 바꾼다.
- 장 제목은 "일 장." + 스페인어 제목으로 나눈다("1장. Hola."가 "한 장 콜라"로 읽혔다).
- 짧은 글("Hola.", "¿Agua?")은 Qwen이 빈 소리를 낸다. 앞에 짧은 문장(CARRIER)을 붙여 만든 뒤
  받아쓰기 낱말 시각으로 그 부분을 잘라 낸다.
- 검수: 토막마다 로컬 Whisper(turbo)로 받아써 낭독 글과 비교(일치율)하고 길이를 본다. 기준 미달이면
  시드·방식을 바꿔 다시 만들고, 끝까지 미달이면 가장 나은 것을 쓰고 보고서에 남긴다.
- 캐시: cache_vb/(토막·시드·방식별 wav와 검수 결과 json). 출력: out_vb/chNN.m4a, .timeline.json, .qa.tsv.
- 생성은 Mike 승인 뒤에 한다(로컬이라 비용은 없다).
"""
import argparse
import os
import difflib
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.request
import wave
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import audiobook as A  # noqa: E402

API = 'http://localhost:17493'
VB = A.CONF / 'voicebox'
CACHE = A.CONF / 'cache_vb'
OUTV = A.CONF / 'out_vb'
ALIAS = {'mama': 'madre', 'megafonia': 'taquillera'}
CROWD = {'vecinos': ['montse', 'jaume', 'pau', 'senyora'], 'todos': ['vale', 'pau', 'sofia', 'luca']}
PAUSE = dict(line=0.5, para=0.8, scene=2.0)
JOIN = dict(stop=0.28, mid=0.07)          # 토막 사이 쉼: 문장 끝 / 문장 가운데
# --pace: 낭독 호흡(11-12 Mike "너무 다급하게 느껴진다"). 서술이 8.1자/초로 샘플(6.5자/초)보다 25% 빨랐다.
PACE = dict(pause=dict(line=0.75, para=1.15, scene=2.6), join=dict(stop=0.5, mid=0.1),
            breath=(0.15, 0.25), tempo=0.95)   # 토막 속 0.15초 넘는 쉼에 0.25초를 더한다. 장 전체 속도 0.95
# CosyVoice 서술용(11-13 Mike "1장 엄청 느리다"): 낱말 속 발음이 5.17자/초로 원래 Gemini(5.88)보다 12% 느렸다.
# 서술 토막만 1.08배, 장 전체 속도는 그대로, 쉼은 줄인다. 제목 뒤 쉼은 따로.
PACE_COSY = dict(pause=dict(line=0.55, para=0.9, scene=1.8), join=dict(stop=0.4, mid=0.1),
                 narr_speed=1.08, tempo=1.0, title=1.2)
CARRIER = {'es': 'Eso es todo.', 'ko': '그게 전부다.'}
TRIES = [('plain', 7), ('plain', 11), ('carrier', 7), ('carrier', 11), ('plain', 23), ('carrier', 23), ('plain', 37)]
PASS = {'ko': 0.85, 'es': 0.82}          # ko는 자모 단위 비교
SHORT = 7                                  # 글자(공백·부호 빼고) 이 이하는 처음부터 carrier
CATALAN = re.compile(r"[àèòï·]|\b(adéu|bon dia|gràcies|carrer|plaça|tancat|serralleria|si us plau"
                     r"|rrellot\w*|rreyud\w*|rreyód\w*|grásia|akét|egsístesh|tumáket|munchuík|paralél|póble|plása|gótic|tancát|vacánses|serrallería|reyoy\w*|reyóy\w*|bon día)\b", re.I)   # 소리 표기도(readings.tsv)


# ── 낭독 글 ───────────────────────────────────────────
SINO = '영일이삼사오육칠팔구'


def sino(n):
    if n == 0:
        return '영'
    out = ''
    for unit, name in ((1000, '천'), (100, '백'), (10, '십'), (1, '')):
        d, n = divmod(n, unit)
        if d:
            out += ('' if d == 1 and name else SINO[d]) + name
    return out


NATIVE = ['', '한', '두', '세', '네', '다섯', '여섯', '일곱', '여덟', '아홉', '열', '열한', '열두']


def hour(h):
    return (NATIVE[h] if 0 < h <= 12 else sino(h)) + ' 시'


def ko_digits(s):
    s = re.sub(r'(?<!\d)10월', '시월', s); s = re.sub(r'(?<!\d)6월', '유월', s)   # 11-14: 십월→시월
    # 시각은 고유어로: '10:00'이 '십:영', '9시'가 '구시'로 읽혔다(11-13 4–30장 점검)
    s = re.sub(r'(\d{1,2}):(\d{2})', lambda m: hour(int(m.group(1))) + ('' if m.group(2) == '00' else f' {sino(int(m.group(2)))} 분'), s)
    s = re.sub(r'(\d{1,2})\s*시(?!간|대|장|작|절|티|도|민)', lambda m: hour(int(m.group(1))), s)
    return re.sub(r'\d+', lambda m: sino(int(m.group(0))), s)


def readings(ch):
    p = VB / 'readings.tsv'
    rows = [l.split('\t') for l in p.read_text().split('\n') if l and not l.startswith('#')] if p.exists() else []
    return [(a, b) for c, a, b in rows if c == '*' or int(c) == ch]


LAT = r"[¿¡]?[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’·\-]*"
RUN = re.compile(rf"{LAT}(?:[ ,]+{LAT})*[.?!…:;]*")


KO_GLUE = [('였', '이었'), ('라고', '이라고'), ('란', '이란'), ('라는', '이라는'), ('랑', '이랑'), ('라서', '이라서')]


V5 = False   # --v5(11-16 3장 시험): 조사 붙은 낱말 한글 표기·윤하 스페인어 한국어 기준 녹음·쉼 줄임·꼬리 검사


def hangul_es():
    f = VB / 'hangul_es.tsv'
    if not f.exists():
        return {}
    return dict(l.split('\t')[:2] for l in f.read_text().splitlines() if l.strip() and not l.startswith('#'))


def glue_ko(t, after_es):
    """스페인어 낱말에 바로 붙은 한국어 서술격·인용 조사(vale였다, eso라고)는 엔진이 머리에 'ㅎ'·'ㅌ'를 붙여
    '허였다·토'처럼 읽었다(11-14 Mike '토 보스 허였다'). TTS 글만 '이었다·이라고'로 바꾼다. 자막·원고는 그대로."""
    if after_es and t and not t[0].isspace():
        for a, b in KO_GLUE:
            if t.startswith(a):
                return b + t[len(a):]
    return t


def pieces(text):
    """낭독 글 → [(언어, 글)]. ⟦es:…⟧·⟦ko:…⟧ 표시는 그대로 따른다."""
    out = []
    for m in re.finditer(r'⟦(es|ko):([^⟧]*)⟧|([^⟦]+)', text):
        if m.group(1):
            out.append([m.group(1), m.group(2)])
            continue
        chunk = m.group(3)
        if not re.search('[가-힣]', chunk):
            out.append(['es', chunk])
            continue
        k, han, HAN = 0, False, (hangul_es() if V5 else {})
        for r in RUN.finditer(chunk):
            out.append(['ko', glue_ko(chunk[k:r.start()], k > 0 and not han)])
            w = r.group(0)
            h = HAN.get(w.strip().rstrip('.,;:')) if re.match(r"[’”'\"]?[가-힣]", chunk[r.end():]) else None
            if h:                                  # --v5: 'yave를' → '야베를'을 한국어 토막으로(조사는 원고 그대로)
                out.append(['ko', h])
            else:
                out.append(['es', w])
            han = bool(h)
            k = r.end()
        out.append(['ko', glue_ko(chunk[k:], k > 0 and not han)])
    res = []
    for lang, t in out:                    # 글자 없는 토막(따옴표·쉼표)은 앞 토막에 붙인다
        if not re.search(r'\w', t):
            if res:
                res[-1][1] += t
            continue
        if res and res[-1][0] == lang:
            res[-1][1] += t
        else:
            res.append([lang, t])
    fixed = []
    for lang, t in res:
        t = re.sub(r'\s+', ' ', t).strip().strip('‘’“”\'"«»()').strip()
        t = re.sub(r'^[,.;:·]+\s*', '', t)
        if lang == 'ko':
            t = ko_digits(t)
            # 문장이 끝난 뒤 스페인어 낱말 앞에 남은 짧은 꼬리("고맙습니다. 앱은")는 Qwen이 빼먹는다(11-11).
            # 꼬리를 따로 떼어 짧은 글 방식(carrier)으로 만든다.
            m = re.match(r'(.*[.?!…’”])\s+([^.?!…]{3,15})$', t)   # 2자 이하 꼬리는 떼면 더 어색(11-14)
            if m and re.search(r'\w', m.group(2)) and not V5:      # CosyVoice는 꼬리를 빼먹지 않는다. 떼면 억양이 끊긴다(11-16)
                fixed += [(lang, m.group(1)), (lang, m.group(2))]
                continue
        if re.search(r'\w', t):
            fixed.append((lang, t))
    return fixed


def spoken(seg, ch, tight=False):
    if seg['kind'] == 'title':
        n, es = re.match(r'(\d+)장\. (.*)$', seg['text']).groups()
        es = re.sub(r'([?!])\.$', r'\1', es)
        # CosyVoice는 '일 장.'을 '이이일~ 장'으로 늘인다(1.2초). 붙여 쓰면 0.7초(11-13 Mike)
        return [('ko', f'{sino(int(n))}{"" if tight else " "}장.'), ('es', es)]
    t = seg['text']
    for a, b in readings(ch):
        t = t.replace(a, b)
    out = pieces(t)
    if True:                               # 스페인어 숫자는 글로 풀어 엔진마다 다르게 읽지 않게(11-13). 11-14 Mike: 1–3장도 같게
        def es_words(x):
            x = re.sub(r'(\d{1,2}):(\d{2})', lambda m: es_num(int(m.group(1))) + ('' if m.group(2) == '00' else ' y ' + es_num(int(m.group(2)))), x)
            return re.sub(r'\d+', lambda m: es_num(int(m.group(0))), x)
        out = [(l, es_words(x) if l == 'es' else x) for l, x in out]
    if V5 and seg['who'] == 'yunha':       # 한국어 기준 녹음은 'Yunha'를 '융가'로 읽는다. Yunja → '윤하'(11-16 후보 시험)
        out = [(l, x.replace('Yunha', 'Yunja') if l == 'es' else x) for l, x in out]
    return out


# ── Voicebox ─────────────────────────────────────────
def profiles():
    return {k: v['profile_id'] for k, v in json.loads((VB / 'profiles.json').read_text()).items()}


def voices_of(seg):
    w = seg['who']
    return CROWD.get(w) or [ALIAS.get(w, w)]


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return r.read() if path.startswith('/audio/') else json.loads(r.read() or 'null')


# ── 다른 엔진(11-13 시험): CosyVoice 3, IndexTTS-2.5. pid가 'cosy|목소리|지시' / 'index|목소리|감정json|세기'면 작업자로 보낸다
LAB = Path.home() / 'Developer' / 'tts-lab'
WORKERS = {'cosy': (LAB / 'CosyVoice' / '.venv' / 'bin' / 'python', 'cosy_worker.py'),
           'index': (LAB / 'mlx-indextts2' / '.venv' / 'bin' / 'python', 'index_worker.py')}
_procs = {}
# 11-14 전수조사로 다시 씀: 낱말 경계(\b)로 겹침 막기(explain→plain, slow→low, already→read, finally→final),
# 부정어 지우기(not angry→angry 막기), 'beginner'는 감정이 아니라 빼기, 무표정 농담(deadpan)이면 happy 빼기.
# 1–30장 모두 같은 규칙(전 장을 다시 만든다).
EMO = [('happy', r'\b(laugh|playful|cheer|delight|pleasant|happy|bright|excit|teas|amused|smil|warm|friendly|pleased|proud|fond'
                 r'|eager|relie[fv]|grateful|approv|easygoing|tender|hope|affection|caring|joke)\w*'),
       ('melancholic', r'\b(sad|melanch|wistful|final\b|tired|lonely|nostalg|tear|moved|hurt|grief|sorrow|longing|bittersweet'
                       r'|holding back|sigh|regret|overwhelm|unsteady|breaking|wet eyes|rueful|distant)\w*'),
       ('surprised', r'\b(surpris|curious|cutting in|astonish|amazed|shock|puzzled|impressed|wonder|stunned|shaken|realiz|confused)\w*'),
       ('angry', r'\b(angry|annoy|irritat|snap|scold|furious|impatien|shout|raising .{0,10}voice|upset|protest|defensive|bitter|accus)\w*'),
       ('afraid', r'\b(afraid|nervous|anxious|worr|concern|scared|unsure|hesita|shy|sheepish|awkward|frighten|alarm|panic|plead'
                  r'|vulnerable|startl|fluster|embarrass|urgent)\w*'),
       ('calm', r'\b(quiet|gentl|hush|shrug|unbother|casual|calm|slow|explain|teach|read\b|reading|soft|kind|patient|brisk|purpose'
                r'|plain|low|dry|deadpan|neutral|serious|steady|polite|sincere|honest|simple|practical|routine|businesslike'
                r'|unhurried|thoughtful|careful|flat|matter|curt)\w*')]
EMO_WIDE = {}                                   # 예전 4장 이후 확장 목록은 위로 합침
NEG = re.compile(r"\b(not|no|never|unaware of|without)\s+((?:her|his|their|the|a|any)\s+)?(\w+)", re.I)


def emotion_of(note, alpha=0.45, wide=True):
    """대본 지시(영어) → IndexTTS 감정 비율. 세게 걸면 널뛰므로 기본 세기 0.45."""
    note = NEG.sub(' ', note or '')
    w = {k: len(re.findall(rx, note, re.I)) for k, rx in EMO}
    if re.search(r'deadpan|straight face', note, re.I):
        w['happy'] = 0
    w = {k: v for k, v in w.items() if v}
    if not w:
        return None, 0.0
    n = sum(w.values())
    return {k: round(v / n, 2) for k, v in w.items()}, alpha


def ref_of(voice, short=False, idx=False):
    """기준 녹음. short: 10초 안팎(voicebox/ref/short) — CosyVoice는 27초 기준이면 2–5배 느리다.
    idx: IndexTTS용 15초 안쪽 판(voicebox/ref/idx). IndexTTS는 앞 15초만 쓴다(11-14 전수조사).
    short가 없으면 idx 판을 쓴다(cosy가 한국어 대사도 읽게 됨)."""
    base = {'narr1': 'narr'}.get(voice, voice)
    r = VB / 'ref'
    for d, use in ((r / 'short', short), (r / 'idx', short or idx)):
        if use and (d / f'{base}_01.wav').exists():
            return str(d / f'{base}_01.wav'), (d / f'{base}_01.txt').read_text().strip()
    return str(r / f'{base}_01.wav'), (r / f'{base}_01.txt').read_text().strip()


_refsig = {}


def refsig(pid):
    """캐시 키에 넣을 기준 녹음 지문. 기준 녹음을 바꾸면 옛 캐시를 쓰지 않는다(11-14)."""
    if '|' not in pid:
        return ''
    eng, voice = pid.split('|')[:2]
    k = (eng, voice)
    if k not in _refsig:
        wav, txt = ref_of(voice, short=eng == 'cosy', idx=eng == 'index')
        _refsig[k] = hashlib.md5(Path(wav).read_bytes() + txt.encode()).hexdigest()[:8]
    return '|r' + _refsig[k]


def readj(p, timeout=600):
    """작업자 표준출력에서 JSON 한 줄(라이브러리 로그 줄은 건너뛴다). timeout초 안에 답이 없으면 {}(11-14)."""
    import select
    end = time.time() + timeout
    while True:
        left = end - time.time()
        if left <= 0 or not select.select([p.stdout], [], [], left)[0]:
            return {}
        line = p.stdout.readline()
        if not line:
            return {}
        if line.startswith('{'):
            try:
                return json.loads(line)
            except ValueError:
                pass


_lock = None
_jobs = {}


def gen_lock():
    """엔진 작업자를 쓰는 프로세스는 한 번에 하나만(11-14: 두 파이프라인이 겹쳐 116 GB → 맥 멈춤).
    다른 프로세스가 쓰고 있으면 끝날 때까지 기다린다."""
    global _lock
    if _lock is None:
        import fcntl
        _lock = open(LAB / 'gen.lock', 'w')
        try:
            fcntl.flock(_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('  다른 생성 작업이 끝나기를 기다립니다(tts-lab/gen.lock)', file=sys.stderr, flush=True)
            fcntl.flock(_lock, fcntl.LOCK_EX)


def rss_gb(pid):
    """작업자 실제 메모리(GB). ps의 rss는 MPS·MLX 통합 메모리를 거의 못 잡아(1.5 GB vs 실제 9.8 GB) footprint를 쓴다(11-14)."""
    out = subprocess.run(['footprint', str(pid)], capture_output=True, text=True).stdout
    m = re.search(r'phys_footprint:\s*([\d.]+)\s*(KB|MB|GB)', out)
    if not m:
        out = subprocess.run(['ps', '-o', 'rss=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
        return int(out) / 1048576 if out else 0.0
    return float(m.group(1)) / {'KB': 1048576, 'MB': 1024, 'GB': 1}[m.group(2)]


def worker(eng):
    gen_lock()
    p = _procs.get(eng)
    _jobs[eng] = _jobs.get(eng, 0) + 1
    if p is not None and p.poll() is None and (_jobs[eng] > 60 or rss_gb(p.pid) > 14):
        p.terminate()                                # 작업자가 불어나면 새로 띄운다(11-14)
        try:
            p.wait(30)
        except subprocess.TimeoutExpired:
            p.kill(); p.wait()
        _jobs[eng] = 1
    if p is None or p.poll() is not None:
        py, script = WORKERS[eng]
        p = subprocess.Popen([str(py), str(Path(__file__).resolve().parent / 'engines' / script)], text=True,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open(LAB / f'{eng}_worker.log', 'a'))
        if readj(p).get('ready') is not True:
            raise RuntimeError(f'{eng} 작업자가 뜨지 않음(로그 {LAB}/{eng}_worker.log)')
        _procs[eng] = p
    return p


def chunks(text, limit=110):
    """긴 글을 문장 끝에서 limit자 안쪽 덩이로. IndexTTS는 몬세 편지(200자)에서 거의 무음을 냈다(11-13)."""
    out = []
    sents = []
    for sent in re.split(r'(?<=[.?!:…»])\s+', text.strip()):
        # 한 문장이 limit보다 길면 쉼표에서 더 나눈다. 못 나누면 그대로(24장에서 무한 반복으로 멈췄다, 11-14)
        sents += re.split(r'(?<=[,;])\s+', sent) if len(sent) > limit else [sent]
    for sent in sents:
        if out and len(out[-1]) + 1 + len(sent) <= limit:
            out[-1] += ' ' + sent
        else:
            out.append(sent)
    return out


def eng_synth(pid, text, lang, seed):
    if pid.startswith('index|') and len(text) > 110 and len(chunks(text)) > 1:
        parts = [eng_synth(pid, t, lang, seed) for t in chunks(text)]
        if not all(parts):
            return b''
        gap = b'\0\0' * int(A.RATE * 0.3)
        return gap.join(A.trim(x) for x in parts)
    eng, voice, *rest = pid.split('|')
    ref, ref_text = ref_of(voice, short=eng == 'cosy', idx=eng == 'index')
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / 'o.wav'
        job = dict(voice=voice, text=text, ref=ref, ref_text=ref_text, seed=seed, out=str(out), lang=lang)
        if eng == 'cosy':
            job['instruct'] = rest[0] if rest else ''
        else:
            job['emotion'] = json.loads(rest[0]) if rest and rest[0] else None
            job['alpha'] = float(rest[1]) if len(rest) > 1 else 0.6
        p = worker(eng)
        p.stdin.write(json.dumps(job, ensure_ascii=False) + '\n'); p.stdin.flush()
        r = readj(p, timeout=180 + 2 * len(text))
        if not r:                                   # 멈춘 작업자는 버리고 다음에 새로 띄운다
            p.kill(); _procs.pop(eng, None)
        if not r.get('ok') or not out.exists():
            print(f'  ! {eng} 실패: {r.get("err")}', file=sys.stderr)
            return b''
        return pcm_of(out)


def synth(pid, text, lang, seed):
    """Voicebox 한 번 → 24 kHz 모노 pcm(빈 소리면 b'')."""
    if '|' in pid:
        return eng_synth(pid, text, lang, seed)
    r = call('POST', '/generate', {'profile_id': pid, 'text': text, 'language': lang, 'seed': seed,
                                   'engine': 'qwen', 'model_size': '1.7B', 'normalize': True})
    gid = r['id']
    while r.get('status') not in ('completed', 'failed', 'error'):
        time.sleep(1)
        r = call('GET', f'/history/{gid}')        # /generate/{id}/status는 SSE 스트림이라 history로 본다
    if r.get('status') != 'completed':
        return b''
    raw = call('GET', f'/audio/{gid}')
    if len(raw) <= 100:
        return b''
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d) / 'in.wav', Path(d) / 'out.wav'
        src.write_bytes(raw)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-ac', '1', '-ar', str(A.RATE), str(dst)], check=True)
        return pcm_of(dst)


def pcm_of(path):
    with wave.open(str(path)) as w:
        return w.readframes(w.getnframes())


def save(path, pcm):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(A.RATE); w.writeframes(pcm)


# ── 받아쓰기 ─────────────────────────────────────────
_W = None


def whisper_model():
    global _W
    if _W is None:
        import warnings
        warnings.filterwarnings('ignore')
        import whisper
        _W = whisper.load_model('turbo')
    return _W


def hear(pcm, lang, words=False):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'h.wav'
        save(p, pcm)
        r = whisper_model().transcribe(str(p), language=lang, fp16=False, word_timestamps=words,
                                       condition_on_previous_text=False)
    if words:
        return [w for s in r['segments'] for w in s.get('words', [])]
    return r['text'].strip()


ES1 = 'cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciséis diecisiete dieciocho diecinueve veinte'.split()
ES10 = {3: 'treinta', 4: 'cuarenta', 5: 'cincuenta', 6: 'sesenta', 7: 'setenta', 8: 'ochenta', 9: 'noventa'}
ES100 = {1: 'ciento', 2: 'doscientos', 3: 'trescientos', 4: 'cuatrocientos', 5: 'quinientos', 6: 'seiscientos',
         7: 'setecientos', 8: 'ochocientos', 9: 'novecientos'}


def es_num(n):
    """받아쓰기가 숫자로 적은 것을 글로(0–999). 'tres'를 '3'으로 적어 미달이 났다(11-12)."""
    if n <= 20:
        return ES1[n]
    if n < 30:
        return 'veinti' + ES1[n - 20]
    if n < 100:
        t, u = divmod(n, 10)
        return ES10[t] + (' y ' + ES1[u] if u else '')
    if n < 1000:
        h, r = divmod(n, 100)
        return ('cien' if n == 100 else ES100[h]) + (' ' + es_num(r) if r else '')
    if n < 10000:                          # 연도(1978 → mil novecientos setenta y ocho)
        k, r = divmod(n, 1000)
        return ('mil' if k == 1 else es_num(k) + ' mil') + (' ' + es_num(r) if r else '')
    return str(n)


def jamo(s):
    """한글을 자모로 풀고, 소리가 같은 모음(ㅐ/ㅔ, ㅒ/ㅖ, ㅙ/ㅚ/ㅞ)을 하나로. '내'와 '네'는 받아쓰기로 못 가른다."""
    V = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'
    same = {'ㅐ': 'ㅔ', 'ㅒ': 'ㅖ', 'ㅙ': 'ㅞ', 'ㅚ': 'ㅞ'}
    out = []
    for c in s:
        k = ord(c) - 0xAC00
        if 0 <= k < 11172:
            v = V[k % 588 // 28]
            out += [chr(0x1100 + k // 588), same.get(v, v)] + ([chr(0x11A7 + k % 28)] if k % 28 else [])
        else:
            out.append(c)
    return ''.join(out)


def norm(s, lang):
    if lang == 'ko':
        s = re.sub(r'(\d)\s*kg\b', r'\1킬로', s)          # Whisper는 '이백 그램'을 '200g'으로 적는다
        s = re.sub(r'(\d)\s*g\b', r'\1그램', s)
        s = re.sub(r'\b([1-9])\s*(개|명|살|마리|시간|번)', lambda m:
                   ['한', '두', '세', '네', '다섯', '여섯', '일곱', '여덟', '아홉'][int(m.group(1)) - 1] + ' ' + m.group(2), s)
        s = jamo(ko_digits(s))
    else:
        s = re.sub(r'\d+', lambda m: es_num(int(m.group(0))), s)
        s = s.lower().replace('ll', 'y')                       # 소리 표기 yave ↔ 받아쓰기 llave(11-14)
        s = re.sub(r'\b(eme|m)\b', 'eme', s)
        s = re.sub(r'\b(ese|s)\b', 'ese', s)
    s = unicodedata.normalize('NFKD', s.lower())
    return ''.join(c for c in s if c.isalnum() and not unicodedata.combining(c))


def score(text, heard, lang):
    a, b = norm(text, lang), norm(heard, lang)
    return difflib.SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def cut_carrier(pcm, lang):
    """carrier 문장 뒤의 진짜 글만 남긴다. 못 자르면 b''."""
    ws = hear(pcm, lang, words=True)
    n = len(CARRIER[lang].split())
    if len(ws) <= n:
        return b''
    lo, hi = ws[n - 1]['end'] - 0.06, ws[n]['start'] + 0.03
    a = array('h', pcm)
    fr = int(A.RATE * 0.01)
    best, at = None, int(hi * A.RATE)
    for k in range(int(lo * A.RATE), int(hi * A.RATE) - fr, fr // 2):
        e = sum(abs(x) for x in a[max(0, k):k + fr])
        if best is None or e < best:
            best, at = e, k
    a = a[at:]
    for k in range(min(len(a), int(A.RATE * 0.012))):     # 자른 자리 딸깍 소리 방지
        a[k] = int(a[k] * k / (A.RATE * 0.012))
    return a.tobytes()


# ── 토막 하나 만들기 + 검수 ────────────────────────────
def expect(text, lang):
    return len(text) / A.CHARS_PER_SEC[lang]


def untail(pcm, lang):
    """마지막 낱말 뒤 쉼 다음에 붙는 소리를 잘라낸다. IndexTTS가 끝에 짧은 잡음 덩어리를 붙였다(11-13)."""
    ws = hear(pcm, lang, words=True)
    if not ws:
        return pcm
    a = array('h', pcm)
    fr = int(A.RATE * 0.02)
    thr = max(150, int(max(map(abs, a)) * 0.03))   # 절대값 400 대신 최대값의 3%(여린 끝자음 보호)
    k = max(0, int((ws[-1]['end'] - 0.05) * A.RATE)) // fr * fr
    run = 0
    while k + fr <= len(a):
        run = run + 1 if max(map(abs, a[k:k + fr])) < thr else 0
        if run * 0.02 >= 0.16:                   # 0.16초 조용하면 말이 끝난 것
            cut = k + fr - int(A.RATE * 0.16) + int(A.RATE * 0.15)
            if len(a) - cut > A.RATE * 1.0:      # 1초 넘게 잘라야 하면 Whisper가 끝을 놓친 것 → 자르지 않음
                return pcm
            return a[:cut].tobytes()
        k += fr
    return pcm


def drop_tail_bursts(pcm):
    """말이 끝나고 0.3초 넘게 쉰 뒤 붙는 짧은(0.35초 미만)·작은 소리 덩어리를 뗀다. Whisper에 기대지 않는다.
    11-14: 2장 Vale '¿Y vos?' 뒤 1초 쉼 + 0.15초 잡음이 untail의 1초 상한에 걸려 남았다."""
    a = array('h', pcm)
    fr = int(A.RATE * 0.01)
    lv = [max(map(abs, a[i:i + fr]), default=0) for i in range(0, len(a) - fr + 1, fr)]
    if not lv:
        return pcm
    peak = max(lv)
    act = [x > peak * 0.01 for x in lv]                       # 최대값보다 40 dB 아래면 조용함
    runs, i = [], 0
    while i < len(act):
        if act[i]:
            j = i
            while j < len(act) and (act[j] or any(act[j:j + 25])):   # 0.25초 안 틈은 한 덩어리
                j += 1
            runs.append((i, j)); i = j
        else:
            i += 1
    while len(runs) > 1:
        (s0, e0), (s1, e1) = runs[-2], runs[-1]
        if (s1 - e0) >= 30 and (e1 - s1) < 35 and max(lv[s1:e1]) < peak * 0.5:
            runs.pop(); cut = min(len(a), (e0 + 10) * fr)
            a = a[:cut]
        else:
            break
    return a.tobytes()


def attempt(pid, voice, text, lang, mode, seed):
    key = hashlib.sha1(f'{pid}{refsig(pid)}|{lang}|{seed}|{mode}|{text}'.encode()).hexdigest()[:16]
    wav, meta = CACHE / f'{key}.wav', CACHE / f'{key}.json'
    if meta.exists():
        m = json.loads(meta.read_text())
        m['score'] = round(score(text, m['heard'], lang), 3)     # 비교 방식이 바뀌어도 다시 받아쓰지 않는다
        m['key'] = key
        return (pcm_of(wav) if wav.exists() else b''), m
    pcm = synth(pid, (CARRIER[lang] + ' ' + text) if mode == 'carrier' else text, lang, seed)
    if pcm and mode == 'carrier':
        pcm = cut_carrier(pcm, lang)
    if pcm and pid.startswith('index|'):          # 끝 잡음은 IndexTTS 문제. 서술(cosy)에 걸면 문장이 잘릴 수 있다
        pcm = untail(pcm, lang)
        pcm = drop_tail_bursts(pcm)
    pcm = A.trim(pcm) if pcm else b''
    sec = len(pcm) / 2 / A.RATE
    heard = hear(pcm, lang) if sec >= 0.15 else ''
    m = dict(voice=voice, lang=lang, mode=mode, seed=seed, text=text, heard=heard, sec=round(sec, 2),
             score=round(score(text, heard, lang), 3), expect=round(expect(text, lang), 2),
             abrupt=bool(pcm) and lang == 'es' and abrupt_end(pcm))
    CACHE.mkdir(parents=True, exist_ok=True)
    if pcm:                                        # 소리가 없으면 캐시에 남기지 않는다(일시 실패가 영구 실패가 되지 않게)
        save(wav, pcm)
        meta.write_text(json.dumps(m, ensure_ascii=False))
    m['key'] = key
    return pcm, m


def abrupt_end(pcm):
    """마지막 소리가 -30 dBFS 넘는 데서 25 ms 안에 뚝 끊기면 True(스페인어 토막 끝 급정지, 11-14 전수조사)."""
    a = array('h', pcm)
    fr = int(A.RATE * 0.005)
    lv = [max(map(abs, a[i:i + fr]), default=0) for i in range(0, len(a) - fr, fr)]
    last = max((i for i, x in enumerate(lv) if x > 32767 * 0.0056), default=None)   # -45 dBFS
    if last is None:
        return False
    return any(x > 32767 * 0.0316 for x in lv[max(0, last - 5):last + 1])        # -30 dBFS


def ok(m):
    if m.get('abrupt'):
        return False
    lim = PASS[m['lang']]
    if m['lang'] == 'es' and CATALAN.search(m['text']):
        lim = 0.6                         # Qwen·Whisper 모두 카탈루냐어가 없다. 귀로 따로 본다
    if len(norm(m['text'], m['lang'])) <= 4:
        lim = min(lim, 0.74)
    e = max(m['expect'], 0.5)              # 낱말 하나는 예상 길이가 너무 짧게 나온다(taxi 0.29초)
    return m['score'] >= lim and e * 0.35 <= m['sec'] <= e * 2.6 + 0.6


def make(pid, voice, text, lang):
    tries = TRIES
    if len(norm(text, lang)) <= SHORT:
        tries = [t for t in TRIES if t[0] == 'carrier'] + [t for t in TRIES if t[0] == 'plain']
    best = None
    for mode, seed in tries:
        pcm, m = attempt(pid, voice, text, lang, mode, seed)
        m['tries'] = tries.index((mode, seed)) + 1
        if pcm and (best is None or m['score'] > best[1]['score']):
            best = (pcm, m)
        if pcm and ok(m) and not (V5 and pid.startswith('index|') and long_tail(pcm, lang)):
            m['pass'] = True
            return pcm, m
    if best is None:                               # 모두 실패해도 장을 멈추지 않는다. 0.5초 무음 + qa에 기록
        print(f'  ! 소리 없음: {voice} {text[:40]}', file=sys.stderr)
        return b'\0\0' * int(A.RATE * 0.5), dict(voice=voice, lang=lang, mode='-', seed=0, text=text, heard='',
                                                  sec=0.5, score=0.0, expect=0, err='no audio', tries=len(tries), **{'pass': False})
    best[1]['pass'] = False
    return best


def long_tail(pcm, lang):
    """마지막 낱말 뒤 1초 넘게 소리가 남으면 True(voicebox_audit '뒤 꼬리', 2장 ¿Y vos? 2.1초)."""
    ws = hear(pcm, lang, words=True)
    return bool(ws) and len(pcm) / 2 / A.RATE - ws[-1]['end'] > 1.0


def f0_of(pcm):
    import numpy as np
    a = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    fr, hop, out = int(A.RATE * 0.04), int(A.RATE * 0.01), []
    for i in range(0, len(a) - fr, hop):
        x = a[i:i + fr]
        if np.sqrt((x ** 2).mean()) < 0.02:
            continue
        x = x - x.mean()
        c = np.correlate(x, x, 'full')[fr - 1:]
        lo, hi = A.RATE // 400, A.RATE // 75
        k = lo + int(np.argmax(c[lo:hi]))
        if c[k] > 0.45 * c[0]:
            out.append(A.RATE / k)
    return float(np.median(out)) if len(out) > 5 else None


def near_pitch(pid, voice, text, lang, ref_f0, pcm, m):
    """서술 속 스페인어가 앞 한국어보다 2반음 넘게 높거나 낮으면 다른 시드 중 가장 가까운 합격본으로(11-16)."""
    import math
    f = f0_of(pcm)
    if not (ref_f0 and f) or abs(12 * math.log2(f / ref_f0)) <= 2:
        return pcm, m
    best = (abs(12 * math.log2(f / ref_f0)), pcm, m)
    for seed in (41, 53, 67):
        p2, m2 = attempt(pid, voice, text, lang, 'plain', seed)
        f2 = f0_of(p2) if p2 else None
        if p2 and f2 and ok(m2) and abs(12 * math.log2(f2 / ref_f0)) < best[0]:
            m2['pass'] = True
            best = (abs(12 * math.log2(f2 / ref_f0)), p2, m2)
        if best[0] <= 2:
            break
    return best[1], best[2]


def cap_pauses(pcm, most=0.6):
    """토막 안 문장 사이 쉼이 most초를 넘으면 most초로(1·2장 0.8–1.1초, 11-16)."""
    a = array('h', pcm)
    fr = int(A.RATE * 0.02)
    lv = [max(map(abs, a[i:i + fr]), default=0) for i in range(0, len(a), fr)]
    th = max(lv, default=0) * 0.03
    out, run = array('h'), []
    for i, x in enumerate(lv):
        blk = a[i * fr:(i + 1) * fr]
        if x < th:
            run.append(blk)
            continue
        if run:
            keep = int(most / 0.02)
            for b in (run if len(run) <= keep else run[:keep // 2] + run[-(keep - keep // 2):]):
                out.extend(b)
            run = []
        out.extend(blk)
    for b in run:
        out.extend(b)
    return out.tobytes()


def fade(pcm, sec=0.012):
    """토막 앞뒤를 아주 짧게 페이드. 잘라 붙인 자리의 딸깍 소리를 막는다(캐시된 토막에도 적용되게 조립 때 한다)."""
    a = array('h', pcm)
    n = min(len(a) // 2, int(A.RATE * sec))
    for k in range(n):
        a[k] = int(a[k] * k / n)
        a[-1 - k] = int(a[-1 - k] * k / n)
    return a.tobytes()


def speed(pcm, x):
    """음높이는 두고 빠르기만 x배."""
    with tempfile.TemporaryDirectory() as d:
        a, b = Path(d) / 'a.wav', Path(d) / 'b.wav'
        save(a, pcm)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(a), '-af', f'atempo={x}', '-ar', str(A.RATE), '-ac', '1', str(b)], check=True)
        return pcm_of(b)


def breathe(pcm, min_gap, add):
    """토막 속 쉼(문장·쉼표 사이)을 늘린다. 말소리는 건드리지 않는다."""
    a = array('h', pcm)
    fr = int(A.RATE * 0.02)
    quiet = [max(map(abs, a[k:k + fr])) < 400 for k in range(0, len(a) - fr, fr)]
    out, k, start = bytearray(), 0, None
    for i, q in enumerate(quiet + [False]):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if (i - start) * 0.02 >= min_gap and start > 0 and i < len(quiet):
                mid = (start + i) // 2 * fr
                out += a[k:mid].tobytes() + b'\0\0' * int(A.RATE * add)
                k = mid
            start = None
    return bytes(out) + a[k:].tobytes()


def mix(pcms, step=0.12):
    """군중: 여러 목소리를 조금씩 어긋나게 겹친다."""
    n = max(len(p) // 2 + int(i * step * A.RATE) for i, p in enumerate(pcms))
    out = [0] * n
    for i, p in enumerate(pcms):
        off = int(i * step * A.RATE)
        for k, x in enumerate(array('h', p)):
            out[off + k] += x // len(pcms) * 2
    return array('h', (max(-32767, min(32767, x)) for x in out)).tobytes()


# ── 장 ──────────────────────────────────────────────
# 11-14 Mike: 마르티가 택시 기사 목소리(Rafael)를 쓰게 되어, 택시 기사는 같은 목소리로 "살짝 방정맞게".
# 밝은 감정을 세게 + 반음 올리고 5% 빠르게(마르티와 구별).
# 같은 날 Mike: "방정은 폐기" → 택시 기사도 원래 말투 그대로. 틀은 남겨 둔다(비어 있으면 아무것도 안 함).
VOICE_TONE = {}


def tone_shift(pcm, semitones=0.0, tempo=1.0):
    """음높이를 semitones만큼, 빠르기를 tempo배로(ffmpeg asetrate+atempo)."""
    r = 2 ** (semitones / 12)
    with tempfile.TemporaryDirectory() as d:
        a, b = Path(d) / 'a.wav', Path(d) / 'b.wav'
        save(a, pcm)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(a), '-af',
                        f'asetrate={A.RATE * r:.0f},aresample={A.RATE},atempo={tempo / r:.5f}', '-ac', '1', str(b)], check=True)
        return pcm_of(b)


def spec(v, lang, s, eng_narr, eng_dlg, pid, ch=0):
    """토막 하나를 어느 엔진·목소리·말투로 만들지 → attempt()에 넘길 pid 문자열."""
    narr = s['who'] == 'narr' or v in ('narr', 'narr1')
    eng = eng_narr if narr else eng_dlg
    if V5 and lang == 'es' and v == 'yunha':   # 윤하 스페인어: 서술(한국어) 기준 녹음 → 한국인 억양, 서술과 같은 높이(11-16)
        if narr:
            return 'index|narr||0.45'
        e, a = emotion_of(s.get('note'))
        return f"index|narr|{json.dumps(e) if e else ''}|{a}"
    if eng == 'voicebox':
        return pid[v]
    if eng == 'index' and lang != 'es':
        return f"cosy|{v}||short2"          # IndexTTS는 한국어가 없다 → CosyVoice(스튜디오 기준 녹음, 11-14 Mike 결정)
    if eng == 'cosy':
        return f"cosy|{v}|{'' if narr else (s.get('note') or '')}|short2"
    e, a = emotion_of(s.get('note'))
    if v in VOICE_TONE:                    # 인물별 말투 덮어쓰기(11-14)
        e, a = VOICE_TONE[v]['emotion'], VOICE_TONE[v]['alpha']
    return f"index|{v}|{json.dumps(e) if e else ''}|{a}"


def pick(segs, sel):
    """--segs '50-58,63-71'(1부터) → 그 조각만."""
    keep = set()
    for part in sel.split(','):
        a, _, b = part.partition('-')
        keep |= set(range(int(a), int(b or a) + 1))
    return [s for i, s in enumerate(segs, 1) if i in keep]


# --glue(11-14 Mike): "스페인어와 한국어 조사는 좀 붙이고, 그 조사와 다음 한국어 사이를 띄우면".
# 'agua를 마시고'에서 agua→를 사이는 거의 붙이고, '를' 뒤에 조금 띄운다. 이미 만든 소리를 다시 잇기만 한다.
GLUE = dict(before=0.02, after=0.15, tail=0.06, head=0.02, thr=300)


def tighten(pcm, head=None, tail=None):
    """토막마다 끝에 0.3초를 남겨 두는데(A.trim), 붙일 자리에서는 그 여운을 줄인다."""
    a = array('h', pcm)
    thr = GLUE['thr']
    if tail is not None:
        j = next((k for k in range(len(a) - 1, -1, -1) if abs(a[k]) > thr), len(a) - 1)
        a = a[:min(len(a), j + int(A.RATE * tail))]
        n = min(len(a), int(A.RATE * 0.02))
        for k in range(n):
            a[len(a) - n + k] = int(a[len(a) - n + k] * (n - k) / n)
    if head is not None:
        i = next((k for k, x in enumerate(a) if abs(x) > thr), 0)
        a = a[max(0, i - int(A.RATE * head)):]
    return a.tobytes()


def glued(seg, ch, es_text, ko_text):
    """원고에서 스페인어 낱말 바로 뒤에 한글이 띄어쓰기 없이 붙어 있으면(조사) True."""
    t = seg['text']
    for a, b in readings(ch):
        t = t.replace(a, b)
    tail = re.sub(r'[.?!…:;,’”\'"]+$', '', es_text.strip())[-8:]
    return bool(tail) and bool(re.search(re.escape(tail) + r"[’”'\"]?" + re.escape(ko_text.strip()[:1]), t))


def after_particle(pcm, ko_text):
    """한국어 토막 첫 어절(조사) 끝에 GLUE['after']초 쉼을 넣는다. 받아쓰기 낱말 시각 근처의 가장 조용한 곳에서 자른다."""
    first, _, rest = ko_text.strip().partition(' ')
    if not rest or re.search(r'[.?!…,]$', first):
        return pcm
    words = hear(pcm, 'ko', words=True)
    if len(words) < 2 or len(re.sub(r'\W', '', words[0]['word'])) > len(re.sub(r'\W', '', first)) + 1:
        return pcm                         # 첫 낱말이 조사보다 길게 잡히면 자리를 모르니 그대로 둔다
    t = words[0]['end']
    a = array('h', pcm)
    fr = int(A.RATE * 0.01)
    lo, hi = max(0, int((t - 0.08) * A.RATE)), min(len(a) - fr, int((t + 0.08) * A.RATE))
    if hi <= lo:
        return pcm
    k = min(range(lo, hi, fr), key=lambda i: max(map(abs, a[i:i + fr])))
    return a[:k].tobytes() + b'\0\0' * int(A.RATE * GLUE['after']) + a[k:].tobytes()


def build(ch, only=None, plan=False, pace=False, narr='narr', tag='', eng_narr='voicebox', eng_dlg='voicebox', sel=None, glue=False):
    segs = A.segments(ch)
    if only:
        segs = segs[:only]
    if sel:
        segs = pick(segs, sel)
    pid = profiles()
    missing = sorted({v for s in segs for v in voices_of(s) if v not in pid})
    if missing:
        sys.exit(f'프로필 없음: {missing}')
    if plan:
        for i, s in enumerate(segs, 1):
            print(f'{i:3d} {s["kind"]:7s} {s["who"]:>10s}→{"+".join(voices_of(s))}')
            for lang, t in spoken(s, ch):
                print(f'      {lang} {t[:100]}')
        print(f'{ch}장: 조각 {len(segs)}개, 토막 {sum(len(spoken(s, ch)) for s in segs)}개')
        return
    cosy = pace and eng_narr == 'cosy'
    cfg = PACE_COSY if cosy else PACE
    pause, join = (cfg['pause'], cfg['join']) if pace else (PAUSE, JOIN)
    pcm, tl, qa, scene, t0 = bytearray(), [], [], 1, time.time()
    last_ko_f0 = None
    for i, s in enumerate(segs, 1):
        parts = []
        for j, (lang, text) in enumerate(spoken(s, ch, tight=cosy)):
            got = []
            for v in voices_of(s):
                if v == 'narr' and lang == 'es':
                    v = 'yunha'           # 같은 목소리(Seulki). narr 프로필은 한국어 샘플이라 스페인어를 못 읽는다(vale→Baila, 11-11)
                elif v == 'narr':
                    v = narr
                sp_ = spec(v, lang, s, eng_narr, eng_dlg, pid, ch)
                p, m = make(sp_, v, text, lang)
                if V5 and p and s['who'] == 'narr' and lang == 'es':
                    p, m = near_pitch(sp_, v, text, lang, last_ko_f0, p, m)
                if V5 and p and lang == 'ko' and sp_.startswith('cosy|'):
                    p = cap_pauses(p)
                if v in VOICE_TONE and p and lang == 'es':
                    p = tone_shift(p, VOICE_TONE[v]['semitones'], VOICE_TONE[v]['tempo'])
                if pace and lang == 'ko' and len(text) >= 20 and eng_narr == 'voicebox':
                    p = breathe(p, *PACE['breath'])   # CosyVoice는 문장 끝 쉼이 이미 길다. 더하면 '~다' 사이가 끊긴다(11-13 Mike)
                if cosy and s['who'] == 'narr' and p:
                    p = speed(p, PACE_COSY['narr_speed'])
                if V5 and p and s['who'] == 'narr' and lang == 'ko':
                    last_ko_f0 = f0_of(p) or last_ko_f0
                got.append(p)
                qa.append(dict(seg=i, piece=j + 1, who=s['who'], **m))
            p = fade(A.level(got[0] if len(got) == 1 else mix(got)))
            if os.environ.get('ROOM'):              # 인물별 같은 녹음실 맞추기 시험(11-14, room_fx.py)
                import room_fx
                p = fade(room_fx.room(p, voices_of(s)[0] if voices_of(s)[0] != 'narr' else narr))
            stuck = glue and parts and lang == 'ko' and parts_lang[-1] == 'es' and glued(s, ch, parts_text[-1], text)
            if stuck:
                p = tighten(after_particle(p, text), head=GLUE['head'])
                parts[-1] = tighten(parts[-1], tail=GLUE['tail'])
            if parts:
                gap = join['stop'] if re.search(r'[.?!…:]$', parts_text[-1]) else join['mid']
                if stuck:
                    gap = GLUE['before']
                parts.append(b'\0\0' * int(A.RATE * gap))
            else:
                parts_text, parts_lang = [], []
            parts.append(p)
            parts_text.append(text)
            parts_lang.append(lang)
        a = b''.join(parts)
        start = len(pcm) / 2 / A.RATE
        pcm += a
        tl.append(dict(start=round(start, 2), end=round(len(pcm) / 2 / A.RATE, 2), scene=scene, kind=s['kind'],
                       who=s['who'], text=s['text'], **({'gloss': s['gloss']} if s.get('gloss') else {})))
        if s['pause'] == 'scene' and s['kind'] != 'title':
            scene += 1
        nxt = segs[i] if i < len(segs) else None
        gap = pause.get(s['pause'], 0.5)
        if cosy and s['kind'] == 'title':
            gap = PACE_COSY['title']
        if s['kind'] in ('letter', 'address') or (nxt and nxt['kind'] in ('letter', 'address')):
            gap = max(gap, pause['para'])
        pcm += b'\0\0' * int(A.RATE * gap)
        bad = sum(1 for q in qa if not q['pass'])
        print(f'  {ch}장 {i}/{len(segs)}  미달 {bad}  {time.time() - t0:5.0f}초', flush=True)
    OUTV.mkdir(parents=True, exist_ok=True)
    name = f'ch{ch:02d}' + (f'_first{only}' if only else '') + tag
    tempo = cfg['tempo'] if pace else 1.0
    if tempo != 1.0:                       # 시간표도 같은 비율로 늘린다
        for t in tl:
            t['start'], t['end'] = round(t['start'] / tempo, 2), round(t['end'] / tempo, 2)
    (OUTV / f'{name}.timeline.json').write_text(json.dumps(tl, ensure_ascii=False, indent=1))
    cols = ['seg', 'piece', 'who', 'voice', 'lang', 'pass', 'score', 'sec', 'expect', 'mode', 'seed', 'tries', 'text', 'heard', 'key']
    (OUTV / f'{name}.qa.tsv').write_text('\t'.join(cols) + '\n' + ''.join(
        '\t'.join(str(q.get(c, '')).replace('\t', ' ') for c in cols) + '\n' for q in qa))
    wav, m4a = OUTV / f'{name}.wav', OUTV / f'{name}.m4a'
    save(wav, bytes(pcm))
    # 배포 음량: -19 LUFS, 최대 -3 dBTP(AAC로 1 dB 남짓 올라가 -4.0으로 맞춘다, 11-13 1장 -2.8)(오디오북 통상 기준). AAC 128k
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(wav), '-af', (f'atempo={tempo},' if tempo != 1.0 else '') + 'loudnorm=I=-19:TP=-4.0:LRA=11,alimiter=limit=0.6:level=disabled',  # loudnorm이 장 첫 0.3초에 넘침(11-13 1장 -1.1)
                    '-ar', '44100', '-c:a', 'aac', '-b:a', '128k', str(m4a)], check=True)
    # wav는 지우지 않는다: 마스터링(pilot_mix --vb)이 무손실 원본에서 한 번만 처리·인코딩한다(11-14 전수조사).
    # m4a는 들어보기용.
    bad = [q for q in qa if not q['pass']]
    print(f'\n  {ch}장: {len(pcm) / 2 / A.RATE / 60:.1f}분, 토막 {len(qa)}개 중 미달 {len(bad)}개, '
          f'{time.time() - t0:.0f}초 → {m4a.relative_to(A.ROOT)}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('chs', nargs='+', type=int)
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--only', type=int)
    ap.add_argument('--pace', action='store_true', help='낭독 호흡(쉼 늘리고 속도 0.95)')
    ap.add_argument('--narr', default='narr', help='서술 프로필 이름(profiles.json 키). narr1 = 샘플 하나 시험')
    ap.add_argument('--tag', default='', help='출력 이름 꼬리(비교본)')
    ap.add_argument('--engine-narr', default='voicebox', choices=['voicebox', 'cosy'], help='서술 엔진')
    ap.add_argument('--engine-dlg', default='voicebox', choices=['voicebox', 'cosy', 'index'], help='대사 엔진')
    ap.add_argument('--glue', action='store_true', help='스페인어 낱말+조사는 붙이고 조사 뒤를 띄운다(11-14)')
    ap.add_argument('--v5', action='store_true', help='11-16 시험: 낱말+조사 한글 표기, 윤하 스페인어 한국어 기준 녹음, 쉼 0.6초, 꼬리 검사')
    ap.add_argument('--segs', help="조각 번호만(1부터), 예: '50-58,63-71'")
    a = ap.parse_args()
    global V5
    V5 = a.v5
    for c in a.chs:
        build(c, a.only, a.plan, a.pace, a.narr, a.tag, a.engine_narr, a.engine_dlg, a.segs, a.glue)


if __name__ == '__main__':
    main()
