"""Grok 작업 폴더의 그림을 render.py가 읽는 곳(audiobook/video/img/chNN_sMM.png)으로 모은다.
python3 collect.py          모든 장
python3 collect.py 1 2 3    그 장만
python3 collect.py --check  복사하지 않고 상태만 본다

고르는 규칙 (장면마다):
  1. 정해진 이름(ch01_s01.png, .jpg/.jpeg/.webp도 됨)이 있으면 그것을 쓴다.
  2. 없고 버전(ch01_s01_1.png …)이 하나뿐이면 그것을 쓴다.
  3. 버전이 여럿이면 쓰지 않고 '고를 것'으로 알린다 → 고른 파일 이름에서 _숫자를 지우면 된다.
PNG로 바꿔 img/에 넣는다. 16:9가 아니거나 가로 1280 미만이면 경고한다(render.py가 가운데를 잘라 맞춘다).
"""
import json, re, sys
from pathlib import Path
from PIL import Image

H = Path(__file__).resolve().parent
IMG = H.parent / 'img'
EXT = ('.png', '.jpg', '.jpeg', '.webp')
items = [json.loads(l) for l in (H / 'grok_prompts.jsonl').read_text().splitlines() if l.strip()]

args = [a for a in sys.argv[1:] if not a.startswith('--')]
check = '--check' in sys.argv
chs = {int(a) for a in args} or set(range(1, 31))


def find(folder, stem):
    exact = [folder / (stem + e) for e in EXT if (folder / (stem + e)).exists()]
    if exact:
        return exact[0], []
    vers = sorted(p for p in folder.glob(stem + '_*') if p.suffix.lower() in EXT and re.fullmatch(re.escape(stem) + r'_\d+', p.stem))
    return (vers[0], vers) if len(vers) == 1 else (None, vers)


def warn_size(p):
    with Image.open(p) as im:
        w, h = im.size
    out = []
    if abs(w / h - 16 / 9) > 0.03:
        out.append(f'비율 {w}×{h} (16:9 아님, 가운데를 잘라 씀)')
    if w < 1280:
        out.append(f'가로 {w}px (작음)')
    return out


miss, pick, done, warns = [], [], 0, []
for o in items:
    if o['kind'] == 'reference':
        folder, stem = H / '00_refs', Path(o['file']).stem
        src, vers = find(folder, stem)
        if not src:
            (pick if vers else miss).append(f'00_refs/{o["file"]}' + (f' ({len(vers)}개 중 고를 것)' if vers else ''))
        continue
    if o['ch'] not in chs:
        continue
    folder, stem = H / f'ch{o["ch"]:02d}', Path(o['file']).stem
    src, vers = find(folder, stem)
    if not src:
        (pick if vers else miss).append(f'ch{o["ch"]:02d}/{o["file"]}' + (f' ({len(vers)}개 중 고를 것)' if vers else ''))
        continue
    warns += [f'{src.name}: {w}' for w in warn_size(src)]
    dst = IMG / o['file']
    if check or (dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime):
        done += dst.exists()
        continue
    IMG.mkdir(exist_ok=True)
    with Image.open(src) as im:
        im.convert('RGB').save(dst)
    done += 1

print(f'img/에 있음 {done}장' + (' (확인만)' if check else ''))
for title, rows in (('고를 것', pick), ('없음', miss), ('경고', warns)):
    if rows:
        print(f'\n{title} {len(rows)}:')
        print('\n'.join('  ' + r for r in rows))
