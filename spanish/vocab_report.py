#!/usr/bin/env python3
"""원고 단어 측정 — IMPROVE.md의 수치를 다시 뽑는다. 원고와 단어표는 읽기만 한다.

  python3 vocab_report.py low    # 책 전체에 3번 미만 나온 새 단어(n): (처음 장, 단어, 전체, 그 뒤 장들, 장별)
  python3 vocab_report.py wfam   # 장별 낯선 낱말 비율(앞 장들에서 3번 미만 본 형태, 이름 제외, 가르친 n 단어는 익숙한 것으로)
  python3 vocab_report.py hard   # 16·17·24장에서 한 번만 나오고 처음 보는 낱말
  python3 vocab_report.py fam    # 단어표 항목 단위 낯선 비율(x 항목이 구라서 실제보다 높게 나온다)
  python3 vocab_report.py cov    # 장별 항목 종류 비율(가르친 n / x / c / p / f)
  python3 vocab_report.py x      # 자주 나오는 x 항목
"""
import sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build
entries, forms = build.load_vocab()
inl = build.Inline(forms, entries)
per = collections.defaultdict(collections.Counter)   # key -> ch -> n
tok = collections.defaultdict(collections.Counter)   # ch -> category -> n
class Uses(dict):
    """build.Inline.uses 대신 — 장별 노출 횟수(구 안에 든 n 단어 포함)를 함께 적는다."""
    def __setitem__(self, k, v):
        expo[k][inl.ch] += v - self.get(k, 0)
        super().__setitem__(k, v)
expo = collections.defaultdict(collections.Counter)  # key -> ch -> n (반복 점검용)
inl.uses = Uses()
orig = inl.word
def word(text, key, first=False, pron=None):
    ch = inl.ch
    per[key][ch] += 1
    e = entries.get(key, {})
    t = e.get('t')
    if t == 'n':
        cat = 'taught' if e['c'] <= ch else 'n_future'
    else:
        cat = t or '?'
    tok[ch][cat] += len(text.split())
    return orig(text, key, first, pron)
inl.word = word
chs = [build.parse_chapter(p, inl) for p in sorted(build.SRC.glob('ch*.txt'))]
mode = sys.argv[1]
if mode == 'cov':
    for ch in range(1, 31):
        c = tok[ch]; tot = sum(c.values())
        print(f"{ch:2d} tot{tot:5d} taught {c['taught']/tot:5.1%} x {c['x']/tot:5.1%} c {c['c']/tot:4.1%} p {c['p']/tot:4.1%} f {c['f']/tot:4.1%} fut {c['n_future']/tot:4.1%}")
elif mode == 'low':
    rows = []
    for e in entries.values():
        if e['t'] != 'n': continue
        k = e['k']; tot = sum(expo[k].values())
        if tot < 3:
            later = sum(v for c, v in expo[k].items() if c > e['c'])
            rows.append((e['c'], k, tot, later, dict(expo[k])))
    for r in sorted(rows): print(r)
    print(len(rows))
elif mode == 'x':
    # 가르치지 않은(x) 말 중 자주 나오는 것
    rows = sorted(((sum(per[k].values()), k, min(per[k]) if per[k] else 0) for k, e in entries.items() if e['t']=='x'), reverse=True)
    for r in rows[:60]: print(r)
    print('x 1회만:', sum(1 for r in rows if r[0]==1), '/', len(rows))
if mode == 'fam':
    seen = collections.Counter()
    for ch in range(1, 31):
        newtypes, unf, tot = set(), 0, 0
        for k in per:
            v = per[k].get(ch, 0)
            if not v: continue
            e = entries.get(k, {}); t = e.get('t')
            w = len(k.split()) * v
            tot += w
            if t == 'x' and seen[k] < 3:
                unf += w
                if seen[k] == 0: newtypes.add(k)
        for k in per:
            seen[k] += per[k].get(ch, 0)
        tn = sum(1 for e in entries.values() if e['t']=='n' and e['c']==ch)
        print(f"{ch:2d} 스페인어 {tot:5d}  낯선(x,앞서 3회 미만) {unf/tot:5.1%}  새 x 종류 {len(newtypes):4d}  가르친 새 단어 {tn:3d}")
if mode in ('wfam', 'hard'):
    # 단어 단위: 앞 장들에서 3번 미만 본 낱말 = 낯선 낱말 (가르친 n 단어는 익숙한 것으로)
    words = collections.defaultdict(collections.Counter)  # ch -> word -> n
    taughtw = {}
    for e in entries.values():
        if e['t']=='n':
            for w in e['k'].lower().split(): taughtw.setdefault(w, e['c'])
    for k in per:
        e = entries.get(k, {})
        if e.get('t') == 'p': continue
        for ch, v in per[k].items():
            for w in k.lower().split(): words[ch][w] += v
    seen = collections.Counter()
    hard = collections.defaultdict(list)
    for ch in range(1, 31):
        tot = sum(words[ch].values()); unf = 0
        for w, v in words[ch].items():
            if seen[w] < 3 and not (w in taughtw and taughtw[w] <= ch):
                unf += v
                if seen[w] == 0 and v == 1: hard[ch].append(w)
        seen.update(words[ch])
        if mode == 'wfam':
            print(f"{ch:2d} 낱말 {tot:5d}  낯선 {unf/tot:5.1%}  (한 번 나오고 처음 보는 낱말 {len(hard[ch])})")
    if mode == 'hard':
        for ch in (16,17,24): print(ch, ' '.join(sorted(hard[ch])))
