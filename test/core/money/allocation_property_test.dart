import 'dart:math';

import 'package:baraka_daftari/core/money/allocation.dart';
import 'package:baraka_daftari/core/money/money.dart';
import 'package:flutter_test/flutter_test.dart';

/// Property-based test (kickoff Vazifa 3 qabul mezoni): tasodifiy summa va
/// ulushlarda xossalar har doim bajariladi. Urug' qatʼiy — xato chiqsa
/// aynan takrorlanadi; urugʻlar roʻyxati kengaytirilishi mumkin.
void main() {
  const seeds = [1, 7, 42, 2026, 31337];
  const casesPerSeed = 4000;

  int randomAmount(Random r) => switch (r.nextInt(4)) {
    0 => r.nextInt(10), // juda kichik (tiyinlar)
    1 => r.nextInt(1000000),
    2 => r.nextInt(1 << 32) * 1000, // milliardlar
    _ => r.nextInt(1 << 31) * r.nextInt(1 << 31), // ~4.6e18 gacha
  };

  List<int> randomRatios(Random r) {
    final n = 1 + r.nextInt(8);
    final ratios = [
      for (var i = 0; i < n; i++)
        switch (r.nextInt(5)) {
          0 => 0,
          1 => 1 + r.nextInt(10),
          2 => 1 + r.nextInt(10000), // basis point
          _ => 1 + r.nextInt(1 << 30),
        },
    ];
    if (ratios.every((x) => x == 0)) ratios[r.nextInt(n)] = 1;
    return ratios;
  }

  for (final seed in seeds) {
    test("urug' $seed: $casesPerSeed ta tasodifiy holat", () {
      final r = Random(seed);
      for (var i = 0; i < casesPerSeed; i++) {
        final total = Money(randomAmount(r), CurrencyCode.uzs);
        final ratios = randomRatios(r);
        final parts = allocate(total, ratios);
        final reason = 'total=${total.minorUnits} ratios=$ratios';

        // 1. Qismlar soni nisbatlar soniga teng.
        expect(parts, hasLength(ratios.length), reason: reason);

        // 2. Yigʻindi aynan butun summa.
        final sum = parts.fold(
          BigInt.zero,
          (a, m) => a + BigInt.from(m.minorUnits),
        );
        expect(sum, BigInt.from(total.minorUnits), reason: reason);

        final ratioSum = ratios.fold(BigInt.zero, (a, x) => a + BigInt.from(x));
        for (var k = 0; k < parts.length; k++) {
          final part = parts[k];
          // 3. Hech bir qism manfiy emas.
          expect(part.isNegative, isFalse, reason: reason);
          // 4. Valyuta saqlanadi.
          expect(part.currency, total.currency, reason: reason);
          // 5. Nol nisbat → nol qism.
          if (ratios[k] == 0) expect(part.isZero, isTrue, reason: reason);
          // 6. Aniq ulushdan farq < 1 minor birlik: floor ≤ qism ≤ floor+1.
          final exact = BigInt.from(total.minorUnits) * BigInt.from(ratios[k]);
          final floor = exact ~/ ratioSum;
          final value = BigInt.from(part.minorUnits);
          expect(
            value >= floor && value <= floor + BigInt.one,
            isTrue,
            reason: '$reason k=$k',
          );
        }
      }
    });
  }

  test('manfiy summalar: yigʻindi saqlanadi, qismlar musbat emas', () {
    final r = Random(99);
    for (var i = 0; i < 2000; i++) {
      final total = Money(-r.nextInt(1 << 31), CurrencyCode.uzs);
      final ratios = randomRatios(r);
      final parts = allocate(total, ratios);
      expect(
        parts.fold(0, (a, m) => a + m.minorUnits),
        total.minorUnits,
      );
      expect(parts.every((m) => !m.isPositive), isTrue);
    }
  });

  test('deterministik: bir xil kirish — bir xil natija', () {
    const total = Money(123456789, CurrencyCode.uzs);
    const ratios = [3, 3, 3, 1];
    expect(allocate(total, ratios), allocate(total, ratios));
  });
}
