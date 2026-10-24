import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/debts/data/drift_debt_repositories.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/debts/domain/recovery_service.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/household/domain/household.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/income/domain/income_service.dart';
import 'package:baraka_daftari/features/obligations/data/drift_obligation_repository.dart';
import 'package:baraka_daftari/features/vault/data/drift_vault_repository.dart';
import 'package:baraka_daftari/features/vault/domain/vault_service.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';

const CurrencyCode uzs = CurrencyCode.uzs;
Money som(int major) => Money.major(major, uzs);

Matcher rule(String code) => throwsA(
  isA<DomainRuleException>().having((e) => e.code, 'code', code),
);

void main() {
  late TestDb t;
  late DriftHouseholdRepository households;
  late DebtService debts;
  late RecoveryService recovery;
  late VaultService vault;
  late IncomeService incomes;
  late DebtDataReadiness readiness;

  setUp(() {
    t = TestDb.open();
    households = DriftHouseholdRepository(t.db, t.clock);
    final repo = DriftDebtRepository(t.db, t.clock);
    final incomeRepo = DriftIncomeRepository(t.db, t.clock);
    debts = DebtService(
      households: households,
      debts: repo,
      installments: DriftDebtInstallmentRepository(t.db, t.clock),
      payments: DriftDebtPaymentRepository(t.db, t.clock),
      receivables: DriftReceivableRepository(t.db, t.clock),
      goals: DriftGoalRepository(t.db, t.clock),
      contributors: DriftDebtContributorRepository(t.db, t.clock),
      sellables: DriftSellableItemRepository(t.db, t.clock),
      incomes: incomeRepo,
      metaFactory: t.meta,
      clock: t.clock,
    );
    readiness = DebtDataReadiness(repo, households);
    vault = VaultService(
      households: households,
      assets: DriftAssetRepository(t.db, t.clock),
      transactions: DriftVaultTransactionRepository(t.db, t.clock),
      rules: DriftAllocationRuleRepository(t.db, t.clock),
      metaFactory: t.meta,
      clock: t.clock,
      debtReadiness: readiness,
    );
    recovery = RecoveryService(
      households: households,
      debts: debts,
      vault: vault,
    );
    incomes = IncomeService(
      households: households,
      incomes: incomeRepo,
      metaFactory: t.meta,
      clock: t.clock,
    );
  });

  /// Iyul–sentabr: oyiga 10 000 000 so'm daromad.
  Future<void> seedIncome() async {
    for (final m in [7, 8, 9]) {
      await incomes.add(
        amount: som(10000000),
        source: IncomeSource.salary,
        channel: PaymentChannel.card,
        receivedAt: DateTime.utc(2026, m, 5, 7),
      );
    }
  }

  Future<DebtView> akmal() => debts.add(
    creditorType: CreditorType.bank,
    creditorName: 'Avtokredit',
    principal: som(39000000),
    scheduleType: DebtScheduleType.annuity,
    termMonths: 14,
    annualRateBp: 2400,
  );

  Future<DebtView> relative(int major) => debts.add(
    creditorType: CreditorType.relative,
    creditorName: 'Togʻam',
    principal: som(major),
    scheduleType: DebtScheduleType.manual,
    manual: [
      Installment(
        dueOn: LocalDate(2026, 12, 1),
        amount: som(major),
        interest: som(0),
      ),
    ],
  );

  group('70 / 20 / 10 ulushlari', () {
    test('jamgʻarma ulushini 0 qilishga urinish toʻxtatiladi', () async {
      await akmal();
      await expectLater(
        recovery.enable(
          const RecoverySplit(needsBp: 8000, debtBp: 2000, savingsBp: 0),
        ),
        rule(RecoveryService.errSavingsRequired),
      );
      await expectLater(
        recovery.enable(
          const RecoverySplit(needsBp: 7950, debtBp: 2000, savingsBp: 50),
        ),
        rule(RecoveryService.errSavingsRequired),
        reason: '1 % dan kam ham yoʻq',
      );
      expect(
        (await households.current()).budgetMode,
        BudgetMode.standard,
        reason: 'rad etilgan sozlama saqlanmaydi',
      );
      await expectLater(
        recovery.enable(
          const RecoverySplit(needsBp: 7000, debtBp: 2000, savingsBp: 500),
        ),
        rule(RecoveryService.errSplitInvalid),
      );
      await recovery.enable(
        const RecoverySplit(needsBp: 7900, debtBp: 2000, savingsBp: 100),
      );
      expect((await households.current()).recoverySplit.savingsBp, 100);
    });

    test(
      'qarz yoʻq boʻlsa rejim yoqilmaydi; qarz boʻlsa taklif qilinadi',
      () async {
        await expectLater(recovery.enable(), rule(RecoveryService.errNoDebts));
        expect((await recovery.state()).offerRecovery, isFalse);
        await akmal();
        expect((await recovery.state()).offerRecovery, isTrue);
      },
    );

    test(
      'yoqilganda: taqsimot, 20 % qoʻshimcha toʻlov, «Kelajagim» 10 %',
      () async {
        await seedIncome();
        final v = await akmal();
        expect((await vault.overview()).rule.basisPoints, 500);
        await recovery.enable();
        final s = await recovery.state();
        expect(s.isActive, isTrue);
        expect(s.offerRecovery, isFalse);
        expect(s.monthlyExtra, som(2000000));
        final b = s.budget!;
        expect(b.needs, som(7000000));
        expect(b.debtExtra, som(2000000));
        expect(b.savings, som(1000000));
        // Majburiy oylik to'lov 70 % ichida (ZARUR).
        expect(b.mandatoryDebt, v.plan.first.amount);
        expect(b.household, som(7000000) - v.plan.first.amount);
        expect(b.mandatoryExceedsNeeds, isFalse);
        expect(
          (await vault.overview()).rule.basisPoints,
          1000,
          reason: '5 % → 10 %',
        );
      },
    );
  });

  group('rejimning avtomatik STANDARD ga qaytishi', () {
    test('hamma qarz yopilganda qaytadi va 20 % taklif qilinadi', () async {
      await seedIncome();
      final bank = await akmal();
      final rel = await relative(1000000);
      await recovery.enable();

      final r1 = await debts.pay(
        bank.debt,
        (await debts.view(bank.debt)).payoffAmount,
      );
      expect(r1.closed, isTrue);
      expect(r1.modeReturned, isFalse, reason: 'qarindoshdan qarz qoldi');
      expect((await recovery.state()).isActive, isTrue);

      final r2 = await debts.pay(rel.debt, som(1000000));
      expect(r2.closed, isTrue);
      expect(r2.modeReturned, isTrue);
      final h = await households.current();
      expect(h.budgetMode, BudgetMode.standard);
      expect(h.freedShareOfferPending, isTrue);
      final s = await recovery.state();
      expect(s.freedOffer, isTrue);
      expect(s.monthlyExtra, som(0));

      // Bo'shagan 20 % «Kelajagim»ga: 10 % + 20 % = 30 %.
      final ruleAfter = await recovery.acceptFreedShare();
      expect(ruleAfter!.basisPoints, 3000);
      expect((await recovery.state()).freedOffer, isFalse);
    });

    test('odatiy rejimda qarz yopilsa hech narsa oʻzgarmaydi', () async {
      final rel = await relative(500000);
      final r = await debts.pay(rel.debt, som(500000));
      expect(r.closed, isTrue);
      expect(r.modeReturned, isFalse);
      expect((await households.current()).freedShareOfferPending, isFalse);
    });

    test('yopilgan qarzning oylik toʻlovi «Kelajagim»ga', () async {
      await seedIncome();
      final rel = await relative(500000);
      final r = await debts.pay(rel.debt, som(500000));
      expect(r.freedMonthly, som(500000));
      // 500 000 / 10 000 000 = 5 % → 5 % + 5 % = 10 %.
      final rule = await recovery.redirectFreed(r.freedMonthly!);
      expect(rule!.basisPoints, 1000);
    });
  });

  group('qoʻshimcha toʻlov (DebtService)', () {
    test(
      'navbatdagi toʻlov + 2 mln: reja qayta quriladi, foiz tejaladi',
      () async {
        final v = await akmal();
        final before = v.cost.totalPaid;
        final r = await debts.pay(v.debt, v.plan.first.amount + som(5000000));
        expect(r.payments, hasLength(2));
        expect(r.payments.first.isPrepayment, isFalse);
        expect(r.payments.last.isPrepayment, isTrue);
        expect(r.payments.last.amount, som(5000000));

        final after = await debts.view(r.debt);
        expect(after.plan.length, lessThan(14));
        expect(after.debt.remaining, after.remainingPlanned);
        expect(after.cost.totalPaid < before, isTrue, reason: 'foiz tejaldi');
        expect(after.next!.dueOn, v.plan[1].dueOn);
        expect(after.debtFreeOn!.isBefore(v.plan.last.dueOn), isTrue);
        // Qoldiq: asosiy qarzdan to'langan qism ayirilgan.
        final principalLeft = Money.sum(
          after.remainingRows.map((x) => x.principal),
          uzs,
        );
        expect(
          principalLeft,
          som(39000000) - v.plan.first.principal - som(5000000),
        );
      },
    );

    test('muddatidan oldin toʻlash jarimasi ushlanadi', () async {
      final v = await akmal();
      final d = await debts.setPrepayFee(v.debt, 200);
      final r = await debts.pay(d, v.plan.first.amount + som(1020000));
      final extra = r.payments.last;
      expect(extra.fee, som(20000));
      expect(extra.net, som(1000000));
    });

    test('toʻlash summasi qarzni yopishdan oshmaydi', () async {
      final v = await akmal();
      await expectLater(
        debts.pay(v.debt, v.payoffAmount + const Money(1, uzs)),
        rule(DebtService.errPaymentTooBig),
      );
      expect(v.payoffAmount < v.debt.remaining, isTrue);
    });
  });

  test('sotilgan buyum puli bir bosishda qarzga', () async {
    final v = await akmal();
    // Navbatdagi to'lovning yarmi to'langan — qisman qator o'z holicha qoladi.
    final half = Money(v.plan.first.amount.minorUnits ~/ 2, uzs);
    await debts.pay(v.debt, half);
    final item = await debts.addSellable('Eski televizor', som(1500000));
    expect(item.status, SellableStatus.listed);
    await expectLater(
      debts.applySale(item, v.debt),
      rule(DebtService.errNothingToApply),
    );
    final sold = await debts.markSold(item, som(1200000));
    expect(sold.awaitsApplying, isTrue);
    final fresh = (await debts.view(v.debt)).debt;
    final r = await debts.applySale(sold, fresh);
    expect(r.payments.single.isPrepayment, isTrue);
    expect(r.payments.single.amount, som(1200000));
    final after = await debts.view(r.debt);
    expect(after.nextDue, v.plan.first.amount - half);
    final applied = (await debts.sellables()).single;
    expect(applied.debtId, v.debt.meta.id);
    expect(applied.awaitsApplying, isFalse);
    await expectLater(
      debts.applySale(applied, r.debt),
      rule(DebtService.errNothingToApply),
    );
  });

  test(
    'qisman toʻlov: kichik oxirgi qator «toʻlangan» boʻlib qolmaydi',
    () async {
      // Regressiya (qurilmada topildi): belgilash birinchi to'lanmagan
      // qatordan keyin ham davom etib, kichik oxirgi qatorni yopardi.
      Installment row(int year, int month, int major) => Installment(
        dueOn: LocalDate(year, month, 1),
        amount: som(major),
        interest: som(0),
      );
      final v = await debts.add(
        creditorType: CreditorType.friend,
        creditorName: 'Doʻstim',
        principal: som(2300000),
        scheduleType: DebtScheduleType.manual,
        manual: [
          row(2026, 11, 1000000),
          row(2026, 12, 1000000),
          row(2027, 1, 300000),
        ],
      );
      expect(v.plan.last.amount, som(300000));
      final r = await debts.pay(v.debt, som(500000));
      final after = await debts.view(r.debt);
      expect(after.paidRows, 0);
      expect(after.nextDue, som(500000));
      await debts.pay(r.debt, som(500000));
      expect((await debts.view(r.debt)).paidRows, 1);
    },
  );

  test('yelkadosh: kim toʻlagani yoziladi', () async {
    final v = await relative(3000000);
    final son = await debts.addContributor(
      v.debt,
      name: 'Sardor',
      monthlyShare: som(500000),
    );
    await debts.pay(v.debt, som(500000), contributorId: son.meta.id);
    await debts.pay(v.debt, som(300000));
    final after = await debts.view(v.debt);
    expect(after.contributors.single.name, 'Sardor');
    expect(after.paidBy(son.meta.id), som(500000));
    expect(after.paid, som(800000));
  });

  test(
    'yopish tartibi: avval eng qimmat foizli, keyin muddati yaqin',
    () async {
      final bank = await akmal();
      final shop = await debts.add(
        creditorType: CreditorType.shop,
        creditorName: 'Doʻkon',
        principal: som(3000000),
        scheduleType: DebtScheduleType.fixedMarkup,
        termMonths: 6,
        markup: som(1500000),
      );
      final late = await relative(1000000);
      final soon = await debts.add(
        creditorType: CreditorType.friend,
        creditorName: 'Doʻstim',
        principal: som(200000),
        scheduleType: DebtScheduleType.manual,
        manual: [
          Installment(
            dueOn: LocalDate(2026, 11, 1),
            amount: som(200000),
            interest: som(0),
          ),
        ],
      );
      List<String> ids(List<DebtView> l) => [for (final v in l) v.debt.meta.id];
      // Do'kon ustamasi 50 % > bank 24 %.
      expect(ids((await debts.overview()).debts), [
        shop.debt.meta.id,
        bank.debt.meta.id,
        soon.debt.meta.id,
        late.debt.meta.id,
      ]);
      await debts.setPayoffOrder([late.debt.meta.id, bank.debt.meta.id]);
      expect(ids((await debts.overview()).debts).take(2), [
        late.debt.meta.id,
        bank.debt.meta.id,
      ]);
      await debts.setPayoffOrder(const []);
      expect(ids((await debts.overview()).debts).first, shop.debt.meta.id);
    },
  );

  test(
    'darvoza: foizli qarz bor, lekin qarzdan chiqish rejasi yoqilgan',
    () async {
      await akmal();
      expect(await readiness.isReady(), isFalse);
      await recovery.enable();
      expect(await readiness.isReady(), isTrue);
    },
  );
}
