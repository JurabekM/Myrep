# Kontent (placeholder)

Qissa matnlari litsenziya (`«Asaxiy Invest» × Abdukarim Mirzayev`) hal bo'lguncha **placeholder**: bu yerda faqat qonun nomlari
va spetsifikatsiyadagi mazmunning qisqa o'z so'zlarimizdagi bayoni bor. Asl matnlarni repoga ko'chirmang.

## Format (`chNN.json`)
- `blocks[]`: `TEXT` yoki `RELIGIOUS`. `RELIGIOUS` bloki uchun `source` va `review_status` (`PENDING` | `APPROVED`) majburiy.
  **Release build'da faqat `APPROVED` diniy bloklar ko'rsatiladi** (ulamo tekshiruvidan o'tmaganlari yashiriladi).
- `tasks[]`: har bobda aniq 3 ta haftalik vazifa. `trigger.type`: `MANUAL`, `INCOME_RECORDED{min}`, `ALLOCATION_MADE{min_days}`,
  `AUDIT_COMPLETED`, `OBLIGATION_ADDED`. Avtomatik triggerlar ilova ma'lumotidan hisoblanadi, `MANUAL` — foydalanuvchi belgilaydi.
- `page_prompt`: «Daftar sahifasi» uchun savol (foydalanuvchi qonunni o'z qo'li bilan yozadi).
