# 「그라시아의 열쇠」 유튜브판 그림 스타일 바이블

> 유튜브 영상용 장면 그림(Grok 이미지 생성) 기준 문서. 모든 프롬프트는 아래 STYLE 문단 + `scenes.tsv`의 prompt + 등장인물 시트 문장 순서로 붙여 쓴다.
> 장면 그림은 낭독이 흐르는 동안 깔리는 배경이다. 하단 1/3은 자막 자리로 비워 둔다.
> 인물 외모 중 원고에 없는 부분은 이 문서에서 정했다. 바꾸려면 여기만 고치고 이미 만든 그림과 맞는지 확인할 것.

## 1. STYLE prefix (every prompt, verbatim)

```
Soft hand-painted watercolor and gouache book illustration, muted warm Mediterranean palette (terracotta, ochre, faded blue, olive green), gentle natural light, calm and quiet mood, small figures, no text, no letters, no signs with writing, no logos, no watermark. 16:9 landscape. The painting fills the whole frame edge to edge, with no blank band, border or frame; the lower third shows only quiet floor, table, ground or water, nothing important.
```

**MEMORY add-on** (scenes set in 1978; `scenes.tsv` prompts for these already begin with "A 1978 memory…"): append

```
Faded sepia-warm washes, softer edges, slightly paler colors, like an old remembered photograph.
```

## 2. Assembling a prompt

```
[STYLE] + [scenes.tsv prompt] + [sheet line for each named character in that prompt]
```

Example (ch05 scene 4): STYLE + prompt + `Montse: …` + `Yuna: …`.
Add the place line from section 4 when the scene is in one of those places.

## 3. Character sheet (paste verbatim)

Source notes in brackets are for us, not for the prompt. **Invented** = not in the manuscript, chosen here.

**Yuna** — `Yuna: Korean woman, 38, slim, medium height, straight black shoulder-length hair in a low ponytail, no makeup; plain cream linen shirt, navy trousers, flat shoes; often holding a small notebook. A small brass key with a flower handle.`
- Manuscript: 38, Korean, writes words on her palm, carries the key in her trouser pocket. Looks and clothes are invented.
- Season variants (append one): Sep–mid Oct: `light grey cardigan over the shirt.` / late Oct–Nov: `charcoal wool coat.` / ch26 date: `green top` (Vale insists green suits her; manuscript). ch30 (August a year later): base outfit.

**Montse** — `Montse: small Catalan woman, 73, only as tall as Yuna's shoulder, short-cropped white hair, large glasses pushed up on her forehead, thin quick hands; simple grey-green house dress under a faded blue apron. Brisk posture.`
- Manuscript: shoulder height to Yuna, short white hair, big glasses on forehead, dry thin hands, apron, fast walker, never cries in public, 73 (74 in ch30). Dress and apron colours are invented.
- Variants: ch16 night out: `blue dress, no apron, hair neatly combed, small evening handbag` (manuscript: blue dress). ch24 Montserrat: `hiking boots, small backpack` (manuscript). ch29 airport: `sunglasses, handbag` (manuscript).

**Vale** — `Vale: Argentine woman, 26, slim, curly dark-brown hair loosely tied on top, lively expression; oversized mustard-yellow T-shirt and jeans, or pajamas at home; often holding a big mug or a mate gourd with a metal straw.`
- Manuscript: twenties, Buenos Aires, curly hair loosely tied, pajamas, big mug, mate with metal straw and thermos, cat pajamas (ch28). Age 26, colours are invented.

**Marc** — `Marc: tall Catalan man, late thirties, long slightly stooped back, short dark-brown hair, short beard, large calm hands; worn grey T-shirt; old wristwatch on a leather strap. Rides an old sky-blue Vespa.`
- Manuscript: tall, short beard, worn grey T-shirt, cloth shopping bag, long slightly stooped back, big quiet hands, oil-stained work apron in the workshop, sky-blue Vespa with two helmets, watch with a tiny five-petal flower on the crown. Hair colour is invented.
- Variants: workshop: `oil-stained work apron`. ch23 and ch25: `dark jacket, white shirt` (manuscript). ch26 date: `grey sweater` (manuscript). ch29: watch gets `a new stiff leather strap` (manuscript).

**Young Martí (1978, memory/photo only)** — `Young Martí: tall, thin Catalan man of 30, black hair, clean-shaven, white shirt with rolled sleeves, dark trousers, wristwatch on a leather strap; quiet, watchful.`
- Manuscript (the photo, ch17): tall, thin, black hair, white shirt, looking at the woman. Born 1948. The rest is invented.

**Young Sun-rye (1978, memory/photo only)** — `Young Sun-rye: Korean woman, 27, slender, dark hair pinned up, long skirt and a blouse with a small flower print; a wide, open smile when happy.`
- Manuscript (photo, ch17): 27, long skirt, small-flower blouse, hair pinned up, big smile. Arrived with a blue suitcase (ch18).

