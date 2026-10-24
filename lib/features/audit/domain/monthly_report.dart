import 'package:baraka_daftari/core/domain/repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/local_date.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'monthly_report.freezed.dart';

/// Oylik audit yakuni (SPEC 5: `MonthlyReport`).
@freezed
abstract class MonthlyReport with _$MonthlyReport implements Synced {
  const factory MonthlyReport({
    required SyncMeta meta,
    required LocalDate periodStart,
    required LocalDate periodEnd,
    required Money income,
    required Money obligations,
    required Money expenses,
    required Money savings,
    required Money unexplained,

    /// UTC.
    required DateTime completedAt,
  }) = _MonthlyReport;
}

abstract interface class MonthlyReportRepository
    implements SyncedRepository<MonthlyReport> {
  Future<MonthlyReport?> findByPeriodStart(
    String householdId,
    LocalDate periodStart,
  );

  /// Eng so'nggi yakunlangan audit.
  Future<MonthlyReport?> latest(String householdId);

  /// Birinchi audit («Qutqarilgan pul» bazaviy oyi).
  Future<MonthlyReport?> earliest(String householdId);
}
