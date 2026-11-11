"""파일럿 장 파일에 간주(BGM)를 붙여 배포용 파일을 만든다. API를 쓰지 않는다.

  python3 audiobook/pilot_mix.py 1 2 3 --pick theme_open=2 B_mystery_a=1 B_mystery_b=3

- 곡 배치는 audiobook/bgm.tsv. 어느 후보를 쓸지는 bgm/picks.tsv(cue, 번호). 돌릴 때마다 고른 후보를
  bgm/<cue>.wav로 복사하고 그 파일을 쓴다. 곡을 바꾸려면 picks.tsv의 번호만 고치고 다시 돌린다.
  --pick cue=번호는 picks.tsv보다 앞선다(시험용).
- 1장 앞: 앞 무음 0.8초 → theme_open(최대 14초, 끝 3초 페이드) → 1초 → 본문.
- 장 끝: 마지막 말 뒤 0.8초 → 간주(11초, 들어갈 때 1초·나갈 때 3초 페이드) → 뒤 무음 2초.
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


def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


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
    m = load(p)[:int(length * SR)]
    m = fade(m, fin, fout)
    m *= (speech * 10 ** (MUSIC_DB / 20)) / rms(m, 0.002)
    return m, f'{name}_{picks[name]}'


def silence(s):
    return np.zeros(int(s * SR), np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('chapters', nargs='+', type=int)
    ap.add_argument('--pick', nargs='*', default=[], help='cue=번호')
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
    FINAL.mkdir(parents=True, exist_ok=True)
    for ch in a.chapters:
        src = PILOT / f'ch{ch:02d}.wav'                # 쉼을 고친 판(audiobook/fix_turn_pauses, 11-10)이 있으면 그것
        if not src.exists():
            src = PILOT / f'ch{ch:02d}.m4a'
        if not src.exists():                           # 4장부터: pilot_sync를 거치지 않은 장은 out/chNN을 바로 쓴다
            src = AB / 'out' / f'ch{ch:02d}.m4a'
        speech = load(src)
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
        out = np.clip(out, -0.98, 0.98)
        wav = FINAL / f'ch{ch:02d}.f32'
        out.astype(np.float32).tofile(wav)
        base = ['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', str(wav)]
        subprocess.run(base + ['-c:a', 'libmp3lame', '-b:a', '192k', str(FINAL / f'ch{ch:02d}.mp3')], check=True)
        subprocess.run(base + ['-c:a', 'aac', '-b:a', '128k', str(FINAL / f'ch{ch:02d}.m4a')], check=True)
        wav.unlink()
        tlp = PILOT / f'ch{ch:02d}.timeline.json'
        tl = json.loads((tlp if tlp.exists() else AB / 'out' / f'ch{ch:02d}.timeline.json').read_text())
        for x in tl:
            x['start'] = round(x['start'] + offset, 2); x['end'] = round(x['end'] + offset, 2)
        (FINAL / f'ch{ch:02d}.timeline.json').write_text(json.dumps(tl, ensure_ascii=False, indent=1))
        db = 20 * np.log10(rms(out) + 1e-9)
        print(f'{ch}장: {len(out) / SR / 60:.1f}분, 말소리 RMS {db:.1f} dBFS, 피크 {20*np.log10(np.abs(out).max()):.1f} dBFS, 곡 {", ".join(used)}')


if __name__ == '__main__':
    main()
