# SMART MOLIYA

AI yordamidagi shaxsiy moliyaviy yordamchi — O'zbekiston bozori uchun native Android FinTech ilova.

## Holat: barcha 11 bosqich yakunlandi ✅

Mobil qism: **native Kotlin + Jetpack Compose** (Android Studio'da to'g'ridan-to'g'ri build bo'ladigan Gradle loyihasi). `android/` papkasini Android Studio'da ochib ishga tushirish mumkin — qo'llanma: [`android/INSTALL.md`](android/INSTALL.md). Butun tizimni Docker bilan ko'tarish: [`docs/11_DEPLOYMENT.md`](docs/11_DEPLOYMENT.md).

1. ✅ Architecture + Android Studio skelet (build bo'ladi)
2. ✅ Database (PostgreSQL + Alembic, Room offline sxema)
3. ✅ Backend (FastAPI — auth, wallets, transactions, budgets, goals, loans, debts, sync)
4. ✅ Android UI (Dashboard, Wallets, Income/Expense, Reports — offline-first, Retrofit+Room+Hilt)
5. ✅ AI Module (`ai_service/` — PyTorch classifier/forecast, statistik anomaly, uz/ru/en chatbot)
6. ✅ Authentication (Phone+parol, Biometric, PIN, device binding — Google/OTP tashqi kalit talab qiladi)
7. ✅ Payments (Universal Bank API Layer — 8 bank mock, Click/Payme/UzumBank mock + webhook imzo tekshiruvi)
8. ✅ Reports (server-side ReportService, PDF/Excel export, Android Pie chart)
9. ✅ Gamification (XP/level/streak/badge, Challenge, Family Mode — Android UI hali yo'q)
10. ✅ Testing (backend 41 test + coverage, AI service 15 test, Android JVM unit test, locust stress-test)
11. ✅ Deployment (Docker Compose + Nginx + GitHub Actions CI, APK/AAB release yo'riqnomasi)
12. ✅ UI-polish (Payments/Gamification/Family Android ekranlari, "Menyu" bo'limi)

## Hujjatlar

- [`docs/01_ARCHITECTURE.md`](docs/01_ARCHITECTURE.md) — umumiy arxitektura, texnologik stek, modul chegaralari
- [`docs/PROJECT_TREE.md`](docs/PROJECT_TREE.md) — to'liq loyiha daraxti (monorepo: android + backend + ai + admin)
- [`docs/diagrams/`](docs/diagrams) — Mermaid formatidagi UML/ER/Sequence diagrammalar
- [`docs/DELIVERY_PLAN.md`](docs/DELIVERY_PLAN.md) — 11 bosqichli yetkazib berish rejasi va har bosqich chiqishi
- [`android/INSTALL.md`](android/INSTALL.md) — Android Studio'da ochish va build qilish yo'riqnomasi

## Monorepo tuzilishi (qisqacha)

```
smart_moliya/
├── android/        # Native Kotlin + Jetpack Compose (Gradle root, Android Studio'da ochiladi)
├── backend/        # Python FastAPI (asosiy API, 15 router, 49 test)
├── ai_service/      # PyTorch modellari, alohida mikroservis (15 test)
├── admin_panel/     # FastAPI + Jinja2 boshqaruv paneli (8 test) — dashboard/users/fraud/analytics/xabarlar
├── infra/         # Dockerfile'lar, docker-compose.yml, nginx.conf
├── .github/workflows/ # CI: testlar + Android APK + Docker image build
└── docs/         # Arxitektura, diagrammalar, deployment qo'llanmasi
```
