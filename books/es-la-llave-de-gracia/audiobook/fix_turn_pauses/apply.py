"""verified.json에서 조립 때 잘못 들어간 화자 전환 쉼(0.45초)을 '다' 뒤로 옮긴다. 전체 길이는 그대로."""
import json,wave,sys,numpy as np
S=sys.argv[1]; OUT=sys.argv[2]
INS=int(0.45*24000)
rows=[r for r in json.load(open(S+'/verified.json')) if r['score']>=0.75 and r['nat']+r['zero']-r['raw_gap']>=0.3]
log=[]
for ch in (1,2,3):
    w=wave.open(f'{S}/ch0{ch}.wav'); a=np.frombuffer(w.readframes(w.getnframes()),np.int16).copy()
    mine=sorted([r for r in rows if r['ch']==ch],key=lambda r:r['zs'],reverse=True)
    for r in mine:
        zs,ze,ve=r['zs'],r['ze'],r['ve']
        mid=(zs+ze)//2; c0=mid-INS//2
        # 다 뒤 쉼: ve부터 소리 전까지 중 가장 조용한 10ms 위치
        k=ve
        while k+240<len(a) and np.abs(a[k:k+240]).max()<500: k+=240
        gap=a[ve:k]
        if len(gap)>=480:
            fr=np.abs(gap[:len(gap)//240*240]).reshape(-1,240).max(1); p=ve+int(np.argmin(fr[:max(1,len(fr)-1)]))*240+120
        else:
            p=ve+len(gap)//2
        a=np.concatenate([a[:c0],a[c0+INS:p],np.zeros(INS,np.int16),a[p:]])
        log.append((ch,r['label'],r['text'][-30:]))
    with wave.open(f'{OUT}/ch0{ch}.wav','wb') as o:
        o.setnchannels(1);o.setsampwidth(2);o.setframerate(24000);o.writeframes(a.tobytes())
for x in sorted(log): print(*x,sep='\t')
print(len(log))
