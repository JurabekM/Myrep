# Bosqichlar holati

| # | Bosqich | Holat | Sana |
|---|---------|-------|------|
| 0 | Skelet | ✅ tugadi | 2026-11-11 |
| 1 | Yadro | ⏳ reja tasdiqlanishi kutilmoqda | — |
| 2 | SDK va plagin yuklovchi | — | — |
| 3 | Shell | — | — |
| 4 | `files` | — | — |
| 5 | `hosting` | — | — |
| 6 | `iot` | — | — |
| 7 | `data` | — | — |
| 8 | `electronics` | — | — |
| 9 | `itops` | — | — |
| 10 | Yakun | — | — |

## 0-bosqich — Skelet

**Qilindi**

- Bitta `uv` loyihasi (`srv1`, Python 3.12), uch paket: `srv1_core`, `srv1_sdk`,
  `srv1_shell` (hozircha faqat `__init__.py` va `__version__`).
- `ruff` (E/W/F/I/UP/B/S/ASYNC/ANN/SIM/PTH/RUF), `pyright` (strict),
  `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`) sozlamalari.
- `tests/test_skeleton.py` — 13 test: import, versiya mosligi, Python 3.12,
  papka tuzilmasi, taqiqlangan bog'liqliklar qo'riqchisi.
- `CLAUDE.md` (loyiha prompti), `docs/`, `tools/README.md`, `.gitignore`.

**Tekshiruv natijasi (2026-11-11)**

- `uv run pytest` — 13 passed
- `uv run ruff check .` va `ruff format --check .` — toza
- `uv run pyright` — 0 xato

**O'lchangan RAM** (Working Set, `Get-Process`, bir marta o'lchangan)

| Jarayon | WS, MB | Private, MB |
|---------|--------|-------------|
| `python.exe` (3.12, uch paket import qilingan, bo'sh turibdi) | 10,0 | 6,0 |
| `python.exe` (venv ishga tushirgichi) | 4,0 | 0,8 |

Bu faqat bo'sh interpretator bazasi: yadro, Caddy va shell hali yo'q, shuning
uchun 350 MB chegarasiga nisbatan hech narsa isbotlanmagan. Chegara birinchi
marta 1-bosqichda (yadro), to'liq holda 5-bosqichda (Caddy bilan) o'lchanadi.

**Qilinmadi / ma'lum kamchiliklar**

- Stekdagi ish vaqti kutubxonalari (FastAPI, PyQt6, DuckDB va h.k.) hali
  o'rnatilmagan — har biri o'z bosqichida qo'shiladi.
- `git init` bajarilmadi: papka allaqachon git repozitoriy (worktree) edi.
- CI yo'q (so'ralmagan).
- `tools/` bo'sh: binarlar 5, 6, 8, 10-bosqichlarda kerak bo'ladi.
