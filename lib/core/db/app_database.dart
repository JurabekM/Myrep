import 'package:baraka_daftari/core/db/app_database.steps.dart';
import 'package:baraka_daftari/core/db/converters.dart';
import 'package:baraka_daftari/core/db/journal_guard.dart';
import 'package:baraka_daftari/core/db/seed.dart';
import 'package:baraka_daftari/core/db/tables.dart';
import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/money/currency.dart';
import 'package:baraka_daftari/core/time/local_date.dart';
import 'package:baraka_daftari/features/agreements/data/agreement_migration.dart';
import 'package:drift/drift.dart';

export 'package:baraka_daftari/core/db/tables.dart';

part 'app_database.g.dart';

@DriftDatabase(
  tables: [
    Households,
    Members,
    Categories,
    Incomes,
    Expenses,
    Obligations,
    Debts,
    Assets,
    AssetSnapshots,
    VaultTransactions,
    AllocationRules,
    FxRates,
    MonthlyReports,
    DaftarPages,
    TaskCompletions,
    NecessityChanges,
    Habits,
    ExpenseTemplates,
    HavasLimits,
    LimitConsents,
    ScheduledTreats,
    Subscriptions,
    Envelopes,
    EnvelopePeriods,
    SavingsRescues,
    PriceItems,
    PricePoints,
    DebtInstallments,
    DebtPayments,
    Receivables,
    Goals,
    LoanSigners,
    DebtContributors,
    SellableItems,
    CeremonyPlans,
    CeremonyScenarios,
    CeremonyBudgetLines,
    CeremonyDiscussionMarks,
    GoalContributions,
    Partnerships,
    Partners,
    CapitalContributions,
    PartnershipContracts,
    BuyoutPayments,
    PartnershipConsents,
    VentureEntries,
    VenturePeriods,
    DistributionShares,
    Skills,
    VentureIdeas,
    IdeaCapexItems,
    OfferChecks,
    Agreements,
    AgreementVersions,
    JournalEntries,
    HourlySnapshots,
    LearningGoals,
    LearningItems,
    TeachingEntries,
  ],
)
class AppDatabase extends _$AppDatabase {
  AppDatabase(super.executor, {required SyncMetaFactory metaFactory})
    : _metaFactory = metaFactory;

  final SyncMetaFactory _metaFactory;

  /// Sxema versiyasi. Oshirilganda: `dart run drift_dev make-migrations`,
  /// `onUpgrade` ga qadam va migratsiya testi qo'shiladi.
  @override
  int get schemaVersion => 17;

