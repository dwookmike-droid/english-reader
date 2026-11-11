"""voicebox/ref/의 인물별 샘플을 Voicebox 음성 프로필로 등록한다(Voicebox 앱이 켜져 있어야 한다).

  python3 audiobook/voicebox_profiles.py          # 전부 등록(이미 있으면 샘플만 새로 넣는다)
  python3 audiobook/voicebox_profiles.py marc     # 그 인물만

- 11-11: 샘플은 ElevenLabs 1순위 목소리(voicebox_el.py). 마르티는 1–9장 편지 음성.
- 프로필 이름: "그라시아 · <원고 이름>". 서술(narr)·엄마(madre)는 한국어(ko), 나머지는 스페인어(es). 엔진은 qwen(Qwen3-TTS 복제).
- 음성을 만들지는 않는다(생성은 매번 Mike 승인). 등록 결과는 voicebox/profiles.json에 남긴다.
- 군중(vecinos)과 카탈루냐어 안내 방송(megafonia)은 복제 대상이 아니라 넣지 않는다.
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

AB = Path(__file__).resolve().parent
REF = AB / 'voicebox' / 'ref'
OUT = AB / 'voicebox' / 'profiles.json'
API = 'http://localhost:17493'
SKIP = {'vecinos', 'megafonia', 'todos'}
SRC = {'marti': '1–9장 ElevenLabs(Álvaro Sereno) 편지 음성'}
KO = {'narr', 'madre'}
LABEL = {'narr': '서술(윤하)', 'yunha': '윤하', 'madre': '엄마'}


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or 'null')


def add_sample(pid, wav, text):
    r = subprocess.run(['curl', '-s', '-m', '120', '-X', 'POST', f'{API}/profiles/{pid}/samples',
                        '-F', f'file=@{wav}', '-F', f'reference_text={text}'], capture_output=True, text=True)
    d = json.loads(r.stdout)
    if 'detail' in d:
        raise SystemExit(f'{wav.name}: {d["detail"]}')
    return d['id']


def main():
    want = set(sys.argv[1:])
    names = sorted({p.stem.rsplit('_', 1)[0] for p in REF.glob('*_[0-9][0-9].wav')} - SKIP)
    names = [n for n in names if not want or n in want]
    have = {p['name']: p for p in call('GET', '/profiles')}
    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    for n in names:
        title = f'그라시아 · {LABEL.get(n, n)}'
        lang = 'ko' if n in KO else 'es'
        wavs = sorted(REF.glob(f'{n}_[0-9][0-9].wav'))
        body = {'name': title, 'language': lang, 'voice_type': 'cloned', 'default_engine': 'qwen',
                'description': f'「그라시아의 열쇠」 {n}. {SRC.get(n, "ElevenLabs 1순위 목소리(voicebox/cast_el.tsv)")}로 만든 샘플 {len(wavs)}개'}
        if title in have:
            pid = have[title]['id']
            for s in call('GET', f'/profiles/{pid}/samples'):
                call('DELETE', f'/profiles/samples/{s["id"]}')
            call('PUT', f'/profiles/{pid}', body)
        else:
            pid = call('POST', '/profiles', body)['id']
        ids = [add_sample(pid, w, w.with_suffix('.txt').read_text().strip()) for w in wavs]
        out[n] = {'profile_id': pid, 'name': title, 'language': lang, 'samples': [w.name for w in wavs], 'sample_ids': ids}
        print(f'{title:24s} {lang}  샘플 {len(ids)}개')
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')


if __name__ == '__main__':
    main()
