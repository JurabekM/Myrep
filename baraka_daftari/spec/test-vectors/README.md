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
| emergency_target | `months[]` (ZARUR+KERAK oylar), `target_months`, `currency` | `{"target"}` (ma'lumot yo'q → 0) |
| guard_months | `balance`, `target`, `target_months`, `currency` | `{"months_x100"}` (floor; maqsad 0 → 0) |
| personal_inflation | `items[{weight_bp,first,last}]`, `currency` | `{"per_item_bp":[...],"index_bp"}` yoki `{"error":"NO_WEIGHTS"\|"INVALID_PRICE"}` |
| readiness_gate | `guard_months_x100`, `has_interest_debt`, `has_debt_plan`, `required_x100` | `{"status":"OPEN"\|"LOCKED","reasons":["GUARD_BELOW_TARGET","INTEREST_DEBT_NO_PLAN"]}` |
| allocation_priority | `share`, `guard_balance`, `guard_target`, `gate_open`, `currency` | `{"guard","growing"}` |
| purchasing_power | `op` = `real_value`\|`future_price`\|`quantity_milli`, ... | `{"amount"}` yoki `{"milli"}` yoki `{"error":"INVALID_AMOUNT"}` |
| debt_schedule | `op`=`fixed_markup` (`principal`,`markup`,`months`,`first_due`) yoki `summary` (`principal`,`rows[]`), `currency` | `{"rows":[{"due","amount"}]}` / `{"total","markup"}` yoki `{"error":"EMPTY_SCHEDULE"\|"NON_POSITIVE"\|"BELOW_PRINCIPAL"\|"INVALID_MONTHS"\|"INVALID_AMOUNT"}` |
| debt_cost | `principal`, `paid`, `remaining_scheduled`, `currency` | `{"total","excess","excess_bp"}` yoki `{"error":"INVALID_AMOUNT"}` |
| debt_burden | `monthly`, `income`, `currency` | `{"burden_bp"}` yoki `{"error":"INVALID_AMOUNT"}` |
