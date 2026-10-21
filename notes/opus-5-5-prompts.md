# Opus 5.5 영상·인터랙티브 프롬프트 중 이 리더에 쓸 만한 것

출처는 [github.com/yihui-dev/awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos)(MIT 라이선스)이고, 2026-10-12 기준 703개가 실려 있습니다. 그중 이 영어 원서 리더(『시크릿 가든』, 『오페라의 유령』, 『젊은 베르테르의 슬픔』, 『프랑켄슈타인』)에 쓰거나 영어 학습 콘텐츠로 바꾸기 좋은 25개를 골랐습니다.

**고른 기준**
- 글자·문장이 주인공인 것(키네틱 타이포그래피, 타이핑, 단어 카드)
- 단계별 설명 영상: 문법·어휘·작품 배경 설명으로 바꿔 쓰기 좋은 구조
- 종이·잉크·크레용 질감, 정원·오페라 극장·밤 장면처럼 차분한 분위기
- 단일 HTML, 외부 에셋 없음, Canvas 2D 위주로 폰에서도 가벼운 것
- 주제만 바꿔 끼우는 프롬프트 틀, 특히 "모든 프레임은 시간의 순수 함수(`draw(t)`/`seek(t)`)" 규칙

**뺀 것:** 제품·SaaS 홍보 영상, 크립토, 3D 게임, Three.js/WebGPU 대형 장면(블랙홀, 엔진 분해, 도시 등)처럼 폰 GPU에 무거운 것.

> 프롬프트 원문은 저장소에서 가져온 자료로만 실었습니다. 길이가 600자 이상이면 핵심 규칙을 한국어로 요약하고 앞부분 약 300자만 인용했습니다. 원래 MP4 렌더용 프롬프트가 많지만, 이 리더에는 HTML/Canvas 결과물을 그대로 페이지에 넣는다는 전제로 적었습니다.

---

## 1. 글자·타이포그래피 애니메이션

