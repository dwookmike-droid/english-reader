# 책 제작 폴더

이 저장소(english-reader)에서 여러 언어의 교재·소설을 만든다. 책 하나 = `books/<언어코드>-<책이름>/` 한 폴더.
웹 리더(`es.html` 등)와 공용 음성(`audio/`)은 GitHub Pages 주소가 바뀌지 않도록 저장소 맨 위에 둔다.

| 폴더 | 책 | 언어 | 상태 | 주요 문서 |
|---|---|---|---|---|
| `es-la-llave-de-gracia/` | 그라시아의 열쇠 (La llave de Gracia) | 스페인어 | 책 PDF·EPUB 완료, 오디오북 1–30장 완성(11-15), 매주 월요일 발행 중 | HANDOFF.md, AUDIOBOOK.md, audiobook/VIDEO.md, audiobook/PLAYBOOK_다음책.md |

## 규칙

- 새 책: `books/<언어코드>-<영문 짧은 이름>/` (예: `fr-...`, `ja-...`, `en-...`). 언어코드는 ISO 639-1.
- 책 폴더 안 구성은 그라시아를 기준으로 한다: `src/`(원고), `build.py`, `print/`(PDF·EPUB), `design/`, `audiobook/`.
- 웹 리더 HTML은 저장소 맨 위 `<언어코드>.html`, 음성은 `audio/<언어코드>/`.
- 여러 책이 함께 쓸 도구는 `books/_kit/`에 모은다(아직 없음. 두 번째 책을 시작할 때 그라시아에서 떼어 낸다).
- 음원·영상·이미지·캐시는 커밋하지 않는다(각 책의 `.gitignore`).
- 새 책의 오디오북은 시작 전에 `es-la-llave-de-gracia/audiobook/PLAYBOOK_다음책.md`를 먼저 읽는다(기준 녹음 → 대본 손질 → 시험 생성 → 검수 순서, 그라시아에서 배운 것).

## 옛 경로

2026-11-11 폴더 정리 전에는 그라시아가 저장소 맨 위 `spanish/`에 있었다. 옛 경로를 쓰는 스크립트·세션·문서를 위해
`spanish` → `books/es-la-llave-de-gracia` 바로가기(심볼릭 링크)를 남겨 두었다. 새 작업은 새 경로를 쓴다.
