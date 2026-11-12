# tools/

Tashqi binarlar shu yerga qo'yiladi va **gitga kirmaydi** (`.gitignore`).

| Fayl | Kerak bo'lgan bosqich | Vazifa | Sinalgan versiya |
|------|----------------------|--------|------------------|
| `caddy.exe` | 5 (`hosting`) | reverse proxy, admin API `127.0.0.1:2019` | 2.11.9 |
| `mosquitto/` | 6 (`iot`) | MQTT broker | sinalmagan (quyiga qarang) |
| `avrdude/` | 8 (`electronics`) | AVR (Arduino) proshivkasi | 8.3 |
| `nssm.exe` | 10 | Windows xizmati | 2.24 (64-bit) |
| `cloudflared.exe` | 10 (`hosting`) | internetga ochish (tunnel) | 2026.10.7 |

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

## NSSM

Rasmiy manba: <https://nssm.cc/download> → `nssm-2.24.zip` (oxirgi barqaror
reliz, 2014-yil; loyiha shundan beri yangilanmagan). Arxivdan
`win64\nssm.exe` ni shu papkaga chiqaring. Sahifada SHA-1 berilgan:

```powershell
(Get-FileHash nssm-2.24.zip -Algorithm SHA1).Hash.ToLower()
# be7b3577c6e3a280e5106a9e9db5b3775931cefc
(Get-FileHash nssm.exe -Algorithm SHA256).Hash.ToLower()   # win64\nssm.exe
# f689ee9af94b00e9e3f0bb072b34caaf207f32dcb4f5782fc9ca351df9a06c97
```

`nssm.exe` ni konsolsiz yoki administratorsiz to'g'ridan-to'g'ri chaqirmang —
u xabar oynasi ochadi. `install\service.ps1` dan foydalaning.

## cloudflared

Rasmiy manba: <https://github.com/cloudflare/cloudflared/releases> →
`cloudflared-windows-amd64.exe`; `cloudflared.exe` deb nomlab shu papkaga
qo'ying. SHA-256 reliz sahifasida; fayl «Cloudflare, Inc.» imzosi bilan:

```powershell
(Get-FileHash cloudflared.exe -Algorithm SHA256).Hash.ToLower()
# 2026.10.7: 2493dbc168923bb3e59e5e7716f71deced92992eea9acd6e9d74f84ac7751343
(Get-AuthenticodeSignature cloudflared.exe).Status   # Valid
```

Boshqa joy: `SRV1_CLOUDFLARED_EXE`. Plagin uni `--no-autoupdate` bilan ishga
tushiradi — yangilash qo'lda.

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
