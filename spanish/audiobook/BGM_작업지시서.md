# 작업지시서: 오디오북 「그라시아의 열쇠」 장 사이 간주 음원 만들기·받기

작성 2026-11-10. 받는 사람: 이 일을 맡는 봇 또는 사람. 처음부터 끝까지 이 문서만 보고 할 수 있게 썼다.

## 0. 배경 (먼저 읽기)
- 스페인어 학습 소설 30장을 오디오북으로 만든다. 장마다 음성 파일 하나(약 7–14분, 전체 약 4.8시간).
- 장이 끝나면 짧은 간주(10–12초)를 넣는다. 간주는 장의 마지막 장면 분위기를 따른다.
- 곡을 어디에 넣을지는 이미 정했다: `spanish/audiobook/bgm.tsv` (29개 자리 + 책 시작·끝).
- 필요한 곡은 **13개**(분위기 6종 × 변주 2개, 마지막 1개, 시작·끝 테마). 같은 곡을 여러 번 다시 쓴다.
- 일관성이 가장 중요하다. 13곡이 한 사람이 한 악기로 쓴 곡처럼 들려야 한다.
- 무대는 바르셀로나(8월–11월, 마지막 장은 1년 뒤 8월), 주인공은 30대 후반 한국인 여성 윤하. 조용하고 따뜻한 성장 이야기다. 극적인 영화음악이 아니다.

## 1. 하지 말 것
- 음성(TTS) 생성, 원고(`spanish/src/`)·`vocab.tsv`·`audiobook.py` 수정, git 커밋·푸시.
- API 키, 비밀번호를 파일에 쓰거나 채팅에 남기기.
- 시스템 설정 바꾸기(`brew` 설치·재설치, MCP 등록 포함)는 **Mike 승인을 받은 뒤에만**.
- K-Sound Library 음원 받기(상업 이용 금지라 이 책에 못 쓴다, §5).
- 보컬·가사가 있는 곡, 유명 곡을 흉내 낸 곡, 저작권이 불분명한 곳(유튜브 등)에서 받은 곡.

## 2. 곡 사양 (13개 공통)
| 항목 | 값 |
|---|---|
| 악기 | **나일론 줄 클래식 기타 한 대**가 중심. 분위기에 따라 첼로 한 대, 부드러운 피아노, 옅은 현악 패드만 더한다. 드럼·신스·전자음 금지 |
| 느낌 | 가깝게 녹음한 듯 따뜻하고 작은 방 울림. 조용하다 |
| 길이 | 간주(A–F): 16초로 생성(쓸 때 10–12초로 자른다). 시작 테마 30초, 끝 테마 50초 |
| 끝 | 자연스럽게 잦아들며 끝날 것. 갑자기 끊기면 안 됨 |
| 형식 | WAV, 44.1 또는 48 kHz, 16/24비트, 스테레오. MP3 금지 |
| 음량 | 피크 −1 dBFS 이하. 정규화는 하지 않아도 된다(조립 때 맞춘다) |
| 이름 | 아래 표의 `cue` 그대로: 예) `B_mystery_a.wav` |

## 3. 곡 목록과 프롬프트
모든 프롬프트 앞에 공통 문장을 붙인다:

> `Solo nylon-string Spanish classical guitar, intimate and close-miked, warm small room, gentle fingerpicking, no drums, no vocals, quiet audiobook interlude, Barcelona in autumn.`

| cue | 쓰는 곳 | BPM | 덧붙일 문장 |
|---|---|---|---|
| theme_open | 1장 앞 | 84 | `Main theme, a simple memorable melody in D major, hopeful and a little uncertain, like arriving in a new city; soft string pad enters halfway, ends gently.` |
| theme_close | 30장 끝 | 84 | `The same kind of simple memorable melody in D major, now calm and settled, a full circle; guitar with a soft cello line and light strings, slow fade at the end.` |
| A_light_a | 10·28장 뒤 | 96 | `Light and warm, a little playful, major key, gentle rumba-like strumming kept soft.` |
| A_light_b | 27장 뒤 | 92 | `Light, hopeful morning feeling, major key, bright arpeggios, relaxed.` |
| B_mystery_a | 1·3·8·18장 뒤 | 70 | `Quiet and curious, something left unsaid, minor key, sparse notes with harmonics, a low soft pad underneath.` |
| B_mystery_b | 2·4·16·24장 뒤 | 72 | `Quiet suspense, a small discovery, minor key, slow arpeggio that rises and stops on an open question.` |
| C_tender_a | 5·12·21장 뒤 | 60 | `Tender and sad, a memory of family, minor key, slow guitar melody with a soft cello.` |
| C_tender_b | 7·14·23장 뒤 | 58 | `Bittersweet and restrained, held-back emotion, minor key, slow guitar with a few soft piano notes.` |
| D_warm_a | 9·13·19·25장 뒤 | 72 | `Quiet warmth and comfort, major key, gentle guitar with soft piano, like sitting together in silence.` |
| D_warm_b | 11·15·22·26장 뒤 | 76 | `Warm and a little shy, quiet happiness that is not yet sure, major key with one minor chord, gentle.` |
| E_uneasy_a | 6·20장 뒤 | 56 | `Uneasy and heavy, quiet tension, minor key, low guitar notes over a dark soft cello drone, unresolved ending.` |
| E_uneasy_b | 17장 뒤 | 58 | `Quiet and unsettled, doubt, minor key, sparse guitar with long silences and a low string pad.` |
| F_bittersweet | 29장 뒤 | 66 | `Bittersweet farewell at peace, leaving a city you love, guitar melody with light strings, starts minor and ends major.` |