**The child (Yuna's mother at 3, 1978)** — `The child: Korean girl, 3, round cheeks, hair in two pigtails, light-coloured short summer dress.`
- Manuscript (photo): light dress, two pigtails, laughing.

**Young Montse (1978, memory only)** — `Young Montse: small, quick Catalan woman, 25, dark hair in a short bob, cotton summer dress.`
- Manuscript gives only her age (25). Look invented.

**Joan** — `Joan: very small, very old Catalan clockmaker, 83, cotton-white hair, enormous glasses, wool vest even in the heat, often carrying an umbrella.`
- Manuscript: all of this is in the text (ch20, ch28).

**Yuna's mother (today)** — `Yuna's mother: Korean woman in her early fifties, short permed black hair, practical and brisk; in Busan a navy work jacket; in Barcelona a wide sun hat, light blouse, small suitcase.`
- Manuscript: born Feb 1975, work jacket (ch27), sun hat and small suitcase (ch30). Hair is invented.

Minor figures (taxi driver, fruit seller, Jaume, archivist, librarian, Quique, police officers, Luca, Sofía, Pau, the Korean backpacker) are described inside the scene prompt itself. They appear once or twice; no sheet needed.

### Fixed objects

- **The key**: `a small, finger-length brass key, heavier than it looks, a five-petal flower carved on its handle.` (brass is invented; flower, size, weight are in the text)
- **The letters**: `old airmail envelopes with foreign stamps, slanted blue-ink handwriting (illegible)`; the eleventh envelope is `slightly whiter`.
- **The biscuit tin**: `a flat old biscuit tin`.
- **Marc's watch**: `an old wristwatch, leather strap, a tiny five-petal flower on the winding crown`.
- **The grandfather clock**: `taller than a person, dark almost-black wood, small five-petal flowers carved on its sides, white dial with Roman numerals, tiny gold lettering on the dial (illegible), long glass door with thin metal rods like harp strings inside.` Hands at ten past three until ch26, at twelve in ch26, moving from ch28.
- **The pendulum**: `long iron rod ending in a palm-sized round brass disc engraved with a five-petal flower, polished like a small moon.` Wrapped in blue cloth when carried.
- **Marc's Vespa**: `old sky-blue Vespa`. **Workshop van** (ch29–30): `white work van with blue lettering (illegible)`.

## 4. Recurring places (one line each, paste when used)

- **Gràcia street (Montse's street)**: `a narrow Gràcia street of four-storey old buildings, iron balconies with laundry and potted plants, an old wooden street door.`
- **Montse's kitchen**: `a small, warm Barcelona kitchen: wooden table, tiled walls, a stovetop coffee pot, a radio on a shelf, a plain wall clock, a window overlooking a small inner patio.`
- **The patio**: `a small inner patio with patterned floor tiles, potted plants, a clothesline and an old wooden bench.`
- **The rooftop (azotea)**: `a flat Gràcia rooftop reached by a narrow stair: clothesline of white laundry, geranium pots, rooftops rising toward Tibidabo, its lit church and a tall telecom tower with a blinking red light at night.`
- **Plaça de la Vila**: `a square of paving stones and café chairs with a slender stone tower and a large clock near its top.`
- **Marc's workshop (ground floor)**: `a dim locksmith's workshop at the end of a shady alley: half-raised metal shutter, one wall of hundreds of keys on hooks, one wall of old mostly stopped clocks, a worn workbench with a lamp; old keys on red velvet in the window.`
- **The workshop basement**: `a basement down thirteen narrow stone steps, lit by one bare yellow bulb: shelves of boxes, rusty tools, a bicycle without wheels, broken chairs, and the tall grandfather clock against the back wall.`

## 5. Rules

1. Faces small, or seen from behind or from the side, in most scenes. Close faces are where separate generations drift apart; posture and silhouette stay consistent.
2. No readable writing anywhere: letters, envelopes, maps, signs, tickets, boards are fine but always "illegible". Add `(no readable text)` again if Grok starts writing words.
3. Mood comes from light, space and posture, not from faces. No tears in close-up, no open-mouthed shock, no dramatic gestures.
4. Leave the lower third quiet: floor, table surface, water, sky, plain pavement. If Grok puts a key object there, regenerate.
5. Keep the season right: August hot and white light (ch1–11), September softer (ch12–18), October grey and cooler (ch19–25), November cold and clear (ch26–29), August again (ch30).
6. Real places should look like themselves (Park Güell three crosses, Santa Maria del Mar, Montjuïc castle and port cable car, Columbus column, Sant Pau pavilions, Tibidabo red plane, Sant Antoni market, Carmel bunkers, Sitges, Bogatell, Montserrat, Palau de la Música, Horta labyrinth).

## 6. Consistency tips for Grok

- Make the character sheets first: one image per character (full figure, plain light background, front and side view), using STYLE + the sheet line. Do the same for the grandfather clock, the key and the two most-used places (kitchen, basement).
- If Grok's tool accepts a reference or input image (image editing / "use this image"), attach the matching sheet image for every scene with that character. Use at most two references at a time; with more, faces blend.
- Keep the STYLE prefix byte-for-byte identical across all 132 scenes. Do not "improve" it midway.
- If a seed setting is exposed, fix one seed for the whole project and change it only to fix a bad frame.
- Generate a chapter's scenes in one sitting, in order; light and wardrobe stay closer that way.
- Reject and regenerate rather than accept a frame with readable text, a wrong number of people, or a key object in the subtitle area.
