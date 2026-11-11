"""Voicebox 프로필용 인물 샘플을 Gemini로 한 번씩 만든다(11-11 Mike: "책속의 대사 뿐만아니라 다양한 발음을
다 소화할수있도록 늘려서", "샘플 없는 사람들도 그렇게 해서 음원 기본 만들어").

  python3 audiobook/voicebox_gen.py --plan          # 요청 없이 프롬프트·글자 수만
  python3 audiobook/voicebox_gen.py                 # 아직 안 만든 인물 전부
  python3 audiobook/voicebox_gen.py marc vale       # 그 인물만(이미 있으면 다시 만들지 않는다)

- 대본: voicebox/scripts.txt(원고 대사 몇 줄 + 여러 발음을 고루 담은 말).
- 인물마다 Gemini 요청 1회(책과 같은 모델 BOOK_MODEL, 같은 목소리, 같은 프롬프트 틀 unit_prompt).
  1회 최대 생성 길이(165.3초)를 넘으면 그 앞 쉼에서 자른다.
- 원본: voicebox/gen/<이름>.wav. Voicebox 샘플: 30초 이하로 쉼에서 나눠 voicebox/ref/<이름>_NN.wav,
  각 조각을 받아써서 <이름>_NN.txt(reference_text).
- 1–9장에서 뽑았던 샘플(voicebox_samples.py)은 voicebox/ref_book/으로 옮겨 둔다.
"""
import argparse
import shutil
import sys
import wave
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import audiobook as A  # noqa: E402

VB = A.CONF / 'voicebox'
SCRIPTS = VB / 'scripts.txt'
GEN = VB / 'gen'
REF = VB / 'ref'
BOOK = VB / 'ref_book'
CAP = 165.3          # Gemini 1회 최대 생성 길이(cache/u*.wav 최댓값, 11-11)
PART = 29.5          # Voicebox 샘플 하나의 상한(30초)
SCENE = '{label} talks to Yuna for a while; one long, natural turn in their own everyday way.'


def scripts():
    d, cur = {}, None
    for l in SCRIPTS.read_text().split('\n'):
        l = l.strip()
        if l.startswith('=== '):
            cur = l[4:].strip(); d[cur] = dict(scene='', lines=[]); continue
        if not cur or not l or l.startswith('#'):
            continue
        if l.startswith('scene:'):
            d[cur]['scene'] = l[6:].strip()
        else:
            d[cur]['lines'].append(l)
    return d


def unit_of(name, sc):
    kind, lane = ('narr', 'narr') if name == 'narr' else ('say', 'dlg')
    label = A.voice_of(dict(who=name))['label']
    scene = sc['scene'] or ('' if name == 'narr' else SCENE.format(label=label))
    return [dict(kind=kind, who=name, text=t, lane=lane, pause='line', scene=scene) for t in sc['lines']]


def frames(pcm, win=0.05):
    a = array('h', pcm)
    n = int(A.RATE * win)
    return [(sum(x * x for x in a[i:i + n]) / max(1, len(a[i:i + n]))) ** 0.5 for i in range(0, len(a), n)], win


def pauses(pcm, quiet=300, least=0.25):
    """쉼 가운데 지점(초) 목록."""
    rms, win = frames(pcm)
    out, start = [], None
    for i, r in enumerate(rms + [quiet + 1]):
        if r < quiet:
            start = i if start is None else start
        else:
            if start is not None and (i - start) * win >= least:
                out.append((start + i) / 2 * win)
            start = None
    return out


def cut(pcm, cap=CAP, part=PART):
    """cap 이하로 줄이고 part 이하 조각으로 나눈다. 자르는 자리는 모두 쉼."""
    total = len(pcm) / 2 / A.RATE
    ps = pauses(pcm)
    if total > cap:
        total = max([p for p in ps if p <= cap] or [cap])
    bounds, last = [], 0.0
    while total - last > part:
        c = max([p for p in ps if last + 3 < p <= last + part] or [last + part])
        bounds.append((last, c)); last = c
    bounds.append((last, total))
    b = lambda s: int(s * A.RATE) * 2
    return [A.trim(pcm[b(s):b(e)], head=0.1, tail=0.3) for s, e in bounds]


def save(path, pcm):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(A.RATE); w.writeframes(pcm)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('names', nargs='*')
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--redo', action='store_true', help='이미 만든 인물도 다시 만든다')
    a = ap.parse_args()
    sc = scripts()
    names = a.names or list(sc)
    GEN.mkdir(parents=True, exist_ok=True)
    for n in names:
        unit = unit_of(n, sc[n])
        prompt, cfg = A.unit_prompt(unit)
        raw = GEN / f'{n}.wav'
        if a.plan:
            print(f'== {n}  {sum(len(s["text"]) for s in unit)}자  {cfg}\n{prompt[:400]}…\n')
            continue
        if raw.exists() and not a.redo:
            with wave.open(str(raw)) as w:
                pcm = w.readframes(w.getnframes())
        else:
            try:
                pcm = A.gemini(unit[0], prompt, cfg, model=A.BOOK_MODEL)
            except A.DailyLimit as e:
                sys.exit(f'{n}: {e}')
            save(raw, pcm)
        pcm = A.level(A.trim(pcm))
        parts = cut(pcm)
        BOOK.mkdir(exist_ok=True)
        for f in REF.glob(f'{n}_[0-9][0-9].*'):
            dst = BOOK / f.name
            if not dst.exists():
                shutil.move(str(f), dst)
            else:
                f.unlink()
        for i, p in enumerate(parts, 1):
            save(REF / f'{n}_{i:02d}.wav', p)
            (REF / f'{n}_{i:02d}.txt').write_text(A.heard(p).strip() + '\n')
        secs = [len(p) / 2 / A.RATE for p in parts]
        print(f'{n:15s} 원본 {len(pcm) / 2 / A.RATE:6.1f}초 → 샘플 {len(parts)}개 {sum(secs):6.1f}초 '
              f'({", ".join(f"{s:.1f}" for s in secs)})', flush=True)


if __name__ == '__main__':
    main()
