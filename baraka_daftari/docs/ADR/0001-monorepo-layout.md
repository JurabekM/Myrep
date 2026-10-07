# ADR 0001 — Monorepo joylashuvi

Qaror: `baraka_daftari/{desktop,spec,docs}`. Sabab: repo allaqachon ko'p loyihali monorepo. `spec/` mobil ilova bilan git submodule o'rniga bir joyda yashaydi, shuning uchun vektorlar ikki tomon uchun yagona manba.
Stek (DESKTOP_PROMPT 2-bo'lim) o'zgarmagan. Aniqlashtirish: `tauri = "2"` pin qilingan (crates.io da `3.0.0-alpha` ham bor, ishlatilmaydi); `tauri-specta`/`specta` — `=2.0.0-rc.25` (prerelease, aniq pin).
