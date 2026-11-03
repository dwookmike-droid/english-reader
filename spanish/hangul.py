"""스페인어(스페인 본토 발음) 철자 → 한글 발음 표기.

이 책의 표기법을 따른다.
  *굵게*  = 강세 음절      _밑줄_ = 혀를 무는 th 소리 (z, ce, ci)
  l 사이에 모음이 있으면 앞 글자에 ㄹ 받침을 더한다 (hola → 올라, maleta → 말레타)
  끝소리 s, r, d 등은 '스, 르, 드'로 따로 적는다

    >>> to_hangul('gracias')
    '*그라*_시_아스'
"""
import re
import unicodedata

CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
JUNG = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'
JONG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ',
        'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']


def syl(c, v, j=''):
    return chr(0xAC00 + (CHO.index(c) * 21 + JUNG.index(v)) * 28 + JONG.index(j))


def add_final(ch, j):
    """완성된 글자에 받침을 더한다(받침이 없을 때만)."""
    code = ord(ch) - 0xAC00
    if code < 0 or code % 28:
        return None
    return chr(ord(ch) + JONG.index(j))


VOW = {'a': 'ㅏ', 'e': 'ㅔ', 'i': 'ㅣ', 'o': 'ㅗ', 'u': 'ㅜ'}
YVOW = {'a': 'ㅑ', 'e': 'ㅖ', 'i': 'ㅣ', 'o': 'ㅛ', 'u': 'ㅠ'}
ONSET = {'b': 'ㅂ', 'd': 'ㄷ', 'f': 'ㅍ', 'g': 'ㄱ', 'x': 'ㅎ', 'k': 'ㅋ', 'l': 'ㄹ', 'm': 'ㅁ',
         'n': 'ㄴ', 'p': 'ㅍ', 'r': 'ㄹ', 's': 'ㅅ', 't': 'ㅌ', 'T': 'ㅅ', 'C': 'ㅊ'}
# 받침으로 붙는 소리와, 따로 '스·르' 같은 글자가 되는 소리
FINAL_JONG = {'n': 'ㄴ', 'l': 'ㄹ', 'm': 'ㅁ', 'k': 'ㄱ', 'g': 'ㄱ'}
FINAL_SYL = {'s': '스', 'r': '르', 'd': '드', 'T': '스', 'x': '흐', 't': '트', 'b': '브',
             'p': '프', 'f': '프', 'C': '치'}


def phonemes(word):
    """철자를 소리 단위로: 모음 aeiou, 반모음 j(이)·w(우), 자음은 한 글자 기호."""
    w = word.lower()
    out, i = [], 0
    while i < len(w):
        c, n = w[i], w[i + 1:i + 2]
        n2 = w[i + 2:i + 3]
        if c in 'áéíóú':
            out.append(c); i += 1; continue
        if c in 'aeiou':
            out.append(c); i += 1; continue
        if c == 'ü':
            out.append('u'); i += 1; continue
        if c == 'h':
            i += 1; continue
        if c == 'c' and n == 'h':
            out.append('C'); i += 2; continue
        if c == 'l' and n == 'l':
            out.append('Y'); i += 2; continue
        if c == 'r' and n == 'r':
            out.append('r'); i += 2; continue
        if c == 'q' and n == 'u':
            out.append('k'); i += 2; continue
        if c == 'g' and n == 'u' and n2 in ('e', 'i', 'é', 'í'):
            out.append('g'); i += 2; continue
        if c == 'c':
            out.append('T' if n in 'eiéí' and n else 'k'); i += 1; continue
        if c == 'z':
            out.append('T'); i += 1; continue
        if c == 'g':
            out.append('x' if n in 'eiéí' and n else 'g'); i += 1; continue
        if c == 'j':
            out.append('x'); i += 1; continue
        if c == 'ñ':
            out.append('N'); i += 1; continue
        if c == 'v':
            out.append('b'); i += 1; continue
        if c == 'x':
            out += ['k', 's']; i += 1; continue
        if c == 'y':
            # 모음 앞이면 자음 y, 아니면 모음 i
            out.append('Y' if n and n in 'aeiouáéíóú' else 'i'); i += 1; continue
        if c == 'w':
            out.append('u'); i += 1; continue
        if c in 'bdfklmnprst':
            out.append(c); i += 1; continue
        i += 1  # 그 밖의 글자(하이픈 등)는 건너뜀
    return out


def syllables(ph):
    """스페인어 음절로 나눈다. 각 음절 = (첫소리들, 모음핵(반모음 포함), 끝소리들)."""
    isv = lambda x: x in 'aeiouáéíóú'
    strong = lambda x: x in 'aeoáéóíú'   # 강세 받은 i/u는 강모음 취급
    # 모음 덩어리를 음절핵으로 묶는다: 약모음(i,u)+강모음, 강모음+약모음은 한 음절
    nuclei, i = [], 0
    while i < len(ph):
        if isv(ph[i]):
            j = i + 1
            while j < len(ph) and isv(ph[j]) and not (strong(ph[j - 1]) and strong(ph[j])):
                j += 1
            nuclei.append((i, j))
            i = j
        else:
            i += 1
    if not nuclei:                      # 모음이 없는 약어(Sr. 등)
        return []
    sylls = []
    prev_end = 0
    for k, (a, b) in enumerate(nuclei):
        cons = ph[prev_end:a]
        if k == 0:
            onset, coda_prev = cons, []
        else:
            # 자음 사이: 하나면 뒤로, 둘 이상이면 마지막 하나(또는 pl, br 같은 묶음)를 뒤로
            if len(cons) <= 1:
                coda_prev, onset = [], cons
            elif len(cons) >= 2 and cons[-1] in 'lr' and cons[-2] in 'bdfgkpt':
                coda_prev, onset = cons[:-2], cons[-2:]
            else:
                coda_prev, onset = cons[:-1], cons[-1:]
            sylls[-1][2].extend(coda_prev)
        sylls.append([list(onset), ph[a:b], []])
        prev_end = b
    sylls[-1][2].extend(ph[prev_end:])
    return sylls


