import math, pathlib
F = pathlib.Path('/home/user/english-reader/spanish/.fonts')
fonts = ''.join(f'<link rel="stylesheet" href="{(F/f).as_uri()}">' for f in (
 'fontsource-gowun-batang-5.1.0/400.css','fontsource-gowun-batang-5.1.0/700.css',
 'fontsource-eb-garamond-5.1.0/400.css','fontsource-eb-garamond-5.1.0/400-italic.css',
 'fontsource-eb-garamond-5.1.0/500.css','fontsource-eb-garamond-5.1.0/600.css','fontsource-eb-garamond-5.1.0/500-italic.css',
 'fontsource-noto-sans-kr-5.1.0/400.css','fontsource-noto-sans-kr-5.1.0/700.css'))

def flower(r=10, c='currentColor', hole=True, sw=0):
    p = ''.join(f'<ellipse cx="0" cy="{-r*.55}" rx="{r*.32}" ry="{r*.52}" transform="rotate({i*72})"/>' for i in range(5))
    h = f'<circle r="{r*.17}" fill="var(--paper)"/>' if hole else ''
    return f'<g fill="{c}">{p}</g>{h}'

def key(color='currentColor', w=2.2):
    # bow = five-petal flower outline + shaft + bit
    pet = ''.join(f'<ellipse cx="0" cy="-6.2" rx="3.6" ry="5.8" transform="rotate({i*72})"/>' for i in range(5))
    return (f'<g fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round">'
            f'<g transform="translate(16 20)">{pet}<circle r="2.2"/></g>'
            f'<path d="M28 20h80M90 20v9M98 20v6M106 20v10"/></g>')

def dial(R=40, h=3, m=10, roman=True, accent='var(--acc)', ink='var(--ink)', label=''):
    out = [f'<circle r="{R}" fill="none" stroke="{ink}" stroke-width=".6"/>',
           f'<circle r="{R-3}" fill="none" stroke="{ink}" stroke-width=".25"/>']
    for i in range(60):
        a = math.radians(i*6)
        l = 3 if i % 5 == 0 else 1.4
        x1, y1 = (R-3)*math.sin(a), -(R-3)*math.cos(a)
        x2, y2 = (R-3-l)*math.sin(a), -(R-3-l)*math.cos(a)
        out.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{ink}" stroke-width="{.6 if i%5==0 else .3}"/>')
    if roman:
        R2 = R-11
        for i, s in enumerate('XII I II III IV V VI VII VIII IX X XI'.split()):
            a = math.radians(i*30)
            out.append(f'<text x="{R2*math.sin(a):.2f}" y="{-R2*math.cos(a)+2.2:.2f}" font-size="6" text-anchor="middle" fill="{ink}" font-family="EB Garamond">{s}</text>')
    ah = math.radians((h % 12 + m/60)*30); am = math.radians(m*6)
    out.append(f'<line x1="0" y1="0" x2="{18*math.sin(ah):.2f}" y2="{-18*math.cos(ah):.2f}" stroke="{accent}" stroke-width="1.4" stroke-linecap="round"/>')
    out.append(f'<line x1="0" y1="0" x2="{27*math.sin(am):.2f}" y2="{-27*math.cos(am):.2f}" stroke="{accent}" stroke-width=".8" stroke-linecap="round"/>')
    out.append(f'<circle r="1.6" fill="{accent}"/>')
    return ''.join(out)

