import sys,re,collections; sys.path.insert(0,'.')
import voicebox_book as V
c=collections.Counter(); chs=collections.defaultdict(set)
for ch in range(1,31):
    for s in V.A.segments(ch):
        if s['who']!='narr': continue
        sp=V.spoken(s,ch)
        for a,b in zip(sp,sp[1:]):
            if a[0]=='es' and b[0]=='ko' and V.glued(s,ch,a[1],b[1]):
                w=a[1].strip().rstrip('.,;:'); c[w]+=1; chs[w].add(ch)
for w,n in sorted(c.items(), key=lambda x:(min(chs[x[0]]),-x[1])):
    print(f'{w}\t{n}\t{",".join(map(str,sorted(chs[w])))}')
