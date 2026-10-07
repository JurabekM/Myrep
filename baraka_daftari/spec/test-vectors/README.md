# Umumiy oltin test vektorlari

Mobil (Dart) va desktop (Rust) ilovalari shu fayllardan o'tishi shart (`docs/DESKTOP_PROMPT.md` 5-bo'lim).

- Pul qiymatlari string (minor birlikda). Case `id` lari o'zgarmaydi; xato topilsa yangi `version` chiqariladi.
- Desktop runner: `cargo test -p vectors` (`desktop/crates/vectors`).
- Hozirgi suite'lar: `allocate`, `percent_of`, `fx_convert`, `money_format`.
- Keyingi vazifalarda (D4, D8, D10, D12) qo'shiladi: `amortization`, `profit_distribution`,
  `emergency_target`, `personal_inflation`, `unexplained_gap`, `readiness_gate`, `debt_recovery_split`.

## Natija formatlari
| suite | expected |
|---|---|
| allocate | `{"parts": ["34","33","33"]}` yoki `{"error": "INVALID_RATIOS"}` |
| percent_of | `{"minor": "80000000"}` |
| fx_convert | `{"minor": "...", "currency": "UZS"}` yoki `{"error": "CURRENCY_MISMATCH" \| "INVALID_RATE"}` |
| money_format | `{"text": "8 000 000 so'm"}` |
