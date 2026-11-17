"""장 하나의 유튜브 영상을 새 음원 영상으로 바꾼다(11-17 Mike "한 번에 고치기").
새 영상은 같은 발행 시각으로 예약(지났으면 바로 공개), 옛 영상은 지우지 않고 예약을 풀어 비공개로 둔다.
  python3.14 tools/yt_swap.py 3   (audiobook 폴더에서)
"""
import datetime as dt, json, re, subprocess, sys
from pathlib import Path
AB = Path(__file__).resolve().parent.parent
V = AB / 'video'
sys.path.insert(0, str(V / 'yt')); sys.path.insert(0, str(AB))
from post_chapter import release
ch = int(sys.argv[1]); n = f'{ch:02d}'
old_key, key = f'ch{n}_final', f'ch{n}_final2'
done_p = V / 'out' / 'done.json'
done = json.loads(done_p.read_text())
if key in done:
    sys.exit(f'{ch}장 이미 교체함 {done[key]["url"]}')
meta = json.loads((V / 'out' / f'meta_final{ch}.json').read_text())
it = meta['items'][0]
it['key'] = key; it.pop('publish_at', None)
it['file'] = str(V / 'out' / 'vb' / f'ch{n}.mp4')
tl = json.loads((AB / 'out' / 'vb_final' / f'ch{n}.timeline.json').read_text())
tl = tl if isinstance(tl, list) else next(v for v in tl.values() if isinstance(v, list))
starts = {}
for x in tl:
    starts.setdefault(x['scene'], x['start'])
times = [f'{int(t // 60)}:{int(t % 60):02d}' for t in starts.values()]
lines, k = it['description'].split('\n'), 0
for i, l in enumerate(lines):                       # '장면' 목록의 시각을 새 음원에 맞춘다
    m = re.match(r'^(\d+:\d\d) ', l)
    if m and k < len(times):
        lines[i] = times[k] + l[len(m.group(1)):]; k += 1
it['description'] = '\n'.join(lines)
when = release(ch)
if when > dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1):
    it['publish_at'] = when.strftime('%Y-%m-%dT%H:%M:%SZ')
mp = V / 'out' / f'meta_final{ch}b.json'
mp.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
py = str(Path.home() / 'yt-pipeline/.venv/bin/python')
r = subprocess.run([py, 'yt/yt_upload.py', 'upload', str(mp.relative_to(V))], cwd=V, capture_output=True, text=True)
print(r.stdout[-300:], r.stderr[-300:])
done = json.loads(done_p.read_text())
if key not in done:
    sys.exit(f'{ch}장 업로드 실패')
from yt_upload import load_creds
from googleapiclient.discovery import build
yt = build('youtube', 'v3', credentials=load_creds(), cache_discovery=False)
if 'publish_at' not in it:
    subprocess.run([py, 'yt/yt_publish.py', 'out/done.json', key], cwd=V)
if old_key in done:
    yt.videos().update(part='status', body={'id': done[old_key]['id'], 'status': {'privacyStatus': 'private', 'embeddable': True, 'publicStatsViewable': True, 'containsSyntheticMedia': True, 'selfDeclaredMadeForKids': False}}).execute()
    done = json.loads(done_p.read_text())
    done[old_key]['privacy'] = 'private-old'; done[old_key]['replaced_by'] = key
    done_p.write_text(json.dumps(done, ensure_ascii=False, indent=1))
print(f'{ch}장 새 영상 {done[key]["url"]} 예약 {it.get("publish_at", "즉시 공개")} / 옛 영상 {done[old_key]["url"]} 비공개')
