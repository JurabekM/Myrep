import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:baraka_daftari/core/time/calendar.dart';
import 'package:baraka_daftari/features/debts/domain/debt_math.dart';
import 'package:meta/meta.dart';

/// Qo'shimcha to'lov qarzga qanday ta'sir qiladi.
enum PayoffKind {
  /// Foiz qoldiqqa hisoblanadi (bank: annuitet / differensial) — qo'shimcha
  /// to'lov asosiy qarzni kamaytiradi, keyingi foizlar qayta hisoblanadi.
  balance,

  /// Summa qat'iy (ustama, qo'lda, foizsiz) — qo'shimcha to'lov oxirgi
  /// to'lovlarni qisqartiradi, tejash yo'q (faqat muddat qisqaradi).
  flat,
}

/// Qo'shimcha to'lovdan keyin qarzning qolgan reja qatorlari qanday qayta
/// quriladi (SPEC 2D.2: «muddatni qisqartirish» — oylik to'lov o'zgarmaydi).
@immutable
final class PayoffTerms {
  const PayoffTerms.flat({this.prepayFeeBp = 0})
    : kind = PayoffKind.flat,
      annualRateBp = 0,
      annuityPayment = null,
      principalPart = null;

  /// Annuitet: [annuityPayment] har oy bir xil (oxirgisi — qoldiq).
  const PayoffTerms.annuity({
    required this.annualRateBp,
    required Money this.annuityPayment,
    this.prepayFeeBp = 0,
  }) : kind = PayoffKind.balance,
       principalPart = null;

  /// Differensial: asosiy qarzdan har oy [principalPart] + qoldiq foizi.
  const PayoffTerms.differentiated({
    required this.annualRateBp,
    required Money this.principalPart,
    this.prepayFeeBp = 0,
  }) : kind = PayoffKind.balance,
       annuityPayment = null;

  final PayoffKind kind;
  final int annualRateBp;
  final Money? annuityPayment;
  final Money? principalPart;

  /// Muddatidan oldin to'lash jarimasi / komissiyasi — qarzni kamaytirgan
  /// qismdan (bp).
  final int prepayFeeBp;

  /// [net] so'm qarzni kamaytirish uchun ushlanadigan jarima.
  Money feeFor(Money net) => Money(
    MoneyRounding.mulDiv(net.minorUnits, prepayFeeBp, basisPointsWhole),
    net.currency,
  );

  /// [budget] so'mlik qo'shimcha to'lovdan qarzni kamaytiradigan eng katta
  /// qism (jarima ustiga qo'shiladi va budjetdan oshmaydi).
  Money netWithin(Money budget) {
    if (!budget.isPositive) return Money.zero(budget.currency);
    if (prepayFeeBp == 0) return budget;
    var p =
        budget.minorUnits *
        basisPointsWhole ~/
        (basisPointsWhole + prepayFeeBp);
    int gross(int n) => n + feeFor(Money(n, budget.currency)).minorUnits;
    while (p > 0 && gross(p) > budget.minorUnits) {
      p--;
    }
    while (gross(p + 1) <= budget.minorUnits) {
      p++;
    }
    return Money(p, budget.currency);
  }
}

/// Qoldiq va shartlardan qolgan reja (SPEC 2D.2 simulyatori asosi): har oy
/// foiz = qoldiq × stavka / 12, oxirgi to'lov qoldiqni **aynan** yopadi.
/// Birinchi to'lov — [firstDue].
List<Installment> rowsFromBalance({
  required Money balance,
  required LocalDate firstDue,
  required PayoffTerms terms,
}) {
  assert(terms.kind == PayoffKind.balance, 'faqat qoldiqli qarz');
  final out = <Installment>[];
  var rest = balance;
  var k = 0;
  while (rest.isPositive) {
    final interest = Money(
      MoneyRounding.mulDiv(
        rest.minorUnits,
        terms.annualRateBp,
        12 * basisPointsWhole,
      ),
      rest.currency,
    );
    Money body;
    if (terms.annuityPayment != null) {
      body = terms.annuityPayment! - interest;
      // To'lov foizni ham qoplamasa — reja hech qachon tugamaydi.
      if (!body.isPositive) throw StateError('payment_below_interest');
    } else {
      body = terms.principalPart!;
    }
    if (body > rest) body = rest;
    out.add(
      Installment(
        dueOn: firstDue.plusMonths(k),
        amount: body + interest,
        interest: interest,
      ),
    );
    rest -= body;
    k++;
  }
  return out;
}

