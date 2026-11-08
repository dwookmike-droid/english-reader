# 인수인계 — 「그라시아의 열쇠」(La llave de Gràcia)

원고 30장은 클라우드 세션에서 끝냈다(PR #4, main에 병합). 책 디자인은 B안 「그라시아의 타일」로 정했고, 브랜치 `claude/book-design`(PR #5, draft)에서 1·2단계를 마쳤다. 기준 문서는 [`design/BRIEF-B.md`](design/BRIEF-B.md)이고, 시안은 [`design/direction-B.png`](design/direction-B.png)에 있다.

## 지금 상태 (2026-11-04)
- 원고 `src/ch01–30.txt`, `src/voices.tsv`는 main과 같다. 디자인 작업 중 한 글자도 고치지 않았다.
  - `src/front.html`(앞붙이 틀)은 지시서 4.2에 따라 고쳤다.
  - 단어표 `src/vocab.tsv`는 원고 개선 1단계에서 형태 겹침 38개를 정리했다(브랜치 `claude/content-fixes`, [`IMPROVE.md`](IMPROVE.md)).
- 원고 개선안: [`IMPROVE.md`](IMPROVE.md). 1–6단계를 마쳤다. 3·4단계에서 원고(주로 장 끝 수첩)를 고쳤고, 5단계에서 문법 쪽지(`@note`)를 만들어 13장 설명을 옮겼고, 6단계에서 27·28·30장을 다듬었다. 23·25·26·27장의 문법 설명 문단을 쪽지로 옮길지는 정하지 않았다.
- 인쇄본: 사륙판 128×188mm, **342쪽**(2026-11-08 지면 다듬기 뒤. 13–30장 다시 쓰기와 2차 다듬기 뒤에는 345쪽). 13–30장 서술을 한국어로 다시 쓰고 대사 뜻·발음을 30장까지 붙여서 늘었다([`REWRITE.md`](REWRITE.md)). 장 표제지 30개는 모두 홀수 쪽에 있다.
- 책등: 342쪽 ÷ 2 × 0.1mm = **17.1mm**.
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
python3 build.py --web-only 2>&1 | grep -E '!|Error'   # 단어표 겹침·본문에 없는 새 단어도 경고한다. 출력이 비어 있어야 정상
python3 build.py --mono          # 1도(먹) 견본: print/la-llave-de-gracia_mono.pdf
python3 build.py --pad 16        # 속지 끝에 빈 쪽을 더해 16의 배수로. 책등도 따라 바뀐다
python3 check_print.py           # 완성 기준 점검. "모두 통과"가 나와야 한다
python3 epub.py                  # 전자책: print/la-llave-de-gracia.epub (build.py 뒤에. 표지는 cover.pdf 앞면을 잘라 쓴다)
```
- 글꼴(Gowun Batang, EB Garamond, Noto Sans KR)은 빌드가 `npm pack @fontsource/...@5.1.0`으로 받아 `spanish/.fonts`에 푼다.
- `print/`에 생기는 것:

| 파일 | 내용 |
|---|---|
| `la-llave-de-gracia_sample.pdf` | 화면 확인용(재단선 없음). 차례 링크와 PDF 책갈피가 들어 있다 |
| `interior-print.pdf` | 납품용 속지(RGB). 쪽마다 재단선이 있고 TrimBox 128×188, BleedBox 134×194. 먹은 #000 |
| `cover.pdf` | 표지 펼침(뒤·책등·앞). 재단 여백 3mm, 재단선과 책등 접지선(점선) |
| `interior-print-cmyk.pdf`, `cover-cmyk.pdf` | CMYK 변환본(아래 참고) |
| `la-llave-de-gracia.epub` | 전자책(EPUB 3, `epub.py`). 표지 이미지, 차례, 장 끝 단어 목록, 문법 쪽지가 들어 있다. QR 대신 장 첫머리에 웹 리더 듣기 링크. 글꼴은 EB Garamond만 넣고 한글은 기기 글꼴. 판권면은 ○○○가 채워지면 넣는다 |
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
- **표제지**: 부마다 타일이 다르다(`TILES`. 4·5부 귀퉁이 꽃은 흰 종이색). 28장만 3시 10분 시계다. 분침은 12시에서 60°(숫자 2), 시침은 95°(3을 조금 지남)이고 둘 다 판의 중심에서 나온다. 장 날짜는 넣지 않는다. QR은 17mm.
- **단어 목록**: 글자를 줄여 가장 긴 13장(36개)도 한 쪽에 들어간다. 다른 장도 한 쪽이다.
- **본문**
  - 쪽 머리: 왼쪽 쪽은 책 제목, 오른쪽 쪽은 "장 · 제목".
  - 쪽 번호: 바깥 아래, 작은 꽃과 함께.
  - 장면 바뀜: 꽃 한 송이.
  - 편지·쪽지·신문(`@letter`): 테라코타 10% 망과 왼쪽 띠, EB Garamond 이탤릭.
  - 윤하의 수첩: 원고에서는 `@letter`지만 `mark_diary()`가 장의 마지막 `@letter`(뒤에 문법 쪽지만 오거나, 5장처럼 바로 다음 문단이 '수첩에' 적었다고 말하는 것)를 수첩으로 본다. 망 없이 왼쪽 이중선(공책 여백선), 항목마다 테라코타 35% 괘선(`--rule`, CMYK 팔레트에 있음), 위에 작은 '수첩' 표시, 바로 선 EB Garamond.
  - 상자 쪽 나눔: 상자 첫 문단은 다음 문단과, 끝 문단은 앞 문단과 붙인다(문단이 둘 이상일 때만). 수첩은 끝 두 항목을 앞과 붙여, 넘어가는 쪽에 적어도 세 항목이 간다.
  - 새 단어(장 끝 목록에 실린 말, 원고의 `{단어|발음}`): 테라코타 색, EB Garamond 500. 굵은 글자는 발음 괄호 속 강세만 뜻한다. 단어 목록의 표제어도 같은 색. 앞붙이 '읽는 법' 2번에 한 문장으로 알린다. `--mono`에서는 60% 회색.
  - 양끝 맞춤: `render.js`가 판면 폭(`body data-measure`)으로 한 번 짜 보고, 낱말 사이가 `LOOSE_EM`(0.5em, 보통 공백의 약 두 배)보다 벌어진 줄만 줄 끝에 `<br>`을 넣어 왼쪽 정렬로 둔다. 줄 나눔 자리는 그대로라 쪽 나눔은 바뀌지 않는다(지금 176줄). 발음 괄호 안 띄어쓰기는 고정 폭 공백(U+2005)으로 찍어 늘어나지 않는다.
  - 책 끝: 30장 단어 목록 쪽(마지막 쪽) 아래에 열쇠를 놓는다(`.words.last .fin`).
  - 간판: 이중 테두리.
  - 문법 쪽지(`@note`): 장 끝 수첩 뒤, 가는 테두리 상자. 안의 스페인어에는 발음을 붙이지 않는다.
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
- 빌드한 PDF 여섯 개(`print/*.pdf`)는 모두 저장소에 넣는다(Mike 결정, 2026-11-05). 다시 빌드하면 함께 커밋한다.
- 남은 선택 사항
  - 편지·수첩이 쪽을 넘으면 앞쪽 상자 아래에 망이나 여백선이 두어 줄 비어 남을 수 있다(예: 119쪽). Chrome이 쪽을 나누는 방식이다. 모양은 무너지지 않는다.
  - 표지 펼침의 앞면 타일 무늬와 뒷면 타일 무늬는 책등을 사이에 두고 이어지지 않는다(따로 깔았다).

## 기타
- 음성: `tts.py`와 `.github/workflows/spanish-tts.yml`(Gemini 무료 TTS, 저장소 secret `GEMINI_API_KEY` 필요). 예전 키는 노출되었으니 새로 발급해서 쓴다.
