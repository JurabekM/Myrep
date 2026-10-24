import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/security/pin/pin_models.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'household.freezed.dart';

/// Uy xo'jaligi (oila). Byudjet davrlari shu yerdagi sozlamalar bilan
/// hisoblanadi.
@freezed
abstract class Household with _$Household implements Synced {
  const factory Household({
    required SyncMeta meta,
    String? name,
    @Default(CurrencyCode.uzs) CurrencyCode baseCurrency,
    @Default(DateTime.friday) int weekAnchor,
    @Default(1) int monthStartDay,

    /// «Qutqarilgan pul» bazaviy oyi boshi; `null` — birinchi audit oyi.
    LocalDate? rescueBaselineStart,

    /// Oylik zarur + kerak taxminiy summasi (zaxira maqsadi uchun, v8).
    Money? reserveMonthlyEstimate,

    /// Tayyorgarlik darvozasi ongli chetlab o'tilgan vaqt (UTC, v8).
    DateTime? gateBypassedAt,

    /// Byudjet rejimi va «Qarzdan chiqish» ulushlari (v10, SPEC 2D.1).
    @Default(BudgetMode.standard) BudgetMode budgetMode,
    @Default(RecoverySplit.standard) RecoverySplit recoverySplit,

    /// Rejim odatiyga qaytgach bo'shagan 20 % ni yo'naltirish taklifi.
    @Default(false) bool freedShareOfferPending,

    /// Onboarding yakunlangan vaqt (UTC, v14) va daromad turi.
    DateTime? onboardedAt,
    IncomeKind? incomeKind,
  }) = _Household;

  const Household._();

  BudgetCalendar get calendar =>
      BudgetCalendar(weekAnchor: weekAnchor, monthStartDay: monthStartDay);
}

/// Oila a'zosi — har yozuvda «kim» belgisi (SPEC 2.3, oilaviy rejim).
@freezed
abstract class Member with _$Member implements Synced {
  const factory Member({
    required SyncMeta meta,
    required String displayName,
    @Default(MemberRole.adult) MemberRole role,
    @Default(false) bool isOwner,

    /// Ixtiyoriy shaxsiy PIN hosilasi (oilaviy rozilik uchun).
    PinRecord? personalPin,
  }) = _Member;

  const Member._();

  bool get hasPersonalPin => personalPin != null;
}

abstract interface class HouseholdRepository
    implements SyncedRepository<Household> {
  /// Qurilmadagi joriy uy xo'jaligi (MVP-1 da bitta, seed yaratadi).
  Future<Household> current();
}

abstract interface class MemberRepository implements SyncedRepository<Member> {}

/// «Qarzdan chiqish» rejimi ulushlari (SPEC 2D.1), bazis punktda:
/// ro'zg'or (majburiy qarz to'lovlari shu ichida) / qo'shimcha qarz to'lovi /
/// «Kelajagim». Standart 70 / 20 / 10.
@immutable
final class RecoverySplit {
  const RecoverySplit({
    required this.needsBp,
    required this.debtBp,
    required this.savingsBp,
  });

  static const standard = RecoverySplit(
    needsBp: 7000,
    debtBp: 2000,
    savingsBp: 1000,
  );

  /// Jamg'arma ulushi bundan kam bo'lmaydi (1 %) — 0 ga tushirilmaydi.
  static const minSavingsBp = 100;

  final int needsBp;
  final int debtBp;
  final int savingsBp;

  int get totalBp => needsBp + debtBp + savingsBp;

  /// Jami 100 %, har biri manfiy emas, jamg'arma ≥ 1 %.
  bool get isValid =>
      needsBp >= 0 &&
      debtBp >= 0 &&
      savingsBp >= minSavingsBp &&
      totalBp == 10000;

  @override
  bool operator ==(Object other) =>
      other is RecoverySplit &&
      other.needsBp == needsBp &&
      other.debtBp == debtBp &&
      other.savingsBp == savingsBp;

  @override
  int get hashCode => Object.hash(needsBp, debtBp, savingsBp);

  @override
  String toString() => 'RecoverySplit($needsBp/$debtBp/$savingsBp)';
}
