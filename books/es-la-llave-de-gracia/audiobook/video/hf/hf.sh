#!/bin/sh
# HyperFrames CLI를 이 폴더에 설치한 판으로, 사용 기록 전송·자동 업데이트 없이, 설치된 Chrome으로 돌린다.
HERE="$(cd "$(dirname "$0")" && pwd)"
export HYPERFRAMES_NO_TELEMETRY=1 DO_NOT_TRACK=1 HYPERFRAMES_NO_UPDATE_CHECK=1 HYPERFRAMES_NO_AUTO_INSTALL=1
export HYPERFRAMES_BROWSER_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
exec "$HERE/node_modules/.bin/hyperframes" "$@"
