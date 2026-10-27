import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/errors/data_exceptions.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/debts/data/drift_debt_repositories.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:baraka_daftari/features/debts/domain/debt_service.dart';
import 'package:baraka_daftari/features/debts/domain/debts.dart';
import 'package:baraka_daftari/features/household/data/drift_household_repository.dart';
import 'package:baraka_daftari/features/income/data/drift_income_repository.dart';
import 'package:baraka_daftari/features/income/domain/income.dart';
import 'package:baraka_daftari/features/obligations/data/drift_obligation_repository.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/db.dart';

const CurrencyCode uzs = CurrencyCode.uzs;
Money som(int major) => Money.major(major, uzs);

Matcher rule(String code) => throwsA(
  isA<DomainRuleException>().having((e) => e.code, 'code', code),
);

void main() {
  late TestDb t;
  late DebtService debts;
  late DebtDataReadiness readiness;

  setUp(() {
    t = TestDb.open();
    final hh = DriftHouseholdRepository(t.db, t.clock);
    final repo = DriftDebtRepository(t.db, t.clock);
    debts = DebtService(
      households: hh,
      debts: repo,
      installments: DriftDebtInstallmentRepository(t.db, t.clock),
      payments: DriftDebtPaymentRepository(t.db, t.clock),
      receivables: DriftReceivableRepository(t.db, t.clock),
      goals: DriftGoalRepository(t.db, t.clock),
      contributors: DriftDebtContributorRepository(t.db, t.clock),
      sellables: DriftSellableItemRepository(t.db, t.clock),
      incomes: DriftIncomeRepository(t.db, t.clock),
      metaFactory: t.meta,
      clock: t.clock,
    );
    readiness = DebtDataReadiness(repo, hh);
  });

  group('Receivable — foiz maydoni yoʻq (SPEC 2D.5)', () {
    const banned = ['markup', 'interest', 'rate', 'foiz', 'percent', 'ustama'];

    test('jadvalda foiz ustuni yoʻq', () {
      final columns = t.db.receivables.$columns.map((c) => c.name).toList();
      expect(columns, isNotEmpty);
      for (final c in columns) {
        for (final b in banned) {
          expect(c.contains(b), isFalse, reason: 'ustun: $c');
        }
      }
    });

    test('domen modelida foiz maydoni yoʻq', () {
      final r = Receivable(
        meta: t.meta.create('h'),
        debtorName: 'Qoʻshni',
        principal: som(200000),
        remaining: som(200000),
        dueDate: LocalDate(2026, 10, 31),
      );
      // freezed toString barcha maydonlarni sanaydi.
      final fields = r.toString().toLowerCase();
      for (final b in banned) {
        expect(fields.contains(b), isFalse, reason: fields);
      }
    });
  });

  group('toʻlash niyati — rejasiz qarz yoʻq', () {
    test('muddatsiz (oylar 0) qarz saqlanmaydi', () async {
      await expectLater(
        debts.add(
          creditorType: CreditorType.bank,
          creditorName: 'Bank',
          principal: som(1000000),
          scheduleType: DebtScheduleType.annuity,
        ),
        rule(DebtService.errScheduleRequired),
      );
    });

    test('qoʻlda: boʻsh reja saqlanmaydi', () async {
      await expectLater(
        debts.add(
          creditorType: CreditorType.relative,
          creditorName: 'Akam',
          principal: som(1000000),
          scheduleType: DebtScheduleType.manual,
        ),
        rule(DebtService.errScheduleRequired),
      );
    });

    test('qoʻlda: reja asosiy summani qoplamasa saqlanmaydi', () async {
      await expectLater(
        debts.add(
          creditorType: CreditorType.relative,
          creditorName: 'Akam',
          principal: som(1000000),
          scheduleType: DebtScheduleType.manual,
          manual: [
            Installment(
              dueOn: LocalDate(2026, 12, 1),
              amount: som(600000),
              interest: const Money.zero(uzs),
            ),
          ],
        ),
        rule(DebtService.errPlanMismatch),
      );
      expect((await debts.overview()).debts, isEmpty);
    });
  });

  test(
    'bank krediti: reja saqlanadi, haqiqiy narx, toʻlov, keyingi qator',
    () async {
      final v = await debts.add(
        creditorType: CreditorType.bank,
        creditorName: 'Avtokredit',
        principal: som(10000000),
        scheduleType: DebtScheduleType.annuity,
        termMonths: 12,
        annualRateBp: 2400,
        reason: 'mashina',
        check: const BorrowCheck(
          isNecessity: false,
          alternative: BorrowAlternative.none,
          loadBp: 1900,
        ),
      );
      expect(v.plan, hasLength(12));
      expect(v.debt.hasMarkup, isTrue, reason: 'foizli — qizil ogohlantirish');
      expect(v.cost.overpayment, const Money(134715159, uzs));
      expect(v.debt.remaining, const Money(1134715159, uzs));
      expect(
        BorrowCheck.fromJson(v.debt.borrowCheckJson!).alternative,
        BorrowAlternative.none,
      );

      final after = (await debts.pay(v.debt, v.plan.first.amount)).debt;
      final view = await debts.view(after);
      expect(view.next!.dueOn, v.plan[1].dueOn);
      expect(view.payments.single.isPrepayment, isFalse);
      await expectLater(
        debts.pay(after, after.remaining + som(1)),
        rule(DebtService.errPaymentTooBig),
      );
    },
  );

  test('umumiy koʻrsatkichlar va oylik qarz yuki', () async {
    final incomes = DriftIncomeRepository(t.db, t.clock);
    // Iyul–sentabr (bugun 2026-10-09): har oy 5 mln daromad.
    for (final m in [7, 8, 9]) {
      await incomes.add(
        Income(
          meta: t.meta.create(
            (await DriftHouseholdRepository(t.db, t.clock).current()).meta.id,
          ),
          amount: som(5000000),
          source: IncomeSource.salary,
          channel: PaymentChannel.card,
          receivedAt: DateTime.utc(2026, m, 10),
        ),
      );
    }
    await debts.add(
      creditorType: CreditorType.relative,
      creditorName: 'Togʻam',
      principal: som(3000000),
      scheduleType: DebtScheduleType.fixedMarkup,
      termMonths: 2,
    );
    final o = await debts.overview();
    expect(o.totalDebt, som(3000000));
    expect(o.monthlyPayments, som(1500000));
    expect(o.monthlyIncome, som(5000000));
    expect(o.loadBp, 3000);
  });

  test('bergan qarz: foizsiz, qaytarish, muddat eslatmasi', () async {
    final r = await debts.lend(
      debtorName: 'Qoʻshni',
      amount: som(200000),
      dueDate: LocalDate(2026, 10, 11),
    );
    expect(await debts.dueReceivables(), hasLength(1));
    final back = await debts.receive(r, som(200000));
    expect(back.isOpen, isFalse);
    expect(await debts.dueReceivables(), isEmpty);
    await expectLater(
      debts.lend(
        debtorName: ' ',
        amount: som(1),
        dueDate: LocalDate(2026, 11, 1),
      ),
      rule(DebtService.errNameRequired),
    );
  });

  test('darvoza qarz sharti: ochiq foizli qarz — tayyor emas', () async {
    expect(await readiness.isReady(), isTrue);
    final hasana = await debts.add(
      creditorType: CreditorType.friend,
      creditorName: 'Doʻstim',
      principal: som(500000),
      scheduleType: DebtScheduleType.manual,
      manual: [
        Installment(
          dueOn: LocalDate(2026, 11, 1),
          amount: som(500000),
          interest: const Money.zero(uzs),
        ),
      ],
    );
    expect(await readiness.isReady(), isTrue, reason: 'qarzi hasana');
    final bank = await debts.add(
      creditorType: CreditorType.bank,
      creditorName: 'Bank',
      principal: som(1000000),
      scheduleType: DebtScheduleType.differentiated,
      termMonths: 2,
      annualRateBp: 1200,
    );
    expect(await readiness.isReady(), isFalse);
    final full = (await debts.view(bank.debt)).payoffAmount;
    // 510 000 + 500 000: ikkinchi oy foizi (5 000) muddatidan oldin
    // to'lagani uchun tejaldi.
    expect(full, som(1010000));
    final r = await debts.pay(bank.debt, full);
    expect(r.closed, isTrue);
    expect(r.debt.remaining, som(0));
    expect(await readiness.isReady(), isTrue, reason: 'foizli qarz yopildi');
    expect(hasana.debt.hasMarkup, isFalse);
  });

  test('maqsad — imkoniyat narxi', () async {
    final g = await debts.addGoal('Qizimning kontrakti', som(25000000));
    expect((await debts.overview()).goals.single.title, g.title);
    expect(opportunityBp(som(20000000), g.target), 8000);
  });
}
