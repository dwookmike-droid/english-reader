"""2장 시험(11-17 Mike): 몬세 calle 발음 후보 · 스페인어 낱말+'와' 조사 한 토막으로 읽기."""
import sys, re, json
sys.path.insert(0, '.')
import voicebox_book as V
A = V.A
OUT = sys.argv[1]
CH = 2
segs = A.segments(CH)
find = lambda pat: next(s for s in segs if re.search(pat, s['text']))

# 1) 몬세 calle: 원고 그대로 / 'ie'(이 소리, 원고 서술과 맞춤) / 'lie'(카탈루냐 노인의 ʎ, 깔례)
CALLE = [('A_지금', None),
         ('B_Ca-ie', {'¡Calle! ¡Ca-lle!': '¡Caie! ¡Ca-ie!', 'A la calle de tu abuela.': 'A la caie de tu abuela.'}),
         ('C_Ca-lie', {'¡Calle! ¡Ca-lle!': '¡Calie! ¡Ca-lie!', 'A la calle de tu abuela.': 'A la calie de tu abuela.'}),
         ('D_Ka-ye', {'¡Calle! ¡Ca-lle!': '¡Kaye! ¡Ka-ye!', 'A la calle de tu abuela.': 'A la kaye de tu abuela.'})]
mont = [find(r'^A la calle de tu abuela'), find(r'^¡Calle! ¡Ca-lle!')]
def montse(s, rep):
    t = s['text'] if not rep else rep[s['text']]
    pid = V.spec('montse', 'es', s, 'cosy', 'index', None, CH)
    p, m = V.make(pid, 'montse', t, 'es')
    print(f'  montse [{t}] pass={m.get("pass")} → {m.get("heard","")}', flush=True)
    return V.fade(A.level(p))

# 2) '와': 스페인어 낱말을 된소리 한글로 바꿔 조사와 한 토막(3장 C안 방식)
HANGUL = {'coreana': '꼬레아나', 'coreano': '꼬레아노', 'a': '아', 'Carrer': '까레르', 'reyóye': '레요예', 'calle': '까예', 'o': '오', 'español': '에스빠뇰'}
WA = [r'coreana와', r'Carrer와', r'rellotge와']
def gap_after(t):
    return V.PACE_COSY['join']['stop'] if re.search(r'[.?!…:]$', t) else V.PACE_COSY['join']['mid']
def merged(s):
    sp = [list(x) for x in V.spoken(s, CH)]
    out, i = [], 0
    while i < len(sp):
        l, t = sp[i]
        if l == 'es' and i + 1 < len(sp) and sp[i + 1][0] == 'ko' and V.glued(s, CH, t, sp[i + 1][1]):
            head, _, w = t.strip().rpartition(' ')
            if head:
                out.append(['es', head])
            nxt = HANGUL.get(w.rstrip('.'), w) + sp[i + 1][1]
            if out and out[-1][0] == 'ko' and not re.search(r'[.?!…:]$', out[-1][1]):
                out[-1][1] += ' ' + nxt
            else:
                out.append(['ko', nxt])
            i += 2; continue
        out.append([l, t]); i += 1
    return out
def narr(s):
    parts, prev = [], ''
    for l, t in merged(s):
        v = 'narr1' if l == 'ko' else 'yunha'
        pid = V.spec(v, l, s, 'cosy', 'index', None, CH) if l == 'ko' else 'index|narr||0.45'
        p, m = V.make(pid, v, t, l)
        p = V.speed(p, V.PACE_COSY['narr_speed'])
        print(f'  {l} pass={m.get("pass")} [{t[:50]}] → {m.get("heard","")[:50]}', flush=True)
        if parts:
            parts.append(b'\0\0' * int(A.RATE * gap_after(prev)))
        parts.append(V.fade(A.level(p))); prev = t
    return b''.join(parts)

sil = b'\0\0' * int(A.RATE * 1.0)
for name, rep in CALLE:
    V.save(f'{OUT}/몬세_{name}.wav', sil.join(montse(s, rep) for s in mont)); print('→', name, flush=True)
for k, pat in enumerate(WA, 1):
    s = find(pat)
    V.save(f'{OUT}/와_{k}_고침.wav', narr(s)); print('→ 와', k, s['text'][:40], flush=True)
