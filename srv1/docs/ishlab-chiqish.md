# Ishlab chiqish muhiti

Talab: Windows 10 x64, `uv` (Python 3.12 ni `uv` o'zi topadi yoki o'rnatadi).

## Buyruqlar

Hammasi repozitoriy ildizidan:

```powershell
uv sync                 # .venv yaratadi, dev bog'liqliklarni o'rnatadi
uv run pytest           # testlar
uv run ruff check .     # lint
uv run ruff format .    # formatlash
uv run pyright          # tip tekshiruvi (strict)

$env:SRV1_DATA_DIR = "$PWD\.srv1-data"
uv run python -m srv1_shell  # shell; yadro ishlamayotgan bo'lsa, o'zi oynasiz ko'taradi
uv run python -m srv1_core   # yadroni qo'lda, jurnali konsolda (shell'dan oldin, boshqa oynada)
```

Shell ko'targan yadro oyna yopilgach ham ishlayveradi: to'xtatish — oynadagi «Serverni
to'xtatish» tugmasi yoki `powershell -File install\stop-core.ps1` (`SRV1_DATA_DIR` bir xil
bo'lsin). Diqqat: `SRV1_DATA_DIR` berilmasa shell haqiqiy `%PROGRAMDATA%\SRV_1` bilan ishlaydi.

Testlarni **PowerShell'dan** yuriting. Git Bash ostida
`test_service_stop.py` yiqiladi: bola jarayon «Ctrl+C ni e'tiborsiz qoldirish»
bayrog'ini meros oladi va yadro to'xtash signalini olmaydi (kod xatosi emas).

Reliz o'rnatuvchisi (`release\SRV_1-Setup-<versiya>.exe`; Inno Setup 6 kerak):

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build.ps1
powershell -ExecutionPolicy Bypass -File packaging\sign.ps1    # o'zi imzolangan sertifikat bilan imzo
```

Tafsiloti: [reliz.md](reliz.md).

O'rnatish skriptlari (`install/`) va Windows xizmati: [ornatish.md](ornatish.md).
Foydalanuvchi qo'llanmasi: [qollanma.md](qollanma.md).

## Paketlar joylashuvi

Bitta `uv` loyihasi (`srv1`), uch paket turli papkalarda:

| Paket | Yo'l | Vazifa |
|-------|------|--------|
| `srv1_core` | `core/srv1_core/` | yadro |
| `srv1_sdk` | `sdk/srv1_sdk/` | plagin API |
| `srv1_shell` | `shell/srv1_shell/` | PyQt6 klient |

`hatchling` ularni bitta editable o'rnatmaga yig'adi
(`[tool.hatch.build.targets.wheel].packages`).

## Qoidalarni avtomatik qo'riqlash

- `ruff` `S602`/`S604`/`S605` — `shell=True` va shunga o'xshash chaqiruvlar.
- `ruff` `S104` — `0.0.0.0` ga bog'lanish.
- `ruff` `ANN` — type hint yo'q funksiya.
- `tests/test_skeleton.py::test_no_forbidden_dependencies` — `pyproject.toml`
  ga taqiqlangan kutubxona (pandas, celery, redis, aiomqtt va h.k.) qo'shilsa
  yiqiladi.

## Bog'liqlik qo'shish

Faqat `CLAUDE.md` dagi stek ro'yxatidan, kerak bo'lgan bosqichda:
`uv add <paket>`. Ro'yxatda yo'q kutubxona — avval loyiha egasidan so'raladi.
