"""올린 영상과 재생목록을 공개로 바꾼다(11-14 Mike "유튜브에는 다 올려줘", 허브에서 직접 지시).

  ~/yt-pipeline/.venv/bin/python yt/yt_publish.py out/done.json ch01_vb ch02_vb ch03_vb [--playlist 제목]

- done.json의 키마다 videos.update(privacyStatus=public). 처리(processing)가 안 끝났으면 건너뛰고 알린다.
- 바꾼 뒤 다시 읽어 public인지 확인하고 done.json의 privacy를 고친다.
- --playlist가 있으면 그 재생목록도 public으로.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from yt_upload import load_creds, reason_of  # noqa: E402
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ap = argparse.ArgumentParser()
ap.add_argument('done', type=Path)
ap.add_argument('keys', nargs='+')
ap.add_argument('--playlist')
a = ap.parse_args()
done = json.loads(a.done.read_text())
yt = build('youtube', 'v3', credentials=load_creds(), cache_discovery=False)
bad = 0
for k in a.keys:
    if k not in done:
        print(f'{k}: done.json에 없음'); bad += 1; continue
    vid = done[k]['id']
    v = yt.videos().list(part='status,processingDetails,snippet', id=vid).execute()['items'][0]
    proc = v.get('processingDetails', {}).get('processingStatus', '?')
    if v['status'].get('uploadStatus') != 'processed':
        print(f'{k}: 아직 처리 중({v["status"].get("uploadStatus")}/{proc}) — 건너뜀'); bad += 1; continue
    try:
        yt.videos().update(part='status', body={'id': vid, 'status': {
            'privacyStatus': 'public', 'selfDeclaredMadeForKids': False,
            'containsSyntheticMedia': True}}).execute()
    except HttpError as e:
        print(f'{k}: 공개 전환 실패 {reason_of(e) or e}'); bad += 1; continue
    now = yt.videos().list(part='status', id=vid).execute()['items'][0]['status']['privacyStatus']
    done[k]['privacy'] = now
    print(f'{k}: {now} {done[k]["url"]}')
    bad += now != 'public'
if a.playlist:
    for p in yt.playlists().list(part='snippet,status', mine=True, maxResults=50).execute().get('items', []):
        if p['snippet']['title'] == a.playlist:
            if p['status']['privacyStatus'] != 'public':
                yt.playlists().update(part='snippet,status', body={'id': p['id'], 'snippet': {'title': a.playlist},
                                      'status': {'privacyStatus': 'public'}}).execute()
            print(f'재생목록 공개: https://www.youtube.com/playlist?list={p["id"]}')
a.done.write_text(json.dumps(done, ensure_ascii=False, indent=1))
sys.exit(1 if bad else 0)
