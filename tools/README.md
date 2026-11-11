# tools/

Tashqi binarlar shu yerga qo'yiladi va **gitga kirmaydi** (`.gitignore`).

| Fayl | Kerak bo'lgan bosqich | Vazifa | Sinalgan versiya |
|------|----------------------|--------|------------------|
| `caddy.exe` | 5 (`hosting`) | reverse proxy, admin API `127.0.0.1:2019` | 2.11.9 |
| `mosquitto/` | 6 (`iot`) | MQTT broker | sinalmagan (quyiga qarang) |
| `avrdude.exe` | 8 (`electronics`) | AVR proshivka | — |
| `nssm.exe` | 10 | Windows xizmati | — |
| `cloudflared.exe` | 10 | tunnel | — |

## Caddy

Rasmiy manba: <https://github.com/caddyserver/caddy/releases> →
`caddy_<versiya>_windows_amd64.zip`. Arxivdan `caddy.exe` ni shu papkaga
chiqaring. Yuklagandan keyin SHA-512 yig'indisini relizdagi
`caddy_<versiya>_checksums.txt` bilan solishtiring:

```powershell
(Get-FileHash caddy_2.11.9_windows_amd64.zip -Algorithm SHA512).Hash.ToLower()
```

Boshqa joydagi Caddy'dan foydalanish: `SRV1_CADDY_EXE` muhit o'zgaruvchisi.

## Mosquitto

Rasmiy manba: <https://mosquitto.org/download/> (Windows x64 o'rnatuvchisi).
Ikki yo'ldan biri:

- o'rnatuvchini ishga tushiring — plagin `C:\Program Files\mosquitto\mosquitto.exe`
  ni o'zi topadi (Mosquitto'ning Windows xizmatini yoqmang: brokerni plagin boshqaradi);
- yoki `mosquitto.exe` va yonidagi DLL'larni `tools/mosquitto/` ga nusxalang.

Boshqa joy: `SRV1_MOSQUITTO_EXE`. 6-bosqich yozilgan paytda `mosquitto.org`
ishlab chiqish mashinasidan ochilmadi, shuning uchun plagin haqiqiy Mosquitto
bilan sinalmagan. Mosquitto paydo bo'lgach `uv run pytest tests/test_iot_plugin.py`
ni qayta yugurtiring va panelda `Broker: running` ko'rinishini tekshiring.
