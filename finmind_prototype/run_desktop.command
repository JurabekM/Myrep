#!/bin/sh
# FinTx desktop interfeysi (macOS). Finder'da ikki marta bosib ishga tushirish mumkin.
# Birinchi ishga tushirishda alohida virtual muhit yaratiladi va PySide6 o'rnatiladi.
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
    .venv/bin/python -m pip install --quiet --upgrade pip
    .venv/bin/python -m pip install --quiet -r requirements-gui.txt
fi
exec .venv/bin/python -m fintx.gui "$@"
