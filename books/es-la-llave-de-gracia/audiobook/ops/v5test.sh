#!/bin/bash
# 11-16 3장 시험본(--v5). 본 음원(_v4, out/vb_final)은 건드리지 않는다.
cd "/Users/dongwookkang/Developer/english-reader/.claude/worktrees/audiobook-0749d8/books/es-la-llave-de-gracia/audiobook"
PY=/opt/homebrew/bin/python3.14
echo "=== 생성 $(date '+%m-%d %H:%M')"
/usr/bin/caffeinate -i $PY voicebox_book.py 3 --pace --narr narr1 --engine-narr cosy --engine-dlg index --v5 --tag _v5test || { echo "FAIL build"; exit 1; }
$PY voicebox_audit.py 3 --tag=_v5test || echo "FAIL audit"
$PY pilot_mix.py 3 --vb --tag _v5test --out out/시험본_v5 || echo "FAIL mix"
echo "=== 끝 $(date '+%m-%d %H:%M')"
