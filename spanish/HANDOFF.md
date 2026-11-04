# 인수인계 — 「그라시아의 열쇠」(La llave de Gràcia)

원고 30장은 클라우드 세션에서 끝냈다(PR #4, main에 병합). 책 디자인은 B안 「그라시아의 타일」로 정했고, 브랜치 `claude/book-design`(PR #5, draft)에서 1·2단계를 마쳤다. 기준 문서는 [`design/BRIEF-B.md`](design/BRIEF-B.md)이고, 시안은 [`design/direction-B.png`](design/direction-B.png)에 있다.

## 지금 상태 (2026-11-04)
- 원고 `src/ch01–30.txt`, 단어표 `src/vocab.tsv`(약 2,800개), `src/voices.tsv`는 main과 같다. 디자인 작업 중 한 글자도 고치지 않았다.
  - `src/front.html`(앞붙이 틀)은 지시서 4.2에 따라 고쳤다. 그래서 `git diff main -- spanish/src`에는 이 파일 하나만 나온다.
- 인쇄본: 사륙판 128×188mm, **318쪽**(기준 305, +4.3%). 장 표제지 30개는 모두 홀수 쪽에 있다.
- 책등: 318쪽 ÷ 2 × 0.1mm = **15.9mm**. `--pad 16`으로 빌드하면 320쪽, 16.0mm가 된다.
- 설정 문서:
  - `CHARACTERS.md`: 인물·세계관
  - `PLAN.md`: 30장 지도
  - `STORY.md`: 언어 비율, 날짜표, 장별 요약
  - `REVIEW.md`: 검수 기준

## 빌드
```bash
cd spanish
pip install segno pypdf          # 없으면 설치. Homebrew 파이썬이면 --user --break-system-packages
npm i playwright                 # 처음 한 번. Chromium이 이미 있으면 install 은 하지 않는다
python3 build.py                 # 아래 결과물 전부 (약 40초)
python3 build.py --web-only 2>&1 | grep -E '!|Error'   # 출력이 비어 있어야 정상
python3 build.py --mono          # 1도(먹) 견본: print/la-llave-de-gracia_mono.pdf
python3 build.py --pad 16        # 속지 끝에 빈 쪽을 더해 16의 배수로. 책등도 따라 바뀐다
python3 check_print.py           # 완성 기준 점검. "모두 통과"가 나와야 한다
```
- 글꼴(Gowun Batang, EB Garamond, Noto Sans KR)은 빌드가 `npm pack @fontsource/...@5.1.0`으로 받아 `spanish/.fonts`에 푼다.
- `print/`에 생기는 것:

| 파일 | 내용 |
|---|---|
| `la-llave-de-gracia_sample.pdf` | 화면 확인용(재단선 없음). 차례 링크와 PDF 책갈피가 들어 있다 |
| `interior-print.pdf` | 납품용 속지(RGB). 쪽마다 재단선이 있고 TrimBox 128×188, BleedBox 134×194. 먹은 #000 |
| `cover.pdf` | 표지 펼침(뒤·책등·앞). 재단 여백 3mm, 재단선과 책등 접지선(점선) |
| `interior-print-cmyk.pdf`, `cover-cmyk.pdf` | CMYK 변환본(아래 참고) |
| `book.html`, `cover.html` | 중간 파일. 커밋하지 않는다(`.gitignore`) |

## 만드는 순서 (`build.py` `main()`)
1. 원고 → `print_html()`.
2. 찍어 보고, 짝수 쪽에 떨어진 표제지 앞에 빈 쪽을 넣고 다시 찍는다.
   - 표제지는 PDF 텍스트의 `CAPÍTULO N`으로 찾는다. 표제지 디자인을 바꿔도 이 글자는 남겨야 한다.
3. 다 맞으면 표제지 쪽수를 차례(`toc_html`)에 넣고 다시 찍는다. 쪽이 밀리면 2부터 다시 한다.
4. 먹을 #000으로 바꿔 한 번 더 찍는다. 그 결과를 재단선 판에 얹어 `interior-print.pdf`를 만든다(`interior_for_press`).
5. 속지 쪽수로 책등을 계산해 `cover.pdf`를 만든다(`cover_html`, `PAPER_CALIPER_MM`).
6. `to_cmyk()`로 CMYK판을 만든다.

## 디자인에서 정한 것
- **판면**: `build.py`의 `MARGIN_*` 한 곳에서 정한다. 위 15, 아래 16, 안쪽 16, 바깥 12mm. 본문은 10pt, 행간 1.72.
- **색**: 속지는 먹 + 테라코타 두 가지(`--accent`)이고, 초록은 표지에만 쓴다. `--mono`로 빌드하면 강조색이 #666이 된다.
- **표제지**: 부마다 타일이 다르다(`TILES`). 28장만 3시 10분 시계판이다. 날짜는 `DATES`에 있다(STORY.md 날짜표를 옮긴 것). QR은 17mm.
- **본문**
  - 쪽 머리: 왼쪽 쪽은 책 제목, 오른쪽 쪽은 "장 · 제목".
  - 쪽 번호: 바깥 아래, 작은 꽃과 함께.
  - 장면 바뀜: 꽃 한 송이.
  - 편지: 테라코타 10% 망과 왼쪽 띠.
  - 간판: 이중 테두리.
  - 본문의 숫자는 EB Garamond로 찍힌다.
- **앞붙이**: 반표제지 → 빈 쪽 → 속표지 → 판권면 → 읽는 법 → 발음 펼침면(6–7쪽) → 사람들 → 차례(9쪽, 한 쪽) → 빈 쪽 → 1장(11쪽).
- **판권면**: 정해지지 않은 것은 모두 `○○○`이다(글쓴이, 펴낸이, 펴낸곳, 날짜, ISBN, 값). 속표지 아래의 `○○○`는 펴낸곳 자리다.
- **뒤표지**
  - 소개 문구(`BACK_BLURB`)는 1장과 STORY.md 1장 요약에 있는 사실만으로 썼다. 반전은 넣지 않았다.
  - 읽는 법 요약은 `BACK_HOWTO`에 있다.
  - 바코드 자리는 40×25mm 흰 상자다.

## CMYK와 인쇄소에 확인할 것
- Chromium은 RGB로만 낸다. Ghostscript의 ICC 변환을 써 보니 먹 글자가 4색 검정이 되었다. 그래서 `to_cmyk()`가 PDF의 `rg/RG` 연산자를 직접 `k/K`로 바꾼다.
  - 팔레트 색(`CMYK_PALETTE`)은 지시서 3.3의 참고값을 쓴다. 테라코타는 C0 M70 Y85 K15, 초록은 C75 M30 Y60 K45, 크림은 C0 M3 Y8 K0, 먹은 K100이다.
  - 회색은 K 한 판으로 보낸다.
  - 재단선은 맞춤색(CMYK 각 100%)이다.
  - 이미지나 다른 색공간이 생기면 변환이 멈추고 알려 준다.
- 판별로 직접 확인하는 법:
  `gs -o p.tif -sDEVICE=tiffsep -r100 -dFirstPage=12 -dLastPage=12 print/interior-print-cmyk.pdf`
  12쪽은 1장 본문 첫 쪽이다. 확인한 결과 글자는 Black 판에만, 테라코타 요소는 Magenta·Yellow 판에만 있었다.
- **인쇄소에 물어볼 것**
  - 테라코타·초록의 CMYK 값. 화면 미리보기에서는 테라코타가 조금 더 주황빛이다.
  - 속지 2도를 별색으로 찍을지, CMYK로 찍을지.
  - 종이 두께. `PAPER_CALIPER_MM`을 실제 값으로 바꾸면 책등이 따라 바뀐다.
  - 제본 단위(16쪽이면 `--pad 16`).
  - RGB 원본(`interior-print.pdf`)과 CMYK판 가운데 어느 것을 받을지.

## 남은 일
- 판권면의 `○○○` 채우기: 글쓴이, 펴낸곳, 날짜, ISBN, 값. 바코드는 ISBN이 정해지면 상자 자리에 넣는다.
- 인쇄소 확인 사항(위)을 반영하기.
- 빌드한 PDF 여섯 개(`print/*.pdf`)는 모두 저장소에 넣는다(Mike 결정, 2026-11-04). 다시 빌드하면 함께 커밋한다.
- 남은 선택 사항
  - 편지가 쪽을 넘으면 앞쪽 상자 아래에 망이 두어 줄 비어 남는다(15장 162쪽 등). Chrome이 쪽을 나누는 방식이다. 모양은 무너지지 않는다.
  - 표지 펼침의 앞면 타일 무늬와 뒷면 타일 무늬는 책등을 사이에 두고 이어지지 않는다(따로 깔았다).

## 기타
- 음성: `tts.py`와 `.github/workflows/spanish-tts.yml`(Gemini 무료 TTS, 저장소 secret `GEMINI_API_KEY` 필요). 예전 키는 노출되었으니 새로 발급해서 쓴다.
