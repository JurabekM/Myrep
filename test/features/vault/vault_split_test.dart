import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/features/expenses/data/drift_expense_repository.dart';
import 'package:baraka_daftari/features/expenses/domain/expense_service.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/income/domain/income_service.dart';
import 'package:baraka_daftari/features/vault/data/drift_vault_repository.dart';
import 'package:baraka_daftari/features/vault/domain/essential_spend.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';

Money som(int major) => Money.major(major, CurrencyCode.uzs);

class _Debt implements DebtReadiness {
  bool ready = true;

  @override
  Future<bool> isReady() async => ready;
}

void main() {
  late TestDb t;
  late ExpenseService expenses;
  late EssentialSpendService essentials;
  late IncomeService incomes;
  late VaultService vault;
  late _Debt debt;

  setUp(() {
    t = TestDb.open();
    final hh = DriftHouseholdRepository(t.db, t.clock);
    final exp = DriftExpenseRepository(t.db, t.clock);
    final cats = DriftCategoryRepository(t.db, t.clock);
    expenses = ExpenseService(
      households: hh,
      expenses: exp,
      categories: cats,
      templates: DriftExpenseTemplateRepository(t.db, t.clock),
      necessityChanges: DriftNecessityChangeRepository(t.db, t.clock),
      metaFactory: t.meta,
      clock: t.clock,
    );
    essentials = EssentialSpendService(
      households: hh,
      expenses: exp,
      categories: cats,
      clock: t.clock,
    );
    incomes = IncomeService(
      households: hh,
      incomes: DriftIncomeRepository(t.db, t.clock),
      metaFactory: t.meta,
      clock: t.clock,
    );
    debt = _Debt();
    vault = VaultService(
      households: hh,
      assets: DriftAssetRepository(t.db, t.clock),
      transactions: DriftVaultTransactionRepository(t.db, t.clock),
      rules: DriftAllocationRuleRepository(t.db, t.clock),
      metaFactory: t.meta,
      clock: t.clock,
      essentials: essentials.monthly,
      debtReadiness: debt,
    );
  });

  /// Iyul–sentabr (bugun 2026-10-09): har oy 2 000 000 zarur + 500 000
  /// kerak + 900 000 havas (havas zaxira maqsadiga kirmaydi).
  Future<void> seedThreeMonths() async {
    final cats = await expenses.categories();
    String cat(CategoryKey k) =>
        cats.firstWhere((c) => c.systemKey == k).meta.id;
    for (final m in [7, 8, 9]) {
      final at = DateTime.utc(2026, m, 10, 7);
      for (final (key, major) in [
        (CategoryKey.groceries, 2000000),
        (CategoryKey.children, 500000),
        (CategoryKey.cafe, 900000),
      ]) {
        await expenses.add(
          amount: som(major),
          categoryId: cat(key),
          channel: PaymentChannel.cash,
          spentAt: at,
        );
      }
    }
  }

  test('zaxira maqsadi: oxirgi 3 oy (zarur + kerak) × 6', () async {
    await seedThreeMonths();
    expect(await essentials.monthTotals(), [
      som(2500000),
      som(2500000),
      som(2500000),
    ]);
    final o = await vault.overview();
    expect(o.reserve.monthlyEssential, som(2500000));
    expect(o.reserve.target, som(15000000));
    expect(o.reserve.fromEstimate, isFalse);
  });

  test('maʼlumot kam — taxminiy summa ishlatiladi', () async {
    expect((await vault.overview()).reserve.needsEstimate, isTrue);
    await essentials.setEstimate(som(3000000));
    final o = await vault.overview();
    expect(o.reserve.monthlyEssential, som(3000000));
    expect(o.reserve.fromEstimate, isTrue);
  });

  test('ulush avval qorovulni toʻldiradi, ortgani oʻsadiganga', () async {
    await seedThreeMonths();
    await vault.setInitialBalance(som(14000000));
    final income = await incomes.add(
      amount: som(15000000),
      source: IncomeSource.salary,
      channel: PaymentChannel.card,
    );
    await vault.allocateFromIncome(income, som(1500000));
    final o = await vault.overview();
    expect(o.reserveBalance, som(15000000));
    expect(o.growthBalance, som(500000));
    expect(o.balance, som(15500000));
    expect(o.reserve.isFull, isTrue);
    expect(o.gate.isOpen, isTrue);
    // Ikkala yozuv ham tarixda.
    expect(o.history.where((x) => x.incomeId == income.meta.id), hasLength(2));
  });

  test('faol qarz bor — ortiqcha ham qorovulda qoladi', () async {
    await seedThreeMonths();
    debt.ready = false;
    await vault.setInitialBalance(som(14000000));
    await vault.depositManual(som(1500000));
    final o = await vault.overview();
    expect(o.reserveBalance, som(15500000));
    expect(o.growthBalance, const Money.zero(CurrencyCode.uzs));
    expect(o.gate.isOpen, isFalse);
  });

  test(
    'darvoza yopiq: oʻsadiganga kiritish — faqat ongli chetlab oʻtish bilan',
    () async {
      await seedThreeMonths();
      await vault.setInitialBalance(som(1000000));
      await expectLater(
        vault.depositGrowth(som(200000)),
        throwsA(
          isA<DomainRuleException>().having(
            (e) => e.code,
            'code',
            VaultService.errGateClosed,
          ),
        ),
      );
      expect((await vault.overview()).household.gateBypassedAt, isNull);

      await vault.depositGrowth(som(200000), bypassConfirmed: true);
      final o = await vault.overview();
      expect(o.growthBalance, som(200000));
      expect(o.household.gateBypassedAt, t.clock.nowUtc());
      expect(o.gate.bypassed, isTrue);
      expect(o.gate.isOpen, isTrue);
      expect(o.gate.ready, isFalse, reason: 'shartlar hali bajarilmagan');
    },
  );

  test('oʻsadigandan olishda favqulodda tasdiq shart emas', () async {
    await vault.depositGrowth(som(300000), bypassConfirmed: true);
    // PIN ruxsatisiz — PIN xatosi (favqulodda tasdigʻi emas).
    await expectLater(
      vault.withdraw(
        amount: som(1000),
        reason: 'Savdo',
        approval: null,
        from: VaultType.osadigan,
      ),
      throwsA(
        isA<DomainRuleException>().having(
          (e) => e.code,
          'code',
          VaultService.errPinRequired,
        ),
      ),
    );
  });
}
