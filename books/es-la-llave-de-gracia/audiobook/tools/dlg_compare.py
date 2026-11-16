"""윤하 대사 6줄, 네 판의 소리 비교(11-16)."""
import sys, wave, warnings, numpy as np
warnings.filterwarnings('ignore')
sys.path.insert(0,'.')
import voicebox_book as V
R=24000
F={'Z_지금(스페인어기준)':'out/샘플_윤하_3장/1_윤하대사_지금.wav','K_IndexTTS한국어기준':'out/샘플_윤하_3장/2_윤하대사_한국억양_IndexTTS.wav',
   'A_Cosy한글':'out/시험본_v5/비교/윤하_한국어스피커/A_한글표기.wav','B_Cosy스페인어':'out/시험본_v5/비교/윤하_한국어스피커/B_스페인어글자.wav'}
def load(p):
    with wave.open(p) as w: return np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768
def split(a):
    fr=int(R*0.02); e=np.array([np.abs(a[i:i+fr]).max() for i in range(0,len(a)-fr,fr)]); s=e<0.003
    segs=[];start=None;n=0
    for i,x in enumerate(s):
        if not x:
            if start is None: start=i
            n=0
        else:
            n+=1
            if start is not None and n>=35: segs.append((start*fr,(i-n+1)*fr)); start=None
    if start is not None: segs.append((start*fr,len(a)))
    return [a[x:y] for x,y in segs]
def f0s(a):
    fr,hop=int(R*0.04),int(R*0.01);out=[]
    for i in range(0,len(a)-fr,hop):
        x=a[i:i+fr]
        if np.sqrt((x**2).mean())<0.02: out.append(np.nan);continue
        x=x-x.mean();c=np.correlate(x,x,'full')[fr-1:];lo,hi=R//450,R//75;k=lo+int(np.argmax(c[lo:hi]))
        out.append(R/k if c[k]>0.45*c[0] else np.nan)
    return np.array(out)
import whisper; W=V.whisper_model()
for name,p in F.items():
    parts=split(load(p)); print(f'\n## {name}: 줄 {len(parts)}개')
    for x in parts[:6]:
        f=f0s(x); v=f[~np.isnan(f)]
        if len(v)<5: print('  (짧음)'); continue
        st=12*np.log2(v/np.median(v)); rng=np.percentile(st,90)-np.percentile(st,10)
        tail=f[~np.isnan(f)][-8:]; head=f[~np.isnan(f)][:8]
        end=12*np.log2(np.median(tail)/np.median(v))
        voiced=np.mean(~np.isnan(f))
        mel=whisper.log_mel_spectrogram(whisper.pad_or_trim(x),n_mels=W.dims.n_mels).to(W.device)
        _,pr=W.detect_language(mel)
        print(f'  {len(x)/R:4.1f}초  높이 {np.median(v):5.0f}Hz  폭 {rng:4.1f}반음  끝 {end:+5.1f}반음  유성 {voiced:.2f}  언어 es {pr["es"]:.2f} ko {pr["ko"]:.2f} en {pr["en"]:.2f}')
