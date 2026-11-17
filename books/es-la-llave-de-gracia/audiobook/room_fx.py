"""인물별 '같은 녹음실' 맞추기(11-14 Mike: "유나가 말하는곳과 발레가 말하는곳의 공기 차이가 느껴져").
조각마다: ① 바닥 잡음·잔향 꼬리를 낮추는 부드러운 익스팬더 ② 인물별 저음·고음 쉘빙 EQ로 공통 기준에 맞춤
③ 모두 같은 작은 방 울림(합성 IR)을 살짝. 재생성 없이 조립 때 적용한다. 기준값은 1–25장 v4 측정(voice_room.py).
"""
import numpy as np
from array import array
from scipy.signal import lfilter, fftconvolve

SR = 24000
# 1–25장 측정 대역 세기(dB, 전체 대비): 60–200 / 4–8k / 8–12k
MEAS = {'narr1': (-12.4, -17.1, -23.4), 'narr': (-12.4, -17.1, -23.4), 'yunha': (-11.9, -16.1, -19.9),
        'marc': (-17.1, -28.6, -39.9), 'montse': (-10.4, -19.0, -22.8), 'vale': (-15.5, -18.2, -30.0),
        'marti': (-7.4, -16.1, -24.7)}
TARGET = (-12.0, -17.5, -24.0)        # 주요 인물 중앙값


def shelf(x, f0, gain_db, kind, q=0.707):
    """RBJ 쉘빙 필터."""
    A = 10 ** (gain_db / 40); w0 = 2 * np.pi * f0 / SR; al = np.sin(w0) / (2 * q); c = np.cos(w0)
    s = 2 * np.sqrt(A) * al
    if kind == 'low':
        b = [A * ((A + 1) - (A - 1) * c + s), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - s)]
        a = [(A + 1) + (A - 1) * c + s, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - s]
    else:
        b = [A * ((A + 1) + (A - 1) * c + s), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - s)]
        a = [(A + 1) - (A - 1) * c + s, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - s]
    return lfilter(np.array(b) / a[0], np.array(a) / a[0], x)


def expander(x, below=38.0, ratio=2.5):
    """말소리 최대보다 below dB 아래의 소리를 ratio로 더 낮춘다(바닥 잡음·잔향 꼬리)."""
    fr = int(SR * 0.01)
    env = np.sqrt(np.convolve(x ** 2, np.ones(fr) / fr, mode='same')) + 1e-9
    lvl = 20 * np.log10(env); thr = np.percentile(lvl, 98) - below
    g_db = np.where(lvl < thr, (lvl - thr) * (ratio - 1), 0.0)
    g_db = np.convolve(g_db, np.ones(fr * 3) / (fr * 3), mode='same')       # 30 ms로 부드럽게
    return x * 10 ** (g_db / 20)


_rng = np.random.default_rng(7)
_t = np.arange(int(SR * 0.35)) / SR
IR = _rng.standard_normal(len(_t)) * np.exp(-_t / 0.045)                   # 작은 방(RT60 약 0.3초)
IR[: int(SR * 0.004)] = 0                                                  # 직접음과 4 ms 띄움
IR /= np.sqrt((IR ** 2).sum())
WET = 10 ** (-17 / 20)


def room(pcm, voice):
    x = np.array(array('h', pcm), dtype=np.float64) / 32768
    if len(x) < SR * 0.05:
        return pcm
    peak0 = np.abs(x).max()
    x = expander(x)
    m = MEAS.get(voice)
    if m:
        lo = np.clip(TARGET[0] - m[0], -6, 6)
        hi = np.clip(TARGET[1] - m[1], -6, 8)
        top = np.clip((TARGET[2] - m[2]) - hi, -6, 6)
        if abs(lo) > 0.5: x = shelf(x, 180, lo, 'low')
        if abs(hi) > 0.5: x = shelf(x, 4000, hi, 'high')
        if abs(top) > 0.5: x = shelf(x, 8500, top, 'high')
    y = x + WET * fftconvolve(x, IR)[: len(x)]          # 길이는 그대로(시간표·자막이 안 밀리게)
    y *= peak0 / (np.abs(y).max() + 1e-9)                                     # 원래 최대값으로
    return (np.clip(y, -1, 1) * 32767).astype('<i2').tobytes()
