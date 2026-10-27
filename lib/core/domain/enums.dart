// Domen enum'lari. Bazada enum NOMI saqlanadi (`textEnum`) — nomni
// o'zgartirish yoki o'chirish migratsiya talab qiladi. Yangi qiymat faqat
// oxiriga qo'shiladi.

/// Daromad manbai (SPEC 2.1).
enum IncomeSource { dailyWork, order, salary, other }

/// To'lov kanali: naqd yoki karta.
enum PaymentChannel { cash, card }

/// «Ter / mol / tavakkal» testi (SPEC 2C.5). MVP-1 da ixtiyoriy (nullable).
enum IncomeSourceType { ter, mol, tavakkal, ribo }

/// Zarur / Kerak / Havas (SPEC 2B.2). MVP-1 da so'ralmaydi (nullable).
enum Necessity { zarur, kerak, havas }

/// Doimiy to'lov turi (SPEC 2.5).
enum ObligationKind { rent, credit, utility, phone, fuel, other }

/// Kreditor turi (SPEC 2C.7). `shop` — nasiya daftari.
enum CreditorType { bank, shop, relative, friend, other }

/// Qiymat saqlovchi turi (SPEC 4.3). MVP-1 da faqat `cash` va `vault`.
enum AssetType {
  cash,
  bankCard,
  vault,
  gold,
  silver,
  foreignCurrency,
  receivable,
  tradeGoods,
  businessShare,
}

/// `Asset.quantity` birligi: pul — minor birlik, oltin/kumush — milligramm.
enum QuantityUnit { minor, milligram, piece }

/// Jamg'arma turi (SPEC 2C.3) — MVP-3 uchun zaxira maydon.
enum VaultType { qorovul, osadigan }

enum VaultTransactionType { deposit, withdraw }

/// Jamg'arma harakati sababi kodi. Pul olishda izoh (`reasonNote`) majburiy.
enum VaultTransactionReason {
  /// «Avval yigʻilgan pul»: ilovadan oldingi jamg'arma (bir martalik).
  initial,

  /// Daromaddan ulush.
  incomeShare,

  /// Qo'lda qo'shilgan summa.
  manual,

  /// Pul olish.
  withdrawal,

  /// «Qutqarilgan pul»ni o'tkazish (v7, SPEC 2B.7).
  rescue,
}

enum AllocationMode { fixed, progressive }

enum MemberRole { adult, child }

/// Standart kategoriyalar (seed). Foydalanuvchiga ko'rinadigan nomi ARB'dan
/// olinadi; bazada faqat kalit saqlanadi.
enum CategoryKey {
  rent,
  credit,
  groceries,
  utilities,
  phone,
  fuel,
  transport,
  dailySmall,
  children,
  sadaqa,
  other,

  /// Ichimlik va gazak (v6).
  snacks,

  /// Choyxona va kafe (v6).
  cafe,
}

/// Obuna to'lov davri (SPEC 2B.5, v7).
enum SubscriptionCycle { monthly, yearly }

/// «Qutqarilgan pul» manbai (SPEC 2B.7, v7).
enum RescueKind {
  /// Bekor qilingan obuna — oylik ekvivalenti.
  subscription,

  /// Konvertda qolgan qoldiq (hafta yopilganda).
  envelopeLeftover,

  /// «Kelajagim»ga o'tkazilgan summa (qutqarilgandan ayiriladi).
  transfer,
}

/// Qarz to'lov jadvali turi (SPEC 2D.3, v9).
enum DebtScheduleType {
  /// Teng oylik to'lov (bank: foiz qoldiqqa).
  annuity,

  /// Asosiy qarz teng, foiz qoldiqqa — to'lov kamayib boradi.
  differentiated,

  /// Qat'iy ustama (masalan, muddatli to'lov): (asosiy + ustama) / oylar.
  fixedMarkup,

  /// Foydalanuvchi sanalar va summalarni o'zi kiritadi (qarzi hasana).
  manual,
}

/// Qarz tilxatidagi imzolovchi roli (SPEC 2D.5, v9).
enum SignerRole {
  borrower,
  lender,
  witness,
  party,

  /// Hakam — hakamlikka roziligini imzo bilan bildiradi (SPEC 2F.3, v15).
  arbiter,
}

/// Byudjet rejimi (SPEC 2D.1, v10): odatiy yoki «Qarzdan chiqish» 70/20/10.
enum BudgetMode { standard, debtRecovery }

/// Sotiladigan buyum holati (SPEC 2D.7, v10).
enum SellableStatus { listed, sold }

/// Marosim turi (SPEC 2D.8, v11).
enum CeremonyType { toy, beshikToy, sunnatToy, maraka, other }

/// Marosim rejasi holati: qoralama → oilada muhokama qilindi → tasdiqlandi.
enum CeremonyStatus { draft, discussed, confirmed }

/// Byudjet qatori: bir martalik yoki «kishi boshiga × mehmonlar».
enum CeremonyLineKind { oneTime, perGuest }

/// Qator qayerdan moliyalanadi.
enum FundingSource { savings, family, expectedGifts, debt }

/// Sheriklik turi (SPEC 2E.1, v12).
enum PartnershipType { mudaraba, musharaka }

/// Sheriklik holati: shartnoma imzolanmagan → imzolangan → faol → yopilgan.
enum PartnershipStatus { draft, signed, active, closed }

/// Sherikning roli.
enum PartnerRole { capitalProvider, worker, both }

/// Kapital turi: pul yoki narxlangan uskuna.
enum CapitalKind { cash, equipment }

/// Hisobot davriyligi.
enum ReportPeriod { monthly, quarterly, yearly }

/// Sheriklik daftari yozuvi (SPEC 2E.3, v13).
enum VentureEntryKind { income, expense, forceMajeure, correction }

/// «Kafolatlangan foyda» detektori natijasi (SPEC 2E.5).
enum OfferVerdict { green, yellow, red }

/// Taklif bo'yicha qaror (SPEC 2G.6, v16): «pul qo'yaman» faqat maslahatdan va
/// 24 soatdan keyin.
enum OfferDecision { declined, postponed, accepted }

/// Oylik daromad turi (onboarding, MVP_PLAN Vazifa 15): bosh ekran va
/// eslatmalar shunga moslashadi.
enum IncomeKind { dailyCash, orders, salary }

/// Kelishuv turi (SPEC 2F.1, v15).
enum AgreementType { partnership, loan, rent, service, family, other }

/// Kelishuv holati: `DRAFT → SIGNED → ACTIVE → (IN_DISPUTE) → CLOSED`.
enum AgreementStatus { draft, signed, active, inDispute, closed }

/// Kelishuv nimaga bog'langan (mavjud modul yozuvi).
enum AgreementSource { debt, receivable, partnership }

/// O'qish maqsadi holati (SPEC 2H.2, v17).
enum LearningGoalStatus { active, done, dropped }

/// O'qish yo'li turi (SPEC 2H.3): kitob, ustoz, kurs, amaliyot.
enum LearningItemKind { book, mentor, course, practice }

/// O'qish yo'li holati (SPEC 2H.3).
enum LearningItemStatus { planned, inProgress, done, dropped }
