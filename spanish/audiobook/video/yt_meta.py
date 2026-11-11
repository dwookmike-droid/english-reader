"""유튜브 업로드용 meta.json 초안과 설명란 타임스탬프를 만든다. 업로드는 하지 않는다.

  python3 audiobook/video/yt_meta.py 1 2 3            # → video/out/meta.json, video/out/desc/chNN.txt
  python3 audiobook/video/yt_meta.py 1-30 --book      # 책 전체를 이어 붙인 영상 하나일 때의 장 타임스탬프도

장 영상 하나의 설명란 타임스탬프 = 장면(scenes.tsv의 한국어 설명) 시작 시각.
유튜브 '챕터' 규칙: 첫 줄 0:00, 3개 이상, 각 10초 이상 → 10초 미만 장면은 앞 장면에 합친다.

meta.json 형식은 업로드 스크립트(yt_upload.py 복사본)가 읽는 것과 같다:
  {"items": [{"key","file","title","description","tags","playlist"}]}
그 밖의 키(category, contains_synthetic_media, language)는 복사본이 읽도록 고칠 때 쓰는 참고값.
설명란에 꺾쇠(<, >)는 넣지 않는다(유튜브가 거부).
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render  # noqa: E402
from render import OUT, audio_duration, chapter_title, load_scenes  # noqa: E402

BOOK = '그라시아의 열쇠'
PLAYLIST = f'{BOOK} · 스페인어 듣는 소설'
TAGS = ['스페인어', '스페인어 공부', '스페인어 듣기', '오디오북', '소설', '바르셀로나',
        '그라시아의 열쇠', 'Spanish', 'learn Spanish', 'audiobook', 'Korean']
MIN_CHAPTER = 10.0
GAP = 0.0          # --book: 장 사이에 따로 넣는 간격(간주가 장 파일에 이미 들어 있으면 0)


def ts(t):
    t = int(t)
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'


def scene_marks(ch, items, labels, duration):
    """[(시각, 설명)] 장면 단위. 0:00 시작, 10초 미만은 합침."""
    first = {}
    for it in items:
        first.setdefault(it['scene'], it['start'])
    marks = []
    for i, s in enumerate(sorted(first)):
        t = 0.0 if i == 0 else first[s]
        marks.append([t, labels.get((ch, s), f'장면 {s}')])
    out = []
    for k, (t, label) in enumerate(marks):
        nxt = marks[k + 1][0] if k + 1 < len(marks) else duration
        if out and nxt - t < MIN_CHAPTER:          # 짧은 장면은 앞에 붙인다
            continue
        if out and t - out[-1][0] < MIN_CHAPTER:
            out[-1][1] += f' / {label}'
            continue
        out.append([t, label])
    return out if len(out) >= 3 else []           # 3개 미만이면 유튜브가 챕터로 안 씀 → 생략


def phrases(items, n=12):
    """그 장의 스페인어 대사 중 뜻풀이가 있는 것(중복 제외), 앞에서부터 n개."""
    seen, out = set(), []
    for it in items:
        if it['kind'] == 'say' and it.get('gloss'):
            es = it['text'].strip()
            if es.lower() not in seen and len(es) <= 60:
                seen.add(es.lower())
                out.append((es, it['gloss'].strip()))
    return out[:n]


def clean(s):
    return s.replace('<', '‹').replace('>', '›')


def describe(ch):
    tl = render.AUDIO / f'ch{ch:02d}.timeline.json'
    if not tl.exists():
        return None
    items = json.loads(tl.read_text())
    duration = audio_duration(render.AUDIO / f'ch{ch:02d}.m4a')
    n, es, ko = chapter_title(ch)
    title = f'{BOOK} {n}장 · {es} ({ko}) | 스페인어 듣는 소설'
    lines = [
        f'「{BOOK}」 {n}장 「{es}」',
        '돌아가신 외할머니의 편지 열한 통과 열쇠 하나를 들고 바르셀로나 그라시아에 간 윤하의 이야기. '
        '한국어로 읽고, 대사는 스페인어로 듣습니다. 화면에 스페인어와 한국어 뜻이 함께 나옵니다.',
        '',
    ]
    marks = scene_marks(ch, items, load_scenes(), duration)
    if marks:
        lines.append('장면')
        lines += [f'{ts(t)} {label}' for t, label in marks]
        lines.append('')
    ph = phrases(items)
    if ph:
        lines.append('이 장의 스페인어')
        lines += [f'· {a} — {b}' for a, b in ph]
        lines.append('')
    lines += [
        '낭독: AI 합성 음성(Google Gemini TTS, 편지 낭독 ElevenLabs). 그림: AI 생성(Grok).',
        '음악: AI 생성(Stable Audio). Powered by Stability AI',
        f'#스페인어 #스페인어공부 #오디오북',
    ]
    desc = clean('\n'.join(lines))
    item = {
        'key': f'ch{ch:02d}',
        'file': str((OUT / f'ch{ch:02d}.mp4').resolve()),
        'title': clean(title)[:100],
        'description': desc,
        'tags': TAGS,
        'playlist': PLAYLIST,
        'category': '27',                         # Education (업로드 원본 스크립트는 19 고정 → 복사본에서 바꿀 것)
        'language': 'ko',
        'contains_synthetic_media': False,        # VIDEO.md '유튜브 합성 콘텐츠 표시' 참고
    }
    return item, duration


def check(item):
    errs = []
    if len(item['title']) > 100:
        errs.append('제목 100자 초과')
    if len(item['description'].encode()) > 5000:
        errs.append('설명 5000바이트 초과')
    if re.search('[<>]', item['title'] + item['description']):
        errs.append('꺾쇠 포함')
    if sum(len(t) for t in item['tags']) + 2 * len(item['tags']) > 500:
        errs.append('태그 500자 초과')
    if not Path(item['file']).exists():
        errs.append('영상 파일 아직 없음')
    return errs


def chapters_arg(xs):
    out = []
    for x in xs:
        if '-' in x:
            a, b = x.split('-')
            out += range(int(a), int(b) + 1)
        else:
            out.append(int(x))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('chapters', nargs='+')
    ap.add_argument('--book', action='store_true', help='책 전체 영상 하나일 때의 장 타임스탬프')
    ap.add_argument('--out', default=str(OUT / 'meta.json'))
    ap.add_argument('--src', help='소리·시간표 폴더(기본 audiobook/out/pilot/final)')
    a = ap.parse_args()
    if a.src:
        render.set_src(a.src)
    items, book, t = [], [], 0.0
    (OUT / 'desc').mkdir(parents=True, exist_ok=True)
    for ch in chapters_arg(a.chapters):
        r = describe(ch)
        if not r:
            print(f'{ch}장: 시간표 없음, 건너뜀')
            continue
        item, dur = r
        items.append(item)
        (OUT / 'desc' / f'ch{ch:02d}.txt').write_text(item['title'] + '\n\n' + item['description'] + '\n')
        n, es, ko = chapter_title(ch)
        book.append(f'{ts(t)} {n}장 {es}')
        t += dur + GAP
        errs = check(item)
        print(f'{item["key"]}: {item["title"]}  ({len(item["description"].encode())}바이트)'
              + (f'  ! {", ".join(errs)}' if errs else ''))
    Path(a.out).write_text(json.dumps({'items': items}, ensure_ascii=False, indent=1))
    print(f'→ {a.out}')
    if a.book:
        p = OUT / 'desc' / 'book_timestamps.txt'
        p.write_text('\n'.join(book) + '\n')
        print(f'→ {p}\n' + '\n'.join(book))


if __name__ == '__main__':
    main()
