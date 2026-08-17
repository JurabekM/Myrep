# Loyiha daraxti (monorepo)

```
smart_moliya/
├── android/                                # Native Android Studio loyihasi (Gradle root)
│   ├── settings.gradle.kts
│   ├── build.gradle.kts
│   ├── gradle.properties
│   ├── gradle/wrapper/
│   └── app/
│       ├── build.gradle.kts
│       ├── proguard-rules.pro
│       └── src/main/
│           ├── AndroidManifest.xml
│           ├── java/com/smartmoliya/app/
│           │   ├── SmartMoliyaApplication.kt      # @HiltAndroidApp
│           │   ├── MainActivity.kt                # @AndroidEntryPoint, NavHost
│           │   ├── app/
│           │   │   └── SmartMoliyaNavHost.kt       # Bottom Navigation + NavHost (Dashboard/Wallets/Expense/Reports)
│           │   ├── core/
│           │   │   ├── di/                        # DatabaseModule, RepositoryModule (Hilt @Binds)
│           │   │   ├── network/                   # ApiService (Retrofit), AuthInterceptor, NetworkModule, dto/
│           │   │   ├── datastore/                 # TokenManager (access/refresh token)
│           │   │   ├── database/                  # Room (SQLCipher-tayyor)
│           │   │   │   ├── AppDatabase.kt          # 8 entity: Wallet, Category, Transaction, Budget,
│           │   │   │   │                            #   Goal, Loan, Debt, Investment
│           │   │   │   ├── entity/                # *Entity.kt
│           │   │   │   └── dao/                   # *Dao.kt (Flow-based)
│           │   │   ├── sync/                       # SyncEngine (WorkManager, push/pull)
│           │   │   ├── security/                  # biometric, PIN, root detection
│           │   │   └── error/
│           │   ├── feature/
│           │   │   ├── auth/                      # google/phone/otp/biometric
│           │   │   │   ├── presentation/
│           │   │   │   ├── domain/
│           │   │   │   └── data/
│           │   │   ├── dashboard/presentation/     # DashboardScreen + DashboardViewModel (balans/oylik/so'nggi)
│           │   │   ├── expense/                    # Income+Expense birlashtirilgan (tranzaksiyalar)
│           │   │   │   ├── domain/                 # Transaction, TransactionRepository (interfeys)
│           │   │   │   ├── data/                   # TransactionRepositoryImpl, mapperlar
│           │   │   │   └── presentation/           # ExpenseScreen + ViewModel (qo'shish/o'chirish)
│           │   │   ├── wallets/
│           │   │   │   ├── domain/                 # Wallet, WalletRepository (interfeys)
│           │   │   │   ├── data/                   # WalletRepositoryImpl, mapperlar
│           │   │   │   └── presentation/           # WalletsScreen + ViewModel (CRUD)
│           │   │   ├── reports/presentation/        # ReportsScreen (Canvas bar-chart) + ViewModel
│           │   │   ├── cards/
│           │   │   ├── loans/
│           │   │   ├── debts/
│           │   │   ├── savingsgoals/
│           │   │   ├── investments/
│           │   │   ├── budget/
│           │   │   ├── aichatbot/
│           │   │   ├── voiceexpense/
│           │   │   ├── ocrreceipt/
│           │   │   ├── familymode/
│           │   │   ├── gamification/
│           │   │   ├── financialeducation/
│           │   │   ├── notifications/
│           │   │   └── settings/
│           │   └── ui/theme/                      # Color.kt, Theme.kt, Type.kt (Material 3)
│           └── res/                               # values, drawable, mipmap (adaptive icon)
│   └── src/test, src/androidTest                  # unit + instrumented tests (har feature uchun)
│
├── backend/                                # Core FastAPI service
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/0001_initial_schema.py      # 14 jadval: users, wallets, transactions, ...
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                          # config.py (Settings/.env)
│   │   ├── db/                            # base.py (Base+mixins), session.py (async engine)
│   │   ├── api/v1/                        # routers: auth, users, wallets, transactions,
│   │   │                                    #   budgets, loans, debts, investments, goals,
│   │   │                                    #   sync, payments, notifications, reports
│   │   ├── services/                      # business logic
│   │   ├── repositories/                  # SQLAlchemy async repositories
│   │   ├── models/                        # ORM models — user, wallet, card, category, transaction,
│   │   │                                    #   budget, goal, loan, debt, investment, notification,
│   │   │                                    #   achievement, ai_log, family_group, enums
│   │   ├── schemas/                       # Pydantic DTOs
│   │   ├── integrations/
│   │   │   ├── banks/                     # BankProvider + AsakaAdapter, NBUAdapter, ...
│   │   │   └── payments/                  # Click, Payme, UzumBank (mock)
│   │   └── workers/                       # background jobs (notifications, recurring income)
│   ├── alembic/                           # migrations
│   └── tests/
│
├── ai_service/                             # AI microservice
│   ├── app/
│   │   ├── main.py
│   │   ├── models/                        # PyTorch model defs + weights loader
│   │   ├── inference/                     # classifier, forecast, anomaly, chatbot
│   │   └── training/                      # training scripts, notebooks-as-scripts
│   └── tests/
│
├── admin_panel/                            # FastAPI admin
│   ├── app/
│   │   ├── main.py
│   │   ├── api/                           # analytics, users, fraud, notifications
│   │   └── dashboard/                     # templates/static or React build
│   └── tests/
│
├── infra/
│   ├── docker/
│   │   ├── backend.Dockerfile
│   │   ├── ai_service.Dockerfile
│   │   └── admin_panel.Dockerfile
│   ├── docker-compose.yml
│   ├── nginx/
│   └── github_actions/                    # ci.yml, cd.yml
│
└── docs/
    ├── 01_ARCHITECTURE.md
    ├── PROJECT_TREE.md
    ├── DELIVERY_PLAN.md
    └── diagrams/
        ├── system_architecture.mmd
        ├── er_diagram.mmd
        ├── sequence_add_expense.mmd
        └── class_domain_core.mmd
```
