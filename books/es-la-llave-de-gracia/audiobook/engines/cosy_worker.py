"""CosyVoice 3 작업자: 표준입력 JSON 한 줄 → wav 파일 → 표준출력 JSON 한 줄. CosyVoice venv로 실행.
작업: {"voice","text","ref","ref_text","instruct"(없으면 zero-shot),"seed","out"}. 출력은 24 kHz 모노 16비트.
- 맥 GPU(MPS) 사용, 보코더(hift)만 CPU(COSY_HIFT_CPU). 보코더까지 GPU면 음색이 바뀐다(닮음 0.91→0.65, 11-13).
- 기준 녹음은 10초 안팎(voicebox/ref/short). 27초 기준은 생성마다 2–5배 느렸다.
- 목소리마다 기준 처리 결과를 한 번 만들어 재사용(add_zero_shot_spk)."""
import json, os, sys, time
os.environ.setdefault('COSY_MPS', '1'); os.environ.setdefault('COSY_HIFT_CPU', '1'); os.environ.setdefault('PYTORCH_ENABLE_MPS_FALLBACK', '1')
HOME = os.environ.get('COSY_HOME', os.path.expanduser('~/Developer/tts-lab/CosyVoice'))
sys.path[:0] = [HOME, f'{HOME}/third_party/Matcha-TTS']
os.chdir(HOME)
_out = sys.stdout; sys.stdout = sys.stderr          # 라이브러리 출력은 로그로
import gc
import torch, torchaudio
sys.modules['wetext'] = None    # 11-14: 뜰 때마다 modelscope 접속(403)하던 것 막기. 결과는 같다
from cosyvoice.cli.cosyvoice import AutoModel
from cosyvoice.utils.common import set_all_random_seed
m = AutoModel(model_dir='pretrained_models/Fun-CosyVoice3-0.5B')
P = 'You are a helpful assistant.'
spk = set()
def reply(d):
    _out.write(json.dumps(d) + '\n'); _out.flush()
reply({'ready': True, 'device': str(m.model.device)})
for line in sys.stdin:
    j = json.loads(line); t = time.time()
    try:
        sid = f"{j['voice']}|{j['ref']}"
        if sid not in spk:
            m.add_zero_shot_spk(f"{P}<|endofprompt|>{j['ref_text']}", j['ref'], sid); spk.add(sid)
        set_all_random_seed(int(j.get('seed', 7)))
        if j.get('instruct'):
            g = m.inference_instruct2(j['text'], f"{P} {j['instruct']}<|endofprompt|>", '', zero_shot_spk_id=sid, stream=False)
        else:
            g = m.inference_zero_shot(j['text'], '', '', zero_shot_spk_id=sid, stream=False)
        w = torch.cat([x['tts_speech'] for x in g], dim=1).cpu()
        w = torchaudio.functional.resample(w, m.sample_rate, 24000)
        pk = float(w.abs().max())
        if pk > 0.89:
            w = w * (0.89 / pk)                # 정수로 바꿀 때 찢어지지 않게(11-13)
        torchaudio.save(j['out'], w, 24000, encoding='PCM_S', bits_per_sample=16)
        del g, w
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()                # 11-14: 작업자가 18 GB까지 불었다
        reply({'ok': True, 'sec': round(time.time() - t, 1)})
    except Exception as e:
        reply({'ok': False, 'err': repr(e)[:300]})
