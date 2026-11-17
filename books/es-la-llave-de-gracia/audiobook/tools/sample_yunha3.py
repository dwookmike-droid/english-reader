"""3장 샘플: 윤하 스페인어 억양 · 스페인어 낱말+조사 붙여 읽기 비교(11-16)."""
import sys, re, json
sys.path.insert(0, '.')
import voicebox_book as V
A = V.A
OUT = sys.argv[1]
CH = 3
NARR_SEGS = [8, 11, 24, 26, 38, 62, 67]
YUN_SEGS = [12, 23, 40, 51, 63, 68]
HANGUL = {'tomates': '토마테스', 'melocotones': '멜로코토네스', 'queso': '케소', 'cuatro': '쿠아트로',
          'cincuenta': '신쿠엔타', 'veinte euros': '베인테 에우로스', 'yo': '요', 'Jaume': '자우메',
          'abuela': '아부엘라', 'yave': '야베', 'adiós': '아디오스', 'guapa': '과파'}
segs = A.segments(CH)
def gap_after(t):
    return V.PACE_COSY['join']['stop'] if re.search(r'[.?!…:]$', t) else V.PACE_COSY['join']['mid']

def merged(s, mode):
    """mode 'cur': 지금 그대로. 'latin': 조사가 붙은 스페인어 낱말을 한국어 토막에 로마자로 넣는다.
    'hangul': 같은 자리를 한글 표기로."""
    sp = [list(x) for x in V.spoken(s, CH)]
    if mode == 'cur':
        return sp
    out = []
    i = 0
    while i < len(sp):
        l, t = sp[i]
        if l == 'es' and i + 1 < len(sp) and sp[i + 1][0] == 'ko' and V.glued(s, CH, t, sp[i + 1][1]):
            w = t.strip()
            w = HANGUL.get(w.rstrip('.'), w) if mode == 'hangul' else w
            nxt = w + sp[i + 1][1]
            if out and out[-1][0] == 'ko' and not re.search(r'[.?!…:]$', out[-1][1]):
                out[-1][1] += ' ' + nxt
            else:
                out.append(['ko', nxt])
            i += 2
            continue
        out.append([l, t]); i += 1
    return out

def render(s, mode, es_voice):
    parts = []
    for l, t in merged(s, mode):
        if l == 'ko':
            v = 'narr1'
            pid = V.spec(v, 'ko', s, 'cosy', 'index', None, CH)
        else:
            v = es_voice
            pid = f'cosy|narr||short2' if es_voice == 'cosy-narr' else V.spec('yunha', 'es', s, 'cosy', 'index', None, CH) if es_voice == 'yunha' else f'index|narr||0.45'
        p, m = V.make(pid, v, t, l)
        if l == 'ko' or s['who'] == 'narr':
            p = V.speed(p, V.PACE_COSY['narr_speed']) if s['who'] == 'narr' else p
        print(f'  {mode}/{es_voice} {l} pass={m.get("pass")} [{t[:40]}] → {m.get("heard","")[:50]}', flush=True)
        if parts:
            parts.append(b'\0\0' * int(A.RATE * gap_after(prev)))
        parts.append(V.fade(A.level(p)))
        prev = t
    return b''.join(parts)

def dlg(s, how):
    t = V.spoken(s, CH)[0][1]
    if how == 'cur':
        pid = V.spec('yunha', 'es', s, 'cosy', 'index', None, CH)
    elif how == 'index-kr':
        e, a = V.emotion_of(s.get('note'))
        pid = f"index|narr|{json.dumps(e) if e else ''}|{a}"
    else:
        pid = 'cosy|narr||short2'
    p, m = V.make(pid, 'yunha', t, 'es')
    print(f'  {how} pass={m.get("pass")} [{t}] → {m.get("heard","")}', flush=True)
    return V.fade(A.level(p))

def write(name, chunks):
    sil = b'\0\0' * int(A.RATE * 1.0)
    V.save(f'{OUT}/{name}.wav', sil.join(chunks))
    print('→', name, flush=True)

pick = lambda ids: [segs[i - 1] for i in ids]
for how, label in (('cur', '1_윤하대사_지금'), ('index-kr', '2_윤하대사_한국억양_IndexTTS'), ('cosy', '3_윤하대사_한국억양_CosyVoice')):
    write(label, [dlg(s, how) for s in pick(YUN_SEGS)])
for mode, esv, label in (('cur', 'yunha', 'A_서술_지금'),
                         ('latin', 'yunha', 'B_서술_조사붙임_로마자'),
                         ('hangul', 'yunha', 'C_서술_조사붙임_한글표기'),
                         ('latin', 'index-kr', 'D_서술_조사붙임_단독낱말도한국억양')):
    write(label, [render(s, mode, esv) for s in pick(NARR_SEGS)])
