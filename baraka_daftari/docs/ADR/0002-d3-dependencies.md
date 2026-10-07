# ADR 0002 — D3 bog'liqliklari

Yangi paketlar va sabablari:
- `rusqlite` (`bundled-sqlcipher-vendored-openssl`) + `rusqlite_migration`: SPEC bo'yicha; OpenSSL vendored, shuning uchun tizim OpenSSL'ga bog'liq emas (Windows'da perl va make kerak, CI'da bor).
- `argon2`, `chacha20poly1305` (XChaCha20-Poly1305), `hkdf` + `sha2`: PIN va keyring sirini bitta o'rash kalitiga birlashtirish uchun (HKDF); boshqa yo'l bilan ikki omillilikka erishib bo'lmaydi.
- `keyring` **3.x** (4.x emas): 4.x API butunlay yangi (`keyring-core`, default store o'rnatiladi) va hali kam sinalgan; 3.x Windows/macOS/Linux'ni `windows-native`, `apple-native`, `sync-secret-service` bilan qoplaydi.
- `getrandom`: `OsRng` bilan bir xil OS manbasi; `rand` 0.10 API'si beqaror, shuning uchun to'g'ridan-to'g'ri `getrandom::fill`.
- `zeroize`: PIN va kalitlarni xotiradan tozalash.
- `uuid` (v7), `time`: SPEC bo'yicha (`chrono-tz` keyingi vazifada, lokal sana hisobi kerak bo'lganda).
- Dev: `tempfile`.
