import 'package:decimal/decimal.dart';

/// Summani so'mga yaxlitlaydi (ROUND_HALF_UP). Backend bilan bir xil qoida.
int roundSom(Decimal value) =>
    (value + Decimal.parse('0.5')).floor().toBigInt().toInt();

/// 14500 -> '14 500'.
String formatSom(int amount) {
  final sign = amount < 0 ? '-' : '';
  final digits = amount.abs().toString();
  final buffer = StringBuffer();
  for (var i = 0; i < digits.length; i++) {
    final remaining = digits.length - i;
    if (i > 0 && remaining % 3 == 0) buffer.write(' ');
    buffer.write(digits[i]);
  }
  return '$sign$buffer';
}

/// 2.000 -> '2', 1.500 -> '1.5'.
String formatQty(Decimal qty) {
  var text = qty.toString();
  if (text.contains('.')) {
    text = text.replaceAll(RegExp(r'0+$'), '');
    if (text.endsWith('.')) text = text.substring(0, text.length - 1);
  }
  return text;
}
