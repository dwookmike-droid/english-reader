"""Voicebox 음성 프로필용 인물별 샘플을 기존 Gemini 음성(1–9장)에서 뽑는다.

  python3 audiobook/voicebox_samples.py          # 뽑기
  python3 audiobook/voicebox_samples.py --list   # 인물별 길이만 본다

- 2026-11-11 Mike: "voicebox를 사용해서 인물들의 목소리를 픽스", "제미나이 1회 최대 생성한 길이가 몇인지 확인하고
  그걸 샘플로 해서 일관성 유지로 간다"
- Gemini 1회 생성(묶음 하나) 최대 길이 = cache/u*.wav 중 가장 긴 것(165.3초). 샘플 하나의 상한으로 쓴다.
- 입력: out/chNN.m4a(BGM 없는 목소리)와 out/chNN.timeline.json. 인물(who)·종류(kind)가 같은 조각을
  긴 것부터 골라 0.4초 간격으로 이어 붙인다. ElevenLabs 편지(marti, 서술 letter)는 쓰지 않는다.
- Voicebox는 샘플 하나가 30초까지다(11-11 확인). 30초 이하 조각만 고르고, 원고 순서대로 30초 이하 묶음으로 나눈다.
  한 프로필에 묶음 여러 개를 샘플로 넣는다(합계가 165.3초 상한).
- 출력: voicebox/ref/<이름>_NN.wav(24 kHz mono)와 <이름>_NN.txt(Voicebox reference_text).
"""
import argparse
import json
import subprocess
import wave
from pathlib import Path

AB = Path(__file__).resolve().parent
OUT = AB / 'out'
DST = AB / 'voicebox' / 'ref'
CHS = range(1, 10)
GAP = 0.4
SR = 24000
PART = 29.5          # Voicebox 샘플 하나의 상한(30초)


def max_unit():
    best = 0.0
    for f in (AB / 'cache').glob('u*.wav'):
        with wave.open(str(f)) as w:
            best = max(best, w.getnframes() / w.getframerate())
    return best


def pieces():
    by = {}
    for c in CHS:
        tl = OUT / f'ch{c:02d}.timeline.json'
        if not tl.exists():
            continue
        for p in json.loads(tl.read_text()):
            if p['who'] == 'marti' or p['kind'] in ('letter', 'title', 'address'):
                continue
            name = 'narr' if p['who'] == 'narr' else p['who']
            by.setdefault(name, []).append((p['end'] - p['start'], c, p))
    return by


def pcm(ch, start, end):
    return subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{start:.3f}', '-to', f'{end:.3f}',
                           '-i', str(OUT / f'ch{ch:02d}.m4a'), '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                          capture_output=True, check=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    cap = max_unit()
    print(f'Gemini 1회 생성 최대 길이: {cap:.1f}초 → 샘플 상한')
    DST.mkdir(parents=True, exist_ok=True)
    for name, ps in sorted(pieces().items(), key=lambda x: -sum(d for d, _, _ in x[1])):
        ps.sort(key=lambda x: -x[0])
        pick, total = [], 0.0
        for d, c, p in ps:
            if d > PART:
                continue
            if total + d + (GAP if pick else 0) > cap:
                continue
            pick.append((c, p))
            total += d + (GAP if len(pick) > 1 else 0)
        pick.sort(key=lambda x: (x[0], x[1]['start']))     # 원고 순서로 잇는다
        print(f'{name:16s} 조각 {len(pick):3d}/{len(ps):3d}  {total:6.1f}초')
        if a.list:
            continue
        for f in DST.glob(f'{name}_[0-9][0-9].*'):
            f.unlink()
        parts, cur, dur = [], [], 0.0
        for c, p in pick:
            d = p['end'] - p['start']
            if cur and dur + GAP + d > PART:
                parts.append(cur); cur, dur = [], 0.0
            dur += d + (GAP if cur else 0)
            cur.append((c, p))
        parts.append(cur)
        for i, part in enumerate(parts, 1):
            audio = (b'\0\0' * int(GAP * SR)).join(pcm(c, p['start'], p['end']) for c, p in part)
            with wave.open(str(DST / f'{name}_{i:02d}.wav'), 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(audio)
            (DST / f'{name}_{i:02d}.txt').write_text(' '.join(p['text'] for _, p in part) + '\n')

if __name__ == '__main__':
    main()
