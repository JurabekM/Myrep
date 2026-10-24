import 'package:baraka_daftari/app/l10n/l10n.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/audit/domain/month_ledger.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

/// Domen qiymatlari uchun foydalanuvchiga ko'rinadigan nomlar (ARB'dan).
extension DomainLabels on AppLocalizations {
  String categoryKey(CategoryKey key) => switch (key) {
    CategoryKey.rent => catRent,
    CategoryKey.credit => catCredit,
    CategoryKey.groceries => catGroceries,
    CategoryKey.utilities => catUtilities,
    CategoryKey.phone => catPhone,
    CategoryKey.fuel => catFuel,
    CategoryKey.transport => catTransport,
    CategoryKey.dailySmall => catDailySmall,
    CategoryKey.children => catChildren,
    CategoryKey.sadaqa => catSadaqa,
    CategoryKey.other => catOther,
    CategoryKey.snacks => catSnacks,
    CategoryKey.cafe => catCafe,
  };

  /// Foydalanuvchi bergan nom standart kalitdan ustun turadi.
  String category(Category c) =>
      c.name ?? (c.systemKey == null ? catOther : categoryKey(c.systemKey!));

  /// `null` — toifadan tashqari (sadaqa).
  String necessity(Necessity? n) => switch (n) {
    Necessity.zarur => necessityZarur,
    Necessity.kerak => necessityKerak,
    Necessity.havas => necessityHavas,
    null => necessityNone,
  };

  String creditorType(CreditorType t) => switch (t) {
    CreditorType.bank => creditorBank,
    CreditorType.shop => creditorShop,
    CreditorType.relative => creditorRelative,
    CreditorType.friend => creditorFriend,
    CreditorType.other => creditorOther,
  };

  String scheduleType(DebtScheduleType t) => switch (t) {
    DebtScheduleType.manual => scheduleManual,
    DebtScheduleType.annuity => scheduleAnnuity,
    DebtScheduleType.differentiated => scheduleDifferentiated,
    DebtScheduleType.fixedMarkup => scheduleFixedMarkup,
  };

  String signerRole(SignerRole r) => switch (r) {
    SignerRole.lender => roleLender,
    SignerRole.borrower => roleBorrower,
    SignerRole.witness => roleWitness,
    SignerRole.party => roleParty,
    SignerRole.arbiter => roleArbiter,
  };

  String ceremonyType(CeremonyType t) => switch (t) {
    CeremonyType.toy => ceremonyTypeToy,
    CeremonyType.beshikToy => ceremonyTypeBeshik,
    CeremonyType.sunnatToy => ceremonyTypeSunnat,
    CeremonyType.maraka => ceremonyTypeMaraka,
    CeremonyType.other => ceremonyTypeOther,
  };

  String ceremonyStatus(CeremonyStatus s) => switch (s) {
    CeremonyStatus.draft => ceremonyStatusDraft,
    CeremonyStatus.discussed => ceremonyStatusDiscussed,
    CeremonyStatus.confirmed => ceremonyStatusConfirmed,
  };

  String fundingSource(FundingSource f) => switch (f) {
    FundingSource.savings => fundingSavings,
    FundingSource.family => fundingFamily,
    FundingSource.expectedGifts => fundingGifts,
    FundingSource.debt => fundingDebt,
  };

  String partnershipType(PartnershipType t) => switch (t) {
    PartnershipType.mudaraba => pnTypeMudaraba,
    PartnershipType.musharaka => pnTypeMusharaka,
  };

  String partnershipStatus(PartnershipStatus s) => switch (s) {
    PartnershipStatus.draft => pnStatusDraft,
    PartnershipStatus.signed => pnStatusSigned,
    PartnershipStatus.active => pnStatusActive,
    PartnershipStatus.closed => pnStatusClosed,
  };

  String partnerRole(PartnerRole r) => switch (r) {
    PartnerRole.capitalProvider => pnRoleProvider,
    PartnerRole.worker => pnRoleWorker,
    PartnerRole.both => pnRoleBoth,
  };

  String reportPeriod(ReportPeriod p) => switch (p) {
    ReportPeriod.monthly => pnPeriodMonthly,
    ReportPeriod.quarterly => pnPeriodQuarterly,
    ReportPeriod.yearly => pnPeriodYearly,
  };

  String capitalKind(CapitalKind k) => switch (k) {
    CapitalKind.cash => pnCapitalCash,
    CapitalKind.equipment => pnCapitalEquipment,
  };

  String obligationKind(ObligationKind k) => switch (k) {
    ObligationKind.rent => kindRent,
    ObligationKind.credit => kindCredit,
    ObligationKind.utility => kindUtility,
    ObligationKind.phone => kindPhone,
    ObligationKind.fuel => kindFuel,
    ObligationKind.other => kindOther,
  };

  String owner(MoneyOwner o) => switch (o) {
    MoneyOwner.landlord => ownerLandlord,
    MoneyOwner.bank => ownerBank,
    MoneyOwner.shop => ownerShop,
    MoneyOwner.utilities => ownerUtilities,
    MoneyOwner.fuel => ownerFuel,
    MoneyOwner.self => ownerSelf,
    MoneyOwner.sadaqa => ownerSadaqa,
    MoneyOwner.other => ownerOther,
    MoneyOwner.unexplained => ownerUnexplained,
  };

  String member(Member m) =>
      m.displayName.isEmpty && m.isOwner ? memberOwnerDefault : m.displayName;
}

/// `09.10.2026`.
String formatDate(LocalDate d) =>
    '${d.day.toString().padLeft(2, '0')}.'
    '${d.month.toString().padLeft(2, '0')}.${d.year}';

/// Davr nomi: kalendar oyi bo'lsa — «oktabr 2026», aks holda sanalar.
String periodLabel(BuildContext context, DateRange p) {
  if (p.start.day == 1 && p.endExclusive.day == 1) {
    final locale = Localizations.localeOf(context).languageCode;
    return DateFormat.yMMMM(
      locale,
    ).format(DateTime(p.start.year, p.start.month));
  }
  final last = p.endExclusive.plusDays(-1);
  return '${formatDate(p.start)} — ${formatDate(last)}';
}

/// Nisbat foizi bir xonali kasr bilan, `double`siz: 1234 / 10000 → «12,3».
/// Bazis punktni foizga: 4000 → «40», 1234 → «12,3».
String percentLabel(int basisPoints) {
  final tenths = (basisPoints + 5) ~/ 10;
  final whole = tenths ~/ 10;
  final frac = tenths % 10;
  return frac == 0 ? '$whole' : '$whole,$frac';
}

/// «24» / «24,5» → bazis punkt (2400 / 2450); noto'g'ri — `null`.
int? parsePercentBp(String text) {
  final m = RegExp(r'^(\d{1,3})(?:[.,](\d{1,2}))?$').firstMatch(text.trim());
  if (m == null) return null;
  return int.parse(m[1]!) * 100 + int.parse((m[2] ?? '').padRight(2, '0'));
}

String ratioPercent(int part, int whole) {
  if (whole <= 0) return '0';
  final tenths = (part * 1000 + whole ~/ 2) ~/ whole;
  final rest = tenths % 10;
  return rest == 0 ? '${tenths ~/ 10}' : '${tenths ~/ 10},$rest';
}
