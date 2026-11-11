"""장 음성을 Voicebox(로컬 Qwen3-TTS 복제)로 만든다(AUDIOBOOK.md 0절, 11-11 Mike: "오디오북 1-30은 전부 보이스박스에서 한다").

  python3 audiobook/voicebox_book.py 1 --plan          # 요청 없이 조각·프로필·글자 수만
  python3 audiobook/voicebox_book.py 1 --only 12       # 앞 12조각만 만든다(시험)
  python3 audiobook/voicebox_book.py 1 2 3             # 장 전체

- 원고 조각은 audiobook.py segments()를 그대로 쓴다(지시 파일·편지 작성자 포함). 조각 하나 = Voicebox 요청 하나.
- 인물 → 프로필: voicebox/profiles.json(이름 "그라시아 · <인물>"). mama → madre. 군중(vecinos·todos)은 여러 프로필을
  겹쳐 만들고, 지하철 안내(megafonia)는 매표소 직원 목소리로 읽는다.
- 언어: 한글이 있으면 ko, 아니면 es. Qwen3는 카탈루냐어가 없어 카탈루냐어 대사도 es로 읽힌다.
- 캐시: cache_vb/<hash>.wav(프로필·글·언어·시드가 같으면 다시 만들지 않는다).
- 출력: out_vb/chNN.m4a, chNN.timeline.json, chNN.srt. 지금 Gemini판(out/)은 건드리지 않는다.
- 생성은 매번 Mike 승인 뒤에 한다(로컬이라 비용은 없다).
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
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
SEED = 7
ALIAS = {'mama': 'madre', 'megafonia': 'taquillera'}
CROWD = {'vecinos': ['montse', 'jaume', 'pau', 'senyora'], 'todos': ['vale', 'pau', 'sofia', 'luca']}
PAUSE = dict(line=0.5, para=0.8, scene=2.0)


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


def gen(pid, text, lang):
    key = hashlib.sha1(f'{pid}|{lang}|{SEED}|{text}'.encode()).hexdigest()[:16]
    path = CACHE / f'{key}.wav'
    if path.exists():
        return path
    r = call('POST', '/generate', {'profile_id': pid, 'text': text, 'language': lang, 'seed': SEED,
                                   'engine': 'qwen', 'model_size': '1.7B', 'normalize': True})
    gid = r['id']
    while r.get('status') not in ('completed', 'failed', 'error'):
        time.sleep(2)
        r = call('GET', f'/history/{gid}')        # /generate/{id}/status는 SSE 스트림이라 history로 본다
    if r.get('status') != 'completed':
        raise RuntimeError(f'Voicebox 생성 실패: {r.get("error")} — {text[:40]}')
    raw = call('GET', f'/audio/{gid}')
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.in')
    tmp.write_bytes(raw)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(tmp), '-ac', '1', '-ar', str(A.RATE), str(path)], check=True)
    tmp.unlink()
    return path


def pcm_of(path):
    with wave.open(str(path)) as w:
        return w.readframes(w.getnframes())


def mix(pcms, step=0.12):
    """군중: 여러 목소리를 조금씩 어긋나게 겹친다."""
    n = max(len(p) // 2 + int(i * step * A.RATE) for i, p in enumerate(pcms))
    out = [0] * n
    for i, p in enumerate(pcms):
        off = int(i * step * A.RATE)
        for k, x in enumerate(array('h', p)):
            out[off + k] += x // len(pcms) * 2
    return array('h', (max(-32767, min(32767, x)) for x in out)).tobytes()


def build(ch, only=None, plan=False):
    segs = A.segments(ch)
    if only:
        segs = segs[:only]
    pid = profiles()
    missing = sorted({v for s in segs for v in voices_of(s) if v not in pid})
    if missing:
        sys.exit(f'프로필 없음: {missing}')
    if plan:
        for i, s in enumerate(segs, 1):
            print(f'{i:3d} {s["kind"]:7s} {s["who"]:>10s}→{"+".join(voices_of(s)):18s} {A.lang(s["text"])} '
                  f'{len(s["text"]):4d}자  {s["text"][:50]}')
        print(f'{ch}장: 조각 {len(segs)}개, {sum(len(s["text"]) for s in segs)}자')
        return
    pcm, tl, scene, t0 = bytearray(), [], 1, time.time()
    for i, s in enumerate(segs, 1):
        lang = A.lang(s['text'])
        parts = [pcm_of(gen(pid[v], s['text'], lang)) for v in voices_of(s)]
        a = A.level(A.trim(parts[0] if len(parts) == 1 else mix(parts)))
        start = len(pcm) / 2 / A.RATE
        pcm += a
        tl.append(dict(start=round(start, 2), end=round(len(pcm) / 2 / A.RATE, 2), scene=scene, kind=s['kind'],
                       who=s['who'], text=s['text'], **({'gloss': s['gloss']} if s.get('gloss') else {})))
        if s['pause'] == 'scene' and s['kind'] != 'title':
            scene += 1
        nxt = segs[i] if i < len(segs) else None
        gap = PAUSE.get(s['pause'], 0.5)
        if s['kind'] in ('letter', 'address') or (nxt and nxt['kind'] in ('letter', 'address')):
            gap = max(gap, PAUSE['para'])
        pcm += b'\0\0' * int(A.RATE * gap)
        print(f'  {ch}장 {i}/{len(segs)}  {time.time() - t0:5.0f}초', end='\r', flush=True)
    OUTV.mkdir(parents=True, exist_ok=True)
    name = f'ch{ch:02d}' + (f'_first{only}' if only else '')
    (OUTV / f'{name}.timeline.json').write_text(json.dumps(tl, ensure_ascii=False, indent=1))
    wav, m4a = OUTV / f'{name}.wav', OUTV / f'{name}.m4a'
    with wave.open(str(wav), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(A.RATE); w.writeframes(bytes(pcm))
    subprocess.run(['afconvert', '-f', 'm4af', '-d', 'aac', '-b', '64000', str(wav), str(m4a)], check=True)
    wav.unlink()
    print(f'\n  {ch}장: {len(pcm) / 2 / A.RATE / 60:.1f}분, 생성 {time.time() - t0:.0f}초 → {m4a.relative_to(A.ROOT)}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('chs', nargs='+', type=int)
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--only', type=int)
    a = ap.parse_args()
    for c in a.chs:
        build(c, a.only, a.plan)


if __name__ == '__main__':
    main()
