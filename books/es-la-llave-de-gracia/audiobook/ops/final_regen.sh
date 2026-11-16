#!/bin/bash
# 11-14 최종 재생성(스튜디오 기준 녹음, 전수조사 반영). 장마다 완료 표시 → 재부팅 뒤 이어서. 1·2·3장 먼저.
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH
D=/Users/dongwookkang/Developer/tts-lab/final; cd "/Users/dongwookkang/Developer/english-reader/.claude/worktrees/audiobook-0749d8/books/es-la-llave-de-gracia/audiobook"
[ -f $D/ALL_DONE ] && exit 0
echo "=== 시작 $(date '+%m-%d %H:%M')"
for pass in 1 2; do
  for c in $(seq 1 30); do
    n=$(printf %02d $c); [ -f $D/done_$n ] && continue
    echo "=== $c장 생성 $(date '+%m-%d %H:%M') ($pass회차)"
    /opt/homebrew/bin/python3.14 voicebox_book.py $c --pace --narr narr1 --engine-narr cosy --engine-dlg index --tag _v4 || { echo "FAIL build $c"; continue; }
    /opt/homebrew/bin/python3.14 voicebox_audit.py $c --tag=_v4 || echo "FAIL audit $c"
    /opt/homebrew/bin/python3.14 pilot_mix.py $c --vb || echo "FAIL mix $c"
    if [ $c -le 9 ]; then (cd video && /opt/homebrew/bin/python3.14 render.py $c --src ../out/vb_final --out out/vb) || echo "FAIL render $c"; fi
    touch $D/done_$n
    echo "=== $c장 끝 $(date '+%m-%d %H:%M')"
  done
done
[ $(ls $D/done_* 2>/dev/null | wc -l) -eq 30 ] && touch $D/ALL_DONE && echo ALL_DONE
launchctl bootout gui/$(id -u)/com.gracia.final
