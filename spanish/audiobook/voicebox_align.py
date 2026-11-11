"""ref/<이름>_NN.txt(받아쓰기)를 실제 대본 글로 바꾼다(11-11). Whisper가 낱말을 틀린 곳(예: 한국어 '녹이 슨'→'노깃은')을
reference_text에서 없앤다. 조각 경계는 받아쓰기와 대본을 글자 단위로 맞춰(difflib) 대본 위의 자리로 옮긴다.

  python3 audiobook/voicebox_align.py          # el_texts.json에 있는 인물 전부 + marti_text.txt
"""
import difflib
import json
import unicodedata
from pathlib import Path

VB = Path(__file__).resolve().parent / 'voicebox'
REF = VB / 'ref'


def norm(s):
    """(정규화 글자열, 각 글자의 원문 위치)"""
    out, pos = [], []
    for i, ch in enumerate(s):
        c = unicodedata.normalize('NFKD', ch.lower())
        c = ''.join(x for x in c if x.isalnum())
        for x in c:
            out.append(x); pos.append(i)
    return ''.join(out), pos


def align(name, script):
    parts = sorted(REF.glob(f'{name}_[0-9][0-9].txt'))
    if len(parts) < 2:
        if parts:
            parts[0].write_text(' '.join(script.split()) + '\n')
        return
    heard = [p.read_text().strip() for p in parts]
    h, _ = norm(' '.join(heard))
    s, spos = norm(script)
    sm = difflib.SequenceMatcher(None, h, s, autojunk=False)
    blocks = sm.get_matching_blocks()

    def to_script(i):                       # 받아쓰기 정규화 위치 → 대본 정규화 위치
        for a, b, n in blocks:
            if a <= i < a + n:
                return b + (i - a)
            if a > i:
                return b
        return len(s)
    cuts, acc = [], 0
    for t in heard[:-1]:
        acc += len(norm(t)[0])
        j = to_script(acc)
        k = spos[j] if j < len(spos) else len(script)
        while k > 0 and not script[k - 1].isspace():      # 낱말 중간이면 앞 공백까지
            k -= 1
        cuts.append(k)
    bounds = [0] + cuts + [len(script)]
    for p, a, b in zip(parts, bounds, bounds[1:]):
        p.write_text(' '.join(script[a:b].split()) + '\n')


def main():
    texts = json.loads((VB / 'el_texts.json').read_text())
    texts['marti'] = {'text': (VB / 'marti_text.txt').read_text()}
    for n, v in texts.items():
        align(n, v['text'])
        print(n, [len(p.read_text()) for p in sorted(REF.glob(f'{n}_[0-9][0-9].txt'))])


if __name__ == '__main__':
    main()
