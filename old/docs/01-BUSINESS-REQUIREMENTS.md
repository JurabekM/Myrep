# AI Business Advisor Uzbekistan — Business Requirements Document (BRD)

**Versiya:** 1.0 | **Sana:** 2026-07-10 | **Bosqich:** 1 — Business Analysis

---

## 1. Loyiha maqsadi

O'zbekistondagi kichik va o'rta biznes, tadbirkorlar hamda startup egalariga sun'iy
intellekt yordamida biznes strategiyasi, marketing, soliq, huquq, moliya va boshqa
15 yo'nalishda professional darajadagi maslahat beruvchi SaaS platforma.

## 2. Muammo (Problem Statement)

| Muammo | Hozirgi holat | Platformaning yechimi |
|---|---|---|
| Konsalting qimmat | 1 soatlik konsultatsiya 500 000 – 2 000 000 so'm | Oylik obuna narxida cheksiz maslahat |
| Qonunchilik murakkab | lex.uz da qidirish qiyin, tili og'ir | RAG orqali qonunlarni oddiy tilda tushuntirish |
| Soliq hisob-kitobi chalkash | YTT/MChJ/mikrofirma rejimlari farqi noaniq | Interaktiv soliq kalkulyatori + AI tushuntirish |
| Biznes-reja yozish qiyin | Shablonlar eskirgan, grant arizalari rad etiladi | AI generatsiya: biznes-reja, pitch deck, grant ariza |
| Marketing bilimi yetishmaydi | SMM agentliklar qimmat | Kontent-plan, reklama matni, funnel generatori |

## 3. Maqsadli foydalanuvchilar (Personas)

1. **Startup founder** — pitch deck, investor hujjatlari, MVP strategiya
2. **Yangi tadbirkor** — ro'yxatdan o'tish, soliq rejimi tanlash, birinchi biznes-reja
3. **Kichik biznes egasi** — marketing, moliya nazorati, xodimlar
4. **O'rta biznes** — eksport/import, tender, investitsiya jalb qilish
5. **Frilanser / YTT** — soliq, shartnomalar, shaxsiy brend
6. **MChJ rahbari** — buxgalteriya, huquqiy risklar, HR
7. **Investor** — bozor tahlili, due diligence savollari
8. **Marketing/konsalting agentligi** — mijozlar uchun tez tahlil (B2B tarif)

## 4. Funksional talablar (Core Features)

| # | Modul | Ustuvorlik | MVP? |
|---|---|---|---|
| F1 | AI Chat (fayl, ovoz, rasm, history, memory) | P0 | ✅ |
| F2 | Business Consultant (SWOT, BMC, biznes-reja, pitch...) | P0 | ✅ |
| F3 | Legal Assistant (lex.uz RAG, shartnoma tahlili, disclaimer) | P0 | ✅ |
| F4 | Tax Assistant (kalkulyator: QQS, aylanma, daromad, YTT/MChJ) | P0 | ✅ |
| F5 | Marketing AI (SEO, SMM, kontent-plan, reklama matni) | P1 | ✅ |
| F6 | Document Analyzer (PDF/DOCX/XLSX/PPTX/rasm, OCR) | P1 | ✅ |
| F7 | Financial Module (ROI, NPV, IRR, Break-even, Cash Flow) | P1 | ✅ |
| F8 | Dashboard (grafiklar, trend, heatmap, forecast) | P1 | ✅ |
| F9 | User Profile (industry, goals — personalizatsiya) | P0 | ✅ |
| F10 | Admin Panel (users, payments, prompts, KB, flags, logs) | P1 | ✅ |

## 5. Nofunksional talablar

- **Til:** UZ (lotin/kirill), RU, EN — UI va AI javoblari
- **Performance:** chat birinchi token < 2s (streaming), API p95 < 300ms
- **Xavfsizlik:** OWASP Top 10, JWT + refresh rotation, 2FA (TOTP), RBAC, audit log
- **AI Safety:** confidence score, source citation, hallucination detection, prompt injection himoyasi, huquqiy/soliq javoblarda majburiy disclaimer
- **Test qamrovi:** ≥ 95%
- **Availability:** 99.5% (MVP), monitoring: Prometheus + Grafana + Sentry
- **Compliance:** O'zR "Shaxsiy ma'lumotlar to'g'risida"gi qonun (ma'lumotlar lokalizatsiyasi rejasi)

## 6. Monetizatsiya

| Tarif | Narx (taxminiy) | Cheklovlar |
|---|---|---|
| Free | 0 | 10 xabar/kun, 1 hujjat/kun, GPT-mini darajali model |
| Pro | ~99 000 so'm/oy | 500 xabar/kun, 20 hujjat, kuchli modellar, barcha modullar |
| Business | ~299 000 so'm/oy | Cheksiz, jamoa (5 user), API access, prioritet |
| Enterprise | Shartnoma | White-label, on-prem/mahalliy LLM, SLA |

To'lov: Payme, Click, Uzum (keyingi bosqichda integratsiya), Stripe (xalqaro).

## 7. Risklar

| Risk | Ehtimol | Ta'sir | Mitigatsiya |
|---|---|---|---|
| AI noto'g'ri huquqiy/soliq maslahat | O'rta | Yuqori | Disclaimer, citation, confidence score, RAG-only rejim |
| lex.uz strukturasi o'zgarishi | O'rta | O'rta | Scraper abstraction + monitoring + KB versiyalash |
| LLM provider narxi/limiti | O'rta | O'rta | Model abstraction — 8 provider, fallback chain |
| Shaxsiy ma'lumotlar qonuni | Past | Yuqori | Mahalliy LLM opsiyasi, ma'lumotlarni O'zR serverida saqlash rejimi |

## 8. Muvaffaqiyat mezonlari (KPI)

- MVP: 1 000 ro'yxatdan o'tgan foydalanuvchi / 3 oy
- Free→Pro konversiya ≥ 5%
- Javob foydaliligi (thumbs up) ≥ 80%
- Hallucination rate (huquq/soliq kategoriyasida) < 2%
