"""최종판 한 장 마무리(11-14 Mike "끝나면 최종 폴더까지 만들어놔 유튜브는 알아서 교체하고").
  python3 post_chapter.py 2
1) out/스포티파이_올릴것/NN장_최종/ : 영상(mp4 있으면)·소리만(mp3)·제목과 설명·올리는 방법
2) 유튜브(영상이 있는 장만): 그 장 발행일(2장 11/16부터 매주 월요일 19:00 KST) 예약으로 새로 올리고,
   예약이 지난 장(이미 공개 시각이 지난 장)은 바로 공개. 같은 장의 옛 영상(공개·예약)은 새 것이 올라간 뒤 비공개로 돌린다.
   done.json에 key chNN_final로 남긴다. 이미 있으면 건너뜀.
"""
import datetime as dt, json, shutil, subprocess, sys
from pathlib import Path
AB = Path(__file__).resolve().parent
V = AB / 'video'
sys.path.insert(0, str(V / 'yt'))

def release(ch):
    """1·2장은 11-14·11-16에 나감. 3장부터 주 2회 월·목 19:00 KST(11-17 Mike), 3장 = 11-23(월)."""
    if ch <= 2:
        d = dt.date(2026, 11, 16) + dt.timedelta(weeks=ch - 2)
    else:
        d, k = dt.date(2026, 11, 23), 3
        while k < ch:
            d += dt.timedelta(days=3 if d.weekday() == 0 else 4)
            k += 1
    return dt.datetime(d.year, d.month, d.day, 10, 0, tzinfo=dt.timezone.utc)   # 19:00 KST

def main(ch):
    n = f'{ch:02d}'
    mp3, mp4 = AB / 'out' / 'vb_final' / f'ch{n}.mp3', V / 'out' / 'vb' / f'ch{n}.mp4'
    if not mp3.exists():
        sys.exit(f'{ch}장 최종 소리 없음')
    subprocess.run([sys.executable, str(V / 'yt_meta.py'), str(ch), '--vb', '--out', str(V / 'out' / f'meta_final{ch}.json')], check=True,
                   capture_output=True)
    desc = V / 'out' / 'desc' / f'ch{n}.txt'
    when = release(ch); kst = (when + dt.timedelta(hours=9)).strftime('%m/%d(%a) 19:00')
    D = AB / 'out' / '스포티파이_올릴것' / f'{ch}장_최종'; D.mkdir(parents=True, exist_ok=True)
    if mp4.exists(): shutil.copy(mp4, D / f'{ch}장_영상.mp4')
    shutil.copy(mp3, D / f'{ch}장_소리만.mp3'); shutil.copy(desc, D / f'{ch}장_제목과_설명.txt')
    (D / '올리는_방법.txt').write_text(
        f'스포티파이 {ch}장 (최종판)\n'
        f'1. creators.spotify.com → 에피소드 → {ch}장이 이미 있으면 열어서 새 파일 업로드로 교체, 없으면 새 에피소드\n'
        f'2. 파일: {ch}장_영상.mp4 (없거나 안 되면 {ch}장_소리만.mp3)\n'
        f'3. 제목: {ch}장_제목과_설명.txt 첫 줄 / 설명: 둘째 줄부터\n'
        f'4. 시즌 1, 에피소드 {ch}, 전체(Full), 클린, 공개 {kst}\n')
    print(f'{ch}장 스포티파이 폴더: {D}')
    if not mp4.exists():
        print(f'{ch}장 영상 없음(그림 없음) → 유튜브 건너뜀'); return
    done_p = V / 'out' / 'done.json'; done = json.loads(done_p.read_text())
    key = f'ch{n}_final'
    if key in done:
        print(f'{ch}장 유튜브 이미 올림 {done[key]["url"]}'); return
    meta = json.loads((V / 'out' / f'meta_final{ch}.json').read_text())
    for it in meta['items']:
        it['key'] = key; it['synthetic'] = True
        if when > dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1):
            it['publish_at'] = when.strftime('%Y-%m-%dT%H:%M:%SZ')
    (V / 'out' / f'meta_final{ch}.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    py = str(Path.home() / 'yt-pipeline/.venv/bin/python')
    r = subprocess.run([py, 'yt/yt_upload.py', 'upload', f'out/meta_final{ch}.json'], cwd=V, capture_output=True, text=True)
    print(r.stdout[-400:], r.stderr[-400:])
    done = json.loads(done_p.read_text())
    if key not in done:
        sys.exit(f'{ch}장 유튜브 업로드 실패')
    from yt_upload import load_creds
    from googleapiclient.discovery import build
    yt = build('youtube', 'v3', credentials=load_creds(), cache_discovery=False)
    if 'publish_at' not in meta['items'][0]:            # 발행일이 지난 장은 처리 끝나면 바로 공개
        subprocess.run([py, 'yt/yt_publish.py', 'out/done.json', key], cwd=V)
    for k, v in list(done.items()):                       # 같은 장 옛 영상 비공개(예약 포함)
        if k.startswith(f'ch{n}') and k != key and not v.get('deleted') and v.get('privacy') != 'private-old':
            try:
                st = yt.videos().list(part='status', id=v['id']).execute()['items']
                if not st:
                    continue
                st = st[0]['status']
                if st.get('publishAt') and st['privacyStatus'] == 'private':    # 아직 안 나간 옛 예약 → 지움(두 번 공개 막기)
                    yt.videos().delete(id=v['id']).execute(); v['deleted'] = dt.date.today().isoformat(); print('옛 예약 삭제', k, v['url'])
                else:
                    yt.videos().update(part='status', body={'id': v['id'], 'status': {'privacyStatus': 'private', 'embeddable': True, 'publicStatsViewable': True, 'containsSyntheticMedia': True, 'selfDeclaredMadeForKids': False}}).execute()
                    v['privacy'] = 'private-old'; print('옛 영상 비공개', k, v['url'])
            except Exception as e:
                print('옛 영상 처리 실패', k, e)
    done_p.write_text(json.dumps(done, ensure_ascii=False, indent=1))
    print(f'{ch}장 유튜브 {done[key]["url"]} 예약 {kst if "publish_at" in meta["items"][0] else "즉시 공개"}')

if __name__ == '__main__':
    main(int(sys.argv[1]))
