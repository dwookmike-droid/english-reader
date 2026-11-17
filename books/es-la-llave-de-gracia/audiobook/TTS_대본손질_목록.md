# 4–30장 소리용 대본 손질 목록 (2026-11-13)

원칙: 책 본문·자막은 그대로 둔다. 바꾸는 것은 소리로 읽을 때만 쓰는 표기(`voicebox/readings.tsv`, 숫자 읽기 규칙)와 말투 지시(`chNN.tsv`)뿐이다.
조사 범위: 4–30장 1,303조각(스페인어 대사 646개).

## A. 실제로 잘못 읽는 곳 (고침)
| 장-조각 | 원문 | 지금 읽기 | 고칠 읽기 |
|---|---|---|---|
| 4-56 | 월요일. 10:00. | 십:영 | 열 시 |
| 5-2 | Lunes. 10:00. Trae la llave. (서술 속 스페인어 쪽지) | 숫자 그대로 → 엔진 임의 | Lunes. Diez. (또는 "las diez") |
| 5-11 | 나는 시계를 보았다. 9시 58분. | 구시 오십팔분 | 아홉 시 오십팔 분 |

규칙으로 고친다: 한국어 "N시"는 고유어(한·두·세…열두 시), "HH:MM"은 "N시"(00분이면 생략).
확인 결과 문제 없음: 연도(천구백칠십팔 년), 월·일(삼월, 사일), 층(이층), 번지(칠번지), 6번 선로(육 번).

## B. 스페인어 속 숫자 93곳 (시험 후 결정)
편지 날짜·연도가 대부분: "Barcelona, 2 de diciembre de 1978", "12 de", "Dong-Hae 7", "las dos" 등.
지금은 숫자 그대로 엔진에 들어간다. CosyVoice·IndexTTS가 1978을 mil novecientos setenta y ocho로 제대로 읽는지 몇 개 만들어 보고,
틀리면 소리용으로 글로 풀어 쓴다(자막은 숫자 그대로).

## C. 카탈루냐어 고유명사 (소리용 표기 추가)
스페인어식으로 읽으면 틀리는 낱말. 1–3장 rellotge·Rellotger와 같은 방식.

| 낱말 | 나오는 조각 수 | 제안 소리 표기 |
|---|---|---|
| Montjuïc | 6 | Munchuík |
| Paral·lel | 5 | Paralél |
| Gòtic | 3 | Gótic |
| Plaça | 2 | Plása |
| Serralleria / SERRALLERIA | 2 | Serrallería |
| Rellotger | 2 | Rrellotchér (이미 있음) |
| Pròxima | 1 | Próxima |
| Catalunya | 1 | Cataluña |
| Poble (Sec) | 1 | Póble |
| Tancat per vacances | 1 | Tancát per vacánses |
| Gràcia | 15 | 그대로(스페인어식도 통용). 귀로 확인 |

제안 표기는 출발점이다. 만든 뒤 받아쓰기·청취로 확인.

## D. 말투 지시가 빠진 스페인어 대사 51개
- 편지 낭독 24개(13·14·15·18·24장의 마르티·몬세 편지): 장면 설명(@scene)이 붙어 있어 차분히 읽힌다. 편지마다 감정 한 줄을 넣는다(그리움, 이별 등).
- 짧은 대사 27개: Hola(6) · Sí(4) · Vale(5) · Gracias(6) · Eso · El martes · Por Martí · ¿Cómo es el bolso? 등. 앞뒤 서술에 맞춰 지시를 채운다.
  예: 28-14 todos "Por Martí." → 건배, 조용하고 따뜻하게.

| 장-조각 | 누구 | 대사 |
|---|---|---|
| 6-19 | marc | Hola. |
| 8-32 / 8-34 | 경찰 | ¿Cómo es el bolso? / ¿Y qué hay en el bolso? |
| 8-46 | yunha | Gracias… |
| 9-47 | marti | El domingo, a las once, en Santa María del Mar. |
| 11-7 / 11-25 | marti / yunha | Desde Montjuïc veo el puerto… |
| 12-9 / 12-20 | marc | Sí. De Las Palmas. / Eso. |
| 13-11…23 | marti | 편지 7조각 |
| 14-6…17 | marti | 편지 6조각 |
| 15-5…13 | marti | 편지 5조각 |
| 18-9…15 | marti | 편지 4조각 |
| 20-28 | yunha | Gracias. |
| 21-35, 22-20, 29-16 | yunha | Sí. |
| 23-20 / 23-21 | marc / yunha | Hola. / Hola. |
| 24-20…26 | montse | 편지 4조각 |
| 25-22 / 25-23 / 25-68 | marc / yunha / yunha | Hola, Yuna. / Hola. / El martes. |
| 26-9, 26-34, 29-39, 29-41 | yunha | Vale. |
| 28-14 | todos | Por Martí. |
| 30-17 / 30-32 | madre / chica | Gracias. |

## E. 그대로 두고 생성 후 검수로 거르는 것
- 스페인어 낱말 + 한국어 조사 191곳("Vale가", "Fontana였다"): 언어가 바뀌는 자리라 조각이 갈린다. 본문을 바꾸면 책과 달라지므로 두고, 받아쓰기·앞 무음 검수로 끊김을 찾는다.
- "…"가 든 대사 76개: 머뭇거림이 길게 나오는지 검수.
- 아주 짧은 대사 53개: 앞에 버림 문장을 붙여 만드는 방식이 이미 있다.

## 적용 결과 (11-13)
- A·B·C·D 모두 반영. 4–30장만 적용하고 1–3장 소리는 그대로.
- 시험 생성: 10개 장 70토막 → 받아쓰기 미달 0(고친 뒤).
  - 열 시 / 아홉 시 오십팔 분 / 열 시 십오 분이라고 / 알오 노선: 정상.
  - 스페인어 연도·날짜(mil novecientos setenta y ocho 등): 정상.
  - Munchuík·Paralél·Póble Sec·Plása·Gótic·Tancát·Serrallería: 받아쓰기상 의도대로. 귀로 확인 필요.
- 시험 중 찾아 고친 것:
  1. 4장 스페인어 쪽지 "10:00"이 "diez:cero"로 나옴 → 스페인어 시각도 글로("diez", "diez y quince").
  2. 24장 몬세 편지(200자)가 IndexTTS에서 거의 무음 → 110자 넘는 스페인어는 문장 끝에서 나눠 만들고 0.3초 쉼으로 잇는다.
- 감정: 지시 낱말이 맞지 않아 256줄이 감정 없이 나오던 것 → 4장부터 낱말 목록을 넓혀 63줄만 남음(동작 지시 위주, 무감정으로 둠).
- 듣기: `out_vb/들어볼_대본손질_시험/`.
