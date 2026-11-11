import json,wave,sys,glob,numpy as np
S=sys.argv[1]
rows=json.load(open(S+'/bugs3.json'))
cand=[r for r in rows if r['voice']<=0.5 and r['to_next'] is not None and r['to_next']<=1.5 and r['nat']<=0.7]
# preload cache at 6k
lib=[]
for f in sorted(glob.glob('cache/*.wav')):
    w=wave.open(f)
    if w.getframerate()!=24000: continue
    b=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)
    lib.append((f,b,b[::4]))
pil={}
for ch in (1,2,3):
    w=wave.open(f'{S}/ch0{ch}.wav'); pil[ch]=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)
out=[]
for r in cand:
    a=pil[r['ch']]; zs=r['zs']
    q=a[zs-72000:zs][::4]; q=(q-q.mean())/(q.std()+1e-6)
    best=(0,None,0)
    for f,b,b6 in lib:
        if len(b6)<len(q): continue
        n=1<<int(np.ceil(np.log2(len(b6)+len(q))))
        c=np.fft.irfft(np.fft.rfft(b6,n)*np.conj(np.fft.rfft(q,n)),n)[:len(b6)-len(q)]
        e=np.sqrt(np.convolve(b6*b6,np.ones(len(q)),'valid')[:len(c)])+1e-6
        cc=c/e/np.sqrt(len(q)); i=int(np.argmax(cc))
        if cc[i]>best[0]: best=(float(cc[i]),f,(i+len(q))*4)
    sc,f,pos=best
    b=next(x[1] for x in lib if x[0]==f)
    # raw: quiet run starting near pos (<500 in 10ms frames)
    seg=np.abs(b[pos-2400:pos+24000]); n=len(seg)//240; pk=seg[:n*240].reshape(n,240).max(1)
    k=0
    while k<n and pk[k]>=500: k+=1
    j=k
    while j<n and pk[j]<500: j+=1
    raw_gap=(j-k)/100
    m,s=divmod(r['final'],60)
    r.update(unit=f.split('/')[-1],score=round(sc,3),raw_gap=raw_gap,label=f"{r['ch']}장 {int(m)}:{s:04.1f}")
    out.append(r)
    print(f"{r['label']} 조립후쉼 {r['nat']+r['zero']:.2f} 원본쉼 {raw_gap:.2f} 뒤소리 {r['voice']:.2f} 상관 {sc:.2f} {r['who']}→{r['nxt']} …{r['text'][-26:]}",flush=True)
json.dump(out,open(S+'/verified.json','w'),ensure_ascii=False,indent=1)
