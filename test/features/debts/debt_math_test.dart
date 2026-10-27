import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:flutter_test/flutter_test.dart';

const CurrencyCode uzs = CurrencyCode.uzs;
Money som(int major) => Money.major(major, uzs);

/// Har qanday reja: asosiy qismlar yigʻindisi aynan asosiy summaga teng.
void expectClosesPrincipal(List<Installment> s, Money principal) {
  expect(Money.sum(s.map((i) => i.principal), uzs), principal);
  for (final i in s) {
    expect(i.interest.isNegative, isFalse);
    expect(i.principal.isNegative, isFalse);
  }
}

void main() {
  final start = LocalDate(2026, 10, 9);

  group('haqiqiy narx — 4 xil jadval turi', () {
    test('annuitet: 10 mln, 24 %, 12 oy — Python bilan mustaqil hisob', () {
      final s = buildSchedule(
        type: DebtScheduleType.annuity,
        principal: som(10000000),
        start: start,
        termMonths: 12,
        annualRateBp: 2400,
      );
      expect(s, hasLength(12));
      expect(s.first.amount, const Money(94559597, uzs));
      expect(s.first.interest, som(200000)); // 2 % × 10 mln
      expect(s.first.dueOn, LocalDate(2026, 11, 9));
      expect(s.last.dueOn, LocalDate(2027, 10, 9));
      expectClosesPrincipal(s, som(10000000));
      final cost = DebtCost.of(som(10000000), s);
      expect(cost.totalPaid, const Money(1134715159, uzs));
      expect(cost.overpayment, const Money(134715159, uzs));
      expect(cost.overpaymentBp, 1347);
    });

    test('differensial: asosiy teng, foiz kamayib boradi', () {
      final s = buildSchedule(
        type: DebtScheduleType.differentiated,
        principal: som(10000000),
        start: start,
        termMonths: 12,
        annualRateBp: 2400,
      );
      expect(s.first.amount, const Money(103333334, uzs));
      expect(s.last.amount < s.first.amount, isTrue);
      expectClosesPrincipal(s, som(10000000));
      final cost = DebtCost.of(som(10000000), s);
      expect(cost.overpayment, som(1300000));
    });

    test('qatʼiy ustama: Hamid aka — 40 mln + 20 mln ustama, 24 oy', () {
      final s = buildSchedule(
        type: DebtScheduleType.fixedMarkup,
        principal: som(40000000),
        start: start,
        termMonths: 24,
        markup: som(20000000),
      );
      expect(s.map((i) => i.amount).toSet(), {som(2500000)});
      expectClosesPrincipal(s, som(40000000));
      final cost = DebtCost.of(som(40000000), s);
      expect(cost.totalPaid, som(60000000));
      expect(cost.overpayment, som(20000000));
      expect(cost.overpaymentBp, 5000);
    });

    test('qoʻlda (qarzi hasana): ortiqcha toʻlov yoʻq', () {
      final manual = [
        Installment(
          dueOn: LocalDate(2026, 11, 1),
          amount: som(1000000),
          interest: const Money.zero(uzs),
        ),
        Installment(
          dueOn: LocalDate(2026, 12, 1),
          amount: som(500000),
          interest: const Money.zero(uzs),
        ),
      ];
      final s = buildSchedule(
        type: DebtScheduleType.manual,
        principal: som(1500000),
        start: start,
        manual: manual,
      );
      expect(s, manual);
      expect(DebtCost.of(som(1500000), s).overpayment, const Money.zero(uzs));
    });

    test('foizsiz annuitet — teng boʻlaklar, tiyin yoʻqolmaydi', () {
      final s = buildSchedule(
        type: DebtScheduleType.annuity,
        principal: som(1000000),
        start: start,
        termMonths: 3,
      );
      expect(Money.sum(s.map((i) => i.amount), uzs), som(1000000));
      expect(s.every((i) => i.interest.isZero), isTrue);
    });

    test('notoʻgʻri muddat rad etiladi', () {
      expect(
        () => buildSchedule(
          type: DebtScheduleType.annuity,
          principal: som(1),
          start: start,
        ),
        throwsArgumentError,
      );
    });

    test('31-sanadan boshlangan reja qisqa oyda oxirgi kunga tushadi', () {
      final s = buildSchedule(
        type: DebtScheduleType.fixedMarkup,
        principal: som(300),
        start: LocalDate(2027, 1, 31),
        termMonths: 2,
      );
      expect(s.first.dueOn, LocalDate(2027, 2, 28));
      expect(s.last.dueOn, LocalDate(2027, 3, 31));
    });
  });

  test('qarz yuki va imkoniyat narxi (bp)', () {
    expect(debtLoadBp(som(1500000), som(5000000)), 3000);
    expect(debtLoadBp(som(1), const Money.zero(uzs)), isNull);
    // 20 mln ortiqcha toʻlov — 25 mln lik kontraktning 80 %i.
    expect(opportunityBp(som(20000000), som(25000000)), 8000);
  });

  test('foizli qarzni aniqlash', () {
    expect(isInterestBearing(hasMarkup: false), isFalse);
    expect(isInterestBearing(hasMarkup: true), isTrue);
    expect(isInterestBearing(hasMarkup: false, annualRateBp: 2400), isTrue);
    expect(isInterestBearing(hasMarkup: false, markup: som(1)), isTrue);
  });

  test('butun soʻmli toʻlov rejadagi tiyinli summaga moslanadi', () {
    const next = Money(94559597, uzs); // 945 595,97
    const remaining = Money(1134715159, uzs);
    expect(ceilToMajor(next), som(945596));
    expect(ceilToMajor(som(5)), som(5));
    expect(snapPayment(som(945596), remaining: remaining, next: next), next);
    expect(snapPayment(som(945595), remaining: remaining, next: next), next);
    expect(
      snapPayment(som(1000000), remaining: remaining, next: next),
      som(1000000),
      reason: 'boshqa summa — oʻzgarmaydi',
    );
    expect(
      snapPayment(som(11347152), remaining: remaining, next: next),
      remaining,
      reason: 'toʻliq yopish',
    );
  });
}