CSS = '''
body{margin:0;background:#cfcac0;font-family:"Gowun Batang";padding:10mm;}
.row{display:flex;gap:7mm;align-items:flex-start;margin-bottom:9mm}
.lab{width:52mm;font-family:"Noto Sans KR";font-size:9pt;line-height:1.6;color:#222}
.lab h1{font-size:15pt;margin:0 0 2mm}.lab .sw{display:flex;gap:1.5mm;margin:2mm 0}.lab .sw i{width:9mm;height:9mm;border-radius:1mm;display:block;border:.3pt solid #0003}
.pg{width:128mm;height:188mm;background:var(--paper);color:var(--ink);position:relative;overflow:hidden;box-shadow:0 1mm 3mm #0003;flex:none}
.cov{background:var(--cov);color:var(--covink)}
.c{position:absolute;left:0;right:0;text-align:center}
.it{font-family:"EB Garamond";font-style:italic}
.gb{font-family:"EB Garamond"}
.sans{font-family:"Noto Sans KR"}
.det{width:128mm;height:188mm;background:var(--paper);color:var(--ink);padding:16mm 14mm;box-sizing:border-box;font-size:10pt;line-height:1.72;flex:none;box-shadow:0 1mm 3mm #0003;position:relative}
.det p{margin:0;text-indent:1em;text-align:justify}
.rh{position:absolute;top:9mm;font:italic 7.8pt "EB Garamond";color:var(--mute)}
.fo{position:absolute;bottom:9mm;font:8pt "EB Garamond";color:var(--mute)}
'''

def page(name, vars_, cover, opener, detail, desc, swatches):
    sw = ''.join(f'<i style="background:{c}"></i>' for c in swatches)
    return f'''<div class="row" style="{vars_}"><div class="lab"><h1>{name}</h1><div class="sw">{sw}</div>{desc}</div>
<div class="pg cov">{cover}</div><div class="pg">{opener}</div><div class="det">{detail}</div></div>'''

BODY = '''<p>Marc puso las dos llaves sobre la mesa. Eran iguales: la misma flor, el mismo peso. 마르크는 한참 동안 아무 말도 하지 않았다.</p>
<p>—No es una llave de puerta —dijo por fin—. Es una llave de reloj.</p>'''
LETTER = '<p style="text-indent:0" class="it">Querida Sun-rye:<br>El domingo, a las once, en Santa María del Mar.</p>'
ADDR = '<p style="text-indent:0" class="gb">M.<br>Carrer del Rellotger, 7<br>Gràcia · Barcelona</p>'

rows = []
# ── A. 시계공의 공방 ─────────────────────────────
A_vars = '--paper:#f6f1e6;--ink:#1f1d1a;--acc:#9a7432;--mute:#8a8070;--cov:#1f2a2e;--covink:#efe6d2'
A_cover = f'''
<svg class="c" style="top:24mm;left:24mm;width:80mm" viewBox="-42 -42 84 84">{dial(40, 3, 10, accent="#c9a35a", ink="#efe6d2")}</svg>
<div class="c it" style="top:112mm;font-size:30pt;line-height:1.02">La llave<br>de Gràcia</div>
<div class="c" style="top:142mm;font-size:10.5pt;letter-spacing:.3em">그라시아의 열쇠</div>
<div class="c sans" style="top:150mm;font-size:6.6pt;letter-spacing:.2em;color:#c9a35a">스페인어로 읽는 소설</div>
<svg class="c" style="top:170mm;left:52mm;width:24mm;color:#c9a35a" viewBox="0 0 120 40">{key(w=2.6)}</svg>'''
A_open = f'''
<svg class="c" style="top:30mm;left:39mm;width:50mm" viewBox="-42 -42 84 84">{dial(40,3,10)}</svg>
<div class="c gb" style="top:88mm;font-size:8pt;letter-spacing:.35em;color:var(--acc)">CAPÍTULO V</div>
<div class="c it" style="top:95mm;font-size:34pt">¿Qué hora es?</div>
<div class="c sans" style="top:113mm;font-size:7.4pt;color:var(--mute)">[케 <b style="color:var(--ink)">오</b>라 에스]</div>
<div class="c sans" style="top:150mm;font-size:6.6pt;color:var(--mute)">2026년 8월 10일 월요일</div>'''
A_det = f'''<div class="rh" style="right:14mm">5 · ¿Qué hora es?</div>{BODY}
<p style="text-align:center;margin:4mm 0;text-indent:0"><svg width="20mm" viewBox="-30 -5 60 10"><line x1="-28" x2="-7" stroke="var(--acc)" stroke-width=".5"/><line x1="7" x2="28" stroke="var(--acc)" stroke-width=".5"/><circle r="3.6" fill="none" stroke="var(--acc)" stroke-width=".6"/><line y2="-2.6" stroke="var(--acc)" stroke-width=".6"/><line x2="2" y2=".6" stroke="var(--acc)" stroke-width=".6"/></svg></p>
<p>Al día siguiente, a las diez, Yuna volvió al taller.</p>
<div style="margin:4mm 0 4mm 5mm;padding-left:4mm;border-left:1.2pt solid var(--acc)">{LETTER}</div>
<div style="margin:4mm auto;width:60%;padding:2mm 3mm;border:.5pt solid var(--ink);outline:.3pt solid var(--ink);outline-offset:.8mm">{ADDR}</div>
<div class="fo" style="right:14mm">47</div>'''
rows.append(page('A. 시계공의 공방', A_vars, A_cover, A_open, A_det,
 '<p>마르티의 괘종시계에서 출발. 짙은 청록 밤색 표지에 놋쇠 금빛 시계판, 바늘은 <b>3시 10분</b>(배가 떠난 시각)에 멈춰 있다.</p><p>장 표제지마다 같은 시계판이 있고, 28장 「Las tres y diez」부터 바늘이 다시 움직인다. 장 번호는 로마 숫자(시계판과 같은 글자).</p><p>본문 색: 검정 + 놋쇠색 1도.</p>',
 ['#1f2a2e', '#9a7432', '#f6f1e6', '#1f1d1a']))

