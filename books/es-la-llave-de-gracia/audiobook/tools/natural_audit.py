"""1·2장 자연스러움 측정(11-16): 토막별 음높이·빠르기·음량·쉼, 이웃 토막 간 차이."""
import sys, csv, re, json, wave, statistics as st
import numpy as np
sys.path.insert(0, '.')
import voicebox_book as V
R = 24000
def load(key):
    p = V.CACHE / f'{key}.wav'
    if not p.exists(): return None
    with wave.open(str(p)) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return a if w.getframerate() == R else None
def f0(a):
    fr, hop = int(R*0.04), int(R*0.01); out = []
    for i in range(0, len(a)-fr, hop):
        x = a[i:i+fr]; 
        if np.sqrt((x**2).mean()) < 0.02: continue
        x = x - x.mean(); c = np.correlate(x, x, 'full')[fr-1:]
        lo, hi = R//400, R//75
        k = lo + np.argmax(c[lo:hi])
        if c[k] > 0.45*c[0]: out.append(R/k)
    return float(np.median(out)) if len(out) > 5 else None
def pauses(a):
    fr = int(R*0.02); e = np.array([np.sqrt((a[i:i+fr]**2).mean()) for i in range(0, len(a)-fr, fr)])
    th = max(e.max()*0.03, 1e-4); sil = e < th; runs=[]; n=0
    for s in sil:
        if s: n+=1
        else:
            if n: runs.append(n*0.02); n=0
    lead = next((i for i,s in enumerate(sil) if not s), 0)*0.02
    trail = next((i for i,s in enumerate(sil[::-1]) if not s), 0)*0.02
    inner = [r for r in runs[1:]] if runs else []
    speech = (~sil).sum()*0.02
    return lead, trail, max(inner) if inner else 0, speech, 20*np.log10(e[~sil].mean()+1e-9)
def syl(t, lang):
    return len(re.findall('[가-힣]', t)) if lang=='ko' else len(re.findall(r'[aeiouáéíóúü]+', t.lower()))
rows=[]
for ch in (int(sys.argv[1]),):
    for q in csv.DictReader(open(f'out_vb/ch{ch:02d}'+sys.argv[2]+'.qa.tsv'), delimiter='\t'):
        a = load(q['key'])
        if a is None: continue
        lead, trail, inner, sp, db = pauses(a)
        rows.append(dict(ch=ch, seg=int(q['seg']), piece=int(q['piece']), who=q['who'], voice=q['voice'], lang=q['lang'],
            text=q['text'], heard=q['heard'], mode=q['mode'], f0=f0(a), rate=syl(q['text'],q['lang'])/sp if sp>0.2 else None,
            inner=inner, db=db, sec=len(a)/R, nsyl=syl(q['text'],q['lang'])))
pass
def grp(f):
    return [r for r in rows if f(r)]
def summ(name, rs, k):
    v=[r[k] for r in rs if r[k]]
    if v: print(f'{name:28s} n={len(v):3d} {k} 중앙 {st.median(v):6.1f}  10%~90% {np.percentile(v,10):6.1f}~{np.percentile(v,90):6.1f}')
for k in ('f0','rate','db'):
    summ('서술 한국어(narr1)', grp(lambda r:r['who']=='narr' and r['lang']=='ko'), k)
    summ('서술 속 스페인어(yunha)', grp(lambda r:r['who']=='narr' and r['lang']=='es'), k)
    summ('윤하 대사 스페인어', grp(lambda r:r['who']=='yunha' and r['lang']=='es'), k)
    summ('윤하 대사 한국어', grp(lambda r:r['who']=='yunha' and r['lang']=='ko'), k)
# 이웃 토막 차이(같은 조각 안)
jumps=[]
for a,b in zip(rows, rows[1:]):
    if a['ch']==b['ch'] and a['seg']==b['seg'] and a['f0'] and b['f0']:
        jumps.append((abs(12*np.log2(b['f0']/a['f0'])), a, b))
lj=[j for j in jumps if j[1]['lang']!=j[2]['lang']]; sj=[j for j in jumps if j[1]['lang']==j[2]['lang']]
print('조각 안 이웃 토막 음높이 차(반음): 언어 바뀜 중앙 %.1f (n=%d) / 같은 언어 중앙 %.1f (n=%d)'%(st.median([j[0] for j in lj]),len(lj),(st.median([j[0] for j in sj]) if sj else 0),len(sj)))
print('3반음 넘게 튀는 곳:', sum(1 for j in jumps if j[0]>3))
for j in sorted(jumps, key=lambda x:-x[0])[:8]:
    print(f"  {j[1]['ch']}장 {j[1]['seg']}: {j[0]:.1f}반음 [{j[1]['text'][-20:]}]→[{j[2]['text'][:20]}]")
rr=[r for r in rows if r['rate'] and r['nsyl']>=6]
print('빠르기 이상(서술 한국어 기준 ±25% 밖):')
base=st.median([r['rate'] for r in rr if r['who']=='narr' and r['lang']=='ko'])
odd=[r for r in rr if r['who']=='narr' and r['lang']=='ko' and abs(r['rate']/base-1)>0.25]
print(f'  서술 한국어 {len(odd)}개 / 기준 {base:.1f}음절/초')
for r in sorted(odd,key=lambda r:r['rate'])[:6]: print(f"  {r['ch']}장 {r['seg']}-{r['piece']} {r['rate']:.1f} [{r['text'][:30]}]")
print('토막 안 긴 쉼(>0.8초):', [(r['ch'],r['seg'],round(r['inner'],1),r['text'][:20]) for r in rows if r['inner']>0.8][:12])
short=[r for r in rows if r['who']=='narr' and r['lang']=='ko' and r['nsyl']<=4]
print('서술 한국어 4음절 이하 짧은 토막:', len(short), [r['text'] for r in short][:25])
print('조각당 토막 수(서술):', np.bincount([max(r['piece'] for r in rows if r['ch']==c and r['seg']==s) for c,s in {(r['ch'],r['seg']) for r in rows if r['who']=='narr'}])[1:].tolist())
