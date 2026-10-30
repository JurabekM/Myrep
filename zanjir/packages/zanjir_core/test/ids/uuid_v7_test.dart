import 'dart:math';

import 'package:test/test.dart';
import 'package:zanjir_core/zanjir_core.dart';

void main() {
  final pattern = RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$');

  test('format: versiya 7, variant 10xx', () {
    for (var i = 0; i < 100; i++) {
      expect(uuidV7(), matches(pattern));
    }
  });

  test('vaqt belgisi 48 bit millisekund', () {
    final t = DateTime.utc(2026, 10, 26, 12);
    final id = uuidV7(now: t, random: Random(1));
    final ms = int.parse(id.replaceAll('-', '').substring(0, 12), radix: 16);
    expect(ms, t.millisecondsSinceEpoch);
  });

  test('vaqt bo\'yicha saralanadi', () {
    final a = uuidV7(now: DateTime.utc(2026, 1, 1));
    final b = uuidV7(now: DateTime.utc(2026, 1, 1, 0, 0, 0, 1));
    expect(a.compareTo(b), lessThan(0));
  });

  test('takrorlanmaydi', () {
    final ids = {for (var i = 0; i < 1000; i++) uuidV7()};
    expect(ids, hasLength(1000));
  });
}