/// Qolgan reja qatorlariga [net] so'm qo'shimcha to'lovni qo'llash
/// (to'lov kuni, keyingi qator oldidan). Natija — yangi qolgan qatorlar.
///
/// * [PayoffKind.balance] — asosiy qarz [net] ga kamayadi va reja shu
///   oylik to'lov bilan qayta quriladi (muddat qisqaradi, foiz tejaladi).
/// * [PayoffKind.flat] — oxirgi qatorlar [net] ga qisqartiriladi.
List<Installment> applyPrepayment(
  List<Installment> rows,
  Money net,
  PayoffTerms terms,
) {
  if (rows.isEmpty || !net.isPositive) return rows;
  final c = net.currency;
  switch (terms.kind) {
    case PayoffKind.balance:
      final principal = Money.sum(rows.map((r) => r.principal), c);
      final rest = net >= principal ? Money.zero(c) : principal - net;
      return rowsFromBalance(
        balance: rest,
        firstDue: rows.first.dueOn,
        terms: terms,
      );
    case PayoffKind.flat:
      final out = [...rows];
      var left = net;
      while (left.isPositive && out.isNotEmpty) {
        final last = out.removeLast();
        if (last.amount > left) {
          final amount = last.amount - left;
          out.add(
            Installment(
              dueOn: last.dueOn,
              amount: amount,
              // Ustama qismi qatordan oshmaydi.
              interest: last.interest > amount ? amount : last.interest,
            ),
          );
          left = Money.zero(c);
        } else {
          left -= last.amount;
        }
      }
      return out;
  }
}

/// Simulyatsiyaning bir oyi (bir qarz uchun).
@immutable
final class PayoffStep {
  const PayoffStep({
    required this.dueOn,
    required this.regular,
    required this.interest,
    required this.extra,
    required this.fee,
    required this.balanceAfter,
  });

  final LocalDate dueOn;

  /// Rejadagi to'lov (foizi bilan).
  final Money regular;
  final Money interest;

  /// Qo'shimcha to'lov (jarimasi bilan) va undan ushlangan jarima.
  final Money extra;
  final Money fee;

  /// Shu oydan keyin qolgan jami to'lanadigan summa.
  final Money balanceAfter;

  Money get total => regular + extra;
}

/// Bitta qarzning simulyatsiya natijasi.
@immutable
final class PayoffSchedule {
  const PayoffSchedule(this.steps, this.currency);

  final List<PayoffStep> steps;
  final CurrencyCode currency;

  int get months => steps.length;
  LocalDate? get endDate => steps.isEmpty ? null : steps.last.dueOn;
  Money get totalPaid => Money.sum(steps.map((s) => s.total), currency);
  Money get totalInterest => Money.sum(steps.map((s) => s.interest), currency);
  Money get totalFees => Money.sum(steps.map((s) => s.fee), currency);

  /// Oxirgi oydan keyingi qoldiq (to'g'ri simulyatsiyada aynan 0).
  Money get finalBalance =>
      steps.isEmpty ? Money.zero(currency) : steps.last.balanceAfter;
}

/// Planner'dagi qarz: identifikator, qolgan reja va shartlar.
@immutable
final class PayoffDebt {
  const PayoffDebt({
    required this.id,
    required this.rows,
    required this.terms,
  });

  final String id;

  /// Qolgan (to'lanmagan) reja qatorlari, sanasi bo'yicha.
  final List<Installment> rows;
  final PayoffTerms terms;
}

/// Bitta qarzning odatiy va tezlashtirilgan grafigi.
@immutable
final class PayoffComparison {
  const PayoffComparison({
    required this.id,
    required this.baseline,
    required this.accelerated,
  });

  final String id;
  final PayoffSchedule baseline;
  final PayoffSchedule accelerated;

  /// Necha oy erta tugaydi.
  int get monthsEarly => baseline.months - accelerated.months;

