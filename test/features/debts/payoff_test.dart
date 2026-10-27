import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:baraka_daftari/features/debts/domain/payoff.dart';
import 'package:flutter_test/flutter_test.dart';

const CurrencyCode uzs = CurrencyCode.uzs;
Money som(int major) => Money.major(major, uzs);
final start = LocalDate(2026, 10, 8);

Money principalOf(Iterable<Installment> rows) =>
    Money.sum(rows.map((r) => r.principal), uzs);

/// Simulyatsiyada qarzni kamaytirgan jami: rejadagi asosiy qism +
/// qoʻshimcha toʻlovlar (jarimasiz).
Money principalPaid(PayoffSchedule s) => Money.sum([
  for (final x in s.steps) ...[x.regular - x.interest, x.extra - x.fee],
], uzs);

void main() {
  group('etalon misollar (MVP_PLAN Vazifa 11)', () {
    test('Hamid aka: 9 mln qoldiq, oyiga 1,5 mln — 600 mingi foiz', () {
      // 600 000 = 9 000 000 × stavka / 12 → yillik 80 % (8 000 bp).
      const terms = PayoffTerms.annuity(
        annualRateBp: 8000,
        annuityPayment: Money(150000000, uzs),
      );
      final rows = rowsFromBalance(
        balance: som(9000000),
        firstDue: start,
        terms: terms,
      );
      expect(rows.first.amount, som(1500000));
      expect(rows.first.interest, som(600000));
      expect(rows.first.principal, som(900000));
      expect(rows, hasLength(8));
      expect(principalOf(rows), som(9000000), reason: 'tiyin farqisiz');
      expect(
        Money.sum(rows.map((r) => r.amount), uzs),
        const Money(1187630396, uzs),
      );
      expect(rows.last.amount, const Money(137630396, uzs));

      // Oyiga 300 000 qoʻshimcha → 7 oy.
      final plan = planPayoff(
        [PayoffDebt(id: 'karim', rows: rows, terms: terms)],
        monthlyExtra: som(300000),
      );
      final d = plan.debts.single;
      expect(d.accelerated.months, 7);
      expect(d.monthsEarly, 1);
      expect(d.saved, const Money(55592402, uzs));
      expect(d.accelerated.finalBalance, som(0));
      expect(principalPaid(d.accelerated), som(9000000));
    });

    test('Akmal: avtokredit 39 mln, 14 oy → qoʻshimcha toʻlov bilan 9 oy', () {
      final schedule = buildSchedule(
        type: DebtScheduleType.annuity,
        principal: som(39000000),
        start: start,
        termMonths: 14,
        annualRateBp: 2400,
      );
      expect(schedule.first.amount, const Money(322147684, uzs));
      final terms = PayoffTerms.annuity(
        annualRateBp: 2400,
        annuityPayment: schedule.first.amount,
      );
      // Daromad 10 mln, 20 % ulush — oyiga 2 mln qoʻshimcha.
      final plan = planPayoff(
        [PayoffDebt(id: 'akmal', rows: schedule, terms: terms)],
        monthlyExtra: som(2000000),
      );
      final d = plan.debts.single;
      expect(d.baseline.months, 14);
      expect(d.accelerated.months, inInclusiveRange(8, 9));
      expect(d.accelerated.months, 9);
      expect(d.monthsEarly, 5);
      expect(d.saved, const Money(243234042, uzs));
      expect(d.accelerated.finalBalance, som(0));
      expect(principalPaid(d.accelerated), som(39000000));
      expect(principalPaid(d.baseline), som(39000000));
      expect(plan.acceleratedDebtFree, start.plusMonths(9));
      expect(plan.baselineDebtFree, start.plusMonths(14));
    });
  });

  test('qoʻshimchasiz simulyatsiya saqlangan rejaning oʻzi', () {
    final schedule = buildSchedule(
      type: DebtScheduleType.differentiated,
      principal: som(12000000),
      start: start,
      termMonths: 12,
      annualRateBp: 1800,
    );
    final plan = planPayoff(
      [
        PayoffDebt(
          id: 'x',
          rows: schedule,
          terms: PayoffTerms.differentiated(
            annualRateBp: 1800,
            principalPart: schedule.first.principal,
          ),
        ),
      ],
      monthlyExtra: som(0),
    );
    final d = plan.debts.single;
    expect(d.accelerated.totalPaid, d.baseline.totalPaid);
    expect(d.monthsEarly, 0);
    expect(d.saved, som(0));
    expect(d.baseline.totalPaid, Money.sum(schedule.map((r) => r.amount), uzs));
  });

  test('har qanday stavka / muddat / qoʻshimchada qoldiq aynan 0', () {
    for (final type in [
      DebtScheduleType.annuity,
      DebtScheduleType.differentiated,
    ]) {
      for (final rate in [1, 999, 2400, 4999]) {
        for (final term in [1, 7, 36]) {
          for (final extra in [0, 1, 333333, 5000000]) {
            const p = Money(1234567891, uzs);
            final schedule = buildSchedule(
              type: type,
              principal: p,
              start: start,
              termMonths: term,
              annualRateBp: rate,
            );
            final terms = type == DebtScheduleType.annuity
                ? PayoffTerms.annuity(
                    annualRateBp: rate,
                    annuityPayment: schedule.first.amount,
                    prepayFeeBp: 150,
                  )
                : PayoffTerms.differentiated(
                    annualRateBp: rate,
                    principalPart: schedule.first.principal,
                    prepayFeeBp: 150,
                  );
            final d = planPayoff(
              [PayoffDebt(id: 'x', rows: schedule, terms: terms)],
              monthlyExtra: Money(extra, uzs),
            ).debts.single;
            final label = '$type $rate bp, $term oy, +$extra';
            expect(d.accelerated.finalBalance, som(0), reason: label);
            expect(principalPaid(d.accelerated), p, reason: label);
            expect(d.accelerated.months, lessThanOrEqualTo(term));
          }
        }
      }
    }
  });

  test('jarima: qoʻshimcha toʻlovdan ushlanadi, budjetdan oshmaydi', () {
    const terms = PayoffTerms.flat(prepayFeeBp: 200);
    expect(terms.feeFor(som(1000000)), som(20000));
    for (final b in [1, 101, 102, 1000000, 2000000, 123456789]) {
      final budget = Money(b, uzs);
      final net = terms.netWithin(budget);
      expect(net + terms.feeFor(net) <= budget, isTrue, reason: '$b');
      final more = net + const Money(1, uzs);
      expect(more + terms.feeFor(more) > budget, isTrue, reason: 'eng katta');
    }
    expect(const PayoffTerms.flat().netWithin(som(5)), som(5));

    // Bankda 2 % jarima: tejash kamayadi, lekin muddat baribir qisqaradi.
    final schedule = buildSchedule(
      type: DebtScheduleType.annuity,
      principal: som(39000000),
      start: start,
      termMonths: 14,
      annualRateBp: 2400,
    );
    PayoffComparison run(int fee) => planPayoff(
      [
        PayoffDebt(
          id: 'a',
          rows: schedule,
          terms: PayoffTerms.annuity(
            annualRateBp: 2400,
            annuityPayment: schedule.first.amount,
            prepayFeeBp: fee,
          ),
        ),
      ],
      monthlyExtra: som(2000000),
    ).debts.single;
    final free = run(0);
    final fined = run(200);
    expect(fined.accelerated.totalFees.isPositive, isTrue);
    expect(fined.saved < free.saved, isTrue);
    expect(fined.accelerated.finalBalance, som(0));
  });

  test('qatʼiy ustama: qoʻshimcha toʻlov muddatni qisqartiradi, ustama '
      'tejalmaydi', () {
    final schedule = buildSchedule(
      type: DebtScheduleType.fixedMarkup,
      principal: som(10000000),
      start: start,
      termMonths: 10,
      markup: som(2000000),
    );
    final d = planPayoff(
      [
        PayoffDebt(
          id: 'shop',
          rows: schedule,
          terms: const PayoffTerms.flat(),
        ),
      ],
      monthlyExtra: som(1200000),
    ).debts.single;
    expect(d.baseline.months, 10);
    expect(d.accelerated.months, 5);
    expect(d.saved, som(0));
    expect(d.accelerated.totalPaid, som(12000000));
    expect(d.accelerated.finalBalance, som(0));
  });

  test('bir nechta qarz: avval birinchisi, yopilgach ortgani keyingisiga', () {
    final bank = buildSchedule(
      type: DebtScheduleType.annuity,
      principal: som(5000000),
      start: start,
      termMonths: 10,
      annualRateBp: 3000,
    );
    final relative = [
      for (var k = 1; k <= 6; k++)
        Installment(
          dueOn: start.plusMonths(k),
          amount: som(500000),
          interest: som(0),
        ),
    ];
    final plan = planPayoff(
      [
        PayoffDebt(
          id: 'bank',
          rows: bank,
          terms: PayoffTerms.annuity(
            annualRateBp: 3000,
            annuityPayment: bank.first.amount,
          ),
        ),
        PayoffDebt(
          id: 'relative',
          rows: relative,
          terms: const PayoffTerms.flat(),
        ),
      ],
      monthlyExtra: som(1000000),
      lumpSum: som(1500000),
    );
    final b = plan.debts[0];
    final r = plan.debts[1];
    expect(b.accelerated.months, lessThan(b.baseline.months));
    expect(b.saved.isPositive, isTrue);
    expect(r.accelerated.months, lessThan(r.baseline.months));
    // Foizsiz qarzga qoʻshimcha faqat bank yopilgan oydan boshlab tushadi.
    final bankEnd = b.accelerated.months;
    for (final s in r.accelerated.steps.take(bankEnd - 1)) {
      expect(s.extra, som(0));
    }
    expect(b.accelerated.steps.first.extra, som(2500000), reason: 'lump sum');
    for (final d in plan.debts) {
      expect(d.accelerated.finalBalance, som(0));
    }
  });

  test('qoʻlda qator: qoʻshimcha toʻlov oxirgi qatorlarni qisqartiradi', () {
    final rows = [
      Installment(
        dueOn: start.plusMonths(1),
        amount: som(300),
        interest: som(0),
      ),
      Installment(
        dueOn: start.plusMonths(2),
        amount: som(300),
        interest: som(0),
      ),
      Installment(
        dueOn: start.plusMonths(3),
        amount: som(300),
        interest: som(0),
      ),
    ];
    final out = applyPrepayment(rows, som(400), const PayoffTerms.flat());
    expect(out, [
      rows[0],
      Installment(
        dueOn: start.plusMonths(2),
        amount: som(200),
        interest: som(0),
      ),
    ]);
    expect(applyPrepayment(rows, som(900), const PayoffTerms.flat()), isEmpty);
  });

  test('toʻlov foizni ham qoplamasa — reja tuzilmaydi', () {
    expect(
      () => rowsFromBalance(
        balance: som(9000000),
        firstDue: start,
        terms: const PayoffTerms.annuity(
          annualRateBp: 8000,
          annuityPayment: Money(60000000, uzs),
        ),
      ),
      throwsStateError,
    );
  });
}
