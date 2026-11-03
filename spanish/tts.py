#!/usr/bin/env python3
"""Gemini TTS 무료 한도로 대사 음성을 조금씩 만든다.

    GEMINI_API_KEY=... python3 spanish/tts.py            # 한도가 허락하는 만큼 만들고 멈춘다
    GEMINI_API_KEY=... python3 spanish/tts.py --max 5    # 이번에는 요청 5번까지만
    python3 spanish/tts.py --plan                        # 요청 없이 남은 일만 보여 준다

무료 등급의 TTS는 하루 요청 수가 아주 적다(10번 안팎이라는 보고가 있다). 그래서 대사를 한 줄씩
요청하지 않고, 한 장면에서 이어지는 대사 여러 줄(말하는 사람 둘까지)을 한 번에 읽게 한다.
줄 사이에 긴 쉼을 넣으라고 지시한 뒤, 돌아온 소리를 가장 긴 쉼 자리에서 잘라 줄마다 파일로 저장한다.
자르기가 미심쩍으면 그 묶음을 반으로 나눠 다음 요청에서 다시 만든다.

이미 만든 줄은 audio/es/<id>.mp3 로 남아 있으니 몇 번이고 다시 실행해도 된다.
하루 한도에 걸리면 저장하고 멈춘다. 한도는 미국 태평양 시간 자정(한국 시간 오후 4~5시)에 풀린다.
"""
import base64, json, os, re, subprocess, sys, time, urllib.error, urllib.request
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

API = 'https://generativelanguage.googleapis.com/v1beta'
MAX_LINES, MAX_CHARS = 14, 700        # 한 번에 읽힐 대사 묶음의 크기
FRAME = 0.01                           # 소리 분석 단위 10ms


class DailyLimit(Exception):
    pass


# ── 무엇을 만들어야 하나 ─────────────────────────────────────────────
def chapters():
    entries, forms = build.load_vocab()
    inline = build.Inline(forms, entries)
    return [build.parse_chapter(p, inline) for p in sorted(build.SRC.glob('ch*.txt'))]


def missing_chunks(chs):
    """장면마다 아직 소리가 없는 대사를 이어 붙여 묶음으로 만든다. 묶음 하나 = 요청 하나."""
    out = []
    for ch in chs:
        scene, chunk = 0, []

        def close():
            if chunk:
                out.append(dict(ch=ch['n'], scene=scene, lines=list(chunk)))
                chunk.clear()

        for b in ch['blocks']:
            if b['t'] == 'br':
                close(); scene += 1; continue
            if b['t'] != 'say' or not b.get('who'):
                continue
            if (build.AUDIO / f'{b["a"]}.mp3').exists():
                close(); continue
            who = {x['who'] for x in chunk} | {b['who']}
            if (len(who) > 2 or len(chunk) >= MAX_LINES
                    or sum(len(x['text']) for x in chunk) + len(b['plain']) > MAX_CHARS):
                close()
            chunk.append(dict(who=b['who'], text=b['plain'], a=b['a']))
        close()
    return out


# ── Gemini 호출 ─────────────────────────────────────────────────────
def call(path, body=None, key=None):
    url = f'{API}/{path}'
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def pick_model(key):
    if os.environ.get('GEMINI_TTS_MODEL'):
        return os.environ['GEMINI_TTS_MODEL']
    names, page = [], ''
    while True:
        r = call(f'models?pageSize=200{page}', key=key)
        names += [m['name'].split('/')[-1] for m in r.get('models', [])]
        if not r.get('nextPageToken'):
            break
        page = f'&pageToken={r["nextPageToken"]}'
    tts = [n for n in names if 'tts' in n]
    if not tts:
        sys.exit('TTS 모델을 찾지 못했습니다. GEMINI_TTS_MODEL 로 모델 이름을 지정하세요.')

    def rank(n):  # flash 우선, 그다음 버전이 높은 것
        v = [int(x) for x in re.findall(r'\d+', n)[:2]] or [0]
        return ('flash' in n, v, 'preview' not in n)
    return max(tts, key=rank)


