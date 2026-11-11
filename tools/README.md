# tools/

Tashqi binarlar shu yerga qo'yiladi va **gitga kirmaydi** (`.gitignore`).

| Fayl | Kerak bo'lgan bosqich | Vazifa | Sinalgan versiya |
|------|----------------------|--------|------------------|
| `caddy.exe` | 5 (`hosting`) | reverse proxy, admin API `127.0.0.1:2019` | 2.11.9 |
| `mosquitto/` | 6 (`iot`) | MQTT broker | sinalmagan (quyiga qarang) |
| `avrdude/` | 8 (`electronics`) | AVR (Arduino) proshivkasi | 8.3 |
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

## avrdude

Rasmiy manba: <https://github.com/avrdudes/avrdude/releases> →
`avrdude-v<versiya>-windows-x64.zip`. Arxivdan `avrdude.exe` va `avrdude.conf`
ni `tools/avrdude/` ga chiqaring (`.pdb` kerak emas). SHA-256 ni reliz
sahifasidagi qiymat bilan solishtiring:

```powershell
(Get-FileHash avrdude-v8.3-windows-x64.zip -Algorithm SHA256).Hash.ToLower()
# 8.3: 8630c7d8bb9682a1685aaa9ad42550ae1131c9d13528f0d20975368ba615e9b0
```

Boshqa joy: `SRV1_AVRDUDE_EXE`. `esptool` alohida yuklanmaydi — u Python
paketi (`uv sync` o'rnatadi).

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
