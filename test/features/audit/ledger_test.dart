import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/domain/sync_meta.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/audit/data/drift_monthly_report_repository.dart';
import 'package:baraka_daftari/features/audit/domain/ledger_service.dart';
import 'package:baraka_daftari/features/audit/domain/month_ledger.dart';
import 'package:baraka_daftari/features/debts/data/drift_debt_repositories.dart';
import 'package:baraka_daftari/features/expenses/data/drift_expense_repository.dart';
import 'package:baraka_daftari/features/expenses/domain/expense.dart';
import 'package:baraka_daftari/features/expenses/domain/expense_service.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/domain/household_service.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:baraka_daftari/features/income/domain/income_service.dart';
import 'package:baraka_daftari/features/obligations/data/drift_obligation_repository.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation.dart';
import 'package:baraka_daftari/features/obligations/domain/obligation_service.dart';
import 'package:baraka_daftari/features/vault/data/drift_vault_repository.dart';
import 'package:baraka_daftari/features/vault/domain/vault.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';

const CurrencyCode uzs = CurrencyCode.uzs;
Money som(int major) => Money.major(major, uzs);

/// Toshkent vaqtida berilgan payt → UTC.
DateTime tk(int y, int m, int d, [int h = 12]) =>
    DateTime.utc(y, m, d, h).subtract(Tashkent.utcOffset);

SyncMeta meta([String id = 'x']) => SyncMeta(
  id: id,
  householdId: 'h',
  createdAt: DateTime.utc(2026),
  updatedAt: DateTime.utc(2026),
);

Income income(int major, DateTime at) => Income(
  meta: meta(),
  amount: som(major),
  source: IncomeSource.dailyWork,
  channel: PaymentChannel.cash,
  receivedAt: at,
);

Expense expense(int major, String category, DateTime at) => Expense(
  meta: meta(),
  amount: som(major),
  categoryId: category,
  channel: PaymentChannel.cash,
  spentAt: at,
);

Obligation obligation(
  int major,
  String? category, {
  ObligationKind kind = ObligationKind.rent,
  bool active = true,
  int day = 25,
}) => Obligation(
  meta: meta(),
  title: 'x',
  kind: kind,
  amount: som(major),
  dayOfMonth: day,
  categoryId: category,
  isActive: active,
);

VaultTransaction vtx(
  int major,
  DateTime at, {
  VaultTransactionType type = VaultTransactionType.deposit,
  VaultTransactionReason reason = VaultTransactionReason.incomeShare,
}) => VaultTransaction(
  meta: meta(),
  vaultAssetId: 'v',
  type: type,
  amount: som(major),
  reason: reason,
  reasonNote: type == VaultTransactionType.withdraw ? 'x' : null,
  occurredAt: at,
);