def prompt(lines):
    who = []
    for x in lines:
        if x['who'] not in who:
            who.append(x['who'])
    v = [build.VOICES[w] for w in who]
    cast = ' '.join(f'{x["label"]} is {x["style"]}.' for x in v)
    head = ('Read the following lines aloud in Castilian Spanish from Spain '
            '(pronounce z and soft c as "th"), unless a speaker\'s description gives another accent. Speak clearly and a little slower than normal, '
            'for beginner learners. Leave a long pause of about two seconds after every line. '
            f'{cast}\n\n')
    if len(v) == 1:
        return head + '\n'.join(x['text'] for x in lines), v
    return head + '\n'.join(f'{build.VOICES[x["who"]]["label"]}: {x["text"]}' for x in lines), v


def synth(key, model, lines):
    text, v = prompt(lines)
    if len(v) == 1:
        speech = {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': v[0]['voice']}}}
    else:
        speech = {'multiSpeakerVoiceConfig': {'speakerVoiceConfigs': [
            {'speaker': x['label'], 'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': x['voice']}}}
            for x in v]}}
    body = {'contents': [{'parts': [{'text': text}]}],
            'generationConfig': {'responseModalities': ['AUDIO'], 'speechConfig': speech}}
    for attempt in range(4):
        try:
            r = call(f'models/{model}:generateContent', body, key)
            part = r['candidates'][0]['content']['parts'][0]['inlineData']
            rate = int(re.search(r'rate=(\d+)', part.get('mimeType', '')) .group(1)) \
                if 'rate=' in part.get('mimeType', '') else 24000
            return base64.b64decode(part['data']), rate
        except urllib.error.HTTPError as e:
            err = e.read().decode(errors='replace')
            if e.code == 429:
                if re.search(r'PerDay|per day|daily', err, re.I):
                    raise DailyLimit(err)
                m = re.search(r'"retryDelay":\s*"(\d+)', err)
                wait = int(m.group(1)) + 2 if m else 60
                print(f'    분당 한도 — {wait}초 기다림')
                time.sleep(wait)
                continue
            if e.code >= 500 and attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            raise RuntimeError(f'HTTP {e.code}: {err[:500]}')
        except (KeyError, IndexError) as e:
            raise RuntimeError(f'응답에 소리가 없습니다: {e}')
    raise DailyLimit('분당 한도가 계속 걸립니다')


# ── 소리 자르기 ─────────────────────────────────────────────────────
def split(pcm, rate, n, texts):
    """가장 긴 쉼 n-1 곳에서 잘라 n 조각을 돌려준다. 미심쩍으면 None."""
    s = array('h'); s.frombytes(pcm[:len(pcm) // 2 * 2])
    step = int(rate * FRAME)
    rms = []
    for i in range(0, len(s), step):
        f = s[i:i + step]
        rms.append((sum(x * x for x in f) / max(1, len(f))) ** .5)
    if not rms:
        return None
    thr = max(rms) * 0.035
    loud = [r > thr for r in rms]
    first = loud.index(True) if True in loud else 0
    last = len(loud) - loud[::-1].index(True) if True in loud else len(loud)
    gaps, i = [], first
    while i < last:
        if not loud[i]:
            j = i
            while j < last and not loud[j]:
                j += 1
            gaps.append((j - i, i, j))
            i = j
        else:
            i += 1
    if len(gaps) < n - 1:
        return None
    cuts = sorted(gaps, key=lambda g: -g[0])[:n - 1]
    if n > 1 and min(g[0] for g in cuts) * FRAME < 0.45:     # 줄 사이 쉼이라기엔 짧다
        return None
    bounds = [first] + [x for g in sorted(cuts, key=lambda g: g[1]) for x in (g[1], g[2])] + [last]
    pad = int(0.12 / FRAME)
    segs = []
    for k in range(n):
        a, b = bounds[2 * k], bounds[2 * k + 1]
        a, b = max(0, a - pad), min(len(rms), b + pad)
        segs.append(s[a * step:b * step].tobytes())
    # 조각 길이가 글자 수와 너무 어긋나면 잘못 자른 것
    total_chars = sum(len(t) for t in texts)
    total_sec = sum(len(x) for x in segs) / 2 / rate
    for seg, t in zip(segs, texts):
        expect = total_sec * len(t) / total_chars
        got = len(seg) / 2 / rate
        if not (0.33 * expect - 0.4 <= got <= 3 * expect + 0.6):
            return None
    return segs


def to_mp3(pcm, rate, out):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(rate), '-ac', '1',
                    '-i', 'pipe:', '-codec:a', 'libmp3lame', '-b:a', '48k', str(out)],
                   input=pcm, check=True)


