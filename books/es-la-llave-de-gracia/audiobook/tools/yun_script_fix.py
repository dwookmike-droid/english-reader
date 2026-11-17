import sys,json,tempfile;sys.path.insert(0,'.')
from pathlib import Path
import voicebox_book as V
A=V.A; D=sys.argv[1]
R='voicebox/ref/idx'; MIX=str(Path.home()/'Developer/tts-lab/ref_yunmix.wav')
L=['Quiero… tomates.','No. Nada más. ¿Cuánto es?','Queso… por favor.','Doscientos gramos.','Me llamo Yunha. Soy coreana.','Marc… ¿Qué es esto?']
VAR={'S1_한국어목소리+스페인어말투':(f'{R}/narr_01.wav',f'{R}/yunha_01.wav',0.7),
     'S2_이어붙인기준':(MIX,None,0.6),
     'S3_이어붙인기준+스페인어말투':(MIX,f'{R}/yunha_01.wav',0.7)}
sil=b'\0\0'*int(A.RATE*0.8)
for name,(ref,emo,al) in VAR.items():
    out=[]
    for t in L:
        p=V.worker('index')
        with tempfile.TemporaryDirectory() as d:
            o=Path(d)/'o.wav'
            job=dict(voice='yunha',text=t,ref=str(Path(ref).resolve()),ref_text='',seed=7,out=str(o),lang='es',emotion=None,alpha=al,emo_ref=str(Path(emo).resolve()) if emo else None)
            p.stdin.write(json.dumps(job,ensure_ascii=False)+'\n');p.stdin.flush()
            r=V.readj(p,timeout=300)
            pcm=V.pcm_of(o) if r.get('ok') else b''
        if pcm:
            pcm=V.drop_tail_bursts(V.untail(pcm,'es')); pcm=A.trim(pcm)
        print(name,'|',t,'→',V.hear(pcm,'es') if pcm else 'FAIL',flush=True)
        out.append(V.fade(A.level(pcm)) if pcm else sil)
    V.save(f'{D}/{name}.wav',sil.join(out))
