#!/bin/bash
# 11-17 Mike "한 번에 고치기": 3–30장 조사 붙은 낱말 한글 표기(--hangul) → 검수 → 믹스 → 영상 → 스포티파이 폴더 → 유튜브 교체
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH
cd "$(dirname "$0")/.."; P=/opt/homebrew/bin/python3.14; B=$HOME/Developer/tts-lab/backup_v4_1117
mkdir -p $B
for c in $(seq ${1:-3} ${2:-30}); do n=$(printf %02d $c)
  echo "=== $c장 $(date '+%m-%d %H:%M')"
  [ -f $B/ch${n}_v4.qa.tsv ] || cp -p out_vb/ch${n}_v4.qa.tsv out_vb/ch${n}_v4.timeline.json out/vb_final/ch${n}.mp3 out/vb_final/ch${n}.timeline.json $B/ 2>/dev/null
  $P voicebox_book.py $c --pace --narr narr1 --engine-narr cosy --engine-dlg index --hangul --tag _v4 | tail -1 || { echo "FAIL build $c"; continue; }
  $P voicebox_audit.py $c --tag=_v4 >/dev/null 2>&1 || echo "FAIL audit $c"
  $P pilot_mix.py $c --vb >/dev/null || { echo "FAIL mix $c"; continue; }
  (cd video && $P render.py $c --src ../out/vb_final --out out/vb >/dev/null 2>&1) || { echo "FAIL render $c"; continue; }
  $P post_chapter.py $c | grep -v "^$" | tail -2
  $P tools/yt_swap.py $c 2>&1 | tail -1 || echo "FAIL yt $c"
done
echo ALL_HANGUL_DONE
