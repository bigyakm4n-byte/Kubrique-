#!/bin/sh
# zoom.sh VX VY SCALE OUT.png [bg]  - renders mark.svg scaled, centred on viewBox point (VX,VY)
DIR="$(cd "$(dirname "$0")" && pwd)"; VX=$1; VY=$2; SC=$3; OUT=$4; BG=${5:-#0d0e13}
SIZE=$((512*SC)); LEFT=$((300-VX*SC)); TOP=$((300-VY*SC))
printf '<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:%s;overflow:hidden}img{position:absolute;left:%dpx;top:%dpx;width:%dpx;height:%dpx}</style></head><body><img src="mark.svg"></body></html>' "$BG" $LEFT $TOP $SIZE $SIZE > "$DIR/zoom.html"
/opt/pw-browsers/chromium --headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size=600,600 --screenshot="$OUT" "file://$DIR/zoom.html" 2>/dev/null