  @override
  MigrationStrategy get migration => MigrationStrategy(
    onCreate: (m) async {
      await m.createAll();
      await seedDefaults(this, _metaFactory);
    },
    onUpgrade: stepByStep(
      from1To2: (m, schema) async {
        await m.addColumn(
          schema.allocationRules,
          schema.allocationRules.progressionOfferedAt,
        );
      },
      from2To3: (m, schema) async {
        await m.createTable(schema.monthlyReports);
      },
      from3To4: (m, schema) async {
        await m.createTable(schema.daftarPages);
        await m.createTable(schema.taskCompletions);
      },
      from4To5: (m, schema) async {
        await m.addColumn(schema.members, schema.members.pinRecord);
      },
      from5To6: (m, schema) async {
        await m.createTable(schema.necessityChanges);
        await m.createTable(schema.habits);
        await m.createTable(schema.expenseTemplates);
        await m.createTable(schema.havasLimits);
        await m.createTable(schema.limitConsents);
        await m.createTable(schema.scheduledTreats);
        await m.addColumn(schema.expenses, schema.expenses.habitId);
        await upgradeCategoriesToV6(this, _metaFactory);
      },
      from6To7: (m, schema) async {
        await m.createTable(schema.subscriptions);
        await m.createTable(schema.envelopes);
        await m.createTable(schema.envelopePeriods);
        await m.createTable(schema.savingsRescues);
        await m.addColumn(
          schema.households,
          schema.households.rescueBaselineStart,
        );
      },
      from7To8: (m, schema) async {
        await m.createTable(schema.priceItems);
        await m.createTable(schema.pricePoints);
        await m.addColumn(
          schema.households,
          schema.households.reserveMonthlyEstimateMinor,
        );
        await m.addColumn(schema.households, schema.households.gateBypassedAt);
        // SPEC 2C.3: mavjud «Kelajagim» to'liq qorovul pulga o'tadi
        // (tranzaksiyalar o'z aktivida qoladi — balans o'zgarmaydi).
        await customStatement(
          "UPDATE assets SET vault_type = 'qorovul' "
          "WHERE type = 'vault' AND vault_type IS NULL",
        );
      },
      from8To9: (m, schema) async {
        for (final c in [
          schema.debts.scheduleType,
          schema.debts.termMonths,
          schema.debts.annualRateBp,
          schema.debts.startDate,
          schema.debts.borrowCheck,
        ]) {
          await m.addColumn(schema.debts, c);
        }
        await m.createTable(schema.debtInstallments);
        await m.createTable(schema.debtPayments);
        await m.createTable(schema.receivables);
        await m.createTable(schema.goals);
        await m.createTable(schema.loanSigners);
        await backfillDebtInstallmentsV9(this, _metaFactory);
      },
      from9To10: (m, schema) async {
        for (final c in [
          schema.households.budgetMode,
          schema.households.recoveryNeedsBp,
          schema.households.recoveryDebtBp,
          schema.households.recoverySavingsBp,
          schema.households.freedShareOfferPending,
        ]) {
          await m.addColumn(schema.households, c);
        }
        await m.addColumn(schema.debts, schema.debts.payoffOrder);
        await m.addColumn(schema.debts, schema.debts.prepayFeeBp);
        await m.createTable(schema.debtContributors);
        await m.addColumn(schema.debtPayments, schema.debtPayments.feeMinor);
        await m.addColumn(
          schema.debtPayments,
          schema.debtPayments.contributorId,
        );
        await m.createTable(schema.sellableItems);
      },
      from10To11: (m, schema) async {
        await m.createTable(schema.ceremonyPlans);
        await m.createTable(schema.ceremonyScenarios);
        await m.createTable(schema.ceremonyBudgetLines);
        await m.createTable(schema.ceremonyDiscussionMarks);
        await m.createTable(schema.goalContributions);
      },
      from11To12: (m, schema) async {
        await m.createTable(schema.partnerships);
        await m.createTable(schema.partners);
        await m.createTable(schema.capitalContributions);
        await m.createTable(schema.partnershipContracts);
        await m.createTable(schema.buyoutPayments);
        await m.createTable(schema.partnershipConsents);
      },
      from12To13: (m, schema) async {
        await m.createTable(schema.ventureEntries);
        await m.createTable(schema.venturePeriods);
        await m.createTable(schema.distributionShares);
        await m.createTable(schema.skills);
        await m.createTable(schema.ventureIdeas);
        await m.createTable(schema.ideaCapexItems);
        await m.createTable(schema.offerChecks);
      },
      from13To14: (m, schema) async {
        await m.addColumn(schema.households, schema.households.onboardedAt);
        await m.addColumn(schema.households, schema.households.incomeKind);
        // Mavjud foydalanuvchi onboarding'dan qayta o'tkazilmaydi.
        await customStatement(
          'UPDATE households SET onboarded_at = created_at',
        );
      },
      from14To15: (m, schema) async {
        await m.createTable(schema.agreements);
        await m.createTable(schema.agreementVersions);
        await m.createTable(schema.journalEntries);
        // 9A dan oldingi tilxat va shartnomalar → Agreement + jurnal.
        await migrateLegacyAgreementsV15(this, _metaFactory);
      },
      from15To16: (m, schema) async {
        // 7-qonun (SPEC 2G.3, 2G.6): taklif tekshiruviga summa va qaror.
        final t = schema.offerChecks;
        await m.addColumn(t, t.amountMinor);
        await m.addColumn(t, t.currency);
        await m.addColumn(t, t.promisedMonthlyBp);
        await m.addColumn(t, t.advisor);
        await m.addColumn(t, t.decision);
        await m.addColumn(t, t.decidedAt);
      },
      from16To17: (m, schema) async {
        // 8-qonun (SPEC 2H): soat qiymati, o'qish maqsadi va yo'llari,
        // «o'rgatganlarim».
        await m.createTable(schema.hourlySnapshots);
        await m.createTable(schema.learningGoals);
        await m.createTable(schema.learningItems);
        await m.createTable(schema.teachingEntries);
      },
    ),
    beforeOpen: (details) async {
      await customStatement('PRAGMA foreign_keys = ON');
      // Jurnal append-only triggerlari (yangi baza, migratsiya, tiklash).
      if (details.versionNow >= 15) await ensureJournalGuard(this);
    },
  );
}