# ── B. 그라시아의 타일 ─────────────────────────────
B_vars = '--paper:#faf6ee;--ink:#1d1d1b;--acc:#b5532f;--acc2:#2f5b4a;--mute:#857d72;--cov:#b5532f;--covink:#fbf3e6'
def tile(s=20, a='#fbf3e6', b='#2f5b4a', bg='#b5532f'):
    return (f'<rect x="{-s}" y="{-s}" width="{2*s}" height="{2*s}" fill="{bg}"/>'
            + ''.join(f'<path d="M{-s} {-s} q{s} {s*.4} {2*s} 0" fill="none" stroke="{a}" stroke-width=".5" transform="rotate({k*90})"/>' for k in range(4))
            + f'<g transform="scale(1)">{flower(s*.62, a, hole=False)}</g><circle r="{s*.13}" fill="{b}"/>'
            + ''.join(f'<g transform="rotate({k*90}) translate({-s} {-s})">{flower(s*.3, b, hole=False)}</g>' for k in range(4)))
pattern = ''.join(f'<g transform="translate({x*40} {y*40})">{tile()}</g>' for x in range(4) for y in range(6))
B_cover = f'''<svg style="position:absolute;inset:0" width="128mm" height="188mm" viewBox="-20 -20 128 188" preserveAspectRatio="xMidYMid slice">{pattern}</svg>
<div style="position:absolute;left:14mm;right:14mm;top:56mm;height:76mm;background:#fbf3e6;color:#1d1d1b;border:.6pt solid #2f5b4a;outline:.6pt solid #fbf3e6;outline-offset:1.4mm"></div>
<div class="c it" style="top:66mm;font-size:29pt;line-height:1.02;color:#1d1d1b">La llave<br>de Gràcia</div>
<div class="c" style="top:96mm;font-size:10.5pt;letter-spacing:.3em;color:#1d1d1b">그라시아의 열쇠</div>
<div class="c sans" style="top:104mm;font-size:6.6pt;letter-spacing:.2em;color:#b5532f">스페인어로 읽는 소설</div>
<svg class="c" style="top:114mm;left:54mm;width:20mm;color:#2f5b4a" viewBox="0 0 120 40">{key(w=2.6)}</svg>'''
B_open = f'''
<svg class="c" style="top:34mm;left:44mm;width:40mm" viewBox="-21 -21 42 42">{tile(20,'#faf6ee','#2f5b4a','#b5532f')}<text y="3.6" font-size="11" text-anchor="middle" fill="#faf6ee" font-family="EB Garamond" font-weight="500" style="display:none">5</text></svg>
<div class="c gb" style="top:84mm;font-size:8pt;letter-spacing:.35em;color:var(--acc)">CAPÍTULO 5</div>
<div class="c it" style="top:91mm;font-size:34pt">¿Qué hora es?</div>
<div class="c sans" style="top:109mm;font-size:7.4pt;color:var(--mute)">[케 <b style="color:var(--ink)">오</b>라 에스]</div>'''
B_det = f'''<div class="rh" style="right:14mm">5 · ¿Qué hora es?</div>{BODY}
<p style="text-align:center;margin:4mm 0;text-indent:0;color:var(--acc)"><svg width="5mm" viewBox="-11 -11 22 22">{flower(10,'var(--acc)')}</svg></p>
<p>Al día siguiente, a las diez, Yuna volvió al taller.</p>
<div style="margin:4mm 0;padding:3mm 4mm;background:#f1e7d6">{LETTER}</div>
<div style="margin:4mm auto;width:62%;padding:2mm 3mm;background:var(--acc2);color:#faf6ee;border-radius:1mm">{ADDR}</div>
<div class="fo" style="right:14mm">47</div>'''
rows.append(page('B. 그라시아의 타일', B_vars, B_cover, B_open, B_det,
 '<p>바르셀로나 보도의 꽃무늬 시멘트 타일(panot)과 모데르니스메 색. 테라코타 + 짙은 초록, 열쇠 손잡이의 <b>다섯 꽃잎 꽃</b>이 타일 무늬가 된다.</p><p>표지는 타일을 깐 바닥 위에 흰 명판. 장 표제지는 타일 한 장, 장면 바뀜은 작은 꽃 하나.</p><p>가장 밝고 경쾌하다. 본문 색: 검정 + 테라코타 1도(초록은 표지에만).</p>',
 ['#b5532f', '#2f5b4a', '#faf6ee', '#f1e7d6']))

