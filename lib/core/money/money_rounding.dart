/// Yaxlitlash rejimlari. Kod bo'ylab tarqoq yaxlitlash taqiqlangan — har
/// qanday bo'lish [MoneyRounding] orqali bajariladi (SPEC 4.2).
enum RoundingMode {
  /// Yarmi juftga (bank yaxlitlashi): 2,5 → 2; 3,5 → 4.
  halfEven,

  /// Yarmi noldan uzoqqa: 2,5 → 3; −2,5 → −3.
  halfUp,

  /// Nolga qarab (kesish): 2,9 → 2; −2,9 → −2.
  down,

  /// Noldan uzoqqa: 2,1 → 3; −2,1 → −3.
  up,

  /// Pastga (−∞ tomon): −2,1 → −3.
  floor,

  /// Yuqoriga (+∞ tomon): 2,1 → 3.
  ceiling,
}

/// Butun sonli arifmetika bilan aniq yaxlitlash. `double` ishlatilmaydi.
abstract final class MoneyRounding {
  /// Pul uchun standart rejim — **half-up** (yarmi noldan uzoqqa). Desktop
  /// ilova bilan bitma-bit moslik uchun (`docs/DESKTOP_PROMPT.md` 4.6,
  /// `spec/test-vectors/`): yaxlitlash faqat shu yerda.
  static const RoundingMode defaultMode = RoundingMode.halfUp;

  /// `numerator / denominator` ni [mode] bo'yicha butun songa yaxlitlaydi.
  static int divide(
    int numerator,
    int denominator, [
    RoundingMode mode = defaultMode,
  ]) => divideBig(BigInt.from(numerator), BigInt.from(denominator), mode);

  /// `a * b / d` — oraliq ko'paytma BigInt'da (toshib ketmaydi).
  static int mulDiv(int a, int b, int d, [RoundingMode mode = defaultMode]) =>
      divideBig(BigInt.from(a) * BigInt.from(b), BigInt.from(d), mode);

  static int divideBig(
    BigInt numerator,
    BigInt denominator, [
    RoundingMode mode = defaultMode,
  ]) {
    if (denominator == BigInt.zero) {
      throw ArgumentError.value(denominator, 'denominator', "nolga bo'lish");
    }
    // Maxrajni musbat qilamiz — ishora suratda qoladi.
    var n = numerator;
    var d = denominator;
    if (d.isNegative) {
      n = -n;
      d = -d;
    }
    final q = n ~/ d; // nolga qarab kesilgan
    final r = n - q * d; // ishorasi n bilan bir xil
    if (r == BigInt.zero) return _toInt(q);

    final positive = !n.isNegative;
    final awayFromZero = positive ? q + BigInt.one : q - BigInt.one;
    final twiceRemainder = r.abs() * BigInt.two;

    final BigInt result;
    switch (mode) {
      case RoundingMode.down:
        result = q;
      case RoundingMode.up:
        result = awayFromZero;
      case RoundingMode.floor:
        result = positive ? q : awayFromZero;
      case RoundingMode.ceiling:
        result = positive ? awayFromZero : q;
      case RoundingMode.halfUp:
        result = twiceRemainder >= d ? awayFromZero : q;
      case RoundingMode.halfEven:
        if (twiceRemainder > d) {
          result = awayFromZero;
        } else if (twiceRemainder < d) {
          result = q;
        } else {
          result = q.isEven ? q : awayFromZero;
        }
    }
    return _toInt(result);
  }

  static final BigInt _maxInt = BigInt.parse('9223372036854775807');
  static final BigInt _minInt = -_maxInt - BigInt.one;

  static int _toInt(BigInt v) {
    if (v > _maxInt || v < _minInt) {
      throw const MoneyOverflowException();
    }
    return v.toInt();
  }
}

/// Natija 64-bitli butun songa sig'madi.
class MoneyOverflowException implements Exception {
  const MoneyOverflowException();

  @override
  String toString() => 'MoneyOverflowException';
}