def chapter_files(chs):
    """한 장의 대사가 모두 모이면 이어 붙인 장 전체 파일도 만든다 (출퇴근길에 듣기용)."""
    for ch in chs:
        ids = [b['a'] for b in ch['blocks'] if b['t'] == 'say' and b.get('who')]
        files = [build.AUDIO / f'{a}.mp3' for a in ids]
        out = build.AUDIO / f'ch{ch["n"]:02d}.mp3'
        if not ids or not all(f.exists() for f in files):
            continue
        if out.exists() and out.stat().st_mtime >= max(f.stat().st_mtime for f in files):
            continue
        lst = build.AUDIO / '.concat.txt'
        gap = build.AUDIO / '.gap.mp3'
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i',
                        'anullsrc=r=24000:cl=mono', '-t', '0.9', '-codec:a', 'libmp3lame', '-b:a', '48k',
                        str(gap)], check=True)
        lst.write_text(''.join(f"file '{f.name}'\nfile '{gap.name}'\n" for f in files))
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst),
                        '-codec:a', 'libmp3lame', '-b:a', '48k', str(out)], check=True)
        lst.unlink(); gap.unlink()
        print(f'  → {out.name}')


def main():
    args = sys.argv[1:]
    limit = int(args[args.index('--max') + 1]) if '--max' in args else 10 ** 6
    chs = chapters()
    queue = missing_chunks(chs)
    total = sum(len(c['lines']) for c in queue)
    print(f'남은 대사 {total}줄 · 예상 요청 {len(queue)}번')
    if '--plan' in args:
        for c in queue:
            who = sorted({x["who"] for x in c["lines"]})
            print(f'  {c["ch"]}장 장면{c["scene"]} · {len(c["lines"])}줄 · {", ".join(who)}')
        return
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not key:
        sys.exit('GEMINI_API_KEY 환경 변수에 API 키를 넣어 주세요.')
    model = pick_model(key)
    print(f'모델: {model}')
    build.AUDIO.mkdir(parents=True, exist_ok=True)

    made = asked = 0
    try:
        while queue and asked < limit:
            c = queue.pop(0)
            lines = c['lines']
            print(f'  {c["ch"]}장 장면{c["scene"]} · {len(lines)}줄 요청…')
            pcm, rate = synth(key, model, lines)
            asked += 1
            segs = split(pcm, rate, len(lines), [x['text'] for x in lines])
            if segs is None:
                if len(lines) == 1:      # 한 줄이면 자를 필요가 없다
                    segs = [pcm]
                else:
                    h = len(lines) // 2
                    print(f'    자르기가 미심쩍어 {h}줄 + {len(lines) - h}줄로 나눠 다시 요청합니다')
                    queue[:0] = [dict(c, lines=lines[:h]), dict(c, lines=lines[h:])]
                    continue
            for x, seg in zip(lines, segs):
                to_mp3(seg, rate, build.AUDIO / f'{x["a"]}.mp3')
                made += 1
    except DailyLimit:
        print('\n오늘 무료 한도가 끝났습니다. 한국 시간 오후 4~5시 이후에 다시 실행하세요.')
    finally:
        chapter_files(chs)
        left = sum(len(c['lines']) for c in missing_chunks(chs))
        print(f'이번에 만든 대사 {made}줄 · 요청 {asked}번 · 남은 대사 {left}줄')
        subprocess.run([sys.executable, str(build.ROOT / 'build.py'), '--web-only'],
                       check=True, stdout=subprocess.DEVNULL)
        print('→ es.html 갱신')


if __name__ == '__main__':
    main()
