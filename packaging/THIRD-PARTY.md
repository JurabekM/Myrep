# Uchinchi tomon dasturlari

SRV_1 o'rnatuvchisi quyidagi tayyor dasturlarni o'zgartirmasdan o'z ichiga oladi.

| Qism | Joyi | Litsenziya | Manba |
|------|------|------------|-------|
| Python 3.12 (python-build-standalone) | `python\` | PSF License (`python\LICENSE.txt`) | <https://github.com/astral-sh/python-build-standalone> |
| Python kutubxonalari | `python\Lib\site-packages\` | har birining litsenziyasi o'z `*.dist-info` papkasida | PyPI |
| Caddy | `tools\caddy.exe` | Apache-2.0 (`Apache-2.0.txt`) | <https://github.com/caddyserver/caddy> |
| NSSM 2.24 | `tools\nssm.exe` | jamoat mulki (public domain) | <https://nssm.cc> |

Alohida e'tibor:

- **PyQt6** GPL v3 litsenziyasida tarqatiladi (tijoriy litsenziya Riverbank Computing'dan
  alohida olinadi). SRV_1 shell'i PyQt6'dan foydalanadi, shuning uchun bu o'rnatuvchini
  tarqatganda GPL v3 shartlari amal qiladi.
- **Qt 6** kutubxonalari (PyQt6 ichida) LGPL v3 da.
- **scapy** GPL v2 da. Uni faqat tarmoq kuzatuvining ushlash jarayoni ishlatadi
  (`plugins\monitor\netcap\worker.py`, alohida jarayon); yadro va shell uni yuklamaydi.

O'rnatuvchiga kirmaydi va kerak bo'lsa alohida qo'yiladi (`tools\README.md`):
cloudflared, Mosquitto, avrdude, **Npcap** (tarmoq kuzatuvi uchun; litsenziyasi uni boshqa
o'rnatuvchiga qo'shib tarqatishga ruxsat bermaydi — <https://npcap.com/#download> dan
alohida o'rnatiladi).
