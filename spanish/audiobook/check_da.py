"""조립한 장에서 '…었 (0.6초) 다' 모양이 다시 생겼는지 점검한다. 읽기만 한다. API를 쓰지 않는다.

찾는 모양: 조립이 넣은 화자 전환 쉼(0.45초, 완전 무음) 앞의 원래 쉼이 0.2초 이하로 짧고(낱말 안 틈),
그 뒤 소리가 0.25초 이하로 짧게 나온 다음 다시 0.3초 넘게 쉬는 곳. 11-10 파일럿 1–3장에서 21곳이 이 모양이었다.

  python3 audiobook/check_da.py 4 5 6        # out/chNN.m4a
"""
import subprocess, sys, json
from pathlib import Path
import numpy as np

AB = Path(__file__).resolve().parent
SR, FR = 24000, 240


def load(p):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                       capture_output=True, check=True).stdout
    a = np.abs(np.frombuffer(r, np.int16).astype(int))
    n = len(a) // FR
    return a[:n * FR].reshape(n, FR).max(1)


def check(ch):
    pk = load(AB / 'out' / f'ch{ch:02d}.m4a')
    tl = json.loads((AB / 'out' / f'ch{ch:02d}.timeline.json').read_text())
    n, k, hits = len(pk), 0, []
    while k < n:
        if pk[k] >= 40:
            k += 1; continue
        j = k
        while j < n and pk[j] < 40:
            j += 1
        if 0.40 <= (j - k) / 100 <= 0.62:
            b = k
            while b > 0 and pk[b - 1] < 500:
                b -= 1
            c = j
            while c < n and pk[c] < 500:
                c += 1
            v = c
            while v < n and (pk[v] >= 500 or pk[v:v + 8].max() >= 500):
                v += 1
            d = v
            while d < n and pk[d] < 500:
                d += 1
            nat, burst, after = (k - b + c - j) / 100, (v - c) / 100, (d - v) / 100
            if nat <= 0.2 and burst <= 0.25 and after >= 0.3:
                t = c / 100
                seg = next((x for x in tl if x['start'] <= t < x['end'] + 0.3), {'text': ''})
                hits.append((t, nat, burst, seg['text'][-30:]))
        k = j
    print(f'{ch}장: 의심 {len(hits)}곳')
    for t, nat, burst, text in hits:
        print(f'   {int(t // 60)}:{t % 60:04.1f}  원래 쉼 {nat:.2f}  뒤 소리 {burst:.2f}  …{text}')
    return len(hits)


if __name__ == '__main__':
    sys.exit(1 if sum(check(int(c)) for c in sys.argv[1:]) else 0)
