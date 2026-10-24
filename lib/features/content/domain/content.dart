import 'package:meta/meta.dart';

/// Ko'p tilli matn: `uz` majburiy (asosiy), `ru` ixtiyoriy (bo'lmasa uz).
@immutable
final class LocalizedText {
  const LocalizedText(this.values);

  final Map<String, String> values;

  String of(String languageCode) => values[languageCode] ?? values['uz']!;
}

/// Diniy matnni ulamo tekshirganmi (SPEC 3). `pending` — production'da
/// ko'rsatilmaydi.
enum ReligiousReviewStatus { pending, approved }

/// Haftalik vazifani ilova o'zi belgilaydigan hodisa (MVP_PLAN Vazifa 6).
///
/// Ro'yxat kengaytiriladi: yangi modul (obunalar, qarzlar …) bu yerga o'z
/// kodini qo'shadi va hodisa ro'y berganda `recordTaskEvent` ni chaqiradi.
/// Kontent JSON'ida `autoComplete` shu [code] bilan yoziladi; noma'lum kod
/// bobni yaroqsiz qiladi (jimgina e'tiborsiz qolmaydi).
enum TaskTrigger {
  /// «Kelajagim» ekrani ochildi.
  vaultOpened('VAULT_OPENED'),

  /// «Kelajagim»ga pul qo'yildi (daromad ulushi). Har qo'yishda yuboriladi —
  /// vazifa haftada bir marta belgilanadi, avval qo'yilgan bo'lsa ham
  /// bob ochilgandan keyingi birinchi qo'yish uni bajaradi.
  vaultFirstDeposit('VAULT_FIRST_DEPOSIT'),

  /// Daromaddan ulush ajratildi.
  incomeShared('INCOME_SHARED'),

  /// Oylik audit yakunlandi.
  auditCompleted('AUDIT_COMPLETED'),

  /// «Daftar sahifasi»ga qonun yozildi.
  daftarPageWritten('DAFTAR_PAGE_WRITTEN'),

  /// Xarajat yozildi.
  expenseRecorded('EXPENSE_RECORDED'),

  // Keyingi vazifalar hodisalari (modul tayyor bo'lganda chaqiriladi).

  /// Obunalar ko'rib chiqildi (Vazifa 8).
  subscriptionsReviewed('SUBSCRIPTIONS_REVIEWED'),

  /// Konvert yaratildi.
  envelopeCreated('ENVELOPE_CREATED'),

  /// Havas xarajatlari chegarasi oilada kelishildi.
  havasLimitAgreed('HAVAS_LIMIT_AGREED'),

  /// Narx solishtirildi.
  priceComparisonDone('PRICE_COMPARISON_DONE'),

  /// Favqulodda jamg'arma maqsadi qo'yildi.
  emergencyTargetSet('EMERGENCY_TARGET_SET'),

  /// Barcha qarzlar ro'yxatga olindi.
  debtInventoryCompleted('DEBT_INVENTORY_COMPLETED'),

  /// Qarzdan chiqish rejasi tuzildi.
  payoffPlanCreated('PAYOFF_PLAN_CREATED'),

  /// Taklif (kredit, sherikchilik …) tekshirildi.
  offerChecked('OFFER_CHECKED'),

  /// Halol tadbirkorlik g'oyasi yozildi.
  ventureIdeaCreated('VENTURE_IDEA_CREATED'),

  /// Kelishuv (9 savol) hamma tomonidan imzolandi (Vazifa 9A).
  agreementSigned('AGREEMENT_SIGNED'),

  /// Og'zaki kelishuv yozib olindi (SPEC 2F.9).
  oralAgreementRecorded('ORAL_AGREEMENT_RECORDED'),

  /// Oylik ochiq hisob ko'rigi bayonnoma bilan yakunlandi (Vazifa 14A).
  accountReviewCompleted('ACCOUNT_REVIEW_COMPLETED'),

  /// Oilaviy kelishuv yaratildi (SPEC 2F.10, Vazifa 14A).
  familyAgreementCreated('FAMILY_AGREEMENT_CREATED');

  const TaskTrigger(this.code);

  /// JSON'dagi kod.
  final String code;

  static final Map<String, TaskTrigger> _byCode = {
    for (final t in values) t.code: t,
  };

  /// Noma'lum kod — `null`.
  static TaskTrigger? fromCode(String code) => _byCode[code];
}

sealed class ContentBlock {
  const ContentBlock();
}

final class ParagraphBlock extends ContentBlock {
  const ParagraphBlock(this.text);

  final LocalizedText text;
}

/// Maslahatchi maslahati yoki ajratilgan iqtibos.
final class QuoteBlock extends ContentBlock {
  const QuoteBlock(this.text);

  final LocalizedText text;
}

/// Oyat, hadis yoki rivoyat. Manba va ulamo tekshiruvi majburiy.
final class ReligiousBlock extends ContentBlock {
  const ReligiousBlock({
    required this.text,
    required this.source,
    required this.status,
  });

  final LocalizedText text;
  final LocalizedText source;
  final ReligiousReviewStatus status;
}

@immutable
final class Law {
  const Law({required this.number, required this.text});

  final int number;
  final LocalizedText text;
}

@immutable
final class WeeklyTask {
  const WeeklyTask({required this.id, required this.text, this.trigger});

  /// Masalan, `ch01.t1`.
  final String id;
  final LocalizedText text;

  /// `null` — faqat qo'lda belgilanadi.
  final TaskTrigger? trigger;
}

@immutable
final class Chapter {
  const Chapter({
    required this.id,
    required this.order,
    required this.title,
    required this.blocks,
    required this.law,
    required this.weeklyTasks,
    this.audioUrl,
  });

  final String id;

  /// 1, 2, 3 … — ochilish tartibi.
  final int order;
  final LocalizedText title;
  final List<ContentBlock> blocks;
  final Law law;

  /// Aniq 3 ta.
  final List<WeeklyTask> weeklyTasks;
  final String? audioUrl;

  /// Ko'rsatiladigan bloklar: tasdiqlanmagan diniy bloklar faqat
  /// [showPendingReligious] bo'lsa (debug — kontent tekshiruvi uchun).
  List<ContentBlock> visibleBlocks({required bool showPendingReligious}) => [
    for (final b in blocks)
      if (b is! ReligiousBlock ||
          b.status == ReligiousReviewStatus.approved ||
          showPendingReligious)
        b,
  ];
}

/// Kontentni yuklash natijasi: yaroqli boblar + topilgan xatolar.
/// Buzuq bob o'tkazib yuboriladi, ilova yiqilmaydi.
@immutable
final class ContentLoadResult {
  const ContentLoadResult({required this.chapters, required this.errors});

  /// `order` bo'yicha tartiblangan.
  final List<Chapter> chapters;
  final List<String> errors;

  bool get isEmpty => chapters.isEmpty;
}
