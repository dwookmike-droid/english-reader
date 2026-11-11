"""배포용 장 오디오와 설명을 k-insider-podcast 저장소(비공개)에 올린다. 피클이 거기서 스포티파이·애플 팟캐스트에 등록한다.

  python3 audiobook/publish_podcast.py 2 3        # 2·3장
  python3 audiobook/publish_podcast.py 4 --dry    # 무엇을 올릴지만 본다

- 올리는 것: out/pilot/final/chNN.mp3 → audiobook/chNN/chNN.mp3, video/out/desc/chNN.txt → audiobook/chNN/chNN.txt
  (1장 때 피클 작업지시서와 같은 자리·이름·커밋 메시지)
- 그 저장소의 다른 변경은 건드리지 않는다. 이 두 파일만 add·commit 한 뒤 main에 push.
- 이미 같은 내용이 올라가 있으면 건너뛴다. mp3나 설명이 없으면 그 장은 올리지 않고 알린다.
- 2026-11-10 Mike: "2,3,4등 올라올때마다 아까 피클이 했던것처럼 푸시 해서 자동등록되게해"
- 2026-11-10 Mike: "유튜브 랜더링까지 다 되고나면 올릴거야" → 그 장의 영상(video/out/chNN.mp4)이 없거나
  배포용 mp3보다 오래됐으면 올리지 않는다.
"""
import argparse
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

AB = Path(__file__).resolve().parent
FINAL = AB / 'out' / 'pilot' / 'final'
DESC = AB / 'video' / 'out' / 'desc'
REPO = Path('~/Library/Mobile Documents/com~apple~CloudDocs/K-Insider Podcast/k-insider-podcast').expanduser()


def git(*args, check=True):
    return subprocess.run(['git', '-C', str(REPO), *args], capture_output=True, text=True, check=check).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('chapters', nargs='+', type=int)
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()

    git('fetch', '-q')
    if 'behind' in git('status', '-sb').splitlines()[0]:
        git('pull', '-q', '--ff-only')

    done = []
    for ch in a.chapters:
        mp3, txt = FINAL / f'ch{ch:02d}.mp3', DESC / f'ch{ch:02d}.txt'
        if not mp3.exists() or not txt.exists():
            print(f'{ch}장: 건너뜀 (없음: {", ".join(p.name for p in (mp3, txt) if not p.exists())})')
            continue
        mp4 = AB / 'video' / 'out' / f'ch{ch:02d}.mp4'
        if not mp4.exists() or mp4.stat().st_mtime < mp3.stat().st_mtime:
            print(f'{ch}장: 건너뜀 (유튜브 영상 렌더가 아직 안 됨: {mp4.name})')
            continue
        dst = REPO / 'audiobook' / f'ch{ch:02d}'
        pairs = [(mp3, dst / mp3.name), (txt, dst / txt.name)]
        if all(d.exists() and filecmp.cmp(s, d, shallow=False) for s, d in pairs):
            print(f'{ch}장: 이미 같은 파일이 올라가 있음')
            continue
        print(f'{ch}장: {mp3.stat().st_size / 1e6:.1f} MB + 설명 → {dst.relative_to(REPO)}')
        if a.dry:
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for s, d in pairs:
            shutil.copy2(s, d)
        paths = [str(d.relative_to(REPO)) for _, d in pairs]
        git('add', '--', *paths)
        git('commit', '-q', '-m',
            f'feat: add La llave de Gracia ch{ch:02d} audio & desc for podcast release\n\n'
            'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>', '--', *paths)
        done.append(ch)

    if done and not a.dry:
        git('push', '-q', 'origin', 'main')
        print('push 완료:', git('log', '--oneline', f'-{len(done)}').strip())


if __name__ == '__main__':
    sys.exit(main())
