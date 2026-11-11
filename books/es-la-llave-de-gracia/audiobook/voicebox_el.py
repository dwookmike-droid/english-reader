"""ElevenLabs 샘플(voicebox/el/<이름>.mp3)을 Voicebox 샘플(voicebox/ref/<이름>_NN.wav/.txt)로 만든다(11-11).

  python3 audiobook/voicebox_el.py
  python3 audiobook/voicebox_profiles.py      # 다음에 프로필 등록

- 2026-11-11 Mike: "오디오북 1-30은 전부 보이스박스에서 한다", 인물 목소리는 ElevenLabs 1순위(cast_el.tsv).
- 30초 이하로 쉼에서 나누고, 조각마다 받아써서 reference_text로 쓴다. 받아쓰기는 로컬 Whisper(turbo).
  셸 기본 Gemini 키는 무료 등급이라 하루 20회에서 막혔다(11-11).
- 마르티: 1–9장 편지 음성은 5초뿐이라(편지 대부분이 11장 이후) 남은 예산으로 13장 편지 654자를 같은 목소리
  (Álvaro Sereno)로 만들어 el/marti.mp3로 쓴다. marti()는 쓰지 않는다(기록용).
- 전에 있던 ref/ 파일(1–9장 Gemini 음성 샘플)은 ref_gemini/로 옮긴다.
"""
import json
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import audiobook as A  # noqa: E402
from voicebox_gen import cut, save, REF, VB, PART  # noqa: E402

EL = VB / 'el'
OLD = VB / 'ref_gemini'
MARTI_CAP = 165.3


LANG = {'narr': 'ko', 'madre': 'ko'}


def heard(pcm, lang):
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / 'p.wav'
        save(wav, pcm)
        subprocess.run(['whisper', str(wav), '--model', 'turbo', '--language', lang, '--output_format', 'txt',
                        '--output_dir', d, '--verbose', 'False', '--fp16', 'False'], capture_output=True, check=True)
        return ' '.join((Path(d) / 'p.txt').read_text().split())


def decode(path):
    return subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(A.RATE), '-f', 's16le', '-'],
                          capture_output=True, check=True).stdout


def marti():
    """편지 조각은 대개 30초가 넘는다. 1–9장 마르티 편지를 원고 순서로 165.3초까지 이어 붙여 쉼에서 나누고 받아쓴다."""
    for f in REF.glob('marti_*'):
        f.unlink()
    pcm, total = b'', 0.0
    for c in range(1, 10):
        tl = A.OUT / f'ch{c:02d}.timeline.json'
        if not tl.exists():
            continue
        for p in json.loads(tl.read_text()):
            if p['who'] != 'marti' or total >= MARTI_CAP:
                continue
            seg = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{p["start"]:.3f}', '-to', f'{p["end"]:.3f}',
                                  '-i', str(A.OUT / f'ch{c:02d}.m4a'), '-ac', '1', '-ar', str(A.RATE), '-f', 's16le', '-'],
                                 capture_output=True, check=True).stdout
            pcm += (b'\0\0' * int(0.4 * A.RATE) if pcm else b'') + seg
            total = len(pcm) / 2 / A.RATE
    parts = cut(pcm, cap=MARTI_CAP)
    for i, p in enumerate(parts, 1):
        save(REF / f'marti_{i:02d}.wav', p)
        (REF / f'marti_{i:02d}.txt').write_text(heard(p, 'es').strip() + '\n')
    secs = [len(p) / 2 / A.RATE for p in parts]
    print(f'{"marti":15s} 조각 {len(parts)}개 {sum(secs):6.1f}초 (1–9장 편지)')


def main():
    OLD.mkdir(exist_ok=True)
    els = {m.stem for m in EL.glob('*.mp3')} | {'marti'}
    for f in REF.glob('*'):
        if f.stem.rsplit('_', 1)[0] in els:
            continue                      # 이번 방식으로 이미 만든 것
        if not (OLD / f.name).exists():
            shutil.move(str(f), OLD / f.name)
        else:
            f.unlink()
    for mp3 in sorted(EL.glob('*.mp3')):
        n = mp3.stem
        if (REF / f'{n}_01.txt').exists() and all(w.with_suffix('.txt').exists() for w in REF.glob(f'{n}_[0-9][0-9].wav')):
            continue
        parts = cut(A.level(A.trim(decode(mp3))), cap=10_000)
        for i, p in enumerate(parts, 1):
            save(REF / f'{n}_{i:02d}.wav', p)
            (REF / f'{n}_{i:02d}.txt').write_text(heard(p, LANG.get(n, 'es')).strip() + '\n')
        secs = [len(p) / 2 / A.RATE for p in parts]
        print(f'{n:15s} 조각 {len(parts)}개 {sum(secs):6.1f}초 ({", ".join(f"{s:.1f}" for s in secs)})', flush=True)


if __name__ == '__main__':
    main()
