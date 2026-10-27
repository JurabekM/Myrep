import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:zanjir_app/theme/tokens.dart';

/// WCAG 2.x nisbiy yorqinlik va kontrast nisbati.
double luminance(Color c) {
  double ch(double v) => v <= 0.04045 ? v / 12.92 : math.pow((v + 0.055) / 1.055, 2.4).toDouble();
  return 0.2126 * ch(c.r) + 0.7152 * ch(c.g) + 0.0722 * ch(c.b);
}

double contrast(Color a, Color b) {
  final (x, y) = (luminance(a), luminance(b));
  return (math.max(x, y) + 0.05) / (math.min(x, y) + 0.05);
}

void main() {
  test('rang juftliklari WCAG AA (matn ≥ 4,5:1) — ilova ishlatadigan barcha matn/fon juftliklari', () {
    final pairs = {
      'ink / paper': (ZanjirColors.ink, ZanjirColors.paper),
      'ink / surface': (ZanjirColors.ink, ZanjirColors.surface),
      'ink / sidebar': (ZanjirColors.ink, ZanjirColors.sidebar),
      'inkMuted / paper': (ZanjirColors.inkMuted, ZanjirColors.paper),
      'inkMuted / surface': (ZanjirColors.inkMuted, ZanjirColors.surface),
      'accentText / paper': (ZanjirColors.accentText, ZanjirColors.paper),
      'accentText / surface': (ZanjirColors.accentText, ZanjirColors.surface),
      'accentInk / accent': (ZanjirColors.accentInk, ZanjirColors.accent),
      'success / paper': (ZanjirColors.success, ZanjirColors.paper),
      'success / surface': (ZanjirColors.success, ZanjirColors.surface),
      'accentInk / success': (ZanjirColors.accentInk, ZanjirColors.success),
      'warn / paper': (ZanjirColors.warn, ZanjirColors.paper),
      'warn / surface': (ZanjirColors.warn, ZanjirColors.surface),
      'danger / paper': (ZanjirColors.danger, ZanjirColors.paper),
      'danger / surface': (ZanjirColors.danger, ZanjirColors.surface),
    };
    for (final MapEntry(key: name, value: (fg, bg)) in pairs.entries) {
      expect(contrast(fg, bg), greaterThanOrEqualTo(4.5), reason: '$name: ${contrast(fg, bg).toStringAsFixed(2)}');
    }
    // Tekshirish sahifasidagi (server) tugma: accent ustida accentInk — xuddi shu juftlik.
    expect(
      contrast(ZanjirColors.ink, ZanjirColors.accent),
      lessThan(4.5),
      reason: 'oq matn accent ustida ishlatilmaydi',
    );
  });
}
