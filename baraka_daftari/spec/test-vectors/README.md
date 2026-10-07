# Umumiy oltin test vektorlari

Mobil (Dart) va desktop (Rust) ilovalari shu fayllardan o'tishi shart (`docs/DESKTOP_PROMPT.md` 5-bo'lim).

- Pul qiymatlari string (minor birlikda). Case `id` lari o'zgarmaydi; xato topilsa yangi `version` chiqariladi.
- Desktop runner: `cargo test -p vectors` (`desktop/crates/vectors`).
- Hozirgi suite'lar: `allocate`, `percent_of`, `fx_convert`, `money_format`, `money_parse`, `unexplained_gap`, `streak`, `share_suggestion`, `chapter_unlock`, `havas_status`, `habit_projection`.
- Keyingi vazifalarda (D4, D8, D10, D12) qo'shiladi: `amortization`, `profit_distribution`,
  `emergency_target`, `personal_inflation`, `unexplained_gap`, `readiness_gate`, `debt_recovery_split`.

## Natija formatlari
| suite | expected |
|---|---|
| allocate | `{"parts": ["34","33","33"]}` yoki `{"error": "INVALID_RATIOS"}` |
| percent_of | `{"minor": "80000000"}` |
| fx_convert | `{"minor": "...", "currency": "UZS"}` yoki `{"error": "CURRENCY_MISMATCH" \| "INVALID_RATE"}` |
| money_format | `{"text": "8 000 000 so'm"}` |

### D4 da qo'shilgan suite'lar
| suite | kirish | expected |
|---|---|---|
| unexplained_gap | `income, obligations, expenses, savings, currency` | `{"month_result", "unexplained"}` (manfiy bo'lishi mumkin) |
| streak | `dates[], today, anchor` (`FRIDAY` ...) | `{"current_weeks", "best_weeks", "saved_days"}` |
| share_suggestion | `rule {kind: PERCENT\|MONTHLY_FIXED, value}`, `income`, `allocated_this_month` | `{"minor"}` |
| money_parse | `text`, `currency` | `{"minor"}` yoki `{"error": "PARSE" \| "OVERFLOW"}` |
| chapter_unlock | `policy{window_weeks,min_satisfied_weeks,min_tasks_per_week}`, `opened_week`, `today`, `anchor`, `results[{week_start,completed_tasks}]` | `{"decision":"UNLOCKED"}` yoki `{"decision":"LOCKED","satisfied_weeks","needed_weeks","weeks_in_window"}` |
| havas_status | `spent`, `limit`, `currency` | `{"state": "OK"\|"NEAR"\|"OVER", "used_bp"}` yoki `{"error": "INVALID_LIMIT"\|"INVALID_AMOUNT"}` |
| habit_projection | `total`, `window_days`, `currency` | `{"week","month","year"}` (minor, string) |
| rescued_money | `baseline`, `current`, `currency` | `{"rescued"}` (manfiy holat → 0) yoki `{"error":"INVALID_AMOUNT"}` |
| subscription_cost | `period` (WEEKLY\|MONTHLY\|QUARTERLY\|YEARLY), `amount` | `{"monthly","yearly"}` |
| forgotten_subscription | `started_on`, `last_used_on` (null bo'lishi mumkin), `today`, `threshold_days` | `{"forgotten": bool}` |
| envelope | `limit`, `spent`, `leftover_cash?` | `{"remaining","state","used_bp","cash_to_fill","difference?"}` yoki `{"error":"INVALID_LIMIT"}` |
| money_parse_signed | `text`, `currency` | `{"negative": bool, "minor"}` yoki `{"error":"PARSE"}` |
