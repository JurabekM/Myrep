import enum


class AuthProvider(str, enum.Enum):
    PHONE = "phone"
    GOOGLE = "google"
    EMAIL = "email"


class Language(str, enum.Enum):
    UZ = "uz"
    RU = "ru"
    EN = "en"


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class TransactionSource(str, enum.Enum):
    MANUAL = "manual"
    VOICE = "voice"
    OCR_RECEIPT = "ocr_receipt"
    BANK_SYNC = "bank_sync"
    AI_SUGGESTED = "ai_suggested"


class SyncStatus(str, enum.Enum):
    PENDING = "pending"
    SYNCED = "synced"
    CONFLICT = "conflict"


class BudgetPeriod(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DebtDirection(str, enum.Enum):
    LENT = "lent"       # men qarz berdim
    BORROWED = "borrowed"  # men qarz oldim


class InvestmentAssetType(str, enum.Enum):
    GOLD = "gold"
    USD = "usd"
    CRYPTO = "crypto"
    STOCK = "stock"
    ETF = "etf"
    BOND = "bond"


class PaymentProviderCode(str, enum.Enum):
    CLICK = "click"
    PAYME = "payme"
    UZUM = "uzum"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELED = "canceled"


class ChallengePeriod(str, enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ChallengeTargetType(str, enum.Enum):
    SAVE_AMOUNT = "save_amount"  # davr ichida jami tejash (daromad-xarajat) belgilangan summadan katta bo'lishi
    NO_SPEND_DAYS = "no_spend_days"  # davr ichida xarajatsiz kunlar soni


class TaskRewardStatus(str, enum.Enum):
    PENDING = "pending"
    DONE = "done"        # bola bajarganini belgiladi
    APPROVED = "approved"  # ota-ona tasdiqladi, mukofot beriladi


class NotificationType(str, enum.Enum):
    BUDGET_ALERT = "budget_alert"
    GOAL_REMINDER = "goal_reminder"
    LOAN_REMINDER = "loan_reminder"
    DEBT_REMINDER = "debt_reminder"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_SUMMARY = "weekly_summary"
    AI_INSIGHT = "ai_insight"
    ADMIN_MESSAGE = "admin_message"  # admin paneldan yuborilgan xabar
