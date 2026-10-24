import 'package:baraka_daftari/core/money/money.dart';

/// 100 % = 10 000 basis point.
const int basisPointsWhole = 10000;

/// Summani [ratios] nisbatlarida bo'ladi — **largest remainder** usuli.
///
/// Kafolatlar:
/// * qismlar yig'indisi aynan [total] ga teng (bir tiyin ham yo'qolmaydi);
/// * musbat summada hech bir qism manfiy emas;
/// * har bir qism aniq ulushdan ko'pi bilan 1 minor birlikka farq qiladi;
/// * nisbati 0 bo'lgan qism doim 0.
///
/// Qoldiq tiyinlar kasr qismi eng katta bo'lgan qismlarga beriladi; teng
/// bo'lsa — ro'yxatda oldinroq turganiga (natija deterministik).
List<Money> allocate(Money total, List<int> ratios) {
  if (ratios.isEmpty) throw ArgumentError.value(ratios, 'ratios', "bo'sh");
  if (ratios.any((r) => r < 0)) {
    throw ArgumentError.value(ratios, 'ratios', 'manfiy nisbat');
  }
  final ratioSum = ratios.fold(BigInt.zero, (a, r) => a + BigInt.from(r));
  if (ratioSum == BigInt.zero) {
    throw ArgumentError.value(ratios, 'ratios', "yig'indi nol");
  }

  // Manfiy summa — modulini bo'lib, ishorani qaytaramiz (simmetriya).
  final negative = total.isNegative;
  final amount = BigInt.from(total.minorUnits).abs();

  final shares = <BigInt>[];
  final remainders = <BigInt>[];
  var allocated = BigInt.zero;
  for (final r in ratios) {
    final exact = amount * BigInt.from(r);
    final share = exact ~/ ratioSum;
    shares.add(share);
    remainders.add(exact - share * ratioSum);
    allocated += share;
  }

  var leftover = (amount - allocated).toInt(); // < ratios.length
  final order = List<int>.generate(ratios.length, (i) => i)
    ..sort((a, b) {
      final byRemainder = remainders[b].compareTo(remainders[a]);
      return byRemainder != 0 ? byRemainder : a.compareTo(b);
    });
  for (final i in order) {
    if (leftover == 0) break;
    if (ratios[i] == 0) continue;
    shares[i] += BigInt.one;
    leftover--;
  }

  return [
    for (final s in shares)
      Money(negative ? -s.toInt() : s.toInt(), total.currency),
  ];
}

/// [part] ning [whole] ga nisbati, bazis punktda (1 % = 100 bp):
/// «ijarangizning 40 %i» → 4000. [whole] nol yoki manfiy bo'lsa `null`.
int? ratioBasisPoints(
  Money part,
  Money whole, [
  RoundingMode mode = MoneyRounding.defaultMode,
]) {
  if (part.currency != whole.currency) {
    throw CurrencyMismatchException(whole.currency, part.currency);
  }
  if (!whole.isPositive) return null;
  return MoneyRounding.mulDiv(
    part.minorUnits,
    basisPointsWhole,
    whole.minorUnits,
    mode,
  );
}

/// Summaning [basisPoints] qismi (1 % = 100 bp). Masalan, 10 % —
/// `percentOf(income, 1000)`.
///
/// Spec (`DESKTOP_PROMPT.md` 4.4): `allocate(amount, [bp, 10000 − bp])[0]` —
/// yaxlitlash `allocate` bilan bir xil (teng kasrda birinchi qism, ya'ni
/// half-up). 0–10 000 dan tashqaridagi bp (masalan, yillik ustama 120 %)
/// uchun — markazlashgan [MoneyRounding] (standart half-up).
Money percentOf(
  Money amount,
  int basisPoints, [
  RoundingMode? mode,
]) {
  if (mode == null && basisPoints >= 0 && basisPoints <= basisPointsWhole) {
    if (basisPoints == 0) return Money.zero(amount.currency);
    return allocate(amount, [basisPoints, basisPointsWhole - basisPoints])[0];
  }
  return Money(
    MoneyRounding.mulDiv(
      amount.minorUnits,
      basisPoints,
      basisPointsWhole,
      mode ?? MoneyRounding.defaultMode,
    ),
    amount.currency,
  );
}