void main() {
  final october = const BudgetCalendar().monthOf(LocalDate(2026, 10, 15));

  MonthLedger ledger({
    List<Income> incomes = const [],
    List<Expense> expenses = const [],
    List<Obligation> obligations = const [],
    List<VaultTransaction> vault = const [],
    DateRange? period,
  }) => buildMonthLedger(
    period: period ?? october,
    currency: uzs,
    incomes: incomes,
    expenses: expenses,
    obligations: obligations,
    vaultTransactions: vault,
  );

  group('izohsiz qolgan summa', () {
    test(
      '«somsaga bir million»: daromad − (majburiyat + xarajat + jamgʻarma)',
      () {
        final l = ledger(
          incomes: [income(8000000, tk(2026, 10, 5))],
          expenses: [expense(2500000, 'food', tk(2026, 10, 10))],
          obligations: [obligation(3000000, 'rent')],
          vault: [vtx(500000, tk(2026, 10, 6))],
        );
        // 8 000 000 − (3 000 000 + 2 500 000 + 500 000) = 2 000 000
        expect(l.unexplained, som(2000000));
        expect(l.obligationsUnrecorded, som(3000000));
      },
    );

    test('manfiy natija: yozilgan chiqim daromaddan koʻp', () {
      final l = ledger(
        incomes: [income(3000000, tk(2026, 10, 5))],
        expenses: [expense(2000000, 'food', tk(2026, 10, 10))],
        obligations: [obligation(1500000, 'rent')],
      );
      expect(l.unexplained, som(-500000));
      expect(l.unexplained.isNegative, isTrue);
    });

    test('hech narsa yozilmagan — nol', () {
      expect(ledger().unexplained, som(0));
    });

    test('majburiyat oʻz kategoriyasida yozilsa ikki marta sanalmaydi', () {
      final l = ledger(
        incomes: [income(8000000, tk(2026, 10, 5))],
        expenses: [expense(3000000, 'rent', tk(2026, 10, 25))],
        obligations: [obligation(3000000, 'rent')],
      );
      expect(l.obligations.single.recorded, som(3000000));
      expect(l.obligations.single.remainder, som(0));
      expect(l.unexplained, som(5000000));
    });

    test('qisman yozilgan majburiyat — faqat qoldigʻi qoʻshiladi', () {
      final l = ledger(
        incomes: [income(8000000, tk(2026, 10, 5))],
        expenses: [expense(1000000, 'credit', tk(2026, 10, 3))],
        obligations: [
          obligation(1500000, 'credit', kind: ObligationKind.credit, day: 5),
          obligation(700000, 'credit', kind: ObligationKind.credit, day: 20),
        ],
      );
      // 1 000 000 birinchi kreditni qisman qoplaydi: qoldiq 500 000 + 700 000.
      expect(l.obligationsUnrecorded, som(1200000));
      expect(l.unexplained, som(8000000 - 1000000 - 1200000));
    });

    test('faol boʻlmagan majburiyat hisobga olinmaydi', () {
      final l = ledger(obligations: [obligation(1000, 'rent', active: false)]);
      expect(l.obligations, isEmpty);
    });

    test('jamgʻarma: avval yigʻilgan pul kirmaydi, olingan pul ayiriladi', () {
      final l = ledger(
        incomes: [income(1000000, tk(2026, 10, 2))],
        vault: [
          vtx(5000000, tk(2026, 10, 1), reason: VaultTransactionReason.initial),
          vtx(100000, tk(2026, 10, 2)),
          vtx(
            30000,
            tk(2026, 10, 9),
            type: VaultTransactionType.withdraw,
            reason: VaultTransactionReason.withdrawal,
          ),
        ],
      );
      expect(l.savingsDeposited, som(100000));
      expect(l.savingsWithdrawn, som(30000));
      expect(l.netSavings, som(70000));
      expect(l.unexplained, som(930000));
    });

    test('boshqa valyutadagi yozuvlar hisobga olinmaydi', () {
      final l = ledger(
        incomes: [
          income(100, tk(2026, 10, 2)),
          Income(
            meta: meta(),
            amount: Money.major(50, CurrencyCode.usd),
            source: IncomeSource.other,
            channel: PaymentChannel.card,
            receivedAt: tk(2026, 10, 2),
          ),
        ],
      );
      expect(l.income, som(100));
    });
  });

  group('oy chegarasi — oylik kuni sozlanadi', () {
    test(
      'standart: 1-sana 00:00 Toshkent kiradi, keyingi oy 1-sana kirmaydi',
      () {
        final l = ledger(
          incomes: [
            income(1, tk(2026, 10, 1, 0)), // kiradi
            income(10, tk(2026, 9, 30, 23)), // kirmaydi
            income(100, tk(2026, 10, 31, 23)), // kiradi
            income(1000, tk(2026, 11, 1, 0)), // kirmaydi
          ],
        );
        expect(l.income, som(101));
      },
    );

    test('oylik 10-sanada: davr 10-sentabr … 9-oktabr', () {
      final period = const BudgetCalendar(
        monthStartDay: 10,
      ).previousMonthOf(LocalDate(2026, 10, 15));
      expect(period.start, LocalDate(2026, 9, 10));
      expect(period.endExclusive, LocalDate(2026, 10, 10));
      final l = ledger(
        period: period,
        incomes: [
          income(1, tk(2026, 9, 9)), // oldingi davr
          income(10, tk(2026, 9, 10, 0)), // kiradi
          income(100, tk(2026, 10, 9, 23)), // kiradi
          income(1000, tk(2026, 10, 10, 0)), // keyingi davr
        ],
      );
      expect(l.income, som(110));
    });
  });

  group('«Kimning puli?»', () {
    test('egalar boʻyicha taqsimot, izohsiz va oʻzingiz bilan', () {
      final l = ledger(
        incomes: [income(10000000, tk(2026, 10, 1))],
        expenses: [
          expense(2000000, 'food', tk(2026, 10, 2)),
          expense(300000, 'gas', tk(2026, 10, 2)),
          expense(100000, 'sadaqa', tk(2026, 10, 2)),
          expense(50000, 'custom', tk(2026, 10, 2)),
        ],
        obligations: [
          obligation(3000000, 'rent'),
          obligation(1500000, null, kind: ObligationKind.credit),
          obligation(400000, null, kind: ObligationKind.utility),
        ],
        vault: [vtx(1000000, tk(2026, 10, 1))],
      );
      final w = whoseMoney(l, {
        'food': CategoryKey.groceries,
        'gas': CategoryKey.fuel,
        'sadaqa': CategoryKey.sadaqa,
        'custom': null,
        'rent': CategoryKey.rent,
      });
      expect(w[MoneyOwner.landlord], som(3000000));
      expect(w[MoneyOwner.bank], som(1500000));
      expect(w[MoneyOwner.shop], som(2000000));
      expect(w[MoneyOwner.utilities], som(400000));
      expect(w[MoneyOwner.fuel], som(300000));
      expect(w[MoneyOwner.self], som(1000000));
      expect(w[MoneyOwner.sadaqa], som(100000));
      expect(w[MoneyOwner.other], som(50000));
      expect(w[MoneyOwner.unexplained], som(1650000));
      expect(Money.sum(w.values, uzs), som(10000000));
      expect(w.keys.toList(), [
        MoneyOwner.landlord,
        MoneyOwner.bank,
        MoneyOwner.shop,
        MoneyOwner.utilities,
        MoneyOwner.fuel,
        MoneyOwner.self,
        MoneyOwner.sadaqa,
        MoneyOwner.other,
        MoneyOwner.unexplained,
      ]);
    });

    test('manfiy izohsiz summa boʻlak sifatida chiqmaydi', () {
      final l = ledger(
        incomes: [income(100, tk(2026, 10, 1))],
        expenses: [expense(300, 'food', tk(2026, 10, 2))],
      );
      final w = whoseMoney(l, {'food': CategoryKey.groceries});
      expect(w.containsKey(MoneyOwner.unexplained), isFalse);
      expect(w[MoneyOwner.shop], som(300));
    });
  });

  group('servislar (in-memory Drift)', () {
    late TestDb t;
    late LedgerService ledgerService;
    late ObligationService obligations;
    late ExpenseService expenses;
    late IncomeService incomes;
    late VaultService vault;
    late HouseholdService households;

    setUp(() {
      t = TestDb.open();
      final hh = DriftHouseholdRepository(t.db, t.clock);
      final cats = DriftCategoryRepository(t.db, t.clock);
      ledgerService = LedgerService(
        households: hh,
        incomes: DriftIncomeRepository(t.db, t.clock),
        expenses: DriftExpenseRepository(t.db, t.clock),
        categories: cats,
        obligations: DriftObligationRepository(t.db, t.clock),
        assets: DriftAssetRepository(t.db, t.clock),
        vaultTransactions: DriftVaultTransactionRepository(t.db, t.clock),
        reports: DriftMonthlyReportRepository(t.db, t.clock),
        metaFactory: t.meta,
        clock: t.clock,
      );
      obligations = ObligationService(
        households: hh,
        obligations: DriftObligationRepository(t.db, t.clock),
        debts: DriftDebtRepository(t.db, t.clock),
        categories: cats,
        installments: DriftDebtInstallmentRepository(t.db, t.clock),
        payments: DriftDebtPaymentRepository(t.db, t.clock),
        metaFactory: t.meta,
      );
      expenses = ExpenseService(
        households: hh,
        expenses: DriftExpenseRepository(t.db, t.clock),
        categories: cats,
        templates: DriftExpenseTemplateRepository(t.db, t.clock),
        necessityChanges: DriftNecessityChangeRepository(t.db, t.clock),
        metaFactory: t.meta,
        clock: t.clock,
      );
      incomes = IncomeService(
        households: hh,
        incomes: DriftIncomeRepository(t.db, t.clock),
        metaFactory: t.meta,
        clock: t.clock,
      );
      vault = VaultService(
        households: hh,
        assets: DriftAssetRepository(t.db, t.clock),
        transactions: DriftVaultTransactionRepository(t.db, t.clock),
        rules: DriftAllocationRuleRepository(t.db, t.clock),
        metaFactory: t.meta,
        clock: t.clock,
      );
      households = HouseholdService(
        households: hh,
        members: DriftMemberRepository(t.db, t.clock),
        metaFactory: t.meta,
      );
    });

    Future<String> category(CategoryKey key) async =>
        (await expenses.categories())
            .firstWhere((c) => c.systemKey == key)
            .meta
            .id;

    test('bosh ekran KPIʼlari repository maʼlumotlariga mos', () async {
      final inc = await incomes.add(
        amount: som(8000000),
        source: IncomeSource.salary,
        channel: PaymentChannel.card,
      );
      await vault.allocateFromIncome(inc, som(800000));
      await vault.setInitialBalance(som(2000000));
      await expenses.add(
        amount: som(1500000),
        categoryId: await category(CategoryKey.groceries),
        channel: PaymentChannel.cash,
      );
      await obligations.addObligation(
        title: 'Ijara',
        kind: ObligationKind.rent,
        amount: som(3000000),
        dayOfMonth: 25,
      );

      final k = await ledgerService.homeKpis();
      expect(k.paidToSelf, som(800000));
      expect(k.vaultBalance, som(2800000));
      expect(k.habit.currentStreakWeeks, 1);
      expect(k.income, som(8000000));
      // 8 000 000 − (3 000 000 + 1 500 000 + 800 000)
      expect(k.monthResult, som(2700000));
      expect(k.lastAudit, isNull);
    });

    test(
      'majburiyat toʻlovi xarajat sifatida yozilsa KPI ikki marta ayirmaydi',
      () async {
        await incomes.add(
          amount: som(5000000),
          source: IncomeSource.salary,
          channel: PaymentChannel.card,
        );
        await obligations.addObligation(
          title: 'Ijara',
          kind: ObligationKind.rent,
          amount: som(2000000),
          dayOfMonth: 1,
        );
        await expenses.add(
          amount: som(2000000),
          categoryId: await category(CategoryKey.rent),
          channel: PaymentChannel.cash,
        );
        expect((await ledgerService.homeKpis()).monthResult, som(3000000));
      },
    );

    test(
      'audit: oʻtgan oy, izohsizni mayda xarajat deb belgilash, yakun',
      () async {
        final prev = await ledgerService.previousPeriod();
        await incomes.add(
          amount: som(4000000),
          source: IncomeSource.dailyWork,
          channel: PaymentChannel.cash,
          receivedAt: ledgerService.instantInside(prev),
        );
        await expenses.add(
          amount: som(1000000),
          categoryId: await category(CategoryKey.groceries),
          channel: PaymentChannel.cash,
          spentAt: ledgerService.instantInside(prev),
        );
        expect((await ledgerService.ledgerFor(prev)).unexplained, som(3000000));

        final small = await ledgerService.markUnexplainedAsDailySmall(prev);
        expect(small.amount, som(3000000));
        expect((await ledgerService.ledgerFor(prev)).unexplained, som(0));
        expect(
          () => ledgerService.markUnexplainedAsDailySmall(prev),
          throwsA(isA<DomainRuleException>()),
        );

        final report = await ledgerService.completeAudit(prev);
        expect(report.periodStart, prev.start);
        expect(report.expenses, som(4000000));
        expect(report.unexplained, som(0));
        // Qayta yakunlash — yangi yozuv emas, yangilanadi.
        final again = await ledgerService.completeAudit(prev);
        expect(again.meta.id, report.meta.id);
        expect(again.meta.version, 2);
        expect(
          (await ledgerService.homeKpis()).lastAudit?.meta.id,
          report.meta.id,
        );
      },
    );

    test('nasiya: qoʻshish, qisman toʻlash, ortiqcha toʻlov rad', () async {
      final d = await obligations.addNasiya(
        shopName: 'Mahalla doʻkoni',
        amount: som(450000),
        dueDate: LocalDate(2026, 11, 1),
      );
      final paid = await obligations.payNasiya(d, som(150000));
      expect(paid.remaining, som(300000));
      expect(paid.totalPaid, som(150000));
      expect(
        () => obligations.payNasiya(paid, som(300001)),
        throwsA(isA<DomainRuleException>()),
      );
      expect((await obligations.nasiya()).single.remaining, som(300000));
    });

    test(
      'majburiyat turi oʻz kategoriyasiga bogʻlanadi; notoʻgʻri qiymatlar rad',
      () async {
        final o = await obligations.addObligation(
          title: ' Kommunal ',
          kind: ObligationKind.utility,
          amount: som(400000),
          dayOfMonth: 31,
        );
        expect(o.title, 'Kommunal');
        expect(o.categoryId, await category(CategoryKey.utilities));
        for (final bad in [
          () => obligations.addObligation(
            title: '',
            kind: ObligationKind.rent,
            amount: som(1),
            dayOfMonth: 1,
          ),
          () => obligations.addObligation(
            title: 'x',
            kind: ObligationKind.rent,
            amount: som(1),
            dayOfMonth: 32,
          ),
        ]) {
          expect(bad, throwsA(isA<DomainRuleException>()));
        }
      },
    );

    test(
      'oila aʼzolari: egasi avtomatik, egasini oʻchirib boʻlmaydi',
      () async {
        final first = await households.members(ownerName: 'Men');
        expect(first.single.isOwner, isTrue);
        await households.addMember('Gulnora', MemberRole.adult);
        final list = await households.members(ownerName: 'Men');
        expect(list.map((m) => m.displayName), ['Men', 'Gulnora']);
        expect(
          () => households.remove(list.first),
          throwsA(isA<DomainRuleException>()),
        );
        await households.remove(list.last);
        expect(await households.members(ownerName: 'Men'), hasLength(1));
      },
    );

    test('oylik kuni sozlamasi davrni oʻzgartiradi', () async {
      await households.setMonthStartDay(10);
      final p = await ledgerService.currentPeriod();
      expect(p.start.day, 10);
      expect(
        () => households.setMonthStartDay(0),
        throwsA(isA<DomainRuleException>()),
      );
    });
  });
}
