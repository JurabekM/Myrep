import 'package:baraka_daftari/core/money/currency.dart';
import 'package:baraka_daftari/core/money/money_rounding.dart';
import 'package:meta/meta.dart';

export 'package:baraka_daftari/core/money/currency.dart';
export 'package:baraka_daftari/core/money/money_rounding.dart';

/// Pul miqdori: butun sonli minor birliklar (tiyin, sent) + valyuta.
///
/// Immutable value-object. `double` va `num` pul uchun taqiqlangan
/// (SPEC 4.2). Har xil valyutalar to'g'ridan-to'g'ri qo'shilmaydi —
/// faqat `FxRate` orqali.
@immutable
final class Money implements Comparable<Money> {
  const Money(this.minorUnits, this.currency);

  const Money.zero(this.currency) : minorUnits = 0;

  /// Butun major birliklardan: `Money.major(8000000, CurrencyCode.uzs)`.
  factory Money.major(int major, CurrencyCode currency) =>
      Money(_checkedMul(major, currency.minorPerMajor), currency);

  final int minorUnits;
  final CurrencyCode currency;

  bool get isZero => minorUnits == 0;
  bool get isNegative => minorUnits < 0;
  bool get isPositive => minorUnits > 0;

  /// Butun major qism: tiyin tashlanadi, nolga qarab (1 234 567 → 1 234).
  int get wholeMajor => minorUnits ~/ currency.minorPerMajor;

  Money operator +(Money other) {
    _requireSameCurrency(other);
    return Money(_checkedAdd(minorUnits, other.minorUnits), currency);
  }

  Money operator -(Money other) {
    _requireSameCurrency(other);
    return Money(_checkedAdd(minorUnits, -other.minorUnits), currency);
  }

  Money operator -() => Money(_checkedMul(minorUnits, -1), currency);

  /// Butun songa ko'paytirish (masalan, «kuniga 2 ta × 30 kun»).
  Money times(int factor) => Money(_checkedMul(minorUnits, factor), currency);

  Money abs() => isNegative ? -this : this;

  /// `this × numerator / denominator`, bir marta yaxlitlanadi (masalan,
  /// 30 kunlik jamini yilga: `scaled(365, 30)`).
  Money scaled(
    int numerator,
    int denominator, [
    RoundingMode mode = MoneyRounding.defaultMode,
  ]) {
    if (denominator == 0) throw ArgumentError.value(denominator, 'denominator');
    return Money(
      MoneyRounding.mulDiv(minorUnits, numerator, denominator, mode),
      currency,
    );
  }

  /// [stepMinor] ga karrali qilib yaxlitlash. Masalan, 1 000 so'mgacha:
  /// `roundTo(100000)`.
  Money roundTo(
    int stepMinor, [
    RoundingMode mode = MoneyRounding.defaultMode,
  ]) {
    if (stepMinor <= 0) throw ArgumentError.value(stepMinor, 'stepMinor');
    final steps = MoneyRounding.divide(minorUnits, stepMinor, mode);
    return Money(_checkedMul(steps, stepMinor), currency);
  }

  bool operator <(Money other) => compareTo(other) < 0;
  bool operator <=(Money other) => compareTo(other) <= 0;
  bool operator >(Money other) => compareTo(other) > 0;
  bool operator >=(Money other) => compareTo(other) >= 0;

  @override
  int compareTo(Money other) {
    _requireSameCurrency(other);
    return minorUnits.compareTo(other.minorUnits);
  }

  void _requireSameCurrency(Money other) {
    if (other.currency != currency) {
      throw CurrencyMismatchException(currency, other.currency);
    }
  }

  /// Bir xil valyutadagi summalar yig'indisi; bo'sh ro'yxat uchun nol.
  // ignore: prefer_constructors_over_static_methods
  static Money sum(Iterable<Money> items, CurrencyCode currency) =>
      items.fold(Money.zero(currency), (acc, m) => acc + m);

  @override
  bool operator ==(Object other) =>
      other is Money &&
      other.minorUnits == minorUnits &&
      other.currency == currency;

  @override
  int get hashCode => Object.hash(minorUnits, currency);

  /// Faqat diagnostika uchun. Foydalanuvchiga `MoneyFormatter` ko'rsatadi.
  /// Loglarga summa yozilmaydi (SPEC 6).
  @override
  String toString() => 'Money($minorUnits ${currency.iso})';
}

/// Har xil valyutadagi summalarni aralashtirishga urinish.
class CurrencyMismatchException implements Exception {
  const CurrencyMismatchException(this.expected, this.actual);

  final CurrencyCode expected;
  final CurrencyCode actual;

  @override
  String toString() =>
      'CurrencyMismatchException: ${expected.iso} != ${actual.iso}';
}

const int _minSafe = -9223372036854775807 - 1;

int _checkedAdd(int a, int b) {
  final r = a + b;
  // Ishoralari bir xil sonlar qo'shilib, ishora o'zgarsa — toshish.
  if ((a >= 0) == (b >= 0) && (r >= 0) != (a >= 0)) {
    throw const MoneyOverflowException();
  }
  return r;
}

int _checkedMul(int a, int b) {
  if (a == 0 || b == 0) return 0;
  if ((a == _minSafe && b == -1) || (b == _minSafe && a == -1)) {
    throw const MoneyOverflowException();
  }
  final r = a * b;
  if (r ~/ b != a) throw const MoneyOverflowException();
  return r;
}
