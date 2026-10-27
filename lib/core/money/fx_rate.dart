import 'package:baraka_daftari/core/money/money.dart';
import 'package:meta/meta.dart';

/// Valyuta kursi snapshoti (SPEC 4.2). MVP'da kursni foydalanuvchi qo'lda
/// kiritadi.
///
/// Kurs `double` emas, kasr: 1 major [from] = [numerator] / [denominator]
/// major [to]. Masalan, 1 USD = 12 650,50 so'm →
/// `numerator: 1265050, denominator: 100`.
@immutable
final class FxRate {
  FxRate({
    required this.from,
    required this.to,
    required this.numerator,
    required this.denominator,
    required this.date,
    this.source = 'manual',
  }) {
    if (from == to) throw ArgumentError('from va to bir xil');
    if (numerator <= 0 || denominator <= 0) {
      throw ArgumentError("Kurs musbat bo'lishi kerak");
    }
  }

  /// O'nli yozuvdan: `FxRate.parse(usd, uzs, '12650.50', date)`.
  /// Vergul ham qabul qilinadi.
  factory FxRate.parse(
    CurrencyCode from,
    CurrencyCode to,
    String rate,
    DateTime date, {
    String source = 'manual',
  }) {
    final match = RegExp(
      r'^\s*(\d+)(?:[.,](\d{1,9}))?\s*$',
    ).firstMatch(rate.replaceAll(RegExp(r'[\s ]'), ''));
    if (match == null) throw FormatException("Kurs noto'g'ri", rate);
    final fraction = match.group(2) ?? '';
    var denominator = 1;
    for (var i = 0; i < fraction.length; i++) {
      denominator *= 10;
    }
    return FxRate(
      from: from,
      to: to,
      numerator: int.parse('${match.group(1)}$fraction'),
      denominator: denominator,
      date: date,
      source: source,
    );
  }

  final CurrencyCode from;
  final CurrencyCode to;
  final int numerator;
  final int denominator;

  /// Kurs sanasi (snapshot).
  final DateTime date;
  final String source;

  /// Teskari kurs (to → from).
  FxRate inverse() => FxRate(
    from: to,
    to: from,
    numerator: denominator,
    denominator: numerator,
    date: date,
    source: source,
  );

  @override
  bool operator ==(Object other) =>
      other is FxRate &&
      other.from == from &&
      other.to == to &&
      other.numerator * denominator == numerator * other.denominator &&
      other.date == date &&
      other.source == source;

  @override
  int get hashCode => Object.hash(from, to, date, source);
}

/// [amount] ni [rate] bo'yicha konvertatsiya qiladi. [amount] valyutasi
/// `rate.from` bo'lishi shart.
Money convert(
  Money amount,
  FxRate rate, [
  RoundingMode mode = MoneyRounding.defaultMode,
]) {
  if (amount.currency != rate.from) {
    throw CurrencyMismatchException(rate.from, amount.currency);
  }
  // minor_to = minor_from * num * 10^toDigits / (den * 10^fromDigits)
  final numerator =
      BigInt.from(amount.minorUnits) *
      BigInt.from(rate.numerator) *
      BigInt.from(rate.to.minorPerMajor);
  final denominator =
      BigInt.from(rate.denominator) * BigInt.from(rate.from.minorPerMajor);
  return Money(
    MoneyRounding.divideBig(numerator, denominator, mode),
    rate.to,
  );
}
