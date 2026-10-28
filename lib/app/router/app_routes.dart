/// Ilova marshrutlari (go_router yo'llari).
abstract final class AppRoutes {
  static const lock = '/lock';
  static const pinSetup = '/setup';
  static const home = '/home';
  static const onboarding = '/onboarding';
  static const backup = '/backup';
  static const incomeNew = '/income/new';
  static const expenses = '/expenses';
  static const expenseNew = '/expenses/new';
  static const vault = '/vault';
  static const vaultRule = '/vault/rule';
  static const vaultWithdraw = '/vault/withdraw';

  /// Katta summa taqsimoti: avval oilaviy zaxira (SPEC 2G.5).
  static const vaultLumpSum = '/vault/lump-sum';
  static const obligations = '/obligations';
  static const nasiya = '/nasiya';
  static const audit = '/audit';
  static const whoseMoney = '/whose-money';
  static const members = '/members';
  static const settings = '/settings';
  static const about = '/settings/about';

  /// Maxfiylik siyosati (Google Play: ilova ichida ham bo'lishi shart).
  static const privacy = '/settings/about/privacy';
  static const content = '/content';
  static const categories = '/expenses/categories';
  static const templates = '/expenses/templates';
  static const havas = '/havas';
  static const subscriptions = '/subscriptions';
  static const envelopes = '/envelopes';
  static const rescue = '/rescue';
  static const prices = '/prices';
  static const mouse = '/vault/mouse';
  static const debts = '/debts';
  static const debtNew = '/debts/new';
  static const debtPlan = '/debts/plan';
  static const debtRecovery = '/debts/recovery';
  static const sellables = '/debts/sell';
  static const ceremonies = '/ceremonies';
  static const ceremonyPattern = '/ceremonies/item/:planId';
  static String ceremony(String id) => '/ceremonies/item/$id';
  static const partnerships = '/partnerships';
  static const partnershipNew = '/partnerships/new';
  static const partnershipPattern = '/partnerships/item/:partnershipId';
  static String partnership(String id) => '/partnerships/item/$id';
  static const partnershipLedgerPattern =
      '/partnerships/item/:partnershipId/ledger';
  static String partnershipLedger(String id) => '/partnerships/item/$id/ledger';
  static const ideas = '/ideas';
  static const ideaNew = '/ideas/new';
  static const offerCheck = '/offer-check';

  /// «Bilimga sarmoya» (8-qonun, Vazifa 14C).
  static const learning = '/learning';
  static const learningHourly = '/learning/hourly';
  static const learningGoalPattern = '/learning/goal/:goalId';
  static String learningGoal(String id) => '/learning/goal/$id';

  /// Kelishuvlar (6-qonun, Vazifa 9A).
  static const agreements = '/agreements';
  static const agreementOral = '/agreements/oral';
  static const agreementPattern = '/agreements/item/:agreementId';
  static String agreement(String id) => '/agreements/item/$id';
  static const agreementReviewPattern = '/agreements/item/:agreementId/review';
  static String agreementReview(String id) => '/agreements/item/$id/review';
  static const agreementDisputePattern =
      '/agreements/item/:agreementId/dispute/:disputeId';
  static String agreementDispute(String agreementId, String disputeId) =>
      '/agreements/item/$agreementId/dispute/$disputeId';

  /// Qarz tafsiloti va qarz tilxati (parametrli — FLAG_SECURE naqsh bo'yicha).
  static const debtDetailPattern = '/debts/item/:debtId';
  static const debtReceiptPattern = '/debts/item/:debtId/receipt';
  static const receivableReceiptPattern = '/debts/lent/:receivableId/receipt';
  static String debt(String id) => '/debts/item/$id';
  static String debtReceipt(String id) => '/debts/item/$id/receipt';
  static String receivableReceipt(String id) => '/debts/lent/$id/receipt';

  /// Bob va uning «Daftar sahifasi» (ta'limiy — FLAG_SECURE yo'q).
  static String chapter(String id) => '$content/$id';
  static String daftar(String id) => '$content/$id/daftar';

  static const List<String> all = [
    lock,
    pinSetup,
    home,
    onboarding,
    backup,
    incomeNew,
    expenses,
    expenseNew,
    vault,
    vaultRule,
    vaultWithdraw,
    vaultLumpSum,
    obligations,
    nasiya,
    audit,
    whoseMoney,
    members,
    settings,
    about,
    privacy,
    content,
    categories,
    templates,
    havas,
    subscriptions,
    envelopes,
    rescue,
    prices,
    mouse,
    debts,
    debtNew,
    debtPlan,
    debtRecovery,
    sellables,
    ceremonies,
    partnerships,
    partnershipNew,
    ideas,
    ideaNew,
    offerCheck,
    learning,
    learningHourly,
    agreements,
    agreementOral,
  ];

  /// Qulf ochilmaguncha kirish mumkin bo'lgan marshrutlar.
  static const Set<String> public = {lock, pinSetup};

  /// Onboarding tugamaguncha (qulf ochiq bo'lsa) ochiladigan marshrutlar.
  static const Set<String> preOnboarding = {onboarding, backup};

  /// FLAG_SECURE yoqiladigan marshrutlar: moliyaviy va shaxsiy ekranlar,
  /// PIN kiritish. Faqat ta'limiy kontent (boblar) bundan mustasno.
  /// Parametrli marshrutlar naqshlari — hammasi moliyaviy (FLAG_SECURE).
  static const Set<String> securePatterns = {
    debtDetailPattern,
    debtReceiptPattern,
    receivableReceiptPattern,
    ceremonyPattern,
    partnershipPattern,
    partnershipLedgerPattern,
    agreementPattern,
    agreementReviewPattern,
    agreementDisputePattern,
    learningGoalPattern,
  };

  static final Set<String> secure = {
    for (final r in all)
      if (r != content) r,
  };
}
