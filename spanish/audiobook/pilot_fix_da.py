"""문장 끝 '-었다'에서 '다'만 0.6초쯤 떨어져 나온 곳의 쉼을 줄인다. TTS를 다시 만들지 않는다.

  python3 audiobook/pilot_fix_da.py 1 2 3     → out/pilot/chNN.wav, chNN.timeline.json 고침
  python3 audiobook/pilot_mix.py 1 2 3        → final 다시 만들기(.wav가 있으면 그것을 씀)

- 고칠 곳은 아래 SPOTS(파일럿 소리 기준 '다' 시작 시각). 2026-11-10 영상 세션이 찾음:
  소리 덩이 길이 0.14–0.2초, 앞 쉼 0.55–0.62초, 뒤에 긴 쉼, Whisper가 그 덩이만 듣고 '다'(또는 '딱','또')로 읽은 곳.
- 쉼을 KEEP초만 남기고 잘라 낸다(잘린 자리 양쪽 10 ms 페이드). 그 뒤 시간표는 잘라 낸 만큼 당긴다.
- 원래 시간표는 chNN.timeline.before_da.json으로 한 번만 남긴다.
"""
import json, shutil, subprocess, sys
from pathlib import Path
import numpy as np

AB = Path(__file__).resolve().parent
PILOT = AB / 'out' / 'pilot'
SR = 44100
KEEP = 0.12
SPOTS = {
    1: [194.16, 202.38, 225.30, 247.18, 500.80, 527.16, 720.68, 733.40, 741.62],
    2: [114.94, 600.64],
    3: [558.06],
}


def load(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def gap_before(a, t):
    """t('다' 시작) 바로 앞 무음 구간 [g0, g1) (샘플)."""
    k = int(SR * 0.01)
    r = lambda i: float(np.sqrt((a[i:i + k] ** 2).mean()))
    g1 = int(t * SR) - k
    while r(g1) > 0.003:        # 시작점을 무음 안쪽으로
        g1 -= k
    while r(g1 + k) <= 0.003:   # 소리 시작 직전까지
        g1 += k
    g1 += k
    g0 = g1 - k
    while r(g0 - k) <= 0.003:
        g0 -= k
    return g0, g1


def main():
    for ch in map(int, sys.argv[1:]):
        a = load(PILOT / f'ch{ch:02d}.m4a')
        tlp = PILOT / f'ch{ch:02d}.timeline.json'
        keep = PILOT / f'ch{ch:02d}.timeline.before_da.json'
        if not keep.exists():
            shutil.copyfile(tlp, keep)
        tl = json.loads(keep.read_text())
        cuts = []
        for t in SPOTS.get(ch, []):
            g0, g1 = gap_before(a, t)
            gap = (g1 - g0) / SR
            if not 0.4 <= gap <= 0.8:
                print(f'  {ch}장 {t}: 쉼 {gap:.2f}초, 건너뜀'); continue
            c0 = g0 + int(KEEP / 2 * SR)
            c1 = g1 - int(KEEP / 2 * SR)
            cuts.append((c0, c1))
            print(f'  {ch}장 {t:.2f}: 쉼 {gap:.2f}초 → {KEEP:.2f}초')
        f = int(0.01 * SR)
        parts, last = [], 0
        for c0, c1 in sorted(cuts):
            x = a[last:c0].copy(); x[-f:] *= np.linspace(1, 0, f)
            parts.append(x)
            y0 = c1; last = c1
            a[c1:c1 + f] *= np.linspace(0, 1, f)
        parts.append(a[last:])
        out = np.concatenate(parts)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                        '-c:a', 'pcm_s16le', str(PILOT / f'ch{ch:02d}.wav')], input=out.astype(np.float32).tobytes(), check=True)
        for x in tl:
            for key in ('start', 'end'):
                v = x[key]
                x[key] = round(v - sum((c1 - c0) / SR for c0, c1 in cuts if c1 / SR <= v + 1e-6), 2)
        tlp.write_text(json.dumps(tl, ensure_ascii=False, indent=1))
        print(f'{ch}장: {len(cuts)}곳, {(len(a) - len(out)) / SR:.2f}초 줄임')


if __name__ == '__main__':
    main()