# ── C. 편지와 소인 ─────────────────────────────
C_vars = '--paper:#f7f4ec;--ink:#1c2230;--acc:#24477a;--mute:#7d8291;--cov:#efe9da;--covink:#1c2230'
def postmark(top='GRÀCIA · BARCELONA', mid='10 AGO', bot='2026', n='5', R=24, c='var(--acc)'):
    return (f'<circle r="{R}" fill="none" stroke="{c}" stroke-width=".7"/><circle r="{R-7}" fill="none" stroke="{c}" stroke-width=".4"/>'
            f'<path id="tp" d="M{-(R-4.6)} 0 A{R-4.6} {R-4.6} 0 0 1 {R-4.6} 0" fill="none"/>'
            f'<text font-size="3.6" letter-spacing=".5" fill="{c}" font-family="EB Garamond"><textPath href="#tp" startOffset="50%" text-anchor="middle">{top}</textPath></text>'
            f'<text y="-4" font-size="4.2" text-anchor="middle" fill="{c}" font-family="EB Garamond">{mid}</text>'
            f'<text y="9" font-size="4.2" text-anchor="middle" fill="{c}" font-family="EB Garamond">{bot}</text>'
            f'<text y="4" font-size="9" text-anchor="middle" fill="{c}" font-family="EB Garamond" font-weight="500" font-style="italic">{n}</text>'
            + ''.join(f'<path d="M{R+3} {y} q8 -3 16 0 t16 0 t16 0" fill="none" stroke="{c}" stroke-width=".5"/>' for y in (-8,-3,2,7)))
