"""그라시아의 열쇠 채널 유튜브 업로드 (양갱 채널 yt_upload.py 복사본, 토큰만 다름).

사용:
  ~/yt-pipeline/.venv/bin/python yt_upload.py check  <meta.json>   # 파일·메타만 점검, 업로드 안 함
  ~/yt-pipeline/.venv/bin/python yt_upload.py upload <meta.json> [--only key1 key2]

meta.json: {"items": [{"key", "file", "title", "description", "tags", "playlist"}...]}

- 항상 비공개 / 아동용 아님 / 구독자 알림 끔. 올린 직후 실제 상태를 읽어 private가 아니면
  고치고, 그래도 아니면 멈춘다.
- 올린 건 meta.json 옆 done.json에 key → video id로 남기고, 다시 돌리면 건너뛴다.
- 인증은 ~/yt-pipeline/oauth/token_gracia.json. 토큰이 만료돼 갱신이 안 되면
  새로 인증하지 않고 멈춘다(브라우저 인증은 사용자가 한다).
- uploadLimitExceeded / quotaExceeded가 나면 다음 항목으로 넘어가지 않고 멈춘다.
- 재생목록 추가는 youtube 또는 youtube.force-ssl 권한이 필요하다. 토큰에 없으면
  건너뛰고 done.json에 playlist_pending으로 남긴다.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError, ResumableUploadError
from googleapiclient.http import MediaFileUpload

TOKEN = Path("~/yt-pipeline/oauth/token_gracia.json").expanduser()
STOP_REASONS = {"uploadLimitExceeded", "quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}
PLAYLIST_SCOPES = {"https://www.googleapis.com/auth/youtube",
                   "https://www.googleapis.com/auth/youtube.force-ssl"}


def load_creds() -> Credentials:
    data = json.loads(TOKEN.read_text())
    creds = Credentials.from_authorized_user_info(data, data.get("scopes"))
    if not creds.valid:
        try:
            creds.refresh(Request())
        except RefreshError as e:
            sys.exit(f"인증 오류: 토큰 갱신 실패 — 새로 인증하지 않고 멈춥니다. ({e})")
        data.update(json.loads(creds.to_json()))
        TOKEN.write_text(json.dumps(data))
    return creds


def reason_of(err: Exception) -> str:
    try:
        body = json.loads(err.content.decode())  # type: ignore[attr-defined]
        return body["error"]["errors"][0].get("reason", "")
    except Exception:
        return ""


def find_or_create_playlist(yt, title: str, cache: dict) -> str:
    if title in cache:
        return cache[title]
    req = yt.playlists().list(part="snippet", mine=True, maxResults=50)
    while req:
        res = req.execute()
        for p in res.get("items", []):
            cache[p["snippet"]["title"]] = p["id"]
        req = yt.playlists().list_next(req, res)
    if title not in cache:
        res = yt.playlists().insert(part="snippet,status", body={
            "snippet": {"title": title}, "status": {"privacyStatus": "private"}}).execute()
        cache[title] = res["id"]
    return cache[title]


def ensure_private(yt, vid: str) -> str:
    """올린 직후 실제 공개 상태를 읽고, private가 아니면 private로 바꾼 뒤 다시 읽는다.
    2026-11-02부터 API 업로드도 비공개로 고정되지 않아서 넣은 확인."""
    def read():
        items = yt.videos().list(part="status", id=vid).execute().get("items", [])
        return items[0]["status"].get("privacyStatus", "?") if items else "없음"
    try:
        p = read()
        if p == "private":
            return p
        print(f"  공개 상태가 {p} → private로 바꿉니다", flush=True)
        yt.videos().update(part="status", body={"id": vid, "status": {
            "privacyStatus": "private", "selfDeclaredMadeForKids": False}}).execute()
        return read()
    except HttpError as e:
        return f"확인 실패 ({reason_of(e) or e})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "upload"])
    ap.add_argument("meta", type=Path)
    ap.add_argument("--only", nargs="+")
    a = ap.parse_args()

    meta = json.loads(a.meta.read_text())
    done_path = a.meta.with_name("done.json")
    done = json.loads(done_path.read_text()) if done_path.exists() else {}
    items = [i for i in meta["items"] if not a.only or i["key"] in a.only]

    for it in items:
        f = Path(it["file"])
        size = f.stat().st_size / 1e9 if f.exists() else -1
        state = "올림 " + done[it["key"]]["id"] if it["key"] in done else "대기"
        print(f"[{state}] {it['key']}: {it['title']} ({size:.2f}GB) → {it.get('playlist')}")
        if size < 0:
            print("  파일 없음")
    if a.cmd == "check":
        return 0

    creds = load_creds()
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    can_playlist = bool(PLAYLIST_SCOPES & set(creds.scopes or []))
    pl_cache: dict = {}

    for it in items:
        if it["key"] in done:
            continue
        body = {
            "snippet": {"title": it["title"], "description": it.get("description", ""),
                        "tags": it.get("tags", []), "categoryId": "19", "defaultLanguage": "ko"},
            "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
        }
        media = MediaFileUpload(it["file"], chunksize=64 * 1024 * 1024, resumable=True,
                                mimetype="video/mp4")
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media,
                                 notifySubscribers=False)
        print(f"업로드: {it['title']}", flush=True)
        resp, last = None, -1
        try:
            while resp is None:
                status, resp = req.next_chunk(num_retries=5)
                if status:
                    pct = int(status.progress() * 100)
                    if pct // 5 != last // 5:
                        print(f"  {pct}%", flush=True)
                        last = pct
        except (HttpError, ResumableUploadError) as e:
            r = reason_of(e)
            print(f"  실패: {r or e}", flush=True)
            if r in STOP_REASONS or getattr(e, "resp", None) is not None and e.resp.status in (401, 403):
                print("  업로드 한도·권한 문제라 여기서 멈춥니다.")
                return 2
            continue
        vid = resp["id"]
        rec = {"id": vid, "url": f"https://youtu.be/{vid}", "title": it["title"],
               "uploaded": time.strftime("%Y-%m-%d %H:%M:%S")}
        rec["privacy"] = ensure_private(yt, vid)
        if rec["privacy"] != "private":
            done[it["key"]] = rec
            done_path.write_text(json.dumps(done, ensure_ascii=False, indent=1))
            print(f"  비공개 확인 실패({rec['privacy']}) — 여기서 멈춥니다. {rec['url']}", flush=True)
            return 3
        if it.get("playlist"):
            if can_playlist:
                try:
                    pid = find_or_create_playlist(yt, it["playlist"], pl_cache)
                    yt.playlistItems().insert(part="snippet", body={"snippet": {
                        "playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
                    rec["playlist"] = it["playlist"]
                except HttpError as e:
                    rec["playlist_pending"] = f"{it['playlist']} ({reason_of(e) or e})"
            else:
                rec["playlist_pending"] = f"{it['playlist']} (토큰에 재생목록 권한 없음)"
        done[it["key"]] = rec
        done_path.write_text(json.dumps(done, ensure_ascii=False, indent=1))
        print(f"  완료 {rec['url']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
