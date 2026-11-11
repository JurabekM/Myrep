# tools/

Tashqi binarlar shu yerga qo'yiladi va **gitga kirmaydi** (`.gitignore`).

| Fayl | Kerak bo'lgan bosqich | Vazifa | Sinalgan versiya |
|------|----------------------|--------|------------------|
| `caddy.exe` | 5 (`hosting`) | reverse proxy, admin API `127.0.0.1:2019` | 2.11.9 |
| `mosquitto/` | 6 (`iot`) | MQTT broker | — |
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
