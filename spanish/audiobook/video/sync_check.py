"""시간표(chNN.timeline.json) 경계가 실제 소리와 맞는지 점검한다. 읽기만 한다.

조각마다 시작 시각 뒤쪽에서 '무음 → 말소리' 전환(말 시작점)을 찾는다.
시간표 경계는 보통 쉼이 시작되는 곳이라 말 시작보다 0.4–0.7초 이르다(자막이 조금 먼저 뜸, 정상).
문제로 적는 것: 자막이 말보다 LATE초 넘게 늦음, EARLY초 넘게 이름, 앞 조각과 같은 말 시작점을 씀,
0.3초보다 짧은 조각, 구간 안에 말소리가 거의 없음.

  python3 audiobook/video/sync_check.py 1 2 3
  python3 audiobook/video/sync_check.py 1 --all      # 모든 조각 출력

소리는 macOS afconvert(없으면 ffmpeg)로 임시 wav로 풀어 읽는다.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

AB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render  # noqa: E402  (입력 폴더 기본값을 render.py와 같이 쓴다)
FRAME = 0.02          # 20 ms 단위 음량
SIL = 150             # 이 RMS 아래면 무음(조립 코드 trim 기준과 같은 값)
MIN_SIL = 0.2         # 이만큼 이어진 무음 뒤의 말소리만 '말 시작점'
LATE = 0.25
EARLY = 1.0
WIN = 3.0


def decode(m4a):
    tmp = Path(tempfile.mkdtemp()) / 'a.wav'
    if shutil.which('afconvert'):
        cmd = ['afconvert', '-f', 'WAVE', '-d', 'LEI16', str(m4a), str(tmp)]
    else:
        cmd = ['ffmpeg', '-v', 'error', '-i', str(m4a), '-ac', '1', str(tmp)]
    subprocess.run(cmd, check=True)
    w = wave.open(str(tmp))
    rate, nch = w.getframerate(), w.getnchannels()
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
    shutil.rmtree(tmp.parent)
    if nch > 1:
        a = a.reshape(-1, nch).mean(1)
    k = int(rate * FRAME)
    n = len(a) // k
    return np.sqrt((a[:n * k].reshape(n, k) ** 2).mean(1))


def onsets(rms):
    """무음이 MIN_SIL 이상 이어진 뒤 말소리가 시작되는 시각들."""
    loud = rms > SIL
    need = int(MIN_SIL / FRAME)
    out, quiet = [], need
    for i, v in enumerate(loud):
        if v:
            if quiet >= need:
                out.append(i * FRAME)
            quiet = 0
        else:
            quiet += 1
    return np.array(out)


def check(ch, show_all=False):
    items = json.loads((render.AUDIO / f'ch{ch:02d}.timeline.json').read_text())
    rms = decode(render.AUDIO / f'ch{ch:02d}.m4a')
    on = onsets(rms)
    bad, prev = 0, None
    print(f'{ch}장: 조각 {len(items)}개, 말 시작점 {len(on)}개')
    for i, it in enumerate(items):
        s, e = it['start'], it['end']
        near = on[(on > s - WIN) & (on < s + WIN)]
        cand = near[near > s - LATE]
        d = float(cand.min() - s) if len(cand) else None
        hit = None if d is None else round(s + d, 2)
        seg = rms[int(s / FRAME):max(int(s / FRAME) + 1, int(e / FRAME))]
        voiced = float((seg > SIL).mean()) if len(seg) else 0.0
        why = []
        if i and d is None:
            why.append('근처에 말 시작 없음')
        elif i and d > EARLY:
            why.append(f'자막이 {d:.1f}초 이름')
        elif i and it['kind'] != 'title' and items[i - 1]['kind'] != 'title' and hit == prev:
            why.append('앞 조각과 같은 말 시작점')
        prev = hit
        if e - s < 0.3:
            why.append(f'너무 짧음 {e - s:.2f}초')
        if voiced < 0.2 and e - s >= 0.3:
            why.append(f'구간 안 말소리 {voiced:.0%}')
        if why or show_all:
            bad += bool(why)
            dd = f'{d:+.2f}' if d is not None else '  ?  '
            print(f'  {s:8.2f}–{e:8.2f}  말시작 {dd}초  {it["kind"]:7} {it["text"][:28]!r}  {", ".join(why)}')
    print(f'  → 문제 {bad}곳')
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('chapters', nargs='+', type=int)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--src', help='소리·시간표 폴더(기본 audiobook/out/pilot/final)')
    a = ap.parse_args()
    if a.src:
        render.set_src(a.src)
    print(f'입력: {render.AUDIO}')
    sys.exit(1 if sum(check(c, a.all) for c in a.chapters) else 0)


if __name__ == '__main__':
    main()
