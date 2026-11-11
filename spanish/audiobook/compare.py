#!/usr/bin/env python3
"""모델 비교판(11-09). 같은 장면을 Gemini 세 모델과 ElevenLabs 두 모델로 만들어 나란히 듣는다.

    python3 spanish/audiobook/compare.py --plan     # 요청 없이 묶음·프롬프트만
    python3 spanish/audiobook/compare.py            # 생성 → audiobook/out/compare/

Gemini는 프롬프트·목소리·묶음(장면 묶음, 한 모델)·쉼·음량을 모두 같게 하고 모델만 바꾼다.
"""
import argparse, sys, wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import audiobook as A  # noqa: E402

SAMPLES = [   # 이름, 장, 시작 조각 앞머리, 끝 조각에 든 말
    ('S1_서술', 1, '외할머니가 돌아가신', '첫 줄만 빼고'),
    ('S2_몬세첫만남', 1, '하숙집 문을 연 사람은', '두 번째 llave였다'),
    ('S3_발레등장', 2, '그때 부엌 문이 벌컥', 'Vale, como'),
    ('S4_마르크고백', 26, '공원 호수에서', 'Estaban allí'),
]
GEMINI = {'2.5flash': 'gemini-2.5-flash-preview-tts', '3.1flash': 'gemini-3.1-flash-tts-preview',
          '2.5pro': 'gemini-2.5-pro-preview-tts'}
ELEVEN = ['eleven_v4', 'eleven_v3']
EL_NARR = 'ksaI0TCD9BstzEzlxj4q'     # Seulki — 차분한 30–40대 한국 여성 낭독(워크스페이스에 있는 목소리)
EL_MARTI = A.CAST['marti']['voice']  # Álvaro Sereno
MARTI = (13, 'Ahora tú estás')       # S5 마르티 편지 한 단락
OUT = A.OUT / 'compare'


def pick(ch, start, end):
    segs = A.segments(ch)
    i = next(k for k, s in enumerate(segs) if s['text'].startswith(start))
    j = next(k for k in range(i, len(segs)) if end in segs[k]['text'])
    return segs[i:j + 1]


def scene_units(segs):
    """한 모델로 만들 때의 장면 묶음: 서술과 대화를 섞되 화자 둘, 1200자, 분위기 지시가 바뀌면 끊는다."""
    out, cur = [], []
    for s in segs:
        labels = {A.voice_of(x)['label'] for x in cur + [s]}
        if cur and (len(labels) > 2 or sum(len(x['text']) for x in cur) + len(s['text']) > A.CHUNK_MAX
                    or (s.get('note') and any(x.get('mood') for x in cur))):
            out.append(cur); cur = []
        cur.append(s)
    out.append(cur)
    for u in out:
        lane = 'narr' if all(x['kind'] != 'say' and x['who'] in A.YUNA for x in u) else 'dlg'
        for x in u:
            x['lane'] = lane
    return out


def assemble(units, paths, path):
    pcm = bytearray()
    for u, ps in zip(units, paths):
        for p in ps:
            with wave.open(str(p)) as w:
                a = w.readframes(w.getnframes())
            a = A.squash_gaps(a)
            if len(u) > 1:
                a = A.turn_pauses(a, u)
            pcm += A.level(a) + b'\0\0' * int(A.RATE * A.PAUSE['para'])
    save(bytes(pcm), path)


def save(pcm, path):
    OUT.mkdir(parents=True, exist_ok=True)
    wav = path.with_suffix('.wav')
    with wave.open(str(wav), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(A.RATE); w.writeframes(pcm)
    A.subprocess.run(['afconvert', '-f', 'm4af', '-d', 'aac', '-b', '64000', str(wav), str(path)], check=True)
    wav.unlink()
    print(f'  {path.name}: {len(pcm) / 2 / A.RATE:.0f}초')


def eleven(text, voice, model):
    pcm = A.post(f'https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=pcm_24000',
                 {'text': text, 'model_id': model}, {'xi-api-key': A.os.environ['ELEVENLABS_API_KEY']}, raw=True)
    A.log('eleven', len(text), 0, len(text), f'[{model}] {text}')
    return A.level(A.trim(pcm))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--v2', action='store_true', help='11-10 판: 2.5 Pro, 장면 설명·줄별 지시·앞 대목, S2–S4')
    a = ap.parse_args()
    if a.v2:
        return v2(a.plan)
    samples = [(name, scene_units(pick(ch, s, e))) for name, ch, s, e in SAMPLES]
    marti = next(x for x in A.segments(MARTI[0]) if x['text'].startswith(MARTI[1]))
    s1_text = ' '.join(x['text'] for u in samples[0][1] for x in u)
    if a.plan:
        for name, units in samples:
            print(f'== {name}: {len(units)}묶음, {sum(len(x["text"]) for u in units for x in u)}자')
            for u in units:
                print('   ', A.unit_prompt(u)[0][:300].replace('\n', ' | '))
        print(f'== ElevenLabs: S1 {len(s1_text)}자, S5 마르티 {len(marti["text"])}자, 모델 {len(ELEVEN)}개')
        return
    for tag, model in GEMINI.items():
        A.unit_model = lambda u, m=model: m
        for name, units in samples:
            if (OUT / f'{name}_{tag}.m4a').exists():
                continue
            try:
                paths = [A.render_unit(u, 6.5) for u in units]
            except A.DailyLimit:
                print(f'  {tag}: 하루 한도 — {name}부터 내일'); break
            assemble(units, paths, OUT / f'{name}_{tag}.m4a')
    for model in ELEVEN:
        save(eleven(s1_text, EL_NARR, model), OUT / f'S1_서술_eleven-{model[7:]}.m4a')
        save(eleven(marti['text'], EL_MARTI, model), OUT / f'S5_마르티편지_eleven-{model[7:]}.m4a')
    print('누적', A.spent())


def v2(plan_only):
    """끊김·맥락 고친 판(11-10). 묶음은 audiobook.scene_units, 조립은 audiobook.assemble.
    _v2: 화자 전환 쉼 넣음, _v2B: 넣지 않음(같은 캐시로 조립만 다르게)."""
    A.unit_model = lambda u: A.BOOK_MODEL
    for name, ch, s, e in SAMPLES[1:]:
        us = A.scene_units(pick(ch, s, e))
        if plan_only:
            print(f'===== {name}: {len(us)}묶음 =====')
            for u in us:
                prompt, cfg = A.unit_prompt(u)
                spk = [c['speaker'] for c in cfg.get('multiSpeakerVoiceConfig', {}).get('speakerVoiceConfigs', [])]
                print(f'--- {sum(len(x["text"]) for x in u)}자, 화자 {spk or "하나"}\n{prompt}\n')
            continue
        try:
            paths = [A.render_unit(u, 6.5) for u in us]
        except A.DailyLimit:
            print(f'  하루 한도 — {name}부터 내일'); break
        save(A.assemble(us, paths), OUT / f'{name}_2.5pro_v2.m4a')
        save(A.assemble(us, paths, turns=False), OUT / f'{name}_2.5pro_v2B.m4a')
    for unit, why in A.REVIEW:
        print('  ! 들어 볼 곳:', why, '—', unit[0]['text'][:40])
    if not plan_only:
        print('누적', A.spent())


if __name__ == '__main__':
    main()