## 4. 방법 A (주된 방법) — audio-studio-mcp로 이 Mac에서 만들기
https://github.com/kanaworksai-hue/audio-studio-mcp — Stable Audio 3를 로컬에서 돌린다. 생성 비용 없음.
- 이 Mac: Apple M5 Pro, 메모리 48 GB, 남은 디스크 약 98 GB → 요건(Apple Silicon, 16 GB 권장, 모델 약 6 GB) 충족.
- 이 오디오북은 **스포티파이와 유튜브에 올린다(상업 배포)**. 그래서 상업 이용이 되는 음원만 쓴다.
- 사용 조건: 코드는 MIT. 생성물은 Stability AI Community License(연 매출 100만 달러 미만이면 상업 이용 가능, 2026-11 README 기준). **설치 전에 라이선스 페이지를 열어 이 조건이 지금도 같은지 확인하고 보고**할 것: https://huggingface.co/stabilityai/stable-audio-3-optimized

### 순서
1. **ffmpeg 고치기 (Mike 승인 후).** 지금 `ffmpeg`는 `libx265.216.dylib`가 없어 실행되지 않는다. 설치 스크립트가 ffmpeg를 요구한다.
   ```bash
   brew reinstall x265 ffmpeg
   ffmpeg -version | head -1
   ```
2. **설치.** 저장소 밖 폴더에 둔다.
   ```bash
   cd ~/Developer && git clone https://github.com/kanaworksai-hue/audio-studio-mcp.git
   cd audio-studio-mcp && ./install.sh
   ```
   모델(약 5.9 GB)을 Hugging Face에서 받는다. macOS는 로그인이 필요 없다.
3. **쓰는 방법 둘 중 하나.**
   - Web UI(시스템 설정을 안 바꿔서 권장): `.venv/bin/audio-studio-mcp --web` 실행 후 브라우저에서 생성.
   - MCP 등록(Mike 승인 후): `claude mcp add --scope user audio-studio -- ~/Developer/audio-studio-mcp/.venv/bin/audio-studio-mcp`
4. **생성.** 곡마다 `generate_audio`:
   - `audio_type: music`, `variations: 4`, 길이는 §2, `bpm`은 §3 표, 프롬프트는 공통 문장 + 덧붙일 문장.
   - 13곡 × 4후보 = 52개. 각 파일 옆 `.json`(프롬프트·시드) 보관.
5. **후보 정리.** 고르지 말고 4개 모두 넘긴다(고르는 건 Mike가 듣고 한다).
   - `spanish/audiobook/bgm/candidates/<cue>/<cue>_1.wav … _4.wav` (+ 같은 이름 `.json`)
   - 처음 2곡(theme_open, B_mystery_a)만 먼저 만들어 보고하고, Mike가 방향을 확인하면 나머지 11곡을 만든다. 공통 문장이 틀리면 13곡 전부를 다시 만들어야 하기 때문이다.
6. **이상한 후보 표시.** 보컬 같은 소리, 드럼, 클리핑, 갑자기 끊기는 끝이 있으면 `candidates/<cue>/notes.txt`에 적는다(들을 수 없으면 파형 피크·끝 1초 음량만이라도).

## 5. K-Sound Library — 이번에는 쓰지 않음
https://www.k-soundlibrary.kr (전주정보문화산업진흥원 효과음 아카이브, 약 33,590개)를 살펴본 결과:
- 음악보다 효과음·환경음 자료다. MUSICAL 분류의 짧은 루프는 신스·게임풍이라 이 책과 맞지 않는다.
- FAQ에 "다운로드 후 제3자 배포 및 상업적 활용을 금합니다"라고 되어 있다. 스포티파이·유튜브 배포는 상업 배포라 **받지 않는다.**
- 나중에 환경음이 필요하면 상업 이용이 명시된 곳(또는 방법 A의 `audio_type: sfx`)으로 만든다.

## 6. 넘겨줄 것
- `spanish/audiobook/bgm/candidates/` (13곡 × 4후보 + json, 방법 A)
- 짧은 보고(한국어): 만든 곡 수, 걸린 시간, 라이선스 확인 결과, 이상한 후보 목록, 하지 못한 것과 이유.
- 음원 파일은 커밋하지 않는다(용량). `bgm/`은 Mike가 정할 때까지 그대로 둔다.

## 7. 이후 (이 지시서 범위 밖)
- Mike가 곡마다 후보 하나를 고르면 `bgm/<cue>.wav`로 둔다.
- 조립 코드(`audiobook.py`)가 `bgm.tsv`를 읽어 장 끝에 붙인다: 마지막 대사 뒤 0.8초 → 곡 10–12초(들어갈 때 1초, 나갈 때 3초 페이드) → 1초 쉼. 곡은 말소리보다 약 9 dB 작게, 말소리와 겹치지 않게. 이 부분은 Claude가 한다.