stripe = ''.join(f'<rect x="{i*8}" y="0" width="4" height="6" fill="{"#b23a33" if i%2 else "#24477a"}" transform="skewX(-40)"/>' for i in range(40))
C_cover = f'''<svg style="position:absolute;left:0;top:0" width="140mm" height="4mm" viewBox="0 0 280 6">{stripe}</svg>
<svg style="position:absolute;left:0;bottom:0" width="140mm" height="4mm" viewBox="0 0 280 6">{stripe}</svg>
<div style="position:absolute;right:12mm;top:14mm;width:22mm;height:27mm;background:#fff;padding:1.6mm;box-sizing:border-box;border:1.4mm dotted #efe9da;outline:.3pt solid #c9c0ad">
<div style="background:#2f5b4a;height:100%;color:#f7f4ec;display:flex;align-items:center;justify-content:center"><svg width="12mm" viewBox="-11 -11 22 22">{flower(10,'#f7f4ec',hole=False)}<circle r="1.8" fill="#2f5b4a"/></svg></div></div>
<svg style="position:absolute;right:22mm;top:24mm;width:40mm" viewBox="-26 -26 80 52">{postmark(mid="3 MAR",bot="1978",n="✕")}</svg>
<div class="it" style="position:absolute;left:14mm;top:66mm;font-size:31pt;line-height:1.02;color:var(--acc)">La llave<br>de Gràcia</div>
<div style="position:absolute;left:14mm;top:96mm;font-size:10.5pt;letter-spacing:.3em">그라시아의 열쇠</div>
<div class="sans" style="position:absolute;left:14mm;top:104mm;font-size:6.6pt;letter-spacing:.2em;color:#7d8291">스페인어로 읽는 소설</div>
<div class="gb" style="position:absolute;left:44mm;top:132mm;font-size:11pt;line-height:1.55;border-top:.4pt solid #1c2230;padding-top:2mm;width:68mm">Sra. Park Sun-rye<br><span class="it">Carrer del Rellotger, 7</span><br>Gràcia · Barcelona</div>
'''
C_open = f'''
<svg class="c" style="top:32mm;left:34mm;width:60mm" viewBox="-26 -26 80 52">{postmark()}</svg>
<div class="c gb" style="top:84mm;font-size:8pt;letter-spacing:.35em;color:var(--acc)">CAPÍTULO 5</div>
<div class="c it" style="top:91mm;font-size:34pt;color:var(--acc)">¿Qué hora es?</div>
<div class="c sans" style="top:109mm;font-size:7.4pt;color:var(--mute)">[케 <b style="color:var(--ink)">오</b>라 에스]</div>'''
C_det = f'''<div class="rh" style="right:14mm">5 · ¿Qué hora es?</div>{BODY}
<p style="text-align:center;margin:4mm 0;text-indent:0"><svg width="22mm" viewBox="0 -4 60 8"><path d="M2 0 q4 -3 8 0 t8 0 t8 0 t8 0 t8 0 t8 0 t8 0" fill="none" stroke="var(--acc)" stroke-width=".6"/></svg></p>
<p>Al día siguiente, a las diez, Yuna volvió al taller.</p>
<div style="margin:4mm 2mm;padding:3mm 4mm;background:#fff;box-shadow:.4mm .6mm 0 #d9d2c2;transform:rotate(-.6deg);color:var(--acc)">{LETTER}</div>
<div style="margin:4mm auto;width:64%;padding:2mm 3mm;border:.4pt solid var(--ink);position:relative">{ADDR}<div style="position:absolute;right:2mm;top:2mm;width:7mm;height:8.5mm;border:.4pt dashed var(--acc)"></div></div>
<div class="fo" style="right:14mm">47</div>'''
rows.append(page('C. 편지와 소인', C_vars, C_cover, C_open, C_det,
 '<p>할머니의 상자 속 편지 열한 통에서 출발. 미색 봉투 같은 표지, 항공우편 띠, 다섯 꽃잎 우표, 1978년 소인, 받는 사람 박순례.</p><p>장 표제지는 소인 도장: 장 번호 + 그 장의 날짜(이야기 속 날짜표에서). 편지는 흰 편지지를 살짝 기울여 놓은 모양.</p><p>본문 색: 검정 + 파란 잉크 1도.</p>',
 ['#24477a', '#b23a33', '#2f5b4a', '#efe9da']))

html = f'<!DOCTYPE html><html><head><meta charset="utf-8">{fonts}<style>{CSS}</style></head><body>{"".join(rows)}</body></html>'
pathlib.Path(__file__).with_name('mock.html').write_text(html)
