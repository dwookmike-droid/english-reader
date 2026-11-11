"""그라시아의 열쇠 채널 OAuth 인증 (Mike가 직접 실행).

브라우저가 열리면 이 책을 올릴 채널의 계정으로 로그인하고, 채널(브랜드 계정)을 고른 뒤 권한을 허용한다.
업로드 + 재생목록 관리 권한으로 ~/yt-pipeline/oauth/token_gracia.json을 쓴다(양갱 채널 토큰은 건드리지 않음).
"""
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

OAUTH = Path("~/yt-pipeline/oauth").expanduser()
TOKEN = OAUTH / "token_gracia.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH / "client_secret.json"), SCOPES)
creds = flow.run_local_server(port=0, prompt="consent")
TOKEN.write_text(creds.to_json())
TOKEN.chmod(0o600)
ch = build("youtube", "v3", credentials=creds).channels().list(part="snippet", mine=True).execute()
print("저장했습니다:", TOKEN)
print("인증된 채널:", [i["snippet"]["title"] for i in ch.get("items", [])])
