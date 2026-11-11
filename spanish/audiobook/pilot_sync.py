"""완성된 장 소리(m4a)에 맞춰 시간표의 조각 시작 시각을 다시 잡는다. API를 쓰지 않는다.

조립 때 시간표는 묶음 안 조각 경계를 글자 수로 어림했다. 짧은 대사가 무음 하나를 건너뛰면 뒤 조각이
줄줄이 밀렸다(영상 세션 sync_check, 장마다 12–14곳). 여기서는 장 전체의 '말 시작점'(무음 뒤 말소리)을
찾고, 조각마다 하나씩 순서대로 배정한다(동적 계획법). 비용 = 원래 시각에서 벗어난 정도
+ 앞 조각 길이가 글자 수로 본 길이와 다른 정도. 같은 말 시작점을 두 조각이 나눠 쓰지 않는다.

  python3 audiobook/pilot_sync.py audiobook/out/pilot/ch01      # ch01.m4a + ch01.timeline.json → 고쳐 씀(원본은 .orig.json)
"""
import json, shutil, subprocess, sys, tempfile, wave
from pathlib import Path
import numpy as np

FRAME = 0.02
SIL = 150            # 무음 기준(조립 코드와 같은 값)
MIN_SIL = 0.12       # 이만큼 이어진 무음 뒤 말소리를 말 시작점으로
LEAD = 0.25          # 글자는 말보다 이만큼 먼저 띄운다
WIN = 4.0            # 원래 시각에서 이 범위 안의 말 시작점만 후보
RATE = dict(ko=6.5, es=11.0)


def rms_of(m4a):
    tmp = Path(tempfile.mkdtemp()) / 'a.wav'
    subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16', str(m4a), str(tmp)], check=True)
    w = wave.open(str(tmp)); r = w.getframerate(); ch = w.getnchannels()
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
    shutil.rmtree(tmp.parent)
    if ch > 1:
        a = a.reshape(-1, ch).mean(1)
    k = int(r * FRAME); n = len(a) // k
    return np.sqrt((a[:n * k].reshape(n, k) ** 2).mean(1))


def onsets(rms):
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


def lang(t):
    return 'ko' if any('가' <= c <= '힣' for c in t) else 'es'


def fix(base):
    base = Path(base)
    tl_path = base.with_suffix('.timeline.json')
    tl = json.loads(tl_path.read_text())
    on = onsets(rms_of(base.with_suffix('.m4a')))
    n = len(tl)
    est = [x['start'] + 0.45 for x in tl]                     # 원래 경계는 쉼 시작 → 말 시작은 조금 뒤
    dur = [len(x['text']) / RATE[lang(x['text'])] for x in tl]
    cand = [np.where(np.abs(on - est[k]) <= WIN)[0] for k in range(n)]
    INF = 1e18
    cost = [dict() for _ in range(n)]
    back = [dict() for _ in range(n)]
    for j in cand[0]:
        cost[0][j] = (on[j] - est[0]) ** 2
    for k in range(1, n):
        for j in cand[k]:
            best, arg = INF, None
            for i, c in cost[k - 1].items():
                if on[i] >= on[j]:
                    continue
                gap = on[j] - on[i]
                c2 = c + (on[j] - est[k]) ** 2 + 0.15 * (gap - dur[k - 1]) ** 2 / max(1.0, dur[k - 1])
                if c2 < best:
                    best, arg = c2, i
            if arg is not None:
                cost[k][j], back[k][j] = best, arg
        if not cost[k]:                                       # 후보가 없으면 원래 시각을 그대로 두고 이어 간다
            raise SystemExit(f'{base.name}: {k}번 조각 근처에 말 시작점이 없음 — {tl[k]["text"][:30]}')
    j = min(cost[-1], key=cost[-1].get)
    pick = [0] * n
    for k in range(n - 1, -1, -1):
        pick[k] = j
        j = back[k].get(j)
    if not (base.parent / (base.name + '.timeline.orig.json')).exists():
        shutil.copy(tl_path, base.parent / (base.name + '.timeline.orig.json'))
    moved = 0
    for k, x in enumerate(tl):
        s = round(max(0.0, on[pick[k]] - LEAD), 2)
        if abs(s - x['start']) > 0.8:
            moved += 1
        x['start'] = s
    for k in range(n - 1):
        tl[k]['end'] = tl[k + 1]['start']
    tl_path.write_text(json.dumps(tl, ensure_ascii=False, indent=1))
    def ts(v):
        ms = int(round(v * 1000))
        return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'
    base.with_suffix('.srt').write_text(''.join(
        f'{i}\n{ts(x["start"])} --> {ts(x["end"])}\n{x["text"]}\n\n' for i, x in enumerate(tl, 1)))
    print(f'{base.name}: 조각 {n}개, 0.8초 넘게 옮긴 것 {moved}개')


if __name__ == '__main__':
    for b in sys.argv[1:]:
        fix(b)