def stress_index(word, sylls):
    for k, s in enumerate(sylls):
        if any(c in 'áéíóú' for c in s[1]):
            return k
    if len(sylls) == 1:
        return 0
    last = word.lower().rstrip()[-1:]
    return len(sylls) - 2 if last in 'aeiouns' else len(sylls) - 1


def plain(v):
    return unicodedata.normalize('NFD', v)[0]


def render(onset, nucleus, coda):
    """한 음절을 한글 글자들로. 반환: (글자 목록, th가 걸린 글자 위치들)."""
    chars, th = [], set()
    vs = [plain(v) for v in nucleus]
    # 첫소리
    cons = list(onset)
    lead = None
    while len(cons) > 1:                          # 자음 묶음의 앞쪽은 '으'를 붙여 따로
        c = cons.pop(0)
        if c == 'T': th.add(len(chars))
        # pl, bl, cl, fl, gl 은 '플라, 블라'처럼 ㄹ 받침을 더한다
        chars.append(syl(ONSET.get(c, 'ㅇ'), 'ㅡ', 'ㄹ' if cons[0] == 'l' else ''))
    if cons:
        lead = cons[0]
    # 모음핵: 반모음 i/u는 앞 모음과 이어 붙이거나 '이·우'로 따로
    first = True
    k = 0
    while k < len(vs):
        v = vs[k]
        nxt = vs[k + 1] if k + 1 < len(vs) else None
        c0 = 'ㅇ'
        jung = VOW[v]
        if first and lead:
            if lead == 'Y':
                jung = YVOW[v]
            elif lead == 'N':
                c0, jung = 'ㄴ', YVOW[v] if v != 'i' else 'ㅣ'
            else:
                c0 = ONSET[lead]
                if lead == 'T': th.add(len(chars))
        chars.append(syl(c0, jung))
        first = False
        k += 1
    # 끝소리
    for c in coda:
        if c in FINAL_JONG:
            got = add_final(chars[-1], FINAL_JONG[c])
            if got:
                chars[-1] = got
                continue
        if c == 'T': th.add(len(chars))
        chars.append(FINAL_SYL.get(c) or syl(ONSET.get(c, 'ㅇ'), 'ㅡ'))
    return chars, th


def to_hangul(word):
    """단어 하나 → 책의 발음 표기 문자열."""
    ph = phonemes(word)
    if not ph:
        return ''
    sy = syllables(ph)
    if not sy:
        return word
    st = stress_index(word, sy)
    parts = []
    for k, (o, n, c) in enumerate(sy):
        chars, th = render(o, n, c)
        parts.append([chars, th, k == st])
    # l 앞의 모음으로 끝난 음절에 ㄹ 받침 (hola → 올라)
    for k in range(1, len(parts)):
        if sy[k][0][:1] == ['l'] and not sy[k - 1][2]:
            got = add_final(parts[k - 1][0][-1], 'ㄹ')
            if got:
                parts[k - 1][0][-1] = got
    # n 다음에 g·k 소리가 오면 ㅇ 받침 (tengo → 텡고, cinco → 싱코)
    for k in range(len(parts) - 1):
        if sy[k][2][-1:] == ['n'] and sy[k + 1][0][:1] and sy[k + 1][0][0] in ('g', 'k', 'x'):
            last = parts[k][0][-1]
            code = ord(last) - 0xAC00
            if code >= 0 and code % 28 == JONG.index('ㄴ'):
                parts[k][0][-1] = chr(ord(last) - JONG.index('ㄴ') + JONG.index('ㅇ'))
    out = []
    for chars, th, stressed in parts:
        s = ''.join(f'_{ch}_' if i in th else ch for i, ch in enumerate(chars))
        out.append(f'*{s}*' if stressed and len(sy) > 1 else s)
    return ''.join(out)


WORDRE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ](?:[A-Za-zÀ-ÖØ-öø-ÿ\-]*[A-Za-zÀ-ÖØ-öø-ÿ])?")


if __name__ == '__main__':
    import sys
    for w in sys.argv[1:] or ['hola', 'gracias', 'maleta', 'vale', 'calle', 'llave', 'señora', 'mañana',
                              'cuántos', 'quiero', 'cincuenta', 'doscientos', 'reloj', 'cerrajería',
                              'bienvenida', 'aeropuerto', 'taxi', 'abuela', 'guapa', 'veinte', 'euros',
                              'melocotones', 'diez', 'plaza', 'castellano', 'hoy', 'muy', 'pasaporte']:
        print(f'{w:14s} {to_hangul(w)}')
