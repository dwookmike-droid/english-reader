# 야간 검수 보고 — 오디오북 (11-12 새벽)

## 목표
「그라시아의 열쇠」 1–30장 오디오북을 Voicebox(로컬)로 만든다(11-11 Mike 결정, AUDIOBOOK.md 0절).
완료 기준: 30장 음성 + 배포 파일(mp3·m4a·timeline·desc)이 있고, 누락 문장·발음·음량·'다' 끊김 검사를 통과.

## 이번 밤에 할 수 있었던 범위
장 생성은 Mike 승인 뒤에만 한다(Voicebox 시험 생성도 승인 필요). 그래서 생성은 하지 않았고,
생성 전에 확인할 수 있는 것만 측정했다. 반복 루프는 돌리지 않았다. 승인 없이는 다음 회차에 바뀔 것이 없다.

## 항목별 상태
| 항목 | 상태 |
|---|---|
| 1–30장 Voicebox 음성 | 없음(voicebox/gen 비어 있음). 승인 대기 |
| 기존 Gemini 1–9장 | out/pilot/final에 그대로. 교체 예정이라 손대지 않음 |
| 원고 화자 ↔ Voicebox 프로필 | 원고 화자 31종 중 28종 프로필 있음. 없는 3종은 vecinos·todos·megafonia(0절 "따로 정한다") |
| 참조 샘플 길이 | 42개 모두 30초 이하. vale_03만 2.3초로 짧음 |
| 참조 샘플 ↔ 대본 글 | 로컬 Whisper(large-v3-turbo)로 42개 받아 적어 비교. 차이는 대부분 숫자 표기·카탈루냐어 인식 차이 |
| 참조 샘플 음량 | 평균 -17.8 ~ -25.3 dB. taquillera_01만 -31.2 dB로 6 dB 이상 작음 |

## 고친 것
- `pilot_mix.py`(BGM 세션 보고 bgm/NIGHTLY_REPORT_bgm.md 반영):
  - 간주를 일괄 11초가 아니라 곡마다 10–12초 안 조용한 지점에서 자른다(CUT 표). theme_open 14.25초, theme_close는 50초 전부.
  - 장 전체 true peak가 -1 dBTP를 넘으면 전체 음량을 그만큼 낮춘다(리미터 없이). 기존 파일럿은 -0.6 ~ -1.3 dBTP였다.
  - 시험: 1·2·6장을 스크래치패드에 조립. true peak -1.0 / -1.1 / -1.0 dBTP, mp3 -1.3 / -1.4 / -1.3 dBTP.
  - out/pilot/final(현재 1–9장)은 다시 만들지 않았다. 영상 세션이 쓰는 파일이고, 1장은 시작 테마가 0.25초 길어져 시간표가 밀리기 때문. Voicebox 음성으로 새로 조립할 때부터 적용된다.
- voicebox_book.py는 다른 세션이 고치는 중(커밋 안 됨)이라 건드리지 않았다.

## 남은 문제(들어 볼 곳)
- narr_01.wav: Whisper가 "녹이 슨 놋쇠"를 "노깃은 노쇠"로, "열세 시간"을 "열쇠 시간"으로 받아 적었다.
  발음 문제인지 인식 오류인지 귀로 확인 필요. 서술 목소리 기준 샘플이라 중요.
- taquillera_01.wav 음량이 다른 샘플보다 작다. Voicebox 결과 음량에 영향이 있으면 맞춘 뒤 프로필 샘플을 바꿔야 한다.
- 시간표: 영상 세션 sync_check에서 짧은 대사 앞 긴 쉼 때문에 자막이 1.1–2.3초 먼저 뜨는 곳이 장마다 3–11곳(옛 Gemini 1·2·3·5·7장).
  Voicebox 장 시간표를 만들 때 조각 시작을 실제 말 시작점(앞 무음 제외)으로 잡아야 한다. 새 음성 조립 뒤 sync_check로 다시 확인.
- vale_03.wav 2.3초, 대본 글 "Callate"에 강세 표시 없음(소리는 "Cállate").
- 비교 결과 전체: /private/tmp/claude-501/-Users-dongwookkang-Developer-english-reader--claude-worktrees-audiobook-0749d8/c4092e7d-7308-4ea6-8dff-353d37432264/scratchpad/refcheck/compare.txt

## 승인 대기 목록
1. Voicebox 시험 생성(한 장 일부) → 장 생성 스크립트로 1–30장.
2. vecinos·todos·megafonia 처리 방법.
3. 1–9장 교체 뒤 영상 재렌더·유튜브 1장·팟캐스트 4–7장 교체(각각 업로드·push 승인).
