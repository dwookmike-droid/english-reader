"""grok_prompts.jsonl → Grok 작업 폴더(00_refs, ch01–ch30)와 폴더마다 PROMPTS.md.
python3 make_folders.py         (이 폴더에서. build.py를 다시 돌린 뒤에도 다시 돌린다. 이미 넣은 그림은 지우지 않는다)
python3 make_folders.py --all   (00_refs와 1–3장 PROMPTS.md까지 다시 쓴다. 기본은 4장부터만: 1–3장은 Grok이 이미 작업함)
"""
import json
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
items = [json.loads(l) for l in (H / 'grok_prompts.jsonl').read_text().splitlines() if l.strip()]
refs = [o for o in items if o['kind'] == 'reference']
scenes = [o for o in items if o['kind'] == 'scene']
PILOT = {1, 2, 3}
NEW_FROM = 4                     # build.py와 같은 값. 이 장부터 규칙·참고 그림 3장
ALL = '--all' in sys.argv

GROK_RULES = """## Instructions for Grok
- Make one image for each prompt below, in order. Use the prompt text exactly as written.
- Aspect ratio 16:9, landscape, the highest resolution available (1920×1080 or larger if possible).
- Same painting style in every image: soft watercolor and gouache book illustration.
- No readable text anywhere: no letters, numbers, signs, gate or platform signs, logos or watermarks.
- Paint the scene all the way to every edge. Never leave a blank band, border or empty strip at the bottom.
- The lower third should show only quiet floor, table, ground or water, because subtitles go over it. No faces or key objects there.
- If "Reference images" are listed, attach those files from the `00_refs` folder and keep the faces, hair, clothes and objects the same as in them.
- File names: save each image as the name in its heading (for example `{example}`).
  If you make more than one version, add `_1`, `_2`, `_3` before `.png` (for example `{example_v}`).
- Save the images in this folder only."""

GROK_RULES_NEW = (GROK_RULES
    .replace('- No readable text anywhere: no letters, numbers, signs, gate or platform signs, logos or watermarks.',
             '- No readable text anywhere: no letters, numbers, signs, gate or platform signs, logos or watermarks. '
             'Shop signs, street signs, awnings and plaques stay blank, even when the prompt names a place. '
             'Letters, notebooks, maps, screens and dates show only soft illegible marks.')
    .replace('- The lower third should show only quiet floor, table, ground or water, because subtitles go over it. No faces or key objects there.',
             '- Subtitles are added later over the bottom third. Do not draw any bar, band, border or empty strip yourself: '
             'paint the scene all the way to every edge, with the floor, table, ground or water continuing naturally into the lower third. '
             'Keep every face, hand, key and important object in the upper two-thirds.\n'
             '- Always a finished scene in its real place. Never a character sheet, never the same person twice, '
             'never people on a plain or blank background, never half of the frame left empty.')
    .replace('- If "Reference images" are listed, attach those files from the `00_refs` folder and keep the faces, hair, clothes and objects the same as in them.',
             '- If "Reference images" are listed (up to 3: people first, then an object or place), attach those files from the `00_refs` folder '
             'and keep the faces, hair, clothes, objects and rooms the same as in them. If only 2 can be attached, leave out the last one.'))


def block(o):
    out = [f'### {o["file"]}']
    if o.get('ko'):
        out.append(f'장면: {o["ko"]}')
    if o.get('reference_images'):
        out.append('Reference images: ' + ', '.join(f'`00_refs/{r}`' for r in o['reference_images']))
    out += ['', '```', o['prompt'], '```', '']
    return out


def write(folder, title, note, group, rules=GROK_RULES):
    folder.mkdir(exist_ok=True)
    ex = group[0]['file']
    md = [f'# {title}', '', note, '',
          rules.format(example=ex, example_v=ex.replace('.png', '_1.png')), '',
          f'## 만들 그림 {len(group)}장', '']
    md += ['- [ ] `' + o['file'] + '`' + (f' — {o["ko"]}' if o.get('ko') else '') for o in group]
    md.append('')
    md.append('## Prompts')
    md.append('')
    for o in group:
        md += block(o)
    (folder / 'PROMPTS.md').write_text('\n'.join(md))


if ALL:
  write(H / '00_refs', '참고 그림 (가장 먼저)',
      '인물·소품·장소 참고 그림 14장. 장면 그림을 만들기 전에 이 폴더부터 끝낸다. '
      '여기 그림이 장면마다 참고로 들어가므로, 마음에 드는 한 장만 정해진 이름으로 남긴다.', refs)

for ch in range(1 if ALL else NEW_FROM, 31):
    group = [o for o in scenes if o['ch'] == ch]
    tag = ' · 파일럿' if ch in PILOT else ''
    write(H / f'ch{ch:02d}', f'{ch}장 장면 그림{tag}',
          f'{ch}장 장면 {len(group)}장. `00_refs` 그림이 다 있어야 시작한다.', group,
          GROK_RULES_NEW if ch >= NEW_FROM else GROK_RULES)

print(('00_refs ' + str(len(refs)) + '장, ch01' if ALL else f'ch{NEW_FROM:02d}') + '–ch30',
      sum(o['ch'] >= (1 if ALL else NEW_FROM) for o in scenes), '장')
