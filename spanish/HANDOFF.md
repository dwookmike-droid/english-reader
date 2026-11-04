# 인수인계 — 「그라시아의 열쇠」(La llave de Gràcia)

클라우드 세션에서 원고 30장을 모두 끝냈다. 이 문서는 다음 세션(로컬, 구독)이 바로 이어서 **책 디자인**을 할 수 있도록 지금 상태를 적어 둔 것이다.

## 지금 상태
- 브랜치: `claude/spanish-novel-ch1` (PR #4, draft). 모든 작업이 푸시되어 있다.
- 원고: `src/ch01.txt` ~ `src/ch30.txt` 완결. 장마다 별도 에이전트 검수를 거쳤고 지적 사항은 반영했다.
- 단어표: `src/vocab.tsv` 약 2,800개. 빌드할 때 "단어표에 없는 말"이 0개여야 한다.
- 설정 문서:
  - `CHARACTERS.md`: 고정 인물·세계관
  - `PLAN.md`: 30장 지도
  - `STORY.md`: 언어 비율, 날짜표, 장별 요약, 남은 실마리
  - `REVIEW.md`: 검수 기준
- 인쇄본: 사륙판 128×188mm, 305쪽. 결과물은 `print/la-llave-de-gracia_sample.pdf`(이름의 sample은 옛 견본 시절 이름이고, 내용은 전권).

## 빌드
```bash
cd spanish
npm i playwright && npx playwright install chromium   # 처음 한 번 (render.js가 쓴다)
python3 build.py              # es.html + print/book.html + print/*.pdf
python3 build.py --web-only   # es.html만, 단어 점검용
python3 build.py --web-only 2>&1 | grep -E '!|Error'   # 아무것도 안 나와야 정상
```
- 글꼴(Gowun Batang, EB Garamond, Noto Sans KR)은 빌드가 `npm pack @fontsource/...@5.1.0`으로 받아 `spanish/.fonts`에 푼다. `FONTS=` 환경변수로 다른 위치를 지정할 수 있다.
- PDF는 두 번 렌더한다. 장 첫 쪽이 오른쪽(홀수) 쪽에 오도록 빈 쪽을 끼운다(`build.py`).

## 디자인 관련 파일
- `print.css`
  - `@page` 판형, 좌우 여백(안쪽 18mm, 바깥 14mm)
  - 본문 10pt, 행간 1.72
  - 장 표제지, 쪽 머리, 단어 목록 쪽(`@page words`)
- `build.py`
  - 원고 마크업을 HTML로 바꾼다. 정해진 마크업은 `{단어|발음}`, `@화자 —대사 :: 뜻`, `##`, `@letter`, `@address`다.
  - 장 끝 "N장의 새 단어" 목록도 만든다.
- `src/front.html`: 앞붙이(읽는 법, 발음 쪽, 등장인물)
- `reader.html`: 웹 리더(es.html) 틀

## 다음 할 일: 책 디자인
> **방향이 정해졌다: B안 「그라시아의 타일」.** 작업 브랜치는 `claude/book-design`(PR #5). 자세한 작업지시서는 [`design/BRIEF-B.md`](design/BRIEF-B.md), 시안은 [`design/direction-B.png`](design/direction-B.png). 아래 목록보다 지시서가 우선한다.
>
> 로컬에서 처음 빌드할 때는 `pip install segno`가 필요하다(QR 생성). `pdftoppm`·`pdffonts`(poppler)도 쓴다.

원고와 내용은 손대지 않고 **조판과 디자인만** 다룬다.
- 표지(앞·뒤·책등. 305쪽 기준 책등 두께는 종이에 따라 계산)
- 속표지, 판권면, 차례(장 번호, 제목, 쪽수)
- 장 표제지 디자인. 지금은 CAPÍTULO N, 제목, [발음]만 있다.
- 쪽 머리와 쪽 번호, 장면 바뀜(`##`) 장식, 편지(`@letter`)와 간판(`@address`) 상자 모양
- 장 끝 단어 목록 쪽 디자인
- 인쇄소 납품용 PDF: 재단 여백(bleed 3mm), 재단선, CMYK, 글꼴 포함 여부 확인
- 손바닥 크기로 들고 다니며 반복해서 읽는 책이라는 점을 고려한다.

## 기타
- 음성: `tts.py`와 `.github/workflows/spanish-tts.yml`(Gemini 무료 TTS, 저장소 secret `GEMINI_API_KEY` 필요). 예전 키는 노출되었으니 새로 발급해서 쓴다.
- 쪽 이미지 뷰어(클라우드 세션에서 게시): https://claude.ai/artifact/XxXcwE3mVaAyUQGLMAuQ3E
