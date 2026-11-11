"""style.md + scenes.tsv → Grok에 그대로 붙여 넣을 완성 프롬프트(grok_prompts.md, grok_prompts.jsonl).
python3 build.py  (이 폴더에서). 원본을 고치면 다시 돌린다."""
import json, re, unicodedata
from pathlib import Path
H = Path(__file__).resolve().parent
style = (H.parent / 'style.md').read_text()
blocks = re.findall(r'```\n(.*?)\n```', style, re.S)
STYLE, MEMORY = blocks[0].strip(), blocks[1].strip()
sheet = dict(re.findall(r'\*\*([^*]+)\*\* — `([^`]+)`', style))
place = dict(re.findall(r'- \*\*([^*]+)\*\*: `([^`]+)`', style))
rows = [l.rstrip('\n').split('\t') for l in (H.parent / 'scenes.tsv').read_text().splitlines()[1:]]

def slug(name):
    n = unicodedata.normalize('NFKD', name.split(' (')[0].lower()).encode('ascii', 'ignore').decode()
    return 'ref_' + re.sub(r'[^a-z]+', '_', n).strip('_') + '.png'


STYLE_REF = STYLE.replace(' small figures,', '').replace(' 16:9 landscape. The painting fills the whole frame edge to edge, with no blank band, border or frame; the lower third shows only quiet floor, table, ground or water, nothing important.', '')


def has(p, pat):
    return re.search(pat, p, re.I) is not None

# 인물: (시트 이름, 찾는 패턴). 앞의 것이 뒤의 것을 가리지 않게 순서대로 지운 뒤 찾는다
PEOPLE = [("Yuna's mother (today)", r"Yuna's mother"), ('Young Martí (1978, memory/photo only)', r'young Martí'),
          ('Young Sun-rye (1978, memory/photo only)', r'young Sun-rye'), ('Young Montse (1978, memory only)', r'young Montse'),
          ('The child (Yuna\'s mother at 3, 1978)', r'three-year-old|little girl|the child\b'),
          ('Yuna', r'\bYuna\b'), ('Montse', r'\bMontse\b'), ('Vale', r'\bVale\b'), ('Marc', r'\bMarc\b'), ('Joan', r'\bJoan\b')]
PLACES = [('Montse\'s kitchen', r"Montse's kitchen"), ('The rooftop (azotea)', r'rooftop'), ('The patio', r'\bpatio\b'),
          ('The workshop basement', r'basement'), ("Marc's workshop (ground floor)", r'workshop(?! van)'),
          ('Plaça de la Vila', r'Plaça de la Vila'), ('Gràcia street (Montse\'s street)', r'Gràcia street')]
OBJ = [('a small, finger-length brass key, heavier than it looks, a five-petal flower carved on its handle.', r'\bkey\b'),
       ('The grandfather clock: taller than a person, dark almost-black wood, small five-petal flowers carved on its sides, white dial with Roman numerals, tiny gold lettering on the dial (illegible), long glass door with thin metal rods like harp strings inside.', r'grandfather clock'),
       ('The pendulum: long iron rod ending in a palm-sized round brass disc engraved with a five-petal flower, polished like a small moon.', r'(?<!empty )pendulum(?! space)'),
       ('Marc\'s Vespa: old sky-blue Vespa.', r'Vespa')]

def season(ch):
    if ch <= 11 or ch == 30: return 'Season: August, hot white Mediterranean light.'
    if ch <= 18: return 'Season: September, softer golden light.'
    if ch <= 25: return 'Season: October, grey and cooler, soft overcast light.'
    return 'Season: November, cold and clear.'

def yuna_line(ch):
    s = sheet['Yuna']
    if 12 <= ch <= 21: s += ' Light grey cardigan over the shirt.'
    elif 22 <= ch <= 29: s += ' Charcoal wool coat.'
    return s

def variant(name, ch, p):
    s = sheet[name]
    if name == 'Montse':
        s += {16: ' Tonight: blue dress, no apron, hair neatly combed, small evening handbag.',
              24: ' Today: hiking boots, small backpack.', 29: ' Today: sunglasses, handbag.'}.get(ch, '')
    if name == 'Marc':
        s = s.replace(' Rides an old sky-blue Vespa.', '')     # 베스파가 없는 장면에 끼어들지 않게
        if has(p, r'workshop|basement'): s += ' Here: oil-stained work apron.'
        s += {23: ' Today: dark jacket, white shirt.', 25: ' Today: dark jacket, white shirt.',
              26: ' Today: grey sweater.'}.get(ch, '')
    return s

out, md = [], []
# 1) 참고 그림(인물 설정표·소품·장소) — 먼저 만든다
refs = []
for name, line in sheet.items():
    refs.append((slug(name),
                 f'{STYLE_REF} Character reference sheet: one figure shown twice, front view and side view, full body, standing, plain light warm-paper background, nothing else in the frame. {line}'))
