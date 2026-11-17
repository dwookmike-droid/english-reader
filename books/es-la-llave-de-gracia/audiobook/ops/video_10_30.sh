#!/bin/bash
# 10–30장: 영상 렌더 → post_chapter(스포티파이 폴더 갱신 + 유튜브 예약 업로드)
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH
cd "$(dirname "$0")/.."
for c in $(seq 10 30); do
  echo "=== $c장 $(date '+%m-%d %H:%M')"
  (cd video && /opt/homebrew/bin/python3.14 render.py $c --src ../out/vb_final --out out/vb) || { echo "FAIL render $c"; continue; }
  /opt/homebrew/bin/python3.14 post_chapter.py $c || echo "FAIL post $c"
done
echo ALL_VIDEO_DONE
