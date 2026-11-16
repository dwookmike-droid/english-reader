"""파일럿 장 파일에 간주(BGM)를 붙여 배포용 파일을 만든다. API를 쓰지 않는다.

  python3 audiobook/pilot_mix.py 1 2 3 --pick theme_open=2 B_mystery_a=1 B_mystery_b=3

- 곡 배치는 audiobook/bgm.tsv. 어느 후보를 쓸지는 bgm/picks.tsv(cue, 번호). 돌릴 때마다 고른 후보를
  bgm/<cue>.wav로 복사하고 그 파일을 쓴다. 곡을 바꾸려면 picks.tsv의 번호만 고치고 다시 돌린다.
  --pick cue=번호는 picks.tsv보다 앞선다(시험용).
- 1장 앞: 앞 무음 0.8초 → theme_open(14.25초, 끝 3초 페이드) → 1초 → 본문.
- 장 끝: 마지막 말 뒤 0.8초 → 간주(곡마다 10.45–11.95초, 아래 CUT; 30장은 theme_close 50초 전부. 들어갈 때 1초·나갈 때 3초 페이드)
- true peak가 -1 dBTP를 넘으면 장 전체 음량을 그만큼 낮춘다. → 뒤 무음 2초.
- 음악은 말소리와 겹치지 않고, 말소리보다 약 9 dB 작게(RMS).
- 결과: out/pilot/final/chNN.mp3(스포티파이: 44.1 kHz, 모노, 192 kbps CBR), chNN.m4a(영상용), chNN.timeline.json(앞에 붙은 길이만큼 밀림).
"""
import argparse, json, shutil, subprocess
from pathlib import Path
import numpy as np

AB = Path(__file__).resolve().parent
PILOT = AB / 'out' / 'pilot'
FINAL = PILOT / 'final'
SR = 44100
SPEECH_RMS = None      # 장 소리에서 잰다
MUSIC_DB = -9.0
TP_MAX = -1.0          # 스포티파이 권장: 손실 압축 전 true peak -1 dBTP 이하
# 곡마다 자르는 지점(초). 10–12초 안의 조용한 곳(BGM 세션 실측, bgm/NIGHTLY_REPORT_bgm.md 11-12).
# 없는 곡은 기본 길이(간주 11초, 시작 테마 14초). None = 자르지 않고 끝까지(theme_close는 스스로 잦아든다).
CUT = {'A_light_a': 11.95, 'A_light_b': 10.45, 'B_mystery_a': 11.95, 'C_tender_a': 11.95, 'C_tender_b': 10.45,
       'D_warm_a': 11.30, 'D_warm_b': 11.70, 'E_uneasy_b': 11.95, 'F_bittersweet': 11.80,
       'theme_open': 14.25, 'theme_close': None}


def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


# 11-14 Mike 결정: 팟캐스트·영상 -16 LUFS / -1.5 dBTP. Adobe 흉내 EQ에서 125 Hz를 +4.8→+3 dB, 70 Hz 아래 자름.
EQ_VB = ('highpass=f=70,equalizer=f=31:t=o:w=1:g=-1.9,equalizer=f=125:t=o:w=1:g=3.0,'
         'equalizer=f=2500:t=o:w=1:g=-0.9,highshelf=f=4500:t=q:w=0.7:g=-3.0')
TARGET_LUFS = -16.0


