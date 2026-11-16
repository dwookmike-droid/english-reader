"""IndexTTS-2.5(MLX) 작업자: 표준입력 JSON 한 줄 → wav → 표준출력 JSON 한 줄. mlx-indextts2 venv로 실행.
작업: {"text","ref","lang","emotion"(dict 또는 이름, 없으면 참조 목소리 그대로),"alpha","seed","out"}. 출력 24 kHz 모노."""
import json, os, sys, time, subprocess, tempfile, wave
import numpy as np
HOME = os.environ.get('INDEX_HOME', os.path.expanduser('~/Developer/tts-lab/mlx-indextts2'))
os.chdir(HOME)
from mlx_indextts.runtime import GenerateOptions, TTSRuntime
import mlx.core as mx
# 11-14: 작업자 하나가 30 GB까지 불어 맥이 멈췄다(Jetsam). 상한 12 GB, 캐시 2 GB, 작업마다 비운다
mx.set_memory_limit(12 * 1024**3)
mx.set_cache_limit(2 * 1024**3)
rt = TTSRuntime()
print(json.dumps({'ready': True}), flush=True)
for line in sys.stdin:
    j = json.loads(line); t = time.time()
    try:
        tmp = tempfile.mktemp(suffix='.wav')
        o = GenerateOptions(language=j.get('lang', 'es'), seed=int(j.get('seed', 7)), temperature=0.8,
                            emotion=j.get('emotion') or None, emo_alpha=float(j.get('alpha', 0.6)),
                            denoise_ref_audio=False, denoise_emotion_ref_audio=False, max_tokens=1500)
        sys.stdout = sys.stderr                     # 라이브러리 출력이 응답 줄을 흐리지 않게
        rt.generate(j['text'], j['ref'], tmp, profile='v25', options=o)
        sys.stdout = sys.__stdout__
        f32 = tmp + '.f32'
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', tmp, '-ar', '24000', '-ac', '1', '-f', 'f32le', f32], check=True)
        w = np.fromfile(f32, dtype=np.float32)
        pk = float(np.abs(w).max()) if len(w) else 0.0
        if pk > 0.89:
            w = w * (0.89 / pk)                       # 정수로 바꿀 때 찢어지지 않게(11-13)
        with wave.open(j['out'], 'wb') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(24000)
            f.writeframes((np.clip(w, -1, 1) * 32767).astype('<i2').tobytes())
        os.remove(tmp); os.remove(f32)
        mx.clear_cache()
        print(json.dumps({'ok': True, 'sec': round(time.time() - t, 1)}), flush=True)
    except Exception as e:
        sys.stdout = sys.__stdout__
        print(json.dumps({'ok': False, 'err': repr(e)[:300]}), flush=True)
