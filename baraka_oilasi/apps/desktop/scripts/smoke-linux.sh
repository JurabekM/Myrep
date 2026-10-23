#!/bin/bash
# Haqiqiy ilovani Xvfb + xdotool bilan tekshirish (Linux): sozlash → tiklash kodi → daromad → ulush → bosh sahifa → Ctrl+L.
# Talab: xvfb, imagemagick, xdotool; debug build. Ishlatish: scripts/smoke-linux.sh [chiqish_papkasi] [ilova]
SP=${1:-/tmp/baraka-smoke}; APP=${2:-$(dirname "$0")/../../../target/debug/baraka-desktop}
mkdir -p "$SP/e2e"
export DISPLAY=:99 BARAKA_INSECURE_DEV_SECRET=1 XDG_DATA_HOME=$SP/e2e/data WEBKIT_DISABLE_COMPOSITING_MODE=1
rm -rf $SP/e2e/data; Xvfb :99 -screen 0 1360x860x24 >/dev/null 2>&1 & XVFB=$!
sleep 2
$APP > $SP/e2e/app.log 2>&1 & PID=$!
sleep 10
import -window root $SP/e2e/1-setup.png
WIN=$(xdotool search --name Baraka | head -1); xdotool windowactivate $WIN 2>/dev/null; sleep 1
# Tab tartibi: uz, uz-Cyrl, ru, oila nomi, ism, PIN, PIN takror, 3 ta katakcha, Boshlash
xdotool key Tab Tab Tab Tab; xdotool type --delay 30 "Bekzodlar"
xdotool key Tab; xdotool type --delay 30 "Bekzod"
xdotool key Tab; xdotool type --delay 30 "246810"
xdotool key Tab; xdotool type --delay 30 "246810"
xdotool key Tab Tab space; xdotool key Return
sleep 4
import -window root $SP/e2e/2-recovery.png
xdotool key Return; sleep 2
xdotool key ctrl+n; sleep 1; xdotool type --delay 30 "8 000 000"; xdotool key Tab; xdotool type --delay 30 "Taksi"; xdotool key Return
sleep 3
import -window root $SP/e2e/3-income.png
xdotool key Return; sleep 2
import -window root $SP/e2e/4-home.png
xdotool key ctrl+l; sleep 2
import -window root $SP/e2e/5-locked.png
kill $PID $XVFB 2>/dev/null
ls $SP/e2e/data/*/ 2>/dev/null
echo done
