#!/usr/bin/env bash
# Zarbxona v3 — kerakli paketlar o'rnatilgan Python'ni o'zi topadi.
# Tartib: $ZARBXONA_PYTHON → ./.venv → python3.13/3.12/python3/python.
# aetherq_core ham bor muhit topilsa — o'sha afzal (onlayn topshirish uchun).
set -u
cd "$(dirname "$0")"

TEKSHIR='import PySide6, cryptography, paho.mqtt; from cryptography.hazmat.primitives.asymmetric import mldsa'
tanlangan=""
zaxira=""

sina() {
    local py="$1"
    command -v "$py" >/dev/null 2>&1 || [ -x "$py" ] || return 0
    "$py" -c "$TEKSHIR" >/dev/null 2>&1 || return 0
    [ -z "$zaxira" ] && zaxira="$py"
    if [ -z "$tanlangan" ] && "$py" -c "import aetherq_core" >/dev/null 2>&1; then
        tanlangan="$py"
    fi
}

if [ -n "${ZARBXONA_PYTHON:-}" ]; then
    tanlangan="$ZARBXONA_PYTHON"
else
    for py in ./.venv/bin/python python3.13 python3.12 python3 python; do
        sina "$py"
    done
    [ -z "$tanlangan" ] && tanlangan="$zaxira"
fi

if [ -z "$tanlangan" ]; then
    echo "Kerakli paketlar o'rnatilgan Python topilmadi." >&2
    echo "O'rnating:  python3 -m pip install -r requirements.txt" >&2
    exit 1
fi
if ! "$tanlangan" -c "import aetherq_core" >/dev/null 2>&1; then
    echo "eslatma: $tanlangan da aetherq_core yo'q — onlayn topshirish o'chiq, fayl orqali ishlaydi" >&2
fi
exec "$tanlangan" run.py "$@"