### ESCAPE THE ORBIT: 연설 한 구절의 키네틱 타이포그래피
- 작성자: [@Gdgtify](https://x.com/Gdgtify/status/2105669567036989608)
- 기술 태그: (태그 없음) · 분류: 3d · 프롬프트 길이: 4694자
- 요약: 케네디의 라이스대 연설(1962) 한 구절을 '문장의 기준선이 곧 궤도'라는 은유 하나로 푼 20초 영상. 읽는 동안에는 글자를 멈춰 두고(reading hold), 다 읽힌 뒤에야 장식적인 움직임을 허용하는 등 가독성 규칙이 아주 꼼꼼합니다.
- **이 리더에 쓰는 법:** 챕터 첫 화면의 '명문장 카드'로 씁니다. 예: 『프랑켄슈타인』의 "Beware; for I am fearless, and therefore powerful." 원문 고정, 생략은 `[…]`, 출처는 따로 적기, 지금 읽는 구절은 최소 64px 같은 규칙을 그대로 가져오면 네 작품 모두에 쓸 수 있습니다.

**핵심 규칙 (한국어 요약):** 표시 문구와 순서를 고정하고, 생략한 부분은 `[…]`로 밝히고, 출처는 본문과 따로 둡니다. 소리 없이도 이해돼야 합니다. 카메라 동작은 세 가지(풀백·롤·속도 맞추기)만 쓰고 동작마다 수사적 목적이 있어야 합니다. 읽기 홀드가 끝나기 전에는 장식적인 이동을 시작하지 않고, 모션 블러는 읽는 중인 글자에 걸지 않습니다. 곡선은 호 길이(arc-length)로 샘플링합니다. `window.seek(t)`와 `frame(n)`으로 어느 시점이든 같은 그림이 나오게 하고, 무작위나 누적 물리는 쓰지 않습니다. 마지막에 지정한 8개 프레임을 검사합니다.

**원문 앞부분:**

> Create a 20.00-second kinetic typography film titled “ESCAPE THE ORBIT,” based on John F. Kennedy’s Rice University address, September 12, 1962.
>
> The central experience: a sentence discovers that it can change its own trajectory.
>
> Deliver one complete, self-contained HTML file. Composition: …

### BUILD THE FLOOR: 단어가 건축 부재가 되는 스포큰 워드
- 작성자: [@Gdgtify](https://x.com/Gdgtify/status/2103458245213929495) · [Skillry 재현본](https://skillry.dev/ai-videos/opus-5-5/gdgtify-929495)
- 기술 태그: canvas · 분류: motion · 프롬프트 길이: 4373자
- 요약: 다섯 줄짜리 짧은 연설에서 단어마다 건축 역할을 줍니다(WAIT=인방, WAITING=매달린 하중, VOICE=기둥, ROOM=개구부, FLOOR=바닥판). 글자 모양 자체가 구조물이 되고, 마지막 문장은 앞 단어들이 만든 바닥 위에 섭니다.
- **이 리더에 쓰는 법:** TTS로 문장을 읽어 줄 때의 하이라이트 타이밍 설계에 참고합니다. 박자가 아니라 '구절·쉼·강세' 큐 시트로 문장을 드러내는 방식이 낭독 하이라이트와 같은 문제입니다. 배경 #102820과 종이색 #F4E9D5 조합은 다크 '서재' 테마 후보입니다.
- 같은 작성자의 변형판(자기장 버전): [@Gdgtify 535](https://x.com/Gdgtify/status/2105570411870130294)

**핵심 규칙 (한국어 요약):** 연설 문구와 순서를 정확히 지키고, 실존 인물의 말로 돌리지 않습니다. 고대비 세리프는 문장에, 굵은 그로테스크는 '하중을 받는' 단어에, 모노스페이스는 타이밍 표시에 씁니다. 박자에 억지로 맞추지 말고 구절·쉼·강세 기반 큐 시트를 쓰며, 400ms 이상 완전히 멈추는 순간을 한 번은 둡니다. 실제 글리프 경로를 변형하되 카운터(o 안쪽 공간)와 가독성을 지킵니다. 구조로 바뀌기 전에 지금 읽는 구절이 먼저 읽혀야 합니다. 20초 주기로 render(0)=render(20)이 되게 하고, `window.seek(t)`로 결정적으로 렌더합니다.

**원문 앞부분:**

> Create a 20.00-second kinetic spoken-word film titled “BUILD THE FLOOR.”  Treat this as an original miniature speech staged entirely through typography. Every line changes the architecture of the frame. The final declaration must stand on something the earlier words physically constructed.  Deliver …

### make it catchy: 종이 위 타이핑 → 글자가 흩어져 기계가 됨
- 작성자: [@adrianduta96](https://x.com/adrianduta96/status/2109187815195992248)
- 기술 태그: (태그 없음) · 분류: motion · 프롬프트 길이: 825자
- 요약: 따뜻한 종이 배경에 문구가 저절로 타이핑되고, 글자가 흩어져 경사로·톱니·건반 블록으로 된 음악 기계를 조립합니다. 12초 뒤 공이 떨어지면서 부딪히는 블록마다 음이 납니다. '보이는 움직임마다 소리 하나'가 핵심 규칙입니다.
- **이 리더에 쓰는 법:** 북마크나 '단어장에 추가' 같은 순간의 마이크로 애니메이션(1초 이내)으로 줄여 씁니다. 글자가 흩어졌다가 책갈피 모양으로 다시 모이는 식입니다. 잉크 블랙·코발트·해바라기 노랑 3색은 기본 종이 테마와 잘 어울립니다.

**핵심 규칙 (한국어 요약):** 처음 12초는 무음입니다. 문구가 타이핑된 뒤 글자가 분해되어 기계 부품이 되고, 공이 떨어지는 순간부터 블록마다 음, 북, 톱니 틱이 4초짜리 비트를 만듭니다. 마지막 타격에 모든 것이 "ONE PROMPT" 글자로 스냅되고 다시 정적. 굵은 기하 도형, 3색 팔레트를 쓰고, 모든 소리는 눈에 보이는 움직임과 짝을 이룹니다.

**원문 앞부분:**

> Make a 20-second 16:9 motion graphics video that tells a little story with sound. For the first 12 seconds there is no sound at all: on a warm paper background, the words "make it catchy." type themselves out, then the letters fall apart and build a colorful music machine piece by piece: ramps, …

### 1분 키네틱 텍스트 설명 영상 틀
- 작성자: [@IncognitoPrince](https://x.com/IncognitoPrince/status/2107664651760849212)
- 기술 태그: (태그 없음) · 분류: explainer · 프롬프트 길이: 313자
- 요약: 주제만 바꿔 끼우는 아주 짧은 템플릿입니다. After Effects 느낌의 키네틱 텍스트, 굵은 타이포, 시간차 등장을 HTML/CSS/JS 단독 파일로 만듭니다.
- **이 리더에 쓰는 법:** `[Topic]`에 "Phrasal verbs in The Secret Garden, chapter 1"처럼 넣어 단원별 1분 복습 화면을 뽑는 출발점으로 씁니다. 결과물이 단일 HTML이라 리더에 그대로 붙일 수 있습니다.

**프롬프트 원문 (전체):**

> Create a 1-minute explainer video about [Topic] featuring After Effects style kinetic text animations. Use HTML/CSS/JS to render the animation with smooth transitions, bold typography, and timed reveals. The final output should be a standalone web-based animation file that can be recorded or exported as a video.

### 점 하나 → 검색창 → 문장이 채워지는 5초 전환
- 작성자: [@cgclick](https://x.com/cgclick/status/2107907343912497325)
- 기술 태그: (태그 없음) · 분류: motion · 프롬프트 길이: 271자
- 요약: 점이 튀어 화면 가운데로 들어와 검색창으로 펼쳐지고, 그 안에 문장이 타이핑되는 5초 모션입니다. 이징 인·아웃을 쓴 부드러운 전환이 핵심입니다.
- **이 리더에 쓰는 법:** '단어 탭 → 뜻 팝업' 전환에 그대로 씁니다. 탭한 단어 위치의 점이 사전 카드로 펼쳐지고 뜻이 타이핑되듯 나타납니다. CSS transform만으로도 구현할 수 있습니다.

**프롬프트 원문 (전체):**

> Create a 5 sec motion graphics animation of a simple dot, bouncing into the center of the screen, it expands to a search bar and then text fills the box: "I'm a motion designer, what should my next career be?"  The animation should be be fluid, ease keyframes in and out,

### UI 카드 타이밍 수치 + 프레임 단위 검증 루프
- 작성자: [@fleyta88](https://x.com/fleyta88/status/2108249741125443662)
- 기술 태그: (태그 없음) · 분류: explainer · 프롬프트 길이: 398자
- 요약: 카드 280ms, 제목 220ms, 메타데이터 160ms, 요소 간 60ms 스태거라는 구체적인 수치를 주고, Playwright로 프레임을 한 장씩 넘기며 오버슈트를 잡아 고치게 하는 프롬프트입니다.
- **이 리더에 쓰는 법:** 단어 뜻 카드(표제어 → 발음 → 뜻 → 예문)가 나타나는 타이밍 기준치로 바로 씁니다. GSAP 없이 CSS `transition-delay`로 옮겨도 됩니다. 검증 루프는 팝업 회귀 테스트 아이디어로 참고합니다.

**프롬프트 원문 (전체):**

> Build a GSAP timeline for UI cards with specific timing constraints: 280ms for cards, 220ms for title, 160ms for metadata, and a 60ms stagger between elements. Implement a verification loop where the animation is stepped through frame-by-frame using Playwright, screenshots are compared to detect overshoot or errors, and the code is patched until it passes the checks without rewriting everything.

## 2. 설명 영상: 문법·어휘 설명에 응용

### THERE IS NO LAST PRIME: 증명을 '기계 장치'로 보여 주기
- 작성자: [@Gdgtify](https://x.com/Gdgtify/status/2107054188836393073)
- 기술 태그: (태그 없음) · 분류: motion · 프롬프트 길이: 2877자
- 요약: 유클리드의 소수 무한 증명을 숫자 바퀴, 곱셈 벨트, 나머지 표시기로 된 검사 기계로 연출합니다. 장식이 아니라 기계 동작 하나하나가 증명의 연산 하나에 대응하고, 흔한 오해('곱하고 1을 더하면 항상 소수')를 하지 말라고 미리 못 박아 둡니다.
- **이 리더에 쓰는 법:** 긴 문장 구조 설명에 씁니다. 예: 『젊은 베르테르의 슬픔』의 긴 복문을 '주어 바퀴·동사 벨트·관계절 게이트'로 분해합니다. '장치는 설명을 장식하지 말고 실제로 보여 줘라', '흔한 오해는 프롬프트에서 미리 금지하라'는 두 규칙이 문법 설명에 그대로 들어맞습니다.

**핵심 규칙 (한국어 요약):** 화면 문구(LOCKED COPY)를 고정하고, 구체적인 예(2·3·5·7·11·13 → 30030 → 30031 = 59 × 509)로 일반 논리를 보여 줍니다. 계산은 표 형식 모노스페이스, 선언은 굵은 기하 그로테스크, 마지막 논리 문장은 작은 세리프로 씁니다. 장면마다 하나의 연산(끝을 막는 스토퍼, 벨트 결합, +1, 여섯 개 나눗셈 게이트, 케이스 열기)을 둡니다. 숫자는 움직일 때만 굴리고 멈출 때는 또렷하게 고정합니다. 20초 루프, 60fps 결정적 렌더링입니다.

**원문 앞부분:**

> Create a kinetic mathematical proof titled “THERE IS NO LAST PRIME.”
> Stage Euclid’s argument as a beautiful mechanical inspection system. Typography becomes engraved number wheels, multiplication belts, and remainder indicators.
> The mechanism must demonstrate the proof rather than decorate a …

### 10초 설명 영상 스타일 15종 모음 (중국어 원문)
- 작성자: [@NFT_Chen](https://x.com/NFT_Chen/status/2107653056771068069)
- 기술 태그: (태그 없음) · 분류: 3d · 프롬프트 길이: 1106자
- 요약: 피영극(그림자 인형극), 아이소메트릭 공정도, 화이트보드 손그림, 한자 '火'의 자형 변천, 3Blue1Brown식 원 넓이, 양피지 고지도 위 경로, 120BPM 단어 카드, 칸 만화, 가로 타임라인 등 짧은 프롬프트 15개를 모았습니다. 모두 【주제】만 바꿔 끼우는 형식입니다.
- **이 리더에 쓰는 법:** '한자 자형 변천' 틀은 영어 어원 카드로(예: *garden* ← 고대 북부 프랑스어 *gardin*), '고지도' 틀은 『프랑켄슈타인』의 제네바 → 잉골슈타트 → 북극 여정으로, '120BPM 단어 카드' 틀은 챕터 핵심 어휘 복습으로 바꿔 씁니다.

**핵심 규칙 (한국어 요약):** 한 줄 프롬프트마다 길이(10–12초), 화풍 하나, 연출 동작 2~3개, 마무리 한 마디를 정합니다. 예: '종이 질감 그림책풍, 크레용 선 + 연필 채색, 선이 떨림', '120 BPM, 단어 하나가 한 박, 검은 바탕 주황 글자, 마지막 한 방: 설명 못 하면 모르는 것', '양피지, 옅은 먹 산길, 주홍 경로를 한 획에 긋고 이정과 설명 한 줄, 끝에 도장'. 15개 모두 '코드 렌더링'이 전제입니다.

**원문 앞부분:**

> 做一支 10 秒彩色皮影戏，讲【曹冲称象】。剪影布局，暖光透背，关节式偶戏。依次出现秤盘、铜碗、石头，先平衡，再把石头分批称、加起来。字幕卡点出现。用代码渲染，导出可播放视频。
>
> 做一支 12 秒等距 2.5D 流程动画，讲【快递怎么分拣】。包裹沿分拣线、货台、平板运输、清关关卡移动，每步编号标签，最后双线汇成一条。干净、可跟读。
>
> 做一支 10 秒比例尺对比，把【地球、木星、太阳】按真实半径同屏摆放。镜头平滑拉远，第一个物体缩小，点题「太阳底下约有 130 万个地球」。数字标注清晰。
>
> 做一支 10 秒白板手绘。白底黑马克笔一笔笔画出【火柴人连甩 5 …

### 색연필 그림책 스타일로 글 한 편 설명하기
- 작성자: [@woojinrad](https://x.com/woojinrad/status/2106083299462455731)
- 기술 태그: (태그 없음) · 분류: explainer · 프롬프트 길이: 383자
- 요약: 첨부한 글을 읽고, 핵심 3가지와 본문에서 그대로 가져온 짧은 캡션, 단순한 캐릭터 하나로 25초 설명 영상을 만듭니다. Canvas로 그리고 Web Audio로 음악을 합성하며, 스토리보드를 먼저 보여 주게 합니다.
- **이 리더에 쓰는 법:** '글'을 『시크릿 가든』 한 챕터로 바꾸면 그대로 챕터 요약 카드가 됩니다. 캡션을 원문에서 그대로 따오라는 조건 덕분에 학습자가 원문 문장을 다시 보게 됩니다. 캐릭터는 울새(robin)로 하면 됩니다.

**프롬프트 원문 (전체):**

> Read the attached article and make a 25-second animated explainer (1080×1350, 24 fps) in a colored-pencil storybook style, drawn entirely in JavaScript on an HTML canvas, with a soundtrack synthesized using the Web Audio API. Pick 3 main ideas, give each a short caption taken from the text, and use one simple original character. Show me the storyboard first, then render it to MP4.

### 과학 설명 영상 틀: 훅 + 반직관 + 생활 비유 + 출처
- 작성자: [@Cryptoxorz](https://x.com/Cryptoxorz/status/2106632900049359201)
- 기술 태그: (태그 없음) · 분류: explainer · 프롬프트 길이: 460자
- 요약: 주제, 보충 자료, 대상 수준을 빈칸으로 둔 설명 영상 템플릿입니다. 핵심 질문 하나에 집중하고, 호기심 훅, 직관에 반하는 점, 생활 비유를 쓰되 사실은 1차 자료로 확인하라고 요구합니다.
- **이 리더에 쓰는 법:** 작품 배경 설명 화면에 씁니다. 예: 『프랑켄슈타인』 시대의 갈바니 전기 실험, 『오페라의 유령』에 나오는 파리 오페라 극장 지하 호수. '출처 우선' 규칙이 있어 학습 자료로 믿고 쓰기 좋습니다.

**프롬프트 원문 (전체):**

> Help me make a science explainer video. Topic: {Topic} (Supplementary materials: {Paper/Link/Screenshot, Optional}; Target audience: {Zero-basis public / Some basis, Optional})
>
> - Content: Explain one core question clearly, with a curiosity hook, counter-intuitive points, and life-like analogies, but facts must be accurate and sourced.
>   - Prioritize citing original papers, authoritative institutions, and textbooks; do not use secondary marketing accounts.

### 손그림 화이트보드 설명
- 작성자: [@tak3sh8](https://x.com/tak3sh8/status/2103667481139441895) · [Skillry 재현본](https://skillry.dev/ai-videos/opus-5-5/tak3sh8-441895)
- 기술 태그: canvas, audio · 분류: explainer · 프롬프트 길이: 152자
- 요약: 어려운 개념을 손으로 그리는 화이트보드 애니메이션으로 설명하고, 2단계에서 내레이션이 붙은 MP4로 만듭니다.
- **이 리더에 쓰는 법:** 가정법 과거완료처럼 까다로운 문법 하나를 화이트보드 그림으로 설명합니다. 먼저 애니메이션만 만들고 그다음에 내레이션을 붙이는 2단계 진행이 리더의 TTS 기능과 잘 맞습니다.

**프롬프트 원문 (전체):**

> Do a quick hand-drawn whiteboard animations explaining what is replica symmetry breaking in the SK model
>
> Prompt 2: build the mp4 version with narration

## 3. 책 분위기 장면

### 크레용으로 그린 밤, 피아노 치는 고양이
- 작성자: [@0xCodez](https://x.com/0xCodez/status/2104257855142474136)
- 기술 태그: (태그 없음) · 분류: 3d · 프롬프트 길이: 700자
- 요약: Canvas 2D 단일 HTML로 만든 약 2분짜리 크레용풍 피아노 연주 장면입니다. 피아노는 Web Audio로 합성하고, 하나의 타임라인이 음악과 그림을 함께 움직여 고양이 발이 실제로 울리는 건반을 누릅니다. 일시정지/다시 재생과 `?t=90` 시점 점프를 지원합니다.
- **이 리더에 쓰는 법:** '야간 독서 모드'의 대기 화면이나 배경으로 씁니다. 『오페라의 유령』 버전으로 무대 위 피아노와 촛불로 바꾸면 됩니다. `?t=` 점프 규칙은 '읽던 위치로 돌아가기'와 같은 발상이라 구현 패턴도 참고할 만합니다.
- 비슷한 프롬프트: 비 오는 도시의 녹슨 로봇이 피아노를 찾는 크레용+수채화 단편 [@kopert0x](https://x.com/kopert0x/status/2104961082880098349). 음이 하나 울릴 때마다 창문에 불이 켜지는 동기화 아이디어가 좋습니다.

**핵심 규칙 (한국어 요약):** 장면: 밤의 아늑한 방, 업라이트 피아노, 작은 검은 고양이. 모든 면에 크레용 질감(거친 획, 흔들리는 윤곽, 종이 결)을 줍니다. 음악은 약 40마디 원곡(차분하게 시작해 고조되고 부드럽게 끝남)을 배음·해머 노이즈·리버브까지 Web Audio로 합성하고, 오디오 파일은 쓰지 않습니다. 하나의 타임라인이 둘 다 구동하며 조명·카메라·분위기도 음악을 따릅니다. Canvas 2D만, 라이브러리·외부 에셋 없음.

**원문 앞부분:**

> Create a single self-contained index.html: a ~2-minute animated piano performance in a hand-drawn crayon style.
>
> Scene: a cozy room at night, an upright piano, a small black cat playing it. Crayon texture on every surface: grainy strokes,wobbly outlines, paper tooth.
>
> Music: compose an original …

### 종이 그림자극
- 작성자: [@x4b47x](https://x.com/x4b47x/status/2103019799614034026) · [Skillry 재현본](https://skillry.dev/ai-videos/opus-5-5/x4b47x-034026)
- 기술 태그: canvas, particles, audio · 분류: motion · 프롬프트 길이: 184자
- 요약: 세로 9:16, 30~60초짜리 종이 오려내기 그림자극 애니메이션을 순수 JS로 만들고, 잔잔한 소리도 코드로 만듭니다.
- **이 리더에 쓰는 법:** 『오페라의 유령』 챕터 표지로 씁니다. 커튼 뒤 그림자극으로 크리스틴과 팬텀의 실루엣을 보여 주고, 주제 자리에 챕터 질문("Who is the Angel of Music?")을 넣습니다. 세로 비율이라 폰 화면에 꼭 맞습니다.

**프롬프트 원문 (전체):**

> Create a pure javascript animation. 30-60s, vertical 9:16, paper cut-out shadow theatre style with gentle, fitting audio (made in code) on the topic: What makes a place feel like home?

### Painting the Night: 종이결·흑연 해칭·달빛
- 작성자: [@obydulme](https://x.com/obydulme/status/2104802322518052905)
- 기술 태그: (태그 없음) · 분류: 3d · 프롬프트 길이: 236자
- 요약: 이미지 에셋 없이 종이 결, 흑연 해칭, 물감 번짐, 별자리, 달빛, 펠트 피아노 사운드까지 런타임에 생성하는 50초 단편입니다.
- **이 리더에 쓰는 법:** 『프랑켄슈타인』 북극 장면(월턴의 편지)의 배경으로 씁니다. 에셋 0개라 단일 파일 원칙과 맞습니다. 다만 WebGL이므로 저사양 폰에서는 Canvas 2D 해칭으로 대체할 수 있게 해 둡니다.

**프롬프트 원문 (전체):**

> Create a 50-second generative short titled 'Painting the Night'. Zero image assets. Generate paper grain, graphite hatching, paint reveal, stars, constellation, moon glow, and felt-piano soundtrack live at runtime with plain JS + WebGL.

### 기차 창밖으로 지나가는 사계절
- 작성자: [@itsolelehmann](https://x.com/itsolelehmann/status/2103124033365762215) · [Skillry 재현본](https://skillry.dev/ai-videos/opus-5-5/itsolelehmann-762215)
- 기술 태그: canvas · 분류: motion · 프롬프트 길이: 115자
- 요약: 아늑한 객실, 테이블 위 커피 한 잔, 창밖으로 사계절이 지나가는 장면을 웨스 앤더슨(『그랜드 부다페스트 호텔』) 풍으로 그립니다. 한 줄짜리 프롬프트입니다.
- **이 리더에 쓰는 법:** 『시크릿 가든』에 씁니다. 기차 창 대신 화원 담장 문 너머로 겨울 → 봄 → 여름 → 가을이 지나가게 하고, 읽기 진행률(%)에 따라 계절이 바뀌는 배경으로 만들면 메리가 화원을 되살리는 흐름과 맞습니다.

**프롬프트 원문 (전체):**

> 4 seasons passing outside a train window, a cozy carriage, a cup of coffee on the table, Grand Budapest Hotel style

### '안개 속의 고슴도치' 같은 6.5분 단편
- 작성자: [@superalesha](https://x.com/superalesha/status/2103052154931970412)
- 기술 태그: (태그 없음) · 분류: motion · 프롬프트 길이: 1006자
- 요약: 9363프레임 전부를 JS 캔버스로 그린 단편입니다. 장면마다 찢은 종이 콜라주, 검은 종이 위 분필, 물속 티슈 페이퍼, 라이트 테이블 위 모래, 팝업북 같은 서로 다른 '종이' 질감을 쓰고, '짧게-짧게-길게' 비밀 노크라는 모티프 하나로 음악까지 묶습니다.
- **이 리더에 쓰는 법:** 책 분위기 질감을 고를 때 레퍼런스 목록으로 씁니다. 테마 설정에 '종이 콜라주 / 분필 / 팝업북' 스킨을 두는 식입니다. 모티프 하나로 전체를 묶는 방식은 『시크릿 가든』의 울새, 『오페라의 유령』의 음악 상자에 응용할 수 있습니다.

**핵심 규칙 (한국어 요약):** 노르시테인 작품을 베끼지 않고 새 이야기를 씁니다(빨간 목도리를 한 생쥐, 안개 속 낚시하는 두더지 할아버지, 호두 껍데기 등불). 이미지·영상 생성 모델 없이 캔버스로만 그리고, 장면마다 다른 종이 매체 질감을 씁니다. 음악은 비밀 노크 리듬을 중심으로 Python으로 작곡했습니다.

**원문 앞부분:**

> make an animated short that felt like Hedgehog in the Fog. I didn’t want to copy Yuri Norstein’s film, so we went with a new story.
>
> It runs for 6.5 minutes. All 9363 frames are drawn by JavaScript code written by Opus. No video or image generation models, just canvas.
>
> It follows a little mouse in …

### 그리스 항아리 표면에 그린 트로이 목마
- 작성자: [@perezalexa23](https://x.com/perezalexa23/status/2103027565703414045)
- 기술 태그: (태그 없음) · 분류: motion · 프롬프트 길이: 241자
- 요약: 20초 HTML 애니메이션입니다. 고대 그리스 항아리 표면에 이야기를 그리고, 항아리가 돌아가면서 목마 입성 → 밤 → 병사 등장이 이어집니다. 모든 그림은 코드로 그립니다.
- **이 리더에 쓰는 법:** '물건 표면에 이야기를 그려 돌리기' 형식을 목차 화면 장식으로 씁니다. 『오페라의 유령』 줄거리는 오르골 원통에, 『젊은 베르테르의 슬픔』은 편지 봉투 띠지에 그리는 식입니다. 2D로 감아 돌리는 연출이라 가볍습니다.

**프롬프트 원문 (전체):**

> Tell the Trojan Horse story in a 20-second HTML animation painted around an ancient Greek vase. Rotate the vase as the horse enters the city, night falls, and hidden warriors emerge. Draw everything in code; no external assets or website UI.

### 고전 소설을 종이 인형 단편으로
- 작성자: [@NoFollowers2023](https://x.com/NoFollowers2023/status/2104792004978974928)
- 기술 태그: (태그 없음) · 분류: 3d · 프롬프트 길이: 166자
- 요약: 토머스 하디의 『광란의 무리를 떠나』를 우주 전초기지 배경으로 옮기고, 인물을 종이 오려내기 인형으로 만든 짧은 영화입니다.
- **이 리더에 쓰는 법:** 퍼블릭 도메인 소설을 '종이 인형 단편'으로 바꾸는 가장 짧은 틀입니다. 『젊은 베르테르의 슬픔』의 편지 한 통을 종이 인형극으로 만드는 식입니다. 배경을 바꾸는 각색은 선택 사항이고, 학습용이라면 원작 배경을 그대로 두는 편이 낫습니다.

**프롬프트 원문 (전체):**

> A short film of Thomas Hardy's Far From The Madding Crowd, but it's set on a space outpost under attack from an invasive plant, and the characters are paper cut-outs.

## 4. 학습용 인터랙티브

### 슬라이더로 바뀌는 개념 설명 프레젠테이션
- 작성자: [@Drake5112](https://x.com/Drake5112/status/2108394129000661428)
- 기술 태그: (태그 없음) · 분류: interactive · 프롬프트 길이: 464자
- 요약: 사용자 수 슬라이더를 움직이면 연결 밀도가 실시간으로 바뀌고, 내레이션이 화면 변화와 맞춰 나오는 인터랙티브 설명 페이지입니다. 외부 이미지 없이 HTML/JS만 씁니다.
- **이 리더에 쓰는 법:** '슬라이더 + 실시간 변화 + 동기 내레이션' 구조를 어휘에 씁니다. 예: 슬라이더로 *glad → happy → overjoyed* 감정 강도를 고르거나, 문장에 수식어를 하나씩 더하면 TTS가 다시 읽어 주는 위젯. 단일 파일 원칙과 그대로 맞습니다.

**프롬프트 원문 (전체):**

> Create an interactive HTML presentation explaining the concept of 'Network Effects' where connections grow exponentially as user count increases (e.g., 5x users = 27x connections). The interface should include a slider allowing the viewer to manually adjust the number of users and see the resulting change in connection density in real-time. Use only HTML and JavaScript without external image assets. Include voice narration synchronized with the visual changes.

### 픽셀 마법사: 가벼운 캔버스 렌더링 규칙의 모범
- 작성자: [@zacxbt](https://x.com/zacxbt/status/2103808699466944604) · [Skillry 재현본](https://skillry.dev/ai-videos/opus-5-5/zacxbt-944604)
- 기술 태그: canvas, pixel, playable · 분류: interactive · 프롬프트 길이: 2209자
- 요약: 128×96 오프스크린 캔버스에 그려 정수 배율로 확대하고, 24색 고정 팔레트, 8~12fps 느낌의 포즈 양자화, 미리 할당한 파티클 풀, 루프 안 객체 할당 0을 지키는 픽셀 아트 루프입니다.
- **이 리더에 쓰는 법:** 챕터를 끝냈을 때 나오는 '읽기 보상' 마스코트로 씁니다(마법사가 주문을 외우며 축하). 렌더링 규칙(정수 배율, `imageSmoothingEnabled=false`, 할당 0)은 폰에서 부담 없는 캔버스 효과 전반에 재사용할 수 있습니다.

**핵심 규칙 (한국어 요약):** 모든 그리기는 논리 캔버스의 정수 좌표에 맞추고, 서브픽셀·안티앨리어싱·그라디언트·shadowBlur를 쓰지 않습니다. 캐릭터는 사각형과 픽셀 런으로 절차적으로 만들고 포즈를 파라미터화합니다. 상태 머신은 IDLE → CHARGE → CAST → RECOVER 순으로 돕니다. 업데이트는 고정 60Hz, 렌더는 rAF로 합니다. 배경은 최소한으로 두어 실루엣이 잘 읽히게 하고, 보석에서 나오는 1px 림 라이트를 줍니다.

**원문 앞부분:**

> Create a single self-contained HTML file that renders an animated pixel art wizard casting a spell, using vanilla JavaScript and Canvas 2D. No external assets, libraries, or network requests.
>
> RENDERING
> - Draw everything to an offscreen canvas at a fixed logical resolution of 128x96, then blit to a …

### 젠 가든: 손가락으로 모래에 결 긋기
- 작성자: [@arixxbt](https://x.com/arixxbt/status/2108541814718292438)
- 기술 태그: (태그 없음) · 분류: interactive · 프롬프트 길이: 518자
- 요약: 드래그하면 모래에 골 5개와 이랑 6개가 파이는 단일 HTML 시뮬레이션입니다. 이끼 낀 바위, 석등, 단풍나무가 있고, 골든아워로 바꾸면 해가 낮아져 골마다 그림자가 집니다.
- **이 리더에 쓰는 법:** 『시크릿 가든』의 '쉬어 가기' 화면으로 씁니다. 다만 1536px 높이맵과 잎 420장은 폰에 무거우니 격자를 절반 이하로 줄이고, 그림자 계산은 터치가 끝났을 때만 하는 식으로 가볍게 바꿔야 합니다.

**프롬프트 원문 (전체):**

> Create an interactive zen garden simulation in a single HTML file. Implement a 1536px heightmap on a 440x440 grid for the sand. Allow users to drag across the sand to cut grooves (5 grooves and 6 ridges per stroke) along their path. Include 5 mossy rocks, 2 stone lanterns, and a maple tree with 420 leaves. Add a time-of-day toggle; when set to golden hour, drop the sun low so every groove throws a shadow. Ensure the rendering handles moss visibility through sand and prevents blocky rocks or out-of-frame lanterns.

## 5. 재사용 가능한 프롬프트 틀

### renderAt(t) 순수 함수 UI 모션 루프 틀
- 작성자: [@flxrnc](https://x.com/flxrnc/status/2108242454105251921)
- 기술 태그: (태그 없음) · 분류: motion · 프롬프트 길이: 1973자
- 요약: 입력을 형용사가 아니라 hex 코드·초·감쇠비·px로 받고, 하나의 도형이 컷 없이 여러 상태로 변하는 14초 루프를 만드는 구조화된 프롬프트입니다(inputs / direction / structure / build / gotchas / start).
- **이 리더에 쓰는 법:** 리더의 장식 애니메이션(페이지 넘김, 팝업, 북마크)을 '시간의 순수 함수'로 짜 두면 `?t=`로 특정 순간을 멈춰 디버깅하거나 스크린샷 테스트하기 쉽습니다. Claude에게 UI 모션을 요청할 때 '형용사 대신 숫자로' 원칙을 그대로 쓰면 됩니다.

**핵심 규칙 (한국어 요약):** 닫힌 형식(closed-form) 스프링을 씁니다(도형: 감쇠 0.72, 0.35초 / 카메라: 1.0, 0.6초). 내용이 바뀔 때는 12px 블러와 0.15초 페이드를 씁니다. 0.5초 비트 그리드를 쓰고, 마지막 프레임이 첫 프레임과 같아야 합니다. `window.renderAt(t)`는 순수 함수여야 하므로 Math.random, 시계, 이월 상태를 쓰지 않으며, `?t=`로 정확한 순간을 고정합니다. 루프 경계의 커서 튐은 `t - 14*floor(t/14)`로 고칩니다. 커서 속도는 65px/프레임 이하로 합니다. 진행은 스토리보드 → 코드 → 첫 렌더 뒤 비트마다 5프레임 점검 순서입니다.

**원문 앞부분:**

> <inputs>
> Give me:
>
> * canvas color
> * shape color
> * accent color
> * shape radius
> * fonts
> * the states the shape should morph through
>
> Use hex codes, seconds, damping ratios and pixel sizes instead of adjectives.
> </inputs>
>
> <direction>
> Make a 14 second, 1440x1440, 60fps seamless UI motion loop.
>
> One …

### draw(f): 프레임 번호만 보고 그리는 4단계 파이프라인
- 작성자: [@0xKarmi](https://x.com/0xKarmi/status/2108495927988129839)
- 기술 태그: (태그 없음) · 분류: motion · 프롬프트 길이: 1383자
- 요약: '프레임 720을 달라고 하면 프레임 0과 픽셀 하나까지 같은 그림이 나온다'는 원칙을 나비 날갯짓으로 설명한 글 겸 프롬프트입니다. STAGE / RENDER / ENCODE / CHECK 4단계로 나눠, 모델은 첫 단계(그리기 프로그램)만 쓰고 나머지는 재사용합니다.
- **이 리더에 쓰는 법:** 요청하신 'one draw(t) function' 규칙을 가장 명료하게 설명한 글입니다. 리더에 애니메이션을 추가할 때 이 4단계를 체크리스트로 쓰고, 특히 '프레임 0과 마지막 프레임 비교(이음새 검사)'는 루프 배경 장면(사계절, 촛불)에 꼭 필요합니다.

**핵심 규칙 (한국어 요약):** STAGE는 고정 1000×1080 캔버스에 폰트를 내장합니다. RENDER는 창 없는 엔진이 프레임 번호마다 `draw(f)`를 한 번씩 부릅니다. ENCODE는 ffmpeg H.264로 픽셀 종횡비를 명시합니다. CHECK는 빌드마다 3패스입니다. 그림은 프레임 번호에만 의존해야 하므로 시계, 타이머, 실행마다 달라지는 난수를 쓰지 않습니다. 스모크 테스트는 루프를 한 번 돌려 스크립트 오류부터 글자 겹침까지 6종 결함을 예/아니오로 셉니다. 이음새 검사에서 픽셀 하나라도 다르면 주기적이지 않은 움직임이 있다는 뜻입니다.

**원문 앞부분:**

> Picture a butterfly with no memory of its last wingbeat.
> Ask it for frame 720 and you get frame 0, pixel for pixel.
>
> 720 frames. 12 seconds. 6 counters. All at 0.
>
> Opus 5.5 can't hand over a video file, one builder says. He made that gap the method.
>
> > STAGE - one fixed 1000x1080 canvas, fonts …

### seek(t) 12초 영상 + 스틸 5장 혹평 후 수정
- 작성자: [@notdwd](https://x.com/notdwd/status/2105031774904766641)
- 기술 태그: (태그 없음) · 분류: motion · 프롬프트 길이: 1267자
- 요약: 한 HTML 파일의 `seek(t)`로 모든 프레임을 그리고 Playwright와 ffmpeg로 렌더하는 12초 영상입니다. 렌더 전에 스틸 5장을 뽑아 '깐깐한 모션 디렉터처럼' 비평하고, 가장 나쁜 문제 3개를 고친 다음 렌더하게 합니다.
- **이 리더에 쓰는 법:** 리더 소개 영상(README나 공유용)을 만들 때 그대로 씁니다. 'pill에 make a launch video 타이핑' 자리에 '단어를 탭하면 뜻과 번역이 뜨는 장면'을 넣으면 됩니다. '폰에서 크게 읽히게' 규칙이 이 앱과 맞습니다.

**핵심 규칙 (한국어 요약):** 빨리 도착하고 부드럽게 착지합니다(프레임마다 남은 거리의 12~19%). 홀드 중에도 느린 푸시를 둬서 화면이 완전히 얼지 않게 합니다. 스태거는 2~4프레임, 블러는 빠른 움직임에만 줍니다. 폰에서도 크고 읽기 쉬워야 합니다. 오프화이트·잉크·오렌지 한 색만 씁니다. 소리는 키마다 틱, 엔터에 클릭, 프레임 스탬프마다 오르는 음, 착지에 쿵입니다.

**원문 앞부분:**

> Make a 12s motion video in code (1920x1080, 30fps, one HTML file drawing every frame from a single seek(t) function, rendered with Playwright + ffmpeg, with original synthesized sound).
>
> Story: a dark prompt pill on an off-white page types "make a launch video" with a real keystroke rhythm → enter, …

### 연표 영상 + 렌더 전 컨택트 시트 검사
- 작성자: [@niirajrshah](https://x.com/niirajrshah/status/2104551261270163739)
- 기술 태그: (태그 없음) · 분류: 3d · 프롬프트 길이: 388자
- 요약: 인생 연표를 받아 장면 하나에 순간 하나씩, 연도는 크게, 내용은 한 줄로 보여 주는 영상입니다. 모든 프레임을 시간의 함수로 만들고, 렌더 전에 정지 화면 모음(컨택트 시트)을 만들어 겹침과 철자를 확인하게 합니다.
- **이 리더에 쓰는 법:** 작가 연표(메리 셸리, 괴테, 가스통 르루, 프랜시스 호지슨 버넷) 화면이나 작품 속 사건 타임라인에 씁니다. '렌더 전에 철자 검사'는 영어 학습 콘텐츠에서 특히 중요한 규칙입니다.

**프롬프트 원문 (전체):**

> Here is my life timeline. Turn it into a [45]-second motion graphics video, 1080 x 1350, for LinkedIn. One scene per moment. Show the year large and the moment in one line, and move between them. Build it as one HTML file where every frame is a part of time
> Before you render, make a contact sheet of stills, check it for overlaps and spelling, and fix what is wrong. Then render the MP4.

---

## 바로 써 볼 만한 3개

1. **UI 카드 타이밍 수치 + 검증 루프 (@fleyta88)**: 지금 있는 '단어 탭 → 뜻 팝업'을 바로 다듬을 수 있습니다. 280/220/160ms에 60ms 스태거라는 숫자가 이미 정해져 있어서 CSS `transition-delay` 몇 줄로 옮기면 끝나고, 라이브러리나 빌드 단계가 필요 없습니다. 위의 '점 → 검색창' 전환(@cgclick)과 합치면 팝업이 열리는 모양까지 정리됩니다.
2. **ESCAPE THE ORBIT (@Gdgtify)**: 명문장 카드는 네 작품 모두에 쓸 수 있고, 이 프롬프트의 가독성 규칙(원문 고정, `[…]` 생략 표시, 읽기 홀드가 끝나기 전 장식 금지, 최소 글자 크기, `seek(t)` 결정적 렌더)이 '읽기 앱'의 우선순위와 정확히 같습니다. 문구와 은유만 바꿔(예: 베르테르의 편지 → 접힌 종이가 펼쳐지는 기준선) 챕터마다 하나씩 만들 수 있습니다.
3. **색연필 그림책 스타일 글 설명 (@woojinrad)**: 학습 효과가 가장 직접적입니다. 챕터 본문을 넣으면 '핵심 3가지 + 본문에서 그대로 가져온 캡션'이 나오므로 요약을 읽으면서 원문 문장을 한 번 더 보게 됩니다. Canvas 2D와 Web Audio만 쓰니 폰에서도 가볍고, 스토리보드를 먼저 확인하는 단계가 있어 결과를 통제하기도 쉽습니다.