refs.append(('ref_clock.png', f'{STYLE_REF} Object reference: {OBJ[1][0]} Shown alone, front view, plain light background.'))
refs.append(('ref_key.png', f'{STYLE_REF} Object reference: {OBJ[0][0]} Shown alone on a plain light surface, close up.'))
refs.append(('ref_kitchen.png', f'{STYLE} Place reference, no people: {place["Montse\'s kitchen"]}'))
refs.append(('ref_basement.png', f'{STYLE} Place reference, no people: {place["The workshop basement"]}'))
for f, p in refs:
    out.append(dict(file=f, kind='reference', prompt=p))

# 4장부터 바꾼 규칙(2026-11-10, 1·2장 검수 결과). 1–3장은 이미 만들어서 그대로 둔다.
NEW_FROM = 4
LOWER_OLD = 'the lower third shows only quiet floor, table, ground or water, nothing important.'
LOWER_NEW = ('keep every face, hand, key and important object in the upper two-thirds; the floor, table, ground or water '
             'continues naturally into the lower third (subtitles go there later, so do not paint any bar or empty strip). '
             'A finished scene in its real place: not a character sheet, no person shown twice, no blank background.')
TEXT_OLD = 'No readable text anywhere.'
TEXT_NEW = ('No readable text anywhere: shop signs, street signs, awnings, labels and plaques are blank; '
            'handwriting, maps, screens, dials and dates appear only as soft illegible marks, never as letters or numbers.')
# 참고 그림: 인물 2장 + 소품·장소 1장(최대 3장). 드문 인물이 먼저(흔들리기 쉬움)
REF_PRIORITY = ["Yuna's mother (today)", 'Young Martí (1978, memory/photo only)', 'Young Sun-rye (1978, memory/photo only)',
                'Young Montse (1978, memory only)', "The child (Yuna's mother at 3, 1978)", 'Joan',
                'Yuna', 'Montse', 'Marc', 'Vale']
REF_THINGS = [('ref_clock.png', r'grandfather clock'), ('ref_key.png', r'\bkey\b'),
              ('ref_basement.png', r'basement'), ('ref_kitchen.png', r"Montse's kitchen")]

# 2) 장면 132개
for ch, sc, prefix, prompt, ko in rows:
    ch, sc = int(ch), int(sc)
    new = ch >= NEW_FROM
    parts = [STYLE.replace(LOWER_OLD, LOWER_NEW) if new else STYLE]
    if prompt.startswith('A 1978 memory'): parts.append(MEMORY)
    parts.append(prompt)
    rest, used = prompt, []
    for name, pat in PEOPLE:
        if has(rest, pat):
            used.append(name)
            parts.append(yuna_line(ch) if name == 'Yuna' else variant(name, ch, prompt))
            rest = re.sub(pat, ' ', rest, flags=re.I)
    for name, pat in PLACES:
        if has(prompt, pat):
            parts.append(place[name]); break
    for line, pat in OBJ:
        if has(prompt, pat) and line not in ' '.join(parts) and not has(prompt, r'five-petal|harp|sky-blue'):
            parts.append(line)
    if not prompt.startswith('A 1978 memory') and not prompt.startswith('A small black-and-white photograph'):
        parts.append(season(ch))
    parts.append(TEXT_NEW if new else TEXT_OLD)
    if new:
        people = sorted(used, key=REF_PRIORITY.index)[:2]
        thing = next((f for f, pat in REF_THINGS if has(prompt, pat)), None)
        refs_for = [slug(n) for n in people] + ([thing] if thing else [])
    else:
        refs_for = [slug(n) for n in used][:2]
    out.append(dict(file=f'ch{ch:02d}_s{sc:02d}.png', kind='scene', ch=ch, scene=sc, ko=ko,
                    reference_images=refs_for, prompt=' '.join(parts)))

(H / 'grok_prompts.jsonl').write_text(''.join(json.dumps(o, ensure_ascii=False) + '\n' for o in out))
md = ['# Grok 이미지 프롬프트 (자동 생성: build.py)', '',
      '- 순서대로 만든다. 먼저 `reference` 그림(인물·소품·장소)을 만들고, 장면은 `참고 그림`에 적힌 그림을 함께 넣는다(도구가 허용하면, 최대 2장).',
      '- 비율 16:9. 파일 이름은 `file` 그대로 `audiobook/video/img/`에 저장.',
      '- 글자가 보이는 그림, 사람 수가 틀린 그림, 아래 1/3에 중요한 물건이 있는 그림은 다시 만든다.', '']
for o in out:
    md.append(f'## {o["file"]}' + (f' — {o["ko"]}' if o.get('ko') else ' — 참고 그림'))
    if o.get('reference_images'): md.append(f'참고 그림: {", ".join(o["reference_images"])}')
    md += ['', '```', o['prompt'], '```', '']
(H / 'grok_prompts.md').write_text('\n'.join(md))
print(len(out), '개', sum(o['kind'] == 'scene' for o in out), '장면')
