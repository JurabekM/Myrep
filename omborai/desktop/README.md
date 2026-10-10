# OmborAI — Desktop (kassa)

Python 3.12 + PySide6. Backend API (`../backend`) bilan ishlaydi.

## Ishga tushirish

```bash
cd desktop
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

export OMBORAI_API_URL=http://127.0.0.1:8000
# ixtiyoriy: tarmoq printeri (ESC/POS, 9100-port)
export OMBORAI_PRINTER_HOST=192.168.1.50
python -m omborai_desktop
```

## Klaviatura

| Tugma | Amal |
|---|---|
| F2 | Qidiruv maydoniga o'tish |
| Enter | Shtrix-kod yoki nomni qidirish (skaner shu yerga yozadi) |
| F12 | To'lash |
| Del | Tanlangan qatorni o'chirish |
| Esc | Qidiruvni tozalash |

## Testlar

```bash
pytest -q
ruff check . && mypy omborai_desktop --ignore-missing-imports
```

Testlar `QT_QPA_PLATFORM=offscreen` rejimida ishlaydi (monitor kerak emas).

## Arxitektura

- `omborai_desktop/api.py` — backend klienti (token yangilash, xatolarni `ApiError` ga aylantirish)
- `omborai_desktop/cart.py` — savat (Qt'siz). Narx yuborilmaydi, server o'zi hisoblaydi.
- `omborai_desktop/receipt.py`, `escpos.py` — chek matni va termal printer baytlari
- `omborai_desktop/ui/` — PySide6 oynalar. API chaqiruvlari fon oqimida (`tasks.py`), UI qotmaydi.

## Muhim qoidalar

- Savdo `id`si klientda yaratiladi. Aloqa uzilsa, F12 bilan **o'sha** savdo qayta yuboriladi: dublikat chek bo'lmaydi.
- Server rad etgan savdo (masalan, qoldiq yetmasa) savatda qoladi, tuzatib qayta yuborish mumkin.
- Offline rejim (mahalliy SQLite navbati) — Faza 4 da qo'shiladi.
