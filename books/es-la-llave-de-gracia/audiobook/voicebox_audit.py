"""Voicebox 장 음성 2차 검수: 받아쓰기 일치(1차, voicebox_book.py) 다음에 소리 자체를 본다(11-12).

  python3 audiobook/voicebox_audit.py 1 2 3

토막마다(out_vb/chNN.qa.tsv에 적힌 캐시 wav) 낱말 시각을 받아써서 본다.
- 앞 무음: 첫 낱말 전 0.5초 넘게 비었으면(자막이 먼저 뜬다)
- 뒤 꼬리: 마지막 낱말 뒤 1.0초 넘게 소리가 남았으면(웅얼거림·잡음 의심)
- 속 끊김: 낱말 사이가 1.5초 넘게 벌어졌으면
- 속도: 한국어 서술 토막의 글자/초가 장 중앙값의 0.7–1.4배 밖이면
- 찢어짐: 진폭 32000 넘는 표본
장 파일: 음량(LUFS)·최대(dBTP).
결과: out_vb/chNN.audit.tsv와 화면 요약. 문제 없음이면 '이상 없음'.
"""
import csv
import hashlib
import re
import statistics
import subprocess
import sys
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voicebox_book as V  # noqa: E402

A = V.A


def wav_of(row, pid):
    if row.get('key'):
        return V.CACHE / f'{row["key"]}.wav'
    v = row['voice']
    key = hashlib.sha1(f'{pid[v]}|{row["lang"]}|{row["seed"]}|{row["mode"]}|{row["text"]}'.encode()).hexdigest()[:16]
    return V.CACHE / f'{key}.wav'


def loud(path):
    out = subprocess.run(['ffmpeg', '-i', str(path), '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    i = re.findall(r'I:\s+(-?[\d.]+) LUFS', out)[-1]
    p = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', out)[-1]
    return float(i), float(p)


def audit(ch, tag=''):
    pid = V.profiles()
    rows = list(csv.DictReader(open(V.OUTV / f'ch{ch:02d}{tag}.qa.tsv'), delimiter='\t'))
    probs, rates = [], []
    for r in rows:
        w = wav_of(r, pid)
        if not w.exists():
            probs.append((r, '캐시 wav 없음'))
            continue
        pcm = V.pcm_of(w)
        sec = len(pcm) / 2 / A.RATE
        a = array('h', pcm)
        if any(abs(x) >= 32000 for x in a):
            probs.append((r, '찢어짐(진폭 한계)'))
        ws = V.hear(pcm, r['lang'], words=True)
        if not ws:
            probs.append((r, '낱말 없음'))
            continue
        if ws[0]['start'] > 0.5:
            probs.append((r, f'앞 무음 {ws[0]["start"]:.1f}초'))
        if sec - ws[-1]['end'] > 1.0:
            probs.append((r, f'뒤 꼬리 {sec - ws[-1]["end"]:.1f}초'))
        gaps = [b['start'] - a_['end'] for a_, b in zip(ws, ws[1:])]
        if gaps and max(gaps) > 1.5:
            probs.append((r, f'속 끊김 {max(gaps):.1f}초'))
        if r['lang'] == 'ko' and r['voice'].startswith('narr') and len(r['text']) >= 30:
            rates.append((r, len(r['text']) / max(0.1, ws[-1]['end'] - ws[0]['start'])))
        print(f'  {ch}장 {r["seg"]}-{r["piece"]}', end='\r', flush=True)
    if rates:
        med = statistics.median(x for _, x in rates)
        for r, x in rates:
            if not 0.7 <= x / med <= 1.4:
                probs.append((r, f'속도 {x / med:.2f}배(중앙값 {med:.1f}자/초)'))
    m4a = V.OUTV / f'ch{ch:02d}{tag}.m4a'
    lufs, peak = loud(m4a)
    if not (-20 <= lufs <= -18) or peak > -3.0:
        probs.append(({'seg': '-', 'piece': '-', 'who': '', 'text': m4a.name}, f'음량 {lufs} LUFS / 최대 {peak} dBTP'))
    with open(V.OUTV / f'ch{ch:02d}{tag}.audit.tsv', 'w') as f:
        f.write('seg\tpiece\twho\tproblem\ttext\n')
        for r, why in probs:
            f.write(f'{r["seg"]}\t{r["piece"]}\t{r["who"]}\t{why}\t{r["text"][:80]}\n')
    print(f'\n{ch}장: 토막 {len(rows)}개, 음량 {lufs} LUFS, 최대 {peak} dBTP, 문제 {len(probs)}건')
    for r, why in probs:
        print(f'   {r["seg"]}-{r["piece"]} {r["who"]:8s} {why}  {r["text"][:50]}')
    return probs


if __name__ == '__main__':
    tag = next((a[6:] for a in sys.argv[1:] if a.startswith('--tag=')), '')
    for c in (int(a) for a in sys.argv[1:] if not a.startswith('--')):
        audit(c, tag)