def master_speech(path):
    """말소리: 44.1 kHz float로 한 번 디코드 → 고정 EQ → 적분 음량을 재서 고정 이득(loudnorm처럼 움직이지 않음)."""
    import re as _re, tempfile
    with tempfile.TemporaryDirectory() as d:
        eq = Path(d) / 'eq.wav'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-af', 'aresample=44100,' + EQ_VB,
                        '-ac', '1', '-c:a', 'pcm_f32le', str(eq)], check=True)
        st = subprocess.run(['ffmpeg', '-i', str(eq), '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
        lufs = float(_re.findall(r'I:\s+(-?[\d.]+) LUFS', st)[-1])
        a = load(eq)
    return a * 10 ** ((TARGET_LUFS - lufs) / 20)


def rms(a, floor=0.015):
    x = a[np.abs(a) > floor]
    return float(np.sqrt((x * x).mean())) if len(x) else 1e-6


def fade(a, fin, fout):
    a = a.copy()
    i, o = int(fin * SR), int(fout * SR)
    if i: a[:i] *= np.linspace(0, 1, i)
    if o: a[-o:] *= np.linspace(1, 0, o)
    return a


def cue(name, picks, length, fin, fout, speech):
    p = AB / 'bgm' / f'{name}.wav'
    length = CUT.get(name, length)
    m = load(p)
    if length is not None:
        m = m[:int(length * SR)]
    m = fade(m, fin, fout)
    m *= (speech * 10 ** (MUSIC_DB / 20)) / rms(m, 0.002)
    return m, f'{name}_{picks[name]}'


def true_peak_db(a):
    from scipy.signal import resample_poly
    return 20 * np.log10(np.abs(resample_poly(a, 4, 1)).max() + 1e-9)


def silence(s):
    return np.zeros(int(s * SR), np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('chapters', nargs='+', type=int)
    ap.add_argument('--pick', nargs='*', default=[], help='cue=번호')
    ap.add_argument('--vb', action='store_true',
                    help='새 음성(11-13): out_vb/chNN_v4a.m4a(Adobe 처리본, 없으면 _v4) → out/vb_final/. 옛 Gemini 최종본은 그대로 둔다')
    a = ap.parse_args()
    picks = {}
    for line in (AB / 'bgm' / 'picks.tsv').read_text().splitlines():
        if line and not line.startswith('#'):
            k, v = line.split('\t')[:2]
            picks[k] = int(v)
    picks.update({k: int(v) for k, v in (x.split('=') for x in a.pick)})
    for k, v in picks.items():                      # 작업지시서 §7: 고른 후보를 bgm/<cue>.wav로
        shutil.copyfile(AB / 'bgm' / 'candidates' / k / f'{k}_{v}.wav', AB / 'bgm' / f'{k}.wav')
    place = {}
    for line in (AB / 'bgm.tsv').read_text().splitlines():
        if line and not line.startswith('#'):
            where, name = line.split('\t')[:2]
            place[where] = name
    global FINAL
    if a.vb:
        FINAL = AB / 'out' / 'vb_final'
    FINAL.mkdir(parents=True, exist_ok=True)
    for ch in a.chapters:
        vb = [AB / 'out_vb' / f'ch{ch:02d}_v4{t}.m4a' for t in ('a', '')]
        src = PILOT / f'ch{ch:02d}.wav'                # 쉼을 고친 판(audiobook/fix_turn_pauses, 11-10)이 있으면 그것
        if not src.exists():
            src = PILOT / f'ch{ch:02d}.m4a'
        if not src.exists():                           # 4장부터: pilot_sync를 거치지 않은 장은 out/chNN을 바로 쓴다
            src = AB / 'out' / f'ch{ch:02d}.m4a'
        if a.vb:
            # 11-14 전수조사: 무손실 원본(out_vb/chNN_v4.wav)에서 고정 EQ → 음량 고정 이득 → BGM → 리미터 → 인코딩 한 번.
            src = AB / 'out_vb' / f'ch{ch:02d}_v4.wav'
            if not src.exists():
                print(f'  {ch}장: 새 음성 wav 없음, 건너뜀'); continue
        speech = load(src) if not a.vb else master_speech(src)
        lvl = rms(speech)
        parts, used, offset = [silence(0.8)], [], 0.8
        if ch == 1 and 'open' in place:
            m, n = cue(place['open'], picks, 14, 0.3, 3, lvl)
            parts += [m, silence(1.0)]; used.append(n); offset += len(m) / SR + 1.0
        parts.append(speech)
        key = 'close' if ch == 30 else f'after {ch:02d}'
        if key in place:
            m, n = cue(place[key], picks, 11 if key != 'close' else 40, 1, 3, lvl)
            parts += [silence(0.8), m]; used.append(n)
        parts.append(silence(2.0))
        out = np.concatenate(parts)
        tp = true_peak_db(out)
        if tp > TP_MAX and not a.vb:                   # 전체를 조금 낮춘다(리미터로 말소리 모양을 바꾸지 않는다)
            out = out * 10 ** ((TP_MAX - 0.1 - tp) / 20)
        if not a.vb:                                   # 새 판은 4배 오버샘플 리미터가 잡는다. 여기서 자르면 찌그러진다(11-14)
            out = np.clip(out, -0.98, 0.98)
        wav = FINAL / f'ch{ch:02d}.f32'
        out.astype(np.float32).tofile(wav)
        base = ['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', str(wav)]
        if a.vb:                                       # 4배 오버샘플 리미터(천장 -2 dBFS → 인코딩 뒤 약 -1.5 dBTP)
            base += ['-af', 'aresample=176400,alimiter=limit=0.794:attack=5:release=60:level=disabled,aresample=44100']
            subprocess.run(base + ['-c:a', 'flac', str(FINAL / f'ch{ch:02d}.flac')], check=True)   # 영상용 무손실
        subprocess.run(base + ['-c:a', 'libmp3lame', '-b:a', '192k', str(FINAL / f'ch{ch:02d}.mp3')], check=True)
        subprocess.run(base + ['-c:a', 'aac', '-b:a', '128k', str(FINAL / f'ch{ch:02d}.m4a')], check=True)
        wav.unlink()
        tlp = PILOT / f'ch{ch:02d}.timeline.json'
        if a.vb:
            tlp = AB / 'out_vb' / f'ch{ch:02d}_v4.timeline.json'
        tl = json.loads((tlp if tlp.exists() else AB / 'out' / f'ch{ch:02d}.timeline.json').read_text())
        for x in tl:
            x['start'] = round(x['start'] + offset, 2); x['end'] = round(x['end'] + offset, 2)
        (FINAL / f'ch{ch:02d}.timeline.json').write_text(json.dumps(tl, ensure_ascii=False, indent=1))
        db = 20 * np.log10(rms(out) + 1e-9)
        print(f'{ch}장: {len(out) / SR / 60:.1f}분, 말소리 RMS {db:.1f} dBFS, true peak {true_peak_db(out):.1f} dBTP(조정 전 {tp:.1f}), 곡 {", ".join(used)}')


if __name__ == '__main__':
    main()
