import 'package:baraka_daftari/core/domain/enums.dart';
import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:meta/meta.dart';

/// Rejadagi bir to'lov: jami va shundan foiz / ustama qismi.
@immutable
final class Installment {
  const Installment({
    required this.dueOn,
    required this.amount,
    required this.interest,
  });

  final LocalDate dueOn;
  final Money amount;

  /// Foiz yoki ustama qismi (`amount` ichida).
  final Money interest;

  Money get principal => amount - interest;

  @override
  bool operator ==(Object other) =>
      other is Installment &&
      other.dueOn == dueOn &&
      other.amount == amount &&
      other.interest == interest;

  @override
  int get hashCode => Object.hash(dueOn, amount, interest);

  @override
  String toString() => 'Installment($dueOn, $amount, foiz $interest)';
}

/// Yillik stavkadan oylik foiz: qoldiq × stavka / (12 × 10 000).
const int _monthlyDenominator = 12 * basisPointsWhole;

Money _monthlyInterest(Money remaining, int annualRateBp) => Money(
  MoneyRounding.mulDiv(remaining.minorUnits, annualRateBp, _monthlyDenominator),
  remaining.currency,
);

/// Qarz to'lov rejasini qurish (SPEC 2D.3). [start] dan keyingi har oy
/// (1-to'lov — bir oydan keyin).
///
/// * [DebtScheduleType.annuity] — teng to'lov `P·r·bⁿ / (12·10⁴·(bⁿ − aⁿ))`
///   (a = 12·10⁴, b = a + stavka), foiz qoldiqqa; oxirgi to'lov qoldiqni
///   aynan yopadi. Stavka 0 — teng bo'laklar.
/// * [DebtScheduleType.differentiated] — asosiy qarz teng, foiz qoldiqqa.
/// * [DebtScheduleType.fixedMarkup] — (asosiy + [markup]) teng bo'lib.
/// * [DebtScheduleType.manual] — [manual] qatorlari o'zgarishsiz.
List<Installment> buildSchedule({
  required DebtScheduleType type,
  required Money principal,
  required LocalDate start,
  int termMonths = 0,
  int annualRateBp = 0,
  Money? markup,
  List<Installment> manual = const [],
}) {
  final c = principal.currency;
  final zero = Money.zero(c);
  if (type == DebtScheduleType.manual) return List.unmodifiable(manual);
  if (termMonths <= 0) throw ArgumentError.value(termMonths, 'termMonths');
  if (annualRateBp < 0) throw ArgumentError.value(annualRateBp, 'rate');
  LocalDate due(int k) => start.plusMonths(k + 1);
  final equal = List.filled(termMonths, 1);

  switch (type) {
    case DebtScheduleType.fixedMarkup:
      final m = markup ?? zero;
      final totals = allocate(principal + m, equal);
      final interests = allocate(m, equal);
      return [
        for (var k = 0; k < termMonths; k++)
          Installment(dueOn: due(k), amount: totals[k], interest: interests[k]),
      ];
    case DebtScheduleType.differentiated:
      final parts = allocate(principal, equal);
      var remaining = principal;
      final out = <Installment>[];
      for (var k = 0; k < termMonths; k++) {
        final interest = _monthlyInterest(remaining, annualRateBp);
        out.add(
          Installment(
            dueOn: due(k),
            amount: parts[k] + interest,
            interest: interest,
          ),
        );
        remaining -= parts[k];
      }
      return out;
    case DebtScheduleType.annuity:
      if (annualRateBp == 0) {
        return [
          for (final (k, part) in allocate(principal, equal).indexed)
            Installment(dueOn: due(k), amount: part, interest: zero),
        ];
      }
      final a = BigInt.from(_monthlyDenominator);
      final b = BigInt.from(_monthlyDenominator + annualRateBp);
      final an = a.pow(termMonths);
      final bn = b.pow(termMonths);
      final payment = Money(
        MoneyRounding.divideBig(
          BigInt.from(principal.minorUnits) * BigInt.from(annualRateBp) * bn,
          a * (bn - an),
        ),
        c,
      );
      var remaining = principal;
      final out = <Installment>[];
      for (var k = 0; k < termMonths; k++) {
        final interest = _monthlyInterest(remaining, annualRateBp);
        final last = k == termMonths - 1;
        final body = last ? remaining : payment - interest;
        out.add(
          Installment(
            dueOn: due(k),
            amount: body + interest,
            interest: interest,
          ),
        );
        remaining -= body;
      }
      return out;
    case DebtScheduleType.manual:
      throw StateError('unreachable');
  }
}

/// Qarzning haqiqiy narxi (SPEC 2D.3): asosiy summa → jami to'lanadi →
/// ortiqcha to'lov.
@immutable
final class DebtCost {
  const DebtCost({required this.principal, required this.totalPaid});

  factory DebtCost.of(Money principal, Iterable<Installment> schedule) =>
      DebtCost(
        principal: principal,
        totalPaid: Money.sum(
          schedule.map((i) => i.amount),
          principal.currency,
        ),
      );

  final Money principal;
  final Money totalPaid;

  /// Foiz / ustama — ortiqcha to'lov (manfiy bo'lmaydi).
  Money get overpayment {
    final d = totalPaid - principal;
    return d.isNegative ? Money.zero(d.currency) : d;
  }

  /// Ortiqcha to'lov asosiy summaning necha foizi (bp).
  int get overpaymentBp => ratioBasisPoints(overpayment, principal) ?? 0;
}

/// Oylik qarz yuki: to'lovlar / o'rtacha oylik daromad (bp); daromad
/// noma'lum — `null`.
int? debtLoadBp(Money monthlyPayments, Money monthlyIncome) =>
    ratioBasisPoints(monthlyPayments, monthlyIncome);

/// Imkoniyat narxi (SPEC 2D.3): ortiqcha to'lov maqsadning necha foizi
/// (bp) — «bu summa qizingizning kontraktining 80 %i».
int? opportunityBp(Money overpayment, Money goalTarget) =>
    ratioBasisPoints(overpayment, goalTarget);

/// Qarz foizli / ustamalimi (qizil ogohlantirish, darvoza sharti).
bool isInterestBearing({
  required bool hasMarkup,
  int? annualRateBp,
  Money? markup,
}) =>
    hasMarkup ||
    (annualRateBp ?? 0) > 0 ||
    (markup != null && markup.isPositive);

/// Butun so'mga yaxlitlangan summa (yuqoriga) — summa oynasi faqat butun
/// major birlik qabul qiladi.
Money ceilToMajor(Money m) {
  final per = m.currency.minorPerMajor;
  final rem = m.minorUnits % per;
  return rem == 0 ? m : Money(m.minorUnits - rem + per, m.currency);
}

/// Butun so'mda kiritilgan to'lovni rejaga moslash: bank jadvalida tiyin
/// bor, oyna esa faqat butun so'm oladi. Kiritilgan summa navbatdagi
/// to'lov yoki qoldiqdan 1 so'mdan kam farq qilsa — aynan o'sha summa.
Money snapPayment(Money entered, {required Money remaining, Money? next}) {
  bool near(Money target) =>
      (entered.minorUnits - target.minorUnits).abs() <
      entered.currency.minorPerMajor;
  if (near(remaining) || entered > remaining) return remaining;
  if (next != null && near(next)) return next;
  return entered;
}