  /// Tejalgan foiz / ustama (jarimalar ayirilgan; manfiy — jarima tejashdan
  /// ko'p).
  Money get saved => baseline.totalPaid - accelerated.totalPaid;
}

/// Bir nechta qarz uchun reja natijasi.
@immutable
final class PayoffPlan {
  const PayoffPlan(this.debts);

  /// Yopish tartibida.
  final List<PayoffComparison> debts;

  LocalDate? _max(LocalDate? Function(PayoffComparison) f) {
    LocalDate? out;
    for (final d in debts) {
      final x = f(d);
      if (x != null && (out == null || x.isAfter(out))) out = x;
    }
    return out;
  }

  /// «Qarzsiz kun» — odatiy va reja bo'yicha.
  LocalDate? get baselineDebtFree => _max((d) => d.baseline.endDate);
  LocalDate? get acceleratedDebtFree => _max((d) => d.accelerated.endDate);

  int get baselineMonths =>
      debts.fold(0, (m, d) => d.baseline.months > m ? d.baseline.months : m);
  int get acceleratedMonths => debts.fold(
    0,
    (m, d) => d.accelerated.months > m ? d.accelerated.months : m,
  );

  Money savedTotal(CurrencyCode c) => Money.sum(debts.map((d) => d.saved), c);
}

/// Payoff planner (SPEC 2D.2): har oy [monthlyExtra] (20 % ulush) va
/// birinchi oyda [lumpSum] (qutqarilgan pul, sotilgan buyum) [ordered]
/// tartibida qarzlarga qo'shimcha to'lov sifatida beriladi: avval
/// birinchisiga, u yopilgach ortgani keyingisiga. Yopilgan qarzning oylik
/// to'lovi qo'shimchaga qo'shilmaydi (bo'shagan summa jamg'armaga taklif
/// qilinadi — SPEC 2D.9).
///
/// Har qarzning k-oyi — uning k-chi qolgan reja qatori sanasi.
PayoffPlan planPayoff(
  List<PayoffDebt> ordered, {
  required Money monthlyExtra,
  Money? lumpSum,
}) {
  final c = monthlyExtra.currency;
  final zero = Money.zero(c);
  final rows = [for (final d in ordered) d.rows];
  final steps = [for (final _ in ordered) <PayoffStep>[]];
  var k = 0;
  while (rows.any((r) => r.isNotEmpty)) {
    var pool = monthlyExtra + (k == 0 ? (lumpSum ?? zero) : zero);
    for (var i = 0; i < ordered.length; i++) {
      final r = rows[i];
      if (r.isEmpty) continue;
      final terms = ordered[i].terms;
      final row = r.first;
      var rest = r.sublist(1);
      var extra = zero;
      var fee = zero;
      if (pool.isPositive && rest.isNotEmpty) {
        final owed = Money.sum(rest.map((x) => x.principal), c);
        final flatOwed = Money.sum(rest.map((x) => x.amount), c);
        final cap = terms.kind == PayoffKind.balance ? owed : flatOwed;
        var net = terms.netWithin(pool);
        if (net > cap) net = cap;
        if (net.isPositive) {
          fee = terms.feeFor(net);
          extra = net + fee;
          pool -= extra;
          rest = applyPrepayment(rest, net, terms);
        }
      }
      rows[i] = rest;
      steps[i].add(
        PayoffStep(
          dueOn: row.dueOn,
          regular: row.amount,
          interest: row.interest,
          extra: extra,
          fee: fee,
          balanceAfter: Money.sum(rest.map((x) => x.amount), c),
        ),
      );
    }
    k++;
  }
  return PayoffPlan([
    for (final (i, d) in ordered.indexed)
      PayoffComparison(
        id: d.id,
        baseline: PayoffSchedule([
          for (final (j, row) in d.rows.indexed)
            PayoffStep(
              dueOn: row.dueOn,
              regular: row.amount,
              interest: row.interest,
              extra: zero,
              fee: zero,
              balanceAfter: Money.sum(
                d.rows.skip(j + 1).map((x) => x.amount),
                c,
              ),
            ),
        ], c),
        accelerated: PayoffSchedule(steps[i], c),
      ),
  ]);
}
