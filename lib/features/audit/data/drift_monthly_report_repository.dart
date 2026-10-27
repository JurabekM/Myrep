import 'package:baraka_daftari/core/db/app_database.dart';
import 'package:baraka_daftari/core/db/synced_repository.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/local_date.dart';
import 'package:baraka_daftari/features/audit/domain/monthly_report.dart';
import 'package:drift/drift.dart';

class DriftMonthlyReportRepository
    extends
        DriftSyncedRepository<
          $MonthlyReportsTable,
          MonthlyReportRow,
          MonthlyReport
        >
    implements MonthlyReportRepository {
  DriftMonthlyReportRepository(super.db, super.clock);

  @override
  TableInfo<$MonthlyReportsTable, MonthlyReportRow> get table =>
      db.monthlyReports;

  @override
  String get entityName => 'monthly_report';

  @override
  List<OrderingTerm Function($MonthlyReportsTable)> get defaultOrder => [
    (t) => OrderingTerm.desc(t.periodStart),
  ];

  @override
  MonthlyReport fromRow(MonthlyReportRow r) {
    Money m(int minor) => Money(minor, r.currency);
    return MonthlyReport(
      meta: DriftSyncedRepository.metaOf(
        id: r.id,
        householdId: r.householdId,
        createdAt: r.createdAt,
        updatedAt: r.updatedAt,
        deletedAt: r.deletedAt,
        version: r.version,
      ),
      periodStart: r.periodStart,
      periodEnd: r.periodEnd,
      income: m(r.incomeMinor),
      obligations: m(r.obligationsMinor),
      expenses: m(r.expensesMinor),
      savings: m(r.savingsMinor),
      unexplained: m(r.unexplainedMinor),
      completedAt: r.completedAt.toUtc(),
    );
  }

  @override
  Insertable<MonthlyReportRow> toRow(MonthlyReport e) {
    final currency = e.income.currency;
    int minor(Money m) {
      if (m.currency != currency) {
        throw CurrencyMismatchException(currency, m.currency);
      }
      return m.minorUnits;
    }

    return MonthlyReportsCompanion.insert(
      id: e.meta.id,
      householdId: e.meta.householdId,
      createdAt: e.meta.createdAt,
      updatedAt: e.meta.updatedAt,
      deletedAt: Value(e.meta.deletedAt),
      version: Value(e.meta.version),
      periodStart: e.periodStart,
      periodEnd: e.periodEnd,
      currency: currency,
      incomeMinor: minor(e.income),
      obligationsMinor: minor(e.obligations),
      expensesMinor: minor(e.expenses),
      savingsMinor: minor(e.savings),
      unexplainedMinor: minor(e.unexplained),
      completedAt: e.completedAt,
    );
  }

  @override
  MonthlyReport withMeta(MonthlyReport e, SyncMeta meta) =>
      e.copyWith(meta: meta);

  @override
  Future<MonthlyReport?> findByPeriodStart(
    String householdId,
    LocalDate periodStart,
  ) async {
    final row =
        await (activeQuery(householdId)
              ..where(
                (t) => t.periodStart.equalsValue(periodStart),
              )
              ..limit(1))
            .getSingleOrNull();
    return row == null ? null : fromRow(row);
  }

  @override
  Future<MonthlyReport?> latest(String householdId) async {
    final row = await (activeQuery(householdId)..limit(1)).getSingleOrNull();
    return row == null ? null : fromRow(row);
  }

  @override
  Future<MonthlyReport?> earliest(String householdId) async {
    final row =
        await (db.select(table)
              ..where(
                (t) => t.householdId.equals(householdId) & t.deletedAt.isNull(),
              )
              ..orderBy([(t) => OrderingTerm.asc(t.periodStart)])
              ..limit(1))
            .getSingleOrNull();
    return row == null ? null : fromRow(row);
  }
}
