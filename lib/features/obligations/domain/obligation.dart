import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/local_date.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'obligation.freezed.dart';

/// Doimiy to'lov: ijara, kredit, kommunal (SPEC 2.5).
@freezed
abstract class Obligation with _$Obligation implements Synced {
  const factory Obligation({
    required SyncMeta meta,
    required String title,
    required ObligationKind kind,
    required Money amount,

    /// 1–31; qisqa oyda oyning oxirgi kuni.
    required int dayOfMonth,
    String? categoryId,
    String? debtId,
    @Default(true) bool isActive,
  }) = _Obligation;
}

/// Qarz (SPEC 2C.7). `creditorType == shop` — nasiya daftari.
@freezed
abstract class Debt with _$Debt implements Synced {
  const factory Debt({
    required SyncMeta meta,
    required CreditorType creditorType,
    required String creditorName,
    required Money principal,
    required Money remaining,
    Money? monthlyPayment,
    LocalDate? dueDate,
    String? reason,
    @Default(false) bool hasMarkup,
    // MVP-4 maydonlari.
    Money? totalPaid,
    Money? markupAmount,
    String? earlyRepaymentTerms,
    int? priority,
    String? note,
    // v9 (MVP_PLAN Vazifa 10).
    DebtScheduleType? scheduleType,
    int? termMonths,

    /// Yillik stavka (bp) — faqat bank krediti hisob-kitobi uchun.
    int? annualRateBp,
    LocalDate? startDate,

    /// Qarz oldidan friction javoblari (JSON, SPEC 2D.6).
    String? borrowCheckJson,
    // v10 (MVP_PLAN Vazifa 11).
    /// Yopish tartibi; `null` — standart (avval foizlilar).
    int? payoffOrder,

    /// Muddatidan oldin to'lash jarimasi (qo'shimcha to'lovdan, bp).
    int? prepayFeeBp,
  }) = _Debt;
}

abstract interface class ObligationRepository
    implements SyncedRepository<Obligation> {}

abstract interface class DebtRepository implements SyncedRepository<Debt> {
  Future<List<Debt>> listByCreditorType(String householdId, CreditorType type);
}
