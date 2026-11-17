#!/bin/bash
# 최종 생성에서 장이 끝날 때마다(done_NN) post_chapter.py를 한 번씩 돌린다. 재부팅 뒤에도 이어서.
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH
cd "/Users/dongwookkang/Developer/english-reader/.claude/worktrees/audiobook-0749d8/books/es-la-llave-de-gracia/audiobook"; D=/Users/dongwookkang/Developer/tts-lab/final
while true; do
  for c in $(seq 1 30); do n=$(printf %02d $c)
    [ -f $D/done_$n ] && [ ! -f $D/post_$n ] && { echo "=== $c장 마무리 $(date '+%m-%d %H:%M')"; /opt/homebrew/bin/python3.14 post_chapter.py $c && touch $D/post_$n; }
  done
  [ -f $D/ALL_DONE ] && [ $(ls $D/post_* 2>/dev/null | wc -l) -ge 30 ] && break
  sleep 120
done
launchctl bootout gui/$(id -u)/com.gracia.post
