import json,wave,sys,numpy as np
S=sys.argv[1]; P='out/pilot/'
FR=240; rows=[]
for ch in (1,2,3):
    w=wave.open(f'{S}/ch0{ch}.wav'); a=np.abs(np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(int))
    n=len(a)//FR; pk=a[:n*FR].reshape(n,FR).max(1)
    tl=json.load(open(P+f'ch0{ch}.timeline.json')); tf=json.load(open(P+f'final/ch0{ch}.timeline.json'))
    off=tf[0]['start']-tl[0]['start']
    starts=np.array([x['start'] for x in tl])
    k=0
    while k<n:
        if pk[k]>=40: k+=1; continue
        j=k
        while j<n and pk[j]<40: j+=1
        z=(j-k)/100
        if 0.38<=z<=0.62:
            c=j
            while c<n and pk[c]<500: c+=1
            v=c
            while v<n and pk[v]>=500 or (v<n and pk[v:v+8].max()>=500): v+=1   # burst: voice until ≥80ms quiet
            t=c/100
            if np.abs(starts-(t-0.25)).min()>0.35:
                i=int(np.searchsorted(starts,t,'right'))-1
                seg=tl[i]; nxt=tl[i+1] if i+1<len(tl) else None
                b=k
                while b>0 and pk[b-1]<500: b-=1
                rows.append(dict(ch=ch,final=round(t+off,2),zero=z,nat=round((k-b+c-j)/100,2),voice=round((v-c)/100,2),
                    to_next=round((nxt['start']-t),2) if nxt else None, kind=seg['kind'],who=seg['who'],text=seg['text'],
                    nxt=nxt['who'] if nxt else '', zs=k*FR, ze=j*FR, ve=v*FR))
        k=j
json.dump(rows,open(S+'/bugs3.json','w'),ensure_ascii=False,indent=1)
for r in rows:
    m,s=divmod(r['final'],60)
    print(f"{r['ch']}장 {int(m)}:{s:04.1f} 0무음{r['zero']:.2f} 원래{r['nat']:.2f} 뒤소리{r['voice']:.2f} 다음줄까지{r['to_next']} {r['who']}→{r['nxt']} …{r['text'][-24:]}")
print(len(rows))
