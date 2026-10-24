import 'package:baraka_daftari/core/money/money.dart';

/// Bo'linmas bo'sh joy: summa qator oxirida ikkiga bo'linib qolmaydi.
const nbsp = ' ';

/// Pulni ko'rsatish: `8 000 000 soʻm`, `8 000 000,50 soʻm`, `12,50 $`.
///
/// * Guruhlash — 3 xonadan bo'sh joy (bo'linmas), uz va ru uchun bir xil.
/// * Kasr ajratgichi — vergul.
/// * Tiyin/sent faqat nol bo'lmasa ko'rsatiladi (`alwaysShowMinor` bilan
///   majburlash mumkin).
/// * Valyuta belgisi tilga mos: uz — `soʻm`, ru — `сум`.
abstract final class MoneyFormatter {
  static String format(
    Money money, {
    String languageCode = 'uz',
    bool alwaysShowMinor = false,
    bool withSymbol = true,
  }) {
    final digits = money.currency.minorDigits;
    final abs = BigInt.from(money.minorUnits).abs();
    final perMajor = BigInt.from(money.currency.minorPerMajor);
    final major = abs ~/ perMajor;
    final minor = (abs % perMajor).toInt();

    final buffer = StringBuffer();
    if (money.isNegative) buffer.write('-');
    buffer.write(groupDigits(major.toString()));
    if (digits > 0 && (minor != 0 || alwaysShowMinor)) {
      buffer
        ..write(',')
        ..write(minor.toString().padLeft(digits, '0'));
    }
    if (withSymbol) {
      buffer
        ..write(nbsp)
        ..write(symbol(money.currency, languageCode));
    }
    return buffer.toString();
  }

  /// `8000000` → `8 000 000` (bo'linmas bo'sh joy bilan).
  static String groupDigits(String digits) {
    final out = StringBuffer();
    for (var i = 0; i < digits.length; i++) {
      if (i > 0 && (digits.length - i) % 3 == 0) out.write(nbsp);
      out.write(digits[i]);
    }
    return out.toString();
  }

  static String symbol(CurrencyCode currency, String languageCode) =>
      switch (currency) {
        // Oʻzbek imlosi: U+02BB (ʻ), oddiy apostrof emas.
        CurrencyCode.uzs => languageCode == 'ru' ? 'сум' : 'soʻm',
        CurrencyCode.usd => r'$',
        CurrencyCode.eur => '€',
        CurrencyCode.rub => '₽',
      };
}

/// Foydalanuvchi kiritgan summani o'qish: `8 000 000`, `8000000,5`,
/// `12.50`. Valyuta belgisi va bo'sh joylar e'tiborsiz qoldiriladi.
abstract final class MoneyParser {
  static final _pattern = RegExp(r'^(-)?(\d+)(?:[.,](\d+))?$');

  /// Noto'g'ri yozuv yoki kasr qismi valyuta aniqligidan ko'p bo'lsa —
  /// `null`.
  static Money? tryParse(String input, CurrencyCode currency) {
    final cleaned = input
        .replaceAll(RegExp(r"[\s  _']"), '')
        .replaceAll(
          RegExp(r'(so[‘’ʻʼ`]?m|сум|\$|€|₽)$', caseSensitive: false),
          '',
        )
        .replaceAll(RegExp(r'som$', caseSensitive: false), '');
    final match = _pattern.firstMatch(cleaned);
    if (match == null) return null;
    final fraction = match.group(3) ?? '';
    if (fraction.length > currency.minorDigits) return null;
    final majorText = match.group(2)!;
    if (majorText.length > 15) return null; // toshishdan himoya
    final minorText = fraction.padRight(currency.minorDigits, '0');
    final value =
        int.parse(majorText) * currency.minorPerMajor +
        (minorText.isEmpty ? 0 : int.parse(minorText));
    return Money(match.group(1) == null ? value : -value, currency);
  }
}
