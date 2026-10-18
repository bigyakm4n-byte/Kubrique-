#!/bin/sh
# Render preview.html -> review.png with headless Chromium (Linux path; see task notes for other OSes)
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-$DIR/review.png}"
# light-background mono variant: same geometry, pale colour
sed 's/fill="#1a1710"/fill="#f3e9cf"/' "$DIR/mark-mono.svg" > "$DIR/mark-mono-light.svg"
/opt/pw-browsers/chromium --headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size=1000,560 --screenshot="$OUT" "file://$DIR/preview.html" 2>/dev/null
ls -la "$OUT"
