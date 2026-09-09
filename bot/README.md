# 청주 출발 항공권 시세 봇

텔레그램으로 청주(CJJ) 출발 오키나와·대만 왕복 시세를 알려준다.
값을 보내면 살 만한지 추천도로 답하고, 매일 아침 요약을 보낸다.

## 데이터는 한 곳에만 있다

시세·여행창 값은 `trip.html` 안의
`<script type="application/json" id="fare-data">` 블록에만 있다.
웹페이지와 이 봇이 같은 블록을 읽으므로 값이 어긋날 일이 없다.
**값을 고칠 때는 그 블록만 고치면 페이지와 봇에 함께 반영된다.**

## 켜는 순서

1. 텔레그램에서 `@BotFather` → `/newbot` (이미 있으면 `/token`으로 토큰 확인)
2. 만든 봇과 대화를 시작하고 아무 메시지나 보낸다
3. 대화 ID 확인:
   `https://api.telegram.org/bot<토큰>/getUpdates` 를 열어 `chat.id` 값을 본다
4. 저장소 **Settings → Secrets and variables → Actions**에서 두 개를 등록한다
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. **Actions** 탭에서 `항공권 시세 봇` → `Run workflow` → `digest`로 한 번 눌러 확인

토큰은 저장소 파일이나 대화창에 절대 넣지 말고 Secrets에만 둔다.

## 봇 사용법

| 보내는 말 | 하는 일 |
|---|---|
| `오키나와 11월 245000` | 그 노선·그 달 시세에서 추천도를 매겨 답한다 |
| `대만 12월 310000` | 〃 |
| `245000` | 목적지를 빼면 오키나와, 달을 빼면 11월로 본다 |
| `/시세` | 여섯 조합 요약과 주말 낀 추천 기간 |
| `/도움` | 사용법 |

## 직접 돌려보기

```bash
python3 bot/fare_bot.py digest --dry-run          # 보낼 요약을 화면에 출력
python3 bot/fare_bot.py ask 오키나와 11월 245000   # 판정만 확인
python3 bot/fare_bot.py poll --dry-run            # 받은 질문과 답장을 출력
```

`digest`와 `poll`을 실제로 보내려면 `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID` 환경변수가 필요하다. 외부 라이브러리는 쓰지 않는다.

## 알아둘 것

- **답장은 최대 15분 늦는다.** GitHub Actions는 주기 실행이라 상시 대기하지
  못한다. 즉시 답하게 하려면 켜져 있는 기계에서
  `while true; do python3 bot/fare_bot.py poll; sleep 5; done` 처럼 돌려야 한다.
  예약 시각도 GitHub 부하에 따라 몇 분씩 밀릴 수 있다.
- **실시간 시세는 아직 안 붙어 있다.** 지금 값은 비교 사이트에 공개된
  가격대에 성수기 폭을 얹은 참고용 기준선이다. "220,000원 밑으로 내려가면
  알려줘" 같은 목표가 알림을 하려면 실제 시세를 읽어오는 소스를 먼저 붙여야
  한다.
